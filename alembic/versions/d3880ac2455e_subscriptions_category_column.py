"""subscriptions category column

Revision ID: d3880ac2455e
Revises: 274966fe8308
Create Date: 2024-11-11 08:57:17.688944

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd3880ac2455e'
down_revision: Union[str, None] = '274966fe8308'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('subscriptions', sa.Column('category_id', sa.String(50), nullable=True))
    op.drop_column('categories', 'name')


def downgrade() -> None:
    op.drop_column('subscriptions', 'category_id')
    op.add_column('categories', sa.Column('name', sa.String(255), nullable=False))
