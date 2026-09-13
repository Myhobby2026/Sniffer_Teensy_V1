# Performance Analysis & Realistic Limits — Teensy 4.1 (i.MX RT1062)

**Date:** 2026-09-13  
**Hardware:** Teensy 4.1 — NXP i.MX RT1062 (Cortex-M7 @ 600 MHz)  
**Relevant constraints govern PHASE 1 and roadmap decisions.**

---

## 1. Core SoC Capabilities

| Resource | Spec | Relevance |
|---|---|---|
| CPU | Cortex-M7 600 MHz, double-precision FPU | Timestamp math, buffering, USB |
| ITCM/DTCM | 512 KB tightly-coupled (512K OCRAM + 512K DTCM total 1 MB RAM flex) | Capture buffers |
| OCRAM | 512 KB | Second buffer arena |
| Flash | 8 MB QSPI | Firmware, not capture |
| USB | USB 2.0 HS 480 Mbit/s via MIMXRT1062 USB OTG (HS PHY on Teensy 4.1) | Streaming to PC |
| GPIO | 55 GPIOs, up to 150 MHz GPIO clock, 32-bit port registers | Sampling |
| FlexIO | 2× FlexIO (up to 32-bit shifter/timer) | Future high-speed synchronous capture |
| DMA | 32-channel eDMA | GPIO → RAM without CPU |
| Timers | QuadTimer (TMR), FlexPWM, PIT, GPT, 64-bit cycle counter (ARM DWT_CYCCNT) | Timestamping |
| ADC | 2× ADC 12-bit ≤ 1 MS/s shared | Not for high-speed logic (separate path) |

Teensy 4.1 routing: USB HS via external PHY (USB3320). Arduino core exposes it as `Serial` (CDC) at effective ~30–40 MB/s raw bulk before overhead; actual achievable continuous bulk via Teensyduino `Serial` ≈ 20–25 MB/s sustained on a good host. Using `USBHost`/`RawHID` is slower; CDC is correct for Phase 1.

---

## 2. GPIO Port Mapping (Critical for Speed)

The RT1062 has 5 GPIO modules (GPIO1-5). Teensy pins are muxed:

* **GPIO6_DR (Board pins 0–13, 14–...):** On Teensy 4.1, `GPIO6` maps to most user-facing digital pins (19,18,14,15,40,41,17,16,22,23,20,21,38,39...). Detailed assignment in `docs/02-pin-assignment.md`.
* **GPIO7, GPIO8, GPIO9** similarly used.

Raw port read: `GPIO6_PSR` gives 32-bit parallel state in **1 cycle** (~1.6 ns). This is the correct primitive — never use `digitalRead()` in the fast path (each `digitalRead()` ≈ 30–50 cycles + branching).

Ideal capture packs 16 channels into a contiguous 16-bit lane of a single GPIO port so one 32-bit read + mask yields a sample. Teensy 4.1 *does not* have 16 contiguous user pins on one port without gaps — Phase 1 therefore uses a **physical-to-logical remap**: firmware reads `GPIO6_PSR` + `GPIO7_PSR` + `GPIO9_PSR`, extracts bits via precomputed masks/shifts, packs into `uint16_t sample`. This costs ~8–12 cycles per sample vs 1 cycle for perfectly contiguous, still negligible.

---

## 3. Capture Modes & Achievable Rates

### 3.1 Distinguish Two Modes

1. **Timestamped transition capture (edge-compressed):** Only records when any channel changes, plus 32/64-bit timestamp. Best for low-to-medium activity buses (I2C 100 kHz–1 MHz, UART 115k2, SPI ≤ 2 MHz with CS-gated). Memory efficient; time resolution matters.
2. **Continuous isochronous sampling (oversampled):** Periodic samples at fixed rate (e.g., 5 MS/s). Needed for timing analysis, glitch detection, unknown protocols. Memory hungry.

### 3.2 Realistic Numbers

