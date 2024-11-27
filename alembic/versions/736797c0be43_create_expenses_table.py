"""Create expenses table

Revision ID: 736797c0be43
Revises: 6d1e76151d7a
Create Date: 2024-11-14 10:28:36.343857

"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy.dialects.postgresql import UUID
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "736797c0be43"
down_revision: Union[str, None] = "6d1e76151d7a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "expenses",
        sa.Column(
            "uuid",
            UUID(as_uuid=True),
            primary_key=True,
            default=sa.text("uuid_generate_v4()"),
            index=True,
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("user_table.uuid"),
            nullable=False,
        ),
        sa.Column(
            "category_id",
            UUID(as_uuid=True),
            sa.ForeignKey("categories.uuid"),
            nullable=False,
        ),
        sa.Column("amount", sa.BigInteger, nullable=False),
        sa.Column("currency", sa.String(10), default="USD"),
        sa.Column("exchange_rate", sa.Float),
        sa.Column("date", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("title", sa.String, nullable=False),          
        sa.Column("merchant", sa.String, nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("expenses")


