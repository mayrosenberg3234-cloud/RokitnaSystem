"""Input validation helpers shared by the controllers.

All user supplied data passes through this service before it reaches the
repository.  Validation failures raise :class:`ValidationError`, which the
controllers translate into friendly Hebrew messages — a stack trace is never
shown to the end user.
"""

from __future__ import annotations

import re

# Pragmatic patterns: an email must look like ``name@host.tld`` and a phone
# number must contain 9-10 digits (optionally with separators / leading +).
_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PHONE_PATTERN = re.compile(r"^\+?[0-9\-\s]{9,15}$")


class ValidationError(Exception):
    """Raised when user supplied input fails a validation rule."""


def require_non_empty(value: str, field_name: str) -> str:
    """Return ``value`` stripped, raising when it is empty or ``None``."""
    if value is None or value.strip() == "":
        raise ValidationError(f"השדה '{field_name}' הוא חובה")
    return value.strip()


def validate_email(email: str) -> str:
    """Validate and normalise an email address."""
    email = require_non_empty(email, "אימייל")
    if not _EMAIL_PATTERN.match(email):
        raise ValidationError("כתובת האימייל אינה תקינה")
    return email


def validate_phone(phone: str) -> str:
    """Validate and normalise a phone number.

    The number is normalised by removing spaces and dashes so the same number
    entered in different formats (``050-1234567`` vs ``0501234567``) is stored
    and compared identically.  This prevents a duplicate client slipping through
    the phone uniqueness check on a cosmetic formatting difference.
    """
    phone = require_non_empty(phone, "טלפון")
    if not _PHONE_PATTERN.match(phone):
        raise ValidationError("מספר הטלפון אינו תקין (9–15 ספרות, ניתן עם מקפים או רווחים)")
    normalized = phone.replace(" ", "").replace("-", "")
    return normalized
