"""add_priority_dimension_coverage_columns

Revision ID: b6fbbde60b29
Revises: 810a44b47bf6
Create Date: 2026-11-13 02:29:38.285478

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b6fbbde60b29'
down_revision: Union[str, Sequence[str], None] = '810a44b47bf6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add dimension coverage columns to priority_scores table."""
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = [c['name'] for c in insp.get_columns('priority_scores')]
    with op.batch_alter_table('priority_scores', schema=None) as batch_op:
        if 'scored_dimensions_count' not in cols:
            batch_op.add_column(sa.Column('scored_dimensions_count', sa.Integer(), nullable=True, server_default='5'))
        if 'dimension_coverage' not in cols:
            batch_op.add_column(sa.Column('dimension_coverage', sa.String(length=50), nullable=True, server_default='5 of 5 dimensions'))
        if 'missing_dimensions_json' not in cols:
            batch_op.add_column(sa.Column('missing_dimensions_json', sa.Text(), nullable=True, server_default='[]'))


def downgrade() -> None:
    """Drop dimension coverage columns."""
    with op.batch_alter_table('priority_scores', schema=None) as batch_op:
        batch_op.drop_column('missing_dimensions_json')
        batch_op.drop_column('dimension_coverage')
        batch_op.drop_column('scored_dimensions_count')
