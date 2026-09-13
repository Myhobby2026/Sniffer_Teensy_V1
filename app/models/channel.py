from __future__ import annotations
from dataclasses import dataclass

DEFAULT_COLORS = [
    "#00BFFF","#FF5C5C","#7FFF7F","#FFD700","#FF8C00","#9D00FF","#00FFCC","#FF1493",
    "#6A5ACD","#32CD32","#FFA07A","#20B2AA","#FF69B4","#87CEEB","#ADFF2F","#FF4500",
]

@dataclass
class ChannelModel:
    id: int
    label: str = ""
    enabled: bool = True
    color: str = "#00BFFF"
    phys_pin: int = 0
    trigger: str = "none"  # none/rising/falling/both

    @property
    def display_label(self) -> str:
        return self.label or f"CH{self.id}"

@dataclass
class TriggerConfig:
    mode: str = "immediate"  # immediate | pattern | protocol
    pattern_mask: int = 0
    pattern_value: int = 0
    edge_ch: int = 0xFF
    edge_type: int = 0  # 0 none,1 rising,2 falling,3 both
    pre_ms: int = 0
    post_ms: int = 0
