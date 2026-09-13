import tempfile, pathlib, struct, json, time
from app.capture.writer import CaptureWriter
from app.capture.reader import CaptureReader

def test_write_read_roundtrip():
    with tempfile.TemporaryDirectory() as td:
        p = pathlib.Path(td)/"test.stcap"
        ch_meta=[{"id":i,"label":f"CH{i}","enabled":True,"color":"#00BFFF","physPin":i} for i in range(16)]
        w=CaptureWriter(p, f_cpu=600_000_000, channels_meta=ch_meta, app_version="1.0.0")
        w.open()
        base=100_000
        recs=[(0x0001,0),(0x0003,6000),(0x0002,6000)]
        w.add_transitions(base, recs)
        w.add_transitions(base+12000, [(0x0000,0),(0x0001,3000)])
        w.add_event(base+15000, code=1, text="TRIGGER")
        w.close()
        assert p.exists()
        r=CaptureReader(p)
        assert r.header is not None
        assert r.header.total_transitions==5
        assert r.header.f_cpu==600_000_000
        batches=list(r.iter_transition_batches())
        assert len(batches)==2
        assert batches[0][1]==recs
        flat=r.get_all_transitions()
        assert len(flat)==5
        # time series
        times,_ = r.get_time_series()
        assert len(times)==5

def test_csv_export():
    with tempfile.TemporaryDirectory() as td:
        p=pathlib.Path(td)/"a.stcap"
        w=CaptureWriter(p, f_cpu=600_000_000)
        w.open()
        w.add_transitions(0, [(0xAAAA,0),(0x5555,6000)])
        w.close()
        r=CaptureReader(p)
        flat=r.get_all_transitions()
        assert flat[0][1]==0xAAAA

def test_forward_compat_unknown_chunk():
    # Write normal then append unknown chunk manually and ensure reader skips
    import struct
    from app.capture.format import CHUNK_HEADER
    from app.utils.crc import crc32_ieee
    with tempfile.TemporaryDirectory() as td:
        p=pathlib.Path(td)/"b.stcap"
        w=CaptureWriter(p)
        w.open()
        w.add_transitions(0, [(0x1234,0)])
        w.close()
        # append unknown chunk type 99
        with open(p,"ab") as fh:
            payload=b"unknown"
            fh.write(CHUNK_HEADER.pack(99, len(payload), crc32_ieee(payload)))
            fh.write(payload)
        r=CaptureReader(p)
        # should still iterate transitions
        batches=list(r.iter_transition_batches())
        assert len(batches)>=1
