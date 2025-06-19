from flask import Flask
from flask_cors import CORS
import os

def create_app():
    app = Flask(__name__)
    
    # Configuration
    app.config['DEBUG'] = True
    
    CORS(app)
    
    from app.services.project_service import ProjectService
    from app.services.session_service import SessionService
    from app.services.model_service import ModelService
    from app.services.database_service import get_db_connection
    session_service = SessionService(get_db_connection=get_db_connection)
    project_service = ProjectService(get_db_connection=get_db_connection)
    model_service   = ModelService(get_db_connection=get_db_connection)

    # Register blueprints
    from app.routes import main, models, projects, sessions

    main.init_controller(session_service=session_service, project_service=project_service)
    app.register_blueprint(main.main_bp)

    projects.init_controller(session_service=session_service, project_service=project_service)
    app.register_blueprint(projects.projects_bp)

    sessions.init_controller(session_service=session_service, project_service=project_service, model_service=model_service)
    app.register_blueprint(sessions.sessions_bp)

    models.init_controller(model_service=model_service)
    app.register_blueprint(models.models_bp)

    return app