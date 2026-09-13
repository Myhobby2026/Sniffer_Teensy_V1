import tkinter as tk
import tkinter.ttk as ttk

def make_placeholder(parent, title: str, subtitle: str = "", app_ref=None):
    frame = ttk.Frame(parent)
    hdr = ttk.Label(frame, text=title, font=("Segoe UI", 14, "bold"))
    hdr.pack(pady=(24,6))
    if subtitle:
        ttk.Label(frame, text=subtitle, foreground="#9E9E9E", wraplength=640, justify=tk.CENTER).pack(pady=4)
    body = ttk.Frame(frame)
    body.pack(fill=tk.BOTH, expand=True, padx=24, pady=12)

    # Phase badge
    badge = tk.Label(body, text="Available in later phases — stub UI", bg="#2D2D30", fg="#CCA700", font=("Segoe UI", 9, "bold"), padx=12, pady=6)
    badge.pack(pady=8)

    # Feature list placeholder
    features = {
        "SPI Analyzer": ["MOSI/MISO/SCLK/CS, Mode 0-3, CPOL/CPHA, bit order, word size, hex view, timing"],
        "I2C Analyzer": ["SDA/SCL, addr decode, R/W, ACK/NACK, START/STOP, filtering"],
        "UART Analyzer": ["RX/TX, baud/parity/stop, inversion, framing errors"],
        "1-Wire Analyzer": ["Reset/presence, ROM cmds, timing analysis"],
        "Protocol Analyzer": ["Search, filter, packet table with hex"],
        "Hex Viewer": ["Hex/Dec/Bin/ASCII, endian, bitfields, pattern detection"],
        "Packet Analyzer": ["Packet list, sorting, highlighting"],
        "Graph Analyzer": ["Plot decoded bytes vs time, zoom/pan/cursors"],
        "Trigger Config": ["Pattern, edge, protocol, pre/post — enhanced in Phase 2"],
        "Search": ["Find patterns, value search across captures"],
        "Compare": ["Diff two captures, highlight differing bytes"],
        "Sensor Analyzer": ["Correlate analog voltage with SPI field"],
        "Calibration": ["Analog gain/offset, voltage scaling"],
        "Settings": ["Theme, paths, device defaults"],
        "Firmware Info": ["Version, capabilities, diagnostics"],
        "Plugin Manager": ["Load/unload protocol plugins"],
        "Help/About": ["Docs, shortcuts, wiring guide"],
    }
    txt = features.get(title, ["This page will host future functionality."])
    for line in txt:
        ttk.Label(body, text="•  " + line, foreground="#D4D4D4", wraplength=640, justify=tk.LEFT).pack(anchor="w", pady=2)

    # button to return
    if app_ref:
        ttk.Button(body, text="Back to Dashboard", command=lambda: app_ref.show_page("Dashboard")).pack(pady=16)
    return frame
