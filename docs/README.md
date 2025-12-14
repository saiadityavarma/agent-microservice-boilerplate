# Agent Service Documentation

Welcome to the Agent Service documentation. This guide will help you build, deploy, and manage production-ready AI agents.

## 🚀 Quick Navigation

### Getting Started (Start Here!)

1. **[Quick Start Guide](./quickstart.md)** - Get running in 5 minutes
   - Docker Compose setup
   - Create first agent
   - Make first API call

2. **[Build Your First Agent](./first-agent.md)** - Step-by-step tutorial
   - Weather agent example
   - Tool integration
   - Testing and deployment

3. **[Installation Guide](./installation.md)** - Complete setup
   - Local development
   - Docker deployment
   - Kubernetes deployment
   - Configuration reference

### API Reference

4. **[Authentication](./api/authentication.md)** - Secure your service
   - Azure AD setup
   - AWS Cognito setup
   - API key management
   - RBAC implementation

5. **[Agent API](./api/agents.md)** - Agent endpoints
   - List and invoke agents
   - Streaming responses
   - Session management
   - Error handling

6. **[Tool System](./api/tools.md)** - Extend agent capabilities
   - Create custom tools
   - Built-in tools
   - Security and validation
   - Advanced patterns

7. **[Protocols](./api/protocols.md)** - MCP, A2A, AG-UI
   - Model Context Protocol (MCP)
   - Agent-to-Agent (A2A)
   - AG-UI for rich responses
   - Custom protocols

## 📖 Documentation Map

### By Role

**I'm a Developer**
1. Start: [Quick Start](./quickstart.md)
2. Learn: [First Agent](./first-agent.md)
3. Build: [Tool System](./api/tools.md)
4. Deploy: [Installation Guide](./installation.md)

**I'm a DevOps Engineer**
1. Setup: [Installation Guide](./installation.md)
2. Security: [Authentication](./api/authentication.md)
3. Deploy: Check Installation Guide K8s section
4. Monitor: Check Installation Guide Monitoring section

**I'm integrating with Claude/MCP**
1. Protocol: [MCP Documentation](./api/protocols.md)
2. Context: See `.claude/CLAUDE.md` in project root
3. Examples: Check `examples/protocols/` directory

