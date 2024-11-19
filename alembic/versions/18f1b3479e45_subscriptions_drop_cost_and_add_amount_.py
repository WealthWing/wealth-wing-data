"""subscriptions drop cost and add amount column


Revision ID: 18f1b3479e45
Revises: 736797c0be43
Create Date: 2024-11-19 14:13:03.967373

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '18f1b3479e45'
down_revision: Union[str, None] = '736797c0be43'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column('subscriptions', 'cost')
    
    op.add_column('subscriptions', sa.Column('amount', sa.BigInteger, nullable=True))
    op.execute('UPDATE subscriptions SET amount = 0')
    op.alter_column('subscriptions', 'amount', nullable=False)


def downgrade() -> None:
    op.drop_column('subscriptions', 'amount')
    op.add_column('subscriptions', sa.Column('cost', sa.Numeric(10, 2), nullable=True))
    op.execute('UPDATE subscriptions SET cost = 0')
