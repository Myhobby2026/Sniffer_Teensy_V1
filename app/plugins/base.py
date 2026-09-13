from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Iterable, List, Dict, Tuple

class Decoder(ABC):
    name: str = "base"
    description: str = ""

    @abstractmethod
    def decode(self, transitions: Iterable[Tuple[int,int,int]], config: Dict) -> List[Dict]:
        """transitions: iterable of (abs_cycles, sample, delta). Return list of packets."""
        raise NotImplementedError

    def auto_detect(self, transitions: Iterable[Tuple[int,int,int]], f_cpu: int = 600_000_000) -> Tuple[bool, float, str]:
        """Return (is_candidate, confidence 0-100, reason). Never claim certainty without evidence."""
        return False, 0.0, "not implemented"

# Registry
REGISTRY: Dict[str, Decoder] = {}

def register(decoder: Decoder):
    REGISTRY[decoder.name] = decoder
