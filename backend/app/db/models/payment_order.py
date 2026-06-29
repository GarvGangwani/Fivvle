"""SQLAlchemy model for Razorpay credit-pack purchase orders."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum as SQLEnum, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.enums import PaymentOrderStatus

if TYPE_CHECKING:
    from app.db.models.user import User


class PaymentOrder(Base):
    __tablename__ = "payment_orders"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    pack_id: Mapped[str] = mapped_column(String(32), nullable=False)
    usd_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    credits_base: Mapped[int] = mapped_column(Integer, nullable=False)
    credits_bonus: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    amount_inr_paise: Mapped[int] = mapped_column(Integer, nullable=False)
    razorpay_order_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
        index=True,
    )
    razorpay_payment_id: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        unique=True,
    )
    status: Mapped[PaymentOrderStatus] = mapped_column(
        SQLEnum(
            PaymentOrderStatus,
            name="payment_order_status",
            native_enum=False,
            length=16,
        ),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    paid_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    user: Mapped[User] = relationship(back_populates="payment_orders")
