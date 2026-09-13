"""Transport — serial reader thread + simulated transport"""
from __future__ import annotations
import threading
import queue
import time
from typing import Optional
from app.core.logger import get_logger
from app.device.protocol import StreamDecoder, Packet, encode_packet

log = get_logger("transport")

class SerialTransport:
    """Threaded serial transport with packet reassembly."""
    def __init__(self, port: str, baud: int = 115200):
        self.port = port
        self.baud = baud
        self._ser = None
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self.packet_queue: queue.Queue[Packet] = queue.Queue()
        self.decoder = StreamDecoder()
        self.connected = False
        self._seq = 0

    def open(self) -> bool:
        try:
            import serial
        except ImportError:
            log.error("pyserial not installed. pip install pyserial")
            return False
        try:
            import serial.tools.list_ports
            self._ser = serial.Serial(self.port, self.baud, timeout=0.05)
            # flush
            self._ser.reset_input_buffer()
            self._ser.reset_output_buffer()
            self.connected = True
            self._stop.clear()
            self._thread = threading.Thread(target=self._reader_loop, daemon=True, name="SerialReader")
            self._thread.start()
            log.info(f"Opened {self.port} @ {self.baud}")
            return True
        except Exception as e:
            log.error(f"Failed to open {self.port}: {e}")
            self.connected = False
            return False

    def close(self):
        self._stop.set()
        self.connected = False
        if self._ser:
            try:
                self._ser.close()
            except Exception:
                pass
            self._ser = None
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        log.info("Transport closed")

    def _reader_loop(self):
        while not self._stop.is_set():
            try:
                if self._ser is None or not self._ser.is_open:
                    time.sleep(0.05)
                    continue
                n = self._ser.in_waiting
                if n:
                    data = self._ser.read(n if n < 4096 else 4096)
                    if data:
                        for pkt in self.decoder.feed(data):
                            self.packet_queue.put(pkt)
                else:
                    # also try reading at least 1 byte with timeout
                    data = self._ser.read(1)
                    if data:
                        for pkt in self.decoder.feed(data):
                            self.packet_queue.put(pkt)
                    else:
                        time.sleep(0.002)
            except Exception as e:
                log.error(f"Reader error: {e}")
                time.sleep(0.1)
                # try to detect disconnect
                if self._ser is None or not getattr(self._ser, 'is_open', False):
                    self.connected = False
                    break

    def send(self, pkt_type: int, payload: bytes = b""):
        if not self.connected or self._ser is None:
            log.warning("send while not connected")
            return False
        frame = encode_packet(pkt_type, payload, self._seq)
        self._seq = (self._seq + 1) & 0xFFFF
        try:
            self._ser.write(frame)
            self._ser.flush()
            return True
        except Exception as e:
            log.error(f"send failed: {e}")
            return False

    def poll_packet(self) -> Optional[Packet]:
        try:
            return self.packet_queue.get_nowait()
        except queue.Empty:
            return None

# ── Simulation transport ──

class SimulationTransport:
    """Replays a .stcap or synthetic stream as if it were live device."""
    def __init__(self, replay_path: Optional[str] = None, f_cpu: int = 600_000_000):
        self.replay_path = replay_path
        self.f_cpu = f_cpu
        self.packet_queue: queue.Queue[Packet] = queue.Queue()
        self.connected = False
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._seq = 0

    def open(self) -> bool:
        self.connected = True
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        log.info(f"Simulation transport started replay={self.replay_path}")
        return True

    def close(self):
        self._stop.set()
        self.connected = False
        if self._thread:
            self._thread.join(timeout=1.0)

    def send(self, pkt_type: int, payload: bytes = b""):
        # Simulate device responses locally
        from app.device.protocol import PT_HELLO, PT_HELLO_ACK, PT_GET_STATUS, PT_STATUS, PT_CMD_START, PT_EVT_STARTED, PT_CMD_STOP, PT_EVT_STOPPED, PT_PING, PT_PONG
        import struct
        if pkt_type == PT_HELLO:
            # reply HELLO_ACK after short delay
            def reply():
                time.sleep(0.08)
                ack = struct.pack("<IIIIHBB", 0x00010000, 0x00010000, self.f_cpu, 1024*1024, 16, 0, 0b11) + b"SIMULATED-UID\x00".ljust(32, b"\x00")
                self.packet_queue.put(Packet(type=PT_HELLO_ACK, seq=0, payload=ack))
            threading.Thread(target=reply, daemon=True).start()
        elif pkt_type == PT_GET_STATUS:
            p = struct.pack("<BBHIIHH", 0, 0, 0, 0, 0, 0, 0)
            self.packet_queue.put(Packet(type=PT_STATUS, seq=0, payload=p))
        elif pkt_type == PT_CMD_START:
            # simulate streaming if replay file provided
            def stream():
                time.sleep(0.05)
                self.packet_queue.put(Packet(type=PT_EVT_STARTED, seq=0, payload=struct.pack("<Q", 0)))
                if self.replay_path:
                    try:
                        from app.capture.reader import CaptureReader
                        r = CaptureReader(self.replay_path)
                        for base, records in r.iter_transition_batches_raw():
                            # chunk into packets like device
                            # records is list of (sample, delta)
                            # base is uint64
                            # pack payload per spec
                            for i in range(0, len(records), 85):
                                chunk = records[i:i+85]
                                payload = struct.pack("<QH", base, len(chunk))
                                # need to compute base for chunk offset? simplified: use base + sum deltas up to i
                                # For sim, just use base for each chunk (host reconstructs)
                                for s,d in chunk:
                                    payload += struct.pack("<HI", s, d)
                                # advance base for next chunk
                                for _,d in chunk:
                                    base += d
                                from app.device.protocol import PT_DATA_TRANSITION
                                self.packet_queue.put(Packet(type=PT_DATA_TRANSITION, seq=0, payload=payload))
                                if self._stop.is_set():
                                    return
                                time.sleep(0.02)
                        self.packet_queue.put(Packet(type=PT_EVT_STOPPED, seq=0, payload=b"sim_complete"))
                    except Exception as e:
                        log.error(f"sim replay error: {e}")
                else:
                    # synthetic sawtooth
                    import struct, random
                    base = 0
                    for _ in range(5):
                        records = []
                        s = 0
                        for i in range(50):
                            s ^= 1 << (i % 16)
                            d = 6000  # ~10us @600MHz
                            records.append((s & 0xFFFF, d))
                        payload = struct.pack("<QH", base, len(records))
                        for sv,dv in records:
                            payload += struct.pack("<HI", sv, dv)
                            base += dv
                        from app.device.protocol import PT_DATA_TRANSITION
                        self.packet_queue.put(Packet(type=PT_DATA_TRANSITION, seq=0, payload=payload))
                        time.sleep(0.05)
                    self.packet_queue.put(Packet(type=PT_EVT_STOPPED, seq=0, payload=b"sim_complete"))
            threading.Thread(target=stream, daemon=True).start()
        elif pkt_type == PT_PING:
            self.packet_queue.put(Packet(type=PT_PONG, seq=0, payload=payload))
        return True

    def poll_packet(self):
        try:
            return self.packet_queue.get_nowait()
        except queue.Empty:
            return None

    def _loop(self):
        while not self._stop.is_set():
            time.sleep(0.05)
