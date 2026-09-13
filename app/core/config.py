from __future__ import annotations
import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List

CONFIG_PATH = Path.home() / ".sniffer" / "config.json"

@dataclass
class ChannelPersist:
    id: int
    label: str = ""
    enabled: bool = True
    color: str = "#00BFFF"
    physPin: int = 0

@dataclass
class AppConfig:
    theme: str = "dark"  # dark | light | high_contrast
    recent_files: List[str] = field(default_factory=list)
    window_geometry: str = "1280x800"
    last_port: str = ""
    channels: List[dict] = field(default_factory=list)

    @classmethod
    def load(cls) -> "AppConfig":
        if CONFIG_PATH.exists():
            try:
                data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
                return cls(
                    theme=data.get("theme", "dark"),
                    recent_files=data.get("recent_files", []),
                    window_geometry=data.get("window_geometry", "1280x800"),
                    last_port=data.get("last_port", ""),
                    channels=data.get("channels", []),
                )
            except Exception:
                return cls()
        return cls()

    def save(self):
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        data = asdict(self)
        CONFIG_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def add_recent(self, path: str, limit: int = 10):
        if path in self.recent_files:
            self.recent_files.remove(path)
        self.recent_files.insert(0, path)
        self.recent_files = self.recent_files[:limit]
        self.save()
