Create a new agent with the following:

1. Agent implementation file at `src/agent_service/agent/custom/{agent_name}_agent.py`
2. Test file at `tests/unit/agents/test_{agent_name}_agent.py`
3. Implement the IAgent interface with:
   - `name` property (kebab-case)
   - `description` property
   - `invoke` method (synchronous execution)
   - `stream` method (streaming execution)
4. Follow the pattern from `src/agent_service/agent/examples/simple_llm_agent.py`
5. Add comprehensive docstrings
6. Include error handling
7. Add logging with structured context
8. The agent will be automatically discovered and registered on service restart

After creating the agent:
- Show the file paths where files were created
- Provide example curl command to test the agent
- Suggest next steps (adding tools, testing, deployment)
