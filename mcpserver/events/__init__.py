from typing import Optional

from .events import SubscriptionManager

_event_manager: Optional[SubscriptionManager] = None


def get_event_manager() -> SubscriptionManager:
    """
    Lazy-getter for the singleton manager.
    Ensures we only have one instance handling the background tasks.
    """
    global _event_manager
    if _event_manager is None:
        _event_manager = SubscriptionManager()
    return _event_manager


def has_event_manager() -> bool:
    """
    Check if the manager has been initialized.
    """
    return _event_manager is not None


__all__ = ["get_event_manager", "has_event_manager"]
