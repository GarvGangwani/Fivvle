"""SQLAlchemy model for the wallet_transactions ledger table.

Append-only audit log of credit movements. Balance changes on ``wallets`` must
always be accompanied by a row here (enforced in wallet_service — Phase 10).

``credits`` is signed: positive adds balance, negative debits.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum as SQLEnum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.enums import WalletTransactionType

if TYPE_CHECKING:
    from app.db.models.experiment import Experiment
    from app.db.models.user import User
    from app.db.models.wallet import Wallet


class WalletTransaction(Base):
    __tablename__ = "wallet_transactions"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    wallet_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("wallets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type: Mapped[WalletTransactionType] = mapped_column(
        SQLEnum(
            WalletTransactionType,
            name="wallet_transaction_type",
            native_enum=False,
            length=32,
        ),
        nullable=False,
    )
    credits: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    experiment_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("experiments.id", ondelete="SET NULL"),
        nullable=True,
    )
    razorpay_payment_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    razorpay_order_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    wallet: Mapped[Wallet] = relationship(back_populates="transactions")
    user: Mapped[User] = relationship(back_populates="wallet_transactions")
    experiment: Mapped[Experiment | None] = relationship()
