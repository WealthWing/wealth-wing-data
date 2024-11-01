"""Create subsrciptions

Revision ID: 2c6b736a55fe
Revises: e869de6adfc9
Create Date: 2024-10-16 21:10:11.656551

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import func
import uuid
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = '2c6b736a55fe'
down_revision: Union[str, None] = 'e869de6adfc9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'subscriptions',
        sa.Column('uuid', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('user_table.uuid'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('cost', sa.Numeric(10, 2)),
        sa.Column('currency', sa.String(10)),
        sa.Column('billing_frequency', sa.String(50)),
        sa.Column('start_date', sa.DateTime(timezone=True)),
        sa.Column('end_date', sa.DateTime(timezone=True)),
        sa.Column('next_billing_date', sa.DateTime(timezone=True)),
        sa.Column('auto_renew', sa.Boolean(), nullable=False, default=True),
        sa.Column('status', sa.String(50)),
        sa.Column('payment_method', sa.String(50)),
        sa.Column('notes', sa.Text()),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=func.now(), onupdate=func.now()),
        sa.Column('cancellation_date', sa.DateTime(timezone=True)),
        sa.Column('trial_period', sa.Boolean(), nullable=False, default=False),
        sa.Column('trial_end_date', sa.DateTime(timezone=True)),
        sa.Column('total_amount_spent', sa.Numeric(15, 2)),
        sa.Column('contract_length', sa.String(50)),
        sa.Column('contract_end_date', sa.DateTime(timezone=True)),
        sa.Column('usage_limits', sa.String(255)),
        sa.Column('support_contact', sa.String(255)),
        sa.Column('website_url', sa.String(255)),
        sa.PrimaryKeyConstraint('uuid')
    )


def downgrade() -> None:
    op.drop_table('subscriptions')
