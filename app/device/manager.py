"""DeviceManager — discovery, handshake, capture orchestration"""
from __future__ import annotations
import time
import threading
from typing import Optional, List
from app.core.logger import get_logger
from app.core.events import bus
from app.device.transport import SerialTransport, SimulationTransport
from app.device.models import DeviceInfo, DeviceStatus
from app.device.protocol import (
    PT_HELLO, PT_HELLO_ACK, PT_GET_STATUS, PT_STATUS, PT_CONFIG_CHANNELS, PT_CONFIG_CAPTURE,
    PT_CMD_START, PT_CMD_STOP, PT_CMD_RESET, PT_EVT_STARTED, PT_EVT_STOPPED,
    PT_DATA_TRANSITION, PT_DATA_SAMPLE, PT_EVT_ERROR, PT_PING, PT_PONG,
    build_hello_payload, parse_hello_ack, parse_status, build_config_channels, build_config_capture,
    parse_data_transition
)

log = get_logger("device")

class DeviceManager:
    def __init__(self):
        self.transport: Optional[object] = None
        self.info: Optional[DeviceInfo] = None
        self.status = DeviceStatus()
        self.connected = False
        self._poll_thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._handshake_done = threading.Event()

    # ── discovery ──
    def list_ports(self) -> List[str]:
        try:
            import serial.tools.list_ports
            return [p.device for p in serial.tools.list_ports.comports()]
        except Exception:
            return []

    def connect(self, port: str, baud: int = 115200, timeout: float = 2.0) -> bool:
        if self.connected:
            self.disconnect()
        # detect simulation port
        if port == "SIM" or port.startswith("SIM:"):
            replay = port[4:] if port.startswith("SIM:") else None
            self.transport = SimulationTransport(replay_path=replay if replay else None)
            self.transport.open()
            self.connected = True
            self._start_poll()
            # sim handshake auto
            ok = self.handshake(timeout=1.0)
            return ok
        tr = SerialTransport(port, baud)
        if not tr.open():
            return False
        self.transport = tr
        self.connected = True
        self._start_poll()
        ok = self.handshake(timeout=timeout)
        if not ok:
            log.warning("Handshake failed")
            # keep connected anyway? allow retry
        return ok

    def connect_simulated(self, replay_path: Optional[str] = None) -> bool:
        return self.connect("SIM:" + replay_path if replay_path else "SIM")

    def disconnect(self):
        self._stop.set()
        self.connected = False
        if self.transport:
            try:
                self.transport.close()
            except Exception:
                pass
            self.transport = None
        if self._poll_thread and self._poll_thread.is_alive():
            self._poll_thread.join(timeout=0.8)
        self.info = None
        bus.emit("device_disconnected", reason="user")

    def _start_poll(self):
        self._stop.clear()
        self._handshake_done.clear()
        self._poll_thread = threading.Thread(target=self._poll_loop, daemon=True, name="DevicePoll")
        self._poll_thread.start()

    def _poll_loop(self):
        while not self._stop.is_set():
            pkt = None
            try:
                if self.transport:
                    pkt = self.transport.poll_packet()  # type: ignore
            except Exception as e:
                log.error(f"poll error: {e}")
            if pkt:
                self._handle_packet(pkt)
            else:
                time.sleep(0.005)

    def _handle_packet(self, pkt):
        # log.debug(f"RX {pkt}")
        if pkt.type == PT_HELLO_ACK:
            try:
                d = parse_hello_ack(pkt.payload)
                fw_int = d["fw"]
                fw_str = f"{(fw_int>>16)&0xFF}.{(fw_int>>8)&0xFF}.{fw_int&0xFF}"
                hw_int = d["hw"]
                hw_str = f"{(hw_int>>16)&0xFF}.{(hw_int>>8)&0xFF}"
                self.info = DeviceInfo(
                    fw_version=fw_str, fw_int=fw_int,
                    hw_version=hw_str,
                    f_cpu=d["f_cpu"], ram_bytes=d["ram"],
                    num_channels=d["nch"], cartridge_id=d["cartridge"],
                    capabilities=d["caps"], uid=d["uid"]
                )
                self._handshake_done.set()
                bus.emit("device_connected", info=self.info)
                log.info(f"HELLO_ACK fw={fw_str} f_cpu={d['f_cpu']} cart={self.info.cartridge_name} caps={d['caps']:02b}")
            except Exception as e:
                log.error(f"HELLO_ACK parse error: {e}")
        elif pkt.type == PT_STATUS:
            try:
                d = parse_status(pkt.payload)
                self.status = DeviceStatus(state=d["state"], fill_pct=d["fill"], pending_bytes=d["pending"],
                                           transitions=d["transitions"], bytes_streamed=d["bytes_streamed"],
                                           crc_errors=d["crc_errors"], overruns=d["overruns"])
                bus.emit("device_status", status=self.status)
            except Exception as e:
                log.error(f"STATUS parse {e}")
        elif pkt.type == PT_DATA_TRANSITION:
            try:
                parsed = parse_data_transition(pkt.payload)
                if parsed:
                    base, records = parsed
                    bus.emit("data_transition", base=base, records=records, raw=pkt)
            except Exception as e:
                log.error(f"DATA_TRANSITION parse {e}")
        elif pkt.type == PT_DATA_SAMPLE:
            bus.emit("data_sample", payload=pkt.payload)
        elif pkt.type == PT_EVT_STARTED:
            bus.emit("capture_started", payload=pkt.payload)
        elif pkt.type == PT_EVT_STOPPED:
            bus.emit("capture_stopped", payload=pkt.payload)
        elif pkt.type == PT_EVT_ERROR:
            try:
                import struct
                code = struct.unpack_from("<H", pkt.payload, 0)[0]
                tlen = struct.unpack_from("<H", pkt.payload, 2)[0]
                text = pkt.payload[4:4+tlen].decode("utf-8", errors="ignore")
                bus.emit("device_error", code=code, text=text)
                log.warning(f"Device error {code}: {text}")
            except Exception:
                bus.emit("device_error", code=0, text="unknown")
        elif pkt.type == PT_PONG:
            bus.emit("pong", payload=pkt.payload)
        else:
            # unknown
            bus.emit("packet", pkt=pkt)

    def handshake(self, timeout: float = 1.5) -> bool:
        self._handshake_done.clear()
        if not self.transport:
            return False
        try:
            self.transport.send(PT_HELLO, build_hello_payload())  # type: ignore
        except Exception as e:
            log.error(f"send HELLO failed: {e}")
            return False
        ok = self._handshake_done.wait(timeout)
        return ok

    def send_config_channels(self, enable_mask: int, rising_mask: int = 0, falling_mask: int = 0):
        if not self.transport: return False
        payload = build_config_channels(enable_mask, rising_mask, falling_mask)
        return self.transport.send(PT_CONFIG_CHANNELS, payload)  # type: ignore

    def send_config_capture(self, mode: int = 0, trigger_mode: int = 0, sample_rate: int = 1000000,
                            pre_ms: int = 0, post_ms: int = 0, pattern_mask: int = 0, pattern_value: int = 0,
                            edge_ch: int = 0xFF, edge_type: int = 0):
        if not self.transport: return False
        payload = build_config_capture(mode, trigger_mode, sample_rate, pre_ms, post_ms, pattern_mask, pattern_value, edge_ch, edge_type)
        return self.transport.send(PT_CONFIG_CAPTURE, payload)  # type: ignore

    def start_capture(self):
        if self.transport:
            return self.transport.send(PT_CMD_START, b"")  # type: ignore
        return False

    def stop_capture(self):
        if self.transport:
            return self.transport.send(PT_CMD_STOP, b"")  # type: ignore
        return False

    def reset_device(self):
        if self.transport:
            return self.transport.send(PT_CMD_RESET, b"")  # type: ignore
        return False

    def ping(self, nonce: int = 0x12345678):
        import struct
        if self.transport:
            return self.transport.send(PT_PING, struct.pack("<Q", nonce))  # type: ignore
        return False

# singleton
device_manager = DeviceManager()
