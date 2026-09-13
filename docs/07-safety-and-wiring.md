# Safety & Wiring Guide

**Read this before connecting any DUT.** Teensy GPIOs are 3.3 V only, not 5 V tolerant, not automotive-tolerant. Permanent damage occurs above 3.6 V on a GPIO, below –0.3 V, or outside current limits.

---

## 1. Golden Rule

> **Every input is UNKNOWN until verified.** Never connect a wire before measuring its voltage relative to sniffer GND, and never without the appropriate protection module.

---

## 2. Voltage Limits (Teensy 4.1 Bare GPIO)

* Absolute maximum: –0.3 V .. 3.6 V
* Recommended operating: 0 .. 3.3 V
* Input clamp current: ±4 mA max (clamp diodes)
* Series resistor required for any risk of over-voltage.

Exceeding these, even briefly, can latch up the i.MX RT1062 and destroy it.

---

## 3. Protection Module (CARRIER-3V3 Default)

Per channel (×16 identical):

```
DUT signal ── 330Ω ─┬─ 100Ω ──> Teensy GPIO
                    │
                   TVS  (PRTR5V0U4Y or ESD5V0S1BB, Vrwm 5 V)
                    │
                   GND
```

* 330 Ω limits short-circuit to ~10 mA @ 3.3 V, ~15 mA @ 5 V accidental (survivable for short transients, not continuous 12 V).
* TVS clamps ESD ±15 kV air, ±8 kV contact.
* Optional secondary: BAT54S dual Schottky to 3.3 V and GND for additional clamp before Teensy.

This module is **intended for 0–3.3 V logic only**. It is *not* a substitute for level shifting when mixing 5 V.

---

## 4. 5 V Systems (Arduino Uno, AVR, 5 V SPI)

Use **CARRIER-5V** (TXS0108E or TXB0108, 8-bit auto-dir level shifter per 8 channels, ×2). Wiring:

```
DUT 5V ── TXS0108 B-port ── A-port 3.3V ── Teensy
VCCA=3.3 V, VCCB=5 V, OE pulled high
```

* OE tied to VCC via 10 k, with jumper to disable.
* Ensure DUT GND ↔ Sniffer GND common.

*Do not use resistive divider for high-speed (>1 MHz) — skew and loading degrade edges.* Use active shifter.

---

## 5. RS-232 (±3…±15 V)

**Never** connect RS-232 directly. Use **CARRIER-RS232** with MAX3232 (3.3 V variant):

```
DB9 ── MAX3232 RS232-in ── TTL 3.3 V ── Teensy
```

Each MAX3232 handles 2 channels; 8 chips for 16 channels is heavy — practically, use a 4-ch module and only sniff needed lanes (TX,RX plus handshake). Alternatively use external USB-RS232 tap.

---

## 6. RS-485 / CAN Differential

Requires transceiver:

* RS-485: THVD1400 / MAX485 — differential A/B → single-ended RO → Teensy.
* CAN: TJA1051 / MCP2551 — CANH/CANL → RXD → Teensy; also needs CAN controller (MCP2515 over SPI or internal FlexCAN). Phase 11.

Do not sniff differential lines with single-ended probe; use proper receiver or differential probe.

---

## 7. Automotive 12 V / 24 V

Use divider + clamp:

```
12 V signal ── 10k ─┬─ 3.3k ── GND
                    │
                   3.3V Zener / Schottky clamp ── Teensy (through 1k)
```

Better: opto-isolation (e.g., ACPL-247) for “dirty” automotive.

Always connect chassis ground, and ensure sniffer and DUT share ground — floating grounds create apparent high voltages.

---

## 8. Analog (0–5 V Sensor)

Resistive divider scaled to 0–3.3 V + op-amp follower (e.g., OPA2376) for impedance buffering. For precision, use external ADS8688 (16-bit, ±10 V, SPI).

Phase 12 adds calibration: host stores `gain` and `offset` per analog channel: `V_actual = raw * gain + offset`.

---

## 9. Wiring Checklist

1. Power off DUT and sniffer.
2. Connect GND first (use multiple GND pins, short leads).
3. Measure DUT signal with multimeter (DC) — verify within expected range.
4. Choose correct cartridge.
5. Connect signals with shortest possible leads (<20 cm for >2 MHz, twist with GND).
6. Power on, observe Device Manager — verify no over-current warning, inspect live channel monitor (should show stable HIGH/LOW, not flicker).
7. Start small capture (10 ms) before long captures.

---

## 10. ESD & Handling

* Use ESD strap when handling Teensy.
* Store protection modules in anti-static bags.
* Keep sniffer away from high-voltage, inductive spikes (relays, motors).

---

## 11. Labels & Strain Relief

Label each wire (CH0..CH15) and keep harness strain-relieved. Document DUT pinout in capture notes (`Metadata.notes`).

---

## 12. Disclaimer

This instrument is not isolated. For mains, high-voltage, or safety-critical buses, use proper isolation (digital isolators ISO7741, or isolated probes). The authors are not responsible for damage due to incorrect wiring.