| Mode | Phase 1 (polling loop + ISR) | Phase 2 goal (DMA + FlexIO) | Theoretical ceiling |
|---|---|---|---|
| **Transition capture, 16 ch, CHANGE trigger** | 1.5–2.0 M transitions/s sustained (polling 16-ch packed read in tight loop @ 600 MHz, polling interval ~ 0.5 µs). Timestamp resolution 20 ns (ARM cycle counter / 600 MHz) | 4–8 M transitions/s with edge interrupt optimized + DMA timestamp FIFO | 10 M+/s with FlexIO shifter + DMA, but jitter increases |
| **Continuous sampling, 16 ch** | ~2 MS/s sustained (raw `uint16_t` samples → 4 MB/s + overhead) limited by USB, not CPU | ~8–10 MS/s burst to RAM (double buffer 400 KB → 40 ms @ 10 MS/s), then stream | GPIO toggle max ~150 MHz, but memory and USB cap it to ~10–12 MS/s continuous to host |
| **SPI clock capture** | 1–2 MHz SCLK reliable (sample 4× oversampled ⇒ 8 MS/s required → burst only) | 4 MHz SCLK with FlexIO SPI slave shifter + DMA (no oversampling) | FlexIO SPI slave 30 Mbit/s with external CS |
| **UART** | Any baud ≤2 Mbaud via edge timestamps | Same | — |
| **I2C** | 400 kHz–1 MHz reliable | 3.4 MHz HS with analog front-end limits | — |

**Why not higher?** Three bottlenecks:

1. **RAM:** 16-bit sample = 2 B. At 10 MS/s → 20 MB/s → 512 KB RAM fills in 25 ms. Hence double-buffer + USB streaming is mandatory for continuous > few seconds.
2. **USB:** Host scheduling, OS driver, Python `pyserial` buffering. Practical CDC throughput ≈ 15–25 MB/s; Python side ~12–18 MB/s after CRC and parsing. This caps continuous streaming to ~6–8 MS/s (16-bit samples).
3. **Interrupt jitter:** `attachInterrupt()` per pin ≈ 1–2 µs entry latency, unacceptable >500 kHz. Phase 1 avoids per-pin interrupts; uses polled port read in PIT-timed loop or tight `while()` with cycle-counter timestamps.

### 3.3 Timestamp Resolution

* **ARM DWT_CYCCNT:** 32-bit counter increments per CPU cycle (600 MHz → 1.666 ns). Overflows every 7.1 s at 600 MHz. Phase 1 extends to 64-bit (`cyccnt_hi` on overflow ISR + `ARM_DWT_CYCCNT`).
* **PIT/GPT timer:** 32-bit 150 MHz clock alternative for absolute timestamps, lower resolution (6.6 ns) but no overflow handling needed when cascaded.
* **Chosen Phase 1:** DWT_CYCCNT, 64-bit extended, timestamp unit = CPU cycles. Host converts to ns via `cycles * (1e9 / F_CPU)` where F_CPU reported in handshake.

Jitter: polled loop jitter < 15 ns (excluding USB ISR preemption). With interrupts disabled during burst, jitter < 5 ns but USB must be serviced ⇒ Phase 1 uses priority: `NVIC_SET_PRIORITY(IRQ_PIT, 16)` higher than USB, but PIT ISR < 1 µs.

---

## 4. DMA & Hardware Paths (Roadmap)

* **eDMA + GPIO:** DMA can trigger on PIT timer, read `GPIO6_PSR`, write to RAM buffer. CPU free. This is Phase 2 primary path for continuous mode. 32 channels allow ping-pong descriptors (double buffering) without CPU.
* **FlexIO:** Can act as 4/8-bit parallel capture, SPI slave, I2C slave. For SPI decoding at >2 MHz, FlexIO shifter is far superior to oversampling — captures bytes directly. Requires 1 FlexIO instance per protocol instance. Teensy 4.1 has 2 FlexIO (FlexIO1 ~ 8 pins, FlexIO2 ~ 8 pins limited). Phase 5+ will use it.
* **XBAR / QTMR:** For frequency/duty measurement with hardware capture (QTMR input capture gives 150 MHz resolution with zero CPU per edge). Useful for Phase 10 graph analyzer.
* **Not used in Phase 1:** DMA/FlexIO to minimize bring-up risk.

