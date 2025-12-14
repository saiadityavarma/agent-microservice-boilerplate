"""
Prometheus metrics.

Claude Code: Add new metrics following this pattern.
"""
from prometheus_client import Counter, Histogram, Gauge, REGISTRY


# Request metrics
REQUEST_COUNT = Counter(
    "agent_requests_total",
    "Total requests",
    ["method", "endpoint", "status"],
)

REQUEST_LATENCY = Histogram(
    "agent_request_latency_seconds",
    "Request latency",
    ["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0],
)

# Agent metrics
AGENT_INVOCATIONS = Counter(
    "agent_invocations_total",
    "Total agent invocations",
    ["agent_name", "status"],
)

AGENT_LATENCY = Histogram(
    "agent_latency_seconds",
    "Agent invocation latency",
    ["agent_name"],
)

# Tool metrics
TOOL_EXECUTIONS = Counter(
    "tool_executions_total",
    "Total tool executions",
    ["tool_name", "status"],
)

# Active connections
ACTIVE_STREAMS = Gauge(
    "active_streams",
    "Number of active streaming connections",
)


# ──────────────────────────────────────────────
# Claude Code: Add new metrics here
# ──────────────────────────────────────────────

# Authentication metrics
AUTH_LOGIN_TOTAL = Counter(
    "auth_login_total",
    "Total authentication login attempts",
    ["provider", "success"],
)

AUTH_TOKEN_REFRESH_TOTAL = Counter(
    "auth_token_refresh_total",
    "Total token refresh attempts",
    ["provider", "success"],
)

AUTH_FAILED_ATTEMPTS_TOTAL = Counter(
    "auth_failed_attempts_total",
    "Total failed authentication attempts",
    ["reason"],
)

# Database metrics
DB_POOL_SIZE = Gauge(
    "db_pool_size",
    "Database connection pool size",
)

DB_POOL_CHECKED_OUT = Gauge(
    "db_pool_checked_out",
    "Number of database connections currently checked out",
)

DB_QUERY_DURATION_SECONDS = Histogram(
    "db_query_duration_seconds",
    "Database query duration in seconds",
    ["query_type"],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0],
)

# Redis metrics
REDIS_CONNECTIONS_ACTIVE = Gauge(
    "redis_connections_active",
    "Number of active Redis connections",
)

REDIS_OPERATIONS_TOTAL = Counter(
    "redis_operations_total",
    "Total Redis operations",
    ["operation"],
)

# Agent metrics (enhanced)
AGENT_EXECUTION_DURATION_SECONDS = Histogram(
    "agent_execution_duration_seconds",
    "Agent execution duration in seconds",
    ["agent_name"],
    buckets=[0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 120.0],
)

AGENT_TOKENS_USED_TOTAL = Counter(
    "agent_tokens_used_total",
    "Total tokens used by agents",
    ["agent_name", "token_type"],
)

# Tool metrics (enhanced)
TOOL_EXECUTION_DURATION_SECONDS = Histogram(
    "tool_execution_duration_seconds",
    "Tool execution duration in seconds",
    ["tool_name"],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0],
)

# Business metrics
USERS_TOTAL = Gauge(
    "users_total",
    "Total number of users in the system",
)

API_KEYS_ACTIVE = Gauge(
    "api_keys_active",
    "Number of active API keys",
)

SESSIONS_ACTIVE = Gauge(
    "sessions_active",
    "Number of active user sessions",
)
