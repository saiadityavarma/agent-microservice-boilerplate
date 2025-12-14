# Security Tests

Comprehensive security test suite for the Agent Service application.

## Overview

This directory contains security-focused tests that verify the application's defenses against common security vulnerabilities and attack vectors.

## Test Files

### 1. `test_headers.py` - Security Headers Tests

Tests for the SecurityHeadersMiddleware to ensure all security headers are properly configured.

**Coverage:**
- ✓ All security headers present (X-Content-Type-Options, X-Frame-Options, X-XSS-Protection, CSP, etc.)
- ✓ HSTS only enabled in production environments
- ✓ Server header removed to prevent information disclosure
- ✓ Content Security Policy properly configured
- ✓ Referrer Policy set correctly
- ✓ Permissions Policy restricts sensitive features
- ✓ Security headers present on all endpoints (including error responses)

**Key Test Classes:**
- `TestSecurityHeaders` - Basic header presence and values
- `TestHSTSHeader` - HSTS behavior in different environments
- `TestSecurityHeadersOnAllEndpoints` - Headers on various routes
- `TestCSPConfiguration` - Content Security Policy settings
- `TestSecurityHeadersConfiguration` - Configuration options

### 2. `test_cors.py` - CORS Tests

Tests for CORS middleware to ensure proper origin validation and cross-origin resource sharing.

**Coverage:**
- ✓ CORS blocks unauthorized origins
- ✓ CORS allows configured origins
- ✓ Preflight OPTIONS requests work correctly
- ✓ Credentials handling (no wildcard with credentials=true)
- ✓ Method validation
- ✓ Header validation
- ✓ Max-age configuration
- ✓ Production-safe configuration

**Key Test Classes:**
- `TestCORSOriginValidation` - Origin whitelist enforcement
- `TestCORSPreflightRequests` - OPTIONS request handling
- `TestCORSCredentialsHandling` - Credentials flag security
- `TestCORSMethodValidation` - HTTP method restrictions
- `TestCORSConfiguration` - Settings and defaults
- `TestCORSSecurityBestPractices` - Security recommendations
- `TestCORSProductionConfiguration` - Production environment settings

### 3. `test_rate_limit.py` - Rate Limiting Tests

Tests for rate limiting middleware using slowapi and Redis backend.

**Coverage:**
- ✓ Rate limit enforcement blocks excessive requests
- ✓ 429 response when limit exceeded
- ✓ Rate limit headers returned (X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset)
- ✓ Retry-After header on 429 responses
- ✓ Different tiers have different limits (free, pro, enterprise)
- ✓ Per-user/IP rate limiting (not global)
- ✓ Different endpoints can have different limits
- ✓ Redis and in-memory storage support

**Key Test Classes:**
- `TestRateLimitEnforcement` - Basic rate limiting
- `TestRateLimitHeaders` - Response headers
- `TestRateLimitTiers` - Tier-based limits
- `TestRateLimitKeyFunctions` - Key extraction (user, API key, IP)
- `TestRateLimitErrorResponse` - 429 response format
- `TestRateLimitConfiguration` - Settings and storage backends
- `TestRateLimitByEndpoint` - Per-endpoint limits
- `TestRateLimitSecurityBestPractices` - Security patterns

### 4. `test_injection.py` - Injection Attack Tests

Tests for protection against various injection attacks.

**Coverage:**
- ✓ SQL injection patterns blocked/escaped
- ✓ XSS patterns sanitized (script tags, event handlers, javascript: protocol)
- ✓ Prompt injection detection
- ✓ Path traversal blocked (../, absolute paths, hidden files)
- ✓ Null byte injection blocked
- ✓ Control characters removed
- ✓ HTML sanitization with whitelist support
- ✓ Unicode and polyglot attacks handled

**Key Test Classes:**
- `TestSQLInjectionProtection` - SQL injection defenses
- `TestXSSProtection` - Cross-site scripting defenses
- `TestPromptInjectionDetection` - LLM prompt injection
- `TestPathTraversalProtection` - File path attacks
- `TestNullByteInjection` - Null byte attacks
- `TestInputSanitizationIntegration` - API endpoint integration
- `TestAdvancedInjectionPatterns` - Polyglot and encoding attacks
- `TestSanitizerEdgeCases` - Edge cases and error handling

### 5. `test_auth_bypass.py` - Authentication & Authorization Tests

Tests for authentication and authorization security.

**Coverage:**
- ✓ Routes require authentication
- ✓ Invalid tokens rejected (malformed, wrong signature, missing Bearer prefix)
- ✓ Expired tokens rejected with proper error messages
- ✓ API key validation (invalid, expired, revoked)
- ✓ RBAC enforcement (role checking, permission checking)
- ✓ Scope validation for API keys
- ✓ JWT 'none' algorithm attack prevented
- ✓ Multiple authentication methods (Bearer token, API key)
- ✓ Error responses don't leak information

**Key Test Classes:**
- `TestRouteProtection` - Protected route access control
- `TestInvalidTokenRejection` - Token validation
- `TestExpiredTokenRejection` - Expiration handling
- `TestAPIKeyValidation` - API key security
- `TestRBACEnforcement` - Role-based access control
- `TestPermissionEnforcement` - Permission-based access
- `TestScopeValidation` - API key scopes
- `TestAuthenticationBypass` - Bypass prevention
- `TestAuthenticationErrorResponses` - Error handling
- `TestMultipleAuthMethods` - Multi-method auth

## Fixtures (conftest.py)

The `conftest.py` file provides comprehensive fixtures for security testing:

