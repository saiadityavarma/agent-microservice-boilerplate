# src/agent_service/api/dependencies.py
from typing import Annotated
from fastapi import Depends

from agent_service.config.settings import Settings, get_settings
from agent_service.interfaces import IAgent
from agent_service.agent.registry import get_default_agent


# Type aliases for clean injection
AppSettings = Annotated[Settings, Depends(get_settings)]
CurrentAgent = Annotated[IAgent, Depends(get_default_agent)]


# Claude Code: Add new dependencies here following this pattern
# Example:
# async def get_my_service() -> MyService:
#     return MyService()
# MyServiceDep = Annotated[MyService, Depends(get_my_service)]
