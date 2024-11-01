"""Create test_table

Revision ID: 05dc6a7aa715
Revises: 
Create Date: 2024-10-10 14:57:22.295986

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '05dc6a7aa715'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'test_table',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('name', sa.String, nullable=False)
    )


def downgrade() -> None:
    op.drop_table('test_table')
