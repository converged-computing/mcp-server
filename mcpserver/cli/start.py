from fastapi import FastAPI

from mcpserver.app import init_mcp

# These are routes also served here
from mcpserver.routes import *
from mcpserver.tools.manager import ToolManager

# Discover and register defaults
manager = ToolManager()
manager.register()


def main(args, extra, **kwargs):
    """
    Starts the MCP Gateway with the specified tools.
    Usage: mcpserver start <tool-a> <tool-b>
    """
    mcp = init_mcp(args.exclude, args.include, args.mask_error_details)

    # Create ASGI app from MCP server
    mcp_app = mcp.http_app(path="/mcp")
    app = FastAPI(title="MCP Server", lifespan=mcp_app.lifespan)

    # Add additional module paths (custom out of tree modules)
    for path in args.tool_module:
        print(f"🧐 Registering additional module: {path}")
        manager.register(path)

    # Dynamic Loading of Tools
    print(f"🔌 Loading tools... ")

    # Load into the manager (tools, resources, prompts)
    for tool in manager.load_tools(mcp, args.tools, args.include, args.exclude):
        print(f"   ✅ Registered: {tool.name}")

    # Plus additional tools, prompts, resources
    for tool in register(mcp, args):
        print(f"   ✅ Registered: {tool.name}")

    # Mount the MCP server. Note from V: we can use mount with antother FastMCP
    # mcp.run can also be replaced with mcp.run_async
    app.mount("/", mcp_app)
    try:

        # http transports can accept a host and port
        if "http" in args.transport:
            mcp.run(transport=args.transport, port=args.port, host=args.host)

        # stdio does not!
        else:
            mcp.run(transport=args.transport)

    # For testing we usually control+C, let's not make it ugly
    except KeyboardInterrupt:
        print("🖥️  Shutting down...")


def register(mcp, args):
    """
    Register additional tools, resources, and prompts.
    """
    for path in args.tool:
        yield manager.register_tool(mcp, path)

    for path in args.resource:
        yield manager.register_resource(mcp, path)

    for path in args.prompt:
        yield manager.register_prompt(mcp, path)
