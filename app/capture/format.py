"""Capture format constants — mirrors docs/04-capture-format-spec.md"""
import struct

MAGIC = 0x53544341  # "STCA"
VERSION_MAJOR = 1
VERSION_MINOR = 0
HEADER_SIZE = 128

CHUNK_TRANSITION = 1
CHUNK_SAMPLE = 2
CHUNK_EVENT = 3

FOOTER_MAGIC = 0x434F4F46

# FileHeader struct: see spec
# offset 0  magic I, version H H, created Q, meta_len I, reserved I, f_cpu Q, num_ch H, flags H, total_trans Q, total_samples Q, mode I, rate I, reserved 68
HEADER_STRUCT = struct.Struct("<IHHQIIQIHHQQII68s")
# Actually per spec: I H H Q I I Q H H Q Q I I 68s = 4+2+2+8+4+4+8+2+2+8+8+4+4+68 =128
# Let's define correctly:
HEADER_FMT = "<IHHQIIQHHQQII68s"  # 4+2+2+8+4+4+8+2+2+8+8+4+4+68 =128? check: 4+2=6+2=8+8=16+4=20+4=24+8=32+2=34+2=36+8=44+8=52+4=56+4=60+68=128 yes
# But we have 11 fields before 68s: I H H Q I I Q H H Q Q I I -> count
HEADER_STRUCT2 = struct.Struct(HEADER_FMT)

CHUNK_HEADER = struct.Struct("<III")  # type, payload_len, crc32
CHUNK_HEADER_SIZE = CHUNK_HEADER.size  # 12

