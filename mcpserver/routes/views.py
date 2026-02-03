from starlette.responses import JSONResponse

from mcpserver.app import mcp


@mcp.custom_route("/health", methods=["GET"])
async def health_check(_):
    return JSONResponse({"status": 200, "message": "OK"})


@mcp.custom_route("/tools/list", methods=["GET"])
async def list_tools(_):
    """
    Courtesy function to get the same JSON structure as the MCP JSON-RPC tools/list
    """
    # FastMCP stores its tools in a list of Tool objects
    tools = await mcp._tool_manager.get_tools()
    return JSONResponse(
        {
            "tools": [
                {"name": tool.name, "description": tool.description, "inputSchema": tool.parameters}
                for _, tool in tools.items()
            ]
        }
    )


@mcp.custom_route("/prompts/list", methods=["GET"])
async def list_prompts(_):
    """List prompts, ditto above"""
    prompts = await mcp._prompt_manager.get_prompts()
    return JSONResponse(
        {
            "prompts": [
                {
                    "name": tool.name,
                    "description": tool.description,
                }
                for _, tool in prompts.items()
            ]
        }
    )


@mcp.custom_route("/resources/list", methods=["GET"])
async def list_resources(_):
    """And resources! I haven't tested this one yet."""
    resources = await mcp._resource_manager.get_resources()
    return JSONResponse(
        {
            "resources": [
                {
                    "name": tool.name,
                    "description": tool.description,
                    # This is untested, we don't have resources yet
                    "mimeType": tool.mime_type,
                }
                for _, tool in resources.items()
            ]
        }
    )
