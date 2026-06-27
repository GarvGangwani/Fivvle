"""Add admin-managed coupons and coupon_redemptions tables."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e1f2a3b4c5d6"
down_revision: str | None = "d6e7f8a9b0c1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "coupons",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("credits", sa.Integer(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("max_redemptions", sa.Integer(), nullable=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("limit_reached_message", sa.Text(), nullable=True),
        sa.Column("not_yet_active_message", sa.Text(), nullable=True),
        sa.Column("expired_message", sa.Text(), nullable=True),
        sa.Column("disabled_message", sa.Text(), nullable=True),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )

    op.create_table(
        "coupon_redemptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("coupon_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("credits", sa.Integer(), nullable=False),
        sa.Column("wallet_transaction_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["coupon_id"], ["coupons.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["wallet_transaction_id"],
            ["wallet_transactions.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "coupon_id",
            "user_id",
            name="uq_coupon_redemptions_coupon_user",
        ),
    )
    op.create_index(
        "ix_coupon_redemptions_coupon_id",
        "coupon_redemptions",
        ["coupon_id"],
    )
    op.create_index(
        "ix_coupon_redemptions_user_id",
        "coupon_redemptions",
        ["user_id"],
    )
    op.create_index(
        "ix_coupon_redemptions_created_at",
        "coupon_redemptions",
        ["created_at"],
    )

    op.execute(
        sa.text(
            """
            INSERT INTO coupons (
                id,
                code,
                credits,
                enabled,
                max_redemptions,
                limit_reached_message,
                not_yet_active_message,
                expired_message,
                disabled_message
            )
            VALUES (
                gen_random_uuid(),
                'WELCOME5',
                25,
                true,
                NULL,
                'The welcome offer has reached its limit. Follow us for future promotions.',
                'This welcome offer is not active yet. Check back soon.',
                'This welcome offer has expired.',
                'This welcome offer is no longer available.'
            )
            ON CONFLICT (code) DO NOTHING
            """
        )
    )

    op.execute(
        sa.text(
            """
            INSERT INTO coupon_redemptions (id, coupon_id, user_id, credits, wallet_transaction_id)
            SELECT
                gen_random_uuid(),
                c.id,
                u.id,
                25,
                NULL
            FROM users u
            CROSS JOIN coupons c
            WHERE u.has_redeemed_welcome_coupon = true
              AND c.code = 'WELCOME5'
              AND NOT EXISTS (
                  SELECT 1
                  FROM coupon_redemptions cr
                  WHERE cr.coupon_id = c.id
                    AND cr.user_id = u.id
              )
            """
        )
    )


def downgrade() -> None:
    op.drop_index("ix_coupon_redemptions_created_at", table_name="coupon_redemptions")
    op.drop_index("ix_coupon_redemptions_user_id", table_name="coupon_redemptions")
    op.drop_index("ix_coupon_redemptions_coupon_id", table_name="coupon_redemptions")
    op.drop_table("coupon_redemptions")
    op.drop_table("coupons")
