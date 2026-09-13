import tkinter as tk
import tkinter.ttk as ttk
from pathlib import Path
from app.core.config import AppConfig
from app.core.logger import get_logger
from app.gui.theme import apply_theme, THEMES
from app.gui.widgets.status_bar import StatusBar
from app.gui.pages.dashboard import DashboardPage
from app.gui.pages.device_manager import DeviceManagerPage
from app.gui.pages.channel_config import ChannelConfigPage
from app.gui.pages.capture_page import CapturePage
from app.gui.pages.waveform import WaveformPage
from app.gui.pages.placeholder import make_placeholder

log = get_logger("gui")

# Modern nav with icons (unicode — renders everywhere, no image deps)
PAGES = [
    ("Dashboard", "Overview and quick actions", "◉"),
    ("Device", "Connection and handshake", "⎔"),
    ("Channels", "16-channel setup", "▦"),
    ("Capture", "Start/stop and save", "●"),
    ("Waveform", "Zoom/pan/cursors", "〰"),
    ("Protocol", "Decoded data overview", "≡"),
    ("SPI", "SPI transaction decode", "⬢"),
    ("I2C", "I2C address/data decode", "⬣"),
    ("UART", "Async serial decode", "⇄"),
    ("1-Wire", "1-Wire timing/decode", "─"),
    ("Hex", "Hex & field analyzer", "⬡"),
    ("Packets", "Packet table", "☰"),
    ("Graph", "Graph / plot analyzer", "◭"),
    ("Trigger", "Trigger builder (Ph.2+)", "⌖"),
    ("Search", "Search & filter", "⌕"),
    ("Compare", "Compare captures", "⇔"),
    ("Sensor", "Sensor correlation", "◈"),
    ("Calibration", "Analog scaling", "◎"),
    ("Settings", "Preferences", "⚙"),
    ("Firmware", "Device & FW info", "⧉"),
    ("Plugins", "Plugin manager", "⬔"),
    ("Help", "Manual & wiring", "?"),
]

# Grouping for sidebar sections — modern collapsible feel
GROUPS = [
    ("OVERVIEW", ["Dashboard"]),
    ("ACQUISITION", ["Device", "Channels", "Capture", "Waveform"]),
    ("DECODERS", ["Protocol", "SPI", "I2C", "UART", "1-Wire"]),
    ("ANALYSIS", ["Hex", "Packets", "Graph", "Trigger", "Search", "Compare", "Sensor"]),
    ("SYSTEM", ["Calibration", "Settings", "Firmware", "Plugins", "Help"]),
]

PAGE_ICON = {name: icon for name, _, icon in PAGES}
PAGE_DESC = {name: desc for name, desc, _ in PAGES}