### Authentication Fixtures
- `valid_jwt_token` - Valid JWT token for testing
- `expired_jwt_token` - Expired JWT token
- `admin_jwt_token` - Admin user token
- `valid_api_key` - Valid API key
- `mock_user_regular` - Regular user UserInfo
- `mock_user_admin` - Admin user UserInfo
- `mock_user_moderator` - Moderator user UserInfo
- `mock_api_key_user` - API key user UserInfo

### HTTP Client Fixtures
- `unauthenticated_client` - Client without auth headers
- `authenticated_client` - Client with valid JWT
- `admin_client` - Client authenticated as admin
- `api_key_client` - Client with API key auth
- `expired_token_client` - Client with expired token

### Helper Fixtures
- `injection_payloads` - Common injection attack payloads
- `cors_origins` - CORS test origins (allowed/blocked)
- `rate_limit_tier_users` - Users with different rate limit tiers

## Running the Tests

### Run all security tests:
```bash
pytest tests/security/ -v
```

### Run specific test file:
```bash
pytest tests/security/test_headers.py -v
pytest tests/security/test_cors.py -v
pytest tests/security/test_rate_limit.py -v
pytest tests/security/test_injection.py -v
pytest tests/security/test_auth_bypass.py -v
```

### Run specific test class:
```bash
pytest tests/security/test_headers.py::TestSecurityHeaders -v
pytest tests/security/test_cors.py::TestCORSOriginValidation -v
```

### Run specific test:
```bash
pytest tests/security/test_headers.py::TestSecurityHeaders::test_all_security_headers_present -v
```

### Run with coverage:
```bash
pytest tests/security/ --cov=agent_service.api.middleware --cov=agent_service.auth --cov=agent_service.api.validators
```

### Run with security report:
```bash
pytest tests/security/ -v --tb=short --maxfail=1
```

## Test Configuration

Tests use the following configuration from `pytest.ini`:
- Async mode: auto (pytest-asyncio)
- Markers: asyncio, slow, integration
- Coverage settings from `pyproject.toml`

## Dependencies

Security tests require:
- `pytest>=8.0.0`
- `pytest-asyncio>=0.23.0`
- `httpx>=0.28.0` - Async HTTP client
- `PyJWT>=2.10.1` - JWT token generation for testing
- `slowapi>=0.1.9` - Rate limiting (tested component)

## Security Testing Best Practices

### 1. Test Both Positive and Negative Cases
- Test that valid input is accepted
- Test that invalid/malicious input is rejected

### 2. Test Boundary Conditions
- Empty strings
- Very long inputs
- Special characters
- Unicode characters
- Null bytes

### 3. Test Error Responses
- Verify error messages don't leak sensitive information
- Check proper HTTP status codes (401, 403, 429)
- Ensure WWW-Authenticate headers are present

### 4. Test Defense in Depth
- Test each security layer independently
- Test combinations of security mechanisms
- Verify fallback behavior

### 5. Test Configuration
- Test security features can be configured
- Test default settings are secure
- Test production vs development differences

## Common Attack Vectors Tested

### Injection Attacks
- SQL Injection: `' OR '1'='1`, `'; DROP TABLE users; --`
- XSS: `<script>alert(1)</script>`, `<img src=x onerror='alert(1)'>`
- Path Traversal: `../../etc/passwd`, `....//etc/passwd`
- Command Injection: `; ls -la`, `| cat /etc/passwd`
- Null Byte: `file.txt\x00.exe`

### Authentication Bypass
- JWT 'none' algorithm attack
- Token signature manipulation
- Expired token reuse
- Header injection: `Bearer token\r\nX-Admin: true`

### Authorization Bypass
- Role escalation attempts
- Permission boundary testing
- Scope validation bypass

### Rate Limiting Bypass
- Distributed attacks (tested via key functions)
- Header manipulation
- IP spoofing (prevented by proper key extraction)

## Integration with CI/CD

Security tests should run in CI/CD pipeline:

```yaml
# Example GitHub Actions
- name: Run Security Tests
  run: |
    pytest tests/security/ -v --cov --cov-report=xml

- name: Security Test Report
  uses: codecov/codecov-action@v3
  with:
    files: ./coverage.xml
    flags: security-tests
```

## Notes

1. **Rate Limiting Tests**: Some rate limit tests may be flaky depending on timing. They use low limits (1-3 requests) to avoid long test times.

2. **Authentication Tests**: Tests use mock tokens and providers. Real OAuth/OIDC provider tests would require integration test environment.

3. **Production Settings**: Some tests verify production-specific behavior (e.g., HSTS only in production). These use mocked settings.

4. **Redis Dependency**: Rate limit tests work with or without Redis. They automatically skip if Redis is not available.

5. **Performance**: Security tests are generally fast (<1s each) except for rate limiting tests which may take longer due to time windows.

## Adding New Security Tests

When adding new security features, follow this pattern:

1. Create tests in the appropriate file or create a new test file
2. Use descriptive test class and method names
3. Add fixtures to `conftest.py` if reusable
4. Document the attack vector being tested
5. Test both positive (allowed) and negative (blocked) cases
6. Update this README with new coverage

## Security Test Checklist

When implementing a new security feature:

- [ ] Authentication tests
- [ ] Authorization tests (RBAC/permissions)
- [ ] Input validation tests
- [ ] Output encoding tests
- [ ] Rate limiting tests
- [ ] CORS/CSP configuration tests
- [ ] Error handling tests (no information leakage)
- [ ] Configuration tests (secure defaults)
- [ ] Integration tests (end-to-end)
- [ ] Documentation updates

## References

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [OWASP Testing Guide](https://owasp.org/www-project-web-security-testing-guide/)
- [CWE Top 25](https://cwe.mitre.org/top25/)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
