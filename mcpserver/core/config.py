from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import yaml

import mcpserver.defaults as defaults


@dataclass
class Capability:
    """
    Strictly structured tool, prompt, or resource.
    Path (function path) is required, name is optional to change reference.
    """

    path: str
    name: Optional[str] = None

    def __post_init__(self):
        # No go, bro.
        if not self.path:
            raise ValueError("Capability for tool, prompt, or resource must have a non-empty path")
        if not self.name:
            # If no name, assume function name.
            self.name = self.path.split(".")[-1]


@dataclass(frozen=True)
class ServerConfig:
    """
    Server runtime settings.
    """

    transport: str = defaults.transport
    ssl_keyfile: str = None
    ssl_certfile: str = None
    port: int = int(defaults.port)
    host: str = defaults.host
    path: str = defaults.path


@dataclass(frozen=True)
class MCPConfig:
    """
    The Source of Truth for the MCP Server.
    """

    server: ServerConfig = field(default_factory=ServerConfig)
    include: Optional[str] = None
    exclude: Optional[str] = None
    discovery: List[str] = field(default_factory=list)
    tools: List[Capability] = field(default_factory=list)
    prompts: List[Capability] = field(default_factory=list)
    resources: List[Capability] = field(default_factory=list)

    @classmethod
    def from_yaml(cls, path: str):
        with open(path, "r") as f:
            data = yaml.safe_load(f) or {}

        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """Helper to recursively build dataclasses from a dictionary."""
        # Build ServerConfig
        server_data = data.get("server", {})
        server_cfg = ServerConfig(**server_data)

        # Build Settings (Flattened in the dataclass)
        settings = data.get("settings", {})

        # Build Capabilities (Ensuring they are objects)
        # This handles: tools: [{"path": "...", "name": "..."}]
        def make_caps(key):
            return [Capability(**item) for item in data.get(key, [])]

        return cls(
            server=server_cfg,
            include=settings.get("include"),
            exclude=settings.get("exclude"),
            discovery=data.get("discovery", []),
            tools=make_caps("tools"),
            prompts=make_caps("prompts"),
            resources=make_caps("resources"),
        )

    @classmethod
    def from_args(cls, args):
        """
        Map argparse flat namespace to the structured Dataclass.
        """
        return cls(
            server=ServerConfig(
                transport=args.transport,
                port=args.port,
                host=args.host,
                path=args.path,
                ssl_certfile=args.ssl_certfile,
                ssl_keyfile=args.ssl_keyfile,
            ),
            include=args.include,
            exclude=args.exclude,
            discovery=args.tool_module or [],
            tools=[Capability(path=t) for t in (args.tool or [])],
            prompts=[Capability(path=p) for p in (args.prompt or [])],
            resources=[Capability(path=r) for r in (args.resource or [])],
        )
