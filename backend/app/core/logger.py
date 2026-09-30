"""
StudyMate RAG — Logging Configuration

Provides a pre-configured logger for the entire application.
"""

import logging
import sys


def get_logger(name: str = "studymate") -> logging.Logger:
    """
    Create and return a logger with a consistent format.
    Uses stdout so Docker/container logs capture it.
    """
    logger = logging.getLogger(name)

    if not logger.handlers:
        logger.setLevel(logging.INFO)

        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.INFO)

        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


logger = get_logger()
