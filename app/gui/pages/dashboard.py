import tkinter as tk
import tkinter.ttk as ttk
from pathlib import Path

def _fam(root, pref="Segoe UI Variable"):
    try:
        import tkinter.font as tkfont
        fams = set(tkfont.families(root))
        for n in (pref, "Segoe UI", "Inter", "Helvetica"):
            if n in fams:
                return n
    except Exception:
        pass
    return "Segoe UI"

class DashboardPage(tk.Frame):
    def __init__(self, parent, app_ref=None):
        super().__init__(parent, bg="#0E0E10")
        self.app_ref = app_ref
        self._build()

    def _build(self):
        fam = _fam(self)
        # Scrollable container for modern feel
        canvas = tk.Canvas(self, bg="#0E0E10", highlightthickness=0, bd=0)
        vsb = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        inner = tk.Frame(canvas, bg="#0E0E10")
        canvas.create_window((0, 0), window=inner, anchor="nw")
        def _on_cfg(e):
            canvas.configure(scrollregion=canvas.bbox("all"))
        inner.bind("<Configure>", _on_cfg)

        # — Hero —
        hero = tk.Frame(inner, bg="#0E0E10")
        hero.pack(fill=tk.X, padx=28, pady=(22, 10))
        # eyebrow
        tk.Label(hero, text="UNIVERSAL  •  MODULAR  •  FUTURE-PROOF", bg="#0E0E10", fg="#6B7280",
                 font=(fam, 8, "bold")).pack(anchor="w")
        tk.Label(hero, text="Universal Bus Sniffer\n& Logic Analyzer", bg="#0E0E10", fg="#ECECEC",
                 font=(fam, 22, "bold"), justify=tk.LEFT).pack(anchor="w", pady=(6, 0))
        tk.Label(hero, text="Teensy 4.1  •  16-channel protected acquisition  •  1.66 ns timestamp  •  Phase 1: Raw Transition Capture",
                 bg="#0E0E10", fg="#9AA0A6", font=(fam, 10)).pack(anchor="w", pady=(6, 0))
        # accent line
        line = tk.Frame(hero, bg="#5B7FFF", height=3, width=64)
        line.pack(anchor="w", pady=(12, 0))

        # — Stats cards (4) —
        grid = tk.Frame(inner, bg="#0E0E10")
        grid.pack(fill=tk.X, padx=20, pady=14)
        grid.columnconfigure((0, 1, 2, 3), weight=1, uniform="stat")
        stats = [
            ("16", "Digital channels", "#5B7FFF", "▦"),
            ("1.66 ns", "Timestamp (600 MHz)", "#10B981", "◈"),
            ("2 M", "Transitions/s (Phase 1)", "#F59E0B", "〰"),
            ("3.3 V", "Protected front-end", "#EF4444", "⬢"),
        ]
        for i, (val, title, accent, icon) in enumerate(stats):
            card = tk.Frame(grid, bg="#1C1C1F", highlightthickness=1, highlightbackground="#2A2A2E", bd=0)
            card.grid(row=0, column=i, padx=8, sticky="nsew", pady=4)
            # top accent
            tk.Frame(card, bg=accent, height=2).pack(fill=tk.X)
            inner_c = tk.Frame(card, bg="#1C1C1F")
            inner_c.pack(fill=tk.BOTH, expand=True, padx=14, pady=12)
            top = tk.Frame(inner_c, bg="#1C1C1F")
            top.pack(fill=tk.X)
            # icon circle
            ic = tk.Canvas(top, width=28, height=28, bg="#1C1C1F", highlightthickness=0)
            ic.pack(side=tk.LEFT)
            ic.create_oval(0, 0, 28, 28, fill="#232326", outline="#2A2A2E")
            ic.create_text(14, 14, text=icon, fill=accent, font=(fam, 11, "bold"))
            tk.Label(top, text=title, bg="#1C1C1F", fg="#9AA0A6", font=(fam, 8, "bold")).pack(side=tk.LEFT, padx=(8, 0))
            tk.Label(inner_c, text=val, bg="#1C1C1F", fg="#ECECEC", font=(fam, 18, "bold")).pack(anchor="w", pady=(10, 0))
            tk.Label(inner_c, text=title, bg="#1C1C1F", fg="#6B7280", font=(fam, 9)).pack(anchor="w")

        # — Quick actions (modern pill buttons) —
        acts_wrap = tk.Frame(inner, bg="#1C1C1F", highlightthickness=1, highlightbackground="#2A2A2E")
        acts_wrap.pack(fill=tk.X, padx=28, pady=10)
        tk.Frame(acts_wrap, bg="#5B7FFF", height=2).pack(fill=tk.X)
        acts = tk.Frame(acts_wrap, bg="#1C1C1F")
        acts.pack(fill=tk.X, padx=16, pady=14)
        tk.Label(acts, text="Quick Actions", bg="#1C1C1F", fg="#ECECEC", font=(fam, 10, "bold")).pack(anchor="w")
        tk.Label(acts, text="Jump to the most common tasks", bg="#1C1C1F", fg="#9AA0A6", font=(fam, 9)).pack(anchor="w", pady=(2, 10))

        btns = tk.Frame(acts, bg="#1C1C1F")
        btns.pack(fill=tk.X)
        def _mk_btn(txt, style, cmd):
            # style: primary / ghost
            if style == "primary":
                b = tk.Button(btns, text=txt, bg="#5B7FFF", fg="white", activebackground="#6C8CFF", activeforeground="white",
                              relief="flat", bd=0, padx=14, pady=8, font=(fam, 10, "bold"), command=cmd, cursor="hand2")
            else:
                b = tk.Button(btns, text=txt, bg="#232326", fg="#ECECEC", activebackground="#2C2C30", activeforeground="white",
                              relief="flat", bd=0, padx=14, pady=8, font=(fam, 9), highlightthickness=1, highlightbackground="#2A2A2E",
                              command=cmd, cursor="hand2")
            b.pack(side=tk.LEFT, padx=6)
            return b
        _mk_btn("⟡  Connect", "primary", lambda: self.app_ref and self.app_ref.show_page("Device"))
        _mk_btn("▦  Channels", "ghost", lambda: self.app_ref and self.app_ref.show_page("Channels"))
        _mk_btn("●  Capture", "ghost", lambda: self.app_ref and self.app_ref.show_page("Capture"))
        _mk_btn("Open…", "ghost", self._open_capture)
        _mk_btn("Simulate", "ghost", self._simulate)

        # — Two-column: Recent + Roadmap —
        cols = tk.Frame(inner, bg="#0E0E10")
        cols.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        cols.columnconfigure(0, weight=3)
        cols.columnconfigure(1, weight=2)

        # Recent
        recent_card = tk.Frame(cols, bg="#1C1C1F", highlightthickness=1, highlightbackground="#2A2A2E")
        recent_card.grid(row=0, column=0, padx=8, sticky="nsew")
        tk.Frame(recent_card, bg="#5B7FFF", height=2).pack(fill=tk.X)
        rh = tk.Frame(recent_card, bg="#1C1C1F")
        rh.pack(fill=tk.X, padx=16, pady=(12, 8))
        tk.Label(rh, text="Recent Captures", bg="#1C1C1F", fg="#ECECEC", font=(fam, 10, "bold")).pack(side=tk.LEFT)
        tk.Label(rh, text="Double-click to open", bg="#1C1C1F", fg="#6B7280", font=(fam, 8)).pack(side=tk.RIGHT)
        # list with modern row style
        list_wrap = tk.Frame(recent_card, bg="#1C1C1F")
        list_wrap.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))
        self.recent_list = tk.Listbox(list_wrap, height=7, bg="#232326", fg="#ECECEC",
                                      selectbackground="#5B7FFF", selectforeground="white",
                                      relief="flat", bd=0, highlightthickness=1, highlightbackground="#2A2A2E",
                                      font=(fam, 9), activestyle="none", selectmode=tk.SINGLE)
        self.recent_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb = ttk.Scrollbar(list_wrap, orient="vertical", command=self.recent_list.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.recent_list.configure(yscrollcommand=sb.set)
        self.recent_list.bind("<Double-Button-1>", self._open_selected)
        self._refresh_recent()

        # Roadmap
        road = tk.Frame(cols, bg="#1C1C1F", highlightthickness=1, highlightbackground="#2A2A2E")
        road.grid(row=0, column=1, padx=8, sticky="nsew")
        tk.Frame(road, bg="#10B981", height=2).pack(fill=tk.X)
        rh2 = tk.Frame(road, bg="#1C1C1F")
        rh2.pack(fill=tk.X, padx=16, pady=(12, 8))
        tk.Label(rh2, text="Roadmap — Where You Are", bg="#1C1C1F", fg="#ECECEC", font=(fam, 10, "bold")).pack(anchor="w")
        tk.Label(rh2, text="Incremental, never breaks previous APIs", bg="#1C1C1F", fg="#6B7280", font=(fam, 8)).pack(anchor="w")
        phases = [
            ("Phase 1", "Raw capture + USB + GUI", "●", "#10B981", "active"),
            ("Phase 2", "DMA + Trigger (pattern/pre-post)", "○", "#6B7280", "next"),
            ("Phases 3-4", "Live monitor + Waveform pro", "○", "#6B7280", "queued"),
            ("Phases 5-8", "SPI / I2C / UART / 1-Wire", "○", "#6B7280", "planned"),
            ("Phases 9-12", "Reverse, Graph, Plugins, Analog", "○", "#6B7280", "planned"),
        ]
        for name, desc, mark, col, _ in phases:
            row = tk.Frame(road, bg="#1C1C1F")
            row.pack(fill=tk.X, padx=16, pady=5)
            # dot
            c = tk.Canvas(row, width=14, height=14, bg="#1C1C1F", highlightthickness=0)
            c.pack(side=tk.LEFT)
            c.create_oval(2, 2, 12, 12, outline=col, width=1.5, fill=col if mark == "●" else "")
            tk.Label(row, text=name, bg="#1C1C1F", fg="#ECECEC", font=(fam, 9, "bold"), width=12, anchor="w").pack(side=tk.LEFT, padx=(8, 0))
            tk.Label(row, text=desc, bg="#1C1C1F", fg="#9AA0A6", font=(fam, 9)).pack(side=tk.LEFT, fill=tk.X, expand=True)
            st = "ACTIVE" if col == "#10B981" else "PLANNED"
            tk.Label(row, text=st, bg="#232326" if st != "ACTIVE" else "#10B981", fg="#6B7280" if st != "ACTIVE" else "white",
                     font=(fam, 7, "bold"), padx=6, pady=2).pack(side=tk.RIGHT)

        # footer hint
        foot = tk.Frame(inner, bg="#0E0E10")
        foot.pack(fill=tk.X, padx=28, pady=(6, 18))
        tk.Label(foot, text="Tip: Press Ctrl+O to open a capture anywhere  •  Theme persists in ~/.sniffer/config.json",
                 bg="#0E0E10", fg="#6B7280", font=(fam, 8)).pack(anchor="w")

    def _refresh_recent(self):
        self.recent_list.delete(0, tk.END)
        try:
            from app.core.config import AppConfig
            cfg = AppConfig.load()
            for p in cfg.recent_files:
                self.recent_list.insert(tk.END, f"  {p}")
            if not cfg.recent_files:
                self.recent_list.insert(tk.END, "  (no recent captures — open or start one)")
                self.recent_list.itemconfig(0, fg="#6B7280")
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
        val = self.recent_list.get(sel[0]).strip()
        if val.startswith("("): return
        if self.app_ref:
            self.app_ref.open_capture_file(val)

    def _simulate(self):
        if self.app_ref:
            self.app_ref.start_simulation()

    def refresh(self):
        self._refresh_recent()
