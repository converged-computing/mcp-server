import os
import time
from typing import Any, Dict, List

from resource_secretary.agents.backends import get_backend
from resource_secretary.agents.secretary import SecretaryAgent
from resource_secretary.providers import discover_providers

from mcpserver.tools.base import BaseTool
from mcpserver.tools.decorator import mcp


class SystemTool(BaseTool):
    """
    Primary interface for cluster identity and negotiation.
    """

    def setup(self, manager=None):
        self.manager = manager
        self.catalog = discover_providers()

        # Capture model config from environment or manager defaults
        # manager.args would contain the CLI values from populate_start_args
        self.backend_config = {
            "type": os.getenv("RESOURCE_SECRETARY_LLM"),
            "model": os.getenv("RESOURCE_SECRETARY_MODEL"),
            "base": os.getenv("RESOURCE_SECRETARY_API_BASE"),
        }

        self.active_providers = [inst for category in self.catalog.values() for inst in category]

    def build_manifest(self) -> Dict[str, Any]:
        manifest = {}
        for category, instances in self.catalog.items():
            manifest[category] = {inst.name: inst.metadata for inst in instances}
        return manifest

    @mcp.tool(name="get_status")
    def get_status(self) -> Dict[str, Any]:
        return {"timestamp": time.time(), "manifest": self.build_manifest()}

    @mcp.tool(name="ask_secretary")
    async def ask_secretary(self, request: str) -> Dict[str, Any]:
        """
        Wakes up the local Secretary Agent using the configured backend.
        """
        # Resolve the backend instance on-demand
        backend = get_backend(
            backend_type=self.backend_config["type"],
            model_name=self.backend_config["model"],
            api_base=self.backend_config["base"],
        )

        agent = SecretaryAgent(self.active_providers, backend=backend)
        proposal = await agent.negotiate(request)

        return {"proposal": proposal, "status": "SUCCESS"}
