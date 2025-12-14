"""create sessions table

Revision ID: 20241213_0004
Revises: 20241213_0003
Create Date: 2024-12-13 21:20:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


# revision identifiers, used by Alembic.
revision = '20241213_0004'
down_revision = '20241213_0003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the sessions table with all required fields and indexes."""

    # Create sessions table
    op.create_table(
        'sessions',
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

        # User and agent identification
        sa.Column(
            'user_id',
            UUID(as_uuid=True),
            nullable=False,
            comment='User who owns this session'
        ),
        sa.Column(
            'agent_id',
            sa.String(length=255),
            nullable=False,
            comment='Agent identifier for this session'
        ),

        # Session identification
        sa.Column(
            'title',
            sa.String(length=500),
            nullable=False,
            comment='Session title'
        ),

        # Session status
        sa.Column(
            'status',
            sa.String(length=50),
            nullable=False,
            server_default='active',
            comment='Session status: active, completed, failed, cancelled'
        ),

        # Conversation data
        sa.Column(
            'messages',
            JSONB,
            nullable=False,
            server_default='[]',
            comment='Conversation messages in chronological order'
        ),

        # Session context and metadata
        sa.Column(
            'context',
            JSONB,
            nullable=False,
            server_default='{}',
            comment='Session context and state variables'
        ),
        sa.Column(
            'metadata',
            JSONB,
            nullable=False,
            server_default='{}',
            comment='Additional session metadata'
        ),

        # Usage statistics
        sa.Column(
            'total_messages',
            sa.Integer(),
            nullable=False,
            server_default='0',
            comment='Total number of messages'
        ),
        sa.Column(
            'total_tokens',
            sa.Integer(),
            nullable=True,
            comment='Total tokens used (if tracked)'
        ),

        # Activity tracking
        sa.Column(
            'last_activity_at',
            sa.DateTime(),
            nullable=False,
            server_default=sa.text('CURRENT_TIMESTAMP'),
            comment='Last activity timestamp'
        ),

        # Expiration
        sa.Column(
            'expires_at',
            sa.DateTime(),
            nullable=True,
            comment='Session expiration timestamp'
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
        'ix_sessions_user_id',
        'sessions',
        ['user_id'],
        unique=False
    )
    op.create_index(
        'ix_sessions_agent_id',
        'sessions',
        ['agent_id'],
        unique=False
    )
    op.create_index(
        'ix_sessions_status',
        'sessions',
        ['status'],
        unique=False
    )
    op.create_index(
        'ix_sessions_last_activity_at',
        'sessions',
        ['last_activity_at'],
        unique=False
    )
    op.create_index(
        'ix_sessions_expires_at',
        'sessions',
        ['expires_at'],
        unique=False
    )

    # Composite indexes for common query patterns
    op.create_index(
        'ix_sessions_user_id_status',
        'sessions',
        ['user_id', 'status'],
        unique=False
    )
    op.create_index(
        'ix_sessions_user_id_last_activity',
        'sessions',
        ['user_id', 'last_activity_at'],
        unique=False
    )
    op.create_index(
        'ix_sessions_agent_id_status',
        'sessions',
        ['agent_id', 'status'],
        unique=False
    )
    op.create_index(
        'ix_sessions_status_deleted_at',
        'sessions',
        ['status', 'deleted_at'],
        unique=False
    )

    # Add foreign key constraint to users table
    op.create_foreign_key(
        'fk_sessions_user_id',
        'sessions',
        'users',
        ['user_id'],
        ['id'],
        ondelete='CASCADE'
    )


def downgrade() -> None:
    """Drop the sessions table and all its indexes."""

    # Drop foreign key first
    op.drop_constraint('fk_sessions_user_id', 'sessions', type_='foreignkey')

    # Drop all indexes
    op.drop_index('ix_sessions_status_deleted_at', table_name='sessions')
    op.drop_index('ix_sessions_agent_id_status', table_name='sessions')
    op.drop_index('ix_sessions_user_id_last_activity', table_name='sessions')
    op.drop_index('ix_sessions_user_id_status', table_name='sessions')
    op.drop_index('ix_sessions_expires_at', table_name='sessions')
    op.drop_index('ix_sessions_last_activity_at', table_name='sessions')
    op.drop_index('ix_sessions_status', table_name='sessions')
    op.drop_index('ix_sessions_agent_id', table_name='sessions')
    op.drop_index('ix_sessions_user_id', table_name='sessions')

    # Drop the table
    op.drop_table('sessions')
