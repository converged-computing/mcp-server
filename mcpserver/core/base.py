import collections
import json
import time

from resource_secretary.apps import discover_applications
from resource_secretary.providers import discover_providers
from resource_secretary.providers.mock import discover_mock_providers

import mcpserver.utils as utils
from mcpserver.logger import logger


class WorkerBase:
    """
    A WorkerBase provides worker interaction functions, e.g., negotiate, status,
    ask secretary. We provide it here so that a hub can use it to generate
    its dual mode (acting as worker AND hub.)
    """

    def jsonify_response(self, result):
        """
        Ensure we get the text, and separate and parse tool calls,
        which the agent will return in a verbose mode.
        """
        print("result")
        print(result)
        print(type(result))
        if isinstance(result, dict):
            return result
        if not isinstance(result, str) and hasattr(result, "content"):
            result = result.content[0].text

        # Audit the tool calls (Did the agent just get lucky?)
        calls = []
        if "CALLS" in result:
            try:
                result, calls_block = result.split("CALLS")
                calls = utils.format_calls(calls_block)
            except:
                print(f"Issue parsing calls, agent had malformed response: {result}")
                pass

        result = json.loads(utils.extract_code_block(result))
        result["calls"] = calls
        return result

    def init_providers(self, mock=False):
        """
        Probe the local system on startup. E.g., "we found spack, flux, etc."
        These can be faux (mock) or real discovered providers
        """
        # We can use apps in mock or regular
        apps = discover_applications()
        logger.info("📡 Probing local system for resource providers...")
        if mock:
            self.catalog = discover_mock_providers(self.worker_id, choice=mock)
        else:
            self.catalog = discover_providers()
        self.catalog.update(apps)

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

            agent = SecretaryAgent(active_providers, verbose=self.verbose)
            raw_result = await agent.submit(request)
            try:
                receipt = self.jsonify_response(raw_result)
            except Exception as e:
                receipt = {"status": "FAILED", "reasoning": raw_result, "error": str(e)}

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
