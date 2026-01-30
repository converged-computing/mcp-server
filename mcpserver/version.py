__version__ = "0.0.13"
AUTHOR = "Vanessa Sochat"
AUTHOR_EMAIL = "vsoch@users.noreply.github.com"
NAME = "mcp-serve"
PACKAGE_URL = "https://github.com/converged-computing/mcp-server"
KEYWORDS = "cluster, orchestration, mcp, server, agents"
DESCRIPTION = "Agentic server to support MCP tools for science"
LICENSE = "LICENSE"


################################################################################
# TODO vsoch: refactor this to use newer pyproject stuff.

INSTALL_REQUIRES = (
    ("jsonschema", {"min_version": None}),
    ("Jinja2", {"min_version": None}),
    ("uvicorn", {"min_version": None}),
    ("mcp", {"min_version": None}),
    ("fastmcp", {"min_version": None}),
    ("requests", {"min_version": None}),
    ("fastapi", {"min_version": None}),
    # Yeah, probably overkill, just being used for printing the scripts
    ("rich", {"min_version": None}),
    ("textual", {"min_version": None}),
)

TESTS_REQUIRES = (("pytest", {"min_version": "4.6.2"}),)

INSTALL_REQUIRES_ALL = INSTALL_REQUIRES + TESTS_REQUIRES
