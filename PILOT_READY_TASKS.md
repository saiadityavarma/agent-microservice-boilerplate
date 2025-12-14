# Pilot-Ready Implementation Tasks

## Vision Statement

**Goal**: A production-grade boilerplate where data scientists and developers can:
1. Clone the repo
2. Use Claude Code to write agent/service logic
3. Deploy to production **without architecture expertise**

**What the boilerplate handles**: Authentication, authorization, logging, observability, security, database, caching, rate limiting, error handling, API best practices, deployment, scaling.

**What users focus on**: Agent logic, business rules, framework selection (LangGraph, CrewAI, AutoGen).

---

## Phase 0: Project Setup & Standards (Week 1)
**Estimated Time**: 3-4 days
**Goal**: Establish development standards and CI/CD pipeline

### Task 0.1: Development Environment Setup
```
Priority: Critical
Files to Create:
├── .pre-commit-config.yaml
├── .github/
│   ├── workflows/
│   │   ├── ci.yml
│   │   ├── security.yml
│   │   └── release.yml
│   ├── CODEOWNERS
│   └── pull_request_template.md
├── .dockerignore
└── tests/
    ├── conftest.py
    ├── unit/
    ├── integration/
    └── e2e/
```

**Subtasks**:
- [ ] 0.1.1: Create `.pre-commit-config.yaml` with ruff, mypy, security checks
- [ ] 0.1.2: Create GitHub Actions CI workflow (lint, test, build)
- [ ] 0.1.3: Create GitHub Actions security workflow (Snyk, Trivy)
- [ ] 0.1.4: Create test directory structure with pytest fixtures
- [ ] 0.1.5: Create `.dockerignore` for efficient builds
- [ ] 0.1.6: Add `CODEOWNERS` and PR template

### Task 0.2: Dependency Management
```
Priority: High
Files to Modify:
├── pyproject.toml (update with all dependencies)
└── requirements/
    ├── base.txt
    ├── dev.txt
    ├── prod.txt
    └── test.txt
```

**Subtasks**:
- [ ] 0.2.1: Add all security dependencies (python-jose, passlib, bcrypt)
- [ ] 0.2.2: Add rate limiting dependencies (slowapi, redis)
- [ ] 0.2.3: Add testing dependencies (pytest-asyncio, httpx, factory-boy)
- [ ] 0.2.4: Add observability dependencies (opentelemetry-*, sentry-sdk)
- [ ] 0.2.5: Generate and commit `uv.lock`

---

## Phase 1: Authentication & Authorization (Week 1-2)
**Estimated Time**: 5-7 days
**Goal**: Complete auth system that works out-of-the-box

### Task 1.1: JWT Authentication System
```
Priority: Critical
Files to Create:
├── src/agent_service/auth/
│   ├── __init__.py
│   ├── jwt.py              # JWT creation/validation
│   ├── password.py         # Password hashing
│   ├── dependencies.py     # Auth dependencies for FastAPI
│   ├── models.py           # User, Token models
│   ├── schemas.py          # Pydantic schemas
│   └── exceptions.py       # Auth-specific exceptions
```

**Subtasks**:
- [ ] 1.1.1: Create `jwt.py` with token creation, validation, refresh logic
  ```python
  # Must include:
  - create_access_token(data, expires_delta)
  - create_refresh_token(data)
  - verify_token(token) -> TokenPayload
  - decode_token(token) -> dict
  - Token blacklist support (Redis)
  ```
- [ ] 1.1.2: Create `password.py` with bcrypt hashing
  ```python
  # Must include:
  - hash_password(plain) -> hashed
  - verify_password(plain, hashed) -> bool
  - Password strength validation
  ```
- [ ] 1.1.3: Create `dependencies.py` for FastAPI injection
  ```python
  # Must include:
  - get_current_user(token) -> User
  - get_current_active_user() -> User
  - require_permissions(*permissions)
  - optional_auth() -> User | None
  ```
- [ ] 1.1.4: Create User and Token SQLAlchemy models
- [ ] 1.1.5: Create Pydantic schemas (UserCreate, UserResponse, TokenResponse)
- [ ] 1.1.6: Create auth-specific exceptions (InvalidToken, ExpiredToken, etc.)

### Task 1.2: API Key Authentication
```
Priority: Critical
Files to Create/Modify:
├── src/agent_service/auth/
│   ├── api_key.py          # API key management
│   └── api_key_models.py   # API key storage
```

**Subtasks**:
- [ ] 1.2.1: Create API key generation with secure random bytes
- [ ] 1.2.2: Create API key hashing (never store plain text)
- [ ] 1.2.3: Create API key validation middleware
- [ ] 1.2.4: Create API key scopes/permissions system
- [ ] 1.2.5: Create API key rotation support
- [ ] 1.2.6: Add API key rate limiting (per key)

### Task 1.3: Auth Routes
```
Priority: Critical
Files to Create:
├── src/agent_service/api/routes/auth.py
```

