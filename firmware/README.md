# Firmware — Sniffer Teensy V1 (Phase 1)

## Build & Upload

### PlatformIO (recommended)
```bash
pip install platformio
cd firmware
pio run --target upload
pio device monitor
```

### Arduino IDE
1. Install Teensyduino (https://www.pjrc.com/teensy/td_download.html)
2. Board: "Teensy 4.1", USB Type: "Serial", CPU Speed: "600 MHz"
3. Open `src/main.cpp` in IDE (or copy to a sketch folder)
4. Upload.

## After Upload
- Open Serial Monitor (any baud). Device waits for framed HELLO.
- Or run host GUI: `python app/main.py` — it performs handshake.

## Diagnostics
- Send `PING` (framed) → device replies `PONG`.
- LED on pin 13 blinks: slow=IDLE, fast=CAPTURING, solid=ERROR.
- If no handshake within 10 s, device stays idle.

## Phase 1 Features
- 16-channel digital capture (transition mode) via GPIO6/GPIO7 polling.
- 64-bit DWT_CYCCNT timestamps.
- Double buffering + USB framed streaming (CRC16).
- Config via CONFIG_CHANNELS / CONFIG_CAPTURE.
- Trigger: immediate (Phase 1), pattern ready for Phase 2.

## Config
Edit `include/config.h` to change:
- pin map
- buffer sizes
- default sample rate
- protection: enable pull-ups etc.

## Troubleshooting
- "No device": check USB cable is data cable, Teensy appears as /dev/ttyACM0 (Linux) `dmesg | tail`.
- "CRC errors": usually USB buffer overrun — lower sample rate or shorten leads.
- Capture overflow: LED fast blink + EVT_ERROR, data preserved until stop.

See `docs/05-firmware-architecture.md` for module breakdown.

