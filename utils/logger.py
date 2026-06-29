"""Central application logger.

Every layer of the system uses this single logger so that all events (logins,
client changes, decisions, reports, permission checks) are recorded in one
place, both to a rotating log file and to the console.
"""

from __future__ import annotations

import logging
from logging import Logger

from config import LOG_PATH

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# A module level singleton so repeated imports do not add duplicate handlers.
_logger: Logger | None = None


def get_logger() -> Logger:
    """Return the shared application logger, configuring it on first use."""
    global _logger
    if _logger is not None:
        return _logger

    logger = logging.getLogger("rokitna")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    # Avoid attaching handlers twice (e.g. on Streamlit script reruns).
    if not logger.handlers:
        formatter = logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)

        file_handler = logging.FileHandler(LOG_PATH, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    _logger = logger
    return logger
