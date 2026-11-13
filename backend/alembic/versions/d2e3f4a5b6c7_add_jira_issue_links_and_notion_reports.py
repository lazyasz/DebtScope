"""Add jira_issue_links and notion_reports tables

Revision ID: d2e3f4a5b6c7
Revises: c1a2d3e4f5a6
Create Date: 2026-11-13 20:25:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = 'd2e3f4a5b6c7'
down_revision = 'c1a2d3e4f5a6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'jira_issue_links',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('workspace_id', sa.String(length=100), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('file_id', sa.Integer(), sa.ForeignKey('source_files.id', ondelete='CASCADE'), nullable=True),
        sa.Column('commit_hash', sa.String(length=100), nullable=True),
        sa.Column('issue_key', sa.String(length=50), nullable=False),
        sa.Column('summary', sa.String(length=255), nullable=True),
        sa.Column('issue_type', sa.String(length=50), server_default='Task'),
        sa.Column('priority', sa.String(length=50), server_default='Medium'),
        sa.Column('status', sa.String(length=50), server_default='Open'),
        sa.Column('is_bug', sa.Boolean(), server_default='0'),
        sa.Column('sprint_id', sa.String(length=100), nullable=True),
        sa.Column('sprint_state', sa.String(length=50), nullable=True),
        sa.Column('fix_version', sa.String(length=100), nullable=True),
        sa.Column('fix_version_date', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_jira_issue_links_id', 'jira_issue_links', ['id'])
    op.create_index('ix_jira_issue_links_workspace_id', 'jira_issue_links', ['workspace_id'])
    op.create_index('ix_jira_issue_links_file_id', 'jira_issue_links', ['file_id'])
    op.create_index('ix_jira_issue_links_issue_key', 'jira_issue_links', ['issue_key'])

    op.create_table(
        'notion_reports',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('workspace_id', sa.String(length=100), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('notion_page_id', sa.String(length=100), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('report_type', sa.String(length=50), server_default='EXECUTIVE_SUMMARY'),
        sa.Column('total_debt_hours', sa.Float(), server_default='0.0'),
        sa.Column('top_debt_items_count', sa.Integer(), server_default='0'),
        sa.Column('export_status', sa.String(length=50), server_default='COMPLETED'),
        sa.Column('report_url', sa.String(length=500), nullable=True),
        sa.Column('exported_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_notion_reports_id', 'notion_reports', ['id'])
    op.create_index('ix_notion_reports_workspace_id', 'notion_reports', ['workspace_id'])


def downgrade() -> None:
    op.drop_table('notion_reports')
    op.drop_table('jira_issue_links')
