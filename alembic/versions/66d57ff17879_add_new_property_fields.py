"""Add new property fields

Revision ID: 66d57ff17879
Revises: c1e81e5b3728
Create Date: 2026-08-20 12:46:46.094253

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '66d57ff17879'
down_revision: Union[str, Sequence[str], None] = '98fe9340efb1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('properties', sa.Column('description', sa.String(length=2000), nullable=True))
    op.add_column('properties', sa.Column('city', sa.String(length=100), nullable=True))
    op.add_column('properties', sa.Column('state', sa.String(length=100), nullable=True))
    op.add_column('properties', sa.Column('pincode', sa.String(length=20), nullable=True))
    op.add_column('properties', sa.Column('deposit', sa.Numeric(10, 2), nullable=True))
    op.add_column('properties', sa.Column('unit_type', sa.String(length=50), nullable=True))
    op.add_column('properties', sa.Column('furnishing', sa.String(length=50), nullable=True))
    op.add_column('properties', sa.Column('other_specifications', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('properties', 'description')
    op.drop_column('properties', 'city')
    op.drop_column('properties', 'state')
    op.drop_column('properties', 'pincode')
    op.drop_column('properties', 'deposit')
    op.drop_column('properties', 'unit_type')
    op.drop_column('properties', 'furnishing')
    op.drop_column('properties', 'other_specifications')
