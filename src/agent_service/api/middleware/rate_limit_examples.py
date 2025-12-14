# src/agent_service/api/middleware/rate_limit_examples.py
"""
Examples of how to use rate limiting decorators in your routes.

This file demonstrates different rate limiting strategies and patterns.
Copy these examples into your actual route files as needed.
"""
from fastapi import APIRouter, Request, Depends
from agent_service.api.middleware.rate_limit import (
    rate_limit,
    rate_limit_by_tier,
    get_user_key,
    get_api_key_key,
    get_ip_key,
    limiter,
)

# Example router
router = APIRouter()


# ==========================================
# Example 1: Simple rate limit by IP
# ==========================================
@router.get("/public/data")
@limiter.limit("10/minute")
async def get_public_data(request: Request):
    """
    Public endpoint with IP-based rate limiting.
    Limited to 10 requests per minute per IP address.
    """
    return {"data": "public information"}


# ==========================================
# Example 2: Custom rate limit with decorator
# ==========================================
@router.get("/search")
@rate_limit("100/hour")
async def search(request: Request, query: str):
    """
    Search endpoint with custom rate limit.
    Limited to 100 requests per hour per IP address.
    """
    return {"results": [], "query": query}


# ==========================================
# Example 3: Rate limit by user ID
# ==========================================
@router.get("/user/profile")
@limiter.limit("50/hour", key_func=get_user_key)
async def get_user_profile(request: Request):
    """
    User profile endpoint with user-based rate limiting.
    Limited to 50 requests per hour per authenticated user.
    Falls back to IP if user is not authenticated.
    """
    return {"profile": {}}


# ==========================================
# Example 4: Rate limit by API key
# ==========================================
@router.post("/api/analyze")
@limiter.limit("200/hour", key_func=get_api_key_key)
async def analyze_data(request: Request, data: dict):
    """
    API endpoint with API key-based rate limiting.
    Limited to 200 requests per hour per API key.
    Falls back to IP if no API key is provided.
    """
    return {"analysis": "results"}


# ==========================================
# Example 5: Tier-based rate limiting
# ==========================================
@router.post("/premium/process")
@rate_limit_by_tier()
async def process_premium(request: Request, data: dict):
    """
    Premium endpoint with tier-based rate limiting.
    Rate limits automatically adjust based on user tier:
    - free: 100 requests/hour
    - pro: 1000 requests/hour
    - enterprise: 10000 requests/hour
    """
    return {"status": "processed"}


# ==========================================
# Example 6: Multiple rate limits on same endpoint
# ==========================================
@router.post("/api/submit")
@limiter.limit("5/minute")  # Short-term limit
@limiter.limit("100/hour")  # Long-term limit
async def submit_data(request: Request, data: dict):
    """
    Endpoint with multiple rate limits.
    Limited to 5 requests per minute AND 100 requests per hour.
    Whichever limit is hit first will trigger rate limiting.
    """
    return {"submission_id": "12345"}


# ==========================================
# Example 7: Different limits for different methods
# ==========================================
@router.get("/resources")
@limiter.limit("100/hour")
async def list_resources(request: Request):
    """GET endpoint with 100 requests/hour limit."""
    return {"resources": []}


@router.post("/resources")
@limiter.limit("50/hour")
async def create_resource(request: Request, data: dict):
    """POST endpoint with 50 requests/hour limit (more restrictive)."""
    return {"id": "new-resource"}


# ==========================================
# Example 8: Exempt specific endpoints from rate limiting
# ==========================================
@router.get("/health")
async def health_check(request: Request):
    """
    Health check endpoint with NO rate limiting.
    Simply don't add any rate limit decorator.
    """
    return {"status": "healthy"}


# ==========================================
# Example 9: Dynamic rate limit based on request
# ==========================================
@router.post("/batch/process")
async def batch_process(request: Request, items: list):
    """
    Batch processing with dynamic limits.
    Could implement custom logic to adjust limits based on batch size.
    """
    # Check batch size
    batch_size = len(items)

    if batch_size > 100:
        # For large batches, apply stricter limit
        # Note: This is a conceptual example - actual implementation
        # would need custom middleware or decorator
        pass

    return {"processed": batch_size}


# ==========================================
# Example 10: Rate limit with custom key function
# ==========================================
def get_organization_key(request: Request) -> str:
    """Custom key function for organization-level rate limiting."""
    # Extract organization from user or API key metadata
    user = getattr(request.state, "user", None)
    if user and hasattr(user, "organization_id"):
        return f"org:{user.organization_id}"

    return get_ip_key(request)


@router.get("/organization/data")
@limiter.limit("1000/hour", key_func=get_organization_key)
async def get_organization_data(request: Request):
    """
    Organization-level rate limiting.
    All users in the same organization share the same rate limit.
    """
    return {"data": []}


# ==========================================
# Example 11: Combining with authentication
# ==========================================
# Assuming you have an auth dependency
async def get_current_user(request: Request):
    """Mock auth dependency - replace with your actual implementation."""
    # Your auth logic here
    return {"id": "user123", "tier": "pro"}


@router.get("/protected/resource")
@limiter.limit("500/hour", key_func=get_user_key)
async def get_protected_resource(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """
    Protected endpoint with authentication and rate limiting.
    Rate limited by authenticated user ID.
    """
    return {"resource": "protected data", "user": current_user}


# ==========================================
# Usage Notes
# ==========================================
"""
1. Rate limit strings format:
   - "X/second" - X requests per second
   - "X/minute" - X requests per minute
   - "X/hour" - X requests per hour
   - "X/day" - X requests per day

2. Key functions determine how to group requests:
   - get_ip_key: Group by IP address (default)
   - get_user_key: Group by authenticated user ID
   - get_api_key_key: Group by API key
   - Custom function: Implement your own grouping logic

3. Headers added to responses:
   - X-RateLimit-Limit: Maximum requests allowed
   - X-RateLimit-Remaining: Requests remaining in current window
   - X-RateLimit-Reset: Unix timestamp when limit resets

4. 429 Response format:
   {
       "error": "rate_limit_exceeded",
       "message": "Too many requests. Please try again later.",
       "detail": "1 per 1 minute"
   }
   Headers: {"Retry-After": "60"}

5. Configuration in settings.py:
   - rate_limit_enabled: bool = True
   - rate_limit_default_tier: str = "free"
   - redis_url: str = "redis://localhost:6379/0"

6. Tier configuration in rate_limit.py:
   RATE_LIMIT_TIERS = {
       "free": "100/hour",
       "pro": "1000/hour",
       "enterprise": "10000/hour",
   }
"""
