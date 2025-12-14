"""
Example test/demo script for FastAPI authentication dependencies.

This demonstrates how to use the authentication dependencies in a real FastAPI application.
"""

from fastapi import FastAPI, Depends, APIRouter
from fastapi.testclient import TestClient
from typing import Optional

# Import authentication dependencies
from agent_service.auth.dependencies import (
    get_current_user,
    get_current_user_from_api_key,
    get_current_user_any,
    optional_auth,
    require_roles,
    require_permissions,
    require_scopes,
    RoleChecker,
    PermissionChecker,
    ScopeChecker,
    set_auth_provider,
)
from agent_service.auth.schemas import UserInfo, AuthProvider


# Mock authentication provider for testing
class MockAuthProvider:
    """Mock auth provider for testing purposes."""

    def get_user_info(self, token: str) -> UserInfo:
        """Return mock user info based on token."""
        if token == "admin-token":
            return UserInfo(
                id="admin-123",
                email="admin@example.com",
                name="Admin User",
                roles=["admin", "user"],
                groups=["admins"],
                provider=AuthProvider.CUSTOM,
                metadata={"permissions": ["users:read", "users:write", "users:delete"]},
            )
        elif token == "user-token":
            return UserInfo(
                id="user-456",
                email="user@example.com",
                name="Regular User",
                roles=["user"],
                groups=["users"],
                provider=AuthProvider.CUSTOM,
                metadata={"permissions": ["users:read"]},
            )
        else:
            raise ValueError("Invalid token")

    def get_provider_name(self) -> str:
        return "mock"


# Create FastAPI app
app = FastAPI(title="Auth Dependencies Demo")
router = APIRouter()


# Set up mock auth provider
@app.on_event("startup")
async def startup():
    set_auth_provider(MockAuthProvider())


# ============================================================================
# Example Routes
# ============================================================================


@router.get("/public")
async def public_route():
    """Public route - no authentication required."""
    return {"message": "This is a public route"}


@router.get("/me")
async def get_me(user: UserInfo = Depends(get_current_user)):
    """Protected route - requires JWT token."""
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "roles": user.roles,
    }


@router.get("/optional")
async def optional_route(user: Optional[UserInfo] = Depends(optional_auth)):
    """Route with optional authentication."""
    if user:
        return {"message": f"Hello, {user.name}", "authenticated": True}
    return {"message": "Hello, anonymous", "authenticated": False}


@router.get("/admin")
async def admin_only(
    user: UserInfo = Depends(get_current_user),
    _: None = Depends(require_roles("admin")),
):
    """Admin-only route."""
    return {"message": "Admin access granted", "user": user.email}


@router.get("/staff")
async def staff_route(
    user: UserInfo = Depends(get_current_user),
    _: None = Depends(require_roles("admin", "staff", "moderator")),
):
    """Route accessible by admin, staff, or moderator."""
    return {"message": "Staff access granted", "user": user.email}


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    user: UserInfo = Depends(get_current_user),
    _: None = Depends(require_permissions("users:delete")),
):
    """Delete user - requires specific permission."""
    return {"deleted": user_id, "deleted_by": user.email}


# Add router to app
app.include_router(router)


# ============================================================================
# Test Cases
# ============================================================================


def test_public_route():
    """Test public route - no auth required."""
    client = TestClient(app)
    response = client.get("/public")
    assert response.status_code == 200
    assert response.json()["message"] == "This is a public route"
    print("✓ Public route test passed")


def test_protected_route_with_token():
    """Test protected route with valid token."""
    client = TestClient(app)
    response = client.get("/me", headers={"Authorization": "Bearer user-token"})
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "user@example.com"
    print("✓ Protected route with token test passed")


def test_protected_route_without_token():
    """Test protected route without token."""
    client = TestClient(app)
    response = client.get("/me")
    assert response.status_code == 401
    assert "WWW-Authenticate" in response.headers
    print("✓ Protected route without token test passed")


def test_optional_auth_with_token():
    """Test optional auth with token."""
    client = TestClient(app)
    response = client.get("/optional", headers={"Authorization": "Bearer user-token"})
    assert response.status_code == 200
    data = response.json()
    assert data["authenticated"] is True
    assert "Regular User" in data["message"]
    print("✓ Optional auth with token test passed")


def test_optional_auth_without_token():
    """Test optional auth without token."""
    client = TestClient(app)
    response = client.get("/optional")
    assert response.status_code == 200
    data = response.json()
    assert data["authenticated"] is False
    assert "anonymous" in data["message"]
    print("✓ Optional auth without token test passed")


def test_admin_route_with_admin():
    """Test admin route with admin token."""
    client = TestClient(app)
    response = client.get("/admin", headers={"Authorization": "Bearer admin-token"})
    assert response.status_code == 200
    print("✓ Admin route with admin token test passed")


def test_admin_route_with_user():
    """Test admin route with regular user token."""
    client = TestClient(app)
    response = client.get("/admin", headers={"Authorization": "Bearer user-token"})
    assert response.status_code == 403
    assert "admin" in response.json()["detail"].lower()
    print("✓ Admin route with user token test passed (correctly denied)")


def test_permission_check_with_permission():
    """Test permission check with required permission."""
    client = TestClient(app)
    response = client.delete(
        "/users/123", headers={"Authorization": "Bearer admin-token"}
    )
    assert response.status_code == 200
    print("✓ Permission check with permission test passed")


def test_permission_check_without_permission():
    """Test permission check without required permission."""
    client = TestClient(app)
    response = client.delete(
        "/users/123", headers={"Authorization": "Bearer user-token"}
    )
    assert response.status_code == 403
    print("✓ Permission check without permission test passed (correctly denied)")


def run_all_tests():
    """Run all test cases."""
    print("\nRunning authentication dependency tests...\n")

    test_public_route()
    test_protected_route_with_token()
    test_protected_route_without_token()
    test_optional_auth_with_token()
    test_optional_auth_without_token()
    test_admin_route_with_admin()
    test_admin_route_with_user()
    test_permission_check_with_permission()
    test_permission_check_without_permission()

    print("\n✓ All tests passed!\n")


if __name__ == "__main__":
    run_all_tests()
