"""change requests can also add a new server

Revision ID: 0004
Revises: 0003
"""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("change_requests", sa.Column("request_type", sa.String(10), nullable=False, server_default="update"))
    op.alter_column("change_requests", "asset_id", existing_type=sa.Integer, nullable=True)


def downgrade():
    pass
