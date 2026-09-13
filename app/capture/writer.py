from __future__ import annotations
import json
import time
import struct
from pathlib import Path
from typing import List, Optional
from app.capture.format import HEADER_FMT, HEADER_SIZE, CHUNK_HEADER, CHUNK_TRANSITION, CHUNK_SAMPLE, CHUNK_EVENT, MAGIC, VERSION_MAJOR, VERSION_MINOR
from app.utils.crc import crc32_ieee

class CaptureWriter:
    """Writes .stcap file incrementally. Not thread-safe — caller must serialize."""
    def __init__(self, path: str | Path, f_cpu: int = 600_000_000, num_channels: int = 16,
                 capture_mode: int = 0, sample_rate: int = 0, channels_meta: Optional[List[dict]] = None,
                 app_version: str = "1.0.0", fw_version: str = "1.0.0", device_uid: str = "", trigger: Optional[dict] = None,
                 notes: str = "", extra_meta: Optional[dict] = None):
        self.path = Path(path)
        self.f_cpu = f_cpu
        self.num_channels = num_channels
        self.capture_mode = capture_mode
        self.sample_rate = sample_rate
        self.channels_meta = channels_meta or []
        self.app_version = app_version
        self.fw_version = fw_version
        self.device_uid = device_uid
        self.trigger = trigger or {}
        self.notes = notes
        self.extra_meta = extra_meta or {}
        self._fh = None
        self._meta_len = 0
        self._total_transitions = 0
        self._total_samples = 0
        self._has_trans = False
        self._has_samples = False
        self._header_pos = 0
        self._created_ms = int(time.time()*1000)

    def open(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = open(self.path, "wb")
        # placeholder header (128 zeros)
        self._fh.write(b"\x00"*HEADER_SIZE)
        # build metadata
        meta = {
            "appVersion": self.app_version,
            "fwVersion": self.fw_version,
            "deviceUid": self.device_uid,
            "channels": self.channels_meta,
            "trigger": self.trigger,
            "notes": self.notes,
            "host": "Python",
            **self.extra_meta,
        }
        meta_bytes = json.dumps(meta, indent=2).encode("utf-8")
        self._meta_len = len(meta_bytes)
        self._fh.write(meta_bytes)
        return self

    def __enter__(self):
        return self.open()

    def __exit__(self, exc_type, exc, tb):
        self.close()

    def add_transitions(self, base_cycles: int, records: List[tuple[int,int]]):
        """records: list of (sample:uint16, delta:uint32)"""
        if not self._fh:
            raise RuntimeError("writer not open")
        if not records:
            return
        self._has_trans = True
        self._total_transitions += len(records)
        # Build payload: base Q, count H, records 6 each
        payload = struct.pack("<QH", base_cycles & 0xFFFFFFFFFFFFFFFF, len(records))
        for s,d in records:
            payload += struct.pack("<HI", s & 0xFFFF, d & 0xFFFFFFFF)
        crc = crc32_ieee(payload)
        header = CHUNK_HEADER.pack(CHUNK_TRANSITION, len(payload), crc)
        self._fh.write(header)
        self._fh.write(payload)

    def add_samples(self, base_cycles: int, samples: List[int], sample_rate: Optional[int] = None):
        if not self._fh:
            raise RuntimeError("writer not open")
        self._has_samples = True
        self._total_samples += len(samples)
        sr = sample_rate if sample_rate is not None else self.sample_rate
        payload = struct.pack("<QII", base_cycles & 0xFFFFFFFFFFFFFFFF, len(samples), sr)
        for s in samples:
            payload += struct.pack("<H", s & 0xFFFF)
        crc = crc32_ieee(payload)
        header = CHUNK_HEADER.pack(CHUNK_SAMPLE, len(payload), crc)
        self._fh.write(header)
        self._fh.write(payload)

    def add_event(self, timestamp_cycles: int, code: int, text: str = ""):
        if not self._fh:
            raise RuntimeError("writer not open")
        tb = text.encode("utf-8")
        payload = struct.pack("<QHH", timestamp_cycles & 0xFFFFFFFFFFFFFFFF, code & 0xFFFF, len(tb)) + tb
        crc = crc32_ieee(payload)
        header = CHUNK_HEADER.pack(CHUNK_EVENT, len(payload), crc)
        self._fh.write(header)
        self._fh.write(payload)

    def close(self):
        if not self._fh:
            return
        # Optionally write footer? skip for streaming compat
        # Now patch header at offset 0
        flags = (1 if self._has_trans else 0) | (2 if self._has_samples else 0)
        # HEADER_FMT = "<IHHQIIQHHQQII68s"
        # fields: magic, verMajor, verMinor, createdMs, metaLen, reserved0, fCpu, numCh, flags, totalTrans, totalSamples, mode, rate, reserved
        reserved = b"\x00"*68
        header = struct.pack(HEADER_FMT, MAGIC, VERSION_MAJOR, VERSION_MINOR, self._created_ms, self._meta_len, 0, self.f_cpu & 0xFFFFFFFFFFFFFFFF, self.num_channels &0xFFFF, flags &0xFFFF, self._total_transitions &0xFFFFFFFFFFFFFFFF, self._total_samples &0xFFFFFFFFFFFFFFFF, self.capture_mode &0xFFFFFFFF, self.sample_rate &0xFFFFFFFF, reserved)
        assert len(header) == HEADER_SIZE
        self._fh.seek(0)
        self._fh.write(header)
        self._fh.close()
        self._fh = None

    # convenience
    @property
    def total_transitions(self): return self._total_transitions
