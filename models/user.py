"""User domain model and the role enumeration."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class RoleEnum(str, Enum):
    """The three roles supported by the system.

    Inheriting from ``str`` lets the value be stored directly in SQLite and
    compared against plain strings while still benefiting from enum safety.
    """

    OFFICE_MANAGER = "OfficeManager"
    ARCHITECT = "Architect"
    CLIENT = "Client"

    @classmethod
    def from_value(cls, value: str) -> "RoleEnum":
        """Return the matching role for ``value`` or raise ``ValueError``."""
        for role in cls:
            if role.value == value:
                return role
        raise ValueError(f"Unknown role: {value}")

    @property
    def hebrew_label(self) -> str:
        """Human readable Hebrew label used in the GUI."""
        labels = {
            RoleEnum.OFFICE_MANAGER: "מנהל משרד",
            RoleEnum.ARCHITECT: "אדריכלית",
            RoleEnum.CLIENT: "לקוח",
        }
        return labels[self]


@dataclass
class User:
    """A system user able to authenticate and perform role based actions.

    ``client_id`` links a user whose role is ``Client`` to their customer record
    in the ``Clients`` table, so the client portal can show that client's own
    projects, meetings and inquiries.  It is ``None`` for staff users.
    """

    username: str
    password_hash: str
    role: RoleEnum
    is_active: bool = True
    user_id: Optional[int] = None
    client_id: Optional[int] = None
    created_at: Optional[str] = None
