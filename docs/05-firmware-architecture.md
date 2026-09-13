# Firmware Architecture — Teensy 4.1

## 1. Folder Layout

```
firmware/
  platformio.ini
  README.md
  include/
    version.h        // FW_VERSION, HW_VERSION, build timestamp
    config.h         // Compile-time defaults, pin map, buffer sizes
    usb_protocol.h   // Packet defs, CRC, encode/decode
    channels.h       // Channel abstraction, physical→logical map
    capture.h        // Capture engine state machine
    buffers.h        // Double buffers, ring for pre-trigger
    timing.h         // DWT cycle counter, 64-bit extension
    diagnostics.h    // Self-test, stats, error codes
  src/
    main.cpp         // setup()/loop(), state machine dispatch
    usb_protocol.cpp
    channels.cpp
    capture.cpp
    buffers.cpp
    timing.cpp
    diagnostics.cpp
```

Modularity rule: `capture.cpp` never touches `Serial` directly — it pushes to `buffers` queue; `usb_protocol.cpp` drains queue. `channels.cpp` owns pin init and fast read.

## 2. State Machine

```
IDLE ──HELLO──> READY ──CONFIG──> ARMED ──START──> CAPTURING ──STOP/OVERFLOW──> IDLE
                  ^                    |               |
                  └──── RESET ─────────┴───────────────┘
```

State is reported in `STATUS` packets (2 Hz).

## 3. Capture Paths

### 3.1 Transition Mode (Phase 1)

* Loop: `while (capturing) { sample = readChannelsPacked(); if (sample != last) { ts=now64(); pushTransition(ts, sample); last=sample; } }`
* `now64()` reads `DWT_CYCCNT` + overflow extension (overflow ISR increments `hi` every 7.1 s).
* No interrupts per edge → minimal jitter. Polling loop at ~600 MHz runs ~50 M reads/s worst-case, but USB handling interleaves → effective ~2 M transitions/s.
* Pre-trigger: ring buffer in OCRAM stores last N transitions before trigger fires (if trigger != immediate). On trigger, flush ring to USB queue first.

### 3.2 Continuous Mode (Phase 1 limited, Phase 2 DMA)

* PIT timer triggers at `SAMPLE_RATE_HZ`. ISR or polling reads sample and pushes.
* Phase 1 continuous: simple PIT interrupt at up to 1 MHz reliable; beyond needs DMA.

## 4. Buffering

* **Double buffer:** Two 96 KB buffers; capture writes to inactive buffer; when full, swap and signal USB to send it. Prevents allocation in fast path.
* **Ring buffer for pre-trigger:** 256 KB circular queue; overwritten until trigger.
* **USB TX queue:** 32 KB FIFO of framed packets awaiting `Serial.write()`.

All buffers statically allocated (`DMAMEM` or `PROGMEM` attributes where useful), no `malloc` in fast path.

## 5. USB Transport

* `Serial` (CDC) buffered; `Serial.availableForWrite()` checked before push.
* Framing: `usb_protocol::encodePacket(type, payload, seq) → bytes with MAGIC+CRC`.
* RX parsing: byte-by-byte state machine resyncing on MAGIC, validating length/CRC, dispatching to `handleHostPacket()`.

## 6. Timing Critical Sections

* `readChannelsPacked()` is `inline __attribute__((always_inline))` and uses `__builtin` barriers.
* Fast loop disables interrupts briefly? Phase 1 keeps interrupts enabled to service USB; measured jitter acceptable. Option to `__disable_irq()` for 100-sample bursts is documented.
* Timestamp read is `uint64_t ts = ((uint64_t)cyccnt_hi << 32) | ARM_DWT_CYCCNT;` with double-read to handle overflow race (like `micros()`).

## 7. Diagnostics

* Boot: blink LED, print `HELLO_ACK` on HELLO; if no HELLO within 2 s, idle.
* `PING` → `PONG` echo for host RTT.
* Stats: `transitionsCaptured`, `bytesStreamed`, `crcErrors`, `overruns`, `maxLoopUs`.
* `CMD_RESET` clears buffers and stats.

## 8. Build

PlatformIO (`platformio.ini`):

```ini
[env:teensy41]
platform = teensy
board = teensy41
framework = arduino
build_flags = -DF_CPU=600000000 -DUSB_SERIAL -O2
```

Alternative: Arduino IDE with Teensyduino.

See `firmware/README.md` for upload instructions.

## 9. Phase 1 Limitations & Phase 2 Hooks

* Phase 1: no DMA, no FlexIO, polling only, single trigger type (immediate + simple pattern). Code is structured so `capture.cpp` has `CaptureStrategy` interface:
  ```cpp
  struct CaptureStrategy { virtual void begin(const CaptureConfig&) =0; virtual void poll() =0; };
  struct PollingStrategy : CaptureStrategy {...};
  struct DmaStrategy : CaptureStrategy {...}; // future
  ```
* Adding DMA only touches `capture.cpp` + `buffers.cpp`.

