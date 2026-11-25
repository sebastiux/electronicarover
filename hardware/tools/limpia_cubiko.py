#!/usr/bin/env python3
"""Limpieza de la PCB Cubiko despues del ruteo.

- Quita los tramos de MOTOR_EN que el router agrego en paralelo al bus vertical de
  las vias EN (ya une los 6 pines ENA/ENB): dejaban 2 vias-pin a 1.7 mm junto a J41.6
  y J42.6 y lazos por la orilla.
- Quita la via GND junto al barreno H3: el separador M3 se apoyaba sobre ella.
Despues borra las pistas que quedan colgando, rellena zonas y verifica que no se
pierda ninguna conexion."""
import os, re, sys, math, pcbnew
O = 30.0
src = sys.argv[1]
def near(a, b, tol=0.06):
    return math.hypot(a[0] - b[0], a[1] - b[1]) < tol
QUITAR = {
    "MOTOR_EN": [
        [(12.2, 87.2)], [(12.2, 60.7), (12.2, 87.2)], [(12.2, 87.2), (6.2, 88.2)], [(6.2, 88.2), (5.5, 88.25)],
        [(12.2, 59.7)], [(11.2, 44.2), (12.2, 59.7)], [(12.2, 59.7), (6.2, 60.7)], [(6.2, 60.7), (5.5, 60.75)],
        [(8.95, 60.45), (6.45, 69.7)], [(6.45, 69.7), (5.95, 70.2)], [(5.95, 70.2), (5.5, 70.75)],
        [(8.95, 42.95), (7.2, 33.45)], [(7.2, 33.45), (6.2, 33.2)], [(6.2, 33.2), (5.5, 33.25)],
        [(4.95, 15.7), (5.5, 15.75)], [(3.45, 16.2), (4.95, 15.7)], [(1.95, 27.95), (3.45, 16.2)], [(4.45, 33.2), (1.95, 27.95)],
    ],
    "GND": [[(10.7, 94.2)], [(8.2, 91.7), (10.7, 94.2)], [(10.7, 94.2), (6.2, 91.7)], [(6.2, 91.7), (5.5, 91.75)]],
}
# 1) quitar por texto (pcbnew se corrompe si se quitan objetos y luego se recorre la tabla)
txt = open(src).read()
codes = {m.group(2): m.group(1) for m in re.finditer(r'\(net (\d+) "([^"]*)"\)', txt)}
def coords(l):
    return [(round(float(x) - O, 2), round(float(y) - O, 2)) for x, y in re.findall(r'\((?:start|end|at) ([-\d.]+) ([-\d.]+)\)', l)]
quitados, lines = 0, []
for l in txt.split("\n"):
    m = re.match(r'\s*\((segment|via) .*\(net (\d+)\)', l)
    hit = False
    if m:
        tp = coords(l)
        for net, lst in QUITAR.items():
            if m.group(2) != codes[net]:
                continue
            for pts in lst:
                if len(tp) == len(pts) and (all(near(a, c) for a, c in zip(tp, pts)) or all(near(a, c) for a, c in zip(tp[::-1], pts))):
                    hit = True
    if hit:
        quitados += 1
    else:
        lines.append(l)
esperados = sum(len(v) for v in QUITAR.values())
print("quitados %d de %d" % (quitados, esperados))
if quitados != esperados:
    sys.exit("no coincide la geometria: nada se guardo")
# se escribe sobre la misma ruta para que KiCad cargue el .kicad_pro del proyecto
# (reglas, clases de red, severidades); con otro nombre usaria las de fabrica
open(src, "w").write("\n".join(lines))
b = pcbnew.LoadBoard(src)
colg = 0
for _ in range(20):
    b.BuildConnectivity(); c = b.GetConnectivity()
    d = [t for t in b.GetTracks() if t.GetClass() != "PCB_VIA" and c.TestTrackEndpointDangling(t, False)]
    if not d: break
    for t in d: b.Remove(t); colg += 1
print("pistas colgando quitadas:", colg)
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
b.BuildConnectivity()
despues = b.GetConnectivity().GetUnconnectedCount(True)
print("sin conectar despues de limpiar:", despues)
if despues:
    sys.exit("se perdio una conexion: nada se guardo")
pcbnew.SaveBoard(src, b)
print("vias:", sum(1 for t in b.GetTracks() if t.GetClass() == "PCB_VIA"))
