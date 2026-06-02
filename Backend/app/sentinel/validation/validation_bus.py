# app/sentinel/telemetry/validation_bus.py
"""
Synchronous in-memory bus for collecting validation events throughout a single projection cycle.
"""
from typing import Dict, List, Any
import threading

class ValidationBus:
    """
    A lightweight, thread-safe, in-memory event bus.
    Stores validation events (like branch exploration, failures, governance decisions)
    to be flushed to the ValidationLogger at the end of the execution cycle.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ValidationBus, cls).__new__(cls)
                cls._instance.events = []
                cls._instance._bus_lock = threading.Lock()
        return cls._instance

    def emit(self, event_type: str, payload: Dict[str, Any]):
        """
        Synchronously append an event to the bus.
        """
        with self._bus_lock:
            self.events.append({
                "type": event_type,
                "payload": payload
            })

    def get_events(self) -> List[Dict[str, Any]]:
        """
        Returns a copy of the current events.
        """
        with self._bus_lock:
            return list(self.events)

    def clear(self):
        """
        Clears all events from the bus (typically called at the start of a cycle).
        """
        with self._bus_lock:
            self.events.clear()
