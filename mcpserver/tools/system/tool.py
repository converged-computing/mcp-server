import os
import platform
import time
from typing import Any, Dict

from mcpserver.tools.base import BaseTool
from mcpserver.tools.decorator import mcp


class SystemTool(BaseTool):
    """
    Provides server metadata and a manifest of loaded tools.
    """

    def setup(self, manager=None):
        # Store the manager reference provided by the standard loading strategy
        self.manager = manager

    @mcp.tool(name="get_status")
    def get_status(self) -> Dict[str, Any]:
        """
        Returns a structured report of the server environment and loaded tools.
        """
        # 1. Custom status implemented by this class
        status = {
            "timestamp": time.time(),
            "system": {
                "os": platform.system(),
                "node": platform.node(),
                "python": platform.python_version(),
                "cwd": os.getcwd() if hasattr(os, "getcwd") else "unknown",
            },
            "tools": {},
        }

        # 2. Metadata about tools (The Manifest)
        # We look at the manager's active instances
        if self.manager and hasattr(self.manager, "instances"):
            for tool_id, inst in self.manager.instances.items():
                if inst == self:
                    continue
                status["tools"][tool_id] = {
                    "class": inst.__class__.__name__,
                    "description": inst.__doc__.strip() if inst.__doc__ else "n/a",
                }

        return status
