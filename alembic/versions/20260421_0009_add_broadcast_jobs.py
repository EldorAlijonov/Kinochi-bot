"""add broadcast jobs

Revision ID: 20260421_0009
Revises: 20260421_0008
Create Date: 2026-04-21 23:30:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260421_0009"
down_revision = "20260421_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "broadcast_jobs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("campaign_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("processed_count", sa.Integer(), nullable=False),
        sa.Column("sent_count", sa.Integer(), nullable=False),
        sa.Column("failed_count", sa.Integer(), nullable=False),
        sa.Column("cancel_requested", sa.Boolean(), nullable=False),
        sa.Column("last_progress_message_id", sa.Integer(), nullable=True),
        sa.Column("admin_chat_id", sa.BigInteger(), nullable=True),
        sa.Column("error_text", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["campaign_id"], ["broadcast_campaigns.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_broadcast_jobs_status", "broadcast_jobs", ["status"], unique=False)
    op.create_index("ix_broadcast_jobs_campaign_id", "broadcast_jobs", ["campaign_id"], unique=False)
    op.create_index("ix_broadcast_jobs_created_at", "broadcast_jobs", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_broadcast_jobs_created_at", table_name="broadcast_jobs")
    op.drop_index("ix_broadcast_jobs_campaign_id", table_name="broadcast_jobs")
    op.drop_index("ix_broadcast_jobs_status", table_name="broadcast_jobs")
    op.drop_table("broadcast_jobs")
