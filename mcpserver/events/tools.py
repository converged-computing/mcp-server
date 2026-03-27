from typing import Any, Dict, List

from fastmcp import Context
from mcp.types import JSONRPCNotification

from mcpserver.events import get_event_manager


async def list_event_streams() -> List[Dict[str, Any]]:
    """
    Discovery tool to list all available reactive event providers and their requirements.

    Returns a list of providers (e.g., 'kubernetes', 'flux') along with:
    1. A description of the events they track.
    2. The specific 'parameters' dictionary keys required to filter events.

    Agents should call this first to understand what events can be subscribed to
    and what filters (like namespace, job_name, or resource_type) are valid.
    """
    return get_event_manager().list_event_streams()


async def subscribe(provider_name: str, params: Dict[str, Any], ctx: Context) -> Dict[str, str]:
    """
    Subscribes to an asynchronous event stream from a specific provider.

    Once called, the server will start a background watcher. When relevant events occur,
    the server will push 'notifications/event' messages to the agent.

    Arguments:
        provider_name: The name of the provider (e.g., 'flux' or 'kubernetes')
                       retrieved from list_event_streams.
        params: A dictionary of filters for the subscription.
                Example for Flux: {"app_name": "lammps", "job_name": "run-1"}
                Example for K8s:  {"resource_type": "pods", "namespace": "default"}
                Refer to list_event_streams for required/optional keys.

    Returns:
        A dictionary containing the 'subscription_id'. This ID is required to
        identify incoming notifications and to later unsubscribe.
    """
    manager = get_event_manager()

    # Validation: Ensure the provider exists before attempting logic
    available = [p["provider"] for p in manager.list_event_streams()]
    if provider_name not in available:
        return {
            "error": f"Provider '{provider_name}' not found. Available: {available}",
            "status": "failed",
        }

    # Internal bridge to route class-level events into MCP JSON-RPC notifications
    async def mcp_notify_bridge(sub_id: str, data: dict):
        if ctx and hasattr(ctx, "session") and ctx.session:
            notification = JSONRPCNotification(
                method="notifications/event",
                params={"subscription_id": sub_id, "provider": provider_name, "data": data},
            )

            try:
                # Now we pass the single object as required
                await ctx.session.send_notification(notification)
            except Exception as e:
                print(f"❌ Failed to send notification: {e}")

    try:
        sub_id = await manager.subscribe(provider_name, params, mcp_notify_bridge)
        return {
            "subscription_id": sub_id,
            "status": "subscribed",
            "message": f"Successfully subscribed to {provider_name}. Watch for notifications.",
        }
    except Exception as e:
        return {"error": str(e), "status": "failed"}


async def unsubscribe(subscription_id: str) -> Dict[str, Any]:
    """
    Terminates an active event subscription and stops the background watcher.

    Arguments:
        subscription_id: The unique ID returned during the initial 'subscribe' call.

    Returns:
        A status message indicating if the subscription was successfully closed.
    """
    success = await get_event_manager().unsubscribe(subscription_id)
    if success:
        return {"status": "success", "message": f"Subscription {subscription_id} has been closed."}
    else:
        return {
            "status": "error",
            "message": f"Subscription {subscription_id} not found or already closed.",
        }