class MainWindow:
    def __init__(self, root: tk.Tk, simulate: str | None = None, replay: str | None = None):
        self.root = root
        self.config = AppConfig.load()
        self.theme_name = self.config.theme or "dark"
        self.pal = apply_theme(root, self.theme_name)
        self.channels = []
        self.root.title("Sniffer Teensy V1 — Universal Bus Sniffer & Logic Analyzer  (Phase 1)")
        try:
            self.root.geometry(self.config.window_geometry)
        except Exception:
            self.root.geometry("1360x840")
        self.root.minsize(1120, 700)

        self._build_menu()
        self._build_header()
        self._build_toolbar()
        self._build_body()
        self._build_statusbar()

        # initial page
        self.show_page("Dashboard")
        if simulate:
            self.start_simulation(simulate if simulate != "__sim__" else None)
        if replay:
            self.open_capture_file(replay)

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ---------- Menu (native) ----------
    def _build_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        m_file = tk.Menu(menubar, tearoff=0)
        m_file.add_command(label="Open Capture…", command=self._open_capture_dialog, accelerator="Ctrl+O")
        m_file.add_command(label="Save Capture As…", command=lambda: self.show_page("Capture"))
        m_file.add_separator()
        m_file.add_command(label="Simulate (no hardware)", command=self.start_simulation)
        m_file.add_separator()
        m_file.add_command(label="Exit", command=self._on_close)
        menubar.add_cascade(label="File", menu=m_file)

        m_view = tk.Menu(menubar, tearoff=0)
        m_view.add_command(label="Dark", command=lambda: self.set_theme("dark"))
        m_view.add_command(label="Light", command=lambda: self.set_theme("light"))
        m_view.add_command(label="High Contrast", command=lambda: self.set_theme("high_contrast"))
        menubar.add_cascade(label="View", menu=m_view)

        m_device = tk.Menu(menubar, tearoff=0)
        m_device.add_command(label="Device Manager", command=lambda: self.show_page("Device"))
        m_device.add_command(label="Channel Config", command=lambda: self.show_page("Channels"))
        m_device.add_command(label="Capture", command=lambda: self.show_page("Capture"))
        menubar.add_cascade(label="Device", menu=m_device)

        m_help = tk.Menu(menubar, tearoff=0)
        m_help.add_command(label="Wiring & Safety", command=self._show_safety)
        m_help.add_command(label="About", command=self._show_about)
        menubar.add_cascade(label="Help", menu=m_help)

        self.root.bind("<Control-o>", lambda e: self._open_capture_dialog())

    # ---------- Modern header (app bar) ----------
    def _build_header(self):
        # Header is a thin branded bar — left logo/title, right actions+theme
        hdr = tk.Frame(self.root, bg=self.pal["bg2"], highlightthickness=0)
        hdr.pack(fill=tk.X, side=tk.TOP)
        # hairline bottom
        line = tk.Frame(hdr, bg=self.pal["border"], height=1)
        line.pack(fill=tk.X, side=tk.BOTTOM)

        inner = tk.Frame(hdr, bg=self.pal["bg2"])
        inner.pack(fill=tk.X, padx=16, pady=8)

        # Left: dot + title
        left = tk.Frame(inner, bg=self.pal["bg2"])
        left.pack(side=tk.LEFT)
        # accent dot
        dot = tk.Canvas(left, width=10, height=10, bg=self.pal["bg2"], highlightthickness=0)
        dot.pack(side=tk.LEFT, padx=(0, 10))
        dot.create_oval(0, 0, 10, 10, fill=self.pal["accent"], outline="")
        tk.Label(left, text="SNIFFER", bg=self.pal["bg2"], fg=self.pal["fg"],
                 font=(self._font_family(), 10, "bold")).pack(side=tk.LEFT)
        tk.Label(left, text="  Teensy 4.1  •  16-ch  •  Phase 1", bg=self.pal["bg2"], fg=self.pal["fg2"],
                 font=(self._font_family(), 9)).pack(side=tk.LEFT, padx=(8, 0))

        # Right: version + theme + quick capture
        right = tk.Frame(inner, bg=self.pal["bg2"])
        right.pack(side=tk.RIGHT)

        tk.Label(right, text="v1.0.0", bg=self.pal["bg2"], fg=self.pal["fg3"],
                 font=(self._font_family(), 8)).pack(side=tk.LEFT, padx=(0, 12))

        # quick connect indicator (will be updated)
        self._header_status = tk.Label(right, text="●  Idle", bg=self.pal["bg2"], fg=self.pal["fg2"],
                                       font=(self._font_family(), 9))
        self._header_status.pack(side=tk.LEFT, padx=(0, 12))

        # theme segmented control — modern pill
        seg = tk.Frame(right, bg=self.pal["bg3"], highlightthickness=1, highlightbackground=self.pal["border"])
        seg.pack(side=tk.LEFT, padx=(0, 8))
        # use uniform size pill
        for name, label in [("dark", "Dark"), ("light", "Light"), ("high_contrast", "HC")]:
            is_active = (name == self.theme_name)
            b = tk.Button(seg, text=label, font=(self._font_family(), 8, "bold" if is_active else "normal"),
                          bg=self.pal["accent"] if is_active else self.pal["bg3"],
                          fg="white" if is_active else self.pal["fg2"],
                          activebackground=self.pal["accent_hover"] if is_active else self.pal["bg4"],
                          activeforeground="white" if is_active else self.pal["fg"],
                          relief="flat", bd=0, padx=10, pady=4,
                          command=lambda n=name: self.set_theme(n))
            b.pack(side=tk.LEFT, padx=1, pady=1)
            # store for later theme refresh
            if not hasattr(self, "_theme_btns"):
                self._theme_btns = []
            self._theme_btns.append((name, b))

    def _font_family(self) -> str:
        # resolve same as theme
        try:
            import tkinter.font as tkfont
            for n in ("Segoe UI Variable", "Segoe UI", "Inter", "Helvetica"):
                if n in tkfont.families(self.root):
                    return n
        except Exception:
            pass
        return "Segoe UI"

    # ---------- Toolbar (context actions) ----------
    def _build_toolbar(self):
        # modern toolbar: card-like, with primary action on right
        bar = tk.Frame(self.root, bg=self.pal["bg"], padx=12, pady=8)
        bar.pack(fill=tk.X)

        # left: breadcrumb / page title
        self._toolbar_title = tk.Label(bar, text="Dashboard", bg=self.pal["bg"], fg=self.pal["fg"],
                                       font=(self._font_family(), 12, "bold"))
        self._toolbar_title.pack(side=tk.LEFT)

        self._toolbar_sub = tk.Label(bar, text="Overview and quick actions", bg=self.pal["bg"], fg=self.pal["fg2"],
                                     font=(self._font_family(), 9))
        self._toolbar_sub.pack(side=tk.LEFT, padx=(10, 0))

        # right: primary actions
        right = tk.Frame(bar, bg=self.pal["bg"])
        right.pack(side=tk.RIGHT)

        # Use ttk buttons with theme styles — modern ghost/accent
        self._tb_capture = ttk.Button(right, text="●  Start Capture", style="Accent.TButton",
                                      command=lambda: self.show_page("Capture"))
        self._tb_capture.pack(side=tk.LEFT, padx=4)

        ttk.Button(right, text="Open", style="Ghost.TButton",
                   command=self._open_capture_dialog).pack(side=tk.LEFT, padx=4)
        ttk.Button(right, text="Simulate", style="Ghost.TButton",
                   command=self.start_simulation).pack(side=tk.LEFT, padx=4)

    # ---------- Body: sidebar + content ----------
    def _build_body(self):
        self.body = tk.Frame(self.root, bg=self.pal["bg"])
        self.body.pack(fill=tk.BOTH, expand=True)

        self.paned = ttk.PanedWindow(self.body, orient=tk.HORIZONTAL, style="TPanedwindow")
        self.paned.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        # Sidebar — modern card with scroll
        self._sidebar = tk.Frame(self.paned, bg=self.pal["sidebar_bg"], width=240,
                                 highlightthickness=1, highlightbackground=self.pal["border"])
        self.paned.add(self._sidebar, weight=0)

        # sidebar header
        hdr = tk.Frame(self._sidebar, bg=self.pal["sidebar_bg"])
        hdr.pack(fill=tk.X, padx=12, pady=(14, 8))
        tk.Label(hdr, text="NAVIGATOR", bg=self.pal["sidebar_bg"], fg=self.pal["fg2"],
                 font=(self._font_family(), 8, "bold")).pack(anchor="w")
        tk.Label(hdr, text="16-ch • USB HS • .stcap", bg=self.pal["sidebar_bg"], fg=self.pal["fg3"],
                 font=(self._font_family(), 8)).pack(anchor="w", pady=(2, 0))

        # scrollable area for groups
        self._sidebar_scroll = tk.Canvas(self._sidebar, bg=self.pal["sidebar_bg"],
                                         highlightthickness=0, bd=0)
        self._sidebar_scroll.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 0))

        vsb = ttk.Scrollbar(self._sidebar, orient="vertical", command=self._sidebar_scroll.yview)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self._sidebar_scroll.configure(yscrollcommand=vsb.set)

        self._sidebar_inner = tk.Frame(self._sidebar_scroll, bg=self.pal["sidebar_bg"])
        self._sidebar_scroll.create_window((0, 0), window=self._sidebar_inner, anchor="nw")

        self._sidebar_inner.bind("<Configure>", lambda e: self._sidebar_scroll.configure(scrollregion=self._sidebar_scroll.bbox("all")))
        # wheel scroll for sidebar
        def _on_wheel(e):
            self._sidebar_scroll.yview_scroll(-1 * int(e.delta / 120) if hasattr(e, "delta") else -1, "units")
        self._sidebar_inner.bind("<Enter>", lambda e: self._sidebar_scroll.bind_all("<MouseWheel>", _on_wheel))
        self._sidebar_inner.bind("<Leave>", lambda e: self._sidebar_scroll.unbind_all("<MouseWheel>"))

        # Build groups
        self._nav_buttons = {}  # name -> (frame, button, indicator)
        for group_name, names in GROUPS:
            # section label
            sec = tk.Frame(self._sidebar_inner, bg=self.pal["sidebar_bg"])
            sec.pack(fill=tk.X, padx=12, pady=(14, 6))
            tk.Label(sec, text=group_name, bg=self.pal["sidebar_bg"], fg=self.pal["fg3"],
                     font=(self._font_family(), 7, "bold")).pack(anchor="w")

            for name in names:
                icon = PAGE_ICON.get(name, "•")
                # row frame with left indicator
                row = tk.Frame(self._sidebar_inner, bg=self.pal["sidebar_bg"])
                row.pack(fill=tk.X, padx=6, pady=1)

                indicator = tk.Frame(row, bg=self.pal["sidebar_bg"], width=3, height=22)
                indicator.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 6))

                # button — custom tk.Button for full control
                btn = tk.Button(row, text=f"  {icon}   {name}", anchor="w",
                                bg=self.pal["sidebar_bg"], fg=self.pal["fg2"],
                                activebackground=self.pal["sidebar_hover"],
                                activeforeground=self.pal["fg"],
                                relief="flat", bd=0, padx=8, pady=7,
                                font=(self._font_family(), 10),
                                command=lambda n=name: self.show_page(n))
                btn.pack(fill=tk.X, expand=True)
                # hover
                def make_hover(b=btn, ind=indicator):
                    def enter(_e):
                        if b.cget("bg") != self.pal["bg3"]:
                            b.configure(bg=self.pal["sidebar_hover"])
                    def leave(_e):
                        if b.cget("bg") != self.pal["bg3"]:
                            b.configure(bg=self.pal["sidebar_bg"])
                    return enter, leave
                e, l = make_hover()
                btn.bind("<Enter>", e)
                btn.bind("<Leave>", l)
                indicator.bind("<Enter>", e)
                indicator.bind("<Leave>", l)

                self._nav_buttons[name] = (row, btn, indicator)

        # footer inside sidebar
        foot = tk.Frame(self._sidebar_inner, bg=self.pal["sidebar_bg"])
        foot.pack(fill=tk.X, padx=12, pady=(16, 12), side=tk.BOTTOM)
        tk.Label(foot, text="Phase 1 • Raw capture", bg=self.pal["sidebar_bg"], fg=self.pal["fg3"],
                 font=(self._font_family(), 8)).pack(anchor="w")
        tk.Label(foot, text="docs/07 safety before wiring", bg=self.pal["sidebar_bg"], fg=self.pal["warning"],
                 font=(self._font_family(), 7, "bold")).pack(anchor="w", pady=(4, 0))

        # Content area — modern card
        content_wrap = tk.Frame(self.paned, bg=self.pal["bg"], padx=0, pady=0)
        self.paned.add(content_wrap, weight=1)

        # subtle card container with border
        self.content_card = tk.Frame(content_wrap, bg=self.pal["card_bg"],
                                     highlightthickness=1, highlightbackground=self.pal["card_border"],
                                     bd=0)
        self.content_card.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)

        # inner content where pages live
        self.content = tk.Frame(self.content_card, bg=self.pal["card_bg"])
        self.content.pack(fill=tk.BOTH, expand=True)

        self.pages = {}
        self._create_pages()

        # ensure sidebar width stable after layout
        self._sidebar.update_idletasks()
        self.paned.sashpos(0, 250)

    def _create_pages(self):
        # real pages
        self.pages["Dashboard"] = DashboardPage(self.content, app_ref=self)
        self.pages["Device"] = DeviceManagerPage(self.content, app_ref=self)
        self.pages["Channels"] = ChannelConfigPage(self.content, app_ref=self)
        self.pages["Capture"] = CapturePage(self.content, app_ref=self)
        self.pages["Waveform"] = WaveformPage(self.content, app_ref=self)
        # placeholders for rest
        for name, desc in PAGES:
            if name not in self.pages:
                # need icon too
                self.pages[name] = make_placeholder(self.content, name, desc, app_ref=self)
        # grid all but show one
        for p in self.pages.values():
            p.place(relx=0, rely=0, relwidth=1, relheight=1)
            p.lower()

    def show_page(self, name: str):
        if name in self.pages:
            self.pages[name].lift()
            # toolbar breadcrumb
            self._toolbar_title.configure(text=name)
            self._toolbar_sub.configure(text=PAGE_DESC.get(name, ""))
            # update sidebar active state
            for n, (row, btn, ind) in self._nav_buttons.items():
                if n == name:
                    btn.configure(bg=self.pal["bg3"], fg=self.pal["fg"],
                                  font=(self._font_family(), 10, "bold"))
                    ind.configure(bg=self.pal["sidebar_active"])
                    row.configure(bg=self.pal["bg3"])
                else:
                    btn.configure(bg=self.pal["sidebar_bg"], fg=self.pal["fg2"],
                                  font=(self._font_family(), 10))
                    ind.configure(bg=self.pal["sidebar_bg"])
                    row.configure(bg=self.pal["sidebar_bg"])
            # adjust canvas bg for waveform readability
            if hasattr(self.pages[name], "refresh"):
                try:
                    self.pages[name].refresh()
                except Exception:
                    pass

    def _build_statusbar(self):
        self.status_bar = StatusBar(self.root)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        self.status_bar.set_message("Ready — Phase 1: connect Teensy or use Simulate")

    def set_status(self, msg: str):
        self.status_bar.set_message(msg)
        # also header dot
        try:
            if "Capturing" in msg or "capture" in msg.lower():
                self._header_status.configure(text="●  Capturing", fg=self.pal["success"])
            elif "Connected" in msg:
                self._header_status.configure(text="●  Connected", fg=self.pal["success"])
            elif "Idle" in msg:
                self._header_status.configure(text="●  Idle", fg=self.pal["fg2"])
            else:
                self._header_status.configure(text=f"●  {msg[:28]}", fg=self.pal["fg2"])
        except Exception:
            pass
        log.info(msg)

    def set_theme(self, name: str):
        self.theme_name = name
        self.pal = apply_theme(self.root, name)
        self.config.theme = name
        self.config.save()
        # Re-apply manual tk colors that ttk doesn't cover
        try:
            # rebuild header/sidebar colors by re-creating? simpler: update known frames
            for frm in [self._sidebar, self._sidebar_inner, self._sidebar_scroll]:
                frm.configure(bg=self.pal["sidebar_bg"])
            for n, (row, btn, ind) in self._nav_buttons.items():
                row.configure(bg=self.pal["sidebar_bg"])
                ind.configure(bg=self.pal["sidebar_bg"])
                btn.configure(bg=self.pal["sidebar_bg"])
            self.show_page(self._toolbar_title.cget("text") or "Dashboard")
        except Exception:
            pass
        self.status_bar.set_message(f"Theme: {name}")
        # refresh theme buttons pill
        try:
            for n, b in getattr(self, "_theme_btns", []):
                is_active = (n == name)
                b.configure(bg=self.pal["accent"] if is_active else self.pal["bg3"],
                            fg="white" if is_active else self.pal["fg2"],
                            font=(self._font_family(), 8, "bold" if is_active else "normal"))
        except Exception:
            pass

    def _open_capture_dialog(self):
        from tkinter import filedialog
        p = filedialog.askopenfilename(title="Open capture", filetypes=[("Sniffer capture","*.stcap"),("All","*.*")])
        if p:
            self.open_capture_file(p)

    def open_capture_file(self, path: str):
        self.show_page("Waveform")
        # defer to allow page to be visible
        self.root.after(80, lambda: self.pages["Waveform"].load_capture(path))
        try:
            self.config.add_recent(path)
        except Exception:
            pass
        self.status_bar.set_message(f"Opened {Path(path).name}")

    def start_simulation(self, replay_path: str | None = None):
        from app.device.manager import device_manager
        if replay_path:
            ok = device_manager.connect(f"SIM:{replay_path}")
        else:
            ok = device_manager.connect_simulated()
        self.show_page("Device")
        self.status_bar.set_message("Simulated device started" + (f" replay {Path(replay_path).name}" if replay_path else ""))

    def _show_safety(self):
        from tkinter import messagebox
        messagebox.showinfo("Wiring & Safety",
            "Read docs/07-safety-and-wiring.md before connecting!\n\n"
            "• Teensy GPIOs are 0–3.3 V only, not 5 V tolerant.\n"
            "• Use the correct cartridge: 3V3 / 5V (TXS0108) / RS232 (MAX3232) / Analog.\n"
            "• Always connect GND first, measure voltage first.\n"
            "• Keep leads <20 cm for >2 MHz.\n"
            "• For differential (RS-485/CAN) use a transceiver module.\n"
            "• Never probe mains/high-voltage without isolation.")

    def _show_about(self):
        from tkinter import messagebox
        messagebox.showinfo("About",
            "Sniffer Teensy V1 — Universal Bus Sniffer & Logic Analyzer\n"
            "Phase 1: Raw Transition Capture\n\n"
            "Hardware: Teensy 4.1 (i.MX RT1062 @ 600 MHz)\n"
            "Host: Python 3 + Tkinter (modern theme)\n"
            "Capture format: .stcap (see docs/04)\n"
            "USB: Framed binary CDC-ACM (see docs/03)\n\n"
            "Docs: docs/ directory\n"
            "Repo: Myhobby2026/Sniffer_Teensy_V1\n"
            "Theme and recent files saved in ~/.sniffer/")

    def _on_close(self):
        try:
            self.config.window_geometry = self.root.geometry()
            self.config.save()
        except Exception:
            pass
        try:
            from app.device.manager import device_manager
            if device_manager.connected:
                device_manager.disconnect()
        except Exception:
            pass
        self.root.destroy()
