"""
API v1 router aggregator.

This module aggregates all v1 API routes into a single router
that can be mounted at /api/v1 in the main application.

Routes included in v1:
    - /agents - Agent invocation and streaming
    - /auth/api-keys - API key management
    - /protocols - Protocol handlers (A2A, MCP, etc.)
    - /admin/audit - Audit log queries (admin only)

Routes NOT versioned (kept at root level):
    - /health/* - Health check endpoints
    - /auth/me - Current user info
    - /auth/permissions - User permissions
    - /auth/validate - Token validation
"""

from fastapi import APIRouter

from agent_service.api.routes import agents, auth, protocols, audit


# Create main v1 router
router = APIRouter()

# ============================================================================
# Include v1 routes
# ============================================================================

# Agent routes: /api/v1/agents/*
router.include_router(
    agents.router,
    prefix="/agents",
    tags=["Agents"]
)

# API key management routes: /api/v1/auth/api-keys/*
# Note: The api_keys_router already has prefix="/api/v1/auth/api-keys"
# We need to remove that prefix and add it here instead
from agent_service.api.routes.auth import api_keys_router
# Create a new router without the prefix
api_keys_router_v1 = APIRouter()
# Copy routes from api_keys_router to new router
for route in api_keys_router.routes:
    api_keys_router_v1.routes.append(route)

router.include_router(
    api_keys_router_v1,
    prefix="/auth/api-keys",
    tags=["API Keys"]
)

# Protocol routes: /api/v1/protocols/*
router.include_router(
    protocols.router,
    prefix="/protocols",
    tags=["Protocols"]
)

# Audit routes: /api/v1/admin/audit/*
router.include_router(
    audit.router,
    prefix="/admin/audit",
    tags=["Audit Logs"]
)


# ============================================================================
# Router export
# ============================================================================

__all__ = ["router"]
