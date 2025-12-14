# Agent Microservice Boilerplate - Project Overview

## Purpose
Create a **scaffold/boilerplate** that enables Claude Code to generate consistent, production-ready agent microservice code. This is NOT an implementation guide—it's a **pattern library** with interfaces, contracts, and conventions.

## Goals
1. **Guardrails for Claude Code** - Clear patterns to follow, reducing mistakes
2. **Framework Agnostic** - Agent framework is pluggable (LangGraph, AutoGen, CrewAI, custom, etc.)
3. **Protocol Ready** - Stubs for MCP, A2A, AG-UI with clear interfaces
4. **Production Patterns** - Auth, logging, DB, config already wired
5. **Extensible** - Claude Code adds features by implementing interfaces, not modifying core

## What This Boilerplate Provides

### Structure (Claude Code knows where things go)
```
src/agent_service/
├── interfaces/          # Abstract classes & protocols - THE CONTRACTS
├── config/              # Settings pattern
├── api/                 # FastAPI routes, middleware
├── protocols/           # MCP, A2A, AG-UI stubs
├── agent/               # Agent interface + placeholder
├── tools/               # Tool interface + examples
├── infrastructure/      # DB, cache, observability
└── domain/              # Domain models
```

### Interfaces (Claude Code implements these)
- `IAgent` - Any agent framework implements this
- `ITool` - Tools follow this contract
- `IProtocolHandler` - Protocol handlers implement this
- `IRepository` - Data access pattern

### Patterns (Claude Code copies these)
- Dependency injection via FastAPI Depends
- Structured logging with context
- Error handling hierarchy
- Streaming response pattern
- Configuration with validation

## Task Summary

| Task | Purpose | Deliverable |
|------|---------|-------------|
| 01 | Project Structure | Directory scaffold + pyproject.toml |
| 02 | Core Interfaces | Abstract classes for Agent, Tool, Protocol |
| 03 | Configuration | Pydantic Settings pattern |
| 04 | FastAPI Foundation | App factory, middleware, error handling |
| 05 | Database Patterns | Connection, base model, repository interface |
| 06 | Protocol Stubs | MCP, A2A, AG-UI interface + minimal example |
| 07 | Agent Interface | IAgent + placeholder implementation |
| 08 | Tool System | ITool interface + registration pattern |
| 09 | Observability | Logging, metrics, tracing patterns |
| 10 | Docker & Scripts | Development environment |

## Success Criteria
When complete, Claude Code should be able to:
- [ ] Add a new tool by implementing `ITool`
- [ ] Swap agent framework by implementing `IAgent`
- [ ] Add protocol support by implementing `IProtocolHandler`
- [ ] Add database models following the base pattern
- [ ] Know exactly where to put new code
- [ ] Follow established error handling
- [ ] Use consistent logging patterns
