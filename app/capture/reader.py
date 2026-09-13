from __future__ import annotations
import json
import struct
from pathlib import Path
from typing import Iterator, List, Tuple, Optional
from app.capture.format import HEADER_FMT, HEADER_SIZE, CHUNK_HEADER, CHUNK_TRANSITION, CHUNK_SAMPLE, CHUNK_EVENT, MAGIC
from app.utils.crc import crc32_ieee

class CaptureHeader:
    def __init__(self, magic:int, ver_major:int, ver_minor:int, created_ms:int, meta_len:int, f_cpu:int, num_ch:int, flags:int, total_trans:int, total_samples:int, mode:int, rate:int, meta:dict):
        self.magic=magic; self.ver_major=ver_major; self.ver_minor=ver_minor
        self.created_ms=created_ms; self.meta_len=meta_len; self.f_cpu=f_cpu
        self.num_channels=num_ch; self.flags=flags; self.total_transitions=total_trans
        self.total_samples=total_samples; self.capture_mode=mode; self.sample_rate=rate
        self.meta=meta

class CaptureReader:
    """Random-access + streaming reader for .stcap"""
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.header: Optional[CaptureHeader] = None
        self._meta_bytes = b""
        self._data_offset = 0
        self._load_header()

    def _load_header(self):
        with open(self.path, "rb") as fh:
            hdr_bytes = fh.read(HEADER_SIZE)
            if len(hdr_bytes) < HEADER_SIZE:
                raise ValueError("File too short for header")
            fields = struct.unpack(HEADER_FMT, hdr_bytes)
            magic, vMaj, vMin, created, meta_len, _res0, fcpu, nch, flags, totalTrans, totalSamples, mode, rate, _res = fields
            if magic != MAGIC:
                raise ValueError(f"Bad magic {magic:08X} not STCA")
            meta = {}
            meta_bytes = fh.read(meta_len)
            self._meta_bytes = meta_bytes
            if meta_bytes:
                try:
                    meta = json.loads(meta_bytes.decode("utf-8"))
                except Exception:
                    meta = {"raw": meta_bytes.decode("utf-8", errors="ignore")}
            self.header = CaptureHeader(magic, vMaj, vMin, created, meta_len, fcpu, nch, flags, totalTrans, totalSamples, mode, rate, meta)
            self._data_offset = HEADER_SIZE + meta_len

    def iter_chunks(self) -> Iterator[Tuple[int, bytes]]:
        with open(self.path, "rb") as fh:
            fh.seek(self._data_offset)
            while True:
                hdr = fh.read(CHUNK_HEADER.size)
                if not hdr or len(hdr) < CHUNK_HEADER.size:
                    break
                ctype, plen, crc = CHUNK_HEADER.unpack(hdr)
                payload = fh.read(plen)
                if len(payload) < plen:
                    break
                calc = crc32_ieee(payload)
                if calc != crc:
                    # CRC mismatch — still yield but mark? for now skip and continue
                    # raise?
                    pass
                yield ctype, payload

    def iter_transition_batches(self) -> Iterator[Tuple[int, List[Tuple[int,int]]]]:
        """Yields (base_cycles, [(sample, delta), ...]) with base per batch."""
        for ctype, payload in self.iter_chunks():
            if ctype != CHUNK_TRANSITION:
                continue
            if len(payload) < 10:
                continue
            base = struct.unpack_from("<Q", payload, 0)[0]
            count = struct.unpack_from("<H", payload, 8)[0]
            off = 10
            batch = []
            for _ in range(count):
                if off+6 > len(payload): break
                s,d = struct.unpack_from("<HI", payload, off)
                batch.append((s,d))
                off+=6
            yield base, batch

    def iter_transition_batches_raw(self):
        return self.iter_transition_batches()

    def get_all_transitions(self) -> List[Tuple[int,int,int]]:
        """Returns list of (abs_cycles, sample, delta) flattened. Warning: may be large."""
        out = []
        for base, batch in self.iter_transition_batches():
            cur = base
            for i, (s,d) in enumerate(batch):
                if i==0:
                    cur = base  # first delta is 0 or from base; per spec delta 0 for first, but we treat cur=base
                else:
                    cur += d
                # For first record, use base as absolute
                abs_c = base if i==0 else cur
                if i>0:
                    abs_c = cur
                else:
                    abs_c = base
                out.append((abs_c, s, d))
                if i==0:
                    cur = base
            # Actually need proper accumulation: records deltas include 0 for first.
        # Simpler second pass: recompute correctly
        # We'll do proper
        flat = []
        for base, batch in self.iter_transition_batches():
            acc = base
            for idx, (s,d) in enumerate(batch):
                if idx==0:
                    acc = base
                else:
                    acc += d
                flat.append((acc, s, d))
        return flat

    def get_time_series(self) -> Tuple[List[float], List[int]]:
        """Returns (times_sec, samples) for waveform. times relative to first."""
        if not self.header:
            return [],[]
        fcpu = self.header.f_cpu or 600_000_000
        all_trans = self.get_all_transitions()
        if not all_trans:
            return [],[]
        t0 = all_trans[0][0]
        times = [(c - t0)/fcpu for c,_,_ in all_trans]
        samples = [s for _,s,_ in all_trans]
        return times, samples

    def get_channels_meta(self):
        return self.header.meta.get("channels", []) if self.header else []
