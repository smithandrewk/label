"""
Centralized logging configuration for the application.
Provides colored console output and consistent formatting across all modules.
"""

import logging
import sys
from typing import Optional

class ColoredFormatter(logging.Formatter):
    """Custom formatter to add colors to log levels"""
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
    }
    RESET = '\033[0m'  # Reset color
    
    def format(self, record):
        # Create a copy of the record to avoid modifying the original
        record_copy = logging.makeLogRecord(record.__dict__)
        
        # Add color to the log level name
        if record_copy.levelname in self.COLORS:
            record_copy.levelname = f"{self.COLORS[record_copy.levelname]}{record_copy.levelname}{self.RESET}"
        
        # Format the message
        formatted = super().format(record_copy)
        return formatted

def setup_logging(
    level: str = "INFO",
    format_string: Optional[str] = None,
    use_colors: bool = True
) -> None:
    """
    Set up centralized logging configuration for the entire application.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_string: Custom format string (uses default if None)
        use_colors: Whether to use colored output in console
    """
    
    # Default format string
    if format_string is None:
        format_string = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Convert string level to logging constant
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    # Get root logger
    root_logger = logging.getLogger()
    
    # Clear any existing handlers to avoid duplicates
    root_logger.handlers.clear()
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    
    # Set up formatter (colored or plain)
    if use_colors and hasattr(sys.stdout, 'isatty') and sys.stdout.isatty():
        # Use colored formatter for TTY terminals
        formatter = ColoredFormatter(
            format_string,
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    else:
        # Use plain formatter for non-TTY (like logs redirected to files)
        formatter = logging.Formatter(
            format_string,
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    console_handler.setFormatter(formatter)
    
    # Add handler to root logger
    root_logger.addHandler(console_handler)
    root_logger.setLevel(numeric_level)
    
    # Prevent propagation to avoid duplicate messages
    root_logger.propagate = False

def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the given name.
    This is a convenience function that ensures consistent logger creation.
    
    Args:
        name: Name for the logger (typically __name__)
        
    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)

def set_log_level(level: str) -> None:
    """
    Change the logging level for all loggers.
    
    Args:
        level: New logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    # Update root logger level
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Update all handlers
    for handler in root_logger.handlers:
        handler.setLevel(numeric_level)

# Auto-setup with default configuration when module is imported
# This can be overridden by calling setup_logging() again with different parameters
setup_logging()
