"""add service verification method

Revision ID: 5d3c2b1a0f9e
Revises: 9c2f1a6b7d01
Create Date: 2024-05-05 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "5d3c2b1a0f9e"
down_revision = "9c2f1a6b7d01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "services",
        sa.Column("verification_method", sa.String(), nullable=False, server_default="link"),
    )


def downgrade() -> None:
    op.drop_column("services", "verification_method")
