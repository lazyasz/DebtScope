"""Add last_heartbeat and timeout_seconds to analysis_jobs table

Revision ID: f4a5b6c7d8e9
Revises: e3f4a5b6c7d8
Create Date: 2026-11-14 02:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = 'f4a5b6c7d8e9'
down_revision = 'e3f4a5b6c7d8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('analysis_jobs', sa.Column('last_heartbeat', sa.DateTime(), nullable=True))
    op.add_column('analysis_jobs', sa.Column('timeout_seconds', sa.Integer(), server_default='600', nullable=True))


def downgrade() -> None:
    op.drop_column('analysis_jobs', 'timeout_seconds')
    op.drop_column('analysis_jobs', 'last_heartbeat')
