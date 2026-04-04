import asyncio
import collections
import json
import socket
import time
from typing import Any, Dict, Optional

import httpx
from resource_secretary.providers import discover_providers
from resource_secretary.providers.mock import discover_mock_providers
from rich import print

import mcpserver.utils as utils
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

        # Note from vsoch: not sure if this will be useful / what we should use for.
        self.labels = self.parse_labels(labels)

        # Register MCP Tools automatically
        self.register_agent_tools()

    def init_providers(self, mock=False):
        """
        Probe the local system on startup. E.g., "we found spack, flux, etc."
        These can be faux (mock) or real discovered providers
        """
        logger.info("📡 Probing local system for resource providers...")
        if mock:
            self.catalog = discover_mock_providers(self.worker_id, choice=mock)
        else:
            self.catalog = discover_providers()

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

            # Verbose mode returns a second block with CALLS
            agent = SecretaryAgent(active_providers, verbose=self.verbose)
            proposal = await agent.negotiate(request)
            return {"worker_id": self.worker_id, "proposal": proposal}

        @self.mcp.tool(name="submit")
        async def receive_job(request: str) -> dict:
            """
            Receive a job. Accepts a job request, invokes the local Secretary to
            generate a spec, submit it, and verify the job ID.
            """
            from resource_secretary.agents.secretary import SecretaryAgent

            active_providers = [inst for cat in self.catalog.values() for inst in cat]

            agent = SecretaryAgent(active_providers)
            raw_result = await agent.submit(request)
            try:
                receipt = json.loads(utils.extract_code_block(raw_result))
            except:
                receipt = {"status": "FAILED", "reasoning": raw_result}

            return {"worker_id": self.worker_id, "receipt": receipt}

        @self.mcp.tool(name="export_provider_metadata")
        def export_provider_metadata() -> str:
            """
            Iterates through all providers and returns their internal 'truth' state.
            This tool is 'hidden' from the Secretary Agent but used by the Hub.
            """
            truth_map = {}
            tool_registry = collections.defaultdict(list)

            # Self.catalog is a dict: {"software": [MockSpackProvider, ...]}
            for category, providers in self.catalog.items():
                truth_map[category] = {}
                for p in providers:
                    # We check if the provider has the export_truth method
                    if hasattr(p, "export_truth"):
                        truth_map[category][p.name] = p.export_truth()
                    else:
                        # Fallback to standard metadata if not a mock
                        truth_map[category][p.name] = p.metadata

                    # Capture all Secretary Tools for this provider
                    # We can use this for simulations to assess what the agent
                    # should have called (vs. what it did)
                    manifest = p.discover_tools(tool_types=["secretary"])
                    for tool_name in manifest.keys():
                        tool_registry[category].append(f"{p.name}.{tool_name}")

            metadata = {"truth": truth_map, "registry": dict(tool_registry)}

            # If we have an archetype (mocking something) save it
            if hasattr(p, "archetype"):
                metadata["metadata"] = {"archetype": p.archetype.name}
            return json.dumps(metadata, indent=2)

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
            labels=args.labels,
            verbose=args.verbose,
        )
