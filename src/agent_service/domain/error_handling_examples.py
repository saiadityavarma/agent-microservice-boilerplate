"""
Examples demonstrating the comprehensive error handling system.

This module provides practical examples of:
- Raising custom exceptions
- Using error messages and suggested actions
- Handling errors in API endpoints
- Testing error scenarios

The error handling system provides:
1. Structured exception hierarchy in domain.exceptions
2. User-friendly error messages in domain.error_messages
3. Automatic error handling middleware in api.middleware.errors
4. Integration with logging and Sentry for monitoring
"""

from typing import Optional
from fastapi import APIRouter, Request, Depends

# Import exceptions from domain
from agent_service.domain.exceptions import (
    AgentNotFound,
    ValidationError,
    InvalidCredentials,
    InsufficientPermissions,
    LLMError,
    DatabaseError,
    AgentTimeout,
    RateLimitError,
)

# Import error message utilities
from agent_service.domain.error_messages import (
    get_error_message,
    get_suggested_action,
    format_resource_not_found,
    format_validation_message,
    format_rate_limit_message,
)


# ========================================
# Example 1: Basic Exception Raising
# ========================================

def example_basic_exception():
    """
    Basic exception raising with default messages.

    The exception will automatically include:
    - Error code (from ErrorCode enum)
    - HTTP status code
    - User-friendly message
    - Suggested action
    """
    # Raise with default message
    raise AgentNotFound()

    # This produces a 404 response with:
    # {
    #   "error": {
    #     "code": "AGENT_NOT_FOUND",
    #     "message": "Agent not found"
    #   },
    #   "suggested_action": "Please verify the agent ID is correct or create a new agent",
    #   "request_id": "..."
    # }


def example_custom_message():
    """
    Exception with custom message and details.
    """
    raise AgentNotFound(
        message="Agent 'gpt-assistant-v1' not found",
        details={"agent_id": "gpt-assistant-v1", "available_agents": ["basic", "advanced"]},
        suggested_action="Please use one of the available agents or create a new one"
    )

    # This produces a 404 response with:
    # {
    #   "error": {
    #     "code": "AGENT_NOT_FOUND",
    #     "message": "Agent 'gpt-assistant-v1' not found",
    #     "details": {
    #       "agent_id": "gpt-assistant-v1",
    #       "available_agents": ["basic", "advanced"]
    #     }
    #   },
    #   "suggested_action": "Please use one of the available agents or create a new one",
    #   "request_id": "..."
    # }


# ========================================
# Example 2: Validation Errors
# ========================================

def example_validation_error():
    """
    Validation error with field details.
    """
    raise ValidationError(
        message="Invalid agent configuration",
        details={
            "fields": {
                "max_tokens": "Must be between 1 and 100000",
                "temperature": "Must be between 0.0 and 2.0",
            }
        },
        suggested_action="Please correct the configuration values and try again"
    )


def validate_agent_config(config: dict) -> None:
    """
    Example of validation with detailed error messages.
    """
    errors = {}

    # Validate max_tokens
    max_tokens = config.get("max_tokens")
    if max_tokens is not None:
        if not isinstance(max_tokens, int):
            errors["max_tokens"] = "Must be an integer"
        elif max_tokens < 1 or max_tokens > 100000:
            errors["max_tokens"] = format_validation_message(
                "max_tokens",
                "number_out_of_range",
                min=1,
                max=100000
            )

    # Validate temperature
    temperature = config.get("temperature")
    if temperature is not None:
        if not isinstance(temperature, (int, float)):
            errors["temperature"] = "Must be a number"
        elif temperature < 0.0 or temperature > 2.0:
            errors["temperature"] = format_validation_message(
                "temperature",
                "number_out_of_range",
                min=0.0,
                max=2.0
            )

    # Raise validation error if there are issues
    if errors:
        raise ValidationError(
            message="Agent configuration validation failed",
            details={"fields": errors},
            suggested_action="Please correct the highlighted fields and try again"
        )


# ========================================
# Example 3: API Endpoint with Error Handling
# ========================================

router = APIRouter(prefix="/examples", tags=["error-examples"])


@router.get("/agents/{agent_id}")
async def get_agent_example(agent_id: str):
    """
    Example endpoint demonstrating error handling.

    The error middleware automatically:
    - Catches all exceptions
    - Logs with context (user, request_id, etc.)
    - Sends 5xx errors to Sentry
    - Returns structured error responses
    - Hides internal details in production
    """
    # Simulate agent lookup
    agent = await lookup_agent(agent_id)

    if agent is None:
        # Raise custom exception - middleware handles the rest
        raise AgentNotFound(
            message=f"Agent '{agent_id}' not found",
            details={"agent_id": agent_id},
        )

    return agent


@router.post("/agents")
async def create_agent_example(request: Request):
    """
    Example endpoint with validation and error handling.
    """
    # Parse request body
    body = await request.json()

    # Validate configuration
    validate_agent_config(body.get("config", {}))

    # Simulate agent creation
    try:
        agent = await create_agent(body)
        return agent
    except Exception as e:
        # Wrap external errors
        raise DatabaseError(
            message="Failed to create agent",
            details={"error": str(e)},
        )


@router.post("/agents/{agent_id}/invoke")
async def invoke_agent_example(agent_id: str, request: Request):
    """
    Example endpoint with timeout and external service error handling.
    """
    # Check rate limit
    if await is_rate_limited(agent_id):
        raise RateLimitError(
            message=format_rate_limit_message(
                limit=100,
                window="hour",
                reset_time="30 minutes"
            )
        )

    # Invoke agent
    try:
        result = await invoke_agent_with_timeout(agent_id, timeout=30)
        return result
    except TimeoutError:
        raise AgentTimeout(
            message=f"Agent '{agent_id}' execution timed out after 30 seconds",
            details={"agent_id": agent_id, "timeout": 30},
        )
    except LLMServiceError as e:
        raise LLMError(
            message="AI service error",
            details={"error": str(e)},
        )


