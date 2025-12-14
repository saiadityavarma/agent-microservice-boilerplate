"""
Examples of using Sentry error tracking integration.

This file demonstrates various use cases for error tracking in the agent service.
"""

from fastapi import APIRouter, Request, HTTPException, Depends
from typing import Optional

from agent_service.infrastructure.observability.error_tracking import (
    set_user_context,
    set_request_context,
    capture_exception,
    capture_message,
    add_breadcrumb,
    set_tag,
    set_context,
    clear_user_context,
)


# Example 1: Basic error capture in an endpoint
router = APIRouter()


@router.post("/process-data")
async def process_data(request: Request, data: dict):
    """
    Example endpoint demonstrating basic error tracking.
    """
    # Add request context at the beginning of the request
    set_request_context(request)

    # Add breadcrumb for tracking user actions
    add_breadcrumb(
        message="User started data processing",
        category="operation",
        level="info",
        data={"data_size": len(data)},
    )

    try:
        # Simulate data processing
        result = perform_data_processing(data)
        return {"status": "success", "result": result}

    except ValueError as e:
        # Capture expected errors with context
        capture_exception(
            e,
            extra={
                "operation": "data_processing",
                "data_size": len(data),
                "error_type": "validation",
            },
            level="warning",  # Use warning for expected errors
        )
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        # Capture unexpected errors
        capture_exception(
            e,
            extra={
                "operation": "data_processing",
                "data_size": len(data),
            },
            level="error",
        )
        raise HTTPException(status_code=500, detail="Internal server error")


# Example 2: User context tracking
@router.post("/login")
async def login(request: Request, username: str, password: str):
    """
    Example endpoint demonstrating user context management.
    """
    set_request_context(request)

    try:
        # Authenticate user
        user = authenticate_user(username, password)

        # Set user context after successful authentication
        set_user_context(
            user_id=str(user["id"]),
            email=user["email"],
            username=user["username"],
            # Additional custom fields
            role=user["role"],
            subscription_tier=user.get("subscription_tier", "free"),
        )

        # Add breadcrumb for login event
        add_breadcrumb(
            message="User logged in successfully",
            category="auth",
            level="info",
            data={"username": username},
        )

        return {"status": "success", "user_id": user["id"]}

    except Exception as e:
        capture_exception(
            e,
            extra={
                "operation": "login",
                "username": username,  # Don't include password!
            },
            level="error",
        )
        raise HTTPException(status_code=401, detail="Authentication failed")


@router.post("/logout")
async def logout(request: Request):
    """
    Example endpoint demonstrating context cleanup.
    """
    set_request_context(request)

    # Clear user context on logout
    clear_user_context()

    add_breadcrumb(
        message="User logged out",
        category="auth",
        level="info",
    )

    return {"status": "success"}


# Example 3: Tags for filtering and grouping
@router.post("/payment/process")
async def process_payment(request: Request, payment_data: dict):
    """
    Example endpoint demonstrating tags for filtering.
    """
    set_request_context(request)

    # Set tags for filtering in Sentry
    set_tag("payment_provider", payment_data.get("provider", "unknown"))
    set_tag("payment_method", payment_data.get("method", "unknown"))
    set_tag("currency", payment_data.get("currency", "USD"))

    try:
        result = process_payment_transaction(payment_data)

        # Capture successful high-value transactions for monitoring
        if payment_data.get("amount", 0) > 10000:
            capture_message(
                "High-value payment processed",
                level="info",
                extra={
                    "amount": payment_data["amount"],
                    "currency": payment_data["currency"],
                    "provider": payment_data["provider"],
                },
            )

        return {"status": "success", "transaction_id": result["id"]}

    except Exception as e:
        capture_exception(
            e,
            extra={
                "operation": "payment_processing",
                "amount": payment_data.get("amount"),
                "currency": payment_data.get("currency"),
            },
            level="error",
        )
        raise HTTPException(status_code=500, detail="Payment processing failed")


# Example 4: Custom contexts for structured data
@router.post("/agent/execute")
async def execute_agent(request: Request, agent_id: str, task_data: dict):
    """
    Example endpoint demonstrating custom contexts.
    """
    set_request_context(request)

    # Set custom context for agent execution
    set_context("agent_execution", {
        "agent_id": agent_id,
        "task_type": task_data.get("type"),
        "priority": task_data.get("priority", "normal"),
        "estimated_duration": task_data.get("estimated_duration"),
    })

    # Add breadcrumb for task start
    add_breadcrumb(
        message="Agent execution started",
        category="agent",
        level="info",
        data={"agent_id": agent_id, "task_type": task_data.get("type")},
    )

    try:
        result = execute_agent_task(agent_id, task_data)

        # Add breadcrumb for task completion
        add_breadcrumb(
            message="Agent execution completed",
            category="agent",
            level="info",
            data={
                "agent_id": agent_id,
                "duration": result.get("duration"),
                "status": "success",
            },
        )

        return {"status": "success", "result": result}

    except Exception as e:
        # Add breadcrumb for task failure
        add_breadcrumb(
            message="Agent execution failed",
            category="agent",
            level="error",
            data={"agent_id": agent_id, "error": str(e)},
        )

        capture_exception(
            e,
            extra={
                "operation": "agent_execution",
                "agent_id": agent_id,
                "task_type": task_data.get("type"),
            },
            level="error",
        )
        raise HTTPException(status_code=500, detail="Agent execution failed")


