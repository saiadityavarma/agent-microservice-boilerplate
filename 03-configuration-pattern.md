# Task 03: Configuration Pattern

## Objective
Establish the configuration pattern using Pydantic Settings. Claude Code adds new config by extending this pattern.

## Deliverables

### Settings Class
```python
# src/agent_service/config/settings.py
from functools import lru_cache
from typing import Literal
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment.
    
    Claude Code: Add new settings here following this pattern:
    - Use type hints
    - Provide sensible defaults for optional settings
    - Use SecretStr for sensitive values
    - Add validation where needed
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    # Application
    app_name: str = "Agent Service"
    app_version: str = "0.1.0"
    environment: Literal["local", "dev", "staging", "prod"] = "local"
    debug: bool = False
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    
    # Database (optional - only if using DB)
    database_url: SecretStr | None = None
    
    # Redis (optional - only if using cache)
    redis_url: SecretStr | None = None
    
    # Auth (optional)
    secret_key: SecretStr | None = None
    
    # Feature Flags - protocols
    enable_mcp: bool = True
    enable_a2a: bool = True
    enable_agui: bool = True
    
    # ──────────────────────────────────────────────
    # Claude Code: Add new settings below this line
    # ──────────────────────────────────────────────
    
    @property
    def is_production(self) -> bool:
        return self.environment == "prod"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
```

### .env.example
```bash
# Application
APP_NAME="Agent Service"
ENVIRONMENT=local
DEBUG=true

# Server
HOST=0.0.0.0
PORT=8000

# Database (optional)
DATABASE_URL=postgresql://user:pass@localhost:5432/agent_db

# Redis (optional)
REDIS_URL=redis://localhost:6379/0

# Auth (required in production)
SECRET_KEY=your-secret-key

# Feature Flags
ENABLE_MCP=true
ENABLE_A2A=true
ENABLE_AGUI=true
```

## Pattern for Claude Code

When adding new configuration:
```python
# 1. Add to Settings class
class Settings(BaseSettings):
    ...
    # My new feature settings
    my_feature_api_key: SecretStr | None = None
    my_feature_timeout: int = 30

# 2. Add to .env.example
MY_FEATURE_API_KEY=
MY_FEATURE_TIMEOUT=30

# 3. Use in code via dependency injection
from agent_service.config.settings import get_settings

def my_function():
    settings = get_settings()
    timeout = settings.my_feature_timeout
```

## Acceptance Criteria
- [ ] Settings load from environment
- [ ] Settings load from .env file
- [ ] SecretStr used for sensitive values
- [ ] `.env.example` documents all variables
