import tkinter as tk
import tkinter.ttk as ttk
from app.device.manager import device_manager
from app.core.events import bus
from app.core.logger import get_logger

log = get_logger("gui.device")

class DeviceManagerPage(ttk.Frame):
    def __init__(self, parent, app_ref=None):
        super().__init__(parent)
        self.app_ref = app_ref
        self._build()
        bus.subscribe("device_connected", self._on_connected)
        bus.subscribe("device_disconnected", self._on_disconnected)
        bus.subscribe("device_status", self._on_status)
        bus.subscribe("device_error", self._on_error)
        self.after(600, self._refresh_ports)

    def _build(self):
        top = ttk.Frame(self)
        top.pack(fill=tk.X, padx=12, pady=8)
        ttk.Label(top, text="Device", font=("Segoe UI", 11, "bold")).pack(side=tk.LEFT)
        ttk.Button(top, text="Refresh", command=self._refresh_ports).pack(side=tk.RIGHT, padx=4)
        ttk.Button(top, text="Simulate", command=self._simulate).pack(side=tk.RIGHT, padx=4)

        # port row
        row = ttk.Frame(self)
        row.pack(fill=tk.X, padx=12, pady=4)
        ttk.Label(row, text="Port:").pack(side=tk.LEFT)
        self.port_var = tk.StringVar()
        self.port_combo = ttk.Combobox(row, textvariable=self.port_var, width=28, state="readonly")
        self.port_combo.pack(side=tk.LEFT, padx=6)
        self.connect_btn = ttk.Button(row, text="Connect", command=self._toggle_connect)
        self.connect_btn.pack(side=tk.LEFT, padx=6)
        self.handshake_lbl = ttk.Label(row, text="disconnected", foreground="#F44747")
        self.handshake_lbl.pack(side=tk.LEFT, padx=12)
        ttk.Button(row, text="Ping", command=self._ping).pack(side=tk.LEFT, padx=4)

        # info grid
        info = ttk.LabelFrame(self, text="Device Information", padding=10)
        info.pack(fill=tk.X, padx=12, pady=8)
        self.info_vars = {}
        for i, key in enumerate(["FW Version","HW Version","F_CPU","RAM","Channels","Cartridge","Capabilities","UID"]):
            ttk.Label(info, text=key+":", width=14, anchor="w", foreground="#9E9E9E").grid(row=i, column=0, sticky="w", pady=1)
            var = tk.StringVar(value="—")
            ttk.Label(info, textvariable=var, anchor="w").grid(row=i, column=1, sticky="w", pady=1)
            self.info_vars[key] = var
        info.columnconfigure(1, weight=1)

        # status
        stat = ttk.LabelFrame(self, text="Live Status", padding=10)
        stat.pack(fill=tk.BOTH, expand=True, padx=12, pady=8)
        self.status_text = tk.Text(stat, height=10, bg="#252526", fg="#D4D4D4", relief=tk.FLAT, font=("Consolas", 9))
        self.status_text.pack(fill=tk.BOTH, expand=True)
        self.status_text.configure(state=tk.DISABLED)

        # log
        self.log(f"Ready. Select a port and click Connect.\nTips: On Linux ports like /dev/ttyACM0, on Windows COM3 etc.")

    def _refresh_ports(self):
        ports = device_manager.list_ports()
        self.port_combo["values"] = ports if ports else ["(no ports — try Simulate)"]
        if ports and not self.port_var.get():
            self.port_var.set(ports[0])
        # also auto-select last
        try:
            from app.core.config import AppConfig
            cfg = AppConfig.load()
            if cfg.last_port and cfg.last_port in ports:
                self.port_var.set(cfg.last_port)
        except Exception:
            pass

    def _toggle_connect(self):
        if device_manager.connected:
            device_manager.disconnect()
            self.connect_btn.configure(text="Connect")
            self.handshake_lbl.configure(text="disconnected", foreground="#F44747")
            self.log("Disconnected.")
        else:
            port = self.port_var.get()
            if not port or port.startswith("("):
                self.log("No port selected.")
                return
            self.log(f"Connecting to {port} …")
            self.handshake_lbl.configure(text="handshaking…", foreground="#CCA700")
            ok = device_manager.connect(port)
            if ok:
                self.log("Handshake OK.")
            else:
                self.log("Handshake timeout — device may be busy or not a Sniffer. Try Reset or Simulate.")
                self.handshake_lbl.configure(text="handshake failed", foreground="#F44747")
            # save last port
            try:
                from app.core.config import AppConfig
                cfg = AppConfig.load()
                cfg.last_port = port
                cfg.save()
            except Exception:
                pass
            self._update_btn()

    def _simulate(self):
        # toggle sim
        if device_manager.connected:
            device_manager.disconnect()
        ok = device_manager.connect_simulated()
        self.log("Started simulated device (no hardware needed).")
        self.handshake_lbl.configure(text="simulated", foreground="#89D185")
        self._update_btn()

    def _ping(self):
        if device_manager.connected:
            device_manager.ping()
            self.log("Ping sent.")

    def _update_btn(self):
        self.connect_btn.configure(text="Disconnect" if device_manager.connected else "Connect")

    def _on_connected(self, info=None):
        self.after(0, lambda: self._show_info(info))
        self.handshake_lbl.configure(text="connected", foreground="#89D185")
        self._update_btn()
        self.log(f"Connected: FW {info.fw_version}  {info.cartridge_name}  {info.uid}")

    def _show_info(self, info):
        mapping = {
            "FW Version": info.fw_version,
            "HW Version": info.hw_version,
            "F_CPU": f"{info.f_cpu/1e6:.0f} MHz",
            "RAM": f"{info.ram_bytes//1024} KB",
            "Channels": str(info.num_channels),
            "Cartridge": info.cartridge_name,
            "Capabilities": f"0b{info.capabilities:04b} (T{bool(info.capabilities&1)} C{bool(info.capabilities&2)} DMA{bool(info.capabilities&4)})",
            "UID": info.uid,
        }
        for k,v in mapping.items():
            self.info_vars[k].set(v)

    def _on_disconnected(self, reason=None):
        self.after(0, lambda: self.handshake_lbl.configure(text="disconnected", foreground="#F44747"))
        self.after(0, self._update_btn)
        self.log(f"Disconnected ({reason})")

    def _on_status(self, status=None):
        txt = f"state={status.state_name}  trans={status.transitions}  bytes={status.bytes_streamed}  crcErr={status.crc_errors}  over={status.overruns}  fill={status.fill_pct}%"
        self.after(0, lambda: self.log(txt, tag="status"))

    def _on_error(self, code=None, text=None):
        self.after(0, lambda: self.log(f"ERROR {code}: {text}", tag="error"))

    def log(self, msg, tag=None):
        self.status_text.configure(state=tk.NORMAL)
        self.status_text.insert(tk.END, msg+"\n")
        self.status_text.see(tk.END)
        self.status_text.configure(state=tk.DISABLED)
