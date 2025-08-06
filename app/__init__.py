from flask import Flask
from flask_cors import CORS
from flask_compress import Compress
import os
from dotenv import load_dotenv

# Import and configure logging early
from app.logging_config import setup_logging, get_logger

def create_app():
    load_dotenv()
    
    # Set up centralized logging for the entire application
    # You can customize this based on environment variables or config
    log_level = os.getenv('LOG_LEVEL', 'DEBUG')
    setup_logging(level=log_level, use_colors=True)
    
    # Get logger for this module
    logger = get_logger(__name__)
    logger.info("Starting Flask application...")
    
    app = Flask(__name__)
    
    # Configuration
    app.config['DEBUG'] = True
    
    # Enable CORS
    CORS(app)
    
    # Enable gzip compression for all responses
    # This will significantly reduce bandwidth usage for remote connections
    app.config['COMPRESS_MIMETYPES'] = [
        'application/json',
        'text/html',
        'text/css',
        'text/javascript',
        'application/javascript',
        'text/xml',
        'application/xml'
    ]
    app.config['COMPRESS_LEVEL'] = 6  # Good balance of compression vs CPU usage
    app.config['COMPRESS_MIN_SIZE'] = 500  # Only compress responses larger than 500 bytes
    app.config['COMPRESS_ALGORITHM'] = 'gzip'
    
    # Force compression for large JSON responses
    @app.after_request
    def force_compression_for_large_responses(response):
        # Force compression for large JSON responses even if client doesn't request it
        if (response.content_type and 
            'application/json' in response.content_type and
            not response.headers.get('Content-Encoding')):
            
            original_data = response.get_data()
            original_size = len(original_data)
            
            # Only compress large responses
            if original_size > 5000:  # 5KB threshold
                import gzip
                import io
                
                # Compress the response
                gzip_buffer = io.BytesIO()
                with gzip.GzipFile(fileobj=gzip_buffer, mode='wb', compresslevel=6) as gzip_file:
                    gzip_file.write(original_data)
                
                # Update response
                compressed_data = gzip_buffer.getvalue()
                response.set_data(compressed_data)
                response.headers['Content-Encoding'] = 'gzip'
                response.headers['Content-Length'] = len(compressed_data)
                response.headers['Vary'] = 'Accept-Encoding'
                
                # Log compression effectiveness
                compression_ratio = len(compressed_data) / original_size * 100
                savings = (1 - len(compressed_data) / original_size) * 100
                logger.info(f"FORCED COMPRESSION: {original_size/1024:.1f}KB -> {len(compressed_data)/1024:.1f}KB ({compression_ratio:.1f}%, saved {savings:.1f}%)")
        
        return response
    
    Compress(app)
    logger.info("Enabled gzip compression with forced compression for large responses")
    
    # Initialize database connection function
    from app.services.database_service import get_db_connection
    
    # Initialize repositories
    from app.repositories.project_repository import ProjectRepository
    from app.repositories.session_repository import SessionRepository
    from app.repositories.participant_repository import ParticipantRepository
    from app.repositories.model_repository import ModelRepository
    
    project_repository = ProjectRepository(get_db_connection=get_db_connection)
    session_repository = SessionRepository(get_db_connection=get_db_connection)
    participant_repository = ParticipantRepository(get_db_connection=get_db_connection)
    model_repository = ModelRepository(get_db_connection=get_db_connection)
    
    # Initialize services with repositories
    from app.services.project_service import ProjectService
    from app.services.session_service import SessionService
    from app.services.model_service import ModelService
    
    session_service = SessionService(
        get_db_connection=get_db_connection, # TODO: get rid of eventually when repository layer is fully implemented
        session_repository=session_repository,
        project_repository=project_repository
    )
    project_service = ProjectService(
        project_repository=project_repository,
        session_repository=session_repository,
        participant_repository=participant_repository
    )
    model_service = ModelService(
        session_repository=session_repository,
        model_repository=model_repository  # Add this line
    )

    # Register blueprints
    from app.routes import main, models, projects, sessions, labelings, cache

    main.init_controller(session_service=session_service, project_service=project_service)
    app.register_blueprint(main.main_bp)

    projects.init_controller(session_service=session_service, project_service=project_service)
    app.register_blueprint(projects.projects_bp)

    sessions.init_controller(session_service=session_service, project_service=project_service, model_service=model_service)
    app.register_blueprint(sessions.sessions_bp)

    models.init_controller(model_service=model_service, session_service=session_service)
    app.register_blueprint(models.models_bp)

    labelings.init_controller(session_service=session_service, project_service=project_service, model_service=model_service)
    app.register_blueprint(labelings.labelings_bp)

    cache.init_controller()
    app.register_blueprint(cache.cache_bp)

    return app