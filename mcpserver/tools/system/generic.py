# mcpserver/tools/system/generic.py
import platform
import socket
import time
from typing import Any, Dict

from mcpserver.tools.base import BaseTool
from mcpserver.tools.decorator import mcp


class SystemTool(BaseTool):
    """
    Default system tool (generic) to return status
    """

    def setup(self, manager=None):
        self.manager = manager

    @mcp.tool(name="get_status")
    async def get_status(self) -> Dict[str, Any]:
        from mcpserver.app import mcp as mcp_instance

        # This is the concept of the server identity
        # If no worker_manager exists, we are a one-off standalone server
        wm = getattr(mcp_instance, "worker_manager", None)

        res = {
            "id": wm.worker_id if wm else socket.gethostname(),
            "type": wm.worker_type if wm else "standalone",
            "labels": wm.labels if wm else {},
            "timestamp": time.time(),
            "system_type": "generic",
            "environment": {
                "os": platform.system(),
                "python": platform.python_version(),
            },
            "tools": {},
        }

        # Tool manifest. Should work even for one-off servers
        if self.manager:
            for tool_id, inst in self.manager.instances.items():
                if inst == self:
                    continue
                res["tools"][tool_id] = {
                    "class": inst.__class__.__name__,
                    "description": inst.__doc__.strip() if inst.__doc__ else "n/a",
                }

        # 3. Fleet Check (Only if this one-off happens to be a Hub)
        hm = getattr(mcp_instance, "hub_manager", None)
        if hm:
            res["fleet"] = await hm.fetch_all_statuses()

        return res
