# Load environment variables from .env file
include .env
export

# Use environment variables with fallback defaults
DB_NAME ?= $(MYSQL_DATABASE)
DB_USER ?= $(MYSQL_USER)
DB_PASSWORD ?= $(MYSQL_PASSWORD)
DB_HOST ?= $(MYSQL_HOST)
DB_PORT ?= 3306
MYSQL = mysql -u$(DB_USER) -p$(DB_PASSWORD) -h$(DB_HOST) -P$(DB_PORT)
SCRIPTS_DIR = ./static

# Default target
.PHONY: help
help:
	@echo "Available targets:"
	@echo "  reset-db      : Drop and recreate the database with initial schema"
	@echo "  create-db     : Create the database if it doesn't exist"
	@echo "  drop-db       : Drop the database if it exists"
	@echo "  seed-db       : Populate the database with sample data"
	@echo "  backup-db     : Create a backup of the current database"
	@echo "  restore-backup: Restore database from the latest backup"
	@echo "  run-app       : Start the Flask application"

# Create the database if it doesn't exist
.PHONY: create-db
create-db: $(SCRIPTS_DIR)/schema.sql
	@echo "Creating database $(DB_NAME)..."
	@$(MYSQL) -e "CREATE DATABASE IF NOT EXISTS $(DB_NAME);"
	@$(MYSQL) $(DB_NAME) < $(SCRIPTS_DIR)/schema.sql
	@echo "Database created successfully!"

# Drop the database if it exists
.PHONY: drop-db
drop-db:
	@echo "Dropping database $(DB_NAME)..."
	@$(MYSQL) -e "DROP DATABASE IF EXISTS $(DB_NAME);"
	@echo "Database dropped successfully!"

# Reset the database (drop and recreate)
.PHONY: reset-db
reset-db: drop-db create-db
	@echo "Database reset completed!"

# Seed the database with sample data
.PHONY: seed-db
seed-db: $(SCRIPTS_DIR)/sample_data.sql
	@echo "Seeding database with sample data..."
	@$(MYSQL) $(DB_NAME) < $(SCRIPTS_DIR)/sample_data.sql
	@echo "Sample data loaded successfully!"

# Create a backup of the current database
.PHONY: backup-db
backup-db:
	@mkdir -p ./backups
	@echo "Creating backup of $(DB_NAME)..."
	@BACKUP_FILE="./backups/$(DB_NAME)_$(shell date +%Y%m%d_%H%M%S).sql" && \
	mysqldump -u$(DB_USER) -p$(DB_PASSWORD) -h$(DB_HOST) -P$(DB_PORT) $(DB_NAME) > $$BACKUP_FILE && \
	echo "Database backed up to $$BACKUP_FILE"

# Restore the database from the latest backup
.PHONY: restore-backup
restore-backup:
	@echo "Restoring from the latest backup..."
	@LATEST_BACKUP=$$(ls -t ./backups/$(DB_NAME)_*.sql | head -1) && \
	if [ -z "$$LATEST_BACKUP" ]; then \
		echo "No backup found!"; \
		exit 1; \
	fi && \
	$(MYSQL) -e "DROP DATABASE IF EXISTS $(DB_NAME); CREATE DATABASE $(DB_NAME);" && \
	$(MYSQL) $(DB_NAME) < $$LATEST_BACKUP && \
	echo "Database restored from $$LATEST_BACKUP"

# Start the Flask application
.PHONY: run
run:
	@echo "Starting Flask application..."
	@python3 app.py