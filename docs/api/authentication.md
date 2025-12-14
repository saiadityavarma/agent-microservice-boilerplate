# Authentication Guide

Complete guide to implementing authentication in your Agent Service.

## Overview

The Agent Service supports multiple authentication methods:

1. **Azure AD** - Enterprise SSO with Microsoft identity platform
2. **AWS Cognito** - AWS-managed user pools
3. **API Keys** - Simple key-based authentication
4. **None** - Disable authentication for development

## Quick Start

### Enable Authentication

```bash
# Edit .env
AUTH_PROVIDER=azure_ad  # or aws_cognito, or none

# For Azure AD
AZURE_TENANT_ID=your-tenant-id
AZURE_CLIENT_ID=your-client-id
AZURE_CLIENT_SECRET=your-client-secret

# For AWS Cognito
AWS_REGION=us-east-1
AWS_COGNITO_USER_POOL_ID=us-east-1_XXXXXXXXX
AWS_COGNITO_CLIENT_ID=your-client-id
AWS_COGNITO_CLIENT_SECRET=your-client-secret

# Restart service
docker-compose -f docker/docker-compose.yml restart api
```

## Azure AD Authentication

### Setup in Azure Portal

1. **Register Application**:
   ```
   Azure Portal → Azure Active Directory → App registrations → New registration
   ```

2. **Configure Settings**:
   - Name: `Agent Service API`
   - Supported account types: Choose based on your needs
   - Redirect URI: `https://your-domain.com/auth/callback` (optional for API)

3. **Create Client Secret**:
   ```
   App registrations → Your App → Certificates & secrets → New client secret
   ```
   Save the secret value immediately.

4. **Configure API Permissions** (optional):
   ```
   App registrations → Your App → API permissions → Add permission
   ```

5. **Get Configuration Values**:
   - Tenant ID: `App registrations → Your App → Overview`
   - Client ID: `App registrations → Your App → Overview`
   - Client Secret: From step 3

### Environment Configuration

```bash
# .env
AUTH_PROVIDER=azure_ad
AZURE_TENANT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
AZURE_CLIENT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
AZURE_CLIENT_SECRET=your-client-secret
AZURE_AUTHORITY=https://login.microsoftonline.com/{AZURE_TENANT_ID}
```

### Get Azure AD Token

```python
import requests
import msal

# Configuration
tenant_id = "your-tenant-id"
client_id = "your-client-id"
client_secret = "your-client-secret"
scope = [f"{client_id}/.default"]

# Create MSAL app
app = msal.ConfidentialClientApplication(
    client_id,
    authority=f"https://login.microsoftonline.com/{tenant_id}",
    client_credential=client_secret
)

# Get token
result = app.acquire_token_for_client(scopes=scope)

if "access_token" in result:
    token = result["access_token"]
    print(f"Token: {token}")
else:
    print(f"Error: {result.get('error_description')}")
```

### Make Authenticated Requests

```bash
# Get token first (using Azure CLI)
TOKEN=$(az account get-access-token --resource <client-id> --query accessToken -o tsv)

# Make request with token
curl -X POST http://localhost:8000/api/v1/agents/my-agent/invoke \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello",
    "session_id": "user-123"
  }'
```

### User Authentication Flow

```python
# For interactive user login
import msal

# Configuration
client_id = "your-client-id"
authority = f"https://login.microsoftonline.com/{tenant_id}"
scopes = ["User.Read"]  # Add your API scopes

# Create public client app
app = msal.PublicClientApplication(client_id, authority=authority)

# Get token interactively
result = app.acquire_token_interactive(scopes=scopes)

if "access_token" in result:
    token = result["access_token"]
    # Use token in requests
```

## AWS Cognito Authentication

### Setup in AWS Console

1. **Create User Pool**:
   ```
   AWS Console → Cognito → User pools → Create user pool
   ```

2. **Configure Sign-in Options**:
   - Username/email
   - Password requirements
   - MFA settings

3. **Create App Client**:
   ```
   User pools → Your pool → App integration → Create app client
   ```
   - App type: Confidential client (for server-to-server)
   - Generate client secret: Yes
   - Authentication flows: Enable required flows

