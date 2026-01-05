"""Initial schema

Revision ID: 001_initial
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('external_core_id', sa.String(255), unique=True, nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_users_external_core_id', 'users', ['external_core_id'])

    # Create transactions table
    op.create_table(
        'transactions',
        sa.Column('transaction_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('reason', sa.String(50), nullable=False),
        sa.Column('stripe_ref', sa.String(255), nullable=True),
        sa.Column('category', sa.String(100), nullable=True),
        sa.Column('metadata', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id']),
    )
    op.create_index('ix_transactions_user_id', 'transactions', ['user_id'])
    op.create_index('ix_transactions_created_at', 'transactions', ['created_at'])
    op.create_index('ix_transactions_stripe_ref', 'transactions', ['stripe_ref'])
    op.create_index('idx_user_created', 'transactions', ['user_id', 'created_at'])
    op.create_index('idx_stripe_ref', 'transactions', ['stripe_ref'])

    # Create stripe_accounts table
    op.create_table(
        'stripe_accounts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), unique=True, nullable=False),
        sa.Column('stripe_account_id', sa.String(255), unique=True, nullable=False),
        sa.Column('account_type', sa.String(50), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id']),
    )
    op.create_index('ix_stripe_accounts_user_id', 'stripe_accounts', ['user_id'])
    op.create_index('ix_stripe_accounts_stripe_account_id', 'stripe_accounts', ['stripe_account_id'])

    # Create campaigns table
    op.create_table(
        'campaigns',
        sa.Column('campaign_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('reward_multiplier', sa.Numeric(5, 2), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('start_date', sa.DateTime(), nullable=False),
        sa.Column('end_date', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )

    # Create audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('log_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id_hash', sa.String(64), nullable=False),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_audit_logs_user_id_hash', 'audit_logs', ['user_id_hash'])
    op.create_index('ix_audit_logs_created_at', 'audit_logs', ['created_at'])
    op.create_index('idx_user_action_created', 'audit_logs', ['user_id_hash', 'action', 'created_at'])


def downgrade() -> None:
    op.drop_table('audit_logs')
    op.drop_table('campaigns')
    op.drop_table('stripe_accounts')
    op.drop_table('transactions')
    op.drop_table('users')

