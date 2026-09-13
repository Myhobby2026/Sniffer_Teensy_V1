from __future__ import annotations
from dataclasses import dataclass

@dataclass
class TriggerPattern:
    mask: int = 0
    value: int = 0
    edge_ch: int = 0xFF
    edge_type: int = 0

    def matches(self, prev: int, cur: int) -> bool:
        if self.mask != 0:
            if (cur & self.mask) != self.value:
                return False
            else:
                return True
        if self.edge_ch != 0xFF:
            bit = 1 << self.edge_ch
            rising = (~prev & cur) & bit
            falling = (prev & ~cur) & bit
            if self.edge_type == 1 and rising: return True
            if self.edge_type == 2 and falling: return True
            if self.edge_type == 3 and (rising or falling): return True
            return False
        return True
