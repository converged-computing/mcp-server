import asyncio
import json
import secrets
import time
from typing import Any, Dict, Optional

from fastmcp import Client
from mcp.types import Tool
from rich import print

import mcpserver.utils as utils
from mcpserver.logger import logger


class HubManager:
    """
    A hub manager is a central coordinator that aggregates worker clusters,
    reflects their tools, and manages federated job negotiation.
    """

    def __init__(self, mcp, host: str, port: int, secret: str = None):
        self.mcp = mcp
        self.host = host
        self.port = port
        self.secret = secret or secrets.token_urlsafe(32)
        self.workers: Dict[str, Dict[str, Any]] = {}

        # Track registered proxies to prevent ValueError on worker re-registration
        self._registered_proxies = set()

        self.registration_url = f"http://{host}:{port}/register"
        self._print_banner()
        self._register_hub_tools()

    @classmethod
    def from_args(cls, mcp, args) -> Optional["HubManager"]:
        """
        Factory to create a HubManager from CLI arguments.
        """
        if not getattr(args, "hub", False):
            return None
        return cls(mcp, host=args.host, port=args.port, secret=args.hub_secret)

    def _print_banner(self):
        """
        Print hub connection info for workers.
        """
        print(f"\n🛡️  Hub Mode Active")
        print(f"   Master Secret: {self.secret}")
        print("   Workers must use this secret to join the hub")
        print(f"   mcpserver start --join {self.registration_url}\n")

    def _register_hub_tools(self):
        """
        Registers tools that the Hub itself provides to users/agents.
        """

        @self.mcp.tool(name="get_fleet_status")
        async def get_fleet_status() -> dict:
            """
            Aggregate Level 1 (Static Manifest + Basic Status) from all workers.
            """
            if not self.workers:
                return {"message": "No workers registered."}
            return await self.fetch_all_statuses()

        @self.mcp.tool(name="negotiate_job")
        async def negotiate_job(prompt: str) -> dict:
            """
            Broadcast a job request to all worker Secretaries in parallel.
            Wakes up local reasoning loops for Level 2 dynamic evaluation.
            """
            if not self.workers:
                return {"error": "No workers registered in fleet."}
            return await self.broadcast_negotiation(prompt)

    async def broadcast_negotiation(self, prompt: str) -> dict:
        """
        Parallelized broadcast using asyncio.gather.
        Each worker is evaluated independently and concurrently.
        """

        async def negotiate_with_worker(wid, info):
            try:
                async with info["client"] as sess:
                    # Check for Level 2 support (Secretary Agent)
                    tools = await sess.list_tools()
                    has_secretary = any(t.name == "ask_secretary" for t in tools)

                    if has_secretary:
                        # Invoke the Agentic Secretary on the child cluster
                        mcp_result = await sess.call_tool("ask_secretary", {"request": prompt})
                        raw_text = mcp_result.content[0].text
                        try:
                            # Handle potential quote issues in LLM-generated JSON
                            proposal_data = json.loads(raw_text.replace("'", '"'))
                        except:
                            proposal_data = {"proposal_text": raw_text}

                        return wid, {"type": "agentic_proposal", "data": proposal_data}
                    else:
                        # Fallback to Level 1 static status
                        mcp_result = await sess.call_tool("get_status", {})
                        raw_text = mcp_result.content[0].text
                        return wid, {
                            "type": "manifest_only",
                            "reasoning": "Worker has no Secretary Agent. Providing static metadata.",
                            "data": raw_text,
                        }
            except Exception as e:
                return wid, {"type": "error", "message": str(e)}

        start_time = time.time()
        # Parallel execution of all worker negotiations
        results = await asyncio.gather(
            *[negotiate_with_worker(w, i) for w, i in self.workers.items()]
        )

        return {
            "negotiation_id": secrets.token_hex(4),
            "timestamp": start_time,
            "user_prompt": prompt,
            "proposals": dict(results),
        }

    async def fetch_all_statuses(self) -> dict:
        """
        Collect aggregate telemetry from all workers in parallel.
        """

        async def get_one(wid, info):
            base_metadata = {
                "type": info.get("type", "generic"),
                "labels": info.get("labels", {}),
                "url": info["url"],
            }
            try:
                async with info["client"] as sess:
                    mcp_result = await sess.call_tool("get_status", {})
                    raw_text = mcp_result.content[0].text
                    try:
                        status_data = json.loads(raw_text.replace("'", '"'))
                    except:
                        status_data = raw_text

                    return wid, {
                        **base_metadata,
                        "online": True,
                        "status": status_data,
                    }
            except Exception as e:
                return wid, {**base_metadata, "online": False, "error": str(e)}

        results = await asyncio.gather(*[get_one(w, i) for w, i in self.workers.items()])
        return dict(results)

    def bind_to_app(self, app):
        """
        Binds the Hub registration endpoint to the FastAPI app.
        """
        from fastapi import HTTPException, Request

        @app.post("/register")
        async def register(request: Request):
            if not secrets.compare_digest(request.headers.get("X-MCP-Token", ""), self.secret):
                raise HTTPException(status_code=403)

            data = await request.json()
            wid, wurl = data["id"], data["url"]

            self.workers[wid] = {
                "url": wurl,
                "client": Client(wurl),
                "type": data.get("type", "generic"),
                "labels": data.get("labels", {}),
            }

            # Discover tools in the background
            asyncio.create_task(self._reflect_child_tools(wid, wurl))
            return {"status": "success"}

    async def _reflect_child_tools(self, worker_id: str, url: str):
        """
        Discover tools from the worker and create local proxies.
        """
        try:
            async with Client(url) as client:
                tools = await client.list_tools()
                print()  # Discovery block spacing
                for tool in tools:
                    self._create_proxy(worker_id, tool)
        except Exception as e:
            logger.error(f"Failed to reflect tools for {worker_id}: {e}")

    def _create_proxy(self, worker_id: str, tool: Tool):
        """
        Dynamically creates a Hub-level tool that proxies to a specific worker.
        """
        proxy_name = f"{utils.sanitize(worker_id)}_{utils.sanitize(tool.name)}"

        if proxy_name in self._registered_proxies:
            print(f"🛰️  Re-discovered worker tool: [blue]{proxy_name}[/blue]")
            return

        properties = tool.inputSchema.get("properties", {})
        arg_mapping = {utils.sanitize(k): k for k in properties.keys()}
        arg_string = ", ".join([f"{safe_name}=None" for safe_name in arg_mapping.keys()])

        exec_globals = {
            "Client": Client,
            "hub": self,
            "worker_id": worker_id,
            "target_tool": tool.name,
            "arg_mapping": arg_mapping,
            "logger": logger,
        }
        namespace = {}

        # The function resolves the current worker URL at call-time
        func_def = (
            f"async def {proxy_name}({arg_string}):\n"
            f"    info = hub.workers.get(worker_id)\n"
            f"    if not info:\n"
            f"        return {{'error': f'Worker {{worker_id}} no longer registered'}}\n"
            f"    url = info['url']\n"
            f"    raw_locals = locals()\n"
            f"    args = {{arg_mapping[k]: raw_locals[k] for k in arg_mapping if raw_locals[k] is not None}}\n"
            f"    async with Client(url) as client:\n"
            f"        return await client.call_tool(target_tool, args)"
        )

        try:
            exec(func_def, exec_globals, namespace)
            proxy_func = namespace[proxy_name]
            proxy_func.__doc__ = tool.description

            self.mcp.tool(name=proxy_name)(proxy_func)
            self._registered_proxies.add(proxy_name)
            print(f"🛰️  Discovered worker tool: [blue]{proxy_name}[/blue]")

        except Exception as e:
            logger.error(f"❌ Failed to generate dynamic proxy for {tool.name}: {e}")
