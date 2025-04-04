"""rename_uploader_to_creator

Revision ID: 8c1d42e2a5d2
Revises: 4276702d8506
Create Date: 2025-04-04 14:04:34.576868

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8c1d42e2a5d2'
down_revision: Union[str, None] = '4276702d8506'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column("memes", "uploader_telegram_id", new_column_name="creator_telegram_id")
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column("memes", "creator_telegram_id", new_column_name="uploader_telegram_id")
    # ### end Alembic commands ###
