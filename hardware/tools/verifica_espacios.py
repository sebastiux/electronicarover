#!/usr/bin/env python3
"""Revisa el espacio para soldar en la cara de cobre (B.Cu) de una tarjeta de una cara:

- cobre libre entre pads (y barrenos de cable) de piezas DISTINTAS >= MIN_PAD_ESPACIO,
  aunque sean de la misma red (asi ningun pad queda encimado ni pegado a otro);
- ancho de toda pista de la cara de cobre >= ancho minimo (DEFAULT_CLASS);
- patios (courtyards) de componentes sin traslape.
Uso: ROVER_VARIANT=traccion python3 verifica_espacios.py
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pcbnew
import rover_design as D
from shapely.geometry import Polygon, Point
from shapely.strtree import STRtree

O = 30.0
MIN = getattr(D, "MIN_PAD_ESPACIO", 1.0)
VMIN = getattr(D, "VIA_PAD_ESPACIO", MIN)
WMIN = D.DEFAULT_CLASS[0]
pcb = os.path.join(HERE, "..", D.PROJECT, D.PROJECT + ".kicad_pcb")
b = pcbnew.LoadBoard(pcb)
mm = pcbnew.ToMM
err = pcbnew.FromMM(0.005)
items = []      # (geom, ref, etiqueta)
for fp in b.GetFootprints():
    for p in fp.Pads():
        if not p.IsOnLayer(pcbnew.B_Cu) or p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
            continue
        ps = pcbnew.SHAPE_POLY_SET()
        p.TransformShapeToPolygon(ps, pcbnew.B_Cu, 0, err)
        ol = ps.Outline(0)
        g = Polygon([(mm(ol.CPoint(i).x) - O, mm(ol.CPoint(i).y) - O) for i in range(ol.PointCount())])
        items.append((g, fp.GetReference(), "%s.%s" % (fp.GetReference(), p.GetNumber())))
for k, t in enumerate(b.GetTracks()):
    if t.GetClass() == "PCB_VIA":
        c = t.GetPosition()
        items.append((Point(mm(c.x) - O, mm(c.y) - O).buffer(mm(t.GetWidth()) / 2, 16), "VIA%d" % k,
                      "cable (%.1f, %.1f)" % (mm(c.x) - O, mm(c.y) - O)))
tree = STRtree([g for g, _, _ in items])
malos = []
for i, (g, ref, lab) in enumerate(items):
    for j in tree.query(g.buffer(MIN)):
        if j <= i or items[j][1] == ref:
            continue
        d = g.distance(items[j][0])
        lim = VMIN if (ref.startswith("VIA") or items[j][1].startswith("VIA")) else MIN
        if d < lim - 1e-3:
            malos.append((d, lab, items[j][2]))
angostas = [(mm(t.GetWidth()), t.GetNetname()) for t in b.GetTracks()
            if t.GetClass() != "PCB_VIA" and t.GetLayer() == pcbnew.B_Cu and mm(t.GetWidth()) < WMIN - 1e-3]
print("%s: %d pads/barrenos en la cara de cobre" % (D.PROJECT, len(items)))
print("  pads de piezas distintas a menos de %.1f mm (barrenos de cable a menos de %.1f mm): %d" % (MIN, VMIN, len(malos)))
for d, a, c in sorted(malos)[:25]:
    print("     %.2f mm  %s <-> %s" % (d, a, c))
print("  pistas de cobre de menos de %.1f mm: %d %s" % (WMIN, len(angostas), sorted(set(angostas))[:10]))
sys.exit(1 if (malos or angostas) else 0)
