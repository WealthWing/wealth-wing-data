"""categories update title max length

Revision ID: aec1c232f85a
Revises: 7e928e39e7ed
Create Date: 2024-11-20 14:13:02.355920

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "aec1c232f85a"
down_revision: Union[str, None] = "7e928e39e7ed"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "categories", "title", type_=sa.String(100), existing_type=sa.String(20)
    )


def downgrade() -> None:
    op.alter_column(
        "categories", "title", type_=sa.String(20), existing_type=sa.String(100)
    )
