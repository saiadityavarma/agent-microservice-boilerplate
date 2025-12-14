"""create users table

Revision ID: 20241213_0002
Revises: 20241213_0001
Create Date: 2024-12-13 21:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


# revision identifiers, used by Alembic.
revision = '20241213_0002'
down_revision = '20241213_0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the users table with all required fields and indexes."""

    # Create users table
    op.create_table(
        'users',
        # Primary key and timestamps (from BaseModel)
        sa.Column('id', UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(),
            nullable=False,
            server_default=sa.text('CURRENT_TIMESTAMP'),
            comment='When the record was created'
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(),
            nullable=False,
            server_default=sa.text('CURRENT_TIMESTAMP'),
            comment='When the record was last updated'
        ),

        # User identification
        sa.Column(
            'email',
            sa.String(length=255),
            nullable=False,
            unique=True,
            comment='User email address - unique across all providers'
        ),
        sa.Column(
            'name',
            sa.String(length=255),
            nullable=False,
            comment="User's full name"
        ),

        # Authentication
        sa.Column(
            'hashed_password',
            sa.String(length=255),
            nullable=True,
            comment='Hashed password - null for OAuth users'
        ),
        sa.Column(
            'provider',
            sa.String(length=50),
            nullable=False,
            comment='Authentication provider: azure_ad, aws_cognito, local'
        ),
        sa.Column(
            'provider_user_id',
            sa.String(length=255),
            nullable=False,
            comment='User ID from the authentication provider'
        ),

        # Authorization
        sa.Column(
            'roles',
            JSONB,
            nullable=False,
            server_default='[]',
            comment='User roles for RBAC'
        ),
        sa.Column(
            'groups',
            JSONB,
            nullable=False,
            server_default='[]',
            comment='User groups for organization'
        ),

        # Status
        sa.Column(
            'is_active',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('true'),
            comment='User account active status'
        ),

        # Soft delete (from SoftDeleteMixin)
        sa.Column(
            'deleted_at',
            sa.DateTime(),
            nullable=True,
            comment='Soft delete timestamp'
        ),
    )

    # Create indexes for performance optimization

    # Individual column indexes
    op.create_index(
        'ix_users_email',
        'users',
        ['email'],
        unique=True
    )
    op.create_index(
        'ix_users_provider',
        'users',
        ['provider'],
        unique=False
    )
    op.create_index(
        'ix_users_provider_user_id',
        'users',
        ['provider_user_id'],
        unique=False
    )
    op.create_index(
        'ix_users_is_active',
        'users',
        ['is_active'],
        unique=False
    )

    # Composite indexes for common query patterns
    op.create_index(
        'ix_users_provider_provider_user_id',
        'users',
        ['provider', 'provider_user_id'],
        unique=False
    )
    op.create_index(
        'ix_users_email_deleted_at',
        'users',
        ['email', 'deleted_at'],
        unique=False
    )
    op.create_index(
        'ix_users_is_active_deleted_at',
        'users',
        ['is_active', 'deleted_at'],
        unique=False
    )


def downgrade() -> None:
    """Drop the users table and all its indexes."""

    # Drop all indexes first
    op.drop_index('ix_users_is_active_deleted_at', table_name='users')
    op.drop_index('ix_users_email_deleted_at', table_name='users')
    op.drop_index('ix_users_provider_provider_user_id', table_name='users')
    op.drop_index('ix_users_is_active', table_name='users')
    op.drop_index('ix_users_provider_user_id', table_name='users')
    op.drop_index('ix_users_provider', table_name='users')
    op.drop_index('ix_users_email', table_name='users')

    # Drop the table
    op.drop_table('users')
