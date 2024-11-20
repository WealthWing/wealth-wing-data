"""Recreate missing migration

Revision ID: dbc238020a3b
Revises: 4fb2b42b1c0c
Create Date: 2024-11-20 11:22:32.951128

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '63abf71bf9d9'
down_revision = '4fb2b42b1c0c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
