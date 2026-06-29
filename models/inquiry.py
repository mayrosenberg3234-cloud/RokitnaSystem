"""Client inquiry domain model.

A ``ClientInquiry`` is a request/question a client submits to the office.  It
implements the Part B ``ClientInquiry`` class (content, date) and its
``sendInquiry()`` behaviour, surfaced through the client portal.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class InquiryStatus(str, Enum):
    """Lifecycle status of a client inquiry."""

    OPEN = "Open"
    REVIEWED = "Reviewed"

    @property
    def hebrew_label(self) -> str:
        labels = {
            InquiryStatus.OPEN: "ממתינה לטיפול",
            InquiryStatus.REVIEWED: "טופלה",
        }
        return labels[self]


@dataclass
class ClientInquiry:
    """A request submitted by a client to a specific office role.

    ``target_role`` is the ``RoleEnum`` value of the recipient the client chose
    (the office manager or the architect), so the request reaches the relevant
    person.
    """

    client_id: int
    content: str
    target_role: str = "OfficeManager"
    status: InquiryStatus = InquiryStatus.OPEN
    inquiry_id: Optional[int] = None
    created_at: Optional[str] = None
