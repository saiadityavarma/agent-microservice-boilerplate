"""create audit_logs table

Revision ID: 20241213_0001
Revises:
Create Date: 2024-12-13 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


# revision identifiers, used by Alembic.
revision = '20241213_0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the audit_logs table with all required fields and indexes."""

    # Create audit_logs table
    op.create_table(
        'audit_logs',
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

        # Audit-specific fields
        sa.Column(
            'timestamp',
            sa.DateTime(),
            nullable=False,
            comment='When the audited action occurred'
        ),
        sa.Column(
            'user_id',
            UUID(as_uuid=True),
            nullable=True,
            comment='User who performed the action, null for system/anonymous'
        ),
        sa.Column(
            'action',
            sa.String(length=50),
            nullable=False,
            comment='Action type: CREATE, READ, UPDATE, DELETE, EXECUTE, LOGIN, LOGOUT, FAILED_AUTH'
        ),
        sa.Column(
            'resource_type',
            sa.String(length=100),
            nullable=False,
            comment='Resource type: user, agent, tool, api_key, etc.'
        ),
        sa.Column(
            'resource_id',
            sa.String(length=255),
            nullable=True,
            comment='Resource identifier, null for list/bulk operations'
        ),
        sa.Column(
            'ip_address',
            sa.String(length=45),  # IPv6 max length
            nullable=False,
            comment='Client IP address (IPv4 or IPv6)'
        ),
        sa.Column(
            'user_agent',
            sa.String(length=500),
            nullable=False,
            comment='Client user agent string'
        ),
        sa.Column(
            'request_id',
            UUID(as_uuid=True),
            nullable=False,
            comment='Request ID for correlating related audit entries'
        ),
        sa.Column(
            'request_path',
            sa.String(length=500),
            nullable=False,
            comment='HTTP request path'
        ),
        sa.Column(
            'request_method',
            sa.String(length=10),
            nullable=False,
            comment='HTTP method: GET, POST, PUT, DELETE, PATCH, etc.'
        ),
        sa.Column(
            'request_body',
            sa.Text(),
            nullable=True,
            comment='Request body, may be encrypted or redacted for sensitive data'
        ),
        sa.Column(
            'response_status',
            sa.Integer(),
            nullable=False,
            comment='HTTP response status code'
        ),
        sa.Column(
            'changes',
            JSONB,
            nullable=True,
            comment='Before/after diff for UPDATE operations: {field: {old: value, new: value}}'
        ),
        sa.Column(
            'metadata',
            JSONB,
            nullable=True,
            comment='Additional context and metadata for the audit entry'
        ),
    )

    # Create indexes for performance optimization

    # Individual column indexes for common filters
    op.create_index(
        'ix_audit_logs_timestamp',
        'audit_logs',
        ['timestamp'],
        unique=False
    )
    op.create_index(
        'ix_audit_logs_user_id',
        'audit_logs',
        ['user_id'],
        unique=False
    )
    op.create_index(
        'ix_audit_logs_action',
        'audit_logs',
        ['action'],
        unique=False
    )
    op.create_index(
        'ix_audit_logs_resource_type',
        'audit_logs',
        ['resource_type'],
        unique=False
    )
    op.create_index(
        'ix_audit_logs_request_id',
        'audit_logs',
        ['request_id'],
        unique=False
    )

    # Composite indexes for common query patterns
    op.create_index(
        'ix_audit_logs_user_action',
        'audit_logs',
        ['user_id', 'action'],
        unique=False
    )
    op.create_index(
        'ix_audit_logs_resource',
        'audit_logs',
        ['resource_type', 'resource_id'],
        unique=False
    )
    op.create_index(
        'ix_audit_logs_timestamp_action',
        'audit_logs',
        ['timestamp', 'action'],
        unique=False
    )
    op.create_index(
        'ix_audit_logs_timestamp_user',
        'audit_logs',
        ['timestamp', 'user_id'],
        unique=False
    )
    op.create_index(
        'ix_audit_logs_timestamp_resource',
        'audit_logs',
        ['timestamp', 'resource_type'],
        unique=False
    )


def downgrade() -> None:
    """Drop the audit_logs table and all its indexes."""

    # Drop all indexes first
    op.drop_index('ix_audit_logs_timestamp_resource', table_name='audit_logs')
    op.drop_index('ix_audit_logs_timestamp_user', table_name='audit_logs')
    op.drop_index('ix_audit_logs_timestamp_action', table_name='audit_logs')
    op.drop_index('ix_audit_logs_resource', table_name='audit_logs')
    op.drop_index('ix_audit_logs_user_action', table_name='audit_logs')
    op.drop_index('ix_audit_logs_request_id', table_name='audit_logs')
    op.drop_index('ix_audit_logs_resource_type', table_name='audit_logs')
    op.drop_index('ix_audit_logs_action', table_name='audit_logs')
    op.drop_index('ix_audit_logs_user_id', table_name='audit_logs')
    op.drop_index('ix_audit_logs_timestamp', table_name='audit_logs')

    # Drop the table
    op.drop_table('audit_logs')
