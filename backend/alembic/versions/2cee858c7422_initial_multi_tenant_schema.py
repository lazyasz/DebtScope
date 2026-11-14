"""initial_multi_tenant_schema

Revision ID: 2cee858c7422
Revises: 
Create Date: 2026-11-13 01:45:39.872283

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2cee858c7422'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema using frozen declarative DDL (no create_all, no inspector guards)."""
    # 1. users
    op.create_table(
        'users',
        sa.Column('id', sa.String(length=100), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=200), nullable=False),
        sa.Column('avatar_url', sa.String(length=500), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_users_email'), ['email'], unique=True)
        batch_op.create_index(batch_op.f('ix_users_id'), ['id'], unique=False)

    # 2. workspaces
    op.create_table(
        'workspaces',
        sa.Column('id', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('slug', sa.String(length=100), nullable=False),
        sa.Column('owner_id', sa.String(length=100), nullable=True),
        sa.Column('is_demo', sa.Boolean(), nullable=True, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('workspaces', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_workspaces_id'), ['id'], unique=False)
        batch_op.create_index(batch_op.f('ix_workspaces_is_demo'), ['is_demo'], unique=False)
        batch_op.create_index(batch_op.f('ix_workspaces_slug'), ['slug'], unique=True)

    # 3. workspace_memberships
    op.create_table(
        'workspace_memberships',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('workspace_id', sa.String(length=100), nullable=False),
        sa.Column('user_id', sa.String(length=100), nullable=False),
        sa.Column('role', sa.String(length=50), nullable=True, server_default='ENGINEER'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('workspace_id', 'user_id', name='uix_workspace_user')
    )
    with op.batch_alter_table('workspace_memberships', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_workspace_memberships_user_id'), ['user_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_workspace_memberships_workspace_id'), ['workspace_id'], unique=False)

    # 4. repositories
    op.create_table(
        'repositories',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('workspace_id', sa.String(length=100), nullable=False, server_default='ws_demo'),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('url', sa.String(length=255), nullable=True),
        sa.Column('default_branch', sa.String(length=50), nullable=True, server_default='main'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('workspace_id', 'name', name='uix_workspace_repo_name')
    )
    with op.batch_alter_table('repositories', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_repositories_id'), ['id'], unique=False)
        batch_op.create_index(batch_op.f('ix_repositories_name'), ['name'], unique=False)
        batch_op.create_index(batch_op.f('ix_repositories_workspace_id'), ['workspace_id'], unique=False)

    # 5. source_files
    op.create_table(
        'source_files',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('workspace_id', sa.String(length=100), nullable=False, server_default='ws_demo'),
        sa.Column('repository_id', sa.Integer(), nullable=False),
        sa.Column('file_path', sa.String(length=255), nullable=False),
        sa.Column('file_name', sa.String(length=100), nullable=False),
        sa.Column('language', sa.String(length=50), nullable=True, server_default='Python'),
        sa.Column('lines_of_code', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['repository_id'], ['repositories.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('source_files', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_source_files_file_path'), ['file_path'], unique=False)
        batch_op.create_index(batch_op.f('ix_source_files_id'), ['id'], unique=False)
        batch_op.create_index(batch_op.f('ix_source_files_repository_id'), ['repository_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_source_files_workspace_id'), ['workspace_id'], unique=False)

    # 6. engineering_metrics
    op.create_table(
        'engineering_metrics',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('workspace_id', sa.String(length=100), nullable=False, server_default='ws_demo'),
        sa.Column('file_id', sa.Integer(), nullable=False),
        sa.Column('cyclomatic_complexity', sa.Float(), nullable=True, server_default='1.0'),
        sa.Column('cognitive_complexity', sa.Float(), nullable=True, server_default='1.0'),
        sa.Column('code_smells_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('duplication_pct', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('test_coverage_pct', sa.Float(), nullable=True, server_default='100.0'),
        sa.Column('code_churn_commits', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('bug_frequency', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('coverage_provenance', sa.String(length=30), nullable=True, server_default='ESTIMATED'),
        sa.Column('churn_provenance', sa.String(length=30), nullable=True, server_default='ESTIMATED'),
        sa.Column('technical_risk_score', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['file_id'], ['source_files.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('engineering_metrics', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_engineering_metrics_file_id'), ['file_id'], unique=True)
        batch_op.create_index(batch_op.f('ix_engineering_metrics_id'), ['id'], unique=False)
        batch_op.create_index(batch_op.f('ix_engineering_metrics_workspace_id'), ['workspace_id'], unique=False)

    # 7. technical_debt_items
    op.create_table(
        'technical_debt_items',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('workspace_id', sa.String(length=100), nullable=False, server_default='ws_demo'),
        sa.Column('file_id', sa.Integer(), nullable=False),
        sa.Column('debt_category', sa.String(length=50), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=True, server_default='MEDIUM'),
        sa.Column('debt_age_days', sa.Integer(), nullable=True, server_default='30'),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('line_number', sa.Integer(), nullable=True),
        sa.Column('remediation_guidance', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['file_id'], ['source_files.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('technical_debt_items', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_technical_debt_items_file_id'), ['file_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_technical_debt_items_id'), ['id'], unique=False)
        batch_op.create_index(batch_op.f('ix_technical_debt_items_workspace_id'), ['workspace_id'], unique=False)

    # 8. ml_predictions
    op.create_table(
        'ml_predictions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('workspace_id', sa.String(length=100), nullable=False, server_default='ws_demo'),
        sa.Column('file_id', sa.Integer(), nullable=False),
        sa.Column('predicted_future_risk', sa.Float(), nullable=True, server_default='50.0'),
        sa.Column('defect_probability', sa.Float(), nullable=True, server_default='0.5'),
        sa.Column('churn_risk_score', sa.Float(), nullable=True, server_default='50.0'),
        sa.Column('confidence_score', sa.Float(), nullable=True, server_default='0.85'),
        sa.Column('model_version', sa.String(length=50), nullable=True, server_default='random-forest-szz-v1'),
        sa.Column('prediction_timestamp', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['file_id'], ['source_files.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('ml_predictions', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_ml_predictions_file_id'), ['file_id'], unique=True)
        batch_op.create_index(batch_op.f('ix_ml_predictions_id'), ['id'], unique=False)
        batch_op.create_index(batch_op.f('ix_ml_predictions_workspace_id'), ['workspace_id'], unique=False)

    # 9. business_contexts
    op.create_table(
        'business_contexts',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('workspace_id', sa.String(length=100), nullable=False, server_default='ws_demo'),
        sa.Column('file_id', sa.Integer(), nullable=False),
        sa.Column('business_criticality', sa.Float(), nullable=True, server_default='50.0'),
        sa.Column('customer_impact', sa.Float(), nullable=True, server_default='50.0'),
        sa.Column('module_criticality', sa.Float(), nullable=True, server_default='50.0'),
        sa.Column('release_proximity', sa.Float(), nullable=True, server_default='50.0'),
        sa.Column('sprint_urgency', sa.Float(), nullable=True, server_default='50.0'),
        sa.Column('maintenance_cost', sa.Float(), nullable=True, server_default='50.0'),
        sa.Column('estimated_remediation_effort', sa.Float(), nullable=True, server_default='50.0'),
        sa.Column('domain_tag', sa.String(length=50), nullable=True, server_default='core'),
        sa.Column('provenance', sa.String(length=30), nullable=True, server_default='DEFAULT'),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['file_id'], ['source_files.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('business_contexts', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_business_contexts_file_id'), ['file_id'], unique=True)
        batch_op.create_index(batch_op.f('ix_business_contexts_id'), ['id'], unique=False)
        batch_op.create_index(batch_op.f('ix_business_contexts_workspace_id'), ['workspace_id'], unique=False)

    # 10. priority_scores
    op.create_table(
        'priority_scores',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('workspace_id', sa.String(length=100), nullable=False, server_default='ws_demo'),
        sa.Column('file_id', sa.Integer(), nullable=False),
        sa.Column('composite_technical_risk', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('composite_business_impact', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('urgency_score', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('baseline_score', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('final_priority_score', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('priority_level', sa.String(length=20), nullable=True, server_default='LOW'),
        sa.Column('roi_score', sa.Float(), nullable=True, server_default='100.0'),
        sa.Column('quadrant', sa.String(length=50), nullable=True, server_default='OPPORTUNISTIC'),
        sa.Column('rank', sa.Integer(), nullable=True, server_default='1'),
        sa.Column('calculated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['file_id'], ['source_files.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('priority_scores', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_priority_scores_file_id'), ['file_id'], unique=True)
        batch_op.create_index(batch_op.f('ix_priority_scores_id'), ['id'], unique=False)
        batch_op.create_index(batch_op.f('ix_priority_scores_workspace_id'), ['workspace_id'], unique=False)

    # 11. recommendations
    op.create_table(
        'recommendations',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('workspace_id', sa.String(length=100), nullable=False, server_default='ws_demo'),
        sa.Column('file_id', sa.Integer(), nullable=False),
        sa.Column('recommendation_type', sa.String(length=50), nullable=False),
        sa.Column('action_summary', sa.String(length=255), nullable=False),
        sa.Column('rationale', sa.Text(), nullable=False),
        sa.Column('sprint_target', sa.String(length=50), nullable=True, server_default='Next Sprint'),
        sa.Column('estimated_story_points', sa.Integer(), nullable=True, server_default='3'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['file_id'], ['source_files.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('recommendations', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_recommendations_file_id'), ['file_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_recommendations_id'), ['id'], unique=False)
        batch_op.create_index(batch_op.f('ix_recommendations_workspace_id'), ['workspace_id'], unique=False)

    # 12. integration_connections
    op.create_table(
        'integration_connections',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('workspace_id', sa.String(length=100), nullable=False, server_default='ws_demo'),
        sa.Column('user_id', sa.String(length=100), nullable=False, server_default='usr_lead_01'),
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.Column('provider_account_id', sa.String(length=100), nullable=True),
        sa.Column('provider_account_name', sa.String(length=200), nullable=True),
        sa.Column('avatar_url', sa.String(length=255), nullable=True),
        sa.Column('access_token_enc', sa.Text(), nullable=True),
        sa.Column('refresh_token_enc', sa.Text(), nullable=True),
        sa.Column('token_expires_at', sa.DateTime(), nullable=True),
        sa.Column('scopes', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=30), nullable=True, server_default='CONNECTED'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('metadata_json', sa.Text(), nullable=True, server_default='{}'),
        sa.Column('last_sync_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('integration_connections', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_integration_connections_id'), ['id'], unique=False)
        batch_op.create_index(batch_op.f('ix_integration_connections_provider'), ['provider'], unique=False)
        batch_op.create_index(batch_op.f('ix_integration_connections_status'), ['status'], unique=False)
        batch_op.create_index(batch_op.f('ix_integration_connections_user_id'), ['user_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_integration_connections_workspace_id'), ['workspace_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema in reverse foreign-key dependency order."""
    op.drop_table('integration_connections')
    op.drop_table('recommendations')
    op.drop_table('priority_scores')
    op.drop_table('business_contexts')
    op.drop_table('ml_predictions')
    op.drop_table('technical_debt_items')
    op.drop_table('engineering_metrics')
    op.drop_table('source_files')
    op.drop_table('repositories')
    op.drop_table('workspace_memberships')
    op.drop_table('workspaces')
    op.drop_table('users')