4. **Get Configuration Values**:
   - User Pool ID: `User pools → Your pool → User pool overview`
   - App Client ID: `User pools → Your pool → App integration → App client list`
   - Region: Your AWS region

### Environment Configuration

```bash
# .env
AUTH_PROVIDER=aws_cognito
AWS_REGION=us-east-1
AWS_COGNITO_USER_POOL_ID=us-east-1_XXXXXXXXX
AWS_COGNITO_CLIENT_ID=your-client-id
AWS_COGNITO_CLIENT_SECRET=your-client-secret
```

### Get Cognito Token

**Server-to-Server (Client Credentials)**:

```python
import boto3
import base64
import hmac
import hashlib

client = boto3.client('cognito-idp', region_name='us-east-1')

# Calculate secret hash
def get_secret_hash(username, client_id, client_secret):
    message = bytes(username + client_id, 'utf-8')
    secret = bytes(client_secret, 'utf-8')
    dig = hmac.new(secret, msg=message, digestmod=hashlib.sha256).digest()
    return base64.b64encode(dig).decode()

# Authenticate
response = client.initiate_auth(
    ClientId='your-client-id',
    AuthFlow='USER_PASSWORD_AUTH',
    AuthParameters={
        'USERNAME': 'user@example.com',
        'PASSWORD': 'password',
        'SECRET_HASH': get_secret_hash('user@example.com', 'client-id', 'client-secret')
    }
)

token = response['AuthenticationResult']['AccessToken']
print(f"Token: {token}")
```

**User Sign-up and Login**:

```python
import boto3

client = boto3.client('cognito-idp', region_name='us-east-1')

# Sign up new user
response = client.sign_up(
    ClientId='your-client-id',
    Username='user@example.com',
    Password='SecurePassword123!',
    UserAttributes=[
        {'Name': 'email', 'Value': 'user@example.com'},
        {'Name': 'name', 'Value': 'John Doe'}
    ]
)

# Confirm sign-up (after receiving confirmation code)
client.confirm_sign_up(
    ClientId='your-client-id',
    Username='user@example.com',
    ConfirmationCode='123456'
)
```

### Make Authenticated Requests

```bash
# Get token using AWS CLI
TOKEN=$(aws cognito-idp initiate-auth \
  --client-id your-client-id \
  --auth-flow USER_PASSWORD_AUTH \
  --auth-parameters USERNAME=user@example.com,PASSWORD=password \
  --query 'AuthenticationResult.AccessToken' \
  --output text)

# Make request
curl -X POST http://localhost:8000/api/v1/agents/my-agent/invoke \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello", "session_id": "user-123"}'
```

## API Key Authentication

### Create API Key

```bash
# Using API endpoint
curl -X POST http://localhost:8000/api/v1/auth/api-keys \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Production Key",
    "expires_in_days": 365,
    "scopes": ["agents:read", "agents:write"]
  }'
```

Response:
```json
{
  "key_id": "sk_live_abc123...",
  "key": "sk_live_abc123def456...",
  "name": "Production Key",
  "expires_at": "2025-12-14T00:00:00Z",
  "scopes": ["agents:read", "agents:write"]
}
```

**IMPORTANT**: Save the `key` value immediately - it will not be shown again!

### Use API Key

```bash
# Make request with API key
curl -X POST http://localhost:8000/api/v1/agents/my-agent/invoke \
  -H "X-API-Key: sk_live_abc123def456..." \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello", "session_id": "user-123"}'
```

### Manage API Keys

```bash
# List all keys
curl http://localhost:8000/api/v1/auth/api-keys \
  -H "X-API-Key: your-admin-key"

# Revoke a key
curl -X DELETE http://localhost:8000/api/v1/auth/api-keys/sk_live_abc123 \
  -H "X-API-Key: your-admin-key"

# Rotate a key
curl -X POST http://localhost:8000/api/v1/auth/api-keys/sk_live_abc123/rotate \
  -H "X-API-Key: your-admin-key"
```

### Programmatic API Key Creation

