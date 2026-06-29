"""Client domain model."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ClientStatus(str, Enum):
    """Lifecycle status of a client."""

    ACTIVE = "Active"
    ARCHIVED = "Archived"

    @property
    def hebrew_label(self) -> str:
        labels = {
            ClientStatus.ACTIVE: "פעיל",
            ClientStatus.ARCHIVED: "בארכיון",
        }
        return labels[self]


@dataclass
class Client:
    """A customer of the architecture office."""

    name: str
    phone: str
    email: str
    status: ClientStatus = ClientStatus.ACTIVE
    client_id: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def archive(self) -> None:
        """Move this client to the archived lifecycle state.

        The controller decides *when* archiving is required (after checking
        linked projects and permissions).  The business object owns the
        actual state transition, keeping the code aligned with the Client
        State Diagram.
        """
        self.status = ClientStatus.ARCHIVED