# ========================================
# Example 4: Authentication and Authorization
# ========================================

async def example_auth_error(token: str):
    """
    Example of authentication error handling.
    """
    # Validate token
    if not token:
        raise InvalidCredentials(
            message="No authentication token provided",
            suggested_action="Please include your API key in the Authorization header"
        )

    # Check if token is expired
    if await is_token_expired(token):
        raise InvalidCredentials(
            message="Authentication token has expired",
            suggested_action="Please refresh your token or log in again"
        )


async def example_permission_error(user_id: str, required_permission: str):
    """
    Example of authorization error handling.
    """
    # Check permissions
    has_permission = await user_has_permission(user_id, required_permission)

    if not has_permission:
        raise InsufficientPermissions(
            message=f"You don't have the '{required_permission}' permission",
            details={
                "required_permission": required_permission,
                "user_id": user_id,
            },
            suggested_action="Please contact your administrator to request this permission"
        )


# ========================================
# Example 5: External Service Error Handling
# ========================================

async def example_external_service_error():
    """
    Example of handling external service errors.
    """
    try:
        # Call external LLM service
        response = await call_llm_service()
        return response
    except LLMServiceUnavailableError:
        raise LLMError(
            message="AI service is currently unavailable",
            suggested_action="Please try again in a few moments. The service should be back shortly."
        )
    except LLMServiceRateLimitError as e:
        raise LLMError(
            message="AI service rate limit exceeded",
            details={"retry_after": e.retry_after},
            suggested_action=f"Please wait {e.retry_after} seconds before trying again"
        )


# ========================================
# Example 6: Database Error Handling
# ========================================

async def example_database_error():
    """
    Example of handling database errors.
    """
    try:
        # Perform database operation
        result = await db_operation()
        return result
    except ConnectionError:
        raise DatabaseError(
            message="Unable to connect to database",
            suggested_action="The database is temporarily unavailable. Please try again in a few moments."
        )
    except IntegrityError as e:
        # Convert to appropriate exception
        if "unique constraint" in str(e).lower():
            from agent_service.domain.exceptions import AlreadyExists
            raise AlreadyExists(
                message="A resource with this identifier already exists",
                details={"constraint": str(e)},
            )
        else:
            raise DatabaseError(
                message="Database integrity error",
                details={"error": str(e)},
            )


# ========================================
# Example 7: Using Error Messages Utilities
# ========================================

def example_error_messages():
    """
    Examples of using error message utilities.
    """
    # Get standard error message
    msg = get_error_message("AGENT_NOT_FOUND")
    # Returns: "The agent you're looking for doesn't exist."

    # Get suggested action
    action = get_suggested_action("TOKEN_EXPIRED")
    # Returns: "Please log in again to continue."

    # Format resource not found
    msg = format_resource_not_found("agent", "abc123")
    # Returns: "Agent 'abc123' was not found."

    # Format validation message
    msg = format_validation_message("age", "number_out_of_range", min=0, max=120)
    # Returns: "Age: The number must be between 0 and 120."

    # Format rate limit message
    msg = format_rate_limit_message(100, "hour", "30 minutes")
    # Returns: "You can make 100 requests per hour. Your limit will reset in 30 minutes."


# ========================================
# Helper Functions (Simulated)
# ========================================

async def lookup_agent(agent_id: str) -> Optional[dict]:
    """Simulated agent lookup."""
    return None


async def create_agent(data: dict) -> dict:
    """Simulated agent creation."""
    return {"id": "new-agent", "name": data.get("name")}


async def invoke_agent_with_timeout(agent_id: str, timeout: int) -> dict:
    """Simulated agent invocation."""
    return {"result": "success"}


async def is_rate_limited(agent_id: str) -> bool:
    """Simulated rate limit check."""
    return False


async def is_token_expired(token: str) -> bool:
    """Simulated token expiry check."""
    return False


async def user_has_permission(user_id: str, permission: str) -> bool:
    """Simulated permission check."""
    return True


async def call_llm_service() -> dict:
    """Simulated LLM service call."""
    return {"response": "Hello"}


async def db_operation() -> dict:
    """Simulated database operation."""
    return {"success": True}


# Custom exception types (for demonstration)
class LLMServiceError(Exception):
    pass


class LLMServiceUnavailableError(LLMServiceError):
    pass


class LLMServiceRateLimitError(LLMServiceError):
    def __init__(self, retry_after: int):
        self.retry_after = retry_after


class IntegrityError(Exception):
    pass


# ========================================
# Testing Examples
# ========================================

def test_error_response_format():
    """
    Example test verifying error response format.
    """
    from fastapi.testclient import TestClient
    from agent_service.api.app import app

    client = TestClient(app)

    # Test agent not found
    response = client.get("/agents/nonexistent")

    assert response.status_code == 404
    assert "error" in response.json()
    assert "request_id" in response.json()
    assert response.json()["error"]["code"] == "AGENT_NOT_FOUND"
    assert "suggested_action" in response.json()


def test_validation_error_format():
    """
    Example test verifying validation error format.
    """
    from fastapi.testclient import TestClient
    from agent_service.api.app import app

    client = TestClient(app)

    # Test invalid request
    response = client.post("/agents", json={"config": {"max_tokens": -1}})

    assert response.status_code == 400
    assert "error" in response.json()
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert "details" in response.json()["error"]
    assert "suggested_action" in response.json()
