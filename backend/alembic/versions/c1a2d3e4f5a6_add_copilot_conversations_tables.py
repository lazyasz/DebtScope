"""Add copilot_conversations and copilot_messages tables

Revision ID: c1a2d3e4f5a6
Revises: b6fbbde60b29
Create Date: 2026-11-13 02:49:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = 'c1a2d3e4f5a6'
down_revision = 'b6fbbde60b29'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'copilot_conversations',
        sa.Column('id', sa.String(length=100), primary_key=True),
        sa.Column('workspace_id', sa.String(length=100), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.String(length=100), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('repository_id', sa.Integer(), sa.ForeignKey('repositories.id', ondelete='CASCADE'), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )
    try:
        op.create_index('ix_copilot_conversations_id', 'copilot_conversations', ['id'])
        op.create_index('ix_copilot_conversations_workspace_id', 'copilot_conversations', ['workspace_id'])
        op.create_index('ix_copilot_conversations_user_id', 'copilot_conversations', ['user_id'])
        op.create_index('ix_copilot_conversations_repository_id', 'copilot_conversations', ['repository_id'])
    except Exception:
        pass

    op.create_table(
        'copilot_messages',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('conversation_id', sa.String(length=100), sa.ForeignKey('copilot_conversations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role', sa.String(length=30), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('citations_json', sa.Text(), nullable=True),
        sa.Column('tool_calls_json', sa.Text(), nullable=True),
        sa.Column('refactor_diff', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )
    try:
        op.create_index('ix_copilot_messages_conversation_id', 'copilot_messages', ['conversation_id'])
    except Exception:
        pass


def downgrade() -> None:
    op.drop_table('copilot_messages')
    op.drop_table('copilot_conversations')
