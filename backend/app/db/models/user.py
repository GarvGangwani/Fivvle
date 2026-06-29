"""SQLAlchemy model for the User table."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy import Boolean, DateTime, Integer, String, desc, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.payment_order import PaymentOrder
from app.db.models.wallet import Wallet
from app.db.models.wallet_transaction import WalletTransaction

if TYPE_CHECKING:
    from app.db.models.experiment import Experiment


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    firebase_uid: Mapped[str] = mapped_column(
        String(128),
        unique=True,
        nullable=False,
        index=True,
    )
    email: Mapped[str] = mapped_column(
        String(320),
        unique=True,
        nullable=False,
        index=True,
    )
    name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    credits_remaining: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    has_redeemed_welcome_coupon: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=sa.text("false"),
        default=False,
    )
    is_admin: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=sa.text("false"),
        default=False,
    )

    # --- Relationships ---
    experiments: Mapped[list[Experiment]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    wallet: Mapped[Wallet | None] = relationship(
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    wallet_transactions: Mapped[list[WalletTransaction]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        order_by=lambda: desc(WalletTransaction.created_at),
    )
    payment_orders: Mapped[list[PaymentOrder]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
