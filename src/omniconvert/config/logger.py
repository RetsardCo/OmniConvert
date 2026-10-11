"""Structured logging configuration for OmniConvert."""

import logging
import sys
from datetime import datetime
from omniconvert.config.paths import get_logs_dir

def setup_logging(level: int = logging.INFO) -> None:
    """Initialize console and file logging."""
    logger = logging.getLogger()
    logger.setLevel(level)

    # Clear existing handlers
    for handler in list(logger.handlers):
        logger.removeHandler(handler)

    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s:%(lineno)d] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File Handler
    try:
        logs_dir = get_logs_dir()
        log_file = logs_dir / f"omniconvert_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        logger.warning("Could not set up file log handler: %s", e)
