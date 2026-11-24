"""initial schema

Revision ID: 0001
Revises:
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

TS = sa.DateTime(timezone=True)


def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("username", sa.String(100), nullable=False),
        sa.Column("full_name", sa.String(200), nullable=False),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="readonly"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("failed_attempts", sa.Integer, nullable=False, server_default="0"),
        sa.Column("locked_until", TS),
        sa.Column("last_login", TS),
        sa.Column("mfa_enabled", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("mfa_secret", sa.String(64)),
        sa.Column("created_date", TS, server_default=sa.func.now()),
        sa.CheckConstraint("role IN ('admin','readonly')", name="ck_users_role"),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    op.create_table(
        "opcos",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("country", sa.String(100)),
        sa.Column("active", sa.Boolean, nullable=False, server_default=sa.true()),
    )

    op.create_table(
        "inventory",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("opco", sa.String(100), nullable=False),
        sa.Column("domain", sa.String(100)),
        sa.Column("asset_type", sa.String(100)),
        sa.Column("hostname", sa.String(255), nullable=False, unique=True),
        sa.Column("status", sa.String(50)),
        sa.Column("ip_address", sa.String(45), unique=True),
        sa.Column("backup_status", sa.String(50)),
        sa.Column("ilo_ip", sa.String(45)),
        sa.Column("serial_number", sa.String(100), unique=True),
        sa.Column("application", sa.String(255)),
        sa.Column("application_owner", sa.String(255)),
        sa.Column("environment", sa.String(20)),
        sa.Column("bia_class", sa.String(50)),
        sa.Column("classification", sa.String(100)),
        sa.Column("physical_virtual", sa.String(20)),
        sa.Column("base_machine", sa.String(255)),
        sa.Column("base_machine_ip", sa.String(45)),
        sa.Column("virtualization_platform", sa.String(100)),
        sa.Column("operating_system", sa.String(150)),
        sa.Column("memory_gb", sa.Integer),
        sa.Column("fqdn", sa.String(255)),
        sa.Column("processor_count", sa.Integer),
        sa.Column("processor_name", sa.String(150)),
        sa.Column("mac_address", sa.String(50)),
        sa.Column("product_name", sa.String(200)),
        sa.Column("hardware_vendor", sa.String(100)),
        sa.Column("support_type", sa.String(30)),
        sa.Column("server_role", sa.String(150)),
        sa.Column("location", sa.String(150)),
        sa.Column("ito_non_ito", sa.String(20)),
        sa.Column("end_of_life", sa.Date),
        sa.Column("end_of_support", sa.Date),
        sa.Column("oracle_support", sa.String(50)),
        sa.Column("db_version", sa.String(50)),
        sa.Column("remarks", sa.Text),
        sa.Column("created_date", TS, server_default=sa.func.now()),
        sa.Column("updated_date", TS, server_default=sa.func.now()),
    )
    for col in ["opco", "domain", "backup_status", "application", "environment",
                "physical_virtual", "operating_system", "location", "end_of_life", "end_of_support"]:
        op.create_index(f"ix_inventory_{col}", "inventory", [col])
    # trigram indexes make wildcard / ILIKE '%text%' search fast at 100k+ rows
    for col in ["hostname", "ip_address", "serial_number", "application", "application_owner"]:
        op.execute(f"CREATE INDEX ix_inventory_{col}_trgm ON inventory USING gin ({col} gin_trgm_ops)")

    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("username", sa.String(100)),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("ip_address", sa.String(45)),
        sa.Column("entity_id", sa.Integer),
        sa.Column("old_value", postgresql.JSONB),
        sa.Column("new_value", postgresql.JSONB),
        sa.Column("timestamp", TS, server_default=sa.func.now()),
    )
    op.create_index("ix_audit_log_username", "audit_log", ["username"])
    op.create_index("ix_audit_log_action", "audit_log", ["action"])
    op.create_index("ix_audit_log_timestamp", "audit_log", ["timestamp"])

    op.create_table(
        "saved_filters",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("filter_json", postgresql.JSONB, nullable=False),
        sa.Column("created_date", TS, server_default=sa.func.now()),
    )
    op.create_index("ix_saved_filters_user_id", "saved_filters", ["user_id"])


def downgrade():
    for t in ["saved_filters", "audit_log", "inventory", "opcos", "users"]:
        op.drop_table(t)
