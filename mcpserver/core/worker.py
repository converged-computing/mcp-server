import asyncio
import socket
from typing import Optional

import httpx

from mcpserver.logger import logger


class WorkerManager:
    """
    A worker mcpserver advertises its tools to a parent hub.
    """

    def __init__(
        self,
        mcp,
        hub_url,
        secret,
        worker_id=None,
        public_url=None,
        worker_type="generic",
        labels=None,
    ):
        self.mcp = mcp
        self.hub_url = hub_url
        self.secret = secret
        self.worker_id = worker_id or socket.gethostname()
        self.worker_type = worker_type
        self.labels = self._parse_labels(labels)
        self.public_url = public_url

    @classmethod
    def from_args(cls, mcp, args, cfg) -> Optional["WorkerManager"]:
        """
        Factory to create a WorkerManager from CLI arguments.
        """
        if not getattr(args, "join", None):
            return None

        # Auto-construct public URL if not provided
        public_url = (
            args.public_url or f"http://{cfg.server.host}:{cfg.server.port}{cfg.server.path}"
        )
        return cls(
            mcp,
            hub_url=args.join,
            secret=args.join_secret,
            worker_id=args.register_id,
            public_url=public_url,
            worker_type=args.worker_type,
            labels=args.labels,
        )

    def _parse_labels(self, label_list) -> dict:
        """
        Converts ['key=val', 'key2=val2'] to a dictionary.
        """
        labels = {}
        if not label_list:
            return labels
        for item in label_list:
            if "=" in item:
                k, v = item.split("=", 1)
                labels[k.strip()] = v.strip()
        return labels

    async def run_registration(self):
        """
        worker registration payload.
        """
        await asyncio.sleep(1)
        async with httpx.AsyncClient() as client:
            payload = {
                "id": self.worker_id,
                "url": self.public_url,
                "type": self.worker_type,
                "labels": self.labels,
            }
            headers = {"X-MCP-Token": self.secret}
            try:
                res = await client.post(f"{self.hub_url}/register", json=payload, headers=headers)
                res.raise_for_status()
                logger.info(f"✅ Registered as '{self.worker_id}' ({self.worker_type})")
            except Exception as e:
                logger.error(f"❌ Registration failed: {e}")
