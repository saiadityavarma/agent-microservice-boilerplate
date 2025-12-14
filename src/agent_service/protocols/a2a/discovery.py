"""
A2A discovery module for agent card generation.

This module provides functionality to generate agent cards that describe
the agent's capabilities, skills, and metadata for the A2A protocol.
"""
from typing import Any
from pydantic import BaseModel, Field

from agent_service.config.settings import get_settings
from agent_service.tools.registry import tool_registry


class AgentSkill(BaseModel):
    """Agent skill definition for A2A agent card."""
    name: str = Field(..., description="Skill name")
    description: str = Field(..., description="Skill description")
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="JSON Schema for skill parameters"
    )
    examples: list[str] = Field(
        default_factory=list,
        description="Example usage of this skill"
    )


class AgentCard(BaseModel):
    """A2A agent card describing agent capabilities."""
    name: str = Field(..., description="Agent name")
    description: str = Field(..., description="Agent description")
    version: str = Field(..., description="Agent version")
    url: str = Field(..., description="Agent base URL")
    capabilities: dict[str, bool] = Field(
        default_factory=dict,
        description="Agent capabilities"
    )
    skills: list[AgentSkill] = Field(
        default_factory=list,
        description="Agent skills (tools)"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata"
    )
    authentication: dict[str, Any] = Field(
        default_factory=dict,
        description="Authentication requirements"
    )


class AgentDiscovery:
    """
    Agent discovery service for generating agent cards.

    Automatically generates agent cards from registered tools and configuration.
    """

    def __init__(self):
        """Initialize agent discovery."""
        self.settings = get_settings()

    def generate_agent_card(
        self,
        base_url: str = "",
        include_skills: bool = True
    ) -> dict[str, Any]:
        """
        Generate A2A agent card.

        Args:
            base_url: Base URL for the agent service
            include_skills: Whether to include skills (tools) in the card

        Returns:
            Agent card as dictionary
        """
        # Build capabilities
        capabilities = {
            "streaming": True,
            "pushNotifications": False,
            "taskManagement": True,
            "fileHandling": False,  # Can be enabled when file upload is implemented
            "structuredData": True,
        }

        # Build skills from tool registry
        skills = []
        if include_skills:
            skills = self._generate_skills_from_tools()

        # Build authentication info
        auth_methods = []
        if self.settings.secret_key:
            auth_methods.append("bearer")
        auth_methods.append("api_key")

        authentication = {
            "required": True,
            "methods": auth_methods,
            "description": "API key or bearer token required"
        }

        # Build metadata
        metadata = {
            "environment": self.settings.environment,
            "protocols": ["a2a", "mcp", "agui"] if self.settings.enable_mcp and self.settings.enable_agui else ["a2a"],
            "frameworks": ["fastapi"],
        }

        # Generate agent card
        agent_card = AgentCard(
            name=self.settings.app_name,
            description="Multi-protocol agent service supporting A2A, MCP, and AG-UI protocols",
            version=self.settings.app_version,
            url=base_url or "/a2a",
            capabilities=capabilities,
            skills=skills,
            metadata=metadata,
            authentication=authentication
        )

        return agent_card.model_dump(mode='json', exclude_none=True)

    def _generate_skills_from_tools(self) -> list[AgentSkill]:
        """
        Generate skills list from registered tools.

        Returns:
            List of agent skills
        """
        skills = []

        for tool_schema in tool_registry.list_tools():
            skill = AgentSkill(
                name=tool_schema.name,
                description=tool_schema.description,
                parameters=tool_schema.parameters,
                examples=[]  # Can be populated from tool metadata if available
            )
            skills.append(skill)

        return skills

    def get_well_known_config(self, base_url: str = "") -> dict[str, Any]:
        """
        Generate .well-known/agent.json configuration.

        This is the standard discovery endpoint for A2A agents.

        Args:
            base_url: Base URL for the agent service

        Returns:
            Well-known configuration dictionary
        """
        return self.generate_agent_card(base_url=base_url, include_skills=True)

    def get_skills_manifest(self) -> dict[str, Any]:
        """
        Get skills manifest with detailed tool information.

        Returns:
            Skills manifest dictionary
        """
        skills = self._generate_skills_from_tools()
        return {
            "skills": [skill.model_dump(mode='json') for skill in skills],
            "total": len(skills),
            "version": self.settings.app_version
        }


# Global discovery instance
_discovery: AgentDiscovery | None = None


def get_agent_discovery() -> AgentDiscovery:
    """
    Get the global agent discovery instance.

    Returns:
        Global AgentDiscovery instance
    """
    global _discovery
    if _discovery is None:
        _discovery = AgentDiscovery()
    return _discovery
