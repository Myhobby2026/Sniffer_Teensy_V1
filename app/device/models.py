from __future__ import annotations
from dataclasses import dataclass

@dataclass
class DeviceInfo:
    fw_version: str = "0.0.0"
    fw_int: int = 0
    hw_version: str = "0.0.0"
    f_cpu: int = 600_000_000
    ram_bytes: int = 0
    num_channels: int = 16
    cartridge_id: int = 0
    capabilities: int = 0
    uid: str = ""

    @property
    def cartridge_name(self) -> str:
        return {0:"CARRIER-3V3",1:"CARRIER-5V",2:"CARRIER-RS232/485",3:"CARRIER-ANALOG"}.get(self.cartridge_id, f"UNKNOWN({self.cartridge_id})")

    def has_cap(self, bit: int) -> bool:
        return bool(self.capabilities & (1 << bit))

@dataclass
class DeviceStatus:
    state: int = 0  # 0 idle,1 armed,2 capturing,3 overflow,4 error
    fill_pct: int = 0
    pending_bytes: int = 0
    transitions: int = 0
    bytes_streamed: int = 0
    crc_errors: int = 0
    overruns: int = 0

    @property
    def state_name(self) -> str:
        return {0:"IDLE",1:"ARMED",2:"CAPTURING",3:"OVERFLOW",4:"ERROR"}.get(self.state, f"STATE_{self.state}")
