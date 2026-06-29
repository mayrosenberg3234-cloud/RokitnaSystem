"""Meeting domain model.

A ``Meeting`` is scheduled against a project and is visible to the project's
client.  It implements the Part B ``Meeting`` class (date, time, location,
summary).  A meeting is first *proposed* by the office and the client then
*confirms* it, so the client can approve meetings that require their attendance.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class MeetingStatus(str, Enum):
    """Confirmation status of a meeting."""

    PROPOSED = "Proposed"
    CONFIRMED = "Confirmed"

    @property
    def hebrew_label(self) -> str:
        labels = {
            MeetingStatus.PROPOSED: "ממתינה לאישורך",
            MeetingStatus.CONFIRMED: "אושרה",
        }
        return labels[self]


@dataclass
class Meeting:
    """A meeting scheduled for a project."""

    project_id: int
    meeting_date: str           # YYYY-MM-DD
    meeting_time: str           # HH:MM
    location: str
    summary: str
    status: MeetingStatus = MeetingStatus.PROPOSED
    meeting_id: Optional[int] = None
    created_at: Optional[str] = None
