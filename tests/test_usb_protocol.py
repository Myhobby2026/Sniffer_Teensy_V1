import struct
from app.device.protocol import encode_packet, StreamDecoder, build_hello_payload, parse_hello_ack, build_config_channels, build_config_capture, parse_status, parse_data_transition
from app.utils.crc import crc16_ccitt

def test_crc():
    assert crc16_ccitt(b"123456789") == 0x29B1

def test_encode_decode_roundtrip():
    from app.device.protocol import PT_PING
    payload = b"hello"
    pkt = encode_packet(PT_PING, payload, seq=42)
    dec = StreamDecoder()
    out = list(dec.feed(pkt))
    assert len(out)==1
    assert out[0].type == PT_PING
    assert out[0].payload == payload
    assert out[0].seq == 42

def test_hello_ack():
    fw=0x00010000; hw=0x00010000; fcpu=600_000_000; ram=1024*1024; nch=16; cart=1; caps=3
    payload = struct.pack("<IIIIHBB", fw,hw,fcpu,ram,nch,cart,caps) + b"TEST-UID\x00".ljust(32,b"\x00")
    d=parse_hello_ack(payload)
    assert d["f_cpu"]==fcpu
    assert d["cartridge"]==1

def test_config_channels():
    p=build_config_channels(0xFFFF, 0x0003, 0x0000)
    assert len(p)==7 or len(p)==6

def test_status():
    p=struct.pack("<BBHIIHH", 2, 50, 0, 1234, 5678, 0, 1)
    d=parse_status(p)
    assert d["state"]==2
    assert d["transitions"]==1234

def test_data_transition():
    base=1_000_000
    records=[(0x1234,0),(0x5678,6000)]
    payload=struct.pack("<QH", base, len(records))
    for s,d in records:
        payload+=struct.pack("<HI", s,d)
    parsed=parse_data_transition(payload)
    assert parsed is not None
    b, recs = parsed
    assert b==base
    assert recs==records

def test_stream_decoder_split():
    from app.device.protocol import PT_HELLO
    p1=encode_packet(PT_HELLO, build_hello_payload())
    # split into chunks
    dec=StreamDecoder()
    pkts=[]
    for chunk in [p1[:3], p1[3:7], p1[7:]]:
        pkts.extend(list(dec.feed(chunk)))
    assert len(pkts)==1

def test_crc_error_counts():
    from app.device.protocol import PT_PING
    pkt=encode_packet(PT_PING, b"xx", seq=1)
    bad=bytearray(pkt)
    bad[-1]^=0xFF
    dec=StreamDecoder()
    list(dec.feed(bytes(bad)))
    assert dec.crc_errors>=1
