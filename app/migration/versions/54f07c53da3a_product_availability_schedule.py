"""Add product availability scheduling fields.

Revision ID: 54f07c53da3a
Revises: f0195aadf351
Create Date: 2026-09-13 17:37:19.271783

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "54f07c53da3a"
down_revision: Union[str, None] = "f0195aadf351"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add retry scheduling state to products."""
    op.add_column("products", sa.Column("next_check_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "products",
        sa.Column("unavailable_attempts", sa.Integer(), server_default=sa.text("'0'"), nullable=False),
    )


def downgrade() -> None:
    """Remove retry scheduling state from products."""
    op.drop_column("products", "unavailable_attempts")
    op.drop_column("products", "next_check_at")
