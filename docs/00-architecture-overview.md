# Universal Bus Sniffer & Logic Analyzer — Architecture Overview

**Platform:** Teensy 4.1 (acquisition) + Python Tkinter (analysis)  
**Channels:** 16 digital (Phase 1), expandable to analog/differential via cartridges  
**Status:** Phase 1 — raw transition capture + USB framed transport + Python GUI  
**Docs index:** `docs/` — start here, then `08-performance-analysis.md` and `03-usb-protocol-spec.md`.

---

## Goals (Summarized from Specification §§1–29)

Instrument-grade, not demo-grade. Separation of concerns:

* Teensy does **acquisition, timestamping, triggering, buffering, streaming** — no heavy decode in ISR.
* Host does **decode, visualize, search, compare, graph, export** — extensible via plugins.

---

## System Layers

```
┌─────────────────────────────────────────────────────────────────┐
│                        Host PC (Python)                          │
│  Dashboard │ Device Mgr │ Channels │ Capture │ Waveform │ …22 pp │
│  ─────────────────────────────────────────────────────────────── │
│  DeviceManager  CaptureManager  Decoder Plugins  Analyzers       │
│  CaptureReader/Writer  EventBus  Storage  Theme                  │
│  USB framing (CRC) driver                                        │
└─────────────────────────────────────────────────────────────────┘
                              │ USB CDC (framed binary)
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Teensy 4.1 Firmware (C++)                     │
│  channels  ──►  capture (poll/DMA)  ──►  buffers (double+ring) │
│                     │ timestamp (DWT)   ──►  usb_protocol        │
│  triggers  diagnostics  config                                   │
└─────────────────────────────────────────────────────────────────┘
                              │ 16-ch protected front-end
                              ▼
                    DUT (unknown bus)
```

---

## Why This Split

* Raw first: decoder bugs never lose data if capture is archived. Capture files replay without hardware.
* Host decode: Python is fast enough and far easier to extend than C++ on MCU; new protocols ship as Python plugins without reflashing Teensy (Phase 11).
* Hardware decode only where it *multiplies* capability (FlexIO SPI slave for >4 MHz).

---

## Phase Roadmap (§26)

| Phase | Deliverable | Status |
|---|---|---|
| 1 | USB handshake + 16-ch raw transition capture | **This branch** |
| 2 | DMA, timestamps, trigger (pattern/edge), pre/post | next |
| 3 | GUI device manager + live monitor | included basic in Phase 1 |
| 4 | Waveform viewer (zoom/pan/cursors) | basic included |
| 5 | SPI decoder (Mode 0-3, CS variants) | stub + synthetic tests |
| 6 | I2C decoder | stub |
| 7 | UART decoder | stub |
| 8 | 1-Wire | stub |
| 9 | Reverse-engineering (diff, correlation, CRC scan) | stub |
| 10 | Graph Analyzer + sensor correlation | stub |
| 11 | Plugin system (hot-load decoders) | interface defined |
| 12 | Optimization + packaging + analog | hooks |

Phase 1 keeps previous functionality working and exposes stable APIs.

---

## Documents

1. `01-hardware-architecture.md` — block diagram, cartridges
2. `02-pin-assignment.md` — logical→physical map, connector
3. `03-usb-protocol-spec.md` — framed packet spec, types, flow
4. `04-capture-format-spec.md` — `.stcap` file, chunks, forward compat
5. `05-firmware-architecture.md` — firmware modules, state machine, DMA hooks
6. `06-python-architecture.md` — Python modules, threading, GUI
7. `07-safety-and-wiring.md` — protection, level shifting, differential
8. `08-performance-analysis.md` — realistic rates, DMA, bottlenecks
9. `00-architecture-overview.md` — this file

---

## Quick Start (Phase 1)

### Firmware
```bash
# PlatformIO
cd firmware
pio run --target upload  # Teensy 4.1 via USB
# or Arduino IDE: open firmware/src/main.cpp, select Teensy 4.1, USB Type: Serial
```

### Host GUI
```bash
pip install -r app/requirements.txt
python app/main.py
# simulated (no hardware):
python app/main.py --simulate
python app/main.py --replay captures/example.stcap
```

### Run tests without hardware
```bash
pytest -q
python tests/generators/spi_generator.py --out /tmp/synth.stcap
```

---

## Safety First

See `07-safety-and-wiring.md` before wiring. Use the correct cartridge; measure before connecting.

---

## Repository Structure

```
.
├── docs/            # architecture & specs
├── firmware/        # Teensy 4.1 C++ (PlatformIO)
├── app/             # Python Tkinter GUI + capture libs
│   ├── core/ device/ capture/ models/ gui/ utils/ plugins/ storage/
│   └── main.py
├── tests/           # pytest + synthetic generators
└── captures/        # example .stcap (generated, not committed)
```
