"""
logger.py - Logging and guardrails for PawPal+

Sets up structured logging to both console and file.
Includes input guardrails to validate user inputs before processing.
"""

import logging
import os
from datetime import datetime

LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE = os.path.join(LOG_DIR, f"pawpalplus_{datetime.today().strftime('%Y%m%d')}.log")

# Guardrail constants
MAX_PET_NAME_LEN = 50
MAX_TASK_NAME_LEN = 100
MAX_NOTES_LEN = 500
MAX_QUERY_LEN = 1000
ALLOWED_PET_TYPES = ["Dog", "Cat", "Rabbit", "Bird", "Fish", "Other"]


def setup_logging():
    """Configure root logger with file + console handlers."""
    logger = logging.getLogger("pawpalplus")
    logger.setLevel(logging.DEBUG)

    if logger.handlers:
        return logger  # Already configured

    # File handler - detailed
    fh = logging.FileHandler(LOG_FILE)
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    ))

    # Console handler - info only
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter("%(levelname)s | %(message)s"))

    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger


def validate_pet_input(name: str, pet_type: str) -> tuple[bool, str]:
    """
    Validate pet name and type. Returns (is_valid, error_message).
    """
    if not name or not name.strip():
        return False, "Pet name cannot be empty."
    if len(name) > MAX_PET_NAME_LEN:
        return False, f"Pet name must be under {MAX_PET_NAME_LEN} characters."
    if not name.replace(" ", "").replace("-", "").isalnum():
        return False, "Pet name can only contain letters, numbers, spaces, and hyphens."
    if pet_type not in ALLOWED_PET_TYPES:
        return False, f"Pet type must be one of: {', '.join(ALLOWED_PET_TYPES)}."
    return True, ""


def validate_task_input(task_name: str, notes: str = "") -> tuple[bool, str]:
    """
    Validate task name and notes. Returns (is_valid, error_message).
    """
    if not task_name or not task_name.strip():
        return False, "Task name cannot be empty."
    if len(task_name) > MAX_TASK_NAME_LEN:
        return False, f"Task name must be under {MAX_TASK_NAME_LEN} characters."
    if len(notes) > MAX_NOTES_LEN:
        return False, f"Notes must be under {MAX_NOTES_LEN} characters."
    return True, ""


def validate_query(query: str) -> tuple[bool, str]:
    """
    Validate AI chat query. Returns (is_valid, error_message).
    """
    if not query or not query.strip():
        return False, "Query cannot be empty."
    if len(query) > MAX_QUERY_LEN:
        return False, f"Query must be under {MAX_QUERY_LEN} characters."
    return True, ""


def sanitize_text(text: str) -> str:
    """Strip leading/trailing whitespace and limit length."""
    return text.strip()[:MAX_QUERY_LEN]
