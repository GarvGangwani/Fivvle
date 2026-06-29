"""Add Razorpay payment metadata columns for wallet top-ups."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b5c6d7e8f9a0"
down_revision: str | None = "a3b4c5d6e7f8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "payment_orders",
        sa.Column("razorpay_payment_id", sa.String(length=64), nullable=True),
    )
    op.create_index(
        "ix_payment_orders_razorpay_payment_id",
        "payment_orders",
        ["razorpay_payment_id"],
        unique=True,
    )

    op.add_column(
        "wallet_transactions",
        sa.Column("razorpay_payment_id", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "wallet_transactions",
        sa.Column("razorpay_order_id", sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("wallet_transactions", "razorpay_order_id")
    op.drop_column("wallet_transactions", "razorpay_payment_id")
    op.drop_index("ix_payment_orders_razorpay_payment_id", table_name="payment_orders")
    op.drop_column("payment_orders", "razorpay_payment_id")
