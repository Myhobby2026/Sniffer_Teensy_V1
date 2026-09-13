# User Manual — Sniffer Teensy V1 (Phase 1)

## 1. Overview

The Sniffer is a 16-channel logic analyzer built around a Teensy 4.1. It captures digital transitions with 20 ns timestamp resolution, streams them over USB, and visualizes them in a Python Tkinter application.

**Phase 1 workflow:**

1. Connect Teensy via USB.
2. Configure 16 channels (labels, enable, trigger).
3. Choose capture mode and trigger (Phase 1: immediate).
4. Start capture → streaming `.stcap` file.
5. View waveform (zoom/pan/cursors), export CSV/JSON.

## 2. Installation

### Firmware

* Install Teensyduino or PlatformIO (`pip install platformio`).
* `cd firmware && pio run --target upload`.
* Device appears as `/dev/ttyACM0` (Linux) / `COMx` (Win) / `/dev/cu.usbmodem*` (macOS).

### Host

```bash
pip install -r app/requirements.txt  # pyserial
python app/main.py
```

If you have no hardware: `python app/main.py --simulate`.

## 3. GUI Tour (22 pages, Phase 1 implemented 5)

### Dashboard

See quick actions, recent captures, roadmap. Click tiles to jump.

### Device Manager

* **Port** dropdown lists serial ports. Click **Refresh**.
* **Connect** performs handshake: `HELLO → HELLO_ACK` and shows FW version, cartridge, capabilities.
* **Simulate** starts a fake device that streams synthetic data — great for learning.
* **Ping** tests latency.
* **Live Status** shows `state, transitions, bytes, crc errors, overruns`.

If handshake fails: check cable is data (not charge-only), check `dmesg`, try **Simulate** to verify GUI.

### Channel Configuration

* 16 rows: `# / Enable / Label / Color / Trigger / Pin`.
* **Trigger** per-channel: `none / rising / falling / both` — Phase 1 stores it but capture uses pattern trigger in Phase 2. Still configure for future and for host-side filtering.
* **Presets:** `SPI 4-wire`, `I2C`, `UART`, `8-bit Parallel`, `Clear`.
* **Apply to Device** sends `CONFIG_CHANNELS` (enable_mask, rising, falling). Local config persists even without device.

### Capture

* **Save to:** choose `.stcap` path. Recent files remembered.
* **Mode:** `Transition` (edge-compressed, recommended) vs `Continuous` (periodic). Continuous requires `Rate (Hz)`.
* **Pre/Post trigger:** ms before/after trigger (Phase 2 honors these; Phase 1 immediate ignores pre).
* **Pattern trigger:** hex mask/value + edge ch/type. Pattern = trigger when `(sample & mask)==value`.
* **Start Capture:** validates config, starts writer, tells device `CMD_START`. Progress shows transitions and rate.
* **Stop:** `CMD_STOP`. Data preserved even on overflow or disconnect.

### Waveform

* X-axis is time (`µs/px` scale). Y is channels stacked.
* **Zoom:** mouse wheel.
* **Pan:** click-drag.
* **Cursors:** click on ruler to place C1/C2, drag to move. Delta box shows `Δ µs, ms, Hz (1/Δt)`. `Clear Cursors` resets.
* **Fit:** zooms to capture span.
* **Channel toggles:** right panel checkboxes hide/show channels without losing data.
* **Export CSV/JSON:** saves `time_s, time_ns, sample_hex, CH0..CH15` or JSON array.

### Future Pages (stubs)

`Protocol, SPI, I2C, UART, 1-Wire, Hex, Packets, Graph, Trigger, Search, Compare, Sensor, Calibration, Settings, Firmware, Plugins, Help` show Phase badges and feature previews.

## 4. Captures

### Saving / Loading

* Captures saved as `.stcap` (header + JSON meta + chunks). Forward-compatible.
* **Open** via `File → Open Capture` or Waveform `Open…` or Dashboard recent list.
* **Replay:** `python app/main.py --replay path.stcap` or `--simulate path.stcap` to stream it live.

### Export

* **CSV:** `time_s, time_ns, sample_hex, ch0..ch15`
* **JSON:** `{"f_cpu":600000000, "transitions":[{"t_ns":0,"sample":4660,"hex":"1234"},...]}`
* **TXT/BIN** planned (use CSV/JSON for now).

### Tips

* Keep captures short for high-rate buses: 50–200 ms at 2 M transitions/s is 100–400k edges, waveform stays responsive.
* Use **Trigger position** (Phase 2) to capture 50 ms pre + 200 ms post around event.
* Save notes in capture: Channel Config labels and Capture notes go into `.stcap` JSON meta.

## 5. Reverse-Engineering Workflow (Phase 9 preview)

Already possible with Phase 1:

1. Capture with unknown SPI: connect protected module, 16-ch, transition mode.
2. Waveform: measure clock frequency (Δ between SCLK edges), identify CS framing.
3. Export CSV, look for repeating packets, constant bytes, variable bytes.
4. Use synthetic generators to test hypotheses: modify `tests/generators/spi_generator.py` to emulate guess, compare timing.

Full tools (field correlation, CRC scan, compare) arrive Phase 9.

## 6. Sensor Workflow (Phase 10 preview)

* Hook analog sensor (0–5 V → divider → Teensy ADC or external ADS8688) plus SPI.
* Capture analog voltage + SPI simultaneously (Phase 12 analog).
* Graph Analyzer will plot `voltage vs time` alongside decoded `SPI byte vs time` to find correlation (scaling, offset, endian).

## 7. Keyboard & Themes

* `Ctrl+O` open capture.
* `View → Dark/Light/High Contrast` or toolbar dropdown. Preference saved in `~/.sniffer/config.json`.

## 8. Safety

See `docs/07-safety-and-wiring.md`. Summary:

* Measure voltage before wiring.
* Use correct cartridge.
* GND first, short leads, twist with GND.
* Never exceed 3.3 V on bare GPIO.

## 9. Troubleshooting

See `docs/11-build-and-troubleshooting.md`.

