"""
Request ID Middleware Usage Examples.

This file demonstrates how to use the request ID and correlation tracking
middleware in various scenarios.
"""
import asyncio
from fastapi import FastAPI, Request, BackgroundTasks
from agent_service.api.middleware.request_id import (
    RequestIDMiddleware,
    get_request_id,
    get_correlation_id,
    preserve_request_id,
)
from agent_service.infrastructure.observability.logging import get_logger

logger = get_logger(__name__)


# Example 1: Basic Usage in Route Handlers
# ==========================================

app = FastAPI()
app.add_middleware(RequestIDMiddleware)


@app.get("/example/basic")
async def basic_example(request: Request):
    """
    Basic example: Access request ID from request.state.

    The request ID is automatically available in request.state and
    in the context variables.
    """
    # Method 1: From request.state (recommended in route handlers)
    request_id = request.state.request_id
    correlation_id = request.state.correlation_id

    # Method 2: From context variables (works anywhere)
    context_request_id = get_request_id()
    context_correlation_id = get_correlation_id()

    logger.info(
        "Processing request",
        endpoint="/example/basic"
        # request_id is automatically added by the log processor
    )

    return {
        "request_id": request_id,
        "correlation_id": correlation_id,
        "message": "Request IDs are automatically tracked"
    }


# Example 2: Background Tasks
# =============================

@preserve_request_id
async def process_order_async(order_id: str):
    """
    Background task that preserves request ID.

    The @preserve_request_id decorator ensures this task has access
    to the original request's ID for log correlation.
    """
    logger.info("Processing order in background", order_id=order_id)
    # Simulate async work
    await asyncio.sleep(1)
    logger.info("Order processed", order_id=order_id)
    # All logs will have the same request_id as the original request


@app.post("/example/order")
async def create_order(
    request: Request,
    background_tasks: BackgroundTasks
):
    """
    Example: Using request ID in background tasks.

    The background task will have the same request ID for proper
    log correlation.
    """
    order_id = "ORDER-123"

    # Add background task (decorator will preserve request ID)
    background_tasks.add_task(process_order_async, order_id)

    logger.info("Order created", order_id=order_id)

    return {
        "order_id": order_id,
        "request_id": request.state.request_id,
        "status": "processing"
    }


# Example 3: Distributed Tracing
# ================================

import httpx


async def call_downstream_service(data: dict) -> dict:
    """
    Call a downstream service and pass along correlation ID.

    This enables distributed tracing across multiple services.
    """
    # Get current request ID and correlation ID
    request_id = get_request_id()
    correlation_id = get_correlation_id()

    logger.info(
        "Calling downstream service",
        downstream_url="https://api.example.com/process"
    )

    # Pass correlation ID to downstream service
    # Generate new request ID for this specific call
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.example.com/process",
            json=data,
            headers={
                # Pass correlation ID so all services share same correlation
                "X-Correlation-ID": correlation_id,
                # Optionally pass our request ID as the parent
                "X-Parent-Request-ID": request_id,
            }
        )

    return response.json()


@app.post("/example/distributed")
async def distributed_example(request: Request):
    """
    Example: Distributed tracing across services.

    The correlation ID follows the request across multiple services,
    while each service generates its own request ID.
    """
    logger.info("Received request")

    # Process locally
    result = await call_downstream_service({"action": "process"})

    logger.info("Downstream service completed")

    return {
        "request_id": request.state.request_id,
        "correlation_id": request.state.correlation_id,
        "result": result
    }


# Example 4: Error Handling with Request ID
# ===========================================

@app.get("/example/error")
async def error_example(request: Request):
    """
    Example: Request ID in error handling.

    When errors occur, the request ID helps correlate error logs
    with the specific request.
    """
    try:
        # Simulate some processing
        logger.info("Starting risky operation")

        # Simulate an error
        raise ValueError("Something went wrong!")

    except ValueError as e:
        logger.error(
            "Operation failed",
            error=str(e),
            # request_id is automatically included
        )

        # Return error response with request ID for client debugging
        return {
            "error": str(e),
            "request_id": request.state.request_id,
            "message": "Use this request_id for support inquiries"
        }


# Example 5: Custom Service Class with Request ID
# =================================================

