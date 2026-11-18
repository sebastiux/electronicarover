#!/usr/bin/env python3
"""Verifica que la PCB funcione SIN barrenos metalizados (prototipado por fresado).

Hace una copia de la PCB donde cada pad existe solo en la cara por la que
realmente se suelda (componentes arriba -> pad solo en B.Cu; header de la Pi
montado abajo -> pad solo en F.Cu) y vuelve a calcular la conectividad con KiCad.
Las vias se consideran pines soldados arriba y abajo (unen ambas caras).
Si algo dependia del metalizado, aparece como "sin conectar"."""
import os, sys, collections
import pcbnew
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rover_design as D

pcb = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "rover_controller", "rover_controller.kicad_pcb")
b = pcbnew.LoadBoard(pcb)
lb, lf = pcbnew.LSET(), pcbnew.LSET()
lb.AddLayer(pcbnew.B_Cu); lb.AddLayer(pcbnew.B_Mask)
lf.AddLayer(pcbnew.F_Cu); lf.AddLayer(pcbnew.F_Mask)
n_b = n_f = 0
for fp in b.GetFootprints():
    side = D.pad_side(fp.GetReference())
    for p in fp.Pads():
        if p.GetAttribute() != pcbnew.PAD_ATTRIB_PTH:
            continue
        p.SetAttribute(pcbnew.PAD_ATTRIB_SMD)
        p.SetDrillSize(pcbnew.VECTOR2I(0, 0))
        if side == "F":
            p.SetLayerSet(lf); n_f += 1
        else:
            p.SetLayerSet(lb); n_b += 1
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
b.BuildConnectivity()
conn = b.GetConnectivity()
un = conn.GetUnconnectedCount(True)
vias = [t for t in b.GetTracks() if t.GetClass() == "PCB_VIA"]
lenF = sum(pcbnew.ToMM(t.GetLength()) for t in b.GetTracks() if t.GetClass() == "PCB_TRACK" and t.GetLayer() == pcbnew.F_Cu)
lenB = sum(pcbnew.ToMM(t.GetLength()) for t in b.GetTracks() if t.GetClass() == "PCB_TRACK" and t.GetLayer() == pcbnew.B_Cu)
drills = collections.Counter(round(pcbnew.ToMM(v.GetDrillValue()), 2) for v in vias)
print("Pads solo abajo: %d   pads solo arriba (header Pi): %d" % (n_b, n_f))
print("Vias (pines a soldar arriba y abajo): %d  taladros %s" % (len(vias), dict(drills)))
print("Pistas: abajo %.0f mm, arriba %.0f mm" % (lenB, lenF))
print("Conexiones abiertas SIN metalizado: %d" % un)
if un:
    out = "/tmp/check_proto_drc.rpt"
    pcbnew.WriteDRCReport(b, out, pcbnew.EDA_UNITS_MILLIMETRES, True)
    print("detalle en", out)
sys.exit(1 if un else 0)
