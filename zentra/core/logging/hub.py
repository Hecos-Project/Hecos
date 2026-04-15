import threading
import queue
import time
from datetime import datetime

class LogHub:
    """
    Centralized hub for log event broadcasting.
    Supports multiple subscribers (e.g. SSE connections).
    """
    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        self.subscribers = []
        self._sub_lock = threading.Lock()
        self.history = [] # Last 100 logs for immediate context
        self.max_history = 100

    @classmethod
    def get_instance(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def broadcast(self, level, message, module=None):
        """Send a log event to all active subscribers."""
        evt = {
            "time": datetime.now().strftime("%H:%M:%S"),
            "level": level,
            "module": module or "SYSTEM",
            "text": message
        }
        
        # Keep history
        with self._sub_lock:
            self.history.append(evt)
            if len(self.history) > self.max_history:
                self.history.pop(0)
            
            # Dispatch to subscribers
            for sub_queue in self.subscribers:
                try:
                    sub_queue.put(evt, block=False)
                except queue.Full:
                    pass # Slow subscriber, skip

    def subscribe(self):
        """Returns a queue for a new subscriber."""
        q = queue.Queue(maxsize=1000)
        with self._sub_lock:
            self.subscribers.append(q)
        return q

    def unsubscribe(self, q):
        """Remove a subscriber queue."""
        with self._sub_lock:
            if q in self.subscribers:
                self.subscribers.remove(q)

def get_hub() -> LogHub:
    return LogHub.get_instance()
