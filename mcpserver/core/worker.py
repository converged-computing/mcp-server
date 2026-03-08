import asyncio
import socket

import httpx

from mcpserver.logger import logger


class WorkerManager:
    """
    A worker mcpserver advertises its tools to a parent hub.
    """

    def __init__(self, mcp, hub_url, secret, worker_id=None, public_url=None):
        self.mcp = mcp
        self.hub_url = hub_url
        self.secret = secret
        self.worker_id = worker_id or socket.gethostname()
        self.public_url = public_url
        self._register_worker_tools()

    def _register_worker_tools(self):
        """
        This function will be able to return a live status.

        Likely we will need to make this an interface that can be customized
        depending on the worker type.
        """

        @self.mcp.tool(name="get_status")
        async def get_status() -> dict:
            """Reports local status and nested fleet status if acting as a Hub."""
            status = {"id": self.worker_id, "type": "leaf"}
            # The Fractal Logic: If we are also a hub, include our children
            if hasattr(self.mcp, "hub_manager"):
                status["type"] = "intermediate_hub"
                status["fleet"] = await self.mcp.hub_manager.fetch_all_statuses()
            return status

    async def run_registration(self):
        """
        Perform the dial-home registration.

        E.T. PHONE HOME!! (stop it, Vanessa) :_)
        """
        await asyncio.sleep(1)  # Wait for local server to be ready
        async with httpx.AsyncClient() as client:
            try:
                res = await client.post(
                    self.hub_url,  # user provides the /register url
                    json={"id": self.worker_id, "url": self.public_url},
                    headers={"X-MCP-Token": self.secret},
                    timeout=10,
                )
                res.raise_for_status()
                logger.info(f"✅ Registered with parent hub: {self.hub_url}")
            except Exception as e:
                logger.error(f"❌ Failed to register with hub: {e}")
