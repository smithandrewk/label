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
	@echo "Creating backup of $(DB_NAME)..."
	@BACKUP_FILE="./backups/$(DB_NAME)_$(shell date +%Y%m%d_%H%M%S).sql" && \
	mysqldump -u$(DB_USER) -p$(DB_PASSWORD) -h$(DB_HOST) -P $(DB_PORT) $(DB_NAME) > $$BACKUP_FILE && \
	echo "Database backed up to $$BACKUP_FILE"

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