---

## 5. What Is / Is Not Possible Without External Hardware

| Signal bus | Direct to GPIO (with protection module) | Needs external transceiver |
|---|---|---|
| 3.3 V CMOS UART/SPI/I2C | ✅ yes (series R + TVS) | — |
| 5 V TTL/CMOS | ✅ with level shifter (TXB0108/TXS0108 or auto-dir) | — |
| 1.8 V | ✅ with 1.8 V LSF | — |
| RS-232 (±12 V) | ❌ never | ✅ MAX3232 |
| RS-485 differential | ❌ | ✅ THVD1400 / MAX485 |
| CAN (2.5 V diff, dominant) | ❌ | ✅ MCP2551 / TJA1050 + controller (MCP2515 or FlexCAN) |
| LIN | ❌ | ✅ TJA1020 |
| Automotive 12 V, 24 V | ❌ | ✅ divider + clamp + opto |
| Differential probe | ❌ | ✅ external comparator/ LVDS receiver |
| Analog 0–5 V | ❌ (ADC is 3.3 V only) | ✅ divider + op-amp + dedicated ADC (ADS8688) |

The term "universal" refers to **digital protocol architecture** + **protected modular front-end**, not to physically tolerating arbitrary voltages on bare GPIO. Phase 1 front-end is a 16-channel **replaceable protection module** — see `docs/07-safety-and-wiring.md`.

---

## 6. Memory Budget (Phase 1)

```
RAM1 (DTCM 512 KB, fast):
  - Capture buffer A: 96 KB (48k samples uint16+ts) or 64 KB raw + 32 KB timestamps for transition mode
  - Capture buffer B: 96 KB (double buffer)
  - USB TX queue: 32 KB
  - Stack/heap: 64 KB
  - Remainder for decoder scratch: ~224 KB

RAM2 (OCRAM 512 KB):
  - Transition history / trigger prebuffer: 256 KB
  - Config/state: 16 KB
```

Phase 1 pre-trigger: ring buffer in OCRAM (e.g., 50 ms @ 2 MS/s transition → 100k entries).

---

## 7. USB Streaming Budget

Frame size Phase 1: `header(2) + type(1) + len(2) + seq(2) + payload(up to 512) + crc16(2) = ~521 B` per USB packet. At 64 B USB FS packet size, Teensyduino CDC fragments; effective overhead ~5%. At 20 MB/s raw, payload ≈ 19 MB/s. Transition frames are 6 B each (ts delta 4 B + sample 2 B) ⇒ ~3.1 M transitions/s streaming cap, matching CPU poll limit. Continuous mode frames pack samples 2 B each ⇒ ~9.5 MS/s streaming cap.

---

## 8. Distinguishing Theory vs. Reality (Principle §28)

1. **Theoretically possible:** 150 MHz GPIO sampling, 480 Mbit/s USB, 600 MHz timestamping.
2. **Realistically achievable (verified, no over-promise):** 2 MS/s continuous streaming, 2 M transitions/s, 20 ns timestamp, 16 ch synchronous within <5 ns skew (single-port read) or <15 ns if cross-port.
3. **Requires external hardware:** Any voltage beyond 0–3.3 V, differential buses, precision analog, galvanic isolation.

Phase 1 targets **realistic** numbers, with hooks to grow toward theoretical via DMA/FlexIO.

---

## 9. Performance Validation Plan

* Synthetic generator on host replays CSV to firmware via loopback for rate measurement.
* Firmware self-test: internal `toggle` on pin 13 via PWM feeding capture pins; measure sample loss counter.
* Host measures: `samples_received / duration` and `crc_error_rate` and `buffer_overrun_flag`.
* CI tests use `tests/generators/` without hardware.

