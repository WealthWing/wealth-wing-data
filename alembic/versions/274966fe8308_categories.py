"""categories

Revision ID: 274966fe8308
Revises: 2c6b736a55fe
Create Date: 2024-11-02 21:42:05.498207

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID 
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import text


# revision identifiers, used by Alembic.
revision: str = '274966fe8308'
down_revision: Union[str, None] = '2c6b736a55fe'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create the ENUM type in the database
    category_type_enum = postgresql.ENUM(
        'Subscriptions and Memberships',
        'Variable Expenses',
        'Savings and Investments',
        'Debt Payments',
        'Fixed Expenses',
        'Discretionary Expenses',
        'Miscellaneous',
        name='category_type',
    )
    conn = op.get_bind()
    result = conn.execute(text("SELECT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'category_type');"))
    
    if not result:
        # Create the ENUM type if it doesn't exist
        category_type_enum = postgresql.ENUM(
            'Subscriptions and Memberships',
            'Variable Expenses',
            'Savings and Investments',
            'Debt Payments',
            'Fixed Expenses',
            'Discretionary Expenses',
            'Miscellaneous',
            name='category_type',
        )
        category_type_enum.create(conn)
    else:
        # Reflect the existing ENUM type
        category_type_enum = sa.Enum(name='category_type')

    # Create the 'categories' table
    op.create_table(
        'categories',
        sa.Column('uuid', UUID(as_uuid=True), primary_key=True, default=sa.text('uuid_generate_v4()'), index=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('type', sa.Enum('Subscriptions and Memberships',
                                  'Variable Expenses',
                                  'Savings and Investments',
                                  'Debt Payments',
                                  'Fixed Expenses',
                                  'Discretionary Expenses',
                                  'Miscellaneous',
                                  name='category_type'),
                  nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False)
    )
   

def downgrade() -> None:
    op.drop_table('categories')

    category_type_enum = postgresql.ENUM(
        'Subscriptions and Memberships',
        'Variable Expenses',
        'Savings and Investments',
        'Debt Payments',
        'Fixed Expenses',
        'Discretionary Expenses',
        'Miscellaneous',
        name='category_type',
    )
    category_type_enum.drop(op.get_bind())

