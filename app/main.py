#!/usr/bin/env python3
"""Sniffer Teensy V1 — main entry"""
import sys
import argparse
import tkinter as tk
from pathlib import Path

# Ensure app is importable when run as script
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.logger import get_logger
log = get_logger("main")

def parse_args():
    ap = argparse.ArgumentParser(description="Universal Bus Sniffer & Logic Analyzer — Teensy 4.1 GUI")
    ap.add_argument("--simulate", nargs="?", const="__sim__", metavar="REPLAY.stcap", help="Start with simulated device, optionally replay a capture")
    ap.add_argument("--replay", metavar="FILE.stcap", help="Open a capture file on startup")
    ap.add_argument("--theme", choices=["dark","light","high_contrast"], help="Override theme")
    return ap.parse_args()

def main():
    args = parse_args()
    root = tk.Tk()
    # High-DPI on Windows
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    from app.gui.app import MainWindow
    app = MainWindow(root, simulate=args.simulate, replay=args.replay)
    if args.theme:
        app.set_theme(args.theme)

    log.info("GUI started")
    root.mainloop()

if __name__ == "__main__":
    main()