**Subtasks**:
- [ ] 1.3.1: POST `/auth/register` - User registration
- [ ] 1.3.2: POST `/auth/login` - Get JWT tokens
- [ ] 1.3.3: POST `/auth/refresh` - Refresh access token
- [ ] 1.3.4: POST `/auth/logout` - Blacklist token
- [ ] 1.3.5: GET `/auth/me` - Get current user
- [ ] 1.3.6: POST `/auth/api-keys` - Create API key
- [ ] 1.3.7: GET `/auth/api-keys` - List user's API keys
- [ ] 1.3.8: DELETE `/auth/api-keys/{key_id}` - Revoke API key

### Task 1.4: Role-Based Access Control (RBAC)
```
Priority: High
Files to Create:
├── src/agent_service/auth/
│   ├── rbac.py             # RBAC logic
│   ├── permissions.py      # Permission definitions
│   └── roles.py            # Role definitions
```

**Subtasks**:
- [ ] 1.4.1: Define permission enum (read:agents, write:agents, admin, etc.)
- [ ] 1.4.2: Define default roles (user, developer, admin)
- [ ] 1.4.3: Create role-permission mapping
- [ ] 1.4.4: Create `require_role` decorator
- [ ] 1.4.5: Create `require_permission` decorator
- [ ] 1.4.6: Add role assignment to user registration

### Task 1.5: Auth Configuration
```
Priority: High
Files to Modify:
├── src/agent_service/config/settings.py
├── .env.example
```

**Subtasks**:
- [ ] 1.5.1: Add JWT settings (secret, algorithm, expiry times)
- [ ] 1.5.2: Add password policy settings (min length, complexity)
- [ ] 1.5.3: Add API key settings (prefix, length, expiry)
- [ ] 1.5.4: Add OAuth2 provider settings (optional, for future)
- [ ] 1.5.5: Update `.env.example` with all auth variables

### Task 1.6: Auth Tests
```
Priority: High
Files to Create:
├── tests/unit/auth/
│   ├── test_jwt.py
│   ├── test_password.py
│   └── test_rbac.py
├── tests/integration/auth/
│   └── test_auth_routes.py
```

**Subtasks**:
- [ ] 1.6.1: Unit tests for JWT creation/validation
- [ ] 1.6.2: Unit tests for password hashing
- [ ] 1.6.3: Unit tests for RBAC
- [ ] 1.6.4: Integration tests for auth routes
- [ ] 1.6.5: Test token refresh flow
- [ ] 1.6.6: Test API key authentication

---

## Phase 2: Security Hardening (Week 2)
**Estimated Time**: 4-5 days
**Goal**: Enterprise-grade security out-of-the-box

### Task 2.1: Security Headers Middleware
```
Priority: Critical
Files to Create:
├── src/agent_service/api/middleware/security.py
```

**Subtasks**:
- [ ] 2.1.1: Add X-Content-Type-Options: nosniff
- [ ] 2.1.2: Add X-Frame-Options: DENY
- [ ] 2.1.3: Add X-XSS-Protection: 1; mode=block
- [ ] 2.1.4: Add Strict-Transport-Security (HSTS)
- [ ] 2.1.5: Add Content-Security-Policy
- [ ] 2.1.6: Add Referrer-Policy
- [ ] 2.1.7: Remove server version headers

### Task 2.2: CORS Configuration
```
Priority: Critical
Files to Modify:
├── src/agent_service/api/app.py
├── src/agent_service/config/settings.py
```

**Subtasks**:
- [ ] 2.2.1: Replace `allow_origins=["*"]` with configurable list
- [ ] 2.2.2: Add environment-specific CORS settings
- [ ] 2.2.3: Add CORS preflight caching
- [ ] 2.2.4: Validate origin format in settings

### Task 2.3: Rate Limiting
```
Priority: Critical
Files to Create:
├── src/agent_service/api/middleware/rate_limit.py
├── src/agent_service/infrastructure/cache/redis.py
```

**Subtasks**:
- [ ] 2.3.1: Implement Redis-backed rate limiter using slowapi
- [ ] 2.3.2: Create rate limit tiers (free: 100/hr, pro: 1000/hr, enterprise: unlimited)
- [ ] 2.3.3: Add per-endpoint rate limits
- [ ] 2.3.4: Add per-user/API-key rate limits
- [ ] 2.3.5: Add rate limit headers (X-RateLimit-*)
- [ ] 2.3.6: Create rate limit exceeded response handler

### Task 2.4: Input Validation & Sanitization
```
Priority: Critical
Files to Create:
├── src/agent_service/api/validators/
│   ├── __init__.py
│   ├── sanitizers.py       # Input sanitization
│   ├── validators.py       # Custom validators
│   └── schemas.py          # Strict Pydantic schemas
```

**Subtasks**:
- [ ] 2.4.1: Create HTML/script sanitizer for text inputs
- [ ] 2.4.2: Create SQL injection prevention validator
- [ ] 2.4.3: Create prompt injection detection (for LLM inputs)
- [ ] 2.4.4: Add max length validators for all string inputs
- [ ] 2.4.5: Add file upload validators (type, size, content)
- [ ] 2.4.6: Create strict Pydantic models with validators

### Task 2.5: Request ID & Correlation
```
Priority: High
Files to Create:
├── src/agent_service/api/middleware/request_id.py
```

**Subtasks**:
- [ ] 2.5.1: Generate unique request ID for each request
- [ ] 2.5.2: Add request ID to all log entries
- [ ] 2.5.3: Return request ID in response headers
- [ ] 2.5.4: Support correlation ID from upstream services
- [ ] 2.5.5: Pass request ID to async tasks

### Task 2.6: Secrets Management
```
Priority: High
Files to Create:
├── src/agent_service/config/secrets.py
```

**Subtasks**:
- [ ] 2.6.1: Create secrets manager abstraction
- [ ] 2.6.2: Implement environment variable backend
- [ ] 2.6.3: Implement AWS Secrets Manager backend (optional)
- [ ] 2.6.4: Implement HashiCorp Vault backend (optional)
- [ ] 2.6.5: Add secret rotation support
- [ ] 2.6.6: Never log secrets (add masking)

### Task 2.7: Security Tests
```
Priority: High
Files to Create:
├── tests/security/
│   ├── test_headers.py
│   ├── test_cors.py
│   ├── test_rate_limit.py
│   ├── test_injection.py
│   └── test_auth_bypass.py
```

**Subtasks**:
- [ ] 2.7.1: Test security headers present
- [ ] 2.7.2: Test CORS enforcement
- [ ] 2.7.3: Test rate limiting works
- [ ] 2.7.4: Test SQL injection blocked
- [ ] 2.7.5: Test XSS blocked
- [ ] 2.7.6: Test auth bypass attempts blocked

---

## Phase 3: Logging & Observability (Week 2-3)
**Estimated Time**: 4-5 days
**Goal**: Complete visibility into system behavior

### Task 3.1: Structured Logging Enhancement
```
Priority: Critical
Files to Modify:
├── src/agent_service/infrastructure/observability/logging.py
├── src/agent_service/api/middleware/logging.py
```

**Subtasks**:
- [ ] 3.1.1: Fix middleware to use structlog (not stdlib logging)
- [ ] 3.1.2: Add request/response body logging (with PII masking)
- [ ] 3.1.3: Add user context to all logs (user_id, api_key_id)
- [ ] 3.1.4: Add request_id to all log entries
- [ ] 3.1.5: Add sensitive data masking (passwords, tokens, keys)
- [ ] 3.1.6: Configure log levels per module
- [ ] 3.1.7: Add log rotation configuration

### Task 3.2: Audit Logging
```
Priority: Critical
Files to Create:
├── src/agent_service/infrastructure/observability/audit.py
├── src/agent_service/infrastructure/database/models/audit_log.py
```

**Subtasks**:
- [ ] 3.2.1: Create AuditLog database model
  ```python
  # Fields:
  - id, timestamp, user_id, action
  - resource_type, resource_id
  - ip_address, user_agent
  - request_body (encrypted), response_status
  - changes (JSON diff for updates)
  ```
- [ ] 3.2.2: Create audit log decorator for sensitive operations
- [ ] 3.2.3: Log all auth events (login, logout, failed attempts)
- [ ] 3.2.4: Log all data modifications (create, update, delete)
- [ ] 3.2.5: Log all agent invocations
- [ ] 3.2.6: Add audit log retention policy (configurable)
- [ ] 3.2.7: Create audit log query API (admin only)

### Task 3.3: Metrics Enhancement
```
Priority: High
Files to Modify:
├── src/agent_service/infrastructure/observability/metrics.py
├── src/agent_service/api/middleware/metrics.py
```

**Subtasks**:
- [ ] 3.3.1: Add authentication metrics (logins, failures, token refreshes)
- [ ] 3.3.2: Add database connection pool metrics
- [ ] 3.3.3: Add Redis connection metrics
- [ ] 3.3.4: Add error rate metrics by type
- [ ] 3.3.5: Add queue depth metrics (if using background jobs)
- [ ] 3.3.6: Add agent execution metrics (by agent name, status)
- [ ] 3.3.7: Add tool execution metrics (by tool name, status)
- [ ] 3.3.8: Add business metrics (users, api_keys, invocations)

### Task 3.4: Distributed Tracing
```
Priority: High
Files to Modify:
├── src/agent_service/infrastructure/observability/tracing.py
├── src/agent_service/api/app.py
```

**Subtasks**:
- [ ] 3.4.1: Complete OpenTelemetry integration
- [ ] 3.4.2: Add trace context propagation
- [ ] 3.4.3: Instrument database operations
- [ ] 3.4.4: Instrument Redis operations
- [ ] 3.4.5: Instrument external HTTP calls
- [ ] 3.4.6: Instrument agent invocations
- [ ] 3.4.7: Add custom span attributes
- [ ] 3.4.8: Configure exporters (Jaeger, Zipkin, OTLP)

### Task 3.5: Error Tracking
```
Priority: High
Files to Create:
├── src/agent_service/infrastructure/observability/error_tracking.py
```

**Subtasks**:
- [ ] 3.5.1: Integrate Sentry SDK
- [ ] 3.5.2: Configure error grouping
- [ ] 3.5.3: Add user context to errors
- [ ] 3.5.4: Add request context to errors
- [ ] 3.5.5: Configure error filtering (ignore expected errors)
- [ ] 3.5.6: Add release tracking

### Task 3.6: Health Checks Enhancement
```
Priority: High
Files to Modify:
├── src/agent_service/api/routes/health.py
```

**Subtasks**:
- [ ] 3.6.1: Add `/health/live` - Kubernetes liveness probe
- [ ] 3.6.2: Add `/health/ready` - Kubernetes readiness probe
- [ ] 3.6.3: Add database connectivity check
- [ ] 3.6.4: Add Redis connectivity check
- [ ] 3.6.5: Add external service checks (if applicable)
- [ ] 3.6.6: Add `/health/startup` - Startup probe

---

## Phase 4: Database & Data Layer (Week 3)
**Estimated Time**: 4-5 days
**Goal**: Production-ready data persistence

### Task 4.1: Database Migrations
```
Priority: Critical
Files to Create:
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       └── 001_initial_schema.py
├── alembic.ini
```

**Subtasks**:
- [ ] 4.1.1: Initialize Alembic with async support
- [ ] 4.1.2: Create initial migration with all models
- [ ] 4.1.3: Add migration for User model
- [ ] 4.1.4: Add migration for API Key model
- [ ] 4.1.5: Add migration for Audit Log model
- [ ] 4.1.6: Add migration for Session model (agent sessions)
- [ ] 4.1.7: Document migration workflow

### Task 4.2: Connection Pool Configuration
```
Priority: High
Files to Modify:
├── src/agent_service/infrastructure/database/connection.py
├── src/agent_service/config/settings.py
```

**Subtasks**:
- [ ] 4.2.1: Add configurable pool size
- [ ] 4.2.2: Add max overflow configuration
- [ ] 4.2.3: Add pool timeout configuration
- [ ] 4.2.4: Add pool recycle time
- [ ] 4.2.5: Add connection health checks
- [ ] 4.2.6: Add pool metrics collection

### Task 4.3: Repository Pattern Enhancement
```
Priority: High
Files to Modify:
├── src/agent_service/infrastructure/database/repositories/base.py
```

**Subtasks**:
- [ ] 4.3.1: Add soft delete as default behavior
- [ ] 4.3.2: Add pagination helper
- [ ] 4.3.3: Add sorting helper
- [ ] 4.3.4: Add filtering helper with operators
- [ ] 4.3.5: Add bulk operations (create_many, update_many)
- [ ] 4.3.6: Add transaction context manager
- [ ] 4.3.7: Add query logging for debugging

### Task 4.4: Redis Cache Layer
```
Priority: High
Files to Create:
├── src/agent_service/infrastructure/cache/
│   ├── redis.py            # Redis connection manager
│   ├── cache.py            # Cache abstraction
│   └── decorators.py       # Caching decorators
```

**Subtasks**:
- [ ] 4.4.1: Create Redis connection manager with pooling
- [ ] 4.4.2: Create cache abstraction (get, set, delete, exists)
- [ ] 4.4.3: Create `@cached` decorator with TTL
- [ ] 4.4.4: Create cache invalidation patterns
- [ ] 4.4.5: Add cache key namespacing
- [ ] 4.4.6: Add cache metrics

### Task 4.5: Session Storage
```
Priority: High
Files to Create:
├── src/agent_service/infrastructure/database/models/session.py
├── src/agent_service/infrastructure/database/repositories/session.py
```

**Subtasks**:
- [ ] 4.5.1: Create Session model for agent conversations
  ```python
  # Fields:
  - id, user_id, agent_name
  - messages (JSONB array)
  - metadata, context
  - created_at, updated_at, expires_at
  ```
- [ ] 4.5.2: Create SessionRepository with custom queries
- [ ] 4.5.3: Add session expiry handling
- [ ] 4.5.4: Add session cleanup job

### Task 4.6: Data Layer Tests
```
Priority: High
Files to Create:
├── tests/integration/database/
│   ├── test_connection.py
│   ├── test_repositories.py
│   ├── test_migrations.py
│   └── test_cache.py
```

---

## Phase 5: API Best Practices (Week 3-4)
**Estimated Time**: 4-5 days
**Goal**: Enterprise-grade API that data scientists can extend

### Task 5.1: API Versioning
```
Priority: High
Files to Create/Modify:
├── src/agent_service/api/
│   ├── v1/
│   │   ├── __init__.py
│   │   └── router.py       # v1 routes
│   └── app.py              # Mount versioned routers
```

**Subtasks**:
- [ ] 5.1.1: Restructure routes into versioned modules
- [ ] 5.1.2: Add version prefix to all routes (`/api/v1/`)
- [ ] 5.1.3: Add deprecation header support
- [ ] 5.1.4: Document versioning strategy

### Task 5.2: Request/Response Standards
```
Priority: High
Files to Create:
├── src/agent_service/api/schemas/
│   ├── __init__.py
│   ├── base.py             # Base response schemas
│   ├── pagination.py       # Pagination schemas
│   └── errors.py           # Error response schemas
```

**Subtasks**:
- [ ] 5.2.1: Create standard success response wrapper
  ```python
  {
    "success": true,
    "data": {...},
    "meta": {"request_id": "..."}
  }
  ```
- [ ] 5.2.2: Create standard error response wrapper
  ```python
  {
    "success": false,
    "error": {
      "code": "VALIDATION_ERROR",
      "message": "...",
      "details": [...]
    },
    "meta": {"request_id": "..."}
  }
  ```
- [ ] 5.2.3: Create pagination response schema
- [ ] 5.2.4: Add response wrapper middleware

### Task 5.3: Error Handling Enhancement
```
Priority: Critical
Files to Modify:
├── src/agent_service/api/middleware/errors.py
├── src/agent_service/domain/exceptions.py
```

**Subtasks**:
- [ ] 5.3.1: Create comprehensive exception hierarchy
  ```python
  AppError
  ├── AuthError
  │   ├── InvalidCredentials
  │   ├── TokenExpired
  │   └── InsufficientPermissions
  ├── ValidationError
  │   ├── InvalidInput
  │   └── MissingField
  ├── ResourceError
  │   ├── NotFound
  │   ├── AlreadyExists
  │   └── Conflict
  ├── AgentError
  │   ├── AgentNotFound
  │   ├── InvocationFailed
  │   └── Timeout
  └── ExternalError
      ├── LLMError
      └── DatabaseError
  ```
- [ ] 5.3.2: Map exceptions to HTTP status codes
- [ ] 5.3.3: Add error logging with context
- [ ] 5.3.4: Add error tracking integration
- [ ] 5.3.5: Create user-friendly error messages

### Task 5.4: OpenAPI Enhancement
```
Priority: Medium
Files to Modify:
├── src/agent_service/api/app.py
```

**Subtasks**:
- [ ] 5.4.1: Add detailed API descriptions
- [ ] 5.4.2: Add example requests/responses
- [ ] 5.4.3: Add authentication documentation
- [ ] 5.4.4: Add error response documentation
- [ ] 5.4.5: Generate OpenAPI client SDKs

### Task 5.5: Background Jobs
```
Priority: High
Files to Create:
├── src/agent_service/workers/
│   ├── __init__.py
│   ├── celery_app.py       # Celery configuration
│   ├── tasks/
│   │   ├── __init__.py
│   │   ├── agent_tasks.py  # Long-running agent tasks
│   │   └── cleanup_tasks.py # Maintenance tasks
```

**Subtasks**:
- [ ] 5.5.1: Set up Celery with Redis broker
- [ ] 5.5.2: Create async agent invocation task
- [ ] 5.5.3: Create session cleanup task
- [ ] 5.5.4: Create audit log archival task
- [ ] 5.5.5: Add task monitoring and retry logic
- [ ] 5.5.6: Add task result backend

---

## Phase 6: Protocol Implementation (Week 4-5)
**Estimated Time**: 6-8 days
**Goal**: Complete MCP, A2A, AG-UI implementations

### Task 6.1: Protocol Registry
```
Priority: Critical
Files to Create:
├── src/agent_service/protocols/registry.py
```

**Subtasks**:
- [ ] 6.1.1: Create protocol registry (currently missing!)
- [ ] 6.1.2: Add protocol registration on startup
- [ ] 6.1.3: Add protocol discovery endpoint
- [ ] 6.1.4: Add protocol health checks

### Task 6.2: MCP Implementation
```
Priority: Critical
Files to Modify:
├── src/agent_service/protocols/mcp/
│   ├── handler.py
│   ├── server.py           # MCP server setup
│   ├── tools.py            # Tool registration
│   └── resources.py        # Resource registration
```

**Subtasks**:
- [ ] 6.2.1: Implement MCP server using FastMCP SDK
- [ ] 6.2.2: Register tools from tool registry
- [ ] 6.2.3: Implement resource providers
- [ ] 6.2.4: Implement prompt templates
- [ ] 6.2.5: Add MCP authentication
- [ ] 6.2.6: Add MCP streaming support
- [ ] 6.2.7: Add MCP tests

### Task 6.3: A2A Implementation
```
Priority: Critical
Files to Modify:
├── src/agent_service/protocols/a2a/
│   ├── handler.py
│   ├── task_manager.py     # Task lifecycle
│   ├── messages.py         # Message handling
│   └── discovery.py        # Agent discovery
```

**Subtasks**:
- [ ] 6.3.1: Implement A2A task lifecycle (created → working → completed)
- [ ] 6.3.2: Implement message handling
- [ ] 6.3.3: Implement agent card generation
- [ ] 6.3.4: Implement task persistence
- [ ] 6.3.5: Implement streaming responses
- [ ] 6.3.6: Add A2A authentication
- [ ] 6.3.7: Add A2A tests

### Task 6.4: AG-UI Implementation
```
Priority: High
Files to Modify:
├── src/agent_service/protocols/agui/
│   ├── handler.py
│   ├── events.py           # Event definitions
│   └── state.py            # State management
```

**Subtasks**:
- [ ] 6.4.1: Implement event emission (RUN_STARTED, TEXT_MESSAGE_*, etc.)
- [ ] 6.4.2: Implement state synchronization
- [ ] 6.4.3: Implement tool call events
- [ ] 6.4.4: Implement streaming responses
- [ ] 6.4.5: Add AG-UI tests

### Task 6.5: Protocol Routes
```
Priority: Critical
Files to Create:
├── src/agent_service/api/routes/protocols.py
```

**Subtasks**:
- [ ] 6.5.1: Create protocol routes (currently missing!)
- [ ] 6.5.2: Add `/.well-known/agent.json` endpoint
- [ ] 6.5.3: Add protocol-specific invoke endpoints
- [ ] 6.5.4: Add protocol-specific stream endpoints

---

## Phase 7: Agent & Tool Framework (Week 5)
**Estimated Time**: 4-5 days
**Goal**: Easy-to-use agent framework for data scientists

### Task 7.1: Agent Base Classes
```
Priority: Critical
Files to Create/Modify:
├── src/agent_service/agent/
│   ├── base.py             # Enhanced base classes
│   ├── decorators.py       # Agent decorators
│   └── context.py          # Agent execution context
```

**Subtasks**:
- [ ] 7.1.1: Create `@agent` decorator for easy agent creation
  ```python
  @agent(name="my_agent", description="...")
  async def my_agent(input: AgentInput) -> AgentOutput:
      # User's agent logic here
      pass
  ```
- [ ] 7.1.2: Create AgentContext for dependency access
  ```python
  # Provides:
  - ctx.tools (available tools)
  - ctx.db (database session)
  - ctx.cache (Redis cache)
  - ctx.logger (contextualized logger)
  - ctx.user (current user)
  ```
- [ ] 7.1.3: Create streaming helpers
- [ ] 7.1.4: Add automatic error handling
- [ ] 7.1.5: Add automatic metrics collection

### Task 7.2: Tool Framework
```
Priority: Critical
Files to Modify:
├── src/agent_service/tools/
│   ├── base.py             # Enhanced base classes
│   ├── decorators.py       # Tool decorators
│   └── builtin/            # Built-in tools
│       ├── __init__.py
│       ├── http.py         # HTTP request tool
│       ├── sql.py          # SQL query tool
│       └── search.py       # Search tool
```

**Subtasks**:
- [ ] 7.2.1: Create `@tool` decorator for easy tool creation
  ```python
  @tool(name="web_search", description="...", confirm=False)
  async def web_search(query: str) -> str:
      # User's tool logic here
      pass
  ```
- [ ] 7.2.2: Add built-in HTTP request tool
- [ ] 7.2.3: Add built-in SQL query tool (with safety)
- [ ] 7.2.4: Add automatic tool schema generation
- [ ] 7.2.5: Add tool execution timeout

### Task 7.3: Framework Integration Helpers
```
Priority: High
Files to Create:
├── src/agent_service/agent/integrations/
│   ├── __init__.py
│   ├── langgraph.py        # LangGraph adapter
│   ├── crewai.py           # CrewAI adapter
│   ├── autogen.py          # AutoGen adapter
│   └── openai.py           # OpenAI SDK adapter
```

**Subtasks**:
- [ ] 7.3.1: Create LangGraph integration helper
  ```python
  from agent_service.agent.integrations import langgraph_agent

  @langgraph_agent(graph=my_graph)
  class MyAgent(IAgent):
      pass
  ```
- [ ] 7.3.2: Create CrewAI integration helper
- [ ] 7.3.3: Create AutoGen integration helper
- [ ] 7.3.4: Create OpenAI function calling helper
- [ ] 7.3.5: Document framework integration

### Task 7.4: Agent Configuration
```
Priority: High
Files to Create:
├── src/agent_service/agent/config.py
```

**Subtasks**:
- [ ] 7.4.1: Create agent configuration schema
  ```python
  # Configurable:
  - timeout, max_tokens, temperature
  - tools (enabled/disabled)
  - permissions, rate limits
  - model selection
  ```
- [ ] 7.4.2: Support YAML agent definitions
- [ ] 7.4.3: Hot-reload agent configuration

---

## Phase 8: Deployment & Operations (Week 5-6)
**Estimated Time**: 5-6 days
**Goal**: Production-ready deployment

### Task 8.1: Docker Enhancement
```
Priority: Critical
Files to Modify:
├── docker/
│   ├── Dockerfile          # Enhanced with security
│   ├── Dockerfile.worker   # Celery worker
│   └── docker-compose.yml  # Full stack
```

**Subtasks**:
- [ ] 8.1.1: Add HEALTHCHECK to Dockerfile
- [ ] 8.1.2: Use distroless base image for production
- [ ] 8.1.3: Add security scanning in build
- [ ] 8.1.4: Create worker Dockerfile
- [ ] 8.1.5: Add resource limits to compose
- [ ] 8.1.6: Add restart policies
- [ ] 8.1.7: Add Prometheus/Grafana to compose

### Task 8.2: Kubernetes Manifests
```
Priority: High
Files to Create:
├── k8s/
│   ├── namespace.yaml
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── ingress.yaml
│   ├── configmap.yaml
│   ├── secret.yaml
│   ├── hpa.yaml            # Horizontal Pod Autoscaler
│   └── pdb.yaml            # Pod Disruption Budget
```

**Subtasks**:
- [ ] 8.2.1: Create namespace configuration
- [ ] 8.2.2: Create deployment with health probes
- [ ] 8.2.3: Create service configuration
- [ ] 8.2.4: Create ingress with TLS
- [ ] 8.2.5: Create configmaps and secrets
- [ ] 8.2.6: Create HPA for autoscaling
- [ ] 8.2.7: Create PDB for availability

### Task 8.3: Helm Chart
```
Priority: Medium
Files to Create:
├── helm/
│   ├── Chart.yaml
│   ├── values.yaml
│   └── templates/
```

**Subtasks**:
- [ ] 8.3.1: Create Helm chart structure
- [ ] 8.3.2: Parameterize all configurations
- [ ] 8.3.3: Add environment-specific values
- [ ] 8.3.4: Document Helm installation

### Task 8.4: CI/CD Pipeline
```
Priority: Critical
Files to Create:
├── .github/workflows/
│   ├── ci.yml              # Test & lint
│   ├── security.yml        # Security scanning
│   ├── build.yml           # Docker build
│   └── deploy.yml          # Deployment
```

**Subtasks**:
- [ ] 8.4.1: Create CI workflow (lint, type check, test)
- [ ] 8.4.2: Create security workflow (Snyk, Trivy, SAST)
- [ ] 8.4.3: Create Docker build workflow
- [ ] 8.4.4: Create deployment workflow (staging, production)
- [ ] 8.4.5: Add semantic versioning
- [ ] 8.4.6: Add changelog generation

### Task 8.5: Monitoring Stack
```
Priority: High
Files to Create:
├── monitoring/
│   ├── prometheus.yml
│   ├── grafana/
│   │   └── dashboards/
│   └── alertmanager.yml
```

**Subtasks**:
- [ ] 8.5.1: Configure Prometheus scraping
- [ ] 8.5.2: Create Grafana dashboards
- [ ] 8.5.3: Configure alerting rules
- [ ] 8.5.4: Add PagerDuty/Slack integration

---

## Phase 9: Documentation & Developer Experience (Week 6)
**Estimated Time**: 4-5 days
**Goal**: Data scientists can use without architecture knowledge

### Task 9.1: Quick Start Guide
```
Priority: Critical
Files to Create:
├── docs/
│   ├── quickstart.md
│   ├── installation.md
│   └── first-agent.md
```

**Subtasks**:
- [ ] 9.1.1: Write 5-minute quickstart guide
- [ ] 9.1.2: Write installation guide (local, Docker, K8s)
- [ ] 9.1.3: Write "Build Your First Agent" tutorial
- [ ] 9.1.4: Add copy-paste examples

### Task 9.2: API Reference
```
Priority: High
Files to Create:
├── docs/api/
│   ├── authentication.md
│   ├── agents.md
│   ├── tools.md
│   └── protocols.md
```

**Subtasks**:
- [ ] 9.2.1: Document all API endpoints
- [ ] 9.2.2: Add request/response examples
- [ ] 9.2.3: Document error codes
- [ ] 9.2.4: Add SDK examples (Python, JS)

### Task 9.3: Architecture Guide
```
Priority: Medium
Files to Create:
├── docs/architecture/
│   ├── overview.md
│   ├── security.md
│   └── scaling.md
```

**Subtasks**:
- [ ] 9.3.1: Document system architecture
- [ ] 9.3.2: Document security model
- [ ] 9.3.3: Document scaling strategies
- [ ] 9.3.4: Add architecture diagrams

