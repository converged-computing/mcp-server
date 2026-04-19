import asyncio
import socket
from typing import Any, Dict, Optional

import httpx
from rich import print

from mcpserver.logger import logger

from .base import WorkerBase


class WorkerManager(WorkerBase):
    """
    A generic worker mcpserver that discovers its own capabilities
    and context using the resource-secretary library.
    """

    def __init__(
        self,
        mcp,
        hub_url: str,
        secret: str,
        worker_id: Optional[str] = None,
        public_url: Optional[str] = None,
        mock: Optional[bool] = False,
        verbose: Optional[bool] = False,
    ):
        self.mcp = mcp
        self.hub_url = hub_url
        self.secret = secret
        self.worker_id = worker_id or socket.gethostname()
        self.public_url = public_url
        self.init_providers(mock)
        self.verbose = verbose
        self.show()

        # Static Manifest for the worker
        self.manifest = self.build_manifest()

        # Register MCP Tools automatically
        self.register_agent_tools()

    def show(self):
        """
        Show providers installed and verbosity.
        """
        for category, providers in self.catalog.items():
            providers = ", ".join([p.name for p in providers])
            print(f"  [purple]{category.rjust(10)}[/purple] {providers}")
        if self.verbose:
            logger.info(f"📢 Running in verbose mode. Secretary negotiate will return calls block.")
        print()

    def build_manifest(self) -> Dict[str, Any]:
        """
        Flattens the discovered provider objects into a static JSON manifest.
        """
        manifest = {}
        for category, instances in self.catalog.items():
            manifest[category] = {inst.name: inst.metadata for inst in instances}
        return manifest

    async def run_registration(self):
        """
        Registers the worker with the Hub.
        Sends the Level 1 Manifest so the Hub knows exactly what resources are here.
        """
        await asyncio.sleep(1)
        async with httpx.AsyncClient() as client:
            payload = {
                "id": self.worker_id,
                "url": self.public_url,
                "manifest": self.manifest,
            }
            headers = {"X-MCP-Token": self.secret}
            try:
                res = await client.post(f"{self.hub_url}/register", json=payload, headers=headers)
                res.raise_for_status()
                logger.info(
                    f"✅ Registered as '{self.worker_id}' with {len(self.manifest)} categories discovered."
                )
            except Exception as e:
                logger.error(f"❌ Registration failed: {e}")

    @classmethod
    def from_args(cls, mcp, args, cfg) -> Optional["WorkerManager"]:
        """
        Factory to create a WorkerManager from CLI arguments.
        """
        if not getattr(args, "join", None):
            return None

        default_url = f"http://{cfg.server.host}:{cfg.server.port}{cfg.server.path}"
        public_url = args.public_url or default_url

        return cls(
            mcp,
            mock=args.mock,
            hub_url=args.join,
            secret=args.join_secret,
            worker_id=args.worker_id,
            public_url=public_url,
            verbose=args.verbose,
        )
