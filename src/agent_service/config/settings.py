from functools import lru_cache
from typing import Literal
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment.

    Claude Code: Add new settings here following this pattern:
    - Use type hints
    - Provide sensible defaults for optional settings
    - Use SecretStr for sensitive values
    - Add validation where needed
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "Agent Service"
    app_version: str = "0.1.0"
    environment: Literal["local", "dev", "staging", "prod"] = "local"
    debug: bool = False

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Database (optional - only if using DB)
    database_url: SecretStr | None = None
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_timeout: int = 30
    db_pool_recycle: int = 3600
    db_echo_sql: bool = False

    # Redis (optional - only if using cache)
    redis_url: SecretStr | None = None

    # Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_default_tier: str = "free"

    # Auth (optional)
    secret_key: SecretStr | None = None

    # Feature Flags - protocols
    enable_mcp: bool = True
    enable_a2a: bool = True
    enable_agui: bool = True

    # Observability
    log_level: int = 20  # INFO by default (DEBUG=10, INFO=20, WARNING=30, ERROR=40)
    log_format: Literal["json", "console"] = "json"
    log_include_request_body: bool = False
    log_pii_masking_enabled: bool = True
    log_max_body_length: int = 1000
    otel_exporter_endpoint: str | None = None

    # Tracing
    tracing_enabled: bool = True
    tracing_exporter: Literal["otlp", "jaeger", "console", "none"] = "console"
    tracing_endpoint: str = "http://localhost:4317"  # OTLP endpoint
    tracing_sample_rate: float = 1.0  # 1.0 = trace everything, 0.0 = trace nothing

    # ──────────────────────────────────────────────
    # Claude Code: Add new settings below this line
    # ──────────────────────────────────────────────

    # Authentication Provider
    auth_provider: Literal["azure_ad", "aws_cognito", "none"] = "none"

    # Azure AD Settings
    azure_tenant_id: str | None = None
    azure_client_id: str | None = None
    azure_client_secret: SecretStr | None = None
    azure_authority: str | None = None

    # AWS Cognito Settings
    aws_region: str | None = None
    aws_cognito_user_pool_id: str | None = None
    aws_cognito_client_id: str | None = None
    aws_cognito_client_secret: SecretStr | None = None

    # API Key Settings
    api_key_prefix: str = "sk_live"
    api_key_default_expiry_days: int = 365
    api_key_hash_algorithm: str = "sha256"

    # General Auth Settings
    auth_token_cache_ttl: int = 300  # seconds
    auth_jwks_cache_ttl: int = 3600  # seconds

    # Security Headers Settings
    security_hsts_enabled: bool = True  # Only enable in production
    security_hsts_max_age: int = 31536000  # 1 year in seconds
    security_csp_policy: str = "default-src 'self'"
    security_frame_options: str = "DENY"

    # CORS Settings
    cors_origins: list[str] = Field(default_factory=list)  # Allowed origins (empty = disallow all in prod)
    cors_allow_credentials: bool = True
    cors_allow_methods: list[str] = Field(
        default_factory=lambda: ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]
    )
    cors_allow_headers: list[str] = Field(default_factory=lambda: ["*"])
    cors_max_age: int = 600  # Preflight cache time in seconds

    # Secrets Management
    secrets_provider: Literal["env", "aws"] = "env"
    secrets_cache_ttl: int = 3600  # Cache TTL in seconds for AWS provider
    secrets_aws_region: str | None = None  # AWS region for Secrets Manager

    # Audit Logging
    audit_logging_enabled: bool = True
    audit_log_retention_days: int = 90

    # Sentry Error Tracking
    sentry_dsn: str | None = None
    sentry_environment: str | None = None
    sentry_sample_rate: float = 1.0  # 1.0 = capture all errors
    sentry_traces_sample_rate: float = 0.1  # 0.1 = capture 10% of transactions

    # Cache Settings
    cache_default_ttl: int = 300  # Default TTL in seconds (5 minutes)
    cache_key_prefix: str = "agent_service"  # Prefix for all cache keys

    # Session Settings
    session_max_messages: int = 100  # Maximum messages per session
    session_expiry_hours: int = 24  # Session expiry time in hours

    # Celery Background Jobs Settings
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"
    celery_task_default_queue: str = "agent-service"
    celery_task_default_retry_delay: int = 60  # Retry delay in seconds
    celery_task_max_retries: int = 3
    celery_task_time_limit: int = 600  # 10 minutes max per task
    celery_task_soft_time_limit: int = 540  # 9 minutes soft limit (warning)
    celery_worker_prefetch_multiplier: int = 4
    celery_worker_max_tasks_per_child: int = 1000

    @property
    def is_production(self) -> bool:
        return self.environment == "prod"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
