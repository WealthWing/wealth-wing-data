"""Create user table

Revision ID: e869de6adfc9
Revises: 05dc6a7aa715
Create Date: 2024-10-16 17:24:33.470199

"""

from typing import Sequence, Union
from sqlalchemy.dialects.postgresql import UUID, ENUM
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e869de6adfc9"
down_revision: Union[str, None] = "05dc6a7aa715"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    user_role_enum = ENUM(
        "Admin",
        "User",
        "User_Manager",
        "User_Admin",
        "User_Viewer",
        "User_Editor",
        name="user_role",
        create_type=False,  # This tells Alembic not to create the type if it exists
    )
    op.create_table(
        "user_table",
        sa.Column("uuid", UUID(as_uuid=True), primary_key=True, index=True),
        sa.Column("email", sa.String, nullable=False),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("last_name", sa.String, nullable=False),
        sa.Column("role", user_role_enum, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=True),
    )


def downgrade() -> None:
    op.drop_table("user_table")
