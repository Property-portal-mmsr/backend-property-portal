"""change_month_to_string_in_employee_monthly_targets

Revision ID: f65cae8253be
Revises: 66d57ff17879
Create Date: 2026-08-25 11:26:42.407876

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = 'f65cae8253be'
down_revision: Union[str, Sequence[str], None] = '66d57ff17879'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Expand month column to VARCHAR(50) to store full month names like 'August'."""
    op.alter_column(
        'employee_monthly_targets', 'month',
        existing_type=mysql.VARCHAR(length=20),
        type_=sa.String(length=50),
        nullable=False,
    )


def downgrade() -> None:
    """Revert month column back to VARCHAR(20)."""
    op.alter_column(
        'employee_monthly_targets', 'month',
        existing_type=sa.String(length=50),
        type_=mysql.VARCHAR(length=20),
        nullable=True,
    )
