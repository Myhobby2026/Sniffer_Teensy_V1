# Python Architecture — Tkinter Desktop Application

## 1. Stack

* Python 3.10+ (type hints, `dataclasses`, `queue`, `threading`, `mmap`)
* Tkinter + ttk (stdlib, no external GUI dep)
* `pyserial` (only non-stdlib dep, for Serial transport)
* `numpy` optional (gracefully degraded if missing, for graph math)

No Electron, no Qt, no heavy deps — keeps install simple and future-proof.

## 2. Folder Layout

```
app/
  main.py                 // entry, parse args, start App
  requirements.txt
  README.md
  core/
    config.py             // AppConfig, load/save JSON (~/.sniffer/config.json)
    logger.py             // centralized logging (logging module, file + console)
    events.py             // lightweight pub/sub EventBus for decoupled UI
  device/
    protocol.py           // Packet dataclass, encode/decode, CRC16
    transport.py          // SerialTransport (threaded reader, queue)
    manager.py            // DeviceManager: discovery, handshake, state machine
    models.py             // DeviceInfo, ChannelConfig
  capture/
    format.py             // .stcap constants, header structs
    writer.py             // CaptureWriter (stream → file)
    reader.py             // CaptureReader (mmap, iter_batches)
    manager.py            // CaptureManager orchestrates writer/reader
  models/
    channel.py            // Channel, TriggerConfig
    trigger.py            // TriggerPattern, TriggerEngine (host-side sim)
  storage/
    recent.py             // recent files, project/session management
  gui/
    theme.py              // Dark/Light/HighContrast palettes, ttk styles
    app.py                // MainWindow, menu, toolbar, statusbar, Notebook
    pages/
      dashboard.py        // Overview + recent + stats
      device_manager.py   // Port list, connect, handshake, status
      channel_config.py   // 16 channels toggles, labels, colors
      capture_page.py     // Start/stop, pre/post, progress, save
      waveform.py         // Canvas waveform (virtualized)
      placeholder.py      // Factory for Ph.5+ pages (SPI/I2C/UART/etc)
    widgets/
      channel_row.py      // Per-channel row (enable, color, label)
      status_bar.py       // StatusBar with state, rate, errors
      waveform_canvas.py  // High-performance Canvas with zoom/pan/cursors
  utils/
    crc.py                // crc16, crc32 helpers
  plugins/
    base.py               // Decoder interface (future)
```

Future (Ph.5+):

```
protocols/  // SPI/I2C/UART decoders implementing plugins.base.Decoder
analyzers/  // hex, graph, reverse
decoders/
```

## 3. Threading & Responsiveness

* **Tk mainloop** never blocks. All I/O in background threads.
* `SerialTransport` spawns `reader Thread` → `queue.Queue` of raw bytes → reassembles packets → `packet_queue`.
* `DeviceManager` runs polling thread that converts `packet_queue → EventBus.emit("packet", pkt)` on main thread via `root.after(10, poll)`.
* `CaptureManager` writes to disk in its own thread; waveform rendering is lazy (only viewport).

```
[Serial Thread] --bytes--> [Reassembly] --packets--> [DeviceManager] --events--> [GUI after()]
```

## 4. GUI Architecture

### 4.1 MainWindow (`gui/app.py`)

* `tk.Tk` root, `ttk.Style` themed.
* Top: `Menu` + `Toolbar`
* Center: `ttk.Notebook` with pages (Dashboard, Device, Channels, Capture, Waveform, …) + `ttk.PanedWindow` for resizable panels.
* Bottom: `StatusBar` (device state, buffer fill, rate, message).
* `EventBus` decouples pages: `bus.subscribe("device_status", handler)` etc.

### 4.2 Pages

Each page is `ttk.Frame` subclass with `on_show()`/`on_hide()` lifecycle.

* **Dashboard:** welcoming stats, recent captures, quick actions.
* **Device Manager:** `serial.tools.list_ports.comports()`, connect/disconnect, handshake display (FW/HW version, cartridge, caps).
* **Channel Config:** 16 rows with enable/ trigger type/ label/ color/ pin override; sends `CONFIG_CHANNELS` on apply.
* **Capture:** mode (transition/continuous), rate, trigger pattern builder, pre/post sliders, start/stop, elapsed, transition count, save-as.
* **Waveform:** `WaveformCanvas` (Canvas-based, virtualized). Features: zoom (mouse wheel), pan (drag), cursors (click), delta measurement, hide/show channels, trigger marker, time scale.

### 4.3 WaveformCanvas

* Data is transition batches (sparse). Rendering converts to screen X: `x = (t - t0) * px_per_sec`.
* Only draws visible window + small overdraw; batches outside viewport skipped.
* Edges drawn as vertical lines, highs as horizontal bars with channel colors.
* Cursors are draggable lines; label shows `Δt`, frequency (`1/Δt`).
* Uses `Canvas.create_line` / `create_text`; batches consolidated where many edges would overlap (level-of-detail downsampling).

## 5. Theming

`gui/theme.py`:

```python
THEMES = {
  "dark": {"bg":"#1E1E1E","fg":"#D4D4D4","accent":"#007ACC", ...},
  "light": {"bg":"#F5F5F5", ...},
  "high_contrast": {...}
}
def apply_theme(root, name): ...
```

Persists in `~/.sniffer/config.json` → `{"theme":"dark", "recentFiles":[...]}`.

## 6. Plugin Interface (future-proof)

```python
# plugins/base.py
class Decoder(ABC):
    name: str
    @abstractmethod
    def decode(self, transitions: Iterable[Transition], config: dict) -> list[Packet]: ...
    @abstractmethod
    def auto_detect(self, transitions) -> tuple[bool, float, str]: ... # (is_candidate, confidence, reason)
```

New protocols added under `plugins/spi/` without touching core. Discovery via `importlib` scanning `plugins/*/plugin.json`.

## 7. Capture Lifecycle

```
CONFIG → START → streaming DATA_* → STOP → finalize .stcap → auto-load in Waveform
```

`CaptureManager` owns `CaptureWriter` instance; on `DATA_TRANSITION` it calls `writer.add_transitions()`; on `EVT_STOPPED` it finalizes file and emits `capture_complete` event.

## 8. Error Handling

* Transport disconnect → `EventBus.emit("device_disconnected", reason)` → StatusBar red, Capture page stops, data preserved.
* CRC error → increment counter, log, continue.
* Overflow → dialog warn, keep data.
* Invalid capture file → dialog + log, no crash.

## 9. Testing Without Hardware

* `tests/generators/*` produce synthetic `.stcap` files.
* `DeviceManager` has `SimulationTransport` that replays a capture file as if streaming.
* `pytest` suite covers `protocol`, `format`, `reader/writer` without serial.

## 10. Entry Point

```bash
pip install -r app/requirements.txt
python app/main.py
# or simulated:
python app/main.py --simulate tests/data/synthetic.stcap
```

See `app/README.md`.

