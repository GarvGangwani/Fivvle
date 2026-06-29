"""Per-user coupon redemption audit rows."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.coupon import Coupon
    from app.db.models.user import User
    from app.db.models.wallet_transaction import WalletTransaction


class CouponRedemption(Base):
    __tablename__ = "coupon_redemptions"
    __table_args__ = (
        UniqueConstraint("coupon_id", "user_id", name="uq_coupon_redemptions_coupon_user"),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    coupon_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("coupons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    credits: Mapped[int] = mapped_column(Integer, nullable=False)
    wallet_transaction_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("wallet_transactions.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    coupon: Mapped[Coupon] = relationship(back_populates="redemptions")
    user: Mapped[User] = relationship()
    wallet_transaction: Mapped[WalletTransaction | None] = relationship()
