"""Business-logic service layer.

Services own all business logic and database access. Routers are thin
(5-15 lines) and delegate everything here. Services never import from
routers. Database access never leaks out of the service layer.

Per .cursorrules conventions:
- Every service function is async (I/O-bound work)
- Services call app.llm.client for LLM calls — never import anthropic directly
- LLM call logging is handled by the client wrapper; services do not write to
  LLMCall themselves
- Exceptions from external calls propagate to the router layer, which
  translates them to appropriate HTTP responses
"""
