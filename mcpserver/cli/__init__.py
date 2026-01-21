#!/usr/bin/env python

import argparse
import os
import sys
from mcpserver.cli.logging import *

# This will pretty print all exceptions in rich
from rich.traceback import install

install()

import mcpserver
from mcpserver.logger import setup_logger

default_port = os.environ.get("MCPSERVER_PORT") or 8000


def get_parser():
    parser = argparse.ArgumentParser(
        description="MCP Server",
        formatter_class=argparse.RawTextHelpFormatter,
    )

    # Global Variables
    parser.add_argument(
        "--debug",
        dest="debug",
        help="use verbose logging to debug.",
        default=False,
        action="store_true",
    )

    parser.add_argument(
        "--quiet",
        dest="quiet",
        help="suppress additional output.",
        default=False,
        action="store_true",
    )
    parser.add_argument(
        "--version",
        dest="version",
        help="show software version.",
        default=False,
        action="store_true",
    )

    subparsers = parser.add_subparsers(
        help="actions",
        title="actions",
        description="actions",
        dest="command",
    )
    subparsers.add_parser("version", description="show software version")

    # Start MCP workers
    start = subparsers.add_parser(
        "start",
        formatter_class=argparse.RawTextHelpFormatter,
        description="generate subsystem metadata for a cluster",
    )
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
    start.add_argument("--host", default="0.0.0.0", help="Host (defaults to 0.0.0.0)")
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
    start.add_argument("--path", help="Server path for mcp", default="/mcp")
    start.add_argument("--config", help="Configuration file for server.")

    start.add_argument(
        "--mask-error_details",
        help="Mask error details (for higher security deployments)",
        action="store_true",
        default=False,
    )
    return parser


def run_start():
    """
    this is the main entrypoint.
    """
    parser = get_parser()

    def help(return_code=0):
        version = mcpserver.__version__

        print("\nMCP Server v%s" % version)
        parser.print_help()
        sys.exit(return_code)

    # If the user didn't provide any arguments, show the full help
    if len(sys.argv) == 1:
        help()

    # If an error occurs while parsing the arguments, the interpreter will exit with value 2
    args, extra = parser.parse_known_args()

    if args.debug is True:
        os.environ["MESSAGELEVEL"] = "DEBUG"

    # Show the version and exit
    if args.command == "version" or args.version:
        print(mcpserver.__version__)
        sys.exit(0)

    setup_logger(quiet=args.quiet, debug=args.debug)

    # Here we can assume instantiated to get args
    if args.command == "start":
        from .start import main
    else:
        help(1)
    main(args, extra)


if __name__ == "__main__":
    run_start()