class OrderService:
    """Example service that uses request ID in logging."""

    def __init__(self):
        self.logger = get_logger(__name__)

    async def create_order(self, user_id: str, items: list) -> str:
        """
        Create an order with proper request ID logging.

        All logs will automatically include the request_id from context.
        """
        order_id = f"ORDER-{user_id}-123"

        self.logger.info(
            "Creating order",
            user_id=user_id,
            item_count=len(items),
            order_id=order_id
        )

        # Simulate order creation
        await asyncio.sleep(0.1)

        self.logger.info("Order created", order_id=order_id)

        return order_id


@app.post("/example/service")
async def service_example(request: Request):
    """
    Example: Using request ID in service classes.

    Service methods automatically get request ID in their logs
    without needing to pass it explicitly.
    """
    service = OrderService()
    order_id = await service.create_order(
        user_id="user123",
        items=["item1", "item2"]
    )

    return {
        "order_id": order_id,
        "request_id": request.state.request_id
    }


# Example 6: Manual Request ID for Testing
# ==========================================

@app.get("/example/test-with-id")
async def test_with_request_id(request: Request):
    """
    Example: Testing with specific request ID.

    Clients can provide their own request ID for testing/debugging.
    """
    # Client can send: X-Request-ID: 12345678-1234-4234-1234-123456789abc
    # The middleware will use it if it's a valid UUID4

    logger.info("Test endpoint called")

    return {
        "request_id": request.state.request_id,
        "correlation_id": request.state.correlation_id,
        "message": "You can provide X-Request-ID header for testing"
    }


# Example 7: Async Workers with Request ID
# ==========================================

@preserve_request_id
async def async_worker(task_data: dict):
    """
    Async worker that maintains request ID.

    Useful for task queues, async processing, etc.
    """
    logger.info("Worker started", task_data=task_data)

    # Simulate work
    await asyncio.sleep(0.5)

    logger.info("Worker completed", task_data=task_data)


@app.post("/example/worker")
async def spawn_worker(request: Request):
    """
    Example: Spawning async workers with request ID.

    The worker will maintain the request ID for log correlation.
    """
    task_data = {"task": "process_data"}

    # Spawn worker (in real app, this might be a task queue)
    asyncio.create_task(async_worker(task_data))

    logger.info("Worker spawned", task_data=task_data)

    return {
        "request_id": request.state.request_id,
        "status": "worker_spawned"
    }


# Example 8: Multiple Service Calls
# ===================================

@preserve_request_id
async def service_a(data: str):
    """Service A maintains request ID."""
    logger.info("Service A processing", data=data)
    await asyncio.sleep(0.1)
    return f"A-{data}"


@preserve_request_id
async def service_b(data: str):
    """Service B maintains request ID."""
    logger.info("Service B processing", data=data)
    await asyncio.sleep(0.1)
    return f"B-{data}"


@app.post("/example/multi-service")
async def multi_service_example(request: Request):
    """
    Example: Multiple async services maintaining request ID.

    All services will log with the same request_id.
    """
    logger.info("Starting multi-service processing")

    # Run services concurrently
    results = await asyncio.gather(
        service_a("data1"),
        service_b("data2")
    )

    logger.info("All services completed", results=results)

    return {
        "request_id": request.state.request_id,
        "results": results
    }


# Usage Notes
# ===========
"""
1. AUTOMATIC REQUEST ID:
   - Every request gets a unique UUID4 request ID
   - Available in request.state.request_id
   - Returned in X-Request-ID response header

2. CORRELATION ID:
   - Defaults to request ID if not provided
   - Accepts X-Correlation-ID header from upstream
   - Use for distributed tracing across services
   - Returned in X-Correlation-ID response header

3. LOGGING:
   - request_id and correlation_id automatically added to all logs
   - No need to manually include them in log calls
   - Makes log searching and correlation easy

4. BACKGROUND TASKS:
   - Use @preserve_request_id decorator
   - Ensures background tasks maintain request ID
   - Critical for log correlation

5. DISTRIBUTED SYSTEMS:
   - Pass X-Correlation-ID to downstream services
   - Each service generates its own request ID
   - All share the same correlation ID

6. TESTING:
   - Send X-Request-ID header with valid UUID4
   - Middleware accepts and uses it
   - Invalid UUIDs are rejected and new one generated

7. SECURITY:
   - Request IDs are validated (must be UUID4)
   - Invalid IDs are rejected
   - Prevents injection attacks
"""
