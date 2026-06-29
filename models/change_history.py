"""Change-history domain model — Requirement 15.

Every successfully saved professional decision creates exactly one audit entry
in ``ChangeHistory``.  The entry refers to the decision, its project and the
user who performed the action.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class ChangeHistory:
    """A single audit record describing a saved professional decision."""

    project_id: int
    created_by_user_id: int
    description: str
    decision_id: Optional[int] = None
    change_id: Optional[int] = None
    created_at: Optional[str] = None
