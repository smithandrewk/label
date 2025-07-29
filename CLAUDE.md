# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Development Commands

### Application Management
- `make run` - Start the Flask application on localhost:5000
- `make test` - Run pytest tests with verbose output
- `python3 -m pytest -v` - Alternative test command

### Database Operations
- `make backup` - Create timestamped database backup in ./backups/
- `make reset-db` - Drop and recreate database (auto-backs up first)
- `make show-tables` - Display all database tables
- `make restore-backup` - Interactive restore from available backups

### Development Workflow
- `make help` - Show all available make targets
- Tests are configured via pytest.ini with testpaths=tests, verbose output, and deprecation warnings filtered

## Architecture Overview

This is a Flask-based web application for labeling smoking detection data from accelerometer sensors with a clean layered architecture.

### Backend Architecture (Python/Flask)
- **Flask App Factory Pattern**: `app/__init__.py` creates app with dependency injection
- **Repository Layer**: Data access objects in `app/repositories/` (project, session, participant, model repositories)
- **Service Layer**: Business logic in `app/services/` (project_service, session_service, model_service, model_processor)
- **Route Layer**: Flask blueprints in `app/routes/` (main, projects, sessions, models, labelings)
- **Database**: MySQL with connection handling in `database_service.py`

### Frontend Architecture (JavaScript)
Follows a 3-layer architecture documented in `app/static/js/README.md`:
- **API Layer** (`js/api/`): HTTP requests to backend (projectAPI.js, sessionAPI.js, modelAPI.js)
- **Service Layer** (`js/services/`): Business logic and data manipulation
- **Controller Layer** (`script.js`): UI coordination and DOM manipulation
- **Utilities**: `helpers.js` for pure utility functions

### Database Schema
Core tables: participants, projects, sessions, models, session_lineage
- Projects belong to participants
- Sessions belong to projects  
- Sessions contain JSON `bouts` field for labeled smoking intervals
- Models table for ML model management

### Model Integration System
Custom ML models must implement three methods:
- `preprocess(self, data)` - Convert raw DataFrame to model input
- `run(self, preprocessed_data, device='cpu')` - Execute inference
- `postprocess(self, raw_predictions, raw_data)` - Convert output to time-domain predictions

Models are dynamically loaded via `model_processor.py` and managed through the models service.

## Environment Configuration
- Uses `.env` file for configuration (MySQL credentials, data directories)
- Environment variables: MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE, DATA_DIR, MODEL_DIR
- Centralized logging configured in `logging_config.py` with LOG_LEVEL environment variable

## Key Development Notes
- Repository pattern partially implemented (TODO comment in app/__init__.py indicates ongoing migration)
- Flask blueprints use controller initialization pattern with dependency injection
- Frontend follows strict separation of concerns - API calls must go through API layer, business logic in service layer
- Database backups are automatically created before destructive operations
- Session data includes hierarchical project/participant relationships for export functionality