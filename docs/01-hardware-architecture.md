# Hardware Architecture — 16-Channel Universal Sniffer (Teensy 4.1)

## 1. System Block Diagram

```
  [Target DUT] --(16x digital)--+
                                 |
  [Protection / Level Module] <--+---> [Analog Front-End (optional, Ph.12)]
         |                               (divider + op-amp + ADS8688)
         | 16x 0–3.3V CMOS
         v
  [Teensy 4.1 — i.MX RT1062]
   - GPIO6/7/9 port capture
   - DWT cycle counter (timestamp)
   - PIT timer / DMA (Ph.2)
   - FlexIO (Ph.5+ SPI)
   - USB HS (device, CDC)
         | USB 480 Mbit/s
         v
  [Host PC — Python Tkinter App]
   - waveform / protocol / hex / graph
   - capture format .stcap
```

## 2. Teensy 4.1 Role

* Sole acquisition master. No FPGA required.
* All 16 digital channels sampled synchronously via 32-bit port reads.
* Timestamped in hardware clock domain, not USB wall-clock.
* Streams framed binary to host; host does decode.
* Firmware modular: `capture/`, `channels/`, `buffers/`, `triggers/`, `usb/`.

## 3. Input Module Philosophy

**Replaceable cartridge.** Do not solder unknown-voltage wiring directly to Teensy.

* **Base board (Teensy carrier):** 2×20 pin header, TVS array + 330 Ω series on every line, ground solid plane, optional solder jumpers to select direct vs. buffered path.
* **Cartridge variants:**
  * `CARRIER-3V3` — direct with protection (default Phase 1)
  * `CARRIER-5V` — TXS0108E level shifter, 5 V tolerant
  * `CARRIER-RS232` — MAX3232 ×4
  * `CARRIER-RS485/CAN` — isolated transceivers
  * `CARRIER-ANALOG` — 8× analog 0–5 V → 0–3.3 V + external ADS8688 over SPI2 (Phase 12)

Each cartridge reports its ID via 2 strap pins read at boot (`CARTRIDGE_ID0/1`), firmware includes it in handshake so app warns if mismatch (e.g., 5 V cartridge needed but 3V3 installed).

## 4. Protection per Channel (CARRIER-3V3)

Per channel (×16):

```
DUT ── 330R ─┬─ 100R ── Teensy GPIO
             │
            TVS ── GND   (ESD5V0S1BB or PRTR5V0U2X, clamping ~5 V)
             │
          3V3 ─ Zener? not needed if TVS
         GND ── BAT54S clamp (optional dual Schottky to 3V3/GND)
```

* Series 330 Ω limits current to ~10 mA @ 5 V accidental (still exceeds spec, but clamps). For 12 V automotive, must use CARRIER-5V + divider or external module.
* 100 pF cap optional for edge filtering.
* Ground: star to Teensy GND, connect DUT GND — never float.

## 5. Clock & Timing

* CPU 600 MHz (F_CPU). Overclock not assumed.
* DWT_CYCCNT timestamps: 64-bit extended, resolution 1.666 ns, drift < 30 ppm (crystal).
* PIT ch0 drives sampling tick for continuous mode (Phase 2). Phase 1 transition mode free-runs poll loop + timestamps on change.

## 6. USB

* Teensy 4.1 USB HS PHY (USB3320). Firmware presents as **CDC Serial** (single interface). Host sees `/dev/ttyACM0` (Linux) / `COMx` (Win) / `/dev/cu.usbmodem*` (macOS).
* Framed protocol on top of CDC (not raw text). DTR controls capture state.
* Power: Teensy VUSB → 5 V, regulator → 3.3 V. Total budget ~120 mA; protection module adds <20 mA.

## 7. Expansion Hooks

* I²C pins (18/19) reserved for ADS8688 or external EEPROM for calibration.
* SPI2 (if not used for capture channels) for external ADC.
* CAN FD pins (22/23) reserved but not used in Phase 1 — wired to transceiver header.
* FlexIO pins exposed on carrier for future 30 MHz capture.

See also: `02-pin-assignment.md`, `07-safety-and-wiring.md`, `08-performance-analysis.md`.
