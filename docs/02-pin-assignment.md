# Pin Assignment — Teensy 4.1 16-Channel Mapping

> Goal: sample 16 logical channels synchronously with minimal skew. Strategy: read two GPIO port registers (`GPIO6_PSR`, `GPIO9_PSR`) and repack.

## 1. Logical → Physical Mapping (Phase 1 default)

Logical channels `CH0 … CH15` are what the host UI shows. Physical Teensy pins are chosen for: (a) no conflict with USB, LED, SD card, (b) 5V-tolerant? none are — all 3.3 V, (c) not used by bootloader pins, (d) contiguous where possible.

| Logical | Teensy Pin | GPIO Module | Bit | Arduino name | Notes |
|---|---|---|---|---|---|
| CH0 | 0 | GPIO6 | 3 | AD_B0_03 | RX1 — available if UART not sniffed |
| CH1 | 1 | GPIO6 | 2 | AD_B0_02 | TX1 |
| CH2 | 2 | GPIO6 | 4 | EMC_04 | |
| CH3 | 3 | GPIO6 | 5 | EMC_05 | |
| CH4 | 4 | GPIO6 | 6 | EMC_06 | |
| CH5 | 5 | GPIO6 | 8 | EMC_08 | |
| CH6 | 6 | GPIO6 | 10 | B0_10 | |
| CH7 | 7 | GPIO6 | 17 | B1_01 | |
| CH8 | 8 | GPIO6 | 16 | B1_00 | |
| CH9 | 9 | GPIO6 | 11 | B0_11 | |
| CH10 | 10 | GPIO6 | 0 | B0_00 | CS on SD — shared but not used in Phase 1 (no SD) |
| CH11 | 11 | GPIO6 | 1 | B0_01 | MOSI SD — OK if SD disabled |
| CH12 | 12 | GPIO6 | 9 | EMC_09 | |
| CH13 | 13 | GPIO6 | 7 | EMC_07 | LED — weak drive, use but LED mirrors CH13 |
| CH14 | 32 | GPIO7 | 12 | B0_12 | Behind SD — free if SD off |
| CH15 | 33 | GPIO7 | 13 | B0_13 | |

*GPIO9 pins 14–23 are alternates for expansion; current map keeps all sampling on GPIO6 + two on GPIO7 to allow faster single-port read in future revision where CH14/15 moved to GPIO6 pins 36/37.*

**Why not pins 14–23 for CH0-7?** Those are GPIO9 on FlexIO route; they add DMA complexity. Current assignment yields only two ports → simple masking.

### 1.1 Reserved / Not Used for Capture (Phase 1)

| Teensy Pin | Use |
|---|---|
| 18,19 | I²C0 (SDA0/SCL0) — reserved for ADC/config EEPROM |
| 22,23 | FlexCAN2 / UART — reserved for CAN transceiver |
| 24–27 | SPI2 for ADS8688 (future) |
| 34–39 | SDIO / QSPI Flash — do not use while capturing to avoid bus contention |
|  LED (13) | Mirrors CH13 — acceptable |
| USB D+/D- | Dedicated |

## 2. Firmware Bit Extraction (Concept)

```cpp
inline uint16_t readChannelsPacked() {
  uint32_t psr6 = GPIO6_PSR; // 1 cycle
  uint32_t psr7 = GPIO7_PSR;
  uint16_t s = 0;
  s |= ((psr6 >> 3)  & 1) << 0;
  s |= ((psr6 >> 2)  & 1) << 1;
  s |= ((psr6 >> 4)  & 1) << 2;
  // ... 14 more lines precomputed
  s |= ((psr7 >> 12) & 1) << 14;
  s |= ((psr7 >> 13) & 1) << 15;
  return s;
}
```

Phase 2 will replace this with a 16-entry LUT + `pdep` equivalent or DMA scatter-gather.

## 3. Alternate Mapping for Bus-Specific Jigs

Host allows **channel reassignment** without firmware recompile: `channels[].physPin` is configurable. For example SPI jig: `CH0=SCLK@2, CH1=MOSI@11, CH2=MISO@12, CH3=CS@10`.

## 4. Connector

Recommend 2×10 0.1" box header, pinout:

```
1: CH0  2: GND
3: CH1  4: GND
...
15: CH7 16: GND
17: CH8 ... 32: CH15 etc
```

Use per-pair GND for signal integrity (16 signal + 8 ground). Ribbon cable length < 20 cm for >2 MHz.

## 5. Cartridge ID Straps

Pins 30 & 31 (GPIO6 bits) pulled to GND/VCC via cartridge resistor; firmware reads at boot:

* 00 = CARRIER-3V3
* 01 = CARRIER-5V
* 10 = CARRIER-RS232/485
* 11 = CARRIER-ANALOG

If not connected, defaults to 00.

## 6. Validation

Continuity test: firmware `DIAGNOSTICS_PIN_TOGGLE` command toggles each pin via `GPIO6_DR_TOGGLE` and host measures loopback on neighboring channel (requires loopback plug).

