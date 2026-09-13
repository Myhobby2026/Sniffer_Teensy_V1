# Sniffer GUI — Python Tkinter

## Run

```bash
pip install -r app/requirements.txt
python app/main.py
# simulated (no Teensy)
python app/main.py --simulate
# replay a capture
python app/main.py --replay captures/example.stcap
# or
python app/main.py --simulate captures/example.stcap
```

## Structure

See `docs/06-python-architecture.md`.

## Capture files

`.stcap` per `docs/04-capture-format-spec.md`. Writer: `app/capture/writer.py`, reader `reader.py`.

## Device

USB CDC Framed protocol `docs/03-usb-protocol-spec.md`. Configure via `app/device/protocol.py`.

## Tests without hardware

```bash
pytest -q
python tests/generators/spi_generator.py --out /tmp/synth.stcap
python app/main.py --simulate /tmp/synth.stcap
```
