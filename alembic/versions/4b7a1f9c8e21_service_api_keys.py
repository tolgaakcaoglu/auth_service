"""service api keys

Revision ID: 4b7a1f9c8e21
Revises: 3c9f2e1a2d4b
Create Date: 2024-03-02 00:00:02.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "4b7a1f9c8e21"
down_revision = "3c9f2e1a2d4b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "services",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("domain", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_services_id"), "services", ["id"], unique=False)

    op.create_table(
        "service_api_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("service_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("key_hash", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["service_id"], ["services.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key_hash"),
    )
    op.create_index(op.f("ix_service_api_keys_id"), "service_api_keys", ["id"], unique=False)
    op.create_index(op.f("ix_service_api_keys_service_id"), "service_api_keys", ["service_id"], unique=False)
    op.create_index(op.f("ix_service_api_keys_key_hash"), "service_api_keys", ["key_hash"], unique=False)

    op.add_column(
        "auth_events",
        sa.Column("service_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_auth_events_service_id_services",
        "auth_events",
        "services",
        ["service_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.drop_column("auth_events", "service")


def downgrade() -> None:
    op.add_column("auth_events", sa.Column("service", sa.String(), nullable=True))
    op.drop_constraint("fk_auth_events_service_id_services", "auth_events", type_="foreignkey")
    op.drop_column("auth_events", "service_id")

    op.drop_index(op.f("ix_service_api_keys_key_hash"), table_name="service_api_keys")
    op.drop_index(op.f("ix_service_api_keys_service_id"), table_name="service_api_keys")
    op.drop_index(op.f("ix_service_api_keys_id"), table_name="service_api_keys")
    op.drop_table("service_api_keys")

    op.drop_index(op.f("ix_services_id"), table_name="services")
    op.drop_table("services")
