"""
Agent execution context with access to tools, database, cache, and services.

Provides a unified context object that agents receive during execution,
giving them access to all necessary infrastructure and services.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING
from uuid import UUID

from structlog import BoundLogger

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession
    from agent_service.tools.registry import ToolRegistry
    from agent_service.infrastructure.cache.cache import ICache
    from agent_service.config.settings import Settings
    from agent_service.infrastructure.database.models.user import User


@dataclass
class UserInfo:
    """
    Information about the current user.

    Subset of the full User model for agent context.
    """

    id: UUID
    email: str
    name: str
    roles: list[str] = field(default_factory=list)
    groups: list[str] = field(default_factory=list)
    provider: str = "local"

    @classmethod
    def from_user_model(cls, user: User) -> UserInfo:
        """
        Create UserInfo from a User database model.

        Args:
            user: User model instance

        Returns:
            UserInfo instance
        """
        return cls(
            id=user.id,
            email=user.email,
            name=user.name,
            roles=user.roles or [],
            groups=user.groups or [],
            provider=user.provider,
        )

    def has_role(self, role: str) -> bool:
        """Check if user has a specific role."""
        return role in self.roles

    def has_any_role(self, *roles: str) -> bool:
        """Check if user has any of the specified roles."""
        return any(role in self.roles for role in roles)

    def is_in_group(self, group: str) -> bool:
        """Check if user is in a specific group."""
        return group in self.groups


class AgentContext:
    """
    Execution context provided to agents during invocation.

    Provides access to:
    - Tool registry for calling other tools
    - Database session for data access
    - Cache for temporary storage
    - Logger for structured logging
    - User information (if authenticated)
    - Request ID for tracing
    - Application settings
    - Secrets management

    Example:
        >>> @agent(name="my_agent", description="Example agent")
        >>> async def my_agent(input: AgentInput, ctx: AgentContext) -> AgentOutput:
        ...     # Call a tool
        ...     result = await ctx.call_tool("web_search", query="Python")
        ...
        ...     # Access database
        ...     async with ctx.db as session:
        ...         users = await session.execute(select(User))
        ...
        ...     # Use cache
        ...     await ctx.cache.set("key", "value", ttl=300)
        ...
        ...     # Log with context
        ...     ctx.logger.info("processing", user_id=str(ctx.user.id))
        ...
        ...     return AgentOutput(content="Done")
    """

    def __init__(
        self,
        tools: ToolRegistry,
        db: AsyncSession | None = None,
        cache: ICache | None = None,
        logger: BoundLogger | None = None,
        user: UserInfo | None = None,
        request_id: str | None = None,
        settings: Settings | None = None,
    ):
        """
        Initialize agent context.

        Args:
            tools: Tool registry for calling tools
            db: Database session (optional)
            cache: Cache instance (optional)
            logger: Structured logger (optional)
            user: Current user info (optional)
            request_id: Request ID for tracing (optional)
            settings: Application settings (optional)
        """
        self._tools = tools
        self._db = db
        self._cache = cache
        self._logger = logger
        self._user = user
        self._request_id = request_id
        self._settings = settings

    @property
    def tools(self) -> ToolRegistry:
        """Get the tool registry."""
        return self._tools

    @property
    def db(self) -> AsyncSession | None:
        """Get the database session."""
        return self._db

    @property
    def cache(self) -> ICache | None:
        """Get the cache instance."""
        return self._cache

    @property
    def logger(self) -> BoundLogger:
        """Get the structured logger."""
        if self._logger is None:
            from agent_service.infrastructure.observability.logging import get_logger

            self._logger = get_logger(__name__)
        return self._logger

    @property
    def user(self) -> UserInfo | None:
        """Get the current user information."""
        return self._user

    @property
    def request_id(self) -> str | None:
        """Get the request ID for tracing."""
        return self._request_id

    @property
    def settings(self) -> Settings:
        """Get application settings."""
        if self._settings is None:
            from agent_service.config.settings import get_settings

            self._settings = get_settings()
        return self._settings

    async def call_tool(self, name: str, **kwargs: Any) -> Any:
        """
        Call a tool by name with the given arguments.

        Args:
            name: Tool name
            **kwargs: Tool arguments

        Returns:
            Tool execution result

        Raises:
            ValueError: If tool not found
            Exception: Any exception raised by the tool

        Example:
            >>> result = await ctx.call_tool("web_search", query="Python", max_results=5)
        """
        self.logger.info("calling_tool", tool=name, args=list(kwargs.keys()))
        try:
            result = await self._tools.execute(name, **kwargs)
            self.logger.info("tool_completed", tool=name, success=True)
            return result
        except Exception as e:
            self.logger.error("tool_failed", tool=name, error=str(e), exc_info=True)
            raise

    async def get_secret(self, key: str) -> str | None:
        """
        Get a secret from the secrets manager.

        Args:
            key: Secret key

        Returns:
            Secret value or None if not found

        Example:
            >>> api_key = await ctx.get_secret("OPENAI_API_KEY")
        """
        from agent_service.config.secrets import get_secrets_manager

        secrets = get_secrets_manager()
        return secrets.get_secret(key)

    async def get_secret_json(self, key: str) -> dict | None:
        """
        Get a secret as JSON from the secrets manager.

        Args:
            key: Secret key

        Returns:
            Parsed JSON dict or None if not found

        Example:
            >>> db_config = await ctx.get_secret_json("DATABASE_CONFIG")
        """
        from agent_service.config.secrets import get_secrets_manager

        secrets = get_secrets_manager()
        return secrets.get_secret_json(key)

    def has_permission(self, permission: str) -> bool:
        """
        Check if the current user has a specific permission.

        Args:
            permission: Permission to check

        Returns:
            True if user has permission, False otherwise

        Example:
            >>> if ctx.has_permission("admin"):
            ...     # Do admin stuff
        """
        if not self._user:
            return False

        # For now, just check roles
        # This can be extended to use the RBAC system
        return self._user.has_role(permission)

    def require_permission(self, permission: str) -> None:
        """
        Require that the current user has a specific permission.

        Args:
            permission: Required permission

        Raises:
            PermissionError: If user doesn't have permission

        Example:
            >>> ctx.require_permission("admin")
        """
        if not self.has_permission(permission):
            raise PermissionError(
                f"User does not have required permission: {permission}"
            )

    def bind_logger(self, **kwargs: Any) -> None:
        """
        Add context to the logger for all subsequent log calls.

        Args:
            **kwargs: Key-value pairs to add to log context

        Example:
            >>> ctx.bind_logger(session_id="abc123", user_id=str(ctx.user.id))
            >>> ctx.logger.info("event")  # Will include session_id and user_id
        """
        if self._logger is not None:
            self._logger = self._logger.bind(**kwargs)

    def __repr__(self) -> str:
        """String representation of the context."""
        return (
            f"AgentContext(user={self.user.email if self.user else None}, "
            f"request_id={self.request_id})"
        )
