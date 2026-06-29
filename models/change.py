"""Project-change / approval domain model.

Implements the Part B ``Approval`` flow: the architect documents a change to the
project (with its cost) and submits it for the client's approval.  The client
then approves or rejects it.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ChangeStatus(str, Enum):
    """Approval status of a documented project change."""

    PENDING = "Pending"
    APPROVED = "Approved"
    REJECTED = "Rejected"

    @property
    def hebrew_label(self) -> str:
        labels = {
            ChangeStatus.PENDING: "ממתין לאישור הלקוח",
            ChangeStatus.APPROVED: "אושר",
            ChangeStatus.REJECTED: "נדחה",
        }
        return labels[self]


@dataclass
class ProjectChange:
    """A documented project change awaiting (or having received) approval."""

    project_id: int
    description: str
    created_by_user_id: int
    cost: float = 0.0
    status: ChangeStatus = ChangeStatus.PENDING
    change_id: Optional[int] = None
    decided_by_user_id: Optional[int] = None
    decided_at: Optional[str] = None
    created_at: Optional[str] = None
