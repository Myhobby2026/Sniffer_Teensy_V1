"""USB framed protocol — mirrors firmware usb_protocol.h / docs/03"""
from __future__ import annotations
import struct
from dataclasses import dataclass
from typing import Iterator, Tuple, Optional
from app.utils.crc import crc16_ccitt

MAGIC = 0x534E  # "SN" little-endian 0x4E53 on wire? Actually bytes [0]=0x4E, [1]=0x53 — but spec says MAGIC 0x534E LE => bytes 0x4E,0x53
HEADER_SIZE = 7
CRC_SIZE = 2
MAX_PAYLOAD = 1024

# Packet types
PT_HELLO = 0x01
PT_HELLO_ACK = 0x02
PT_GET_STATUS = 0x03
PT_STATUS = 0x04
PT_CONFIG_CHANNELS = 0x05
PT_CONFIG_CAPTURE = 0x06
PT_CMD_START = 0x07
PT_CMD_STOP = 0x08
PT_CMD_RESET = 0x09
PT_EVT_STARTED = 0x0A
PT_EVT_STOPPED = 0x0B
PT_DATA_TRANSITION = 0x0C
PT_DATA_SAMPLE = 0x0D
PT_EVT_ERROR = 0x0E
PT_PING = 0x0F
PT_PONG = 0x10

@dataclass
class Packet:
    type: int
    seq: int
    payload: bytes

    def __repr__(self):
        return f"Packet(type=0x{self.type:02X}, seq={self.seq}, len={len(self.payload)})"

def encode_packet(pkt_type: int, payload: bytes = b"", seq: int = 0) -> bytes:
    if payload is None:
        payload = b""
    length = len(payload)
    if length > MAX_PAYLOAD:
        raise ValueError(f"payload too large {length}")
    header = struct.pack("<HBBHH", MAGIC & 0xFFFF, 0, 0, 0, 0)  # placeholder trick? Actually we pack manually
    # Build frame: MAGIC(2) TYPE(1) LEN(2) SEQ(2) PAYLOAD CRC(2)
    frame = struct.pack("<H", MAGIC)  # 2B little endian => bytes 0x4E,0x53
    frame += struct.pack("<B", pkt_type)
    frame += struct.pack("<H", length)
    frame += struct.pack("<H", seq & 0xFFFF)
    frame += payload
    crc_data = struct.pack("<B", pkt_type) + struct.pack("<H", length) + struct.pack("<H", seq & 0xFFFF) + payload
    crc = crc16_ccitt(crc_data)
    frame += struct.pack("<H", crc)
    return frame

def try_decode_one(buf: bytes) -> Tuple[Optional[Packet], int]:
    """Attempt to decode one packet from buf. Returns (packet_or_None, bytes_consumed).
    If no complete packet, packet is None and consumed=0. Scans for MAGIC."""
    n = len(buf)
    for start in range(n - 1):
        if buf[start] == (MAGIC & 0xFF) and buf[start+1] == ((MAGIC >> 8) & 0xFF):
            if n - start < HEADER_SIZE + CRC_SIZE:
                return None, 0  # need more data
            pkt_type = buf[start+2]
            length = buf[start+3] | (buf[start+4] << 8)
            if length > MAX_PAYLOAD:
                # bad length, skip this magic
                continue
            total = HEADER_SIZE + length + CRC_SIZE
            if n - start < total:
                return None, 0
            seq = buf[start+5] | (buf[start+6] << 8)
            payload = bytes(buf[start+HEADER_SIZE:start+HEADER_SIZE+length])
            recv_crc = buf[start+HEADER_SIZE+length] | (buf[start+HEADER_SIZE+length+1] << 8)
            crc_data = bytes([pkt_type]) + struct.pack("<H", length) + struct.pack("<H", seq) + payload
            calc = crc16_ccitt(crc_data)
            if calc != recv_crc:
                # CRC mismatch, skip this start and continue scanning
                continue
            pkt = Packet(type=pkt_type, seq=seq, payload=payload)
            return pkt, start + total
    return None, 0

