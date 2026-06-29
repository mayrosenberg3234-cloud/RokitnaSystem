"""Decision-log domain model — Requirement 15.

A ``DecisionLog`` is the persistent business record of one professional
architectural decision.  It belongs to one project and keeps the identity of
its author for auditability.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class DecisionLog:
    """A professional decision recorded against a project."""

    project_id: int
    created_by_user_id: int
    decision_text: str
    decision_id: Optional[int] = None
    created_at: Optional[str] = None
