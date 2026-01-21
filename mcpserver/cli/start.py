from fastapi import FastAPI

from mcpserver.app import init_mcp
from mcpserver.core.config import MCPConfig

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
    if args.config is not None:
        print(f"📖 Loading config from {args.config}")
        cfg = MCPConfig.from_yaml(args.config)
    else:
        cfg = MCPConfig.from_args(args)

    mcp = init_mcp(cfg.exclude, cfg.include, args.mask_error_details)

    # Create ASGI app from MCP server
    mcp_app = mcp.http_app(path=cfg.server.path)
    app = FastAPI(title="MCP Server", lifespan=mcp_app.lifespan)

    # Dynamic Loading of Tools
    print(f"🔌 Loading tools... ")
    async_mode = getattr(cfg, "async_execution", False)

    # Add additional module paths (custom out of tree modules)
    for path in cfg.discovery:
        print(f"🧐 Registering additional module: {path}")
        manager.register(path)

    # explicit egistration
    for endpoint in register(mcp, cfg):
        print(f"   ✅ Registered: {endpoint.name}")

    # Load into the manager (tools, resources, prompts)
    for tool in manager.load_tools(mcp, cfg.include, cfg.exclude):
        print(f"   ✅ Registered: {tool.name}")

    # Mount the MCP server. Note from V: we can use mount with antother FastMCP
    # mcp.run can also be replaced with mcp.run_async
    app.mount("/", mcp_app)
    try:

        # http transports can accept a host and port
        if "http" in cfg.server.transport:
            mcp.run(transport=cfg.server.transport, port=cfg.server.port, host=cfg.server.host)

        # stdio does not!
        else:
            mcp.run(transport=cfg.server.transport)

    # For testing we usually control+C, let's not make it ugly
    except KeyboardInterrupt:
        print("🖥️  Shutting down...")


def register(mcp, cfg: MCPConfig):
    """
    Registers specific tools, prompts, and resources defined in the config.
    Replaces the previous args-based register function.
    """
    # Define which config lists map to which manager methods
    registries = [
        (cfg.tools, manager.register_tool),
        (cfg.prompts, manager.register_prompt),
        (cfg.resources, manager.register_resource),
    ]

    for capability_list, register_func in registries:
        for item in capability_list:
            as_job = item.job if item.job is not None else cfg.jobs.enabled
            # item is a Capability object with .path and .name
            yield register_func(mcp, item.path, name=item.name, as_job=as_job)
