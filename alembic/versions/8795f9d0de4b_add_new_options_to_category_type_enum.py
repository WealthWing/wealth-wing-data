"""Add new options to category_type enum

Revision ID: 8795f9d0de4b
Revises: d3880ac2455e
Create Date: 2024-11-11 14:56:18.786491

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import text


# revision identifiers, used by Alembic.
revision: str = "8795f9d0de4b"
down_revision: Union[str, None] = "d3880ac2455e"
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
    for value in new_enum_values:
        conn.execute(
            text(f"ALTER TYPE category_type ADD VALUE IF NOT EXISTS '{value}'")
        )
        conn.commit()  
   

    for old_value, new_value in zip(old_enum_values, new_enum_values):
        conn.execute(
            text(
                f"UPDATE categories SET type = '{new_value}' WHERE type = '{old_value}'"
            )
        )


def downgrade():

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
