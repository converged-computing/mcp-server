import json
from typing import Callable

from fastapi import Request
from fastmcp.server.middleware import Middleware


class MCPRequestLogger(Middleware):
    """
    Debug middleware to print raw MCP traffic.
    Uses print() to bypass logging configuration issues.
    """

    async def __call__(self, request: Request, call_next: Callable):
        method = request.method
        if method not in ["initialize", "tools/list", "prompts/list", "resources/list", None]:
            print(f"   [MCP] Method: {method}", flush=True)

        if method == "tools/call":
            tool_name = request.message.name
            print(f"\n🔎 [MCP] Call Tool: \033[96m{tool_name}\033[0m", flush=True)
            print(f"   Args: {json.dumps(request.message.arguments, indent=2)}", flush=True)

        elif method == "prompts/get":
            prompt_name = request.message.name
            print(f"\n📥 [MCP] Get Prompt: \033[92m{prompt_name}\033[0m", flush=True)
            print(f"   Context: {json.dumps(request.message.arguments, indent=2)}", flush=True)

        response = await call_next(request)
        return response
