"""add statistics tracking

Revision ID: 20260421_0005
Revises: 20260421_0004
Create Date: 2026-04-21 18:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260421_0005"
down_revision = "20260421_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("username", sa.String(length=255), nullable=True),
        sa.Column(
            "joined_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "last_active_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("is_banned", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("referred_by", sa.BigInteger(), nullable=True),
        sa.Column("start_payload", sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint("telegram_id"),
    )
    op.create_index("ix_users_joined_at", "users", ["joined_at"], unique=False)
    op.create_index("ix_users_last_active_at", "users", ["last_active_at"], unique=False)
    op.create_index("ix_users_referred_by", "users", ["referred_by"], unique=False)

    op.create_table(
        "user_action_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("action_type", sa.String(length=50), nullable=False),
        sa.Column("movie_id", sa.Integer(), nullable=True),
        sa.Column("movie_code", sa.String(length=32), nullable=True),
        sa.Column("subscription_id", sa.Integer(), nullable=True),
        sa.Column("is_success", sa.Boolean(), nullable=True),
        sa.Column("payload", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_user_action_logs_action_created",
        "user_action_logs",
        ["action_type", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_user_action_logs_user_created",
        "user_action_logs",
        ["user_telegram_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_user_action_logs_movie_id",
        "user_action_logs",
        ["movie_id"],
        unique=False,
    )
    op.create_index(
        "ix_user_action_logs_subscription_id",
        "user_action_logs",
        ["subscription_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_user_action_logs_subscription_id", table_name="user_action_logs")
    op.drop_index("ix_user_action_logs_movie_id", table_name="user_action_logs")
    op.drop_index("ix_user_action_logs_user_created", table_name="user_action_logs")
    op.drop_index("ix_user_action_logs_action_created", table_name="user_action_logs")
    op.drop_table("user_action_logs")

    op.drop_index("ix_users_referred_by", table_name="users")
    op.drop_index("ix_users_last_active_at", table_name="users")
    op.drop_index("ix_users_joined_at", table_name="users")
    op.drop_table("users")
