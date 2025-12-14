"""create api_keys table

Revision ID: 20241213_0003
Revises: 20241213_0002
Create Date: 2024-12-13 21:10:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON


# revision identifiers, used by Alembic.
revision = '20241213_0003'
down_revision = '20241213_0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the api_keys table with all required fields and indexes."""

    # Create api_keys table
    op.create_table(
        'api_keys',
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

        # User relationship
        sa.Column(
            'user_id',
            UUID(as_uuid=True),
            nullable=False,
            comment='UUID of the user who owns this API key'
        ),

        # Key identification
        sa.Column(
            'name',
            sa.String(length=255),
            nullable=False,
            comment='Human-friendly name for the key'
        ),

        # Key storage (NEVER store raw key, only hash)
        sa.Column(
            'key_hash',
            sa.String(length=64),
            nullable=False,
            unique=True,
            comment='SHA256 hash of the API key - NEVER store raw key'
        ),
        sa.Column(
            'key_prefix',
            sa.String(length=12),
            nullable=False,
            comment="First 8-12 characters of the key for identification (e.g., 'sk_live')"
        ),

        # Permissions and access control
        sa.Column(
            'scopes',
            JSON,
            nullable=False,
            server_default='[]',
            comment='JSON array of permission scopes'
        ),

        # Rate limiting
        sa.Column(
            'rate_limit_tier',
            sa.String(length=20),
            nullable=False,
            server_default='free',
            comment='Rate limit tier (free, pro, enterprise)'
        ),

        # Expiration
        sa.Column(
            'expires_at',
            sa.DateTime(),
            nullable=True,
            comment='Optional expiration timestamp (None = never expires)'
        ),

        # Usage tracking
        sa.Column(
            'last_used_at',
            sa.DateTime(),
            nullable=True,
            comment='Timestamp of last successful authentication'
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
        'ix_api_keys_user_id',
        'api_keys',
        ['user_id'],
        unique=False
    )
    op.create_index(
        'ix_api_keys_key_hash',
        'api_keys',
        ['key_hash'],
        unique=True
    )
    op.create_index(
        'ix_api_keys_key_prefix',
        'api_keys',
        ['key_prefix'],
        unique=False
    )
    op.create_index(
        'ix_api_keys_expires_at',
        'api_keys',
        ['expires_at'],
        unique=False
    )

    # Composite indexes for common query patterns
    op.create_index(
        'ix_api_keys_user_id_deleted_at',
        'api_keys',
        ['user_id', 'deleted_at'],
        unique=False
    )
    op.create_index(
        'ix_api_keys_key_hash_deleted_at',
        'api_keys',
        ['key_hash', 'deleted_at'],
        unique=False
    )

    # Add foreign key constraint to users table
    op.create_foreign_key(
        'fk_api_keys_user_id',
        'api_keys',
        'users',
        ['user_id'],
        ['id'],
        ondelete='CASCADE'
    )


def downgrade() -> None:
    """Drop the api_keys table and all its indexes."""

    # Drop foreign key first
    op.drop_constraint('fk_api_keys_user_id', 'api_keys', type_='foreignkey')

    # Drop all indexes
    op.drop_index('ix_api_keys_key_hash_deleted_at', table_name='api_keys')
    op.drop_index('ix_api_keys_user_id_deleted_at', table_name='api_keys')
    op.drop_index('ix_api_keys_expires_at', table_name='api_keys')
    op.drop_index('ix_api_keys_key_prefix', table_name='api_keys')
    op.drop_index('ix_api_keys_key_hash', table_name='api_keys')
    op.drop_index('ix_api_keys_user_id', table_name='api_keys')

    # Drop the table
    op.drop_table('api_keys')
