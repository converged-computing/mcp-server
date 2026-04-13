import asyncio
import json
import random
import secrets
import socket
import time
from typing import Any, Dict, Optional

from fastmcp import Client
from mcp.types import Tool
from rich import print

import mcpserver.utils as utils
from mcpserver.logger import logger

from .base import WorkerBase


class HubManager:
    """
    A hub manager is a central coordinator that aggregates worker clusters,
    reflects their tools, and manages federated job negotiation.
    """

    def __init__(
        self,
        mcp,
        host: str,
        port: int,
        secret: str = None,
        batch=None,
        serial=False,
        dual=False,
        hub_id=None,
        path="/mcp",
    ):
        self.mcp = mcp
        self.host = host
        self.port = port
        self.path = path
        self.secret = secret or secrets.token_urlsafe(32)
        self.workers: Dict[str, Dict[str, Any]] = {}
        self.hub_id = hub_id or socket.gethostname()

        # Make requests to hub in batches, in serial, or in parallel
        self.set_running_mode(batch, serial, dual)

        # Track registered proxies to prevent ValueError on worker re-registration
        self._registered_proxies = set()
        self._print_banner()
        self._register_hub_tools()

    @property
    def url(self):
        # This is running with uvicorn that serves the ssl
        return f"http://{self.host}:{self.port}"

    @property
    def registration_url(self):
        return f"{self.url}/register"

    def set_running_mode(self, batch_size=None, serial=False, dual=False):
        """
        Set the function to call the fleet.
        If we are worried about rate limits or running experiments,
        we should be sure to run in small batches.
        """
        # Set the fleet engine to run full parallel
        self.semaphore = None
        self.run_on_fleet = self.run_on_fleet_parallel

        if serial:
            logger.info(f"⚡ Hub initialized in serial mode")
            self.run_on_fleet = self.run_on_fleet_serial
            return

        elif not batch_size or batch_size <= 0:
            logger.info(f"⚡ Hub initialized in full Parallel mode")
            return

        # Set the fleet engine to use the semaphore
        self.batch_size = batch_size
        self.semaphore = asyncio.Semaphore(batch_size)
        self.run_on_fleet = self.run_on_fleet_batched
        logger.info(f"🚦 Hub initialized with Batch Size: {batch_size} Worker mode: {dual}")

        # If we are also running as a worker, add ourselves to the fleet
        self.dual = dual

    @classmethod
    def from_args(cls, mcp, args) -> Optional["HubManager"]:
        """
        Create a HubManager from CLI arguments.
        """
        # Running in hub or dual mode?
        if not getattr(args, "hub", False) and not getattr(args, "dual", False):
            return None
        return cls(
            mcp,
            host=args.host,
            port=args.port,
            secret=args.hub_secret,
            batch=args.batch,
            serial=args.serial,
            dual=args.dual,
            # server path
            path=args.path,
        )

    def _print_banner(self):
        """
        Print hub connection info for workers.
        """
        print(f"\n🛡️  Hub Mode Active")
        print(f"   Master Secret: {self.secret}")
        print("   Workers must use this secret to join the hub")
        print(f"   mcpserver start --join {self.registration_url}\n")

    async def run_on_fleet_parallel(self, action_fn) -> Dict[str, Any]:
        """
        Run parallel sessions across all workers.
        action_fn: An async function that takes (worker_id, session) and returns data.
        """

        async def _safe_wrapper(wid, info):
            try:
                async with info["client"] as sess:
                    return wid, await action_fn(wid, sess)
            except Exception as e:
                return wid, {"type": "error", "message": str(e)}

        if not self.workers:
            return {}

        # Parallel execution of all worker actions
        results = await asyncio.gather(*[_safe_wrapper(w, i) for w, i in self.workers.items()])
        return dict(results)

    async def run_on_fleet_serial(self, action_fn) -> Dict[str, Any]:
        """
        Run sessions across all workers one by one (sequentially).
        """
        results = {}
        if not self.workers:
            return results

        for wid, info in self.workers.items():
            try:
                # await each one so we wait for worker to return
                async with info["client"] as sess:
                    results[wid] = await action_fn(wid, sess)
            except Exception as e:
                results[wid] = {"type": "error", "message": str(e)}

        return results

    async def run_on_fleet_batched(self, action_fn) -> Dict[str, Any]:
        """
        Execute on workers using a semaphore to stay under rate limits.
        """

        async def _safe_wrapper(wid, info):
            # Wait for a spot in the semaphore
            async with self.semaphore:
                try:
                    # Add a micro-jitter (100-300ms) to prevent perfect bursts
                    await asyncio.sleep(random.uniform(0.1, 0.3))
                    async with info["client"] as sess:
                        return wid, await action_fn(wid, sess)
                except Exception as e:
                    return wid, {"type": "error", "message": str(e)}

        if not self.workers:
            return {}
        results = await asyncio.gather(*[_safe_wrapper(w, i) for w, i in self.workers.items()])
        return dict(results)

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

        @self.mcp.tool(name="dispatch_job")
        async def dispatch_job(worker_id: str, prompt: str) -> dict:
            """
            Directly targets a specific worker to execute a job.
            """
            info = self.workers.get(worker_id)
            if not info:
                return {"error": f"Worker {worker_id} not found."}

            async with info["client"] as sess:
                result = await sess.call_tool("submit", {"request": prompt})
                return json.loads(utils.extract_code_block(result.content[0].text))

        @self.mcp.tool(name="negotiate_job")
        async def negotiate_job(prompt: str) -> dict:
            """
            Broadcast a job request to all worker Secretaries in parallel.
            Wakes up local reasoning loops for Level 2 dynamic evaluation.
            """
            if not self.workers:
                return {"error": "No workers registered in fleet."}
            return await self.broadcast_negotiation(prompt)

        @self.mcp.tool(name="export_fleet_truth")
        async def export_fleet_truth() -> dict:
            """
            Collects internal mock metadata (ground truth) from all workers.
            Used for accuracy experiments to compare against agent findings,
            but you could also use it for a real worker.
            """
            if not self.workers:
                return {"error": "No workers registered."}

            async def truth_handler(wid, sess):
                mcp_result = await sess.call_tool("export_provider_metadata", {})
                return json.loads(mcp_result.content[0].text)

            results = await self.run_on_fleet(truth_handler)
            return {"timestamp": time.time(), "ground_truth": results}

    async def broadcast_negotiation(self, prompt: str) -> dict:
        """
        Uses the Fleet Engine to invoke Agentic Secretaries on all children.
        """

        async def negotiate_handler(wid, sess):
            # Check for Level 2 support (Secretary Agent)
            tools = await sess.list_tools()
            has_secretary = any(t.name == "ask_secretary" for t in tools)

            if has_secretary:
                # Invoke the Agentic Secretary
                mcp_result = await sess.call_tool("ask_secretary", {"request": prompt})
                raw_text = mcp_result.content[0].text

                try:
                    # Parse and handle potential quote issues in LLM JSON
                    proposal_data = json.loads(utils.extract_code_block(raw_text))
                except:
                    proposal_data = {"proposal_text": raw_text}

                return {
                    "type": "agentic_proposal",
                    "data": proposal_data,
                    "status": utils.extract_code_block(raw_text),
                }
            else:
                # Fallback to manifest only
                mcp_result = await sess.call_tool("get_status", {})
                return {
                    "type": "manifest_only",
                    "reasoning": "Worker has no Secretary Agent. Providing static metadata.",
                    "data": mcp_result.content[0].text,
                }

        start_time = time.time()
        results = await self.run_on_fleet(negotiate_handler)

        return {
            "negotiation_id": secrets.token_hex(4),
            "timestamp": start_time,
            "user_prompt": prompt,
            "proposals": results,
        }

    async def fetch_all_statuses(self) -> dict:
        """
        Collect aggregate telemetry from all workers using the Fleet Engine.
        """

        async def status_handler(wid, sess):
            info = self.workers[wid]
            base_metadata = {
                "labels": info.get("labels", {}),
                "url": info["url"],
            }

            mcp_result = await sess.call_tool("get_status", {})
            raw_text = mcp_result.content[0].text
            try:
                # Note: Preserving the replace hack from original for status data
                status_data = json.loads(raw_text.replace("'", '"'))
            except:
                status_data = raw_text

            return {
                **base_metadata,
                "online": True,
                "status": status_data,
            }

        return await self.run_on_fleet(status_handler)

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


class DualHubManager(WorkerBase, HubManager):
    """
    Combined hub and worker base. Aka, a hub that also serves as a worker
    """

    def __init__(self, *args, **kwargs):
        # Calls super on the HubManager. WorkerBase has no init
        super().__init__(*args, **kwargs)
        self.setup_dual()

    def setup_dual(self):
        """
        Setup dual mode, which means adding ourselves to the fleet.
        """
        hub_id = self.hub_id or socket.gethostname()
        default_url = f"http://{self.host}:{self.port}{self.path}"
        self.workers[hub_id] = {
            "url": self.registration_url,
            "client": Client(default_url),
        }
