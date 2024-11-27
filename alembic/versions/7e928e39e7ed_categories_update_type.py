"""categories update type

Revision ID: 7e928e39e7ed
Revises: 63abf71bf9d9
Create Date: 2024-11-20 13:58:24.416977

"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy.sql import text


# revision identifiers, used by Alembic.
revision: str = '7e928e39e7ed'
down_revision: Union[str, None] = '63abf71bf9d9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    new_enum_values = [
        "SUBSCRIPTIONS_AND_MEMBERSHIPS",
        "VARIABLE_EXPENSES",
        "SAVINGS_AND_INVESTMENTS",
        "DEBT_PAYMENTS",
        "FIXED_EXPENSES",
        "DISCRETIONARY_EXPENSES",
        "MISCELLANEOUS",
    ]
    old_enum_values = [
        "Subscriptions and Memberships",
        "Variable Expenses",
        "Savings and Investments",
        "Debt Payments",
        "Fixed Expenses",
        "Discretionary Expenses",
        "Miscellaneous",
    ]
    conn = op.get_bind()
    
    for old_value, new_value in zip(old_enum_values, new_enum_values):
        conn.execute(
            text(
                f"UPDATE categories SET type = '{new_value}' WHERE type = '{old_value}'"
            )
        )


def downgrade() -> None:
    conn = op.get_bind()

    new_to_old_mapping = {
        "SUBSCRIPTIONS_AND_MEMBERSHIPS": "Subscriptions and Memberships",
        "VARIABLE_EXPENSES": "Variable Expenses",
        "SAVINGS_AND_INVESTMENTS": "Savings and Investments",
        "DEBT_PAYMENTS": "Debt Payments",
        "FIXED_EXPENSES": "Fixed Expenses",
        "DISCRETIONARY_EXPENSES": "Discretionary Expenses",
        "MISCELLANEOUS": "Miscellaneous",
    }

    for new_value, old_value in new_to_old_mapping.items():
        conn.execute(
            text(
                f"UPDATE categories SET type = '{old_value}' WHERE type = '{new_value}'"
            )
        )
