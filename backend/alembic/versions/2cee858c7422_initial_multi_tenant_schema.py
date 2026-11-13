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
    """Upgrade schema."""
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing_tables = set(insp.get_table_names())

    if 'users' not in existing_tables:
        op.create_table('users',
        sa.Column('id', sa.String(length=100), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=200), nullable=False),
        sa.Column('avatar_url', sa.String(length=500), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
        )
        with op.batch_alter_table('users', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_users_email'), ['email'], unique=True)
            batch_op.create_index(batch_op.f('ix_users_id'), ['id'], unique=False)

    if 'workspaces' not in existing_tables:
        op.create_table('workspaces',
        sa.Column('id', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('slug', sa.String(length=100), nullable=False),
        sa.Column('owner_id', sa.String(length=100), nullable=True),
        sa.Column('is_demo', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
        )
        with op.batch_alter_table('workspaces', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_workspaces_id'), ['id'], unique=False)
            batch_op.create_index(batch_op.f('ix_workspaces_is_demo'), ['is_demo'], unique=False)
            batch_op.create_index(batch_op.f('ix_workspaces_slug'), ['slug'], unique=True)

    if 'workspace_memberships' not in existing_tables:
        op.create_table('workspace_memberships',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('workspace_id', sa.String(length=100), nullable=False),
        sa.Column('user_id', sa.String(length=100), nullable=False),
        sa.Column('role', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('workspace_id', 'user_id', name='uix_workspace_user')
        )
        with op.batch_alter_table('workspace_memberships', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_workspace_memberships_user_id'), ['user_id'], unique=False)
            batch_op.create_index(batch_op.f('ix_workspace_memberships_workspace_id'), ['workspace_id'], unique=False)

    insp = sa.inspect(bind)
    existing_tables = set(insp.get_table_names())

    # If base tables do not exist (e.g. fresh database setup), ensure base models are created first
    if 'business_contexts' not in existing_tables or 'repositories' not in existing_tables:
        from backend.database.models import Base
        Base.metadata.create_all(bind=bind)
        existing_tables = set(sa.inspect(bind).get_table_names())

    if 'business_contexts' in existing_tables:
        cols = [c['name'] for c in sa.inspect(bind).get_columns('business_contexts')]
        if 'workspace_id' not in cols:
            with op.batch_alter_table('business_contexts', schema=None) as batch_op:
                batch_op.add_column(sa.Column('workspace_id', sa.String(length=100), nullable=False, server_default='ws_demo'))
                batch_op.add_column(sa.Column('provenance', sa.String(length=30), nullable=True, server_default='DEFAULT'))
                batch_op.create_index(batch_op.f('ix_business_contexts_workspace_id'), ['workspace_id'], unique=False)

    if 'engineering_metrics' in existing_tables:
        cols = [c['name'] for c in sa.inspect(bind).get_columns('engineering_metrics')]
        if 'workspace_id' not in cols:
            with op.batch_alter_table('engineering_metrics', schema=None) as batch_op:
                batch_op.add_column(sa.Column('workspace_id', sa.String(length=100), nullable=False, server_default='ws_demo'))
                batch_op.add_column(sa.Column('coverage_provenance', sa.String(length=30), nullable=True, server_default='ESTIMATED'))
                batch_op.add_column(sa.Column('churn_provenance', sa.String(length=30), nullable=True, server_default='ESTIMATED'))
                batch_op.create_index(batch_op.f('ix_engineering_metrics_workspace_id'), ['workspace_id'], unique=False)

    if 'integration_connections' in existing_tables:
        cols = [c['name'] for c in sa.inspect(bind).get_columns('integration_connections')]
        if 'workspace_id' not in cols:
            with op.batch_alter_table('integration_connections', schema=None) as batch_op:
                batch_op.add_column(sa.Column('workspace_id', sa.String(length=100), nullable=False, server_default='ws_demo'))
                batch_op.create_index(batch_op.f('ix_integration_connections_workspace_id'), ['workspace_id'], unique=False)

    if 'ml_predictions' in existing_tables:
        cols = [c['name'] for c in sa.inspect(bind).get_columns('ml_predictions')]
        if 'workspace_id' not in cols:
            with op.batch_alter_table('ml_predictions', schema=None) as batch_op:
                batch_op.add_column(sa.Column('workspace_id', sa.String(length=100), nullable=False, server_default='ws_demo'))
                batch_op.create_index(batch_op.f('ix_ml_predictions_workspace_id'), ['workspace_id'], unique=False)

    if 'priority_scores' in existing_tables:
        cols = [c['name'] for c in sa.inspect(bind).get_columns('priority_scores')]
        if 'workspace_id' not in cols:
            with op.batch_alter_table('priority_scores', schema=None) as batch_op:
                batch_op.add_column(sa.Column('workspace_id', sa.String(length=100), nullable=False, server_default='ws_demo'))
                batch_op.create_index(batch_op.f('ix_priority_scores_workspace_id'), ['workspace_id'], unique=False)

    if 'recommendations' in existing_tables:
        cols = [c['name'] for c in sa.inspect(bind).get_columns('recommendations')]
        if 'workspace_id' not in cols:
            with op.batch_alter_table('recommendations', schema=None) as batch_op:
                batch_op.add_column(sa.Column('workspace_id', sa.String(length=100), nullable=False, server_default='ws_demo'))
                batch_op.create_index(batch_op.f('ix_recommendations_workspace_id'), ['workspace_id'], unique=False)

    if 'repositories' in existing_tables:
        cols = [c['name'] for c in sa.inspect(bind).get_columns('repositories')]
        if 'workspace_id' not in cols:
            with op.batch_alter_table('repositories', schema=None) as batch_op:
                batch_op.add_column(sa.Column('workspace_id', sa.String(length=100), nullable=False, server_default='ws_demo'))
                try:
                    batch_op.drop_index(batch_op.f('ix_repositories_name'))
                except Exception:
                    pass
                batch_op.create_index(batch_op.f('ix_repositories_name'), ['name'], unique=False)
                batch_op.create_index(batch_op.f('ix_repositories_workspace_id'), ['workspace_id'], unique=False)
                try:
                    batch_op.create_unique_constraint('uix_workspace_repo_name', ['workspace_id', 'name'])
                except Exception:
                    pass

    if 'source_files' in existing_tables:
        cols = [c['name'] for c in sa.inspect(bind).get_columns('source_files')]
        if 'workspace_id' not in cols:
            with op.batch_alter_table('source_files', schema=None) as batch_op:
                batch_op.add_column(sa.Column('workspace_id', sa.String(length=100), nullable=False, server_default='ws_demo'))
                batch_op.create_index(batch_op.f('ix_source_files_workspace_id'), ['workspace_id'], unique=False)

    if 'technical_debt_items' in existing_tables:
        cols = [c['name'] for c in sa.inspect(bind).get_columns('technical_debt_items')]
        if 'workspace_id' not in cols:
            with op.batch_alter_table('technical_debt_items', schema=None) as batch_op:
                batch_op.add_column(sa.Column('workspace_id', sa.String(length=100), nullable=False, server_default='ws_demo'))
                batch_op.create_index(batch_op.f('ix_technical_debt_items_workspace_id'), ['workspace_id'], unique=False)

    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('technical_debt_items', schema=None) as batch_op:
        # WARNING: constraint name is None; this directive will fail as
        # rendered.  Add a name, or use a naming convention; see
        # https://alembic.sqlalchemy.org/en/latest/naming.html
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_technical_debt_items_workspace_id'))
        batch_op.drop_column('workspace_id')

    with op.batch_alter_table('source_files', schema=None) as batch_op:
        # WARNING: constraint name is None; this directive will fail as
        # rendered.  Add a name, or use a naming convention; see
        # https://alembic.sqlalchemy.org/en/latest/naming.html
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_source_files_workspace_id'))
        batch_op.drop_column('workspace_id')

    with op.batch_alter_table('repositories', schema=None) as batch_op:
        # WARNING: constraint name is None; this directive will fail as
        # rendered.  Add a name, or use a naming convention; see
        # https://alembic.sqlalchemy.org/en/latest/naming.html
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.drop_constraint('uix_workspace_repo_name', type_='unique')
        batch_op.drop_index(batch_op.f('ix_repositories_workspace_id'))
        batch_op.drop_index(batch_op.f('ix_repositories_name'))
        batch_op.create_index(batch_op.f('ix_repositories_name'), ['name'], unique=1)
        batch_op.drop_column('workspace_id')

    with op.batch_alter_table('recommendations', schema=None) as batch_op:
        # WARNING: constraint name is None; this directive will fail as
        # rendered.  Add a name, or use a naming convention; see
        # https://alembic.sqlalchemy.org/en/latest/naming.html
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_recommendations_workspace_id'))
        batch_op.drop_column('workspace_id')

    with op.batch_alter_table('priority_scores', schema=None) as batch_op:
        # WARNING: constraint name is None; this directive will fail as
        # rendered.  Add a name, or use a naming convention; see
        # https://alembic.sqlalchemy.org/en/latest/naming.html
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_priority_scores_workspace_id'))
        batch_op.drop_column('workspace_id')

    with op.batch_alter_table('ml_predictions', schema=None) as batch_op:
        # WARNING: constraint name is None; this directive will fail as
        # rendered.  Add a name, or use a naming convention; see
        # https://alembic.sqlalchemy.org/en/latest/naming.html
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_ml_predictions_workspace_id'))
        batch_op.drop_column('workspace_id')

    with op.batch_alter_table('integration_connections', schema=None) as batch_op:
        # WARNING: constraint name is None; this directive will fail as
        # rendered.  Add a name, or use a naming convention; see
        # https://alembic.sqlalchemy.org/en/latest/naming.html
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_integration_connections_workspace_id'))
        batch_op.drop_column('workspace_id')

    with op.batch_alter_table('engineering_metrics', schema=None) as batch_op:
        # WARNING: constraint name is None; this directive will fail as
        # rendered.  Add a name, or use a naming convention; see
        # https://alembic.sqlalchemy.org/en/latest/naming.html
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_engineering_metrics_workspace_id'))
        batch_op.drop_column('churn_provenance')
        batch_op.drop_column('coverage_provenance')
        batch_op.drop_column('workspace_id')

    with op.batch_alter_table('business_contexts', schema=None) as batch_op:
        # WARNING: constraint name is None; this directive will fail as
        # rendered.  Add a name, or use a naming convention; see
        # https://alembic.sqlalchemy.org/en/latest/naming.html
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_business_contexts_workspace_id'))
        batch_op.drop_column('provenance')
        batch_op.drop_column('workspace_id')

    with op.batch_alter_table('workspace_memberships', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_workspace_memberships_workspace_id'))
        batch_op.drop_index(batch_op.f('ix_workspace_memberships_user_id'))

    op.drop_table('workspace_memberships')
    with op.batch_alter_table('workspaces', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_workspaces_slug'))
        batch_op.drop_index(batch_op.f('ix_workspaces_is_demo'))
        batch_op.drop_index(batch_op.f('ix_workspaces_id'))

    op.drop_table('workspaces')
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_users_id'))
        batch_op.drop_index(batch_op.f('ix_users_email'))

    op.drop_table('users')
    # ### end Alembic commands ###
