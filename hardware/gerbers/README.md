# Gerbers — How to Generate & Order

**Source:** `hardware/kicad/Sniffer_Teensy_V1.kicad_pcb` (KiCad 7/8)

## Generate

In KiCad:

1. Open `Sniffer_Teensy_V1.kicad_pro` → PCB Editor
2. **File → Fabrication Outputs → Gerbers (RS-274X):**
   - Layers: `F.Cu`, `B.Cu`, `F.Mask`, `B.Mask`, `F.SilkS`, `B.SilkS`, `Edge.Cuts`
   - Format: `Gerber`, `4.6`, `Use Protel extensions` OFF, `Generate Gerber job file` ON
   - Output: `hardware/gerbers/`
3. **File → Fabrication Outputs → Drill Files:**
   - Format: `Excellon`, `PTH and NPTH separate`, `Minimal header`, `Mirror Y` OFF
   - Output same folder

Or CLI:

```bash
kicad-cli pcb export gerbers --layers F.Cu,B.Cu,F.Mask,B.Mask,F.SilkS,B.SilkS,Edge.Cuts -o hardware/gerbers hardware/kicad/Sniffer_Teensy_V1.kicad_pcb
kicad-cli pcb export drill --format excellon --excellon-oval-format route -o hardware/gerbers hardware/kicad/Sniffer_Teensy_V1.kicad_pcb
```

## Files Produced

```
Sniffer_Teensy_V1-F_Cu.gbr
Sniffer_Teensy_V1-B_Cu.gbr
Sniffer_Teensy_V1-F_Mask.gbr
Sniffer_Teensy_V1-B_Mask.gbr
Sniffer_Teensy_V1-F_Silkscreen.gbr
Sniffer_Teensy_V1-B_Silkscreen.gbr
Sniffer_Teensy_V1-Edge_Cuts.gbr
Sniffer_Teensy_V1-PTH.drl      (plated: 0.4mm stitch, 1.0mm headers)
Sniffer_Teensy_V1-NPTH.drl     (mounting 3.2mm)
Sniffer_Teensy_V1-job.gbrjob
```

Zip them:

```bash
cd hardware/gerbers && zip ../Sniffer_Teensy_V1_Gerbers_rev1.0.zip *.gbr *.drl *.gbrjob
```

## Order

Upload the zip to **JLCPCB** / **PCBWay**:

- Layers: 2, Size: 100×65 mm, Thickness 1.6 mm, Copper 1oz, Finish ENIG, Mask Black, Silk White, Edge 0.2mm
- Preview in viewer — should match `hardware/images/pcb-3d-top.png`
- Qty 5, lead ~3 days

