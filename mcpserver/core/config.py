from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import yaml

import mcpserver.defaults as defaults


@dataclass
class Capability:
    """
    Strictly structured tool, prompt, or resource.
    Path (function path) is required.
    
    Attributes:
        path: Dot-path to the function (e.g. 'my_module.tools.build')
        name: Optional override for the tool name.
        job:  If True, this tool runs as an async Job (Submit -> Return Ticket).
              If None, it inherits the global server setting.
    """

    path: str
    name: Optional[str] = None
    job: Optional[bool] = None

    def __post_init__(self):
        if not self.path:
            raise ValueError("Capability for tool, prompt, or resource must have a non-empty path")
        if not self.name:
            self.name = self.path.split(".")[-1]

@dataclass
class JobConfig:
    """
    Configuration specific to Async Job execution.
    """
    # Global toggle. If True, tools run as jobs unless overridden.
    enabled: bool = False 


@dataclass(frozen=True)
class ServerConfig:
    """
    Server runtime settings.
    """

    transport: str = defaults.transport
    port: int = int(defaults.port)
    host: str = defaults.host
    path: str = defaults.path


@dataclass(frozen=True)
class MCPConfig:
    """
    The Source of Truth for the MCP Server.
    """

    server: ServerConfig = field(default_factory=ServerConfig)    

    # Job configuration for long running tasks (event driven)
    jobs: JobConfig = field(default_factory=JobConfig) 

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

        # Build Settings
        settings = data.get("settings", {})

        # Look for a top-level 'jobs' key in the YAML
        jobs_data = data.get("jobs", {})
        job_cfg = JobConfig(**jobs_data)

        # Build Capabilities
        def make_caps(key):
            # The **item unpacking automatically handles 'job' if present in YAML
            # e.g., - { path: "foo.bar", job: true }
            return [Capability(**item) for item in data.get(key, [])]

        return cls(
            server=server_cfg,
            jobs=job_cfg,
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
                transport=args.transport, port=args.port, host=args.host, path=args.path
            ),
            # Do we want all MCP functions to be provided as jobs (return immediately with future)
            jobs=JobConfig(enabled=getattr(args, "job", False)),
            include=args.include,
            exclude=args.exclude,
            discovery=args.tool_module or [],
            
            # Note: Parsing 'job=True' inside individual CLI string args (like --tool path:name:job) 
            # is complex. Usually, CLI-defined tools inherit the global setting.
            # If you need granular CLI control, you'd need a custom parser here.
            tools=[Capability(path=t) for t in (args.tool or [])],
            prompts=[Capability(path=p) for p in (args.prompt or [])],
            resources=[Capability(path=r) for r in (args.resource or [])],
        )