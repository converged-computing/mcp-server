import importlib
import inspect
from typing import Any, Dict, List, Optional, Set

from fastmcp.prompts import Prompt
from fastmcp.resources import Resource
from fastmcp.tools import Tool

from mcpserver.events import get_event_manager

from .base import BaseTool
from .system.system import SystemTool


class ToolManager:
    """
    Top-level manager for tool registration.
    Worker tools are registered with clean names; Hub handles namespacing.
    """

    def __init__(self):
        self.tools: Dict[str, Dict[str, Any]] = {}
        self.instances: Dict[str, BaseTool] = {}
        self.registered_keys: Set[str] = set()
        self._events_initialized = False

    def register_instance_with_mcp(self, mcp, instance: BaseTool):
        """
        Maps decorated methods from a tool instance to FastMCP endpoints.
        """
        mapping = {Tool: mcp.add_tool, Resource: mcp.add_resource, Prompt: mcp.add_prompt}

        for ToolClass, add_func in mapping.items():
            type_prefix = ToolClass.__name__.lower()
            method_name = f"get_mcp_{type_prefix}s"
            getter = getattr(instance, method_name, None)

            if not getter:
                continue

            for func in getter():
                name = getattr(func, "_mcp_name", func.__name__)

                # Check for duplicate registration within this process
                unique_key = f"{type_prefix}:{name}"
                if unique_key in self.registered_keys:
                    continue

                endpoint = ToolClass.from_function(func, name=name)
                try:
                    add_func(endpoint)
                    self.registered_keys.add(unique_key)
                except Exception as e:
                    print(f"⚠️  Failed to register {unique_key}: {e}")

    def load_fleet_tools(self, mcp, include: Optional[List[str]] = None):
        """
        The standard loader for an agentic worker.
        """
        # Initialize and register the local SystemTool
        system = SystemTool()
        system.name = "system"
        system.setup(manager=self)
        self.instances["system"] = system
        self.register_instance_with_mcp(mcp, system)

        # Optional user-defined tool modules (maybe we don't need)
        if not include:
            return

        for path in include:
            if "mcpserver.tools.system" in path:
                continue
            self.load_and_register_module(mcp, path)

    def load_and_register_module(self, mcp, module_path: str):
        """
        Load and register a module.
        """
        try:
            module = importlib.import_module(module_path)
            for _, obj in inspect.getmembers(module):
                if inspect.isclass(obj) and issubclass(obj, BaseTool) and obj is not BaseTool:
                    name = module_path.split(".")[-1]
                    if name in self.instances:
                        continue

                    inst = obj()
                    inst.name = name
                    inst.setup(manager=self)
                    self.instances[name] = inst
                    self.register_instance_with_mcp(mcp, inst)
        except Exception as e:
            print(f"❌ Could not load extra tool module at {module_path}: {e}")

    def load_function(self, tool_path: str):
        """
        Load a function. Worst docstring ever. I'm tired.
        """
        module_path, function_name = tool_path.rsplit(".", 1)
        module = importlib.import_module(module_path)
        return getattr(module, function_name)

    def register_tool(self, mcp, tool_path: str, name: str = None):
        """
        Register a tool.
        """
        from fastmcp.tools import Tool

        func = self.load_function(tool_path)
        actual_name = name or func.__name__
        if f"tool:{actual_name}" in self.registered_keys:
            return
        endpoint = Tool.from_function(func, name=actual_name)
        mcp.add_tool(endpoint)
        self.registered_keys.add(f"tool:{actual_name}")
        return endpoint

    def register_resource(self, mcp, tool_path: str, name: str = None):
        """
        Register a resource.

        Note from vsoch: I haven't tried any resources yet.
        """
        from fastmcp.resources import Resource

        func = self.load_function(tool_path)
        actual_name = name or func.__name__
        if f"resource:{actual_name}" in self.registered_keys:
            return
        endpoint = Resource.from_function(func, name=actual_name)
        mcp.add_resource(endpoint)
        self.registered_keys.add(f"resource:{actual_name}")
        return endpoint

    def register_prompt(self, mcp, tool_path: str, name: str = None):
        """
        Register a prompt.

        Note from vsoch: In practice, I'm not sure I find server prompts useful.
        """
        from fastmcp.prompts import Prompt

        func = self.load_function(tool_path)
        actual_name = name or func.__name__
        if f"prompt:{actual_name}" in self.registered_keys:
            return
        endpoint = Prompt.from_function(func, name=actual_name)
        mcp.add_prompt(endpoint)
        self.registered_keys.add(f"prompt:{actual_name}")
        return endpoint

    def register_event(self, mcp, class_path: str, name: str = None):
        """
        Loads an external Event Class (e.g. FluxEvents), validates it,
        and registers it with the SubscriptionManager.
        """
        try:
            # 1. Load the class
            module_path, class_name = class_path.rsplit(".", 1)
            module = importlib.import_module(module_path)
            cls = getattr(module, class_name)

            if not inspect.isclass(cls):
                raise TypeError(f"{class_path} is not a class.")

            # 2. Instantiate and Validate
            instance = cls()
            required = ["get_metadata", "subscribe", "unsubscribe"]
            for req in required:
                if not hasattr(instance, req):
                    raise AttributeError(f"Event class {class_name} missing required method: {req}")

            # 3. Register with the Event Manager
            provider_name = name or class_name.lower().replace("events", "")
            manager = get_event_manager()
            manager.register_provider(provider_name, instance)

            # Ensure we can satisfy the server print "name"
            if not hasattr(instance, "name"):
                instance.name = provider_name

            # 4. Inject the 3 core MCP tools if this is the first event registered
            if not self._events_initialized:
                self._register_core_event_tools(mcp)
                self._events_initialized = True
            return instance

        except Exception as e:
            print(f"❌ Failed to register event provider at {class_path}: {e}")

    def _register_core_event_tools(self, mcp):
        """
        Adds the list, subscribe, and unsubscribe tools to FastMCP.
        """
        from fastmcp.tools import Tool

        from mcpserver.events import tools as event_tools

        core_funcs = [
            event_tools.list_event_streams,
            event_tools.subscribe,
            event_tools.unsubscribe,
        ]

        for func in core_funcs:
            endpoint = Tool.from_function(func, name=func.__name__)
            mcp.add_tool(endpoint)
            self.registered_keys.add(f"tool:{func.__name__}")

# TODO STOPPED HERE - any reason we can't have the tool interface for an agent here?
# the one that isn't mcp? Or should we put under the worker/hub so thus remove
# from the config?