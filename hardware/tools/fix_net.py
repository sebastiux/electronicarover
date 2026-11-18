# Re-rutea una red puntual sobre una PCB ya ruteada (cierre manual de pendientes).
# Uso: python3 fix_net.py entrada.kicad_pcb salida.kicad_pcb RED [redes_a_levantar] [x0,y0,x1,y1 caja F.Cu] [redes_F_a_levantar]
# v1.1: python3 fix_net.py pcb pcb_out 5V_U5 "" "100,75,150,115" GND
import sys, re, pcbnew
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rover_design as D, router1l, generate as G
src, dst, target = sys.argv[1], sys.argv[2], sys.argv[3]
rip = [n for n in sys.argv[4].split(",") if n] if len(sys.argv) > 4 else []
D.build()
classes = {"Default": D.DEFAULT_CLASS[:2]}
via = {"Default": D.DEFAULT_CLASS[2:4]}
for (n, tw, clr, vd, vdr, p) in D.NETCLASSES:
    classes[n] = (tw, clr); via[n] = (vd, vdr)
asg = G.write_project(D.nets())
res = [(x0 + 30, y0 + 30, x1 + 30, y1 + 30, a) for (x0, y0, x1, y1, a) in D.routing_reserved()]
txt = open(src).read()
codes = {m.group(2): m.group(1) for m in re.finditer(r'\(net (\d+) "([^"]*)"\)', txt)}
drop = set(codes[n] for n in [target] + rip)
# opcional: quitar solo pistas en F.Cu de ciertas redes dentro de una caja (x0,y0,x1,y1 abs)
fbox = [float(v) for v in sys.argv[5].split(",")] if len(sys.argv) > 5 else None
fnets = set(codes[n] for n in sys.argv[6].split(",")) if len(sys.argv) > 6 else set()
def keep(l):
    m = re.search(r'\(net (\d+)\)', l)
    if not (re.match(r'\s*\((segment|via|arc) ', l) and m):
        return True
    if m.group(1) in drop:
        return False
    if fbox and m.group(1) in fnets and '"F.Cu"' in l and l.lstrip().startswith("(segment"):
        xs = [float(v) for v in re.findall(r'\((?:start|end) ([-\d.]+) [-\d.]+\)', l)]
        ys = [float(v) for v in re.findall(r'\((?:start|end) [-\d.]+ ([-\d.]+)\)', l)]
        if any(fbox[0] <= x <= fbox[2] and fbox[1] <= y <= fbox[3] for x, y in zip(xs, ys)):
            return False
    return True
out = [l for l in txt.split("\n") if keep(l)]
open(dst, "w").write("\n".join(out))
b = pcbnew.LoadBoard(dst)
r = router1l.Router(b, classes, reserved=res, two_layer=True, via_sizes=via, log=print)
for n in [target] + rip + sorted(set(sys.argv[6].split(",")) if len(sys.argv) > 6 else []):
    r.route_net(n, asg.get(n, "Default"), relaxed=True)
for _ in range(10):
    b.BuildConnectivity(); conn = b.GetConnectivity()
    d = [t for t in b.GetTracks() if conn.TestTrackEndpointDangling(t, False)]
    if not d: break
    for t in d: b.Remove(t)
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
b.BuildConnectivity()
print("sin conectar:", b.GetConnectivity().GetUnconnectedCount(True))
pcbnew.SaveBoard(dst, b)
