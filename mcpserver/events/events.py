import asyncio
import inspect
from typing import Any, Awaitable, Callable, Dict, List


class SubscriptionManager:
    """
    Generic Manager that proxies MCP calls to external Event Classes.
    Does not require inheritance, only expects specific method signatures.
    """

    def __init__(self):
        # provider_name -> Instance of the external Event Class
        self._providers: Dict[str, Any] = {}
        # Track which provider owns which sub_id for routing unsubscribes
        self._sub_to_provider: Dict[str, str] = {}

    def register_provider(self, name: str, instance: Any):
        """
        Validates and registers an external class instance.
        """
        required_methods = ["get_metadata", "subscribe", "unsubscribe"]
        for method in required_methods:
            if not hasattr(instance, method) or not callable(getattr(instance, method)):
                raise TypeError(f"Event provider '{name}' must implement '{method}'")

        self._providers[name] = instance

    def list_event_streams(self) -> List[Dict[str, Any]]:
        """
        Aggregates metadata and docstrings from all registered external classes.
        """
        results = []
        for name, instance in self._providers.items():
            # Get the base metadata provided by the class
            meta = instance.get_metadata()

            # Sniff the docstrings from the subscribe method if metadata is thin
            subscribe_method = getattr(instance, "subscribe")
            doc = inspect.getdoc(subscribe_method) or meta.get("description", "")

            results.append(
                {
                    "provider": name,
                    "description": doc,
                    "parameters": meta.get("parameters", {}),
                    "capabilities": meta.get("capabilities", []),
                }
            )
        return results

    async def subscribe(
        self,
        provider_name: str,
        params: Dict[str, Any],
        notify_fn: Callable[[str, Dict[str, Any]], Awaitable[None]],
    ) -> str:
        """
        Proxies the subscription request to the specific class.
        """
        if provider_name not in self._providers:
            raise ValueError(f"Provider '{provider_name}' not found.")

        instance = self._providers[provider_name]

        # We pass the notify_fn to the class so it can push events back
        sub_id = await instance.subscribe(params, notify_fn)

        self._sub_to_provider[sub_id] = provider_name
        return sub_id

    async def unsubscribe(self, sub_id: str) -> bool:
        """
        Finds the owner of the sub_id and tells it to stop.
        """
        provider_name = self._sub_to_provider.get(sub_id)
        if not provider_name:
            return False

        instance = self._providers[provider_name]
        success = await instance.unsubscribe(sub_id)

        if success:
            del self._sub_to_provider[sub_id]
        return success

    async def cleanup_all(self):
        """
        Iterates through all active sub_ids and unsubscribes them.
        """
        ids = list(self._sub_to_provider.keys())
        for sub_id in ids:
            await self.unsubscribe(sub_id)
