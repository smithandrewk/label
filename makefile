# Load environment variables from .env file
include .env
export

# Use environment variables with fallback defaults
DB_NAME ?= $(MYSQL_DATABASE)
DB_USER ?= $(MYSQL_USER)
DB_PASSWORD ?= $(MYSQL_PASSWORD)
DB_HOST ?= localhost
DB_PORT ?= 3306
MYSQL = mysql -u$(DB_USER) -p$(DB_PASSWORD) -h$(DB_HOST) -P $(DB_PORT)
SCRIPTS_DIR = ./app/static

# Default target
.DEFAULT_GOAL := help

# Default target
.PHONY: help
help:
	@echo "Available targets:"
	@echo "  run           : Start the Flask application (default)"
	@echo "  test          : Run pytest tests"
	@echo "  backup        : Create a backup of the current database"
	@echo "  restore-backup: List and restore from available backups (auto-backs up first)"
	@echo "  show-tables   : Show all tables in the database"
	@echo "  reset-db      : Drop and recreate the database with initial schema (auto-backs up first)"
	@echo "  clean-data    : DESTRUCTIVE: Remove all project data files (prompts for confirmation)"
	@echo "  clean         : DESTRUCTIVE: Remove all data files AND reset database (prompts for confirmation)"

# Start the Flask application
.PHONY: run
run:
	@echo "Starting Flask application..."
	@flask run --host 0.0.0.0

# Run pytest tests
.PHONY: test
test:
	@echo "Running pytest tests..."
	@python3 -m pytest -v

# Create a backup of the current database
.PHONY: backup
backup:
	@mkdir -p ./backups
	@echo "Checking if database $(DB_NAME) exists..."
	@if $(MYSQL) -e "USE $(DB_NAME);" 2>/dev/null; then \
		echo "Creating backup of $(DB_NAME)..."; \
		BACKUP_FILE="./backups/$(DB_NAME)_$(shell date +%Y%m%d_%H%M%S).sql" && \
		mysqldump -u$(DB_USER) -p$(DB_PASSWORD) -h$(DB_HOST) -P $(DB_PORT) $(DB_NAME) > $$BACKUP_FILE && \
		echo "Database backed up to $$BACKUP_FILE"; \
	else \
		echo "Database $(DB_NAME) does not exist. Skipping backup."; \
	fi

# List and restore from available backups (with automatic backup first)
.PHONY: restore-backup
restore-backup: backup
	@echo ""
	@echo "Available backups:"
	@ls -la ./backups/$(DB_NAME)_*.sql 2>/dev/null | cat -n || (echo "No backups found!" && exit 1)
	@echo ""
	@echo -n "Enter the number of the backup to restore (or press Ctrl+C to cancel): "
	@read choice && \
	BACKUP_FILE=$$(ls -la ./backups/$(DB_NAME)_*.sql 2>/dev/null | sed -n "$${choice}p" | awk '{print $$NF}') && \
	if [ -z "$$BACKUP_FILE" ]; then \
		echo "Invalid selection!"; \
		exit 1; \
	fi && \
	echo "Restoring from $$BACKUP_FILE..." && \
	$(MYSQL) -e "DROP DATABASE IF EXISTS $(DB_NAME); CREATE DATABASE $(DB_NAME);" && \
	$(MYSQL) $(DB_NAME) < $$BACKUP_FILE && \
	echo "Database restored from $$BACKUP_FILE"

# Show all tables in the database
.PHONY: show-tables
show-tables:
	@echo "Tables in database $(DB_NAME):"
	@$(MYSQL) $(DB_NAME) -e "SHOW TABLES;"

# Reset the database (drop and recreate) with automatic backup first
.PHONY: reset-db
reset-db: backup $(SCRIPTS_DIR)/schema.sql
	@echo ""
	@echo "Dropping and recreating database $(DB_NAME)..."
	@$(MYSQL) -e "DROP DATABASE IF EXISTS $(DB_NAME);"
	@$(MYSQL) -e "CREATE DATABASE $(DB_NAME);"
	@$(MYSQL) $(DB_NAME) < $(SCRIPTS_DIR)/schema.sql
	@echo "Database reset completed!"

# Remove all project data files (DESTRUCTIVE OPERATION)
.PHONY: clean-data
clean-data:
	@DATA_DIR_EXPANDED=$$(python3 -c "import os; print(os.path.expanduser('$(DATA_DIR)'))") && \
	echo "⚠️  WARNING: DESTRUCTIVE OPERATION ⚠️" && \
	echo "" && \
	echo "This will permanently delete ALL project data files in:" && \
	echo "  $$DATA_DIR_EXPANDED" && \
	echo "" && \
	if [ -d "$$DATA_DIR_EXPANDED" ]; then \
		echo "Directory contents to be deleted:" && \
		ls -la "$$DATA_DIR_EXPANDED" 2>/dev/null || echo "  (directory exists but is empty or inaccessible)" && \
		echo ""; \
	else \
		echo "Directory does not exist: $$DATA_DIR_EXPANDED" && \
		echo "Nothing to delete." && \
		exit 0; \
	fi && \
	echo "This action CANNOT be undone!" && \
	echo "" && \
	echo -n "Type 'DELETE ALL DATA' to confirm (or press Ctrl+C to cancel): " && \
	read confirmation && \
	if [ "$$confirmation" = "DELETE ALL DATA" ]; then \
		echo "Deleting all project data..." && \
		rm -rf "$$DATA_DIR_EXPANDED" && \
		echo "✅ All project data has been deleted from $$DATA_DIR_EXPANDED" && \
		echo "📝 Note: Database records still exist. Use 'make reset-db' to clear the database as well."; \
	else \
		echo "❌ Confirmation text did not match. Operation cancelled." && \
		exit 1; \
	fi

# Complete destructive reset: remove all data files and reset database
.PHONY: clean
clean: clean-data reset-db
	@echo ""
	@echo "🧹 Complete cleanup finished!"
	@echo "   ✅ All project data files deleted"
	@echo "   ✅ Database reset to initial state"
	@echo ""
	@echo "The application is now in a clean state."
