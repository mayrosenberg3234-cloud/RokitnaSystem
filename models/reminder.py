"""Reminder domain model.

A reminder is a short message the office manager sends to a target audience
(a specific client or all architects).  Recipients see it on their screen.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class Reminder:
    """A reminder message sent by the office manager."""

    message: str
    created_by_user_id: int
    target_role: str                       # RoleEnum value of the audience
    target_client_id: Optional[int] = None  # set when the audience is one client
    reminder_id: Optional[int] = None
    created_at: Optional[str] = None
