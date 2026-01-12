"""auth events

Revision ID: 3c9f2e1a2d4b
Revises: 1f6f8b3d2c01
Create Date: 2024-03-02 00:00:01.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "3c9f2e1a2d4b"
down_revision = "1f6f8b3d2c01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "auth_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("ip_address", sa.String(), nullable=True),
        sa.Column("service", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_auth_events_id"), "auth_events", ["id"], unique=False)
    op.create_index(op.f("ix_auth_events_user_id"), "auth_events", ["user_id"], unique=False)
    op.create_index(op.f("ix_auth_events_created_at"), "auth_events", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_auth_events_created_at"), table_name="auth_events")
    op.drop_index(op.f("ix_auth_events_user_id"), table_name="auth_events")
    op.drop_index(op.f("ix_auth_events_id"), table_name="auth_events")
    op.drop_table("auth_events")
