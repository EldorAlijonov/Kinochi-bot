"""create subscriptions table

Revision ID: 20260419_0001
Revises:
Create Date: 2026-04-19 12:30:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260419_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "subscriptions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("subscription_type", sa.String(length=50), nullable=False),
        sa.Column("chat_username", sa.String(length=255), nullable=True),
        sa.Column("chat_id", sa.BigInteger(), nullable=True),
        sa.Column("invite_link", sa.String(length=500), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("chat_id", name="uq_subscriptions_chat_id"),
        sa.UniqueConstraint("chat_username", name="uq_subscriptions_chat_username"),
        sa.UniqueConstraint("invite_link", name="uq_subscriptions_invite_link"),
    )
    op.create_index("ix_subscriptions_is_active", "subscriptions", ["is_active"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_subscriptions_is_active", table_name="subscriptions")
    op.drop_table("subscriptions")
