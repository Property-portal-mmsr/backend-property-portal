"""Add sales_kit to properties

Revision ID: 98fe9340efb1
Revises: 
Create Date: 2026-08-20 12:20:30.023809

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '98fe9340efb1'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c['name'] for c in inspector.get_columns('properties')]
    if 'sales_kit' not in columns:
        op.add_column('properties', sa.Column('sales_kit', sa.JSON(), nullable=True))

def downgrade() -> None:
    """Downgrade schema."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c['name'] for c in inspector.get_columns('properties')]
    if 'sales_kit' in columns:
        op.drop_column('properties', 'sales_kit')
