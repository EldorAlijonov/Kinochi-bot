"""add movie bases and movies

Revision ID: 20260420_0002
Revises: 20260419_0001
Create Date: 2026-04-20 10:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260420_0002"
down_revision = "20260419_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "movie_bases",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("base_type", sa.String(length=50), nullable=False),
        sa.Column("chat_username", sa.String(length=255), nullable=True),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("invite_link", sa.String(length=500), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("chat_id", name="uq_movie_bases_chat_id"),
        sa.UniqueConstraint("chat_username", name="uq_movie_bases_chat_username"),
    )
    op.create_index("ix_movie_bases_is_active", "movie_bases", ["is_active"], unique=False)

    op.create_table(
        "movies",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("movie_base_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False, server_default="Nomsiz kino"),
        sa.Column("content_type", sa.String(length=50), nullable=False),
        sa.Column("storage_chat_id", sa.BigInteger(), nullable=False),
        sa.Column("storage_message_id", sa.Integer(), nullable=False),
        sa.Column("file_unique_id", sa.String(length=255), nullable=True),
        sa.Column("caption", sa.String(length=1024), nullable=True),
        sa.Column("original_chat_id", sa.BigInteger(), nullable=True),
        sa.Column("original_message_id", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["movie_base_id"], ["movie_bases.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_movies_code", "movies", ["code"], unique=True)
    op.create_index("ix_movies_movie_base_id", "movies", ["movie_base_id"], unique=False)
    op.create_index("ix_movies_is_active", "movies", ["is_active"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_movies_is_active", table_name="movies")
    op.drop_index("ix_movies_movie_base_id", table_name="movies")
    op.drop_index("ix_movies_code", table_name="movies")
    op.drop_table("movies")
    op.drop_index("ix_movie_bases_is_active", table_name="movie_bases")
    op.drop_table("movie_bases")
