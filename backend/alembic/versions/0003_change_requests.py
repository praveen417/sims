"""change requests (approval workflow)

Revision ID: 0003
Revises: 0002
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "change_requests",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("asset_id", sa.Integer, sa.ForeignKey("inventory.id", ondelete="CASCADE"), nullable=False),
        sa.Column("hostname", sa.String(255), nullable=False),
        sa.Column("requested_by", sa.String(100), nullable=False),
        sa.Column("requester_email", sa.String(255)),
        sa.Column("changes", postgresql.JSONB, nullable=False),
        sa.Column("old_values", postgresql.JSONB, nullable=False),
        sa.Column("reason", sa.Text),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("reviewed_by", sa.String(100)),
        sa.Column("review_comment", sa.Text),
        sa.Column("review_source", sa.String(20)),
        sa.Column("created_date", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("reviewed_date", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_change_requests_asset_id", "change_requests", ["asset_id"])
    op.create_index("ix_change_requests_requested_by", "change_requests", ["requested_by"])
    op.create_index("ix_change_requests_status", "change_requests", ["status"])


def downgrade():
    op.drop_table("change_requests")