**I'm building a UI**
1. API: [Agent API Reference](./api/agents.md)
2. Auth: [Authentication Guide](./api/authentication.md)
3. Components: [AG-UI Protocol](./api/protocols.md#ag-ui-protocol)

### By Task

**Create a new agent**
- Tutorial: [First Agent](./first-agent.md)
- Reference: [Agent API](./api/agents.md)
- Claude Code: Use `/new-agent {name}` command

**Add a new tool**
- Guide: [Tool System](./api/tools.md)
- Examples: Check `src/agent_service/tools/examples/`
- Claude Code: Use `/new-tool {name}` command

**Enable authentication**
- Guide: [Authentication](./api/authentication.md)
- Azure AD: See authentication.md Azure section
- Cognito: See authentication.md Cognito section

**Deploy to production**
- Full guide: [Installation](./installation.md)
- Kubernetes: See installation.md K8s section
- Claude Code: Use `/deploy` command

**Implement a protocol**
- MCP: [Protocols - MCP](./api/protocols.md#model-context-protocol-mcp)
- A2A: [Protocols - A2A](./api/protocols.md#agent-to-agent-protocol-a2a)
- AG-UI: [Protocols - AG-UI](./api/protocols.md#ag-ui-protocol)

## 🎯 Common Workflows

### Local Development Workflow

```bash
# 1. Quick start
cat docs/quickstart.md

# 2. Start services
docker-compose -f docker/docker-compose.yml up -d

# 3. Create agent (use Claude Code)
/new-agent my-agent

# 4. Test
curl http://localhost:8000/api/v1/agents/my-agent/invoke \
  -H "Content-Type: application/json" \
  -d '{"message": "test", "session_id": "dev"}'

# 5. View API docs
open http://localhost:8000/docs
```

### Production Deployment Workflow

```bash
# 1. Review installation guide
cat docs/installation.md

# 2. Build images
docker build -f docker/Dockerfile -t registry/agent-service:v1.0.0 --target prod .

# 3. Deploy to K8s
kubectl apply -f k8s/

# 4. Verify
kubectl get pods -n agent-service

# Or use Claude Code
/deploy
```

### Adding Authentication Workflow

```bash
# 1. Read auth guide
cat docs/api/authentication.md

# 2. Configure environment
# Edit .env:
AUTH_PROVIDER=azure_ad
AZURE_TENANT_ID=your-tenant-id
AZURE_CLIENT_ID=your-client-id
AZURE_CLIENT_SECRET=your-secret

# 3. Restart service
docker-compose restart api

# 4. Test with token
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/agents
```

## 📚 Additional Resources

### In This Repository

- **Examples**: `/examples/` directory
  - Agent examples
  - Tool examples
  - Protocol clients
  - Authentication examples

- **Reference Implementations**: `src/agent_service/*/examples/`
  - Simple LLM agent
  - LangGraph agent
  - HTTP request tool
  - Echo tool

- **Tests**: `tests/` directory
  - Unit tests
  - Integration tests
  - E2E tests

- **Claude Code Context**: `/.claude/CLAUDE.md`
  - Project architecture
  - Code patterns
  - Where to find things

### External Links

- **FastAPI Docs**: https://fastapi.tiangolo.com
- **SQLAlchemy 2.0**: https://docs.sqlalchemy.org/en/20/
- **Pydantic**: https://docs.pydantic.dev
- **Docker**: https://docs.docker.com
- **Kubernetes**: https://kubernetes.io/docs

## 🔍 Search Tips

Use your editor's search to find:
- Code examples: Search for "```python" or "```bash"
- Environment variables: Search for "UPPER_SNAKE_CASE" pattern
- API endpoints: Search for "POST /api" or "GET /api"
- Error handling: Search for "try:" or "except"
- Testing: Search for "@pytest" or "def test_"

## 🆘 Getting Help

1. **Check Documentation**
   - Start with Quick Start
   - Search for your specific topic
   - Review examples

2. **Check Examples**
   - Look in `/examples/` directory
   - Check reference implementations

3. **Use Claude Code**
   - Ask questions with full project context
   - Use slash commands for common tasks
   - Reference `.claude/CLAUDE.md` for patterns

4. **Review Logs**
   ```bash
   # Docker Compose
   docker-compose logs -f api

   # Kubernetes
   kubectl logs -f deployment/agent-service-api -n agent-service
   ```

## 📝 Documentation Standards

All documentation follows these principles:

- **Copy-paste ready**: All code examples work as-is
- **Complete**: Include all necessary imports and setup
- **Tested**: Examples are tested and verified
- **Real-world**: Use realistic scenarios, not toy examples
- **Multi-language**: Python, JavaScript, Bash examples
- **Error handling**: Show how to handle failures
- **Security**: Include security considerations
- **Production-ready**: Best practices for production

## 🔄 Updates

Documentation is kept in sync with code:
- Version controlled in Git
- Updated with each major release
- Tested examples on each release
- Cross-references maintained

## 📄 License

This documentation is part of the Agent Service project.

---

**Last Updated**: 2024-12-14
**Documentation Version**: 1.0
**Project Path**: `/Users/saiadityavarmavuppalapati/Downloads/agents_boiler_plate/`

## Quick Links

- [Quick Start](./quickstart.md) - Get started in 5 minutes
- [First Agent](./first-agent.md) - Build your first agent
- [Installation](./installation.md) - Deploy to production
- [Authentication](./api/authentication.md) - Secure your service
- [Agent API](./api/agents.md) - API reference
- [Tool System](./api/tools.md) - Extend capabilities
- [Protocols](./api/protocols.md) - MCP, A2A, AG-UI
