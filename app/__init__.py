from flask import Flask
from flask_cors import CORS
import os
from dotenv import load_dotenv

def create_app():
    load_dotenv()
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
    
    project_repository = ProjectRepository(get_db_connection=get_db_connection)
    session_repository = SessionRepository(get_db_connection=get_db_connection)
    participant_repository = ParticipantRepository(get_db_connection=get_db_connection)
    
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
        session_repository=session_repository
    )

    # Register blueprints
    from app.routes import main, models, projects, sessions, labelings

    main.init_controller(session_service=session_service, project_service=project_service)
    app.register_blueprint(main.main_bp)

    projects.init_controller(session_service=session_service, project_service=project_service)
    app.register_blueprint(projects.projects_bp)

    sessions.init_controller(session_service=session_service, project_service=project_service, model_service=model_service)
    app.register_blueprint(sessions.sessions_bp)

    models.init_controller(model_service=model_service)
    app.register_blueprint(models.models_bp)

    labelings.init_controller(session_service=session_service, project_service=project_service, model_service=model_service)
    app.register_blueprint(labelings.labelings_bp)

    return app