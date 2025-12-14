"""
User-friendly error messages and templates.

This module provides:
- User-friendly error message templates
- Contextual messages based on error type
- Suggested actions for common error scenarios
- Message formatting utilities

The messages are designed to be:
- Clear and understandable to non-technical users
- Actionable (tell users what they can do)
- Non-technical (avoid implementation details)
- Consistent in tone and style

Usage:
    from agent_service.domain.error_messages import (
        get_error_message,
        get_suggested_action,
        format_validation_message,
    )

    # Get user-friendly message
    message = get_error_message("AGENT_NOT_FOUND", agent_id="abc123")

    # Get suggested action
    action = get_suggested_action("TOKEN_EXPIRED")
"""

from typing import Any, Optional


# ========================================
# Error Message Templates
# ========================================

ERROR_MESSAGES = {
    # Authentication errors (401)
    "UNAUTHORIZED": "You need to be logged in to access this resource.",
    "INVALID_CREDENTIALS": "The username, password, or API key you provided is incorrect.",
    "TOKEN_EXPIRED": "Your session has expired.",
    "TOKEN_INVALID": "Your session is invalid or has been revoked.",
    "API_KEY_INVALID": "The API key you provided is invalid or has been revoked.",

    # Authorization errors (403)
    "FORBIDDEN": "You don't have permission to perform this action.",
    "INSUFFICIENT_PERMISSIONS": "Your account doesn't have the required permissions for this action.",
    "RESOURCE_ACCESS_DENIED": "You don't have access to this resource.",

    # Validation errors (400)
    "VALIDATION_ERROR": "The information you provided contains errors.",
    "INVALID_REQUEST": "The request format is invalid.",
    "INVALID_PARAMETER": "One or more parameters in your request are invalid.",
    "MISSING_FIELD": "Some required information is missing.",

    # Resource errors (404, 409)
    "NOT_FOUND": "The resource you're looking for doesn't exist.",
    "ENDPOINT_NOT_FOUND": "The API endpoint you're trying to access doesn't exist.",
    "USER_NOT_FOUND": "The user you're looking for doesn't exist.",
    "AGENT_NOT_FOUND": "The agent you're looking for doesn't exist.",
    "DUPLICATE_RESOURCE": "A resource with this identifier already exists.",
    "CONFLICT": "The operation conflicts with the current state of the resource.",
    "RESOURCE_LOCKED": "This resource is currently being modified by another process.",

    # Rate limiting (429)
    "RATE_LIMITED": "You've made too many requests.",
    "QUOTA_EXCEEDED": "You've exceeded your usage quota.",

    # Agent errors
    "AGENT_INVOCATION_FAILED": "The agent encountered an error while processing your request.",
    "AGENT_TIMEOUT": "The agent took too long to respond.",
    "AGENT_CONFIG_ERROR": "The agent configuration is invalid.",

    # External service errors (502, 503)
    "EXTERNAL_SERVICE_ERROR": "An external service is currently unavailable.",
    "LLM_ERROR": "The AI service is currently unavailable.",
    "LLM_RATE_LIMIT": "The AI service is experiencing high demand.",
    "DATABASE_ERROR": "A database error occurred.",
    "DATABASE_UNAVAILABLE": "The database is currently unavailable.",
    "CACHE_ERROR": "The cache service is currently unavailable.",

    # Timeout errors (504)
    "TIMEOUT": "The request took too long to process.",
    "UPSTREAM_TIMEOUT": "An external service took too long to respond.",

    # Service availability (503)
    "SERVICE_UNAVAILABLE": "The service is temporarily unavailable.",
    "MAINTENANCE_MODE": "The service is currently under maintenance.",

    # Internal errors (500)
    "INTERNAL_ERROR": "An unexpected error occurred.",
}


# ========================================
# Suggested Actions
# ========================================

SUGGESTED_ACTIONS = {
    # Authentication errors
    "UNAUTHORIZED": "Please log in or provide valid authentication credentials.",
    "INVALID_CREDENTIALS": "Please check your credentials and try again. If you've forgotten your password, use the password reset option.",
    "TOKEN_EXPIRED": "Please log in again to continue.",
    "TOKEN_INVALID": "Please log out and log back in.",
    "API_KEY_INVALID": "Please check your API key in your account settings or generate a new one.",

    # Authorization errors
    "FORBIDDEN": "If you believe you should have access, please contact your administrator.",
    "INSUFFICIENT_PERMISSIONS": "Please contact your administrator to request the necessary permissions.",
    "RESOURCE_ACCESS_DENIED": "This resource may be private or restricted. Contact the resource owner if you need access.",

    # Validation errors
    "VALIDATION_ERROR": "Please review the highlighted fields and correct any errors.",
    "INVALID_REQUEST": "Please check the request format and try again.",
    "INVALID_PARAMETER": "Please check the parameter values and try again.",
    "MISSING_FIELD": "Please fill in all required fields and try again.",

    # Resource errors
    "NOT_FOUND": "Please check the resource ID or URL and try again.",
    "ENDPOINT_NOT_FOUND": "Please check the API documentation for the correct endpoint.",
    "USER_NOT_FOUND": "Please verify the user ID and try again.",
    "AGENT_NOT_FOUND": "Please verify the agent ID or create a new agent.",
    "DUPLICATE_RESOURCE": "Please use a different identifier or update the existing resource instead.",
    "CONFLICT": "Please refresh the page and try again.",
    "RESOURCE_LOCKED": "Please wait a moment and try again.",

    # Rate limiting
    "RATE_LIMITED": "Please wait a few moments before making more requests.",
    "QUOTA_EXCEEDED": "Please upgrade your plan for higher limits or wait until your quota resets.",

    # Agent errors
    "AGENT_INVOCATION_FAILED": "Please try again. If the problem continues, contact support with the request ID.",
    "AGENT_TIMEOUT": "Please try again with a simpler request or break it into smaller parts.",
    "AGENT_CONFIG_ERROR": "Please check the agent configuration and ensure all required parameters are correct.",

    # External service errors
    "EXTERNAL_SERVICE_ERROR": "Please try again in a few moments. If the issue persists, contact support.",
    "LLM_ERROR": "Please try again in a few moments. The AI service should be back shortly.",
    "LLM_RATE_LIMIT": "Please wait a moment and try again. Consider simplifying your request to reduce processing time.",
    "DATABASE_ERROR": "Please try again later. If the issue persists, contact support.",
    "DATABASE_UNAVAILABLE": "Please try again in a few moments.",
    "CACHE_ERROR": "Your request will be processed normally but may take longer than usual.",

    # Timeout errors
    "TIMEOUT": "Please try again with a simpler or smaller request.",
    "UPSTREAM_TIMEOUT": "Please try again in a few moments.",

    # Service availability
    "SERVICE_UNAVAILABLE": "Please try again in a few moments.",
    "MAINTENANCE_MODE": "Please check our status page for updates on when the service will be available.",

    # Internal errors
    "INTERNAL_ERROR": "Please try again. If the problem persists, contact support with the request ID.",
}


# ========================================
# Detailed Error Context Messages
# ========================================

CONTEXT_MESSAGES = {
    # Authentication context
    "auth_required": "This endpoint requires authentication. Please include your credentials in the request.",
    "token_format_invalid": "The authentication token format is invalid. Please ensure you're using the correct token type.",
    "api_key_format_invalid": "The API key format is invalid. API keys should start with your configured prefix.",

    # Validation context
    "email_invalid": "Please provide a valid email address in the format: user@example.com",
    "url_invalid": "Please provide a valid URL starting with http:// or https://",
    "number_out_of_range": "The number must be between {min} and {max}.",
    "string_too_short": "This field must be at least {min} characters long.",
    "string_too_long": "This field must be no more than {max} characters long.",
    "invalid_enum": "The value must be one of: {allowed_values}",
    "invalid_date": "Please provide a valid date in the format: YYYY-MM-DD",
    "invalid_datetime": "Please provide a valid date and time in ISO format.",

    # Resource context
    "resource_deleted": "This resource has been deleted and is no longer available.",
    "resource_archived": "This resource has been archived. You may be able to restore it from your archive.",
    "permission_required": "You need the '{permission}' permission to perform this action.",

    # Agent context
    "agent_busy": "This agent is currently processing another request. Please try again in a moment.",
    "agent_disabled": "This agent has been disabled. Please contact the agent owner for more information.",
    "agent_quota_exceeded": "This agent has exceeded its usage quota for this period.",
    "tool_not_available": "The tool '{tool_name}' is not available for this agent.",

    # Rate limiting context
    "rate_limit_details": "You can make {limit} requests per {window}. Your limit will reset in {reset_time}.",
    "quota_details": "You've used {used} of {total} {resource_type}. Your quota resets on {reset_date}.",

    # System context
    "scheduled_maintenance": "Scheduled maintenance is in progress. Expected completion: {end_time}",
    "degraded_performance": "We're experiencing higher than normal traffic. Some operations may be slower than usual.",
    "partial_outage": "Some features may be unavailable. We're working to restore full service.",
}


# ========================================
# Field-Specific Validation Messages
# ========================================

FIELD_VALIDATION_MESSAGES = {
    # Common field names
    "email": "Please enter a valid email address",
    "password": "Password must be at least 8 characters and include uppercase, lowercase, and numbers",
    "username": "Username must be 3-30 characters and contain only letters, numbers, and underscores",
    "phone": "Please enter a valid phone number",
    "url": "Please enter a valid URL",
    "date": "Please enter a valid date",

    # Agent fields
    "agent_name": "Agent name must be 3-100 characters",
    "agent_description": "Agent description must be under 500 characters",
    "max_tokens": "Maximum tokens must be between 1 and 100000",
    "temperature": "Temperature must be between 0.0 and 2.0",
    "timeout": "Timeout must be between 1 and 300 seconds",

    # API fields
    "api_key_name": "API key name must be 3-50 characters",
    "callback_url": "Callback URL must be a valid HTTPS URL",
}


# ========================================
# Utility Functions
# ========================================

def get_error_message(
    error_code: str,
    default: str = "An error occurred",
    **kwargs: Any
) -> str:
    """
    Get user-friendly error message for an error code.

    Args:
        error_code: Error code to look up
        default: Default message if code not found
        **kwargs: Variables to format into the message template

    Returns:
        User-friendly error message

    Example:
        >>> get_error_message("AGENT_NOT_FOUND")
        "The agent you're looking for doesn't exist."

        >>> get_error_message("NOT_FOUND", resource="agent")
        "The agent you're looking for doesn't exist."
    """
    message = ERROR_MESSAGES.get(error_code.upper(), default)

    # Format message with provided kwargs
    try:
        return message.format(**kwargs)
    except (KeyError, AttributeError):
        return message


def get_suggested_action(
    error_code: str,
    default: str = "Please try again later.",
    **kwargs: Any
) -> str:
    """
    Get suggested action for an error code.

    Args:
        error_code: Error code to look up
        default: Default action if code not found
        **kwargs: Variables to format into the action template

    Returns:
        Suggested action message

    Example:
        >>> get_suggested_action("TOKEN_EXPIRED")
        "Please log in again to continue."

        >>> get_suggested_action("RATE_LIMITED", wait_time="30 seconds")
        "Please wait 30 seconds before making more requests."
    """
    action = SUGGESTED_ACTIONS.get(error_code.upper(), default)

    # Format action with provided kwargs
    try:
        return action.format(**kwargs)
    except (KeyError, AttributeError):
        return action


def get_context_message(
    context_key: str,
    default: Optional[str] = None,
    **kwargs: Any
) -> Optional[str]:
    """
    Get contextual message for additional error details.

    Args:
        context_key: Context key to look up
        default: Default message if key not found
        **kwargs: Variables to format into the message template

    Returns:
        Contextual message or None

    Example:
        >>> get_context_message("rate_limit_details", limit=100, window="hour", reset_time="30 minutes")
        "You can make 100 requests per hour. Your limit will reset in 30 minutes."
    """
    message = CONTEXT_MESSAGES.get(context_key, default)

    if message is None:
        return None

    # Format message with provided kwargs
    try:
        return message.format(**kwargs)
    except (KeyError, AttributeError):
        return message


def get_field_validation_message(field_name: str) -> Optional[str]:
    """
    Get field-specific validation message.

    Args:
        field_name: Name of the field

    Returns:
        Field validation message or None

    Example:
        >>> get_field_validation_message("email")
        "Please enter a valid email address"
    """
    return FIELD_VALIDATION_MESSAGES.get(field_name.lower())


def format_validation_message(
    field_name: str,
    error_type: str,
    **kwargs: Any
) -> str:
    """
    Format a validation error message for a specific field.

    Args:
        field_name: Name of the field
        error_type: Type of validation error
        **kwargs: Additional context (min, max, allowed_values, etc.)

    Returns:
        Formatted validation message

    Example:
        >>> format_validation_message("age", "number_out_of_range", min=0, max=120)
        "Age must be between 0 and 120."

        >>> format_validation_message("status", "invalid_enum", allowed_values=["active", "inactive"])
        "Status must be one of: active, inactive"
    """
    # Check for field-specific message first
    field_msg = get_field_validation_message(field_name)
    if field_msg:
        return field_msg

    # Check for context message based on error type
    context_msg = get_context_message(error_type, **kwargs)
    if context_msg:
        return f"{field_name.replace('_', ' ').title()}: {context_msg}"

    # Generic message
    return f"{field_name.replace('_', ' ').title()} is invalid."


def format_resource_not_found(
    resource_type: str,
    resource_id: Optional[str] = None
) -> str:
    """
    Format a resource not found message.

    Args:
        resource_type: Type of resource (agent, user, etc.)
        resource_id: Optional resource identifier

    Returns:
        Formatted not found message

    Example:
        >>> format_resource_not_found("agent", "abc123")
        "Agent 'abc123' was not found."

        >>> format_resource_not_found("user")
        "User was not found."
    """
    resource_name = resource_type.replace("_", " ").title()

    if resource_id:
        return f"{resource_name} '{resource_id}' was not found."

    return f"{resource_name} was not found."


def format_permission_error(permission: str) -> str:
    """
    Format a permission error message.

    Args:
        permission: Required permission

    Returns:
        Formatted permission error message

    Example:
        >>> format_permission_error("agents:delete")
        "You need the 'agents:delete' permission to perform this action."
    """
    return get_context_message("permission_required", permission=permission) or \
           f"You need the '{permission}' permission to perform this action."


def format_rate_limit_message(
    limit: int,
    window: str,
    reset_time: str
) -> str:
    """
    Format a rate limit error message.

    Args:
        limit: Request limit
        window: Time window (e.g., "minute", "hour")
        reset_time: Time until reset (e.g., "30 seconds")

    Returns:
        Formatted rate limit message

    Example:
        >>> format_rate_limit_message(100, "hour", "30 minutes")
        "You can make 100 requests per hour. Your limit will reset in 30 minutes."
    """
    return get_context_message(
        "rate_limit_details",
        limit=limit,
        window=window,
        reset_time=reset_time
    ) or "You've exceeded your rate limit. Please try again later."


def format_quota_message(
    used: int,
    total: int,
    resource_type: str,
    reset_date: str
) -> str:
    """
    Format a quota exceeded message.

    Args:
        used: Amount used
        total: Total quota
        resource_type: Type of resource (requests, tokens, etc.)
        reset_date: Date when quota resets

    Returns:
        Formatted quota message

    Example:
        >>> format_quota_message(1000, 1000, "API requests", "January 1, 2025")
        "You've used 1000 of 1000 API requests. Your quota resets on January 1, 2025."
    """
    return get_context_message(
        "quota_details",
        used=used,
        total=total,
        resource_type=resource_type,
        reset_date=reset_date
    ) or "You've exceeded your quota. Please upgrade your plan or wait for quota reset."
