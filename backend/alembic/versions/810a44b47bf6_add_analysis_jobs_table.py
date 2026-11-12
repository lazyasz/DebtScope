"""add_analysis_jobs_table

Revision ID: 810a44b47bf6
Revises: 2cee858c7422
Create Date: 2026-11-13 02:15:05.285478

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '810a44b47bf6'
down_revision: Union[str, Sequence[str], None] = '2cee858c7422'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema — create analysis_jobs table."""
    op.create_table(
        'analysis_jobs',
        sa.Column('id', sa.String(length=100), nullable=False),
        sa.Column('workspace_id', sa.String(length=100), nullable=False, server_default='ws_demo'),
        sa.Column('repository_id', sa.Integer(), nullable=True),
        sa.Column('repo_url', sa.String(length=255), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=True, server_default='QUEUED'),
        sa.Column('stage', sa.String(length=100), nullable=True, server_default='Queued for analysis'),
        sa.Column('progress_pct', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('result_summary', sa.Text(), nullable=True),
        sa.Column('files_analyzed', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['repository_id'], ['repositories.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('analysis_jobs', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_analysis_jobs_id'), ['id'], unique=False)
        batch_op.create_index(batch_op.f('ix_analysis_jobs_repository_id'), ['repository_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_analysis_jobs_status'), ['status'], unique=False)
        batch_op.create_index(batch_op.f('ix_analysis_jobs_workspace_id'), ['workspace_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema — drop analysis_jobs table."""
    with op.batch_alter_table('analysis_jobs', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_analysis_jobs_workspace_id'))
        batch_op.drop_index(batch_op.f('ix_analysis_jobs_status'))
        batch_op.drop_index(batch_op.f('ix_analysis_jobs_repository_id'))
        batch_op.drop_index(batch_op.f('ix_analysis_jobs_id'))

    op.drop_table('analysis_jobs')
