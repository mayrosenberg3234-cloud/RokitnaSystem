"""Payment request domain model."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class PaymentRequestStatus(str, Enum):
    """Lifecycle status of a payment request."""

    OPEN = "Open"
    PAID = "Paid"
    CANCELLED = "Cancelled"

    @property
    def hebrew_label(self) -> str:
        labels = {
            PaymentRequestStatus.OPEN: "פתוח",
            PaymentRequestStatus.PAID: "שולם",
            PaymentRequestStatus.CANCELLED: "בוטל",
        }
        return labels[self]


@dataclass
class PaymentRequest:
    """A request for payment issued against a project.

    ``description`` labels which part of the project the cost is for (for
    example "תכנון אדריכלי" or "עבודות חשמל"), which the financial report uses to
    break the project cost down by part.
    """

    project_id: int
    amount: float
    description: str = ""
    status: PaymentRequestStatus = PaymentRequestStatus.OPEN
    request_id: Optional[int] = None
    created_at: Optional[str] = None
