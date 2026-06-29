"""SQLAlchemy model for the Wallet table.

One wallet per user. Balance and lifetime counters live here; the legacy
``users.credits_remaining`` column is deprecated in favor of this table
(see migration f8a2c1d4e6b7 backfill).

Transaction history is stored in ``wallet_transactions`` (see ``WalletTransaction``).
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy import DateTime, ForeignKey, Integer, desc, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.wallet_transaction import WalletTransaction

if TYPE_CHECKING:
    from app.db.models.user import User


class Wallet(Base):
    __tablename__ = "wallets"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    credits_balance: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=sa.text("0"),
    )
    total_credits_purchased: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=sa.text("0"),
    )
    total_credits_consumed: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=sa.text("0"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user: Mapped[User] = relationship(back_populates="wallet")
    transactions: Mapped[list[WalletTransaction]] = relationship(
        back_populates="wallet",
        cascade="all, delete-orphan",
        order_by=lambda: desc(WalletTransaction.created_at),
    )