```python
# src/agent_service/auth/services/api_key_service.py
from agent_service.auth.services import APIKeyService
from agent_service.auth.schemas import CreateAPIKeyRequest

service = APIKeyService()

# Create key
key = await service.create_api_key(CreateAPIKeyRequest(
    name="My Application",
    expires_in_days=90,
    scopes=["agents:read", "agents:write"]
))

print(f"Key: {key.key}")  # Save this securely
print(f"Key ID: {key.key_id}")
```

## Role-Based Access Control (RBAC)

### Define Roles and Permissions

```python
# src/agent_service/auth/rbac/roles.py
from agent_service.auth.rbac import Role, Permission

# Built-in roles
ADMIN = Role(
    name="admin",
    permissions=[
        Permission.AGENTS_READ,
        Permission.AGENTS_WRITE,
        Permission.AGENTS_DELETE,
        Permission.TOOLS_READ,
        Permission.TOOLS_WRITE,
        Permission.TOOLS_DELETE,
        Permission.USERS_MANAGE
    ]
)

DEVELOPER = Role(
    name="developer",
    permissions=[
        Permission.AGENTS_READ,
        Permission.AGENTS_WRITE,
        Permission.TOOLS_READ,
        Permission.TOOLS_WRITE
    ]
)

READ_ONLY = Role(
    name="read_only",
    permissions=[
        Permission.AGENTS_READ,
        Permission.TOOLS_READ
    ]
)
```

### Protect Endpoints with RBAC

```python
# src/agent_service/api/routes/agents.py
from fastapi import APIRouter, Depends
from agent_service.auth.rbac import require_permission, Permission
from agent_service.auth.dependencies import get_current_user

router = APIRouter()

@router.post("/agents/{agent_name}/invoke")
@require_permission(Permission.AGENTS_WRITE)
async def invoke_agent(
    agent_name: str,
    request: AgentRequest,
    user = Depends(get_current_user)
):
    # User has been authenticated and authorized
    # Proceed with agent invocation
    pass

@router.delete("/agents/{agent_name}")
@require_permission(Permission.AGENTS_DELETE)
async def delete_agent(
    agent_name: str,
    user = Depends(get_current_user)
):
    # Only users with AGENTS_DELETE permission can access
    pass
```

### Assign Roles to Users

```python
from agent_service.auth.rbac import assign_role

# Assign role to user
await assign_role(user_id="user-123", role=DEVELOPER)

# Check permissions
from agent_service.auth.rbac import has_permission

if await has_permission(user_id="user-123", permission=Permission.AGENTS_WRITE):
    # User can write agents
    pass
```

## Token Validation

### How Tokens are Validated

1. **JWT Signature**: Verify using provider's public keys
2. **Expiration**: Check `exp` claim
3. **Audience**: Verify `aud` matches your client ID
4. **Issuer**: Verify `iss` matches provider
5. **Cache**: Cache validation results to reduce overhead

### Custom Token Validation

```python
# src/agent_service/auth/validators/custom.py
from agent_service.auth.providers.base import BaseAuthProvider

class CustomAuthProvider(BaseAuthProvider):
    async def verify_token(self, token: str) -> dict:
        """Custom token verification logic."""
        # Decode token
        payload = jwt.decode(
            token,
            self.public_key,
            algorithms=["RS256"],
            audience=self.client_id
        )

        # Custom validation
        if payload.get("custom_claim") != "expected_value":
            raise AuthenticationError("Invalid custom claim")

        return {
            "user_id": payload["sub"],
            "email": payload.get("email"),
            "roles": payload.get("roles", [])
        }
```

## Security Best Practices

### 1. Always Use HTTPS in Production

```yaml
# k8s/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/force-ssl-redirect: "true"
```

### 2. Rotate Secrets Regularly

```bash
# Rotate Azure AD client secret every 90 days
# Rotate API keys every 180 days
# Rotate SECRET_KEY annually
```

### 3. Use Strong Secret Keys

```python
import secrets

# Generate strong secret key
secret_key = secrets.token_urlsafe(32)
print(f"SECRET_KEY={secret_key}")
```

### 4. Implement Rate Limiting

```python
# Automatic rate limiting on auth endpoints
# See .env.rate_limiting.example for configuration
AUTH_RATE_LIMIT=10/minute
```

### 5. Monitor Authentication Events

