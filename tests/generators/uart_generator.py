#!/usr/bin/env python3
"""Synthetic UART generator — TX=CH0 (idle high), 115200 8N1"""
import argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from app.capture.writer import CaptureWriter

CH_TX=0

def generate_uart_capture(out_path: str, text="Hello", f_cpu=600_000_000, baud=115200):
    ch_meta=[{"id":i,"label":lbl,"enabled":i==0,"color":c,"physPin":i} for i,(lbl,c) in enumerate([("UART_TX","#FFD700")] + [(f"CH{i}","#9E9E9E") for i in range(1,16)])]
    bit_cycles=int(f_cpu/baud)
    w=CaptureWriter(out_path, f_cpu=f_cpu, channels_meta=ch_meta, notes=f"Synthetic UART {baud} {text}")
    w.open()
    cur=1<<CH_TX
    cycles=0
    timeline=[(cycles,cur)]
    def set_bit(v):
        nonlocal cur
        if v: cur|=1<<CH_TX
        else: cur&=~(1<<CH_TX)
    def after(d):
        nonlocal cycles
        cycles+=d
        timeline.append((cycles,cur))
    # idle gap
    after(bit_cycles*2)
    for ch in text:
        byte=ord(ch)
        # start bit low
        set_bit(0); after(bit_cycles)
        for bit in range(8):
            set_bit((byte>>bit)&1); after(bit_cycles)
        # stop bit high
        set_bit(1); after(bit_cycles)
        # inter-byte gap
        after(bit_cycles)
    records=[]
    base=timeline[0][0]
    prev=timeline[0][0]
    for i,(c,s) in enumerate(timeline):
        delta=c-prev if i else 0
        records.append((s,delta))
        prev=c
    w.add_transitions(base, records)
    w.close()
    print(f"Generated {out_path} UART {text}")

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--out", default="/tmp/synth_uart.stcap")
    ap.add_argument("--text", default="Hello")
    args=ap.parse_args()
    generate_uart_capture(args.out, text=args.text)
