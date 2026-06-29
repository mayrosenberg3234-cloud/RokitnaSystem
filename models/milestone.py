"""Milestone domain model."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class MilestoneStatus(str, Enum):
    """Lifecycle status of a milestone."""

    PENDING = "Pending"
    IN_PROGRESS = "InProgress"
    DONE = "Done"

    @property
    def hebrew_label(self) -> str:
        labels = {
            MilestoneStatus.PENDING: "ממתין",
            MilestoneStatus.IN_PROGRESS: "בתהליך",
            MilestoneStatus.DONE: "הושלם",
        }
        return labels[self]


@dataclass
class Milestone:
    """A project milestone."""

    project_id: int
    title: str
    status: MilestoneStatus = MilestoneStatus.PENDING
    milestone_id: Optional[int] = None
    created_at: Optional[str] = None
