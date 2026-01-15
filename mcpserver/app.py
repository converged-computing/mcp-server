import os

from fastmcp import FastMCP
from mcp.types import Icon

import mcpserver.version as version
from mcpserver.middleware import MCPRequestLogger, TokenAuthMiddleware

icons = [
    Icon(
        src="https://built.careers/files/pictures/01111111.png",
        mimeType="image/png",
        sizes=["48x48"],
    ),
    Icon(
        src="https://flux-framework.org/assets/images/Flux-logo-mark-only-full-color.png",
        mimeType="image/png",
        sizes=["96x96"],
    ),
]

mcp = FastMCP(
    name="MCP Server Gateway",
    instructions="This server provides tools for HPC and scientific workloads.",
    website_url="https://github.com/converged-computing/mcpserver",
    version=version.__version__,
    icons=icons,
    # Throw up if we accidentally define a tool with the same name
    on_duplicate_tools="error",
)

# Authentication - let's do simple BearerToken from environment for now
auth_token = os.environ.get("MCPSERVER_TOKEN")
auth = None
if auth_token:
    auth = TokenAuthMiddleware(auth_token)
    mcp.add_middleware(auth)

mcp.add_middleware(MCPRequestLogger())


def init_mcp(exclude_tags=None, include_tags=None, mask_error_details=False):
    """
    Function to init app. Doesn't need to be called at start as long as called
    to update global context.
    """
    global mcp

    mcp.exclude_tags = set(exclude_tags or []) or None
    mcp.include_tags = set(include_tags or []) or None
    mcp.mask_error_details = mask_error_details
    return mcp