# Example 5: Monitoring business events with capture_message
@router.post("/subscription/upgrade")
async def upgrade_subscription(request: Request, user_id: str, new_tier: str):
    """
    Example endpoint demonstrating business event tracking.
    """
    set_request_context(request)
    set_user_context(user_id=user_id)

    try:
        old_tier = get_user_subscription(user_id)

        # Perform upgrade
        upgrade_user_subscription(user_id, new_tier)

        # Track business event
        capture_message(
            "User upgraded subscription",
            level="info",
            extra={
                "user_id": user_id,
                "old_tier": old_tier,
                "new_tier": new_tier,
                "revenue_impact": calculate_revenue_impact(old_tier, new_tier),
            },
        )

        add_breadcrumb(
            message="Subscription upgraded",
            category="business",
            level="info",
            data={"from": old_tier, "to": new_tier},
        )

        return {"status": "success", "new_tier": new_tier}

    except Exception as e:
        capture_exception(
            e,
            extra={
                "operation": "subscription_upgrade",
                "user_id": user_id,
                "new_tier": new_tier,
            },
            level="error",
        )
        raise HTTPException(status_code=500, detail="Subscription upgrade failed")


# Example 6: Monitoring quota and rate limits
@router.post("/api/execute")
async def api_execute(request: Request, user_id: str, operation: str):
    """
    Example endpoint demonstrating quota monitoring.
    """
    set_request_context(request)
    set_user_context(user_id=user_id)

    # Check quota
    current_usage = get_user_quota_usage(user_id)
    quota_limit = get_user_quota_limit(user_id)

    # Set context for quota information
    set_context("quota", {
        "current_usage": current_usage,
        "limit": quota_limit,
        "percentage": (current_usage / quota_limit) * 100 if quota_limit > 0 else 0,
    })

    # Warn when approaching quota limit
    if current_usage >= quota_limit * 0.9:
        capture_message(
            "User approaching quota limit",
            level="warning",
            extra={
                "user_id": user_id,
                "current_usage": current_usage,
                "quota_limit": quota_limit,
                "percentage": (current_usage / quota_limit) * 100,
            },
        )

    # Check if quota exceeded
    if current_usage >= quota_limit:
        capture_message(
            "User exceeded quota limit",
            level="warning",
            extra={
                "user_id": user_id,
                "current_usage": current_usage,
                "quota_limit": quota_limit,
            },
        )
        raise HTTPException(status_code=429, detail="Quota limit exceeded")

    try:
        result = execute_operation(operation)
        increment_user_quota_usage(user_id)
        return {"status": "success", "result": result}

    except Exception as e:
        capture_exception(
            e,
            extra={
                "operation": "api_execute",
                "user_id": user_id,
                "quota_usage": current_usage,
            },
            level="error",
        )
        raise HTTPException(status_code=500, detail="Operation failed")


# Dummy helper functions for examples (would be implemented in real code)
def perform_data_processing(data: dict) -> dict:
    """Dummy data processing function."""
    if not data:
        raise ValueError("Data cannot be empty")
    return {"processed": True}


def authenticate_user(username: str, password: str) -> dict:
    """Dummy authentication function."""
    # In real code, this would verify credentials
    return {
        "id": 123,
        "username": username,
        "email": f"{username}@example.com",
        "role": "user",
        "subscription_tier": "pro",
    }


def process_payment_transaction(payment_data: dict) -> dict:
    """Dummy payment processing function."""
    return {"id": "txn_123456", "status": "completed"}


def execute_agent_task(agent_id: str, task_data: dict) -> dict:
    """Dummy agent execution function."""
    return {"status": "completed", "duration": 1.5}


def get_user_subscription(user_id: str) -> str:
    """Dummy subscription getter."""
    return "free"


def upgrade_user_subscription(user_id: str, new_tier: str) -> None:
    """Dummy subscription upgrade."""
    pass


def calculate_revenue_impact(old_tier: str, new_tier: str) -> float:
    """Dummy revenue calculation."""
    return 50.0


def get_user_quota_usage(user_id: str) -> int:
    """Dummy quota usage getter."""
    return 950


def get_user_quota_limit(user_id: str) -> int:
    """Dummy quota limit getter."""
    return 1000


def execute_operation(operation: str) -> dict:
    """Dummy operation execution."""
    return {"result": "success"}


def increment_user_quota_usage(user_id: str) -> None:
    """Dummy quota increment."""
    pass
