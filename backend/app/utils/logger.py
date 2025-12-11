"""
Centralized logging configuration with structured logging support
"""
import logging
import sys
import os
from typing import Optional
from datetime import datetime
import traceback


class ContextFilter(logging.Filter):
    """Filter to add context information to log records"""
    
    def filter(self, record):
        # Add function name and line number if not already present
        if not hasattr(record, 'funcName') or not record.funcName:
            record.funcName = record.pathname.split('/')[-1] if record.pathname else 'unknown'
        
        # Add module name
        record.module_name = record.name.split('.')[-1] if record.name else 'unknown'
        
        # Add timestamp in ISO format
        record.iso_time = datetime.utcnow().isoformat() + 'Z'
        
        return True


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured logging with better readability"""
    
    # Color codes for different log levels
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'        # Reset
    }
    
    def __init__(self, use_colors: bool = None, include_location: bool = True):
        """
        Initialize formatter
        
        Args:
            use_colors: Whether to use colors (auto-detect if None)
            include_location: Whether to include file:line in logs
        """
        super().__init__()
        self.include_location = include_location
        
        # Auto-detect color support
        if use_colors is None:
            self.use_colors = sys.stdout.isatty() and os.getenv('TERM') != 'dumb'
        else:
            self.use_colors = use_colors
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with structured information"""
        # Get color for log level
        level_color = self.COLORS.get(record.levelname, '')
        reset_color = self.COLORS['RESET'] if self.use_colors else ''
        
        # Format timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        
        # Build location string
        location = ""
        if self.include_location:
            filename = record.pathname.split('/')[-1] if record.pathname else 'unknown'
            location = f"{filename}:{record.lineno}"
            if record.funcName and record.funcName != '<module>':
                location += f":{record.funcName}()"
            location = f" [{location}]"
        
        # Format message
        message = record.getMessage()
        
        # Add exception info if present
        if record.exc_info:
            message += "\n" + self.formatException(record.exc_info)
        
        # Build log line
        log_parts = [
            f"{level_color}{record.levelname:8}{reset_color}",
            f"{timestamp}",
            f"[{record.module_name:20}]",
            f"{location}",
            message
        ]
        
        return " | ".join(part for part in log_parts if part.strip())


def setup_logging(
    level: str = None,
    use_colors: bool = None,
    include_location: bool = True,
    log_file: Optional[str] = None
) -> logging.Logger:
    """
    Set up centralized logging configuration
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        use_colors: Whether to use colors in console output
        include_location: Whether to include file:line:function in logs
        log_file: Optional file path to write logs to
    
    Returns:
        Root logger
    """
    # Get log level from environment or use default
    if level is None:
        level = os.getenv('LOG_LEVEL', 'INFO').upper()
    
    log_level = getattr(logging, level, logging.INFO)
    
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove existing handlers to avoid duplicates
    root_logger.handlers.clear()
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_formatter = StructuredFormatter(use_colors=use_colors, include_location=include_location)
    console_handler.setFormatter(console_formatter)
    console_handler.addFilter(ContextFilter())
    root_logger.addHandler(console_handler)
    
    # Create file handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(log_level)
        # File logs don't need colors
        file_formatter = StructuredFormatter(use_colors=False, include_location=include_location)
        file_handler.setFormatter(file_formatter)
        file_handler.addFilter(ContextFilter())
        root_logger.addHandler(file_handler)
    
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a module
    
    Args:
        name: Logger name (typically __name__)
    
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


class LoggerMixin:
    """Mixin class to add logging capabilities to any class"""
    
    @property
    def logger(self) -> logging.Logger:
        """Get logger for this class"""
        return logging.getLogger(self.__class__.__module__ + '.' + self.__class__.__name__)


def log_exception(logger: logging.Logger, exc: Exception, context: str = "", level: int = logging.ERROR):
    """
    Log an exception with full context and stack trace
    
    Args:
        logger: Logger instance
        exc: Exception to log
        context: Additional context string
        level: Log level (default: ERROR)
    """
    exc_type = type(exc).__name__
    exc_msg = str(exc)
    
    # Get full traceback
    tb_lines = traceback.format_exception(type(exc), exc, exc.__traceback__)
    tb_str = ''.join(tb_lines)
    
    # Build log message
    msg_parts = []
    if context:
        msg_parts.append(f"{context}:")
    msg_parts.append(f"{exc_type}: {exc_msg}")
    
    logger.log(level, "\n".join(msg_parts) + f"\n{tb_str}", exc_info=False)


# Initialize logging on import
setup_logging()

