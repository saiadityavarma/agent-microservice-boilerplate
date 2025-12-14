"""
Pydantic schemas for authentication.

This module exports all authentication-related Pydantic schemas.

Note: There is a naming conflict - both schemas.py and schemas/ directory exist.
This __init__.py acts as a bridge to re-export from both locations.
"""

# Use importlib to import the schemas.py module (not the package)
import importlib.util
import sys
from pathlib import Path

# Load the schemas.py module directly
schemas_py_path = Path(__file__).parent.parent / "schemas.py"
spec = importlib.util.spec_from_file_location("auth_schemas_module", schemas_py_path)
schemas_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(schemas_module)

# Re-export the main auth schemas from schemas.py
AuthConfig = schemas_module.AuthConfig
AuthProvider = schemas_module.AuthProvider
AzureADConfig = schemas_module.AzureADConfig
CognitoConfig = schemas_module.CognitoConfig
TokenPayload = schemas_module.TokenPayload
TokenResponse = schemas_module.TokenResponse
UserInfo = schemas_module.UserInfo

# Import API key schemas from this package
from .api_key import (
    APIKeyCreate,
    APIKeyResponse,
    APIKeyInfo,
    APIKeyParts,
    APIKeyUpdate,
    APIKeyValidation,
)

__all__ = [
    # API Key schemas
    "APIKeyCreate",
    "APIKeyResponse",
    "APIKeyInfo",
    "APIKeyParts",
    "APIKeyUpdate",
    "APIKeyValidation",
    # Auth schemas
    "AuthConfig",
    "AuthProvider",
    "AzureADConfig",
    "CognitoConfig",
    "TokenPayload",
    "TokenResponse",
    "UserInfo",
]
