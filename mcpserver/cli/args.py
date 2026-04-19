#!/usr/bin/env python

import os
import socket

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
        default="http",
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
    start.add_argument(
        "--event", action="append", help="Direct event stream to import.", default=[]
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

    # Hub Group
    hub_group = start.add_argument_group("🦞 Hub Mode")
    hub_group.add_argument(
        "--hub",
        action="store_true",
        help="Start the server in Hub mode to aggregate remote workers.",
    )
    hub_group.add_argument(
        "--hub-secret",
        default=os.environ.get("MCP_HUB_SECRET"),
        help="Secret key required for workers to register. (Auto-generated if omitted)",
    )
    hub_group.add_argument(
        "--batch",
        default=None,
        type=int,
        help="make requests to workers in batches of X (e.g., for experiments)",
    )
    hub_group.add_argument(
        "--serial",
        action="store_true",
        help="Run the hub in serial mode (ideal for experiments on single machines)",
        default=False,
    )
    # Dual mode means "I am a hub AND a worker" - added this for dispatch experiments
    hub_group.add_argument(
        "--dual",
        action="store_true",
        help="Start as both a Hub and a Worker (registers local resources to the fleet).",
    )

    # Worker Registration Group
    worker_group = start.add_argument_group("🐝 Worker Registration")
    worker_group.add_argument(
        "--join", help="URL of the MCP Hub to join (e.g., http://hub-host:8089)"
    )
    worker_group.add_argument(
        "--join-secret",
        help="The registration secret provided by the Hub.",
        default=os.environ.get("MCPSERVER_JOIN_SECRET"),
    )
    worker_group.add_argument(
        "--worker-id",
        help="Unique ID for this worker. Defaults to the hostname.",
        default=socket.gethostname(),
    )
    worker_group.add_argument(
        "--public-url",
        help="The URL the Hub should use to reach this worker (e.g. http://ip:port/mcp)",
    )
    worker_group.add_argument(
        "--verbose",
        help="Request worker to send back a second block with provider calls",
        action="store_true",
        default=False,
    )
    # const=True is what we get if the flag is present but no value is given
    # default=False is what we get if the flag is totally absent
    # THe user can also ask for an archetype (hpc, cloud, standalone)
    worker_group.add_argument(
        "--mock",
        nargs="?",
        const=True,
        default=False,
        help="Start a mock worker. Can optionally select hpc, cloud, or standalone",
    )

    # Agent Reasoning Group
    agent_group = start.add_argument_group("🧠 Agent Reasoning")
    agent_group.add_argument(
        "--llm-backend",
        help="LLM provider (gemini, openai). Env: RESOURCE_SECRETARY_LLM",
    )
    agent_group.add_argument(
        "--llm-model",
        help="Specific model name. Env: RESOURCE_SECRETARY_MODEL",
    )
    agent_group.add_argument(
        "--llm-api-base",
        help="Base URL for the API (OpenAI/Local only). Env: RESOURCE_SECRETARY_API_BASE",
    )
