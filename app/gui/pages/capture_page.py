import tkinter as tk
import tkinter.ttk as ttk
from tkinter import filedialog, messagebox
from pathlib import Path
import time
from app.device.manager import device_manager
from app.capture.manager import capture_manager
from app.core.events import bus
from app.core.logger import get_logger
from app.core.config import AppConfig

log = get_logger("gui.capture")

class CapturePage(ttk.Frame):
    def __init__(self, parent, app_ref=None):
        super().__init__(parent)
        self.app_ref = app_ref
        self.capturing = False
        self._elapsed = 0
        self._transitions = 0
        self._file_path = tk.StringVar(value=str(Path.home() / "capture.stcap"))
        self.mode_var = tk.StringVar(value="Transition (edge-compressed)")
        self.rate_var = tk.StringVar(value="1000000")
        self.pre_var = tk.StringVar(value="0")
        self.post_var = tk.StringVar(value="0")
        self.pattern_mask_var = tk.StringVar(value="0x0000")
        self.pattern_value_var = tk.StringVar(value="0x0000")
        self.edge_ch_var = tk.StringVar(value="none")
        self.edge_type_var = tk.StringVar(value="none")
        self._build()
        bus.subscribe("capture_progress", self._on_progress)
        bus.subscribe("capture_manager_started", self._on_mgr_started)
        bus.subscribe("capture_manager_stopped", self._on_mgr_stopped)
        bus.subscribe("device_status", self._on_dev_status)

    def _build(self):
        top = ttk.Frame(self)
        top.pack(fill=tk.X, padx=12, pady=8)
        ttk.Label(top, text="Capture", font=("Segoe UI", 11, "bold")).pack(side=tk.LEFT)
        self.state_lbl = ttk.Label(top, text="Idle", foreground="#9E9E9E")
        self.state_lbl.pack(side=tk.LEFT, padx=12)

        # file row
        fr = ttk.Frame(self)
        fr.pack(fill=tk.X, padx=12, pady=4)
        ttk.Label(fr, text="Save to:").pack(side=tk.LEFT)
        ttk.Entry(fr, textvariable=self._file_path, width=48).pack(side=tk.LEFT, padx=6, fill=tk.X, expand=True)
        ttk.Button(fr, text="Browse…", command=self._browse).pack(side=tk.LEFT, padx=4)

        # mode
        mode_fr = ttk.LabelFrame(self, text="Capture Mode", padding=8)
        mode_fr.pack(fill=tk.X, padx=12, pady=6)
        ttk.Label(mode_fr, text="Mode:").grid(row=0, column=0, sticky="w")
        ttk.Combobox(mode_fr, textvariable=self.mode_var, values=["Transition (edge-compressed)","Continuous (periodic)"], width=28, state="readonly").grid(row=0, column=1, sticky="w", padx=6)
        ttk.Label(mode_fr, text="Rate (Hz, continuous only):").grid(row=0, column=2, sticky="w", padx=(12,0))
        ttk.Entry(mode_fr, textvariable=self.rate_var, width=10).grid(row=0, column=3, sticky="w", padx=4)
        ttk.Label(mode_fr, text="Pre-trigger (ms):").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Entry(mode_fr, textvariable=self.pre_var, width=10).grid(row=1, column=1, sticky="w", padx=6, pady=4)
        ttk.Label(mode_fr, text="Post-trigger (ms):").grid(row=1, column=2, sticky="w", padx=(12,0))
        ttk.Entry(mode_fr, textvariable=self.post_var, width=10).grid(row=1, column=3, sticky="w", padx=4, pady=4)

        # trigger
        trig = ttk.LabelFrame(self, text="Trigger (Phase 1: Immediate; Pattern ready for Phase 2)", padding=8)
        trig.pack(fill=tk.X, padx=12, pady=6)
        ttk.Label(trig, text="Pattern mask (hex):").grid(row=0, column=0, sticky="w")
        ttk.Entry(trig, textvariable=self.pattern_mask_var, width=10).grid(row=0, column=1, sticky="w", padx=6)
        ttk.Label(trig, text="Pattern value (hex):").grid(row=0, column=2, sticky="w", padx=(12,0))
        ttk.Entry(trig, textvariable=self.pattern_value_var, width=10).grid(row=0, column=3, sticky="w", padx=4)
        ttk.Label(trig, text="Edge ch:").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Combobox(trig, textvariable=self.edge_ch_var, values=["none"]+[f"CH{i}" for i in range(16)], width=10, state="readonly").grid(row=1, column=1, sticky="w", padx=6, pady=4)
        ttk.Label(trig, text="Edge type:").grid(row=1, column=2, sticky="w", padx=(12,0))
        ttk.Combobox(trig, textvariable=self.edge_type_var, values=["none","rising","falling","both"], width=10, state="readonly").grid(row=1, column=3, sticky="w", padx=4, pady=4)

        # controls
        ctrl = ttk.Frame(self)
        ctrl.pack(fill=tk.X, padx=12, pady=10)
        self.start_btn = ttk.Button(ctrl, text="● Start Capture", command=self._start)
        self.start_btn.pack(side=tk.LEFT, padx=4)
        self.stop_btn = ttk.Button(ctrl, text="■ Stop", command=self._stop, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=4)
        ttk.Button(ctrl, text="Reset Device Buffers", command=self._reset).pack(side=tk.LEFT, padx=8)

        # progress
        prog = ttk.LabelFrame(self, text="Progress", padding=8)
        prog.pack(fill=tk.BOTH, expand=True, padx=12, pady=6)
        self.progress = ttk.Progressbar(prog, mode="indeterminate")
        self.progress.pack(fill=tk.X, pady=4)
        self.stats_var = tk.StringVar(value="Transitions: 0  |  Elapsed: 0.0 s  |  Rate: —")
        ttk.Label(prog, textvariable=self.stats_var, font=("Consolas", 9)).pack(anchor="w", pady=4)
        self.log_text = tk.Text(prog, height=8, bg="#252526", fg="#D4D4D4", relief=tk.FLAT, font=("Consolas", 8))
        self.log_text.pack(fill=tk.BOTH, expand=True, pady=4)
        self.log_text.configure(state=tk.DISABLED)

        # tips
        tip = ttk.Frame(self)
        tip.pack(fill=tk.X, padx=12, pady=6)
        ttk.Label(tip, text="Tip: Start with immediate trigger and transition mode. For SPI ~1 MHz, capture 50–200 ms.", foreground="#6A9955", font=("Segoe UI", 8)).pack(anchor="w")

    def _browse(self):
        p = filedialog.asksaveasfilename(defaultextension=".stcap", filetypes=[("Sniffer capture","*.stcap"),("All","*.*")], initialfile="capture.stcap")
        if p:
            self._file_path.set(p)

    def _parse_hex(self, s: str) -> int:
        s=s.strip()
        if s.lower().startswith("0x"):
            return int(s,16)
        if s=="": return 0
        return int(s,0)

    def _start(self):
        if self.capturing:
            return
        if not device_manager.connected:
            if not messagebox.askyesno("No device", "No device connected. Start simulated capture instead?\n(You can also connect a real Teensy in Device page)"):
                return
            device_manager.connect_simulated()

        # validate path
        save_path = self._file_path.get().strip()
        if not save_path:
            messagebox.showerror("Error","Please choose a save path.")
            return
        # build capture config
        mode = 0 if "Transition" in self.mode_var.get() else 1
        try:
            rate = int(self.rate_var.get())
            pre = int(self.pre_var.get())
            post = int(self.post_var.get())
            pmask = self._parse_hex(self.pattern_mask_var.get())
            pval = self._parse_hex(self.pattern_value_var.get())
            edge_ch_str = self.edge_ch_var.get()
            edge_ch = 0xFF if edge_ch_str=="none" else int(edge_ch_str[2:])
            edge_type_map = {"none":0,"rising":1,"falling":2,"both":3}
            edge_type = edge_type_map.get(self.edge_type_var.get(),0)
        except Exception as e:
            messagebox.showerror("Invalid config", str(e))
            return
        trigger_mode = 0
        if pmask!=0 or edge_ch!=0xFF:
            trigger_mode = 1

        # send config to device
        device_manager.send_config_capture(mode, trigger_mode, rate, pre, post, pmask, pval, edge_ch, edge_type)
        # also send channel config from app_ref
        if self.app_ref and hasattr(self.app_ref, "channels"):
            en = 0; rising=0; falling=0
            for ch in self.app_ref.channels:
                if ch.get("enabled"):
                    en |= 1<<ch["id"]
                tr = ch.get("trigger","none")
                if tr in ("rising","both"): rising |= 1<<ch["id"]
                if tr in ("falling","both"): falling |= 1<<ch["id"]
            device_manager.send_config_channels(en, rising, falling)
            channels_meta = self.app_ref.channels
        else:
            channels_meta = []

        # start writer
        f_cpu = device_manager.info.f_cpu if device_manager.info else 600_000_000
        ok = capture_manager.start_capture(save_path, f_cpu=f_cpu, channels_meta=channels_meta,
                                           capture_mode=mode, sample_rate=rate,
                                           trigger={"mode": "pattern" if trigger_mode else "immediate", "mask":pmask, "value":pval})
        if not ok:
            messagebox.showerror("Capture", "Already capturing")
            return
        # tell device to start
        device_manager.start_capture()
        self.capturing = True
        self.start_btn.configure(state=tk.DISABLED)
        self.stop_btn.configure(state=tk.NORMAL)
        self.state_lbl.configure(text="Capturing…", foreground="#89D185")
        self.progress.start(12)
        self._log(f"Capture started → {save_path}  mode={'TRANSITION' if mode==0 else 'CONT'}")
        # remember recent dir
        try:
            cfg = AppConfig.load()
            cfg.add_recent(save_path)
        except Exception:
            pass

    def _stop(self):
        if not self.capturing:
            return
        device_manager.stop_capture()
        # manager will close on EVT_STOPPED, but also force after timeout
        self.after(600, self._force_stop_if_needed)
        self._log("Stop requested…")

    def _force_stop_if_needed(self):
        if capture_manager.is_capturing():
            capture_manager.stop_capture()
            self._finalize()

    def _reset(self):
        device_manager.reset_device()
        self._log("Device buffers reset.")

    def _on_progress(self, transitions=0, elapsed=0):
        self._transitions = transitions
        self._elapsed = elapsed
        rate = transitions/elapsed if elapsed>0 else 0
        self.stats_var.set(f"Transitions: {transitions:,}  |  Elapsed: {elapsed:.1f} s  |  Rate: {rate:,.0f} trans/s")
        if self.app_ref:
            self.app_ref.status_bar.set_rate(f"{rate:,.0f} t/s")

    def _on_mgr_started(self, path=None):
        pass

    def _on_mgr_stopped(self, path=None, transitions=0):
        self.after(0, self._finalize)
        self.after(0, lambda: self._log(f"Capture stopped. Saved {transitions:,} transitions → {path}"))
        self.after(0, lambda: self._maybe_open(path))

    def _maybe_open(self, path):
        if path and self.app_ref:
            self.app_ref.open_capture_file(path)

    def _finalize(self):
        self.capturing = False
        self.start_btn.configure(state=tk.NORMAL)
        self.stop_btn.configure(state=tk.DISABLED)
        self.state_lbl.configure(text="Idle", foreground="#9E9E9E")
        self.progress.stop()

    def _on_dev_status(self, status=None):
        # could update fill etc.
        pass

    def _log(self, msg):
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] {msg}\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)
