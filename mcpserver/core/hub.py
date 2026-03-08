import asyncio
import secrets
from typing import Any, Dict

from fastmcp import Client
from mcp.types import Tool
from rich import print

import mcpserver.utils as utils
from mcpserver.logger import logger


class HubManager:
    """
    A hub manager is a part role that can serve / expose children workers.
    """

    def __init__(self, mcp, host: str, port: int, secret: str = None):
        self.mcp = mcp
        self.host = host
        self.port = port
        self.secret = secret or secrets.token_urlsafe(32)
        self.workers: Dict[str, Dict[str, Any]] = {}
        self.registration_url = f"http://{host}:{port}/register"
        self._print_banner()
        self._register_hub_tools()

    def _print_banner(self):
        """
        Print that hub mode is active, how to connect, etc.
        """
        print(f"\n🛡️  Hub Mode Active")
        print(f"   Master Secret: {self.secret}")
        print("   Workers must use this secret to join the hub")
        print(f"   mcpserver start --join {self.registration_url}\n")

    def _register_hub_tools(self):
        """
        Specific tools for a hub to advertise functionality.
        """

        @self.mcp.tool(name="get_fleet_status")
        async def get_fleet_status() -> dict:
            """
            Aggregate real-time status from registered children.
            """
            if not self.workers:
                return {"message": "No workers registered."}
            return await self.fetch_all_statuses()

    async def fetch_all_statuses(self) -> dict:
        """
        Handy function to get all statuses
        """

        async def get_one(wid, info):
            try:
                async with info["client"] as sess:
                    return wid, {"online": True, "status": await sess.call_tool("get_status", {})}
            except Exception as e:
                return wid, {"online": False, "error": str(e)}

        results = await asyncio.gather(*[get_one(w, i) for w, i in self.workers.items()])
        return dict(results)

    def bind_to_app(self, app):
        """
        We have to call this to bind the hub to the app.
        """
        from fastapi import HTTPException, Request

        @app.post("/register")
        async def register(request: Request):
            if not secrets.compare_digest(request.headers.get("X-MCP-Token", ""), self.secret):
                raise HTTPException(status_code=403)
            data = await request.json()
            wid, wurl = data["id"], data["url"]
            self.workers[wid] = {"url": wurl, "client": Client(wurl)}
            asyncio.create_task(self._reflect_child_tools(wid, wurl))
            return {"status": "success"}

    async def _reflect_child_tools(self, worker_id: str, url: str):
        """
        Discover worker (child) tools
        """
        try:
            async with Client(url) as client:
                tools = await client.list_tools()
                print()
                for tool in tools:
                    self._create_proxy(worker_id, url, tool)
        except Exception as e:
            logger.error(f"Failed to reflect tools for {worker_id}: {e}")

    def _create_proxy(self, worker_id: str, url: str, tool: Tool):
        """
        Dynamically adds a proxied tool to the FastMCP instance.
        """
        # Generate a safe function name and map original argument names
        proxy_name = f"{utils.sanitize(worker_id)}_{utils.sanitize(tool.name)}"

        # Map original argument names to safe Python parameter names
        properties = tool.inputSchema.get("properties", {})

        # Map: {"safe_name": "original-name"}
        arg_mapping = {utils.sanitize(k): k for k in properties.keys()}

        # Create the signature string: arg_1=None, arg_2=None
        arg_string = ", ".join([f"{safe_name}=None" for safe_name in arg_mapping.keys()])

        # 3. Build the dynamic function
        exec_globals = {
            "Client": Client,
            "target_url": url,
            "target_tool": tool.name,
            "arg_mapping": arg_mapping,
            "logger": logger,
        }
        namespace = {}

        # We use the arg_mapping inside the function to restore the original
        # names (with hyphens) before calling the remote tool.
        func_def = (
            f"async def {proxy_name}({arg_string}):\n"
            f"    # Map safe Python names back to original schema names\n"
            f"    raw_locals = locals()\n"
            f"    args = {{arg_mapping[k]: raw_locals[k] for k in arg_mapping if raw_locals[k] is not None}}\n"
            f"    async with Client(target_url) as client:\n"
            f"        return await client.call_tool(target_tool, args)"
        )

        try:
            exec(func_def, exec_globals, namespace)
            proxy_func = namespace[proxy_name]
            proxy_func.__doc__ = tool.description

            # Register with FastMCP
            self.mcp.tool(name=proxy_name)(proxy_func)
            print(f"🛰️  Discovered worker tool: [blue]{proxy_name}[/blue]")

        except Exception as e:
            logger.error(f"❌ Failed to generate dynamic proxy for {tool.name}: {e}")
