"""name column categories

Revision ID: 6d1e76151d7a
Revises: 8795f9d0de4b
Create Date: 2024-11-12 08:36:52.287688

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6d1e76151d7a'
down_revision: Union[str, None] = '8795f9d0de4b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('categories', sa.Column('title', sa.String(255), nullable=False))
     

def downgrade() -> None:
    op.drop_column('categories', 'title', nullable=False)
