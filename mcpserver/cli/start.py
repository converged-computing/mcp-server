import asyncio
import warnings
from contextlib import asynccontextmanager

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
from mcpserver.core.hub import HubManager
from mcpserver.core.worker import WorkerManager
from mcpserver.logger import logger

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

    # Setup Hub (parent role)
    if args.hub:
        mcp.hub_manager = HubManager(
            mcp, host=cfg.server.host, port=cfg.server.port, secret=args.hub_secret
        )

    # Setup Worker (child role) - triggered by --join
    if args.join:

        # Require a join secret
        if not args.join_secret:
            logger.exit("A --join-secret is required to register with a hub.")
        public_url = (
            args.public_url or f"http://{cfg.server.host}:{cfg.server.port}{cfg.server.path}"
        )
        mcp.worker_manager = WorkerManager(
            mcp,
            hub_url=args.join,
            secret=args.join_secret,
            worker_id=args.register_id,
            public_url=public_url,
        )

    mcp_app = mcp.http_app(path=cfg.server.path)

    # 3. Modern Chained Lifespan Fix
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Startup: Logic for Worker registration
        if hasattr(mcp, "worker_manager"):
            asyncio.create_task(mcp.worker_manager.run_registration())

        # Chain: Execute FastMCP's internal lifespan context
        async with mcp_app.router.lifespan_context(app):
            yield

    app = FastAPI(title="MCP Server", lifespan=lifespan)

    # Bind the /register endpoint if we are a Hub
    if args.hub:
        mcp.hub_manager.bind_to_app(app)

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
