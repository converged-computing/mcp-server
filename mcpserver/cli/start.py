import warnings

import uvicorn
from fastapi import FastAPI

# Ignore these for now
warnings.filterwarnings("ignore", category=DeprecationWarning, module="websockets.legacy")
warnings.filterwarnings(
    "ignore", category=DeprecationWarning, module="uvicorn.protocols.websockets"
)


from mcpserver.app import init_mcp
from mcpserver.cli.manager import get_manager
from mcpserver.core.config import MCPConfig

# These are routes also served here
from mcpserver.routes import *


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

    # Get the tool manager and register discovered tools
    mcp = init_mcp(cfg.exclude, cfg.include, args.mask_error_details)
    get_manager(mcp, cfg)

    # Create ASGI app from MCP server
    mcp_app = mcp.http_app(path=cfg.server.path)
    app = FastAPI(title="MCP Server", lifespan=mcp_app.lifespan)

    # Mount the MCP server. Note from V: we can use mount with antother FastMCP
    # mcp.run can also be replaced with mcp.run_async
    app.mount("/", mcp_app)
    try:

        # http transports can accept a host and port
        if "http" in cfg.server.transport:
            # mcp.run(transport=cfg.server.transport, port=cfg.server.port, host=cfg.server.host)
            uvicorn.run(
                app,
                host=cfg.server.host,
                port=cfg.server.port,
                ssl_keyfile=cfg.server.ssl_keyfile,
                ssl_certfile=cfg.server.ssl_certfile,
                timeout_graceful_shutdown=75,
                timeout_keep_alive=60,
            )

        # stdio does not!
        else:
            mcp.run(transport=cfg.server.transport)

    # For testing we usually control+C, let's not make it ugly
    except KeyboardInterrupt:
        print("🖥️  Shutting down...")
