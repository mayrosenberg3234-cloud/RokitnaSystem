"""Drawing (architectural sketch) domain model.

Implements the Part B ``Document`` concept for project drawings: an architect
uploads a drawing file for a project, and the project's client can view and
download it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class Drawing:
    """An architectural drawing/sketch file attached to a project."""

    project_id: int
    file_name: str
    stored_path: str
    description: str
    created_by_user_id: int
    drawing_id: Optional[int] = None
    created_at: Optional[str] = None
