"""Alert domain model."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class Alert:
    """A notification raised in the context of a project."""

    project_id: int
    message: str
    alert_id: Optional[int] = None
    created_at: Optional[str] = None
