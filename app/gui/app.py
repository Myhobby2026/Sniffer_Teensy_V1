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

PAGES = [
    ("Dashboard", "Overview and quick actions"),
    ("Device", "Connection and handshake"),
    ("Channels", "16-channel setup"),
    ("Capture", "Start/stop and save"),
    ("Waveform", "Zoom/pan/cursors"),
    ("Protocol", "Decoded data overview"),
    ("SPI", "SPI transaction decode"),
    ("I2C", "I2C address/data decode"),
    ("UART", "Async serial decode"),
    ("1-Wire", "1-Wire timing/decode"),
    ("Hex", "Hex & field analyzer"),
    ("Packets", "Packet table"),
    ("Graph", "Graph / plot analyzer"),
    ("Trigger", "Trigger builder (Ph.2+)"),
    ("Search", "Search & filter"),
    ("Compare", "Compare captures"),
    ("Sensor", "Sensor correlation"),
    ("Calibration", "Analog scaling"),
    ("Settings", "Preferences"),
    ("Firmware", "Device & FW info"),
    ("Plugins", "Plugin manager"),
    ("Help", "Manual & wiring"),
]

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
            self.root.geometry("1280x800")
        self.root.minsize(1080, 680)

        self._build_menu()
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
        m_view.add_command(label="Dark Theme", command=lambda: self.set_theme("dark"))
        m_view.add_command(label="Light Theme", command=lambda: self.set_theme("light"))
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

    def _build_toolbar(self):
        bar = ttk.Frame(self.root, padding=(6,4))
        bar.pack(fill=tk.X)
        ttk.Button(bar, text="Dashboard", width=11, command=lambda: self.show_page("Dashboard")).pack(side=tk.LEFT, padx=2)
        ttk.Button(bar, text="Device", width=9, command=lambda: self.show_page("Device")).pack(side=tk.LEFT, padx=2)
        ttk.Button(bar, text="Channels", width=9, command=lambda: self.show_page("Channels")).pack(side=tk.LEFT, padx=2)
        ttk.Button(bar, text="Capture", width=9, command=lambda: self.show_page("Capture")).pack(side=tk.LEFT, padx=2)
        ttk.Button(bar, text="Waveform", width=10, command=lambda: self.show_page("Waveform")).pack(side=tk.LEFT, padx=2)
        ttk.Separator(bar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)
        self.theme_var = tk.StringVar(value=self.theme_name)
        ttk.Label(bar, text="Theme:").pack(side=tk.LEFT)
        cb = ttk.Combobox(bar, textvariable=self.theme_var, values=["dark","light","high_contrast"], width=13, state="readonly")
        cb.pack(side=tk.LEFT, padx=4)
        cb.bind("<<ComboboxSelected>>", lambda e: self.set_theme(self.theme_var.get()))

    def _build_body(self):
        self.body = ttk.Frame(self.root)
        self.body.pack(fill=tk.BOTH, expand=True)
        # left nav + notebook
        self.paned = ttk.PanedWindow(self.body, orient=tk.HORIZONTAL)
        self.paned.pack(fill=tk.BOTH, expand=True)

        # nav list
        nav_frame = ttk.Frame(self.paned, width=160)
        self.paned.add(nav_frame, weight=0)
        ttk.Label(nav_frame, text="NAVIGATOR", foreground="#9E9E9E", font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=8, pady=(8,4))
        self.nav_list = tk.Listbox(nav_frame, bg=self.pal["bg2"], fg=self.pal["fg"], selectbackground=self.pal["accent"], relief=tk.FLAT, font=("Segoe UI", 11), highlightthickness=0, activestyle="none")
        for name,_desc in PAGES:
            self.nav_list.insert(tk.END, name)
        self.nav_list.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        self.nav_list.bind("<<ListboxSelect>>", self._on_nav)
        self.nav_list.selection_set(0)

        # notebook/content
        self.content = ttk.Frame(self.paned)
        self.paned.add(self.content, weight=1)
        self.pages = {}
        self._create_pages()

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
                self.pages[name] = make_placeholder(self.content, name, desc, app_ref=self)
        # grid all but show one
        for p in self.pages.values():
            p.place(relx=0, rely=0, relwidth=1, relheight=1)
            p.lower()

    def show_page(self, name: str):
        if name in self.pages:
            self.pages[name].lift()
            # sync nav
            try:
                idx = [n for n,_ in PAGES].index(name)
                self.nav_list.selection_clear(0, tk.END)
                self.nav_list.selection_set(idx)
                self.nav_list.see(idx)
            except ValueError:
                pass
            if hasattr(self.pages[name], "refresh"):
                self.pages[name].refresh()

    def _on_nav(self, _evt=None):
        sel = self.nav_list.curselection()
        if sel:
            name = self.nav_list.get(sel[0])
            self.show_page(name)

    def _build_statusbar(self):
        self.status_bar = StatusBar(self.root)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        self.status_bar.set_message("Ready — Phase 1: connect Teensy or use Simulate")

    def set_status(self, msg: str):
        self.status_bar.set_message(msg)
        log.info(msg)

    def set_theme(self, name: str):
        self.theme_name = name
        self.pal = apply_theme(self.root, name)
        self.config.theme = name
        self.config.save()
        self.status_bar.set_message(f"Theme: {name}")

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
            "Host: Python 3 + Tkinter\n"
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
