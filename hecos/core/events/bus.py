import threading
from typing import Callable, Any, Dict, List
from hecos.core.logging import logger

_subscribers: Dict[str, List[Callable]] = {}
_lock = threading.RLock()

def subscribe(event_type: str, callback: Callable[[Dict[str, Any]], None]):
    """Subscribe to a specific event_type. Use '*' to subscribe to all events."""
    with _lock:
        if event_type not in _subscribers:
            _subscribers[event_type] = []
        if callback not in _subscribers[event_type]:
            _subscribers[event_type].append(callback)

def unsubscribe(event_type: str, callback: Callable):
    """Remove a subscription."""
    with _lock:
        if event_type in _subscribers and callback in _subscribers[event_type]:
            _subscribers[event_type].remove(callback)

def emit(event_type: str, payload: Dict[str, Any] = None):
    """Emit an event to all subscribers synchronously."""
    if payload is None:
        payload = {}
    
    with _lock:
        cbs = list(_subscribers.get(event_type, []))
        cbs_all = list(_subscribers.get("*", []))
    
    logger.info(f"[EVENTS] emit('{event_type}') → {len(cbs)} direct + {len(cbs_all)} wildcard subscribers")
    
    event_data = {"type": event_type, "payload": payload}
    
    for cb in cbs + cbs_all:
        try:
            cb(event_data)
        except Exception as e:
            logger.error(f"[EVENTS] Error in subscriber for {event_type}: {e}")