class StreamDecoder:
    def __init__(self):
        self.buf = bytearray()
        self.crc_errors = 0
        self.frames = 0

    def feed(self, data: bytes) -> Iterator[Packet]:
        self.buf.extend(data)
        while True:
            pkt, consumed = try_decode_one(self.buf)
            if pkt is None:
                # If we have a lot of garbage, keep last byte if it could be start of MAGIC
                if len(self.buf) > 4096:
                    # Trim to last 2KB to avoid unbounded growth
                    del self.buf[:len(self.buf)-2048]
                # Also detect CRC error case: if we scanned and found MAGIC but CRC failed, try_decode returns None,0
                # We need to advance 1 byte to avoid infinite loop
                # Heuristic: if buffer starts with MAGIC but decode failed, it was CRC error
                if len(self.buf) >= 2 and self.buf[0] == (MAGIC & 0xFF) and self.buf[1] == ((MAGIC >>8) &0xFF) and len(self.buf) >= HEADER_SIZE:
                    # peek length
                    length = self.buf[3] | (self.buf[4]<<8)
                    total = HEADER_SIZE + length + CRC_SIZE
                    if len(self.buf) >= total:
                        # we had a candidate but CRC failed => count and drop 1 byte
                        self.crc_errors += 1
                        del self.buf[0]
                        continue
                break
            self.frames += 1
            # remove consumed bytes
            del self.buf[:consumed]
            yield pkt

# Helpers for building payloads per spec

def build_hello_payload(app_version_int: int = 0x00010000) -> bytes:
    import struct
    host_caps = 0
    host_id = b"SnifferGUI v1.0".ljust(16, b"\x00")
    return struct.pack("<II", app_version_int, host_caps) + host_id

def parse_hello_ack(payload: bytes) -> dict:
    import struct
    if len(payload) < 52:
        raise ValueError("HELLO_ACK too short")
    fw, hw, fcpu, ram, nch, cart, caps = struct.unpack_from("<IIIIHBB", payload, 0)
    uid = payload[20:52].split(b"\x00")[0].decode("utf-8", errors="ignore")
    return dict(fw=fw, hw=hw, f_cpu=fcpu, ram=ram, nch=nch, cartridge=cart, caps=caps, uid=uid)

def build_config_channels(enable_mask: int, rising_mask: int = 0, falling_mask: int = 0, pull_mode: int = 0) -> bytes:
    import struct
    return struct.pack("<HHHB", enable_mask & 0xFFFF, rising_mask & 0xFFFF, falling_mask & 0xFFFF, pull_mode & 0xFF)

def build_config_capture(mode: int = 0, trigger_mode: int = 0, sample_rate: int = 1000000,
                         pre_ms: int = 0, post_ms: int = 0, pattern_mask: int = 0, pattern_value: int = 0,
                         edge_ch: int = 0xFF, edge_type: int = 0) -> bytes:
    import struct
    return struct.pack("<BBIIIHHBB", mode &0xFF, trigger_mode &0xFF, sample_rate &0xFFFFFFFF,
                       pre_ms &0xFFFFFFFF, post_ms &0xFFFFFFFF, pattern_mask &0xFFFF, pattern_value &0xFFFF,
                       edge_ch &0xFF, edge_type &0xFF)

def parse_status(payload: bytes) -> dict:
    import struct
    if len(payload) < 16:
        raise ValueError("STATUS too short")
    state, fill, pending, trans, bstream, crcE, ov = struct.unpack_from("<BBHIIHH", payload, 0)
    return dict(state=state, fill=fill, pending=pending, transitions=trans, bytes_streamed=bstream, crc_errors=crcE, overruns=ov)

def parse_data_transition(payload: bytes):
    """Yield (sample, delta) tuples and base."""
    import struct
    if len(payload) < 10:
        return None
    base = struct.unpack_from("<Q", payload, 0)[0]
    count = struct.unpack_from("<H", payload, 8)[0]
    off = 10
    records = []
    for _ in range(count):
        if off + 6 > len(payload):
            break
        sample, delta = struct.unpack_from("<HI", payload, off)  # sample 2B, delta 4B? spec says sample 2 + delta 4
        # Note struct: "<HI" gives 2+4=6
        records.append((sample, delta))
        off += 6
    return base, records
