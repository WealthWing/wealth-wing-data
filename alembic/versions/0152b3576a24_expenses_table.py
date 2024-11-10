"""expenses table

Revision ID: 0152b3576a24
Revises: 274966fe8308
Create Date: 2024-11-02 22:48:19.406913

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0152b3576a24'
down_revision: Union[str, None] = '274966fe8308'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
