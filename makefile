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
MYSQL_ROOT = mysql -uroot -p -h$(DB_HOST) -P$(DB_PORT)
SCRIPTS_DIR = ./static

# Default target
.PHONY: help
help:
	@echo "Available targets:"
	@echo "  setup         : Complete setup (install deps, create user, database)"
	@echo "  setup-simple  : Simple setup (install deps, create database with root user)"
	@echo "  reset-db      : Drop and recreate the database with initial schema"
	@echo "  create-db     : Create the database if it doesn't exist"
	@echo "  drop-db       : Drop the database if it exists"
	@echo "  setup-user    : Create database user with proper permissions"
	@echo "  seed-db       : Populate the database with sample data (if available)"
	@echo "  backup-db     : Create a backup of the current database"
	@echo "  restore-backup: Restore database from the latest backup"
	@echo "  install-deps  : Install Python dependencies"
	@echo "  run-app       : Start the Flask application"
	@echo "  test-db       : Test database connection"
	@echo "  test-connection: Quick connection test with Python"
	@echo "  test-schema   : Run comprehensive schema compatibility test"
	@echo "  verify-setup  : Verify complete setup and configuration"
	@echo "  show-tables   : Show all tables in the database"

# Complete setup process
.PHONY: setup
setup: install-deps setup-user create-db
	@echo "Setup completed! You can now run 'make run-app' to start the application."
	@echo ""
	@echo "Don't forget to:"
	@echo "1. Copy .env.example to .env and update with your credentials"
	@echo "2. Optionally run 'make seed-db' to add sample data"

# Simple setup without creating new user (uses root)
.PHONY: setup-simple
setup-simple: install-deps create-db-simple
	@echo "Simple setup completed! You can now run 'make run-app' to start the application."
	@echo ""
	@echo "Note: This setup uses the root MySQL user. For production, consider creating a dedicated user."
	@echo "Optionally run 'make seed-db' to add sample data"

# Create the database if it doesn't exist
.PHONY: create-db
create-db: $(SCRIPTS_DIR)/schema.sql
	@echo "Creating database $(DB_NAME)..."
	@$(MYSQL) -e "CREATE DATABASE IF NOT EXISTS $(DB_NAME);"
	@$(MYSQL) $(DB_NAME) < $(SCRIPTS_DIR)/schema.sql
	@echo "Database created successfully!"

# Create database using root user (for simple setup)
.PHONY: create-db-simple
create-db-simple: $(SCRIPTS_DIR)/schema.sql
	@echo "Creating database $(DB_NAME) with root user..."
	@echo "You will be prompted for the MySQL root password..."
	@mysql -uroot -p -h$(DB_HOST) -P$(DB_PORT) -e "CREATE DATABASE IF NOT EXISTS $(DB_NAME);"
	@mysql -uroot -p -h$(DB_HOST) -P$(DB_PORT) $(DB_NAME) < $(SCRIPTS_DIR)/schema.sql
	@echo "Database created successfully!"

# Drop the database if it exists
.PHONY: drop-db
drop-db:
	@echo "Dropping database $(DB_NAME)..."
	@$(MYSQL) -e "DROP DATABASE IF EXISTS $(DB_NAME);"
	@echo "Database dropped successfully!"

# Setup database user with proper permissions
.PHONY: setup-user
setup-user:
	@echo "Setting up database user $(DB_USER)..."
	@echo "You will be prompted for the MySQL root password..."
	@mysql -uroot -p -h$(DB_HOST) -P$(DB_PORT) -e "CREATE USER IF NOT EXISTS '$(DB_USER)'@'localhost' IDENTIFIED BY '$(DB_PASSWORD)';"
	@mysql -uroot -p -h$(DB_HOST) -P$(DB_PORT) -e "GRANT ALL PRIVILEGES ON $(DB_NAME).* TO '$(DB_USER)'@'localhost';"
	@mysql -uroot -p -h$(DB_HOST) -P$(DB_PORT) -e "FLUSH PRIVILEGES;"
	@echo "Database user setup completed!"

# Reset the database (drop and recreate)
.PHONY: reset-db
reset-db: drop-db create-db
	@echo "Database reset completed!"

# Seed the database with sample data
.PHONY: seed-db
seed-db:
	@if [ -f "$(SCRIPTS_DIR)/sample_data.sql" ]; then \
		echo "Seeding database with sample data..."; \
		$(MYSQL) $(DB_NAME) < $(SCRIPTS_DIR)/sample_data.sql; \
		echo "Sample data loaded successfully!"; \
	else \
		echo "Sample data file not found at $(SCRIPTS_DIR)/sample_data.sql"; \
		echo "Skipping seeding step."; \
	fi

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

# Install Python dependencies
.PHONY: install-deps
install-deps:
	@echo "Installing Python dependencies..."
	@pip3 install -r requirements.txt
	@echo "Dependencies installed successfully!"

# Start the Flask application
.PHONY: run
run:
	@echo "Starting Flask application..."
	@python3 app.py

# Alias for run target
.PHONY: run-app
run-app: run

# Test database connection
.PHONY: test-db
test-db:
	@echo "Testing database connection..."
	@$(MYSQL) -e "SELECT 'Connection successful!' as result;"

# Quick connection test with Python
.PHONY: test-connection
test-connection:
	@python3 test_connection.py

# Run comprehensive schema compatibility test
.PHONY: test-schema
test-schema:
	@echo "Running schema compatibility test..."
	@python3 test_schema_compatibility.py

# Verify complete setup and configuration
.PHONY: verify-setup
verify-setup:
	@python3 verify_setup.py

# Show all tables in the database
.PHONY: show-tables
show-tables:
	@echo "Tables in database $(DB_NAME):"
	@$(MYSQL) $(DB_NAME) -e "SHOW TABLES;"