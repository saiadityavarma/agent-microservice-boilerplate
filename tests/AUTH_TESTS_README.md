# Authentication Tests - Complete Test Suite

This directory contains comprehensive tests for the authentication system, covering API key management, RBAC, authentication providers, and route integration.

## Test Structure

```
tests/
├── unit/auth/
│   ├── __init__.py
│   ├── test_api_key.py       # API key utility tests
│   ├── test_rbac.py           # RBAC permission tests
│   └── test_providers.py      # Auth provider tests (Azure AD, Cognito)
└── integration/auth/
    ├── __init__.py
    └── test_auth_routes.py    # Route integration tests
```

## Running the Tests

### Prerequisites

- Python 3.11+ (as specified in pyproject.toml)
- Install dependencies: `pip install -e ".[dev]"`

### Run All Auth Tests

```bash
# Run all auth tests
pytest tests/unit/auth/ tests/integration/auth/ -v

# Run with coverage
pytest tests/unit/auth/ tests/integration/auth/ --cov=agent_service.auth --cov-report=html

# Run specific test file
pytest tests/unit/auth/test_api_key.py -v

# Run specific test class
pytest tests/unit/auth/test_api_key.py::TestAPIKeyGeneration -v

# Run specific test
pytest tests/unit/auth/test_api_key.py::TestAPIKeyGeneration::test_generate_api_key_produces_valid_format -v
```

## Test Coverage

### 1. API Key Utility Tests (`test_api_key.py`)

**Total Tests: 30+**

#### Test Classes:
- `TestAPIKeyGeneration` - API key generation functionality
- `TestAPIKeyHashing` - Key hashing operations
- `TestAPIKeyVerification` - Key verification logic
- `TestAPIKeyParsing` - Key parsing functionality
- `TestAPIKeyFormatValidation` - Format validation rules
- `TestAPIKeyIntegration` - End-to-end workflows

#### Key Test Cases:
- ✓ Generate keys with valid format (prefix_random)
- ✓ Custom prefix support (sk_live, pk_test, etc.)
- ✓ Key uniqueness across multiple generations
- ✓ Cryptographically secure randomness
- ✓ Consistent hashing (SHA256)
- ✓ Hash collision resistance
- ✓ Case-sensitive verification
- ✓ Constant-time comparison (timing attack prevention)
- ✓ Key parsing with multiple underscores
- ✓ Format validation (minimum 16-char random part)
- ✓ Complete lifecycle: generate → validate → verify

### 2. RBAC Tests (`test_rbac.py`)

**Total Tests: 40+**

#### Test Classes:
- `TestRolePermissionMappings` - Role-to-permission mappings
- `TestRoleHierarchy` - Role inheritance rules
- `TestPermissionChecking` - Permission validation logic
- `TestAzureADGroupMapping` - Azure AD group-to-role mapping
- `TestCognitoGroupMapping` - AWS Cognito group-to-role mapping
- `TestGenericRoleMapping` - Generic role string conversion
- `TestRBACServiceWithGroups` - Integration with identity providers
- `TestCustomPermissions` - User-specific permission overrides
- `TestRoleChecking` - Role validation operations

#### Key Test Cases:
- ✓ VIEWER has read-only permissions
- ✓ USER has execute permissions
- ✓ DEVELOPER has write/delete permissions
- ✓ ADMIN has user management permissions
- ✓ SUPER_ADMIN has all permissions including ADMIN_FULL
- ✓ Role hierarchy: SUPER_ADMIN → ADMIN → DEVELOPER → USER → VIEWER
- ✓ Permission inheritance through hierarchy
- ✓ Azure AD group names (AgentService.Admins, etc.)
- ✓ Cognito group names (agent-service-admins, etc.)
- ✓ Case-insensitive group matching
- ✓ Custom permissions in user metadata
- ✓ Role checking (has_role, has_any_role, has_all_roles)
- ✓ Get highest role from user's role set

### 3. Auth Provider Tests (`test_providers.py`)

**Total Tests: 25+**

#### Test Classes:

**Azure AD Provider:**
- `TestAzureADProviderConfiguration` - Configuration validation
- `TestAzureADTokenParsing` - Token verification and parsing
- `TestAzureADTokenCaching` - Token validation caching

**Cognito Provider:**
- `TestCognitoProviderConfiguration` - Configuration validation
- `TestCognitoTokenParsing` - Token verification and parsing
- `TestCognitoTokenCaching` - Token validation caching
- `TestCognitoGroupOperations` - Cognito-specific group operations

**Error Handling:**
- `TestProviderErrorHandling` - Error scenarios across providers

#### Key Test Cases:
- ✓ Azure AD provider initialization with OIDC discovery
- ✓ Missing configuration fields raise errors
- ✓ Successful JWT token verification (mocked MSAL)
- ✓ Expired token raises TokenExpiredError
- ✓ Invalid token raises InvalidTokenError
- ✓ Extract user info from Azure AD token
- ✓ Token validation caching (performance optimization)
- ✓ Signing key caching (JWKS cache)
- ✓ Cognito provider initialization (mocked boto3)
- ✓ Cognito JWT token verification
- ✓ Cognito custom roles from custom:roles claim
- ✓ Cognito groups from cognito:groups claim
- ✓ Token_use validation (id vs access token)
- ✓ JWKS caching for Cognito
- ✓ Fetch user groups via admin_list_groups_for_user
- ✓ Network errors on JWKS fetch
- ✓ Missing 'kid' in token header

### 4. Route Integration Tests (`test_auth_routes.py`)

**Total Tests: 35+**

#### Test Classes:
- `TestGetCurrentUserEndpoint` - GET /auth/me
- `TestGetUserPermissionsEndpoint` - GET /auth/permissions
- `TestCreateAPIKeyEndpoint` - POST /api/v1/auth/api-keys
- `TestListAPIKeysEndpoint` - GET /api/v1/auth/api-keys
- `TestGetAPIKeyEndpoint` - GET /api/v1/auth/api-keys/{key_id}
- `TestRevokeAPIKeyEndpoint` - DELETE /api/v1/auth/api-keys/{key_id}
- `TestRotateAPIKeyEndpoint` - POST /api/v1/auth/api-keys/{key_id}/rotate
- `TestTokenValidationEndpoint` - POST /auth/validate
- `TestUnauthorizedAccess` - 401 error scenarios
- `TestForbiddenAccess` - 403 error scenarios

#### Key Test Cases:

**User Info Routes:**
- ✓ GET /auth/me returns authenticated user info
- ✓ Returns 401 without authentication
- ✓ Works with API key authentication
- ✓ GET /auth/permissions returns roles and groups
- ✓ Includes scopes from API key metadata

**API Key CRUD:**
- ✓ Create API key with name, scopes, expiration
- ✓ Raw key returned only once in response
- ✓ Custom prefix support (pk_test, sk_live)
- ✓ List user's API keys (no raw keys in response)
- ✓ Get specific API key details
- ✓ Returns 404 for non-existent keys
- ✓ Revoke (soft delete) API key
- ✓ Key marked as deleted after revocation

**API Key Rotation:**
- ✓ Rotate key creates new key with same properties
- ✓ Old key is automatically revoked
- ✓ New raw key returned only once
- ✓ Preserves name, scopes, rate limit tier

**Authorization:**
- ✓ All endpoints return 401 without authentication
- ✓ Cannot access other users' API keys (403)
- ✓ Cannot delete other users' API keys (403)
- ✓ Cannot rotate other users' API keys (403)
- ✓ Token validation endpoint (placeholder)

## Test Fixtures

### Provided by conftest.py:
- `db_session` - Database session with automatic rollback
- `async_client` - Async HTTP client for API testing
- `test_settings` - Test configuration overrides

### Auth-specific fixtures:
- `mock_user_info` - Sample user with developer role
- `mock_admin_user_info` - Sample admin user
- `test_api_key` - Pre-created API key in database

## Mocking Strategy

### External Services Mocked:
1. **Azure AD (MSAL)**:
   - `requests.get` for OIDC discovery
   - `jwt.decode` for token validation
   - `jwt.PyJWK` for signing key conversion

2. **AWS Cognito (boto3)**:
   - `boto3.client` for Cognito client initialization
   - `jwt.decode` for token validation
   - `admin_list_groups_for_user` for group fetching

3. **Authentication Dependencies**:
   - `get_current_user_any` for injecting test users
   - `get_db_session` for database session injection

## Best Practices Demonstrated

1. **Security Testing**:
   - Raw API keys never logged or stored
   - Constant-time comparison for hash verification
   - Proper format validation before processing

2. **Error Handling**:
   - Invalid tokens raise appropriate exceptions
   - Missing configuration fields detected early
   - Network errors handled gracefully

3. **Test Isolation**:
   - Each test uses fresh database transactions
   - Mocks prevent external service calls
   - Fixtures provide clean test data

4. **Coverage**:
   - Happy path scenarios
   - Error conditions
   - Edge cases
   - Security boundaries

## Running Tests in CI/CD

```yaml
# Example GitHub Actions workflow
name: Auth Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -e ".[dev]"
      - run: pytest tests/unit/auth/ tests/integration/auth/ --cov --cov-report=xml
      - uses: codecov/codecov-action@v3
```

## Troubleshooting

### Import Errors
```bash
# Install package in development mode
pip install -e .

# Or add src to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
```

### Database Errors
```bash
# Tests use SQLite in-memory by default
# For PostgreSQL tests, set DATABASE_URL:
export DATABASE_URL="postgresql+asyncpg://user:pass@localhost/test_db"
pytest tests/integration/auth/
```

### Async Warnings
```bash
# Ensure pytest-asyncio is installed
pip install pytest-asyncio

# Check pytest.ini has:
# [tool.pytest.ini_options]
# asyncio_mode = "auto"
```

## Test Metrics

- **Total Test Count**: 130+ tests
- **Coverage Target**: >90% for auth module
- **Average Test Duration**: <1s per test
- **Integration Tests**: Use real database (SQLite in-memory)
- **Unit Tests**: Pure Python, no external dependencies

## Future Enhancements

1. **Performance Tests**: Add load testing for API key validation
2. **Security Tests**: Penetration testing for auth endpoints
3. **E2E Tests**: Full authentication flows with real tokens
4. **Benchmarks**: Token validation throughput testing
5. **Mutation Tests**: Verify test suite catches bugs

## Contributing

When adding new auth features:

1. Add unit tests in `tests/unit/auth/`
2. Add integration tests in `tests/integration/auth/`
3. Update this README with new test cases
4. Ensure coverage remains above 90%
5. Run full test suite before committing

```bash
# Run tests with coverage report
pytest tests/unit/auth/ tests/integration/auth/ \
  --cov=agent_service.auth \
  --cov-report=html \
  --cov-report=term-missing \
  --cov-fail-under=90
```
