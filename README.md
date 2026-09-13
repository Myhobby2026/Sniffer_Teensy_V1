# Universal Bus Sniffer & Logic Analyzer — Teensy 4.1 + Python Tkinter

**Phase 1** — 16-channel raw transition capture, USB framed transport, modular GUI.

> Professional instrument architecture, not an Arduino demo. Fully documented, testable without hardware, forward-compatible capture format, and ready for SPI/I2C/UART/etc. decoders.

![Phase](https://img.shields.io/badge/Phase-1%20Raw%20Capture-blue) ![Teensy](https://img.shields.io/badge/Hardware-Teensy%204.1-success) ![Python](https://img.shields.io/badge/GUI-Python%20Tkinter-yellow)

---

## Architecture at a Glance

```
DUT (unknown bus) → 16-ch protected front-end → Teensy 4.1 (i.MX RT1062 600 MHz)
                    ↳ GPIO6/7 port capture + DWT cycle counter (1.66 ns)
                    ↳ double buffering + USB HS CDC (framed binary, CRC16)
                                   ↓ 480 Mbit/s
                    Python Tkinter Desktop App
                    ↳ Device Manager, Channels, Capture, Waveform (zoom/pan/cursors), Hex/Graph stubs
                    ↳ .stcap file (header + JSON meta + chunked payload, CRC32)
                    ↳ Plugin-ready decoders (SPI/I2C/UART/1-Wire)
```

**Docs:** `docs/00-architecture-overview.md` → `01` hardware, `02` pin map, `03` USB protocol, `04` capture format, `05` firmware, `06` Python, `07` safety, `08` performance.

---

## 16-Channel Input & Safety

* 16 independent digital channels, each with enable/trigger/label/color.
* Replaceable protection cartridge. **Default CARRIER-3V3:** 330 Ω + TVS per channel, BAT54S clamp. *Never* connect >3.3 V without the correct cartridge.
* 5 V → **CARRIER-5V** (TXS0108), RS-232 → **MAX3232**, RS-485/CAN → transceivers, Automotive 12/24 V → divider+opto. See `docs/07-safety-and-wiring.md`.

---

## Teensy 4.1 Capabilities (Realistic)

| Mode | Phase 1 sustained | Burst | Timestamp |
|---|---|---|---|
| Transition (edge-compressed) | ~2 M transitions/s | — | 20 ns (1.66 ns raw) |
| Continuous (periodic) | ~2 MS/s streaming | 8–10 MS/s burst to RAM | — |

Theory vs. reality distinguished in `docs/08-performance-analysis.md`. High-speed paths (DMA/FlexIO) are Phase 2+.

---

## USB Protocol & Capture Format

* **Framed binary:** `MAGIC(2) TYPE(1) LEN(2) SEQ(2) PAYLOAD CRC16(2)` on CDC-ACM. See `docs/03-usb-protocol-spec.md`.
* **.stcap:** `Header 128B + JSON meta + ChunkHeader(12B)+payload + CRC32`, forward-compatible. See `docs/04`.

---

## Repository Layout

```
docs/            # architecture & specs
firmware/        # Teensy 4.1 C++ (PlatformIO)
  include/       # version, config, usb, channels, capture, buffers, timing
  src/           # main.cpp, capture, usb, channels...
app/             # Python GUI
  core/ device/ capture/ models/ gui/ utils/ plugins/ storage/
  main.py
tests/           # pytest + synthetic SPI/I2C/UART generators (.stcap without hardware)
```

GUI is modular: `Dashboard | Device | Channels | Capture | Waveform | … (16 placeholder pages for future phases)` with dark/light/high-contrast themes, `ttk.Notebook`, `Canvas` waveform, background threads (never blocks mainloop).

---

## Quick Start

### Firmware (Teensy 4.1)

```bash
# PlatformIO (recommended)
pip install platformio
cd firmware
pio run --target upload
pio device monitor

# Arduino IDE alternative: open firmware/src/main.cpp, Board Teensy 4.1, USB Type Serial, CPU 600 MHz
```

Wiring: see `docs/02-pin-assignment.md` (logical CH0-15 → Teensy pins 0,1,2,3,4,5,6,7,8,9,10,11,12,13,32,33) and `docs/07`.

### Host GUI

```bash
pip install -r app/requirements.txt
python app/main.py
# no hardware? simulate
python app/main.py --simulate
# open a capture on start
python app/main.py --replay captures/example.stcap

# generate synthetic captures for demo/tests
python tests/generators/spi_generator.py --out /tmp/synth_spi.stcap --transactions 5
python tests/generators/i2c_generator.py --out /tmp/synth_i2c.stcap
python tests/generators/uart_generator.py --out /tmp/synth_uart.stcap --text "Hello"
python app/main.py --simulate /tmp/synth_spi.stcap
```

Recent files & theme persist in `~/.sniffer/config.json`.

---

## Testing (no hardware needed)

```bash
pytest -q
# or per-file
pytest tests/test_usb_protocol.py -v
pytest tests/test_capture_format.py -v
```

Synthetic `.stcap` files verify decoder & GUI paths in CI.

---

## Phased Roadmap

| Phase | Goal | Status |
|---|---|---|
| **1** | USB + raw 16-ch capture + GUI skeleton + waveform + .stcap | **Done (this branch)** |
| 2 | DMA, trigger (pattern/edge/pre-post), timestamps | Next |
| 3 | Live monitor polish | — |
| 4 | Waveform pro (measurements, annotations) | Basic included |
| 5–8 | SPI (Modes 0-3), I2C, UART, 1-Wire decoders | Stubs & synthetic generators |
| 9 | Reverse tools (diff, correlation, CRC scan) | Interface defined |
| 10 | Graph & sensor correlation | Stub |
| 11 | Plugin system (hot-load decoders) | Interface `plugins/base.py` |
| 12 | Optimization, analog, packaging | Hooks |

Each phase keeps prior APIs working.

---

## Coding Rules

* Firmware: C++17, fixed-width ints, no `digitalRead` in fast path, DMA/FlexIO where it multiplies capability, documented timing sections.
* Host: Python 3.10+, type hints, logging, `queue`+`threading`, no unnecessary deps (only `pyserial`).

---

## Safety

**Every input is UNKNOWN until verified.** Measure voltage vs. sniffer GND, use the correct cartridge, connect GND first, keep leads short. Full guide `docs/07`.

---

## License & Disclaimer

Research/engineering tool. No isolation for mains/high-voltage. Use proper isolation for dangerous buses. Authors not liable for damage from incorrect wiring.