### Task 9.4: Claude Code Integration
```
Priority: Critical
Files to Create:
├── .claude/
│   ├── commands/
│   │   ├── new-agent.md    # /new-agent command
│   │   ├── new-tool.md     # /new-tool command
│   │   └── deploy.md       # /deploy command
│   └── CLAUDE.md           # Claude Code instructions
```

**Subtasks**:
- [ ] 9.4.1: Create `/new-agent` slash command
  ```
  User: /new-agent weather-agent "Get weather for a location"
  Result: Creates complete agent with tests
  ```
- [ ] 9.4.2: Create `/new-tool` slash command
- [ ] 9.4.3: Create `/deploy` slash command
- [ ] 9.4.4: Write CLAUDE.md with project context
- [ ] 9.4.5: Add code generation templates

### Task 9.5: Example Agents
```
Priority: High
Files to Create:
├── examples/
│   ├── chatbot/            # Simple chatbot
│   ├── rag-agent/          # RAG with retrieval
│   ├── multi-agent/        # Multi-agent collaboration
│   └── tool-use/           # Tool-using agent
```

**Subtasks**:
- [ ] 9.5.1: Create simple chatbot example
- [ ] 9.5.2: Create RAG agent example
- [ ] 9.5.3: Create multi-agent example
- [ ] 9.5.4: Create tool-use example
- [ ] 9.5.5: Add README to each example

---

## Phase 10: Testing & Quality (Throughout)
**Estimated Time**: Ongoing
**Goal**: 80%+ code coverage

### Task 10.1: Unit Tests
```
Files to Create:
├── tests/unit/
│   ├── auth/
│   ├── api/
│   ├── agents/
│   ├── tools/
│   └── protocols/
```

**Coverage Targets**:
- [ ] Auth module: 90%+
- [ ] API routes: 85%+
- [ ] Agent framework: 85%+
- [ ] Tool framework: 85%+
- [ ] Protocols: 80%+

### Task 10.2: Integration Tests
```
Files to Create:
├── tests/integration/
│   ├── test_auth_flow.py
│   ├── test_agent_invocation.py
│   ├── test_protocol_handlers.py
│   └── test_database.py
```

### Task 10.3: E2E Tests
```
Files to Create:
├── tests/e2e/
│   ├── test_full_agent_flow.py
│   └── test_api_workflow.py
```

### Task 10.4: Load Tests
```
Files to Create:
├── tests/load/
│   ├── locustfile.py
│   └── k6_test.js
```

---

## Summary: Task Count by Phase

| Phase | Tasks | Subtasks | Priority | Time |
|-------|-------|----------|----------|------|
| 0. Setup | 2 | 11 | Critical | 3-4 days |
| 1. Auth | 6 | 38 | Critical | 5-7 days |
| 2. Security | 7 | 34 | Critical | 4-5 days |
| 3. Logging | 6 | 38 | Critical | 4-5 days |
| 4. Database | 6 | 29 | High | 4-5 days |
| 5. API | 5 | 25 | High | 4-5 days |
| 6. Protocols | 5 | 27 | Critical | 6-8 days |
| 7. Agent Framework | 4 | 19 | Critical | 4-5 days |
| 8. Deployment | 5 | 28 | High | 5-6 days |
| 9. Documentation | 5 | 21 | High | 4-5 days |
| 10. Testing | 4 | Ongoing | High | Ongoing |

**Total**: ~55 major tasks, ~270 subtasks
**Timeline**: 6-8 weeks with 2-3 engineers
**Investment**: ~$150-200K in engineering time

---

## Definition of "Pilot Ready"

When complete, the boilerplate will:

### For Data Scientists:
1. Clone repo and run `./scripts/dev.sh start`
2. Use Claude Code with `/new-agent my-agent "description"`
3. Write agent logic (only business logic, no infra)
4. Run `./scripts/dev.sh deploy` to production

### Infrastructure Handles:
- ✅ JWT + API key authentication
- ✅ Role-based authorization
- ✅ Rate limiting (by user, API key, endpoint)
- ✅ Security headers and CORS
- ✅ Input validation and sanitization
- ✅ Structured logging with request ID
- ✅ Audit logging for compliance
- ✅ Prometheus metrics
- ✅ Distributed tracing
- ✅ Error tracking (Sentry)
- ✅ Database migrations
- ✅ Redis caching
- ✅ Background job processing
- ✅ Health checks (live, ready, startup)
- ✅ API versioning
- ✅ MCP/A2A/AG-UI protocols
- ✅ Docker + Kubernetes deployment
- ✅ CI/CD pipeline
- ✅ Auto-scaling

### User Writes:
- Agent logic (using any framework)
- Tool implementations
- Business rules
- Custom configurations

---

## Next Steps

1. **Prioritize**: Start with Phase 1 (Auth) and Phase 2 (Security)
2. **Parallel Work**: Phase 3 (Logging) can run parallel to Phase 1-2
3. **Critical Path**: Auth → Security → Protocols → Agent Framework
4. **Continuous**: Testing throughout all phases
