"""
Agent configuration models and loaders.

Supports per-agent configuration with YAML file loading and runtime overrides.
"""

from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field
import yaml
from pathlib import Path


class AgentConfig(BaseModel):
    """
    Configuration for agent behavior and resource limits.

    Attributes:
        timeout: Maximum execution time in seconds
        max_tokens: Maximum tokens for LLM responses
        temperature: Sampling temperature (0.0-2.0)
        enabled_tools: Whitelist of tool names (None = all enabled)
        disabled_tools: Blacklist of tool names
        rate_limit: Rate limit string (e.g., "100/hour", "10/minute")
        model: LLM model identifier (e.g., "gpt-4", "claude-3-opus")
        streaming: Enable streaming responses by default
        retry_attempts: Number of retry attempts on failure
        retry_delay: Delay between retries in seconds
        metadata: Additional custom configuration
    """

    timeout: int = Field(default=300, ge=1, description="Timeout in seconds")
    max_tokens: int = Field(default=4096, ge=1, description="Maximum tokens")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Sampling temperature")
    enabled_tools: list[str] | None = Field(default=None, description="Whitelist of tools")
    disabled_tools: list[str] | None = Field(default=None, description="Blacklist of tools")
    rate_limit: str | None = Field(default="100/hour", description="Rate limit (e.g., '100/hour')")
    model: str | None = Field(default=None, description="LLM model identifier")
    streaming: bool = Field(default=False, description="Enable streaming by default")
    retry_attempts: int = Field(default=3, ge=0, description="Number of retry attempts")
    retry_delay: float = Field(default=1.0, ge=0.0, description="Retry delay in seconds")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Custom metadata")

    model_config = {
        "extra": "allow",  # Allow additional fields for framework-specific config
    }

    def merge(self, other: AgentConfig) -> AgentConfig:
        """
        Merge this config with another, with other taking precedence.

        Args:
            other: Configuration to merge with

        Returns:
            New merged configuration
        """
        data = self.model_dump()
        other_data = other.model_dump(exclude_unset=True)

        # Merge metadata separately
        if "metadata" in other_data and other_data["metadata"]:
            data["metadata"] = {**data.get("metadata", {}), **other_data["metadata"]}
            del other_data["metadata"]

        data.update(other_data)
        return AgentConfig(**data)

    def filter_tools(self, available_tools: list[str]) -> list[str]:
        """
        Apply tool filtering based on enabled/disabled lists.

        Args:
            available_tools: List of all available tool names

        Returns:
            Filtered list of tool names
        """
        tools = set(available_tools)

        # Apply whitelist if specified
        if self.enabled_tools is not None:
            tools = tools.intersection(set(self.enabled_tools))

        # Apply blacklist if specified
        if self.disabled_tools is not None:
            tools = tools.difference(set(self.disabled_tools))

        return sorted(list(tools))

    @classmethod
    def from_yaml(cls, file_path: str | Path) -> AgentConfig:
        """
        Load configuration from YAML file.

        Args:
            file_path: Path to YAML configuration file

        Returns:
            Loaded configuration

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If YAML is invalid
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {file_path}")

        try:
            with open(path, "r") as f:
                data = yaml.safe_load(f)

            if data is None:
                data = {}

            return cls(**data)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in {file_path}: {e}")
        except Exception as e:
            raise ValueError(f"Error loading config from {file_path}: {e}")

    def to_yaml(self, file_path: str | Path) -> None:
        """
        Save configuration to YAML file.

        Args:
            file_path: Path to save configuration
        """
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w") as f:
            yaml.safe_dump(
                self.model_dump(exclude_none=True),
                f,
                default_flow_style=False,
                sort_keys=False,
            )


class AgentConfigLoader:
    """
    Loads and manages agent configurations from various sources.
    """

    def __init__(self, config_dir: str | Path | None = None):
        """
        Initialize config loader.

        Args:
            config_dir: Directory containing agent config files
        """
        self.config_dir = Path(config_dir) if config_dir else None
        self._cache: dict[str, AgentConfig] = {}

    def load(self, agent_name: str, defaults: AgentConfig | None = None) -> AgentConfig:
        """
        Load configuration for an agent.

        Loads from: {config_dir}/{agent_name}.yaml
        Falls back to defaults if file doesn't exist.

        Args:
            agent_name: Name of the agent
            defaults: Default configuration to use

        Returns:
            Loaded or default configuration
        """
        if agent_name in self._cache:
            return self._cache[agent_name]

        config = defaults or AgentConfig()

        if self.config_dir:
            config_file = self.config_dir / f"{agent_name}.yaml"
            if config_file.exists():
                try:
                    file_config = AgentConfig.from_yaml(config_file)
                    config = config.merge(file_config)
                except Exception as e:
                    # Log warning but continue with defaults
                    import warnings
                    warnings.warn(f"Failed to load config for {agent_name}: {e}")

        self._cache[agent_name] = config
        return config

    def save(self, agent_name: str, config: AgentConfig) -> None:
        """
        Save configuration for an agent.

        Args:
            agent_name: Name of the agent
            config: Configuration to save

        Raises:
            ValueError: If config_dir is not set
        """
        if not self.config_dir:
            raise ValueError("config_dir must be set to save configurations")

        self.config_dir.mkdir(parents=True, exist_ok=True)
        config_file = self.config_dir / f"{agent_name}.yaml"
        config.to_yaml(config_file)
        self._cache[agent_name] = config

    def clear_cache(self) -> None:
        """Clear the configuration cache."""
        self._cache.clear()


# Global config loader instance
_global_loader: AgentConfigLoader | None = None


def set_config_dir(config_dir: str | Path) -> None:
    """
    Set the global configuration directory.

    Args:
        config_dir: Path to configuration directory
    """
    global _global_loader
    _global_loader = AgentConfigLoader(config_dir)


def get_config(agent_name: str, defaults: AgentConfig | None = None) -> AgentConfig:
    """
    Get configuration for an agent using global loader.

    Args:
        agent_name: Name of the agent
        defaults: Default configuration

    Returns:
        Agent configuration
    """
    global _global_loader
    if _global_loader is None:
        _global_loader = AgentConfigLoader()
    return _global_loader.load(agent_name, defaults)
