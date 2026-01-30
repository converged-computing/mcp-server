#!/usr/bin/env python

import os

default_port = os.environ.get("MCPSERVER_PORT") or 8000
default_host = os.environ.get("MCPSERVER_HOST") or "0.0.0.0"
default_path = os.environ.get("MCPSERVER_PATH") or "/mcp"


def populate_start_args(start):
    """
    Given the argparse parser, add start args to it.

    We provide this so a secondary library can consistently
    add parsing args to its parser.
    """
    start.add_argument(
        "--port", default=default_port, type=int, help="port to run the agent gateway"
    )

    # Note from V: SSE is considered deprecated (don't use it...)
    start.add_argument(
        "-t",
        "--transport",
        default="stdio",
        help="Transport to use (defaults to stdin)",
        choices=["stdio", "http", "sse", "streamable-http"],
    )
    start.add_argument("--host", default=default_host, help=f"Host (defaults to {default_host})")
    start.add_argument(
        "--tool-module",
        action="append",
        help="Additional tool module paths to discover from.",
        default=[],
    )
    start.add_argument("--tool", action="append", help="Direct tool to import.", default=[])
    start.add_argument("--resource", action="append", help="Direct resource to import.", default=[])
    start.add_argument("--prompt", action="append", help="Direct prompt to import.", default=[])
    start.add_argument("--include", help="Include tags", action="append", default=None)
    start.add_argument("--exclude", help="Exclude tag", action="append", default=None)
    start.add_argument("--path", help="Server path for mcp", default=default_path)
    start.add_argument("--config", help="Configuration file for server.")

    # Args for ssl
    start.add_argument("--ssl-keyfile", default=None, help="SSL key file (e.g. key.pem)")
    start.add_argument("--ssl-certfile", default=None, help="SSL certificate file (e.g. cert.pem)")
    start.add_argument(
        "--mask-error_details",
        help="Mask error details (for higher security deployments)",
        action="store_true",
        default=False,
    )
