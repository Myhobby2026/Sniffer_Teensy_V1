import tkinter as tk
import tkinter.ttk as ttk
from app.models.channel import ChannelModel, DEFAULT_COLORS
from app.device.manager import device_manager
from app.core.logger import get_logger

log = get_logger("gui.channels")

class ChannelConfigPage(ttk.Frame):
    def __init__(self, parent, app_ref=None):
        super().__init__(parent)
        self.app_ref = app_ref
        self.rows = []
        self._build()

    def _build(self):
        top = ttk.Frame(self)
        top.pack(fill=tk.X, padx=12, pady=8)
        ttk.Label(top, text="Channel Configuration — 16 Independent Digital Inputs", font=("Segoe UI", 11, "bold")).pack(side=tk.LEFT)
        btns = ttk.Frame(top)
        btns.pack(side=tk.RIGHT)
        ttk.Button(btns, text="Enable All", command=lambda: self._set_all(True)).pack(side=tk.LEFT, padx=2)
        ttk.Button(btns, text="Disable All", command=lambda: self._set_all(False)).pack(side=tk.LEFT, padx=2)
        ttk.Button(btns, text="Apply to Device", command=self._apply).pack(side=tk.LEFT, padx=6)

        # header
        hdr = ttk.Frame(self)
        hdr.pack(fill=tk.X, padx=12, pady=(4,0))
        for txt,w in [("#",3),("En",3),("Label",16),("●",2),("Trigger",10),("Pin",6)]:
            ttk.Label(hdr, text=txt, width=w, foreground="#9E9E9E", font=("Segoe UI", 8, "bold")).pack(side=tk.LEFT, padx=2)

        # scrollable list
        container = ttk.Frame(self)
        container.pack(fill=tk.BOTH, expand=True, padx=12, pady=6)
        canvas = tk.Canvas(container, bg="#1E1E1E", highlightthickness=0)
        sb = ttk.Scrollbar(container, orient=tk.VERTICAL, command=canvas.yview)
        inner = ttk.Frame(canvas)
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.create_window((0,0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        # create rows
        from app.gui.widgets.channel_row import ChannelRow
        for i in range(16):
            color = DEFAULT_COLORS[i % len(DEFAULT_COLORS)]
            # default phys pin mapping mirrors docs/02
            phys = [0,1,2,3,4,5,6,7,8,9,10,11,12,13,32,33][i]
            row = ChannelRow(inner, ch_id=i, label=f"CH{i}", enabled=True, color=color, trigger="none", on_change=self._on_row_change)
            row.pack(fill=tk.X, pady=1)
            # add pin label
            ttk.Label(row, text=f"P{phys}", width=6, foreground="#9E9E9E").pack(side=tk.LEFT, padx=4)
            self.rows.append(row)

        # presets
        presets = ttk.LabelFrame(self, text="Bus Presets (applies labels & enables)", padding=8)
        presets.pack(fill=tk.X, padx=12, pady=8)
        for name, fn in [
            ("SPI 4-wire", self._preset_spi),
            ("I2C (2-wire)", self._preset_i2c),
            ("UART (2-wire)", self._preset_uart),
            ("8-bit Parallel", self._preset_parallel),
            ("Clear Labels", self._preset_clear),
        ]:
            ttk.Button(presets, text=name, command=fn).pack(side=tk.LEFT, padx=4)

        # safety note
        note = ttk.Frame(self)
        note.pack(fill=tk.X, padx=12, pady=6)
        ttk.Label(note, text="⚠  Never exceed 0–3.3 V on GPIO without the correct cartridge. See docs/07-safety-and-wiring.md", foreground="#CCA700", font=("Segoe UI", 8)).pack(anchor="w")

    def _set_all(self, en: bool):
        for r in self.rows:
            r.enabled_var.set(en)
        self._on_row_change()

    def _on_row_change(self, _row=None):
        # live update local model for waveform etc.
        if self.app_ref:
            self.app_ref.channels = [r.get_config() for r in self.rows]

    def _apply(self):
        # build masks and send to device
        enable_mask = 0
        rising = 0
        falling = 0
        for r in self.rows:
            cfg = r.get_config()
            if cfg["enabled"]:
                enable_mask |= 1 << cfg["id"]
            tr = cfg["trigger"]
            if tr in ("rising","both"):
                rising |= 1 << cfg["id"]
            if tr in ("falling","both"):
                falling |= 1 << cfg["id"]
        if device_manager.connected:
            ok = device_manager.send_config_channels(enable_mask, rising, falling)
            log.info(f"CONFIG_CHANNELS en={enable_mask:04X} r={rising:04X} f={falling:04X} -> {ok}")
            self._status(f"Applied: enabled {bin(enable_mask).count('1')}/16")
        else:
            self._status("No device — config saved locally, will apply on connect.")
        # persist to app ref
        if self.app_ref:
            self.app_ref.channels = [r.get_config() for r in self.rows]

    def _status(self, msg: str):
        if self.app_ref:
            self.app_ref.set_status(msg)

    # presets
    def _preset_spi(self):
        # CH0=SCLK,1=MOSI,2=MISO,3=CS, others off? Keep but relabel
        labels = ["SCLK","MOSI","MISO","CS"] + [f"CH{i}" for i in range(4,16)]
        for i,r in enumerate(self.rows):
            r.label_var.set(labels[i])
            r.enabled_var.set(i<4)
        self._on_row_change()

    def _preset_i2c(self):
        labels = ["SCL","SDA"] + [f"CH{i}" for i in range(2,16)]
        for i,r in enumerate(self.rows):
            r.label_var.set(labels[i])
            r.enabled_var.set(i<2)
        self._on_row_change()

    def _preset_uart(self):
        labels = ["TX","RX"] + [f"CH{i}" for i in range(2,16)]
        for i,r in enumerate(self.rows):
            r.label_var.set(labels[i])
            r.enabled_var.set(i<2)
        self._on_row_change()

    def _preset_parallel(self):
        for i,r in enumerate(self.rows):
            r.label_var.set(f"D{i}")
            r.enabled_var.set(i<8)
        self._on_row_change()

    def _preset_clear(self):
        for i,r in enumerate(self.rows):
            r.label_var.set(f"CH{i}")
            r.enabled_var.set(True)
        self._on_row_change()

    def get_channels_meta(self):
        return [r.get_config() for r in self.rows]
