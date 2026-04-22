"""add broadcast campaigns

Revision ID: 20260421_0007
Revises: 20260421_0006
Create Date: 2026-04-21 22:20:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260421_0007"
down_revision = "20260421_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "broadcast_campaigns",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("admin_id", sa.BigInteger(), nullable=False),
        sa.Column("content_type", sa.String(length=50), nullable=False),
        sa.Column("text", sa.Text(), nullable=True),
        sa.Column("source_chat_id", sa.BigInteger(), nullable=False),
        sa.Column("source_message_id", sa.Integer(), nullable=False),
        sa.Column("target_type", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_broadcast_campaigns_created_at",
        "broadcast_campaigns",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_broadcast_campaigns_status",
        "broadcast_campaigns",
        ["status"],
        unique=False,
    )

    op.create_table(
        "broadcast_deliveries",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("campaign_id", sa.Integer(), nullable=False),
        sa.Column("target_type", sa.String(length=50), nullable=False),
        sa.Column("target_chat_id", sa.BigInteger(), nullable=True),
        sa.Column("target_identifier", sa.String(length=255), nullable=True),
        sa.Column("sent_message_id", sa.Integer(), nullable=True),
        sa.Column("delivery_status", sa.String(length=50), nullable=False),
        sa.Column("error_text", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["campaign_id"],
            ["broadcast_campaigns.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_broadcast_deliveries_campaign_id",
        "broadcast_deliveries",
        ["campaign_id"],
        unique=False,
    )
    op.create_index(
        "ix_broadcast_deliveries_target_type",
        "broadcast_deliveries",
        ["target_type"],
        unique=False,
    )
    op.create_index(
        "ix_broadcast_deliveries_delivery_status",
        "broadcast_deliveries",
        ["delivery_status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_broadcast_deliveries_delivery_status", table_name="broadcast_deliveries")
    op.drop_index("ix_broadcast_deliveries_target_type", table_name="broadcast_deliveries")
    op.drop_index("ix_broadcast_deliveries_campaign_id", table_name="broadcast_deliveries")
    op.drop_table("broadcast_deliveries")
    op.drop_index("ix_broadcast_campaigns_status", table_name="broadcast_campaigns")
    op.drop_index("ix_broadcast_campaigns_created_at", table_name="broadcast_campaigns")
    op.drop_table("broadcast_campaigns")
