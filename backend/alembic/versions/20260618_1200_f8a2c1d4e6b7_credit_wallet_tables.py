"""Add credit wallet tables and welcome coupon flag."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f8a2c1d4e6b7"
down_revision: str | None = "e4b7c2a1f9d3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "has_redeemed_welcome_coupon",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )

    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE wallet_transaction_type AS ENUM (
                'TOPUP', 'BONUS', 'COUPON', 'SERVICE_USAGE', 'REFUND', 'ADMIN_ADJUSTMENT'
            );
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END $$;
        """
    )
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE payment_order_status AS ENUM ('CREATED', 'PAID', 'FAILED');
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END $$;
        """
    )

    wallet_tx_type = postgresql.ENUM(
        "TOPUP",
        "BONUS",
        "COUPON",
        "SERVICE_USAGE",
        "REFUND",
        "ADMIN_ADJUSTMENT",
        name="wallet_transaction_type",
        create_type=False,
    )
    payment_status = postgresql.ENUM(
        "CREATED",
        "PAID",
        "FAILED",
        name="payment_order_status",
        create_type=False,
    )

    op.create_table(
        "wallets",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("credits_balance", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "total_credits_purchased", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "total_credits_consumed", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index("ix_wallets_user_id", "wallets", ["user_id"])

    op.create_table(
        "wallet_transactions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("wallet_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("type", wallet_tx_type, nullable=False),
        sa.Column("credits", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("experiment_id", sa.UUID(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["wallet_id"], ["wallets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["experiment_id"], ["experiments.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_wallet_transactions_wallet_id", "wallet_transactions", ["wallet_id"])
    op.create_index("ix_wallet_transactions_user_id", "wallet_transactions", ["user_id"])
    op.create_index(
        "ix_wallet_transactions_created_at", "wallet_transactions", ["created_at"]
    )

    op.create_table(
        "payment_orders",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("pack_id", sa.String(length=32), nullable=False),
        sa.Column("usd_cents", sa.Integer(), nullable=False),
        sa.Column("credits_base", sa.Integer(), nullable=False),
        sa.Column("credits_bonus", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("amount_inr_paise", sa.Integer(), nullable=False),
        sa.Column("razorpay_order_id", sa.String(length=64), nullable=False),
        sa.Column("status", payment_status, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("razorpay_order_id"),
    )
    op.create_index("ix_payment_orders_user_id", "payment_orders", ["user_id"])
    op.create_index(
        "ix_payment_orders_razorpay_order_id", "payment_orders", ["razorpay_order_id"]
    )

    op.create_table(
        "processed_webhooks",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("event_id", sa.String(length=128), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id"),
    )

    op.execute(
        sa.text(
            """
            INSERT INTO wallets (id, user_id, credits_balance, total_credits_purchased, total_credits_consumed)
            SELECT gen_random_uuid(), u.id, COALESCE(u.credits_remaining, 0), 0, 0
            FROM users u
            WHERE NOT EXISTS (SELECT 1 FROM wallets w WHERE w.user_id = u.id)
            """
        )
    )


def downgrade() -> None:
    op.drop_table("processed_webhooks")
    op.drop_index("ix_payment_orders_razorpay_order_id", table_name="payment_orders")
    op.drop_index("ix_payment_orders_user_id", table_name="payment_orders")
    op.drop_table("payment_orders")
    op.drop_index("ix_wallet_transactions_created_at", table_name="wallet_transactions")
    op.drop_index("ix_wallet_transactions_user_id", table_name="wallet_transactions")
    op.drop_index("ix_wallet_transactions_wallet_id", table_name="wallet_transactions")
    op.drop_table("wallet_transactions")
    op.drop_index("ix_wallets_user_id", table_name="wallets")
    op.drop_table("wallets")
    op.drop_column("users", "has_redeemed_welcome_coupon")
    op.execute("DROP TYPE IF EXISTS payment_order_status")
    op.execute("DROP TYPE IF EXISTS wallet_transaction_type")
