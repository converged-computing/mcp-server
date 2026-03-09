import time
from typing import Any, Dict

from mcpserver.tools.base import BaseTool
from mcpserver.tools.decorator import mcp


class SystemTool(BaseTool):
    """
    System tool specialized for Flux Framework.
    """

    def setup(self, manager=None):
        self.manager = manager

    @mcp.tool(name="get_status")
    def get_status(self) -> Dict[str, Any]:
        """
        Get status of the flux cluster.
        """
        import flux
        import flux.resource

        flux_meta = {"status": "error", "message": "Flux handle failed"}
        try:
            h = flux.Flux()
            listing = flux.resource.list.resource_list(h).get()
            flux_meta = {
                "status": "online",
                "free_cores": listing.free.ncores,
                "up_nodes": listing.up.nnodes,
            }
        except Exception as e:
            flux_meta["error"] = str(e)

        res = {"timestamp": time.time(), "system_type": "flux", "flux": flux_meta, "tools": {}}
        if self.manager:
            for tid, inst in self.manager.instances.items():
                if inst == self:
                    continue
                res["tools"][tid] = {"class": inst.__class__.__name__}
        return res
