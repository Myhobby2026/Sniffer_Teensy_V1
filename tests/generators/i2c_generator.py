#!/usr/bin/env python3
"""Synthetic I2C generator — SDA=CH0, SCL=CH1"""
import argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from app.capture.writer import CaptureWriter

CH_SDA=0
CH_SCL=1

def generate_i2c_capture(out_path: str, f_cpu=600_000_000, scl_hz=100_000):
    ch_meta=[{"id":i,"label":lbl,"enabled":i<2,"color":c,"physPin":i} for i,(lbl,c) in enumerate([("SDA","#FF5C5C"),("SCL","#00BFFF")] + [(f"CH{i}","#9E9E9E") for i in range(2,16)])]
    half=int(f_cpu/scl_hz/2)
    w=CaptureWriter(out_path, f_cpu=f_cpu, channels_meta=ch_meta, notes="Synthetic I2C")
    w.open()
    cur= (1<<CH_SDA)|(1<<CH_SCL)  # idle high
    cycles=0
    timeline=[(cycles,cur)]
    def set_bit(ch,val):
        nonlocal cur
        if val: cur|=1<<ch
        else: cur&=~(1<<ch)
    def after(d):
        nonlocal cycles
        cycles+=d
        timeline.append((cycles,cur))
    # START: SDA falling while SCL high
    set_bit(CH_SDA,0); after(half)
    set_bit(CH_SCL,0); after(half)
    # 7-bit addr 0x50 + R/W 0
    addr=0x50
    bits=[ (addr>>6)&1,(addr>>5)&1,(addr>>4)&1,(addr>>3)&1,(addr>>2)&1,(addr>>1)&1,(addr>>0)&1,0]  # 0 write
    for b in bits:
        set_bit(CH_SDA,b); after(half//2)
        set_bit(CH_SCL,1); after(half)
        set_bit(CH_SCL,0); after(half//2)
    # ACK from slave (0)
    set_bit(CH_SDA,0); after(half//2)
    set_bit(CH_SCL,1); after(half)
    set_bit(CH_SCL,0); after(half//2)
    # data bytes 0xAB,0xCD
    for byte in [0xAB,0xCD]:
        for bit in range(7,-1,-1):
            set_bit(CH_SDA,(byte>>bit)&1); after(half//2)
            set_bit(CH_SCL,1); after(half)
            set_bit(CH_SCL,0); after(half//2)
        # ACK
        set_bit(CH_SDA,0); after(half//2)
        set_bit(CH_SCL,1); after(half)
        set_bit(CH_SCL,0); after(half//2)
    # STOP: SDA rising while SCL high
    set_bit(CH_SDA,0); after(half//2)
    set_bit(CH_SCL,1); after(half)
    set_bit(CH_SDA,1); after(half)
    # to records
    records=[]
    base=timeline[0][0]
    prev=timeline[0][0]
    for i,(c,s) in enumerate(timeline):
        delta=c-prev if i else 0
        records.append((s,delta))
        prev=c
    w.add_transitions(base, records)
    w.close()
    print(f"Generated {out_path} I2C")

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--out", default="/tmp/synth_i2c.stcap")
    args=ap.parse_args()
    generate_i2c_capture(args.out)
