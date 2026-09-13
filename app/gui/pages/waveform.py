import tkinter as tk
import tkinter.ttk as ttk
from pathlib import Path
from app.core.events import bus

class WaveformPage(ttk.Frame):
    def __init__(self, parent, app_ref=None):
        super().__init__(parent)
        self.app_ref = app_ref
        self.current_path = None
        self.data = []  # list of (cycles, sample)
        self.f_cpu = 600_000_000
        self.channels = [{"id":i,"label":f"CH{i}","enabled":True,"color":f"#%06x"%(0x00BFFF + i*0x33333)} for i in range(16)]
        self._build()
        bus.subscribe("capture_manager_stopped", self._on_new_capture)

    def _build(self):
        top = ttk.Frame(self)
        top.pack(fill=tk.X, padx=8, pady=4)
        ttk.Label(top, text="Waveform Viewer", font=("Segoe UI", 11, "bold")).pack(side=tk.LEFT)
        self.info_var = tk.StringVar(value="No capture loaded")
        ttk.Label(top, textvariable=self.info_var, foreground="#9E9E9E", font=("Consolas", 8)).pack(side=tk.LEFT, padx=12)
        ctrl = ttk.Frame(top)
        ctrl.pack(side=tk.RIGHT)
        ttk.Button(ctrl, text="Open…", command=self._open).pack(side=tk.LEFT, padx=2)
        ttk.Button(ctrl, text="Fit", command=self._fit).pack(side=tk.LEFT, padx=2)
        ttk.Button(ctrl, text="Zoom+", command=lambda: self._zoom(0.7)).pack(side=tk.LEFT, padx=2)
        ttk.Button(ctrl, text="Zoom−", command=lambda: self._zoom(1.4)).pack(side=tk.LEFT, padx=2)
        ttk.Button(ctrl, text="Clear Cursors", command=self._clear_cursors).pack(side=tk.LEFT, padx=4)
        ttk.Button(ctrl, text="Export CSV", command=self._export_csv).pack(side=tk.LEFT, padx=2)
        ttk.Button(ctrl, text="Export JSON", command=self._export_json).pack(side=tk.LEFT, padx=2)

        # paned: waveform + channel toggles
        pan = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        pan.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        left = ttk.Frame(pan)
        pan.add(left, weight=1)
        from app.gui.widgets.waveform_canvas import WaveformCanvas
        self.canvas = WaveformCanvas(left)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<Configure>", lambda e: self.canvas.redraw())

        right = ttk.Frame(pan, width=200)
        pan.add(right, weight=0)
        ttk.Label(right, text="Channels", font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=6, pady=4)
        self.ch_vars = []
        for i in range(16):
            var = tk.BooleanVar(value=True)
            cb = ttk.Checkbutton(right, text=f"CH{i}", variable=var, command=self._toggle_channels)
            cb.pack(anchor="w", padx=6)
            self.ch_vars.append(var)
        ttk.Separator(right, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=6, pady=6)
        ttk.Label(right, text="Instructions:", foreground="#9E9E9E", font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=6)
        ttk.Label(right, text="• Wheel: zoom\n• Drag: pan\n• Click ruler: cursors\n• Ctrl+click: second cursor\n• Delta shows Δt & freq", foreground="#9E9E9E", font=("Segoe UI", 7), justify=tk.LEFT).pack(anchor="w", padx=6, pady=2)
        # details
        self.detail = tk.Text(right, height=10, width=28, bg="#252526", fg="#D4D4D4", relief=tk.FLAT, font=("Consolas", 7))
        self.detail.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        self.detail.configure(state=tk.DISABLED)

    def load_capture(self, path: str | Path):
        from app.capture.reader import CaptureReader
        p = Path(path)
        if not p.exists():
            self.info_var.set(f"Not found: {p}")
            return
        try:
            r = CaptureReader(p)
            # Build data list for canvas
            flat = r.get_all_transitions()
            self.data = [(c,s) for c,s,_d in flat]
            self.f_cpu = r.header.f_cpu if r.header else 600_000_000
            self.current_path = p
            # channels meta if present
            ch_meta = r.get_channels_meta()
            if ch_meta:
                self.channels = []
                for cm in ch_meta:
                    self.channels.append({"id": cm.get("id",0), "label": cm.get("label") or f"CH{cm.get('id')}", "enabled": cm.get("enabled",True), "color": cm.get("color","#00BFFF")})
                # sync checkboxes
                for i,var in enumerate(self.ch_vars):
                    found = next((c for c in self.channels if c["id"]==i), None)
                    if found is not None:
                        var.set(found.get("enabled",True))
            self.canvas.set_data(self.data, f_cpu=self.f_cpu, channels=self.channels)
            self.canvas.zoom_fit()
            self.info_var.set(f"{p.name}  —  {len(flat):,} transitions  •  {self.f_cpu/1e6:.0f} MHz  •  duration {(flat[-1][0]-flat[0][0])/self.f_cpu*1e3:.2f} ms" if flat else "empty capture")
            self._show_detail(r)
            if self.app_ref:
                self.app_ref.set_status(f"Loaded {p.name}")
        except Exception as e:
            self.info_var.set(f"Failed to load: {e}")
            import traceback
            traceback.print_exc()

    def _open(self):
        from tkinter import filedialog
        p = filedialog.askopenfilename(title="Open capture", filetypes=[("Sniffer capture","*.stcap"),("All","*.*")])
        if p:
            self.load_capture(p)

    def _fit(self):
        self.canvas.zoom_fit()

    def _zoom(self, factor):
        self.canvas.set_zoom(self.canvas.sec_per_px * factor)

    def _clear_cursors(self):
        self.canvas.cursors.clear()
        self.canvas.redraw()

    def _toggle_channels(self):
        for i,var in enumerate(self.ch_vars):
            for ch in self.channels:
                if ch["id"]==i:
                    ch["enabled"] = bool(var.get())
        self.canvas.set_data(self.data, f_cpu=self.f_cpu, channels=self.channels)

    def _export_csv(self):
        if not self.current_path or not self.data:
            return
        from tkinter import filedialog
        out = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV","*.csv")])
        if not out:
            return
        try:
            import csv
            with open(out, "w", newline="", encoding="utf-8") as fh:
                w = csv.writer(fh)
                w.writerow(["time_s","time_ns","sample_hex"] + [f"CH{i}" for i in range(16)])
                t0 = self.data[0][0]
                for cyc,samp in self.data:
                    t_s = (cyc - t0)/self.f_cpu
                    t_ns = int(t_s*1e9)
                    row = [f"{t_s:.9f}", t_ns, f"0x{samp:04X}"] + [ (samp>>i)&1 for i in range(16) ]
                    w.writerow(row)
            if self.app_ref: self.app_ref.set_status(f"Exported CSV → {out}")
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror("Export failed", str(e))

    def _export_json(self):
        if not self.current_path or not self.data:
            return
        from tkinter import filedialog
        import json
        out = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON","*.json")])
        if not out: return
        try:
            t0 = self.data[0][0]
            arr = [{"t_ns": int((c-t0)/self.f_cpu*1e9), "sample": s, "hex": f"{s:04X}"} for c,s in self.data]
            with open(out,"w",encoding="utf-8") as fh:
                json.dump({"f_cpu":self.f_cpu, "transitions":arr}, fh, indent=2)
            if self.app_ref: self.app_ref.set_status(f"Exported JSON → {out}")
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror("Export failed", str(e))

    def _show_detail(self, reader):
        self.detail.configure(state=tk.NORMAL)
        self.detail.delete("1.0", tk.END)
        hdr = reader.header
        if hdr:
            self.detail.insert(tk.END, f"File: {self.current_path.name}\n")
            self.detail.insert(tk.END, f"Version: {hdr.ver_major}.{hdr.ver_minor}\n")
            self.detail.insert(tk.END, f"Created: {hdr.created_ms}\n")
            self.detail.insert(tk.END, f"F_CPU: {hdr.f_cpu}\n")
            self.detail.insert(tk.END, f"Mode: {hdr.capture_mode}\n")
            self.detail.insert(tk.END, f"Total: {hdr.total_transitions} trans\n")
            self.detail.insert(tk.END, f"Meta: {reader.header.meta}\n")
        self.detail.configure(state=tk.DISABLED)

    def _on_new_capture(self, path=None, transitions=0):
        self.after(0, lambda: self.load_capture(path) if path else None)
