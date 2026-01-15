import importlib
import inspect
import os
import re
from pathlib import Path
from typing import Dict

from fastmcp.prompts import Prompt
from fastmcp.resources import Resource

# These are the function types we want to discover
from fastmcp.tools import Tool

from .base import BaseTool


class ToolManager:

    def __init__(self):
        self.tools = {}

    def load_function(self, tool_path):
        """
        Assume this is the function name provided
        """
        module_path, function = tool_path.rsplit(".", 1)
        module = importlib.import_module(module_path)
        return getattr(module, function)

    def register_tool(self, mcp, tool_path: str, name: str = None):
        """
        Register an mcp function directly.
        """
        func = self.load_function(tool_path)
        endpoint = Tool.from_function(func, name=name or func.__name__)
        mcp.add_tool(endpoint)
        return endpoint

    def register_resource(self, mcp, tool_path: str, name: str = None):
        """
        Register an mcp resource directly.
        """
        func = self.load_function(tool_path)
        endpoint = Resource.from_function(func, name=name or func.__name__)
        mcp.add_resource(endpoint)
        return endpoint

    def register_prompt(self, mcp, tool_path: str, name: str = None):
        """
        Register an mcp resource directly.
        """
        func = self.load_function(tool_path)
        endpoint = Prompt.from_function(func, name=name or func.__name__)
        mcp.add_prompt(endpoint)
        return endpoint

    def register(self, module_name: str = "mcpserver.tools"):
        """
        Discover and register tools from a module path.

        Note that we don't actually load mcp functions here.
        They are loaded on demand based on the user start
        request. Here we just keep track of discovered
        contenders.
        """
        # This needs to fail if we can't find it.
        module = importlib.import_module(module_name)
        if isinstance(module.__path__, list):
            root_path = Path(module.__path__[0]).resolve()
        # NamespacePath
        else:
            root_path = Path(module.__path__._path[0]).resolve()
        self.tools.update(self.discover_tools(root_path, module_name))

    def discover_tools(self, root_path: str, module_path: str) -> Dict[str, Path]:
        """
        Walks the directory tree to load tool metadata
        """
        discovered = {}
        module_path = module_path.replace(os.sep, ".")

        # Recursive glob for all .py files
        for file_path in root_path.rglob("*.py"):
            if file_path.name != "tool.py":
                continue

            # Calculate the relative path from 'tools/'
            # e.g., kubernetes/deploy/job.py
            rel_path = file_path.relative_to(root_path)

            # Assemble the module name
            parts = list(rel_path.parts)
            parts[-1] = os.path.splitext(parts[-1])[0]
            import_path = module_path + "." + ".".join(parts)

            # Create the ID: kubernetes-deploy-job
            # We strip the .py extension and replace slashes with dashes
            tool_id = str(rel_path.with_suffix(""))
            for repl in [[os.sep, "-"], ["-tool", ""], ["_", "-"]]:
                tool_id = tool_id.replace(repl[0], repl[1])
            discovered[tool_id] = {"path": file_path, "module": import_path, "root": root_path}
        return discovered

    def load_tools(self, mcp, include=None, exclude=None):
        """
        Load a set of named tools, or default to all those discovered.
        """
        # If no tools are selected... select all tools discovered
        names = self.tools
        include = "(%s)" % "|".join(include) if include else None
        exclude = "(%s)" % "|".join(exclude) if exclude else None

        to_load = {}
        for name in names:
            # Prefix matching is more flexible than tag matching
            matches = {k: v for k, v in self.tools.items() if name in k}
            if not matches:
                print(f"⚠️  No tools match pattern: '{name}'")
            to_load.update(matches)

        # Load and Register a tool module
        for name in to_load:

            # Inclusion and exclusion
            if include and not re.search(include, name):
                continue
            if exclude and re.search(exclude, name):
                continue

            # This is a tool instance. A tool instance can have 1+ functions
            instance = self.load_tool(name)
            if not instance:
                continue

            # Add tools, resources, and prompts on the fly
            for ToolClass in [Tool, Resource, Prompt]:
                tooltype = ToolClass.__name__.lower()
                getfunc = getattr(instance, f"get_mcp_{tooltype}s", None)

                # Skip if the imlpementer did not add the class
                if not getfunc:
                    continue

                # Get the decorated functions
                for func in getfunc():

                    # This is how we handle dynamic loading
                    endpoint = ToolClass.from_function(func, name=func._mcp_name)

                    # @mcp.tool
                    if ToolClass == Tool:
                        mcp.add_tool(endpoint)

                    # @mcp.prompt
                    elif ToolClass == Prompt:
                        mcp.add_prompt(endpoint)

                    # @mcp.resource
                    else:
                        mcp.add_resource(endpoint)
                    yield endpoint

    def load_tool(self, tool_id: str) -> BaseTool:
        """
        Load a single tool (the actual module) based on finding BaseTool.
        """
        # Convert filesystem path to python module notation
        relative_module = self.tools[tool_id]["module"]

        try:
            module = importlib.import_module(relative_module)

            # Find the class that inherits from BaseTool
            for _, obj in inspect.getmembers(module):
                if inspect.isclass(obj) and issubclass(obj, BaseTool) and obj is not BaseTool:

                    # Instantiate
                    instance = obj()
                    # Inject the filesystem-derived name
                    instance.name = tool_id
                    instance.setup()
                    return instance

        except ImportError as e:
            print(f"❌ Error importing {tool_id}: {e}")
            return None

    def get_available_prompts(self):
        """
        Scans all discoverable tools for functions decorated with @mcp.prompt.
        Returns a set of prompt names (personas). We need this to validate a plan.
        A plan is not valid if it names a persona (prompt) that is not known.
        """
        prompts = set()

        # 2. Load them (to execute decorators)
        for tool_id, path in self.tools.items():
            mod = self.load_tool_module(tool_id, path)
            if not mod:
                continue

            # 3. Inspect the classes/functions in the module
            for name, obj in inspect.getmembers(mod):
                # We usually look for classes inheriting from BaseTool
                # But we can also just scan the class attributes
                if inspect.isclass(obj):
                    for attr_name in dir(obj):
                        try:
                            func = getattr(obj, attr_name)
                        except:
                            continue

                        # CHECK FOR PROXY TAG
                        if callable(func) and getattr(func, "_is_mcp_prompt", False):
                            # Get the name from the decorator
                            p_name = getattr(func, "_mcp_name", None)
                            if p_name:
                                prompts.add(p_name)

        return prompts
