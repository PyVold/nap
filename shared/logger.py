# ============================================================================
# utils/logger.py
# ============================================================================

import logging
import sys
import os
from logging.handlers import RotatingFileHandler
from config import settings

def setup_logger(name: str) -> logging.Logger:
    """Setup logger with consistent formatting and file output"""
    logger = logging.getLogger(name)

    # Set log level - use DEBUG if debug_mode is enabled
    if settings.debug_mode:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(getattr(logging, settings.log_level.upper()))

    if not logger.handlers:
        # Create logs directory if it doesn't exist
        log_dir = os.path.dirname(settings.log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)

        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # Console handler (stdout)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # File handler with rotation
        file_handler = RotatingFileHandler(
            settings.log_file,
            maxBytes=settings.log_file_max_bytes,
            backupCount=settings.log_file_backup_count
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        # In debug mode, add more detailed formatter for file
        if settings.debug_mode:
            debug_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(funcName)s() - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(debug_formatter)

    return logger
