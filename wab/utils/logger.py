#!/usr/bin/env python3
"""
Logger Configuration
Sets up logging for the WhatsApp webhook application.
"""

import logging
import os
from datetime import datetime
from pathlib import Path


def setup_logger(name, log_level=None):
    """
    Set up a logger with console and file handlers.

    Args:
        name (str): Logger name (usually __name__ of calling module)
        log_level (str, optional): Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    Returns:
        logging.Logger: Configured logger instance
    """
    # Create logger
    logger = logging.getLogger(name)

    # Set log level from environment or parameter
    if log_level is None:
        log_level = os.environ.get('LOG_LEVEL', 'INFO')

    logger.setLevel(getattr(logging, log_level.upper()))

    # Avoid duplicate handlers
    if logger.handlers:
        return logger

    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    simple_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Console handler (simpler format)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    logger.addHandler(console_handler)

    # File handler (detailed format)
    try:
        # Create logs directory if it doesn't exist
        log_dir = Path(__file__).parent.parent / 'logs'
        log_dir.mkdir(exist_ok=True)

        # Create log file with date
        log_file = log_dir / f"webhook_{datetime.now().strftime('%Y%m%d')}.log"

        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(detailed_formatter)
        logger.addHandler(file_handler)

    except Exception as e:
        logger.warning(f"Could not create file handler: {e}")

    return logger
