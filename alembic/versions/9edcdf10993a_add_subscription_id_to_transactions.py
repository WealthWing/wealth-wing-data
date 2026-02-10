"""add_subscription_id_to_transactions

Revision ID: 9edcdf10993a
Revises: 15f9c25bf77e
Create Date: 2026-02-10 14:18:48.824439

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9edcdf10993a'
down_revision: Union[str, None] = '15f9c25bf77e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'transactions', sa.Column('subscription_id', sa.UUID(), nullable=True)
    )
    op.create_foreign_key(
        'fk_transactions_subscription_id',
        'transactions',
        'subscriptions',
        ['subscription_id'],
        ['uuid'],
        ondelete='SET NULL',
    )
    op.create_index(
        'ix_transactions_subscription_id',
        'transactions',
        ['subscription_id'],
    )


def downgrade() -> None:
    op.drop_index('ix_transactions_subscription_id', table_name='transactions')
    op.drop_constraint(
        'fk_transactions_subscription_id', 'transactions', type_='foreignkey'
    )
    op.drop_column('transactions', 'subscription_id')
