# BOM — Sniffer Teensy V1 Carrier (2L, 16-ch, CARRIER-3V3 integrated)

**Qty per board. Prices Sep 2025 (JLC/LCSC low-volume). Teensy not included.**

| Ref | Value | Footprint | Qty | MPN / LCSC | Unit | Notes |
|---|---|---|---|---|---|---|
| U1 | Teensy 4.1 | 2×14 2.54 (socket) | 1 | PJRC TEENSY41 | $29.50 | Socket: Samtec SSW-114-01-T-S ×2 |
| J1 | Box header 2×10 shrouded | IDC Wurth 61201021621 | 1 | C560919 | $0.65 | Main 16-ch + GND, key up |
| J2a/J2b | Female 14p 2.54 | Sockets | 2 | C49202 | $0.45 ea | For Teensy |
| R330_0-15 | 330 Ω 1% 0.25W | 0603 | 16 | Yageo RC0603JR-07330RL LCSC C25804 | $0.02 | Current limit |
| R100_0-15 | 100 Ω 1% | 0603 | 16 | Yageo RC0603JR-07100RL C25819 | $0.02 | Damping |
| C_NP | 100 pF C0G 50V | 0603 | 16 | Samsung CL10C101JB8 C2048 | $0.04 | DNP (populate for <2 MHz) |
| U2-U5 | PRTR5V0U4Y 4-ch TVS | SOT-457 | 4 | Nexperia PRTR5V0U4Y C20922 | $0.55 | 16 ch total |
| D1-D8 | BAT54S | SOT-23 | 8 | ON BAT54S C8599 | $0.06 | Dual Schottky |
| R_ID1/2 | 10 k | 0603 | 2 | RC0603JR-07103RL C25803 | $0.02 | ID straps |
| C_ID1/2 | 100 nF X7R 50V | 0603 | 2 | CL10B104KO8 C28164 | $0.04 | ID debounce |
| FB1 | Ferrite 600Ω@100MHz | 0805 | 1 | Murata BLM21PG601 C3470 | $0.18 | VIN filter |
| C_BULK | 10 µF 16V X7R | 0805 | 3 | Samsung CL21A106KOQNNNG C23744 | $0.08 | Bulk |
| C_DEC | 100 nF 50V X7R | 0603 | 8 | Samsung CL10B104KO8 | $0.04 | Decoupling |
| TPs | Loop testpoint | Keystone 5019 | 2 | C502125 | $0.15 | 3.3V/GND |
| H_M3 | Mounting hole M3 3.2mm | NPTH 6mm pad | 4 | — | — | |
| PCB | 100×65×1.6 FR-4 2L ENIG black | — | 1 | JLC 2L | ~$2.40 (5pcs) | |

**Totals:**
- PCB 5 pcs (JLC, ENIG, black): ~$12 (2.40×5) + shipping
- Parts per board (without Teensy): **~$8.50**
- With Teensy 4.1: **~$38**

**Alternatives / DNP:**
- Populate `C_NP` only if you want ~4 MHz low-pass.
- Add `J3` (1×4 I2C), `J4` (1×4 CAN), `J5` (2×4 SPI2) — headers, $0.15 ea, DNP if not using external ADC/CAN.
- For 5V cartridge variant, do NOT load this BOM — use separate `CARRIER-5V` daughter board with 2× TXS0108E (0.1 µF each, OE 10k).

**LCSC cart export:** Search MPN, add to cart, export CSV — KiCad plugin `JLCPCB Tools` can auto-place.

**Assembly note:** Stencil for top only (B.Cu is GND plane, no parts bottom). Reflow at 245 °C, hand-solder headers/Teensy socket after.

