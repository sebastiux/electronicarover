# -*- coding: utf-8 -*-
"""
Simula el aislamiento como lo hace un CAM generico (LPKF CircuitPro, FlatCAM, la app del Fab Lab):
desplaza TODO el cobre junto el radio de la fresa y da una pasada por ese contorno.

Reporta, para una fresa nominal de 1.0 mm (y con corte real mas angosto o mas ancho):
  - cortos: una pieza de cobre que queda tocando 2 o mas redes;
  - redes abiertas (contando los cables por arriba);
  - tiras sueltas: cobre que queda aislado de todas las redes, con su ancho y posicion.

Uso: ROVER_VARIANT=traccion python3 sim_cam_union.py [imagen.png]
"""
import csv, math, os, sys
_args = sys.argv[1:]
sys.argv = sys.argv[:1]
import cubiko_cam as C
from shapely.geometry import Point, box, LineString
from shapely.ops import unary_union

T = 1.0                                   # fresa nominal


def contorno(copper, r):
    g = copper.buffer(r, resolution=16)
    lines = []
    for p in (g.geoms if hasattr(g, "geoms") else [g]):
        lines.append(LineString(p.exterior.coords))
        lines += [LineString(i.coords) for i in p.interiors]
    return lines


def main():
    net_polys, pads, vias, holes, keepouts, hard = C.load()
    B = {n: g for n, g in net_polys["B"].items() if not g.is_empty}
    copper = unary_union(list(B.values()))
    tarjeta = box(0, 0, C.W, C.H)
    hoyos = unary_union([Point(x, y).buffer(d / 2, resolution=12) for (x, y, d, _, _) in holes])
    cables = []
    fcsv = os.path.join(C.HERE, "..", C.D.PROJECT, "puentes_alambre.csv")
    if os.path.exists(fcsv):
        for r in csv.DictReader(open(fcsv), delimiter=";"):
            cables.append((r["Red"], (float(r["X1(mm)"]), float(r["Y1(mm)"])), (float(r["X2(mm)"]), float(r["Y2(mm)"]))))
    paths = [l.intersection(tarjeta) for l in contorno(copper, T / 2)]
    ok = True
    print("%s  %.0f x %.0f mm   redes %d   cables %d" % (C.D.PROJECT, C.W, C.H, len([n for n in B if n]), len(cables)))
    img_data = None
    for w in (0.8, 0.9, 1.0, 1.1):
        cut = unary_union([p.buffer(w / 2, resolution=8) for p in paths if not p.is_empty])
        rem = tarjeta.difference(cut).difference(hoyos)
        comps = list(rem.geoms) if hasattr(rem, "geoms") else [rem]
        cortos, sueltas, de_red = [], [], {}
        for i, c in enumerate(comps):
            t = [n for n, g in B.items() if n and c.intersects(g) and c.intersection(g).area > 0.002]
            if len(t) > 1:
                cortos.append((t, c.representative_point().coords[0]))
            elif not t and c.area > 0.02:
                ancho = 99
                if c.area < 400:
                    ancho = 4.0
                    for k in range(1, 200):
                        if c.buffer(-k / 100.0).is_empty:
                            ancho = 2 * k / 100.0
                            break
                sueltas.append((c.area, ancho, c.representative_point().coords[0]))
            for n in t:
                de_red.setdefault(n, []).append(i)
        # redes abiertas: piezas de una red unidas por cables
        par = {}

        def find(a):
            par.setdefault(a, a)
            while par[a] != a:
                par[a] = par[par[a]]; a = par[a]
            return a
        for net, a, b in cables:
            ia = [i for i in de_red.get(net, []) if comps[i].distance(Point(a)) < 1.3]
            ib = [i for i in de_red.get(net, []) if comps[i].distance(Point(b)) < 1.3]
            if ia and ib:
                par[find(ia[0])] = find(ib[0])
        abiertas = []
        for p in pads:
            if not p["net"]:
                continue
        for n, idx in de_red.items():
            # solo cuentan las piezas que tienen un pad de esa red
            con_pad = [i for i in set(idx) if any(pp["net"] == n and comps[i].distance(Point(pp["x"], pp["y"])) < pp["size"] / 2 for pp in pads)]
            if len({find(i) for i in con_pad}) > 1:
                abiertas.append(n)
        finas = [s for s in sueltas if s[1] < 90]
        print("  corte real %.1f mm: cortos %d   redes abiertas %d   tiras sueltas %d%s"
              % (w, len(cortos), len(abiertas), len(finas),
                 ("  (la mas ancha %.2f mm)" % max(s[1] for s in finas)) if finas else ""))
        for t, pt in cortos[:6]:
            print("      CORTO %s cerca de (%.1f, %.1f)" % (",".join(t[:4]), pt[0], pt[1]))
        for n in abiertas[:6]:
            print("      ABIERTA %s" % n)
        if w == T:
            for a, an, pt in sorted(finas, key=lambda s: -s[0])[:12]:
                print("      tira suelta de %.2f mm2, ancho %.2f mm, en (%.1f, %.1f)" % (a, an, pt[0], pt[1]))
            img_data = (rem, cut, finas, cortos)
        if w in (0.9, 1.0, 1.1) and (cortos or abiertas):
            ok = False
    if _args and img_data:
        from PIL import Image, ImageDraw
        S = 12
        rem, cut, finas, cortos = img_data
        im = Image.new("RGB", (int(C.W * S), int(C.H * S)), (30, 30, 34))
        d = ImageDraw.Draw(im)
        for c in (rem.geoms if hasattr(rem, "geoms") else [rem]):
            t = [n for n, g in B.items() if n and c.intersects(g) and c.intersection(g).area > 0.002]
            col = (200, 60, 60) if len(t) > 1 else (214, 140, 70) if t else (90, 200, 120)
            d.polygon([(x * S, y * S) for x, y in c.exterior.coords], fill=col)
            for h in c.interiors:
                d.polygon([(x * S, y * S) for x, y in h.coords], fill=(30, 30, 34))
        im.save(_args[0])
    print("  RESULTADO:", "OK" if ok else "FALLA")
    return ok


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
