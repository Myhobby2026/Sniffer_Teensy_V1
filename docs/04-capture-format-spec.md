# Capture Format Specification — `.stcap` v1

**Purpose:** Portable, replayable, forward-compatible binary capture. Written by host (not device). Device streams transition/sample packets; host muxes into this file.

---

## 1. File Structure

```
[FileHeader 128 B]
[Metadata JSON blob, length = header.metaLen]
[DataSection: sequence of ChunkHeaders + payloads]
[Footer 16 B optional hash]
```

All integers little-endian.

### 1.1 FileHeader (128 B)

```
Offset Size Field
0      4   MAGIC 0x53544341 ("STCA" — Sniffer Teensy CApture)
4      2   VERSION_MAJOR =1
6      2   VERSION_MINOR =0
8      8   CREATED_UNIX_MS uint64
16     4   META_LEN uint32 length of JSON metadata blob
20     4   RESERVED0
24     8   F_CPU_HZ uint64 (cycles → ns)
32     2   NUM_CHANNELS uint16
34     2   FLAGS uint16 bit0=hasTransitions bit1=hasSamples bit2=hasAnalog
36     8   TOTAL_TRANSITIONS uint64 (0 if continuous)
44     8   TOTAL_SAMPLES uint64
52     4   CAPTURE_MODE 0=TRANSITION,1=CONTINUOUS
56     4   SAMPLE_RATE_HZ (if continuous)
60     68  RESERVED (zero) to pad to 128 B
```

### 1.2 Metadata JSON

UTF-8 JSON, `META_LEN` bytes, not null-terminated. Example:

```json
{
  "appVersion": "1.0.0",
  "fwVersion": "1.0.0",
  "deviceUid": "TEENSY41-abc123",
  "cartridgeId": 0,
  "channels": [
    {"id": 0, "label": "SPI_CLK", "enabled": true, "color": "#00BFFF", "physPin": 2},
    {"id": 1, "label": "SPI_MOSI", "enabled": true, "color": "#FF5C5C", "physPin": 11}
  ],
  "trigger": {"mode": "immediate", "patternMask": 0, "patternValue": 0},
  "notes": "Sensor revision B, pressure 100kPa",
  "host": "Linux x86_64 Python 3.11"
}
```

Reader must tolerate unknown keys (forward compat). Writer must include `channels` for all 16 entries even if disabled.

### 1.3 DataSection

Sequence of chunks. Each chunk:

```
ChunkHeader 12 B:
  0 4  CHUNK_TYPE uint32 1=TRANSITION_BATCH,2=SAMPLE_BATCH,3=EVENT
  4 4  PAYLOAD_LEN uint32
  8 4  CRC32 uint32 (IEEE over payload only)

Payload: PAYLOAD_LEN bytes
```

#### Type 1 — TRANSITION_BATCH

Same wire format as USB DATA_TRANSITION payload (base timestamp delta-compressed), repacked for file:

```
0  8  BASE_CYCLES uint64 LE
8  2  COUNT uint16
10 ... COUNT records:
     0 2 SAMPLE uint16
     2 4 DELTA uint32
```

May contain multiple batches; total across file = TOTAL_TRANSITIONS.

Timestamps absolute: `cycles = BASE + Σ DELTA`, converted to ns: `ns = cycles * 1e9 / F_CPU_HZ`, or seconds `t = ns / 1e9`.

#### Type 2 — SAMPLE_BATCH

```
0 8 BASE_CYCLES uint64
8 4 COUNT uint32
12 4 SAMPLE_RATE_HZ uint32 (redundant, for chunk-level rate change)
16 COUNT*2 bytes samples little-endian uint16 each
```

#### Type 3 — EVENT

```
0 8 TIMESTAMP_CYCLES uint64
8 2 CODE uint16  1=TRIGGER_FIRED,2=OVERFLOW,3=MARKER
10 2 TEXT_LEN uint16
12 TEXT bytes UTF-8
```

***Ordering:*** Chunks are in capture time order.

### 1.4 Footer (optional 16 B)

```
0  4 MAGIC_FOOT 0x434F4F46 ("FOOC")
4  4 CRC32 of entire file preceding footer
8  8 TOTAL_BYTES uint64
```

Writer may omit footer when streaming to allow tail-following; reader handles EOF without footer.

---

## 2. Host Time vs Device Time

Device timestamps are DWT cycles since capture start (BASE is absolute cycles since boot; host subtracts first timestamp to get relative). Host may add wall-clock anchor: metadata `captureWallClockUnixMs` = host receive time of first packet; analysis uses relative time for correctness.

---

## 3. Export Formats

Converter `app/capture/writer.py` and `app/storage/` handle:

* **CSV:** `time_s, time_ns, sample_hex, ch0..ch15` — per transition/sample row. Optional filtered by channel.
* **TXT:** human-readable log.
* **JSON:** `{"header": {...}, "transitions": [{"t_ns":123, "sample":0x1A2B}, ...]}`
* **BIN raw:** dump of chunk payloads without framing.

Exports never alter `.stcap`; they are derived.

---

## 4. Forward Compatibility

* Reader ignores unknown CHUNK_TYPE (skip PAYLOAD_LEN).
* FileHeader VERSION_MAJOR increment = breaking change → reader must reject with clear message ("File requires newer app"). VERSION_MINOR increment = backward compatible.
* Metadata JSON unknown keys ignored.
* CRC failures: per-chunk CRC error → report but continue (skip chunk); file CRC mismatch → warn.

---

## 5. Performance Considerations

* Writer uses buffered I/O (64 KB) and batches transitions in 8 KB chunks; chunk size ≤ 64 KB.
* Reader uses memory-map for large files: `mmap` + zero-copy `struct` parsing; lazy decode (only decode batches needed for viewport in waveform).
* Transition count: 1 M transitions → ~6 MB payload + header → fine for Python. 10 M → ~60 MB, needs chunked processing (app does).

---

## 6. Python API

```python
from app.capture.writer import CaptureWriter
from app.capture.reader import CaptureReader

w = CaptureWriter("capture.stcap", f_cpu=600_000_000, channels=cfg)
w.add_transitions(base, samples, deltas)
w.close()

r = CaptureReader("capture.stcap")
hdr = r.header
for batch in r.iter_transition_batches():
    ...
```

See `app/capture/format.py` for constants, `writer.py`, `reader.py`.

---

## 7. Example Synthetic File (for tests)

`tests/generators/spi_generator.py` creates a synthetic SPI capture without hardware — useful for decoder tests and CI.