```python
from agent_service.infrastructure.observability import audit_log

await audit_log(
    event_type="auth.login",
    user_id=user_id,
    metadata={
        "provider": "azure_ad",
        "ip_address": request.client.host,
        "success": True
    }
)
```

### 6. Secure Token Storage

```javascript
// Frontend: Never store tokens in localStorage
// Use httpOnly cookies or secure session storage

// Set token in httpOnly cookie (server-side)
response.set_cookie(
    key="access_token",
    value=token,
    httponly=True,
    secure=True,  # HTTPS only
    samesite="strict",
    max_age=3600
)
```

## Testing Authentication

### Test with Mock Tokens

```python
# tests/conftest.py
import pytest
from unittest.mock import patch

@pytest.fixture
def mock_auth():
    """Mock authentication for testing."""
    with patch('agent_service.auth.dependencies.get_current_user') as mock:
        mock.return_value = {
            "user_id": "test-user",
            "email": "test@example.com",
            "roles": ["developer"]
        }
        yield mock

# tests/integration/test_agents.py
def test_invoke_agent_authenticated(client, mock_auth):
    response = client.post(
        "/api/v1/agents/test-agent/invoke",
        json={"message": "Hello", "session_id": "test"}
    )
    assert response.status_code == 200
```

### Test Auth Flows

```python
# tests/integration/auth/test_auth_flows.py
import pytest

@pytest.mark.asyncio
async def test_azure_ad_token_validation():
    """Test Azure AD token validation."""
    from agent_service.auth.providers.azure_ad import AzureADProvider

    provider = AzureADProvider()

    # Test with valid token
    valid_token = "eyJ..."  # Real or mocked token
    user_info = await provider.verify_token(valid_token)

    assert user_info["user_id"]
    assert user_info["email"]

@pytest.mark.asyncio
async def test_api_key_validation():
    """Test API key validation."""
    from agent_service.auth.services import APIKeyService

    service = APIKeyService()

    # Create test key
    key = await service.create_api_key(name="Test Key")

    # Validate key
    is_valid = await service.validate_key(key.key)
    assert is_valid

    # Revoke key
    await service.revoke_key(key.key_id)

    # Should be invalid now
    is_valid = await service.validate_key(key.key)
    assert not is_valid
```

## Troubleshooting

### Token Validation Failures

```bash
# Check token expiration
python -c "
import jwt
token = 'your-token'
decoded = jwt.decode(token, options={'verify_signature': False})
print('Expires:', decoded.get('exp'))
print('Issued:', decoded.get('iat'))
"

# Verify token audience
# Should match your AZURE_CLIENT_ID or AWS_COGNITO_CLIENT_ID
```

### Azure AD Issues

```bash
# Test Azure AD configuration
curl https://login.microsoftonline.com/{TENANT_ID}/v2.0/.well-known/openid-configuration

# Verify token endpoint
curl -X POST https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token \
  -d "client_id={CLIENT_ID}" \
  -d "client_secret={CLIENT_SECRET}" \
  -d "scope={CLIENT_ID}/.default" \
  -d "grant_type=client_credentials"
```

### Cognito Issues

```bash
# Test Cognito endpoint
aws cognito-idp describe-user-pool --user-pool-id us-east-1_XXXXXXXXX

# Verify user exists
aws cognito-idp admin-get-user \
  --user-pool-id us-east-1_XXXXXXXXX \
  --username user@example.com
```

### API Key Issues

```bash
# Check if key exists in database
docker-compose exec postgres psql -U postgres -d agent_db \
  -c "SELECT * FROM api_keys WHERE key_id = 'sk_live_abc123';"

# Check key hash
# API keys are stored as hashes - raw keys are never stored
```

## Examples

### Complete Authentication Examples

See `/Users/saiadityavarmavuppalapati/Downloads/agents_boiler_plate/examples/` for complete examples:

- `auth_azure_ad.py` - Azure AD authentication flow
- `auth_cognito.py` - AWS Cognito authentication flow
- `auth_api_keys.py` - API key management
- `auth_rbac.py` - RBAC implementation

## Next Steps

- [Agent API Reference](./agents.md) - Learn about agent endpoints
- [Tool System](./tools.md) - Add tools to your agents
- [Protocols](./protocols.md) - Implement MCP, A2A, AG-UI
