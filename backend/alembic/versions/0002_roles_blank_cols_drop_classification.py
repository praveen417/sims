"""drop classification, allow blanks / long text, add roles

Revision ID: 0002
Revises: 0001
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

TEXT_COLS = ["application", "application_owner", "base_machine", "base_machine_ip", "fqdn",
             "processor_name", "mac_address", "product_name", "server_role", "location"]


def upgrade():
    op.drop_column("inventory", "classification")
    op.alter_column("inventory", "opco", existing_type=sa.String(100), nullable=True)

    # btree indexes cannot hold very long text; trigram indexes cover these searches
    op.execute("DROP INDEX IF EXISTS ix_inventory_application")
    op.execute("DROP INDEX IF EXISTS ix_inventory_location")
    for c in TEXT_COLS:
        op.alter_column("inventory", c, type_=sa.Text(), existing_nullable=True)
    op.execute("CREATE INDEX IF NOT EXISTS ix_inventory_location_trgm ON inventory USING gin (location gin_trgm_ops)")

    op.drop_constraint("ck_users_role", "users", type_="check")
    op.create_check_constraint(
        "ck_users_role", "users",
        "role IN ('admin','manager','developer','requester','readonly')")


def downgrade():
    pass
