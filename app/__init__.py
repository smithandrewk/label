from flask import Flask
from flask_cors import CORS
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
    
    CORS(app)
    
    # Initialize database connection function
    from app.services.database_service import get_db_connection
    
    # Initialize repositories
    from app.repositories.project_repository import ProjectRepository
    from app.repositories.session_repository import SessionRepository
    from app.repositories.participant_repository import ParticipantRepository
    from app.repositories.model_repository import ModelRepository
    from app.repositories.raw_dataset_repository import RawDatasetRepository
    
    project_repository = ProjectRepository(get_db_connection=get_db_connection)
    session_repository = SessionRepository(get_db_connection=get_db_connection)
    participant_repository = ParticipantRepository(get_db_connection=get_db_connection)
    model_repository = ModelRepository(get_db_connection=get_db_connection)
    raw_dataset_repository = RawDatasetRepository()
    
    # Initialize services with repositories
    from app.services.project_service import ProjectService
    from app.services.session_service import SessionService
    from app.services.model_service import ModelService
    from app.services.raw_dataset_service import RawDatasetService
    
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
    raw_dataset_service = RawDatasetService()

    # Register blueprints
    from app.routes import main, models, projects, sessions, labelings, raw_datasets

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

    raw_datasets.init_controller(raw_dataset_service=raw_dataset_service)
    app.register_blueprint(raw_datasets.raw_datasets_bp)

    return app