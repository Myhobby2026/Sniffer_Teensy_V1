# USB Protocol Specification — Sniffer Teensy V1

**Transport:** USB 2.0 HS CDC-ACM (Teensy `Serial`) — 115200 baud ignored (USB HS), host opens port at any baud, 8N1, no flow control. Framed binary on top.

**Endianness:** Little-endian for all multi-byte fields.

**Version:** 1.0 (Phase 1)

---

## 1. Framing

Every packet on the wire:

```
Offset  Size  Field
0       2     MAGIC   = 0x534E ("SN")
2       1     TYPE    (see §3)
3       2     LENGTH  payload length 0..1024 (uint16 LE)
5       2     SEQ     uint16 LE, wraps, host and device have independent counters
7       N     PAYLOAD (LENGTH bytes)
7+N     2     CRC16   CCITT-FALSE (poly 0x1021, init 0xFFFF) over TYPE+LENGTH+SEQ+PAYLOAD
```

Total max frame = 2+1+2+2+1024+2 = 1033 B. CDC may split across USB transactions — receiver must resync on MAGIC.

**Resync:** Receiver scans for MAGIC. LENGTH validated ≤1024, CRC checked. Bad CRC → discard frame, increment `stats.crcErrors`.

**No COBS** in Phase 1; MAGIC inside payload is okay because LENGTH delimits; but payload containing 0x534E won't confuse resync after CRC failure — still robust. Future may add COBS if needed.

---

## 2. CRC16 Reference

```python
def crc16_ccitt(data: bytes, poly=0x1021, init=0xFFFF) -> int:
    crc = init
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ poly) if (crc & 0x8000) else (crc << 1)
            crc &= 0xFFFF
    return crc
```

Covers bytes [TYPE .. PAYLOAD].

---

## 3. Packet Types

| TYPE | Name | Dir | Description |
|---|---|---|---|
| 0x01 | HELLO | H→D | Host handshake, app version |
| 0x02 | HELLO_ACK | D→H | Device handshake, fw version, caps |
| 0x03 | GET_STATUS | H→D | Poll status |
| 0x04 | STATUS | D→H | Periodic status (state, buffer fill, overruns) |
| 0x05 | CONFIG_CHANNELS | H→D | 16-channel config |
| 0x06 | CONFIG_CAPTURE | H→D | Capture mode, rate, trigger |
| 0x07 | CMD_START | H→D | Start capture |
| 0x08 | CMD_STOP | H→D | Stop capture |
| 0x09 | CMD_RESET | H→D | Soft reset buffers |
| 0x0A | EVT_STARTED | D→H | Capture started ack |
| 0x0B | EVT_STOPPED | D→H | Capture stopped, reason |
| 0x0C | DATA_TRANSITION | D→H | Batch of transition records |
| 0x0D | DATA_SAMPLE | D→H | Batch of continuous samples |
| 0x0E | EVT_ERROR | D→H | Error report (code, text) |
| 0x0F | PING | H↔D | Echo for latency |
| 0x10 | PONG | D→H | Echo reply |

Dir: H→D host to device, D→H device to host, H↔D either.

---

## 4. Payload Definitions

### 4.1 HELLO (0x01)

```
offset  size  field
0       4     APP_VERSION  uint32  e.g. 0x00010000 = 1.0.0 (major.minor.patch)
4       4     HOST_CAPS    uint32  bitmask (reserved 0 for now)
8       16    HOST_ID      ASCII, zero-padded, e.g. "SnifferGUI v1.0"
```

### 4.2 HELLO_ACK (0x02)

```
0   4   FW_VERSION   uint32
4   4   HW_VERSION   uint32  (0x00010000 = rev 1.0)
8   4   F_CPU_HZ     uint32  e.g. 600000000
12  4   RAM_BYTES    uint32
16  2   NUM_CHANNELS uint16  =16
18  1   CARTRIDGE_ID uint8   (0..3)
19  1   CAPABILITIES uint8   bit0=TRANSITION, bit1=CONTINUOUS, bit2=DMA, bit3=FlexIO
20  32  DEVICE_UID   ASCII / serial
```

### 4.3 CONFIG_CHANNELS (0x05)

```
For each ch 0..15 (16 * 6 B =96 B):
  0  1  ENABLED    uint8 (0/1)
  1  1  MODE       uint8 0=DISABLED,1=DIGITAL,2=ANALOG_FUTURE
  2  1  TRIGGER    uint8 0=NONE,1=RISING,2=FALLING,3=BOTH
  3  1  PULL       uint8 0=NONE,1=PULLUP,2=PULLDOWN (if hardware supports)
  4  2  LABEL_LEN + LABEL (not here — labels stay host-side)
```

Simplified Phase 1: payload is 16 bytes ENABLED mask + 16 bytes TRIGGER mask.

Actual Phase 1 payload:
```
0  2  ENABLE_MASK  uint16 LE bit i = ch i enabled
2  2  TRIGGER_RISING_MASK uint16
4  2  TRIGGER_FALLING_MASK uint16
6  1  PULL_MODE 0..2
```

### 4.4 CONFIG_CAPTURE (0x06)

```
0  1  MODE         0=TRANSITION (edge-compressed), 1=CONTINUOUS
1  1  TRIGGER_MODE 0=IMMEDIATE,1=PATTERN,2=PROTOCOL (future)
2  4  SAMPLE_RATE_HZ uint32 (only for CONTINUOUS, e.g. 1000000)
6  4  PRE_TRIGGER_MS uint32
10 4  POST_TRIGGER_MS uint32
14 2  TRIGGER_PATTERN_MASK uint16
16 2  TRIGGER_PATTERN_VALUE uint16
18 1  TRIGGER_EDGE_CH 0..15 or 0xFF=none
19 1  TRIGGER_EDGE_TYPE 0/1/2
```

### 4.5 CMD_START / CMD_STOP / CMD_RESET — no payload (LENGTH=0)

### 4.6 STATUS (0x04) — D→H 16 B

```
0  1  STATE 0=IDLE,1=ARMED,2=CAPTURING,3=OVERFLOW,4=ERROR
1  1  FILL_PCT 0..100 (buffer fill)
2  2  PENDING_BYTES uint16 pending to send
4  4  TRANSITIONS_CAPTURED uint32 (since start)
8  4  BYTES_STREAMED uint32
12 2  CRC_ERRORS uint16
14 2  OVERRUNS uint16
```

### 4.7 DATA_TRANSITION (0x0C)

Batch of delta-encoded transitions. Timestamps are **delta from previous** compressed to save bandwidth.

```
Payload:
0  8  BASE_TIMESTAMP uint64 LE  absolute DWT cycles of first record
8  2  COUNT uint16 LE number of records
10 ... RECORDS (COUNT * 6 B):
    0 2 SAMPLE uint16 LE  packed 16-ch state AFTER transition
    2 4 DELTA_CYCLES uint32 LE cycles since previous (first record delta=0)
```

Host reconstructs: `ts[i] = BASE + sum(delta[0..i])`.

Max batch ~85 records (512 B payload) → frame fits 1024.

### 4.8 DATA_SAMPLE (0x0D) — continuous mode

```
0 8 BASE_TIMESTAMP uint64
8 2 COUNT uint16
10  COUNT*2 bytes SAMPLES (uint16 LE each, periodic)
```

Rate is known from CONFIG_CAPTURE.

### 4.9 EVT_ERROR (0x0E)

```
0 2 CODE uint16
2 2 TEXT_LEN uint16
4 TEXT_LEN bytes ASCII
```

Codes: 1=BUFFER_OVERFLOW,2=INVALID_CONFIG,3=USB_OVERRUN,4=TRIGGER_TIMEOUT, ...

### 4.10 PING/PONG

```
PING payload: 8 B nonce uint64
PONG payload: same nonce echo
```

---

## 5. Session Flow

```
Host open port → wait 200 ms → send HELLO
Device → HELLO_ACK (within 500 ms) else host retries
Host → CONFIG_CHANNELS, CONFIG_CAPTURE
Host → CMD_START
Device → EVT_STARTED + streaming DATA_* + periodic STATUS (2 Hz)
Host → CMD_STOP (or device auto EVT_STOPPED on trigger completion)
Host validates CRC, reassembles, writes .stcap
```

**Host must handle:** device disconnect (SerialException), timeout waiting HELLO_ACK (show "No device"), overflow EVT_ERROR (warn user, keep data).

---

## 6. Versioning

`FW_VERSION` and `APP_VERSION` major must match for streaming; minor mismatch allowed with warning. `CAPABILITIES` tells host which modes device actually supports — app greys out unsupported.

---

## 7. Python API

See `app/device/protocol.py` for `Packet`, `encode()`, `decode_stream()`, `crc16()` and `app/device/transport.py` for `SerialTransport`.

---

## 8. Future Extensions (Reserved TYPE ranges)

* 0x20–0x2F Spontaneous protocol-decoded packets (if decoded on-device)
* 0x30–0x3F Analog samples
* 0x80+ Vendor experiments

Forward compat: unknown TYPE → ignore but still CRC-check.

