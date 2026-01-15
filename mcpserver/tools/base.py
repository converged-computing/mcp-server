from abc import ABC
from typing import Callable, List


class BaseTool(ABC):
    """
    Base class for a tool to inherit from.
    The Manager looks for subclasses of this class in the target files.
    Each tool can provision prompts, resources, or tools.
    """

    def setup(self):
        pass

    def get_mcp_tools(self) -> List[Callable]:
        return self.get_mcp_methods("_is_mcp_tool")

    def get_mcp_prompts(self) -> List[Callable]:
        return self.get_mcp_methods("_is_mcp_prompt")

    def get_mcp_resources(self) -> List[Callable]:
        return self.get_mcp_methods("_is_mcp_resource")

    def get_mcp_methods(self, attribute) -> List[Callable]:
        """
        Introspects for methods decorated for an MCP type.
        """
        methods = []
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if callable(attr) and getattr(attr, attribute, False):
                methods.append(attr)
        return methods
