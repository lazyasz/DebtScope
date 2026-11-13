"""Add file_category to source_files and create pending_actions table

Revision ID: e3f4a5b6c7d8
Revises: d2e3f4a5b6c7
Create Date: 2026-11-14 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = 'e3f4a5b6c7d8'
down_revision = 'd2e3f4a5b6c7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    
    # 1. Add file_category column to source_files if not present
    cols = [c['name'] for c in insp.get_columns('source_files')]
    if 'file_category' not in cols:
        with op.batch_alter_table('source_files', schema=None) as batch_op:
            batch_op.add_column(sa.Column('file_category', sa.String(length=50), server_default='source', nullable=True))
            batch_op.create_index('ix_source_files_file_category', ['file_category'])

    # 2. Create pending_actions table if not present
    if 'pending_actions' not in insp.get_table_names():
        op.create_table(
            'pending_actions',
            sa.Column('id', sa.String(length=100), primary_key=True),
            sa.Column('workspace_id', sa.String(length=100), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
            sa.Column('user_id', sa.String(length=100), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            sa.Column('tool_name', sa.String(length=50), nullable=False),
            sa.Column('arguments_json', sa.Text(), nullable=False),
            sa.Column('arguments_hash', sa.String(length=64), nullable=False),
            sa.Column('status', sa.String(length=20), server_default='PENDING'),
            sa.Column('result_json', sa.Text(), nullable=True),
            sa.Column('expires_at', sa.DateTime(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('executed_at', sa.DateTime(), nullable=True),
        )
        with op.batch_alter_table('pending_actions', schema=None) as batch_op:
            batch_op.create_index('ix_pending_actions_id', ['id'])
            batch_op.create_index('ix_pending_actions_status', ['status'])
            batch_op.create_index('ix_pending_actions_workspace_id', ['workspace_id'])
            batch_op.create_index('ix_pending_actions_user_id', ['user_id'])


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if 'pending_actions' in insp.get_table_names():
        op.drop_table('pending_actions')
    if 'source_files' in insp.get_table_names():
        cols = [c['name'] for c in insp.get_columns('source_files')]
        if 'file_category' in cols:
            with op.batch_alter_table('source_files', schema=None) as batch_op:
                try:
                    batch_op.drop_index('ix_source_files_file_category')
                except Exception:
                    pass
                batch_op.drop_column('file_category')
