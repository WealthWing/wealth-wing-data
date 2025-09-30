"""seed_categories

Revision ID: 5dfd9212b108
Revises: ea157a18309c
Create Date: 2025-09-30 09:42:28.959433

"""
from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa
import datetime
from sqlalchemy.dialects.postgresql import UUID as PGUUID

# revision identifiers, used by Alembic.
revision: str = '5dfd9212b108'
down_revision: Union[str, None] = 'ea157a18309c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SYSTEM = [
    # expense
    ("rent_mortgage", "Rent / Mortgage", "expense"),
    ("utilities", "Utilities", "expense"),
    ("groceries", "Groceries", "expense"),
    ("restaurants", "Restaurants", "expense"),
    ("shopping", "Shopping", "expense"),
    ("transportation", "Transportation", "expense"),
    ("health_medical", "Health & Medical", "expense"),
    ("insurance", "Insurance", "expense"),
    ("subscriptions", "Subscriptions", "expense"),
    ("entertainment", "Entertainment", "expense"),
    ("travel", "Travel", "expense"),
    ("household_supplies", "Household Supplies", "expense"),
    ("fees", "Fees & Interest", "expense"),
    ("misc", "Misc", "expense"),
    # income
    ("salary_wages", "Salary & Wages", "income"),
    ("other_income", "Other Income", "income"),
    # transfer
    ("transfer_internal", "Internal Transfer", "transfer"),
    ("credit_card_payment", "Credit Card Payment", "transfer"),
    ("atm_withdrawal", "Cash / ATM", "transfer"),
]


def upgrade() -> None:
    category_table = sa.table(
        "categories",
        sa.column("uuid", PGUUID(as_uuid=True)),
        sa.column("organization_id", PGUUID(as_uuid=True)),
        sa.column("title", sa.String),
        sa.column("type", sa.String),
        sa.column("slug", sa.String),
        sa.column("description", sa.Text),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    now = datetime.datetime.now(datetime.timezone.utc)
    rows = []
    for key, title, ctype in SYSTEM:
        rows.append(
            {
                "uuid": uuid.uuid4(),
                "organization_id": None,
                "title": title,
                "type": ctype,
                "slug": key,
                "description": None,
                "created_at": now,
                "updated_at": now,
            }
        )

    op.bulk_insert(category_table, rows)    


def downgrade() -> None:
    conn = op.get_bind()
    slugs = [k for k, _, _ in SYSTEM]
    # Delete seeded rows by slug; adjust if you use a different unique key
    conn.execute(sa.text("DELETE FROM categories WHERE slug = ANY(:slugs)"), {"slugs": slugs})
