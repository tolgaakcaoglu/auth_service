"""add phone to users

Revision ID: 9c2f1a6b7d01
Revises: 4b7a1f9c8e21
Create Date: 2025-01-01 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "9c2f1a6b7d01"
down_revision = "4b7a1f9c8e21"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("phone", sa.String(), nullable=True))
    op.create_unique_constraint("uq_users_phone", "users", ["phone"])
    op.create_index(op.f("ix_users_phone"), "users", ["phone"], unique=False)
    op.alter_column("users", "email", existing_type=sa.String(), nullable=True)


def downgrade() -> None:
    op.alter_column("users", "email", existing_type=sa.String(), nullable=False)
    op.drop_index(op.f("ix_users_phone"), table_name="users")
    op.drop_constraint("uq_users_phone", "users", type_="unique")
    op.drop_column("users", "phone")
