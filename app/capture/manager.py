from __future__ import annotations
import threading
import time
from pathlib import Path
from typing import Optional
from app.core.logger import get_logger
from app.core.events import bus
from app.capture.writer import CaptureWriter

log = get_logger("capture")

class CaptureManager:
    def __init__(self):
        self.writer: Optional[CaptureWriter] = None
        self.path: Optional[Path] = None
        self.capturing = False
        self._transitions = 0
        self._start_ts = 0
        self._lock = threading.Lock()
        # Subscribe to device events
        bus.subscribe("data_transition", self._on_data)
        bus.subscribe("capture_started", self._on_started)
        bus.subscribe("capture_stopped", self._on_stopped)

    def start_capture(self, path: str|Path, f_cpu: int = 600_000_000, channels_meta=None, **kw):
        with self._lock:
            if self.capturing:
                log.warning("Already capturing")
                return False
            self.path = Path(path)
            self.writer = CaptureWriter(self.path, f_cpu=f_cpu, channels_meta=channels_meta, **kw)
            self.writer.open()
            self.capturing = True
            self._transitions = 0
            self._start_ts = time.time()
            log.info(f"Capture started -> {self.path}")
            bus.emit("capture_manager_started", path=str(self.path))
            return True

    def _on_data(self, base, records, raw=None):
        with self._lock:
            if not self.capturing or not self.writer:
                return
            try:
                self.writer.add_transitions(base, records)
                self._transitions += len(records)
                bus.emit("capture_progress", transitions=self._transitions, elapsed=time.time()-self._start_ts)
            except Exception as e:
                log.error(f"writer error: {e}")

    def _on_started(self, payload=None):
        log.info("Device reported capture started")

    def _on_stopped(self, payload=None):
        log.info(f"Device reported capture stopped: {payload}")
        self.stop_capture()

    def stop_capture(self):
        with self._lock:
            if not self.capturing:
                return
            self.capturing = False
            if self.writer:
                try:
                    self.writer.close()
                    log.info(f"Capture saved {self.path} transitions={self._transitions}")
                    bus.emit("capture_manager_stopped", path=str(self.path), transitions=self._transitions)
                except Exception as e:
                    log.error(f"close error {e}")
                self.writer = None

    def is_capturing(self) -> bool:
        return self.capturing

capture_manager = CaptureManager()
