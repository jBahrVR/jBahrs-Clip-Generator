import threading
from typing import Callable, Dict, List, Any

class Event:
    """Standard application event identifiers."""
    LOG = "log"
    STATUS = "status"
    PROGRESS = "progress"
    CONFIG_SAVED = "config_saved"
    PROMPT_UPDATED = "prompt_updated"
    CLIPS_UPDATED = "clips_updated"
    NAVIGATE = "navigate"
    BINARY_STATUS = "binary_status"
    QUEUE_UPDATED = "queue_updated"
    QUEUE_ITEM_STATUS = "queue_item_status"
    SOCIAL_PUBLISHED = "social_published"


class EventBus:
    """
    Thread-safe publisher/subscriber event hub.
    Decouples UI views, business controllers, and background workers.
    """

    def __init__(self):
        self._subscribers: Dict[str, List[Callable[..., Any]]] = {}
        self._lock = threading.Lock()

    def subscribe(self, event_name: str, handler: Callable[..., Any]) -> None:
        """Subscribes a callable handler to an event topic."""
        with self._lock:
            if event_name not in self._subscribers:
                self._subscribers[event_name] = []
            if handler not in self._subscribers[event_name]:
                self._subscribers[event_name].append(handler)

    def unsubscribe(self, event_name: str, handler: Callable[..., Any]) -> None:
        """Unsubscribes a callable handler from an event topic."""
        with self._lock:
            if event_name in self._subscribers:
                self._subscribers[event_name] = [h for h in self._subscribers[event_name] if h != handler]

    def publish(self, event_name: str, *args, **kwargs) -> None:
        """Publishes an event to all subscribed handlers."""
        with self._lock:
            handlers = list(self._subscribers.get(event_name, []))

        for handler in handlers:
            try:
                handler(*args, **kwargs)
            except Exception:
                # Protect other handlers from single-subscriber failure
                pass

    def subscriber_count(self, event_name: str) -> int:
        """Returns the number of active subscribers for an event."""
        with self._lock:
            return len(self._subscribers.get(event_name, []))

    def clear(self) -> None:
        """Clears all event subscriptions."""
        with self._lock:
            self._subscribers.clear()


_GLOBAL_BUS = EventBus()

def get_event_bus() -> EventBus:
    """Returns the singleton application event bus."""
    return _GLOBAL_BUS
