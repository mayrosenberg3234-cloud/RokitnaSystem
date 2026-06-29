"""Field-note domain model.

Implements the Part B ``FieldNote`` class: an on-site note the architect records
against a project.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class FieldNote:
    """An on-site note recorded by the architect for a project."""

    project_id: int
    description: str
    created_by_user_id: int
    note_id: Optional[int] = None
    created_at: Optional[str] = None
