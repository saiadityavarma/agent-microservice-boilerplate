"""
Input validation and sanitization package.

This package provides comprehensive input validation and sanitization
utilities for securing API endpoints against common attacks including:
- XSS (Cross-Site Scripting)
- SQL Injection
- Path Traversal
- Prompt Injection
- Null Byte Injection

Usage:
    from agent_service.api.validators import (
        sanitize_html,
        validate_prompt_injection,
        SanitizedString,
        StrictBaseModel,
    )

    # Sanitize user input
    clean_text = sanitize_html(user_input)

    # Validate for security issues
    is_safe = validate_prompt_injection(prompt_text)

    # Use in Pydantic models
    class MyModel(StrictBaseModel):
        user_text: SanitizedString
"""

# Sanitizers
from .sanitizers import (
    sanitize_html,
    sanitize_sql,
    strip_null_bytes,
    normalize_whitespace,
    truncate_string,
    sanitize_filename,
    sanitize_email,
    remove_control_characters,
    sanitize_json_string,
)

# Validators
from .validators import (
    validate_prompt_injection,
    validate_no_scripts,
    validate_safe_path,
    validate_uuid,
    validate_email,
    validate_url,
    validate_alphanumeric,
    validate_length,
)

# Schemas
from .schemas import (
    # Base models
    StrictBaseModel,
    PermissiveBaseModel,
    # Custom string types
    SanitizedString,
    SafeText,
    NoScriptString,
    BoundedString,
    # Predefined types
    Username,
    Email,
    UUID,
    Url,
    # Input schemas
    ValidatedTextInput,
    SanitizedHtmlInput,
    SafePathInput,
    UuidInput,
    EmailInput,
    UrlInput,
    PaginationParams,
    BoundedListInput,
    SecureAgentPrompt,
)


__all__ = [
    # Sanitizers
    'sanitize_html',
    'sanitize_sql',
    'strip_null_bytes',
    'normalize_whitespace',
    'truncate_string',
    'sanitize_filename',
    'sanitize_email',
    'remove_control_characters',
    'sanitize_json_string',
    # Validators
    'validate_prompt_injection',
    'validate_no_scripts',
    'validate_safe_path',
    'validate_uuid',
    'validate_email',
    'validate_url',
    'validate_alphanumeric',
    'validate_length',
    # Base models
    'StrictBaseModel',
    'PermissiveBaseModel',
    # Custom string types
    'SanitizedString',
    'SafeText',
    'NoScriptString',
    'BoundedString',
    # Predefined types
    'Username',
    'Email',
    'UUID',
    'Url',
    # Input schemas
    'ValidatedTextInput',
    'SanitizedHtmlInput',
    'SafePathInput',
    'UuidInput',
    'EmailInput',
    'UrlInput',
    'PaginationParams',
    'BoundedListInput',
    'SecureAgentPrompt',
]
