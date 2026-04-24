"""initial schema

Revision ID: c712bae9b154
Revises:
Create Date: 2026-04-24 20:38:16.022443

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def _user_role() -> postgresql.ENUM:
    return postgresql.ENUM(
        "user", "analyst", "admin", name="user_role", create_type=False
    )


def _parse_status() -> postgresql.ENUM:
    return postgresql.ENUM(
        "pending", "running", "completed", "failed", name="parse_status", create_type=False
    )


def _sentiment_label() -> postgresql.ENUM:
    return postgresql.ENUM(
        "positive", "negative", "neutral", name="sentiment_label", create_type=False
    )


revision: str = "c712bae9b154"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE TYPE user_role AS ENUM ('user', 'analyst', 'admin')")
    op.execute("CREATE TYPE parse_status AS ENUM ('pending', 'running', 'completed', 'failed')")
    op.execute("CREATE TYPE sentiment_label AS ENUM ('positive', 'negative', 'neutral')")

    op.create_table(
        "marketplaces",
        sa.Column("marketplace_id", sa.SmallInteger(), nullable=False),
        sa.Column("slug", sa.String(length=50), nullable=False),
        sa.Column("display_name", sa.String(length=100), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("marketplace_id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_table(
        "users",
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "role",
            _user_role(),
            server_default="user",
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("user_id"),
        sa.UniqueConstraint("email"),
    )
    op.create_table(
        "products",
        sa.Column("product_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("product_id"),
    )
    op.create_table(
        "role_change_audit",
        sa.Column("audit_id", sa.BigInteger(), nullable=False),
        sa.Column("target_user_id", sa.BigInteger(), nullable=False),
        sa.Column("changed_by_id", sa.BigInteger(), nullable=False),
        sa.Column("old_role", _user_role(), nullable=False),
        sa.Column("new_role", _user_role(), nullable=False),
        sa.Column("changed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["changed_by_id"], ["users.user_id"]),
        sa.ForeignKeyConstraint(["target_user_id"], ["users.user_id"]),
        sa.PrimaryKeyConstraint("audit_id"),
    )
    op.create_table(
        "analysis_result",
        sa.Column("analysis_id", sa.BigInteger(), nullable=False),
        sa.Column("product_id", sa.BigInteger(), nullable=False),
        sa.Column("marketplace_id", sa.SmallInteger(), nullable=False),
        sa.Column("total_reviews", sa.Integer(), nullable=False),
        sa.Column("positive_count", sa.Integer(), nullable=False),
        sa.Column("negative_count", sa.Integer(), nullable=False),
        sa.Column("neutral_count", sa.Integer(), nullable=False),
        sa.Column("avg_sentiment", sa.Float(), nullable=False),
        sa.Column("calculated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["marketplace_id"], ["marketplaces.marketplace_id"]),
        sa.ForeignKeyConstraint(["product_id"], ["products.product_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("analysis_id"),
    )
    op.create_index(
        "idx_analysis_product_marketplace_calculated",
        "analysis_result",
        ["product_id", "marketplace_id", sa.literal_column("calculated_at DESC")],
        unique=False,
    )
    op.create_table(
        "product_urls",
        sa.Column("url_id", sa.BigInteger(), nullable=False),
        sa.Column("product_id", sa.BigInteger(), nullable=False),
        sa.Column("marketplace_id", sa.SmallInteger(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("last_price", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("last_image_url", sa.Text(), nullable=True),
        sa.Column("last_parsed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["marketplace_id"], ["marketplaces.marketplace_id"]),
        sa.ForeignKeyConstraint(["product_id"], ["products.product_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("url_id"),
        sa.UniqueConstraint("product_id", "url", name="uq_product_url"),
    )
    op.create_table(
        "parse_runs",
        sa.Column("run_id", sa.BigInteger(), nullable=False),
        sa.Column("url_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "status",
            _parse_status(),
            server_default="pending",
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("reviews_collected", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["url_id"], ["product_urls.url_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("run_id"),
    )
    op.create_table(
        "reviews",
        sa.Column("review_id", sa.BigInteger(), nullable=False),
        sa.Column("url_id", sa.BigInteger(), nullable=False),
        sa.Column("run_id", sa.BigInteger(), nullable=True),
        sa.Column("external_id", sa.String(length=255), nullable=True),
        sa.Column("review_text", sa.Text(), nullable=False),
        sa.Column("rating", sa.SmallInteger(), nullable=True),
        sa.Column("author", sa.String(length=255), nullable=True),
        sa.Column("date", sa.Date(), nullable=True),
        sa.Column("sentiment_score", sa.Float(), nullable=True),
        sa.Column("sentiment_label", _sentiment_label(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("rating IS NULL OR rating BETWEEN 1 AND 5", name="ck_review_rating_range"),
        sa.ForeignKeyConstraint(["run_id"], ["parse_runs.run_id"]),
        sa.ForeignKeyConstraint(["url_id"], ["product_urls.url_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("review_id"),
    )
    op.create_index(
        "uq_review_external_id",
        "reviews",
        ["url_id", "external_id"],
        unique=True,
        postgresql_where=sa.text("external_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_review_external_id",
        table_name="reviews",
        postgresql_where=sa.text("external_id IS NOT NULL"),
    )
    op.drop_table("reviews")
    op.drop_table("parse_runs")
    op.drop_table("product_urls")
    op.drop_index("idx_analysis_product_marketplace_calculated", table_name="analysis_result")
    op.drop_table("analysis_result")
    op.drop_table("role_change_audit")
    op.drop_table("products")
    op.drop_table("users")
    op.drop_table("marketplaces")

    op.execute("DROP TYPE sentiment_label")
    op.execute("DROP TYPE parse_status")
    op.execute("DROP TYPE user_role")
