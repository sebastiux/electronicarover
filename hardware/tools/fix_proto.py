#!/usr/bin/env python3
"""Cierre puntual de conexiones pendientes sobre una PCB ya ruteada (2 capas o prototipado).

Quita pistas de algunas redes y las vuelve a rutear EN EL ORDEN dado, con los mismos
parametros que generate.py (cara de soldadura por componente, costo de via, etc.).

Uso:
  python3 fix_proto.py entrada.kicad_pcb salida.kicad_pcb [opciones]
    --drop RED                     quita todas las pistas y vias de la red
    --dropbox RED:x0,y0,x1,y1      quita las pistas/vias de la red con algun extremo en la caja
                                   (coordenadas de diseno, sin el desfase de 30 mm)
    --via RED:x,y                  agrega una via (pin) de la clase de la red
    --track RED:F|B:ancho:x,y/x,y/...  agrega una pista manual
    --route RED[:REF.PAD+REF.PAD]  rutea la red (opcional: solo esos pads pendientes)
Las opciones se aplican en orden: primero todos los --drop/--dropbox, luego los --route.
"""
import os, re, sys
import pcbnew
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rover_design as D, router1l, generate as G

O = 30.0
src, dst = sys.argv[1], sys.argv[2]
args = sys.argv[3:]
drops, boxes, routes, adds = set(), [], [], []
i = 0
while i < len(args):
    a, v = args[i], args[i + 1]
    if a == "--drop":
        drops.add(v)
    elif a == "--dropbox":
        n, b = v.split(":")
        boxes.append((n, [float(c) for c in b.split(",")]))
    elif a in ("--via", "--track"):
        adds.append((a, v))
    elif a == "--route":
        n, _, pads = v.partition(":")
        routes.append((n, set(pads.split("+")) if pads else None))
    else:
        sys.exit("opcion desconocida: " + a)
    i += 2

D.build()
txt = open(src).read()
codes = {m.group(2): m.group(1) for m in re.finditer(r'\(net (\d+) "([^"]*)"\)', txt)}
dcodes = {codes[n] for n in drops}
bcodes = [(codes[n], b) for n, b in boxes]


def inbox(l, b):
    pts = re.findall(r'\((?:start|end|at) ([-\d.]+) ([-\d.]+)\)', l)
    return any(b[0] <= float(x) - O <= b[2] and b[1] <= float(y) - O <= b[3] for x, y in pts)


def keep(l):
    m = re.search(r'\(net (\d+)\)', l)
    if not (re.match(r'\s*\((segment|via|arc) ', l) and m):
        return True
    c = m.group(1)
    if c in dcodes:
        return False
    return not any(c == bc and inbox(l, b) for bc, b in bcodes)


lines = txt.split("\n")
out = [l for l in lines if keep(l)]
print("pistas/vias quitadas:", len(lines) - len(out))
open(dst, "w").write("\n".join(out))

board = pcbnew.LoadBoard(dst)
nb = board.GetNetsByName()
asg0 = G.write_project(D.nets())
vsz = {n: (vd, vdr) for (n, tw, clr, vd, vdr, p) in D.NETCLASSES}
P = lambda x, y: pcbnew.VECTOR2I(pcbnew.FromMM(x + O), pcbnew.FromMM(y + O))
for a, v in adds:
    if a == "--via":
        n, xy = v.split(":")
        x, y = map(float, xy.split(","))
        vd, vdr = vsz.get(asg0.get(n, "Default"), D.DEFAULT_CLASS[2:4])
        t = pcbnew.PCB_VIA(board)
        t.SetPosition(P(x, y)); t.SetWidth(pcbnew.FromMM(vd)); t.SetDrill(pcbnew.FromMM(vdr))
        t.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); t.SetNet(nb[n]); board.Add(t)
    else:
        n, lay, w, pts = v.split(":")
        pts = [tuple(map(float, q.split(","))) for q in pts.split("/")]
        for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
            t = pcbnew.PCB_TRACK(board)
            t.SetStart(P(x1, y1)); t.SetEnd(P(x2, y2)); t.SetWidth(pcbnew.FromMM(float(w)))
            t.SetLayer(pcbnew.F_Cu if lay == "F" else pcbnew.B_Cu); t.SetNet(nb[n]); board.Add(t)
classes = {"Default": D.DEFAULT_CLASS[:2]}
via = {"Default": D.DEFAULT_CLASS[2:4]}
for (n, tw, clr, vd, vdr, p) in D.NETCLASSES:
    classes[n] = (tw, clr)
    via[n] = (vd, vdr)
asg = G.write_project(D.nets())
res = [(x0 + O, y0 + O, x1 + O, y1 + O, a) for (x0, y0, x1, y1, a) in D.routing_reserved()]
proto = D.FAB == "proto"
r = router1l.Router(board, classes, reserved=res, two_layer=(D.LAYERS == 2), via_sizes=via, log=print,
                    pad_side=D.pad_side, via_cost_mm=(12.0 if proto else 3.0),
                    no_via_under_parts=proto)
for n, pads in routes:
    filt = None
    if pads:
        filt = (lambda ps: lambda pad: "%s.%s" % (pad.GetParent().GetReference(), pad.GetNumber()) in ps)(pads)
    print("ruteando", n, sorted(pads) if pads else "")
    r.route_net(n, asg.get(n, "Default"), pad_filter=filt, relaxed=True)
    done = r.trees.get(n, [None, set()])[1]
    miss = ["%s.%s" % (p.GetParent().GetReference(), p.GetNumber())
            for k, (p, s_) in enumerate(r.pads_by_net.get(n, [])) if k not in done]
    if pads:
        miss = [m for m in miss if m in pads]
    print("   pendientes:", miss or "ninguno")
for _ in range(10):
    board.BuildConnectivity()
    conn = board.GetConnectivity()
    d = [t for t in board.GetTracks() if conn.TestTrackEndpointDangling(t, False)]
    if not d:
        break
    for t in d:
        board.Remove(t)
pcbnew.ZONE_FILLER(board).Fill(board.Zones())
board.BuildConnectivity()
print("sin conectar (con metalizado):", board.GetConnectivity().GetUnconnectedCount(True))
pcbnew.SaveBoard(dst, board)
