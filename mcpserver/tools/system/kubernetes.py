import os
import platform
import time
from typing import Any, Dict

from mcpserver.tools.base import BaseTool
from mcpserver.tools.decorator import mcp


class SystemTool(BaseTool):
    """
    System tool specialized for Kubernetes environments.
    Discovers cluster topology, resource pressures, and tool manifests.
    """

    def setup(self, manager=None):
        self.manager = manager
        self._k8s_loaded = False
        try:
            from kubernetes import client, config

            try:
                config.load_kube_config()
            except:
                config.load_incluster_config()

            self.v1 = client.CoreV1Api()
            self._k8s_loaded = True
        except Exception as e:
            self._k8s_error = str(e)

    @mcp.tool(name="get_status")
    async def get_status(self) -> Dict[str, Any]:
        """
        Returns Kubernetes cluster status, node telemetry, and loaded tool manifest.
        """
        from mcpserver.app import mcp as mcp_instance
        from mcpserver.cli.manager import ToolManager

        manager = self.manager or ToolManager.get_instance()
        wm = getattr(mcp_instance, "worker_manager", None)

        # Base identity
        res = {
            "timestamp": time.time(),
            "system_type": "kubernetes",
            "id": wm.worker_id if wm else platform.node(),
            "kubeconfig_path": os.environ.get("KUBECONFIG", "~/.kube/config"),
            "kubernetes": self._get_kube_stats(),
            "tools": {},
        }

        if manager:
            # Add Discovered Classes
            for tool_id, inst in manager.instances.items():
                if inst == self:
                    continue
                res["tools"][tool_id] = {
                    "class": inst.__class__.__name__,
                    "description": inst.__doc__.strip() if inst.__doc__ else "n/a",
                }

            # Add Explicitly Registered Functions (from YAML)
            if hasattr(manager, "explicit_metadata"):
                for name, meta in manager.explicit_metadata.items():
                    res["tools"][name] = meta

        # Handle Hub/Fleet recursion
        hm = getattr(mcp_instance, "hub_manager", None)
        if hm:
            res["fleet"] = await hm.fetch_all_statuses()

        return res

    def _get_kube_stats(self) -> Dict[str, Any]:
        """
        Queries the K8s API for node and 'queue' (pod) statistics.
        """
        if not self._k8s_loaded:
            return {
                "status": "error",
                "message": getattr(self, "_k8s_error", "K8s client not initialized"),
            }

        stats = {
            "status": "online",
            "nodes": {"total": 0, "ready": 0, "capacity": {"cpu": 0, "mem_bytes": 0}},
            "workload_summary": {"running_pods": 0, "pending_pods": 0},
        }

        try:
            # Gather Node Stats
            nodes = self.v1.list_node()
            stats["nodes"]["total"] = len(nodes.items)
            for node in nodes.items:
                # Check Ready status
                if any(c.type == "Ready" and c.status == "True" for c in node.status.conditions):
                    stats["nodes"]["ready"] += 1

                # Aggregate Capacity
                stats["nodes"]["capacity"]["cpu"] += int(node.status.capacity.get("cpu", 0))
                # Note: Mem strings like '32Gi' need parsing for real math, returning raw for now
                stats["nodes"]["capacity"]["mem_raw"] = node.status.capacity.get("memory")

            # Gather Pod Stats (The "Queue")
            pods = self.v1.list_pod_for_all_namespaces()
            for pod in pods.items:
                if pod.status.phase == "Running":
                    stats["workload_summary"]["running_pods"] += 1
                elif pod.status.phase == "Pending":
                    stats["workload_summary"]["pending_pods"] += 1

        except Exception as e:
            return {"status": "partial_error", "error": str(e)}

        return stats
