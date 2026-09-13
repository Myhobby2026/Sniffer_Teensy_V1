# Plugin Development Guide

This document defines how to add a new protocol decoder without modifying core.

## 1. Interface

See `app/plugins/base.py`:

```python
from app.plugins.base import Decoder, register
from typing import Iterable, List, Dict, Tuple

class MyDecoder(Decoder):
    name = "my_protocol"
    description = "My proprietary synchronous bus"

    def decode(self, transitions: Iterable[Tuple[int,int,int]], config: Dict) -> List[Dict]:
        # transitions: (abs_cycles, sample, delta)
        # config: {"sclk_ch":0, "mosi_ch":1, ...}
        # return list of packets: {"t_start":cycles, "t_end":cycles, "data":bytes, "fields":{}}
        ...

    def auto_detect(self, transitions, f_cpu=600_000_000) -> Tuple[bool,float,str]:
        # return (is_candidate, confidence 0-100, reason)
        # MUST NOT claim 100% without strong evidence
        # Example: "Likely SPI Mode 0 — 82% (clock periodic, CS framing, 8-bit words)"
        return True, 65.0, "Periodic clock 500 kHz, 8-bit framed by CS"
```

Register via:

```python
register(MyDecoder())
```

Or use discovery: place decoder in `app/plugins/my_protocol/plugin.py` and add `plugins/my_protocol/plugin.json`:

```json
{
  "name": "my_protocol",
  "version": "1.0.0",
  "entry": "plugin:decoder",
  "description": "My protocol"
}
```

App scans `app/plugins/*/plugin.json` on startup using `importlib`.

## 2. Transition Model

Capture is transition-compressed: `sample` is 16-bit packed state *after* the edge, `delta` is cycles since previous edge. Host `CaptureReader.get_all_transitions()` expands to absolute cycles. Decoders work on expanded list.

Convert to seconds: `t = (cycles - t0)/f_cpu`. Use `f_cpu` from capture header.

## 3. SPI Example (Phase 5 pattern)

See `tests/generators/spi_generator.py` for synthetic.

Decoder logic (simplified):

1. Identify `SCLK`, `MOSI`, `MISO`, `CS` channels from config.
2. Find CS framing: `CS` falling → rising is one transaction.
3. Inside transaction, sample `MOSI/MISO` on configured clock edge (Mode 0: rising, Mode 1: rising..., etc.).
4. Group bits into bytes (MSB/LSB per config, word size).
5. Output packets with `t_start`, `t_end`, `mosi_bytes`, `miso_bytes`.

## 4. Auto-Detection Guidelines

Analyze captured signals and *suggest*, never assert:

* Number of active channels
* Clock-like periodic signal (FFT or interval histogram)
* Edge timing, bit timing
* START/STOP patterns
* ACK patterns
* Baud candidates (for UART)
* SPI clock relationships, CS behavior
* I2C addressing patterns

Display: `"Likely SPI Mode 0 — confidence 82%"` not `"SPI detected"`.

Implementation: `auto_detect()` returns `confidence` 0-100. UI shows sorted candidates. User can override.

## 5. Testing a Decoder

* Generate synthetic capture: `python tests/generators/spi_generator.py --out /tmp/synth.stcap`
* Write unit test:

```python
from app.capture.reader import CaptureReader
from app.plugins.spi.plugin import SPIDecoder  # future

r = CaptureReader("/tmp/synth.stcap")
trans = r.get_all_transitions()
dec = SPIDecoder()
pkts = dec.decode(trans, {"sclk":0,"mosi":1,"miso":2,"cs":3,"mode":0})
assert len(pkts)==5
assert pkts[0]["mosi"] == bytes([0xA5,0x00])
cand,conf,reason = dec.auto_detect(trans)
assert cand and conf>50
```

## 6. UI Integration

Decoders can expose:

* `config_schema`: JSON schema for settings page (channels, baud, mode...)
* `packet_view_columns`: `[(name, width), ...]` for protocol data view
* `annotation_renderer(canvas, packet, y, x_scale)`: draws hex overlays on waveform

Phase 11 Plugin Manager will list installed decoders, enable/disable, and hot-load.

## 7. Distribution

Keep decoders isolated: `app/plugins/<protocol>/` contains `plugin.py`, `decoder.py`, `tests/`, `README.md`. Core never imports them directly — discovery loads them.

This keeps the instrument *future-proof*: new buses (CAN, LIN, Manchester, NRZ, PWM, custom) ship as plugins.

