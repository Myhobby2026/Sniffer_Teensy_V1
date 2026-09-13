import tempfile, pathlib
from tests.generators.spi_generator import generate_spi_capture

def test_spi_gen():
    with tempfile.TemporaryDirectory() as td:
        p=pathlib.Path(td)/"spi.stcap"
        generate_spi_capture(str(p), transactions=3)
        assert p.exists()
        from app.capture.reader import CaptureReader
        r=CaptureReader(p)
        assert r.header.total_transitions>0
        flat=r.get_all_transitions()
        assert len(flat)>10
