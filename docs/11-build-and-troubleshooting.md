# Build Instructions & Troubleshooting

## Firmware Build

### PlatformIO (recommended, cross-platform)

```bash
pip install platformio
cd firmware
pio run                # compile only, check for errors
pio run --target upload # compile + upload to Teensy 4.1
pio device monitor     # serial monitor 115200 (framed binary, not readable text)
```

`platformio.ini` expects `board = teensy41`, `framework = arduino`, `F_CPU=600000000`.

### Arduino IDE

1. Install Teensyduino from https://www.pjrc.com/teensy/td_download.html
2. Open `firmware/src/main.cpp` — if IDE wants a sketch folder, create `Sniffer/` and copy `main.cpp` as `Sniffer.ino` plus `include/*`.
3. Tools → Board: Teensy 4.1, USB Type: Serial, CPU Speed: 600 MHz.
4. Upload.

Upload erases previous firmware; keep a backup of `.hex` via `pio run --target build` in `.pio/build/teensy41/firmware.hex`.

## Host Build

```bash
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r app/requirements.txt
python app/main.py
```

Requires Python 3.10+. No external GUI deps beyond stdlib `tkinter` and `pyserial`.

*Linux*: `sudo apt install python3-tk` if `tkinter` missing.
*macOS*: Tk bundled with python.org installer; `brew install tcl-tk` if needed.
*Windows*: Official python.org installer includes Tk.

## Running Without Hardware

```bash
pytest -q  # all unit tests
python tests/generators/spi_generator.py --out /tmp/synth.stcap
python app/main.py --simulate /tmp/synth.stcap
python app/main.py --replay /tmp/synth.stcap
```

CI uses these generators — no Teensy needed.

## Common Issues

### 1. “No serial ports”

* Use a data USB cable (4-wire). Charge-only cables fail.
* Linux: `dmesg | tail` should show `cdc_acm 1-2:1.0: ttyACM0: USB ACM device` when Teensy plugged. If not, try another port/hub.
* Windows: Check Device Manager → Ports (COMx). Install Teensyduino drivers if needed.
* Permissions (Linux): `sudo usermod -a -G dialout $USER` then log out/in, or `sudo chmod 666 /dev/ttyACM0` for quick test.

### 2. “Handshake failed / timeout”

* Device is not a Sniffer firmware — upload correct firmware.
* Another app holds port (Arduino monitor, `pio device monitor`) — close it.
* Try `Reset` in Device Manager or press Teensy button.
* Use **Simulate** to verify GUI path.

### 3. “Capture overflow”

* Bus too fast for polling path (>2 M transitions/s). Reduce sample rate, shorten leads, or wait for Phase 2 DMA.
* Check CPU load host side — close heavy apps.

### 4. CRC errors increasing

* USB buffer overrun or loose wiring causing missed bits? Actually CRC covers framed packets, not signal — indicates USB corruption or EMI. Lower rate, shorter USB cable.
* Firmware `rxDecoder crcErrors` should stay 0; host parser `StreamDecoder.crc_errors` similarly.

### 5. Waveform empty or flat

* Channels disabled — check Channel Config `Enable All`.
* Wrong pins? Verify `docs/02-pin-assignment.md` and your harness.
* Bare GPIO floating picks up noise — tie unused channels LOW or disable them, enable pull-down in future Phase.

### 6. App theme not applying

* Theme saved in `~/.sniffer/config.json`. Delete file to reset.

### 7. Large captures slow

* >1 M transitions: waveform virtualized but still parses all. Use **Trigger** to limit capture window, or export filtered CSV.
* Phase 12 will add lazy rendering + level-of-detail decimation.

### 8. Linux `tkinter` missing

```
ModuleNotFoundError: No module named '_tkinter'
```
→ `sudo apt update && sudo apt install python3-tk python3-pil python3-pil.imagetk`

### 9. Windows antivirus blocks serial

* Windows Defender may block newly plugged COM ports. Allow `python.exe` in firewall, or test with Simulate first.

### 10. PlatformIO “teensy” platform not found

```bash
pio platform install teensy
pio run --target upload
```

If behind proxy, set `http_proxy`.

## Logs

* File: `~/.sniffer/logs/app.log` — tail with `tail -f ~/.sniffer/logs/app.log`
* Console: `python app/main.py 2>&1 | tee log.txt`

## Getting Help

* Check `docs/00-architecture-overview.md` for phase roadmap.
* Open an issue with: OS, Python `python --version`, Teensy FW `HELLO_ACK` log line, and a synthetic `.stcap` repro if possible.

