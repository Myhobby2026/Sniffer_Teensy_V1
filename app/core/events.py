from __future__ import annotations
from typing import Callable, Dict, List

class EventBus:
    """Simple pub/sub, thread-safe for emit from any thread (handlers run in emit thread).
    GUI handlers should marshal to Tk via root.after if needed."""
    def __init__(self):
        self._subs: Dict[str, List[Callable]] = {}

    def subscribe(self, event: str, handler: Callable):
        self._subs.setdefault(event, []).append(handler)

    def unsubscribe(self, event: str, handler: Callable):
        if event in self._subs:
            try:
                self._subs[event].remove(handler)
            except ValueError:
                pass

    def emit(self, event: str, *args, **kwargs):
        for h in list(self._subs.get(event, [])):
            try:
                h(*args, **kwargs)
            except Exception:
                import traceback
                traceback.print_exc()

bus = EventBus()
