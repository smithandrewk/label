# Load environment variables from .env file
include .env
export

# Use environment variables with fallback defaults
DB_NAME ?= $(MYSQL_DATABASE)
DB_USER ?= $(MYSQL_USER)
DB_PASSWORD ?= $(MYSQL_PASSWORD)
DB_HOST ?= $(MYSQL_HOST)
DB_PORT ?= 3306
SCRIPTS_DIR = ./static

# Default target
.PHONY: help
help:
	@echo "Available targets:"
	@echo "  setup         : Complete setup (install deps)"
	@echo "  install-deps  : Install Python dependencies"
	@echo "  run           : Start the Flask application (mounts data directory automatically)"
	@echo "  mount-data    : Mount the remote data directory using SSHFS"
	@echo "  unmount-data  : Unmount the remote data directory"

# Complete setup process
.PHONY: setup
setup: install-deps mount-data
	@echo "Setup completed! You can now run 'make run' to start the application."
	@echo ""
	@echo "Don't forget to:"
	@echo "1. Copy .env.example to .env and update with your credentials"

# Install Python dependencies
.PHONY: install-deps
install-deps:
	@echo "Installing Python dependencies..."
	@pip3 install -r requirements.txt
	@echo "Dependencies installed successfully!"

# Mount the remote data directory using SSHFS
.PHONY: mount-data
mount-data:
	@echo "Setting up data directory..."
	@DATA_DIR_EXPANDED=$$(echo $(DATA_DIR) | sed "s|~|$$HOME|g") && \
	mkdir -p $$DATA_DIR_EXPANDED && \
	if mount | grep -q "$$(echo $$DATA_DIR_EXPANDED | sed 's/\//\\\//g')"; then \
		echo "Data directory already mounted at $$DATA_DIR_EXPANDED"; \
	else \
		echo "Mounting remote data directory at $$DATA_DIR_EXPANDED..."; \
		echo "Using beast username: $(BEAST_USERNAME)"; \
		sshfs $(BEAST_USERNAME)@beast:/media/data/.delta/data $$DATA_DIR_EXPANDED -o reconnect,ServerAliveInterval=15,ServerAliveCountMax=3; \
	fi

# Start the Flask application
.PHONY: run
run: mount-data
	@echo "Starting Flask application..."
	@python3 app.py

# Unmount the remote data directory
.PHONY: unmount-data
unmount-data:
	@echo "Unmounting data directory..."
	@DATA_DIR_EXPANDED=$$(echo $(DATA_DIR) | sed "s|~|$$HOME|g") && \
	if mount | grep -q "$$(echo $$DATA_DIR_EXPANDED | sed 's/\//\\\//g')"; then \
		fusermount -u $$DATA_DIR_EXPANDED; \
		echo "Data directory unmounted from $$DATA_DIR_EXPANDED"; \
	else \
		echo "Data directory not currently mounted at $$DATA_DIR_EXPANDED"; \
	fi