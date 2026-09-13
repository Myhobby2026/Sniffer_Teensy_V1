import tkinter as tk
import tkinter.ttk as ttk
from pathlib import Path

class DashboardPage(ttk.Frame):
    def __init__(self, parent, app_ref=None):
        super().__init__(parent)
        self.app_ref = app_ref
        self._build()

    def _build(self):
        hdr = ttk.Frame(self)
        hdr.pack(fill=tk.X, padx=20, pady=16)
        ttk.Label(hdr, text="Universal Bus Sniffer & Logic Analyzer", font=("Segoe UI", 16, "bold")).pack(anchor="w")
        ttk.Label(hdr, text="Teensy 4.1 — 16-channel protected acquisition  •  Phase 1: Raw Transition Capture", font=("Segoe UI", 9), foreground="#9E9E9E").pack(anchor="w", pady=2)

        # stats grid
        grid = ttk.Frame(self)
        grid.pack(fill=tk.X, padx=20, pady=8)
        for i, (title, value) in enumerate([
            ("Channels", "16 digital"),
            ("Timestamp", "1.66 ns (600 MHz)"),
            ("Capture", "Transition-compressed"),
            ("Front-end", "Replaceable cartridge"),
        ]):
            card = ttk.Frame(grid, relief=tk.SOLID, borderwidth=1)
            card.grid(row=0, column=i, padx=6, sticky="nsew")
            ttk.Label(card, text=title, font=("Segoe UI", 8), foreground="#9E9E9E").pack(anchor="w", padx=10, pady=(8,0))
            ttk.Label(card, text=value, font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=10, pady=(2,10))
        grid.columnconfigure((0,1,2,3), weight=1)

        # quick actions
        acts = ttk.LabelFrame(self, text="Quick Actions", padding=10)
        acts.pack(fill=tk.X, padx=20, pady=10)
        ttk.Button(acts, text="Connect Device", command=lambda: self.app_ref and self.app_ref.show_page("Device")).pack(side=tk.LEFT, padx=4)
        ttk.Button(acts, text="Configure Channels", command=lambda: self.app_ref and self.app_ref.show_page("Channels")).pack(side=tk.LEFT, padx=4)
        ttk.Button(acts, text="Start Capture", command=lambda: self.app_ref and self.app_ref.show_page("Capture")).pack(side=tk.LEFT, padx=4)
        ttk.Button(acts, text="Open Capture…", command=self._open_capture).pack(side=tk.LEFT, padx=4)
        ttk.Button(acts, text="Simulate", command=self._simulate).pack(side=tk.LEFT, padx=4)

        # recent captures
        recent = ttk.LabelFrame(self, text="Recent Captures", padding=10)
        recent.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        self.recent_list = tk.Listbox(recent, height=6, bg="#252526", fg="#D4D4D4", selectbackground="#007ACC", relief=tk.FLAT)
        self.recent_list.pack(fill=tk.BOTH, expand=True)
        self.recent_list.bind("<Double-Button-1>", self._open_selected)
        self._refresh_recent()

        # phase roadmap
        roadmap = ttk.LabelFrame(self, text="Roadmap — Where You Are", padding=10)
        roadmap.pack(fill=tk.X, padx=20, pady=10)
        phases = [
            ("Phase 1", "Raw capture + USB + GUI", "● active"),
            ("Phase 2", "DMA + Trigger (pattern/pre-post)", "○ next"),
            ("Phases 3-4", "Live monitor + Waveform polishing", "○ queued"),
            ("Phases 5-8", "SPI / I2C / UART / 1-Wire", "○ planned"),
            ("Phases 9-12", "Reverse tools, Graph, Plugins, Analog", "○ planned"),
        ]
        for name, desc, mark in phases:
            row = ttk.Frame(roadmap)
            row.pack(fill=tk.X, pady=1)
            ttk.Label(row, text=name, width=12, font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT)
            ttk.Label(row, text=desc, font=("Segoe UI", 9)).pack(side=tk.LEFT)
            ttk.Label(row, text=mark, foreground="#89D185").pack(side=tk.RIGHT)

    def _refresh_recent(self):
        self.recent_list.delete(0, tk.END)
        try:
            from app.core.config import AppConfig
            cfg = AppConfig.load()
            for p in cfg.recent_files:
                self.recent_list.insert(tk.END, p)
            if not cfg.recent_files:
                self.recent_list.insert(tk.END, "(no recent captures)")
        except Exception:
            pass

    def _open_capture(self):
        from tkinter import filedialog
        p = filedialog.askopenfilename(title="Open capture", filetypes=[("Sniffer capture","*.stcap"),("All","*.*")])
        if p and self.app_ref:
            self.app_ref.open_capture_file(p)

    def _open_selected(self, _evt=None):
        sel = self.recent_list.curselection()
        if not sel: return
        val = self.recent_list.get(sel[0])
        if val.startswith("("): return
        if self.app_ref:
            self.app_ref.open_capture_file(val)

    def _simulate(self):
        if self.app_ref:
            self.app_ref.start_simulation()

    def refresh(self):
        self._refresh_recent()
