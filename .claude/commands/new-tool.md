Create a new tool with the following:

1. Tool implementation file at `src/agent_service/tools/custom/{tool_name}_tool.py`
2. Test file at `tests/unit/tools/test_{tool_name}_tool.py`
3. Implement the ITool interface with:
   - `schema` property (returns ToolSchema with JSON Schema format)
   - `execute` method (async execution with **kwargs)
   - `requires_confirmation` property (default False)
4. Follow the pattern from `src/agent_service/tools/examples/http_request.py`
5. Include:
   - Clear tool name (snake_case)
   - Descriptive tool description for LLM
   - Detailed parameter schema with types and descriptions
   - Required vs optional parameters
   - Input validation
   - Error handling
   - Type hints
6. Add comprehensive docstrings
7. The tool will be automatically available to all agents

After creating the tool:
- Show the file paths where files were created
- Provide example of how to use the tool in an agent
- Show the JSON schema that will be sent to LLMs
- Suggest testing approach
