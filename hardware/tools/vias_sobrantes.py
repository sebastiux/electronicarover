#!/usr/bin/env python3
"""Prueba cada via-pin: la borra (como si no se soldara el alambre) y vuelve a
calcular la conectividad de KiCad SIN metalizado (cada pad solo en su cara de
soldadura, zonas rellenadas de nuevo). Si no se abre ninguna conexion, la via sobra.
Uso: python3 vias_sobrantes.py tarjeta.kicad_pcb"""
import os, sys, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
pcb = os.path.abspath(sys.argv[1])
if len(sys.argv) > 2:          # proceso hijo: probar la via numero k
    import pcbnew
    sys.path.insert(0, HERE)
    import rover_design as D
    import re, shutil, tempfile
    k = int(sys.argv[2])
    # copia del proyecto (con su .kicad_pro, para que valgan las reglas) sin la linea de la via k
    tmp = tempfile.mkdtemp()
    base_pro = pcb[:-len(".kicad_pcb")] + ".kicad_pro"
    dst = os.path.join(tmp, os.path.basename(pcb))
    shutil.copy(base_pro, dst[:-len(".kicad_pcb")] + ".kicad_pro")
    lines = open(pcb).read().split("\n")
    vl = [i for i, l in enumerate(lines) if re.match(r"\s*\(via ", l)]
    def pos(l):
        m = re.search(r"\(at ([-\d.]+) ([-\d.]+)\)", l); return float(m.group(2)), float(m.group(1))
    vl.sort(key=lambda i: pos(lines[i]))
    if k >= 0:
        l = lines[vl[k]]
        y, x = pos(l)
        net = re.search(r"\(net (\d+)\)", l).group(1)
        name = re.search(r'\(net %s "([^"]*)"\)' % net, "\n".join(lines[:200])).group(1)
        print("VIA %s (%.2f, %.2f)" % (name, x - 30, y - 30))
        del lines[vl[k]]
    else:
        print("N", len(vl))
    open(dst, "w").write("\n".join(lines))
    b = pcbnew.LoadBoard(dst)
    lb, lf = pcbnew.LSET(), pcbnew.LSET()
    lb.AddLayer(pcbnew.B_Cu); lf.AddLayer(pcbnew.F_Cu)
    for fp in b.GetFootprints():
        side = D.pad_side(fp.GetReference())
        for p in fp.Pads():
            if p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH:
                p.SetAttribute(pcbnew.PAD_ATTRIB_SMD); p.SetDrillSize(pcbnew.VECTOR2I(0, 0))
                p.SetLayerSet(lf if side == "F" else lb)
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    b.BuildConnectivity()
    print("ABIERTAS", b.GetConnectivity().GetUnconnectedCount(True))
    sys.stdout.flush(); shutil.rmtree(tmp); os._exit(0)
env = dict(os.environ)
def corre(k):
    o = subprocess.run([sys.executable, __file__, pcb, str(k)], capture_output=True, text=True, env=env).stdout
    d = dict(l.split(" ", 1) for l in o.splitlines() if " " in l)
    return d
base = corre(-1)
n = int(base["N"]); print("vias:", n, " abiertas de base:", base["ABIERTAS"])
sobran = []
for k in range(n):
    d = corre(k)
    if d["ABIERTAS"] == base["ABIERTAS"]:
        sobran.append(d["VIA"])
print("vias que sobran (quitarlas no abre nada): %d" % len(sobran))
for s in sobran: print("  ", s)
