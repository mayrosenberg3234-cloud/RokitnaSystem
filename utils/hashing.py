"""Password hashing helpers.

Passwords are never stored in plain text.  We use SHA-256 (as required by the
project specification) to derive a deterministic hash that can be compared on
login.
"""

from __future__ import annotations

import hashlib
import secrets


def generate_password() -> str:
    """Return a 6-digit numeric password for a newly provisioned client account.

    Digits only — no case sensitivity, no ambiguous characters, easy to read
    aloud or type from a printed sheet.
    """
    return "".join(secrets.choice("0123456789") for _ in range(6))


def hash_password(password: str) -> str:
    """Return the hexadecimal SHA-256 digest of ``password``."""
    if password is None:
        raise ValueError("Password must not be None")
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    """Return ``True`` when ``password`` matches the stored ``password_hash``."""
    if password is None or password_hash is None:
        return False
    return hash_password(password) == password_hash
