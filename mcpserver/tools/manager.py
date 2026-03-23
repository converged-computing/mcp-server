import importlib
import inspect
from typing import Any, Dict, List, Optional, Set

from fastmcp.prompts import Prompt
from fastmcp.resources import Resource
from fastmcp.tools import Tool

from .base import BaseTool
from .system.system import SystemTool


class ToolManager:
    """
    Top-level manager for tool registration.
    Prevents duplicate registration and handles worker identity prefixing.
    """

    def __init__(self):
        self.tools: Dict[str, Dict[str, Any]] = {}
        self.instances: Dict[str, BaseTool] = {}
        # Track registered names to prevent FastMCP duplicate errors
        self.registered_names: Set[str] = set()
        self.worker_id: Optional[str] = None

    def get_prefixed_name(self, name: str) -> str:
        """
        Applies the worker identity prefix to a tool name if configured.
        """
        if not self.worker_id:
            return name
        # Prevent double-prefixing if the name already starts with the ID
        if name.startswith(f"{self.worker_id}_"):
            return name
        return f"{self.worker_id}_{name}"

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
                # Apply the worker identity prefix here
                base_name = getattr(func, "_mcp_name", func.__name__)
                prefixed_name = self.get_prefixed_name(base_name)

                # Check for duplicate registration
                unique_key = f"{type_prefix}:{prefixed_name}"
                if unique_key in self.registered_names:
                    continue

                endpoint = ToolClass.from_function(func, name=prefixed_name)
                try:
                    add_func(endpoint)
                    self.registered_names.add(unique_key)
                except Exception as e:
                    print(f"⚠️  Failed to register {unique_key}: {e}")

    def load_fleet_tools(self, mcp, include: Optional[List[str]] = None, worker_id: str = None):
        """
        The standard loader for an agentic worker.
        """
        self.worker_id = worker_id

        # 1. Initialize and register the local SystemTool
        system = SystemTool()
        system.name = "system"
        system.setup(manager=self)
        self.instances["system"] = system
        self.register_instance_with_mcp(mcp, system)

        # 2. Boot optional user-defined tool modules
        if not include:
            return

        for path in include:
            # SHARP FIX: If the discovery path is the system module, skip it.
            # We already loaded it above manually.
            if "mcpserver.tools.system" in path:
                continue
            self.load_and_register_module(mcp, path)

    def load_and_register_module(self, mcp, module_path: str):
        """
        Loads a module by path and registers any BaseTool subclasses.
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
        module_path, function_name = tool_path.rsplit(".", 1)
        module = importlib.import_module(module_path)
        return getattr(module, function_name)

    def register_tool(self, mcp, tool_path: str, name: str = None):
        from fastmcp.tools import Tool

        func = self.load_function(tool_path)
        actual_name = self.get_prefixed_name(name or func.__name__)

        if f"tool:{actual_name}" in self.registered_names:
            return

        endpoint = Tool.from_function(func, name=actual_name)
        mcp.add_tool(endpoint)
        self.registered_names.add(f"tool:{actual_name}")
        return endpoint

    def register_resource(self, mcp, tool_path: str, name: str = None):
        from fastmcp.resources import Resource

        func = self.load_function(tool_path)
        actual_name = self.get_prefixed_name(name or func.__name__)

        if f"resource:{actual_name}" in self.registered_names:
            return

        endpoint = Resource.from_function(func, name=actual_name)
        mcp.add_resource(endpoint)
        self.registered_names.add(f"resource:{actual_name}")
        return endpoint

    def register_prompt(self, mcp, tool_path: str, name: str = None):
        from fastmcp.prompts import Prompt

        func = self.load_function(tool_path)
        actual_name = self.get_prefixed_name(name or func.__name__)

        if f"prompt:{actual_name}" in self.registered_names:
            return

        endpoint = Prompt.from_function(func, name=actual_name)
        mcp.add_prompt(endpoint)
        self.registered_names.add(f"prompt:{actual_name}")
        return endpoint
