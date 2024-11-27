"""categories table add title

Revision ID: 4fb2b42b1c0c
Revises: 18f1b3479e45
Create Date: 2024-11-19 20:16:16.292240

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4fb2b42b1c0c'
down_revision: Union[str, None] = '18f1b3479e45'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('categories', sa.Column('title', sa.String(20), nullable=True))
    op.execute("UPDATE categories SET title = 'change'")
    op.alter_column('categories', 'amount', nullable=False)


def downgrade() -> None:
    op.drop_column('categories', 'title', nullable=False)
