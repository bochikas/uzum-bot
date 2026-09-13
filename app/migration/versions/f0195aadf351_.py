"""empty message

Revision ID: f0195aadf351
Revises: f06c6588eba0
Create Date: 2026-09-11 09:48:23.759484

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "f0195aadf351"
down_revision: Union[str, None] = "f06c6588eba0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""


def downgrade() -> None:
    """Downgrade schema."""
