#!/usr/bin/env python3
"""Synthetic SPI generator — creates .stcap without hardware.
Use for decoder tests and GUI demo.
SPI: CH0=SCLK, CH1=MOSI, CH2=MISO, CH3=CS (active low)
"""
import argparse, struct, random
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.capture.writer import CaptureWriter

# Channel assignments
CH_SCLK=0
CH_MOSI=1
CH_MISO=2
CH_CS=3

def generate_spi_capture(out_path: str, transactions=5, f_cpu=600_000_000, sclk_hz=500_000, mode=0):
    # Mode 0: CPOL=0 CPHA=0 — sample on rising, idle low
    cpol = (mode>>1)&1
    cpha = mode &1
    # timing: half period in cycles
    half_period_cycles = int(f_cpu / sclk_hz / 2)
    if half_period_cycles < 60:
        half_period_cycles = 60
    idle = 20 * half_period_cycles  # gap between transactions

    # channel meta
    ch_meta=[{"id":i,"label":lbl,"enabled":i<4,"color":c,"physPin":i} for i,(lbl,c) in enumerate([("SCLK","#00BFFF"),("MOSI","#FF5C5C"),("MISO","#7FFF7F"),("CS","#FFD700")] + [(f"CH{i}","#9E9E9E") for i in range(4,16)])]

    w=CaptureWriter(out_path, f_cpu=f_cpu, channels_meta=ch_meta, app_version="1.0.0-gen", notes=f"Synthetic SPI mode{mode} {transactions} transactions")
    w.open()
    # build transition timeline as (abs_cycles, sample)
    timeline = []
    cur_sample = 0
    # idle state: SCLK = CPOL, CS=1, MOSI/MISO=0
    if cpol:
        cur_sample |= 1<<CH_SCLK
    cur_sample |= 1<<CH_CS  # CS high
    cycles = 0
    timeline.append((cycles, cur_sample))

    def set_bit(ch, val):
        nonlocal cur_sample, cycles
        if val:
            cur_sample |= 1<<ch
        else:
            cur_sample &= ~(1<<ch)

    def append_after(delta):
        nonlocal cycles
        cycles += delta
        timeline.append((cycles, cur_sample))

    for t in range(transactions):
        # select varying data
        mosi_bytes = [0xA5, t &0xFF] if t%2==0 else [0x5A, (0xFF-t)&0xFF]
        miso_bytes = [0x12 + t, 0x34 + t]
        # CS low
        set_bit(CH_CS, 0)
        append_after(half_period_cycles)
        # clock out 16 bits (2 bytes)
        bits_mosi = []
        for b in mosi_bytes:
            for bit in range(7,-1,-1):
                bits_mosi.append((b>>bit)&1)
        bits_miso = []
        for b in miso_bytes:
            for bit in range(7,-1,-1):
                bits_miso.append((b>>bit)&1)
        # For each bit, drive MOSI/MISO then toggle SCLK
        # Mode 0: data set on falling, sample on rising
        for i in range(len(bits_mosi)):
            # ensure SCLK low at start of bit (CPOL=0)
            set_bit(CH_MOSI, bits_mosi[i])
            set_bit(CH_MISO, bits_miso[i])
            append_after(half_period_cycles//2)  # data setup
            # SCLK rising (sample edge)
            set_bit(CH_SCLK, 1)
            append_after(half_period_cycles)
            # SCLK falling
            set_bit(CH_SCLK, 0)
            append_after(half_period_cycles//2)
        # CS high
        set_bit(CH_CS, 1)
        set_bit(CH_MOSI, 0)
        set_bit(CH_MISO, 0)
        append_after(idle)

    # Convert timeline (abs cycles) to transition records (delta compressed)
    # Timeline already is transitions where sample changes; but we need to emit only changes
    # Our timeline includes duplicate samples where we set same value? We already filtered? We emitted after each change, so each entry is new sample.
    # Build records
    records=[]
    base = timeline[0][0]
    prev_c = timeline[0][0]
    for abs_c, samp in timeline:
        delta = abs_c - prev_c if records else 0
        records.append((samp, delta))
        prev_c = abs_c
        # batch into 85 per packet + writer chunks
        if len(records) >= 500:
            w.add_transitions(base, records)
            # new base for next chunk is last abs_c
            base = abs_c + 0  # next batch base will be next abs_c
            records = []
            # trick: need to handle delta for first of next batch as 0? We'll set base correctly and delta 0 for first
            # So reset prev_c to next base
    if records:
        w.add_transitions(base, records)
    w.close()
    print(f"Generated {out_path}: {len(timeline)} transitions, {transactions} transactions")

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--out", default="/tmp/synth_spi.stcap")
    ap.add_argument("--transactions", type=int, default=5)
    ap.add_argument("--mode", type=int, default=0)
    ap.add_argument("--sclk", type=int, default=500000)
    args=ap.parse_args()
    generate_spi_capture(args.out, transactions=args.transactions, mode=args.mode, sclk_hz=args.sclk)
