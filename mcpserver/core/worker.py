import asyncio
import socket
import time
from typing import Any, Dict, Optional

import httpx
from resource_secretary.providers import discover_providers

from mcpserver.logger import logger


class WorkerManager:
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
        labels: Optional[list] = None,
    ):
        self.mcp = mcp
        self.hub_url = hub_url
        self.secret = secret
        self.worker_id = worker_id or socket.gethostname()
        self.public_url = public_url

        # Probe the local system on startup. E.g., "we found spack, flux, etc."
        logger.info("📡 Probing local system for resource providers...")
        self.catalog = discover_providers()

        # Static Manifest for the worker
        self.manifest = self.build_manifest()

        # Note from vsoch: not sure if this will be useful / what we should use for.
        self.labels = self.parse_labels(labels)
        self.integrate_site_metadata()

        # Register MCP Tools automatically
        self.register_agent_tools()

    def build_manifest(self) -> Dict[str, Any]:
        """
        Flattens the discovered provider objects into a static JSON manifest.
        """
        manifest = {}
        for category, instances in self.catalog.items():
            manifest[category] = {inst.name: inst.metadata for inst in instances}
        return manifest

    def integrate_site_metadata(self):
        """
        Looks for the site provider in the catalog and adds its metadata to labels.
        """
        site_instances = self.catalog.get("system", [])
        for inst in site_instances:
            if inst.name == "site":
                self.labels.update(inst.metadata)

    def parse_labels(self, label_list: Optional[list]) -> dict:
        """
        Converts ['key=val', 'key2=val2'] to a dictionary.
        """
        labels = {}
        if not label_list:
            return labels
        for item in label_list:
            if "=" in item:
                k, v = item.split("=", 1)
                labels[k.strip()] = v.strip()
        return labels

    def register_agent_tools(self):
        """
        Registers the core negotiation tools with the FastMCP instance.
        """

        @self.mcp.tool(name="get_status")
        async def get_status() -> dict:
            """
            Returns the Level 1 Static Manifest of this cluster.
            Use this to verify hardware, software providers, and site info.
            """
            return {
                "worker_id": self.worker_id,
                "timestamp": time.time(),
                "manifest": self.manifest,
            }

        @self.mcp.tool(name="ask_secretary")
        async def ask_secretary(request: str) -> dict:
            """
            Wakes up the local Secretary Agent to perform a Level 2 investigation.
            Use this to ask about specific software availability, queue depth, or node health.
            """
            from resource_secretary.agents.secretary import SecretaryAgent

            # Flatten the catalog into a list of active provider instances
            active_providers = [inst for category in self.catalog.values() for inst in category]

            agent = SecretaryAgent(active_providers)
            proposal = await agent.negotiate(request)

            return {"worker_id": self.worker_id, "proposal": proposal}

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
                "labels": self.labels,
                # Identify the worker by its primary workload manager if available
                # Note from vsoch: after refactor all workers are generic, so site needs to apply this.
                "type": self.labels.get("manager", "generic"),
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

        public_url = (
            args.public_url or f"http://{cfg.server.host}:{cfg.server.port}{cfg.server.path}"
        )

        return cls(
            mcp,
            hub_url=args.join,
            secret=args.join_secret,
            worker_id=args.register_id,
            public_url=public_url,
            labels=args.labels,
        )
