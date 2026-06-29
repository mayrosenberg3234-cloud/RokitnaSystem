"""Password hashing helpers.

Passwords are never stored in plain text.  We use SHA-256 (as required by the
project specification) to derive a deterministic hash that can be compared on
login.
"""

from __future__ import annotations

import hashlib
import secrets


def generate_password(length: int = 8) -> str:
    """Return a readable random password for a newly provisioned account.

    Uses an unambiguous alphabet (no 0/O/1/l) so the office manager can dictate
    it to the client without confusion, and ``secrets`` for cryptographic
    randomness.
    """
    alphabet = "ABCDEFGHJKMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789"
    return "".join(secrets.choice(alphabet) for _ in range(length))


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
