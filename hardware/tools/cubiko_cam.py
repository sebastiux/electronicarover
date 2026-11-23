#!/usr/bin/env python3
"""CAM + simulacion para fresar la tarjeta Cubiko en la Genmitsu Cubiko (GRBL 1.1).

Lee la PCB ruteada (KiCad) y genera:
  hardware/cubiko/gcode/   un archivo .nc por herramienta y por cara
  hardware/cubiko/sim/     imagenes de como queda cada cara despues del corte
  hardware/cubiko/sim/reporte.txt   verificacion electrica del resultado fresado

Flujo de doble cara (volteo con 2 pines de alineacion):
  LADO 1 = cara INFERIOR (B.Cu) hacia arriba, espejada en X. Ahi se taladra todo.
  LADO 2 = cara SUPERIOR (F.Cu) hacia arriba, sin espejo. Ahi se corta el contorno.
  El volteo es sobre el eje vertical X = X0 + W/2; los pines entran en los barrenos
  H1 (3.5, 3.5) y el de la Pi (W-3.5, 3.5), que son simetricos respecto a ese eje.

La simulacion resta del cobre el area barrida por la herramienta (ancho real del
V-bit a la profundidad de corte) y los taladros, y despues comprueba que:
  - cada red quede en una sola pieza de cobre (contando las vias como pines
    soldados por ambas caras y cada pad solo por la cara donde se suelda);
  - ninguna pieza de cobre toque dos redes distintas (cortos);
  - los anillos de los pads queden aislados del cobre sobrante.

Uso: ROVER_VARIANT=cubiko python3 cubiko_cam.py
"""
import math, os, sys
os.environ.setdefault("ROVER_VARIANT", "cubiko")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pcbnew
import rover_design as D
from shapely.geometry import Polygon, MultiPolygon, LineString, Point, box
from shapely.ops import unary_union
from shapely import affinity
from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------------------
# PARAMETROS (Genmitsu Cubiko: husillo 775 de 75 W, max 10 000 RPM, GRBL 1.1h)
# ---------------------------------------------------------------------------
P = dict(
    # Valores por defecto del Fab Lab (https://fablab.sebs.mx/cnc/, cam.js DEF), calibrados en la Cubiko
    blank=(142.0, 100.0),       # placa virgen doble cara FR1, 1.6 mm, cobre 35 um (recortar de 150x100)
    X0=3.0, Y0=2.0,             # esquina inferior izquierda de la tarjeta dentro del blank
    thickness=1.6,
    safe_z=2.0, approach_z=0.3, travel_z=5.0,  # entre trayectorias: sube a 2 mm; baja rapido a 0.3 y entra con avance
    rpm=10000,
    # T1: V-bit 20 grados, punta 0.1 mm (la del Fab Lab)
    vbit_angle=20.0, vbit_tip=0.10, iso_depth=0.10, iso_feed=120.0, iso_plunge=60.0,
    iso_passes=3, iso_overlap=0.50,            # 3 x 50 %: con menos quedan hilos de cobre (nota del Fab Lab)
    # T2: una sola broca de 1.0 mm para todos los agujeros de 0.6 a 1.15 mm
    drill_feed=60.0, drill_depth=1.9,          # atraviesa 1.6 + 0.3 en la cinta / martir
    drill_bits=[1.0], drill_max=1.15,
    # T3: fresa tipo maiz (corn) de 1.0 mm: barrenos de 1.2 mm o mas, pines de alineacion, antena y contorno
    mill_d=1.0, mill_feed=120.0, mill_plunge=60.0, mill_step=0.3,
    outline_depth=1.85, outline_passes=4, tab_w=3.1, tab_h=0.7, n_tabs=4,   # puentes con tope en Z -0.9
    align_d=3.0, align_depth=3.4,               # pines de 3 mm: 1.6 de placa + 1.8 en el MDF (el recorrido Z acaba en el MDF de 2 mm)
    antenna_depth=0.12,
)
W, H = D.BOARD_W, D.BOARD_H
OUTDIR = os.path.join(HERE, "..", "cubiko")
GDIR, SDIR = os.path.join(OUTDIR, "gcode"), os.path.join(OUTDIR, "sim")
PCB = os.path.join(HERE, "..", D.PROJECT, D.PROJECT + ".kicad_pcb")
O = 30.0          # desfase de la PCB en KiCad (generate.py)
ALIGN = list(D.ALIGN_HOLES)   # H1 y el barreno sup. der. de la Pi (simetricos respecto a X = W/2)


def vbit_width(depth):
    return P["vbit_tip"] + 2 * depth * math.tan(math.radians(P["vbit_angle"] / 2))


# ---------------------------------------------------------------------------
# GEOMETRIA DESDE KICAD
# ---------------------------------------------------------------------------
def mm(v):
    return pcbnew.ToMM(v)


def polyset(ps):
    out = []
    for i in range(ps.OutlineCount()):
        o = ps.Outline(i)
        ext = [(mm(o.CPoint(j).x) - O, mm(o.CPoint(j).y) - O) for j in range(o.PointCount())]
        holes = []
        for h in range(ps.HoleCount(i)):
            hh = ps.Hole(i, h)
            holes.append([(mm(hh.CPoint(j).x) - O, mm(hh.CPoint(j).y) - O) for j in range(hh.PointCount())])
        if len(ext) >= 3:
            out.append(Polygon(ext, holes).buffer(0))
    return out


def load():
    b = pcbnew.LoadBoard(PCB)
    err = pcbnew.FromMM(0.005)
    layers = {"F": pcbnew.F_Cu, "B": pcbnew.B_Cu}
    net_polys = {k: {} for k in layers}
    pads, vias, holes = [], [], []
    for fp in b.GetFootprints():
        ref = fp.GetReference()
        side = D.pad_side(ref)
        for p in fp.Pads():
            c = p.GetPosition()
            cx, cy = mm(c.x) - O, mm(c.y) - O
            dx, dy = mm(p.GetDrillSize().x), mm(p.GetDrillSize().y)
            if dx > 0:
                holes.append((cx, cy, max(dx, dy), p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH, ref))
            if p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
                continue
            for k, L in layers.items():
                if not p.IsOnLayer(L):
                    continue
                ps = pcbnew.SHAPE_POLY_SET()
                p.TransformShapeToPolygon(ps, L, 0, err)
                net_polys[k].setdefault(p.GetNetname(), []).extend(polyset(ps))
            pads.append(dict(ref=ref, num=p.GetNumber(), net=p.GetNetname(), x=cx, y=cy, side=side,
                             drill=dx, size=min(mm(p.GetSize().x), mm(p.GetSize().y))))
    for t in b.GetTracks():
        # pistas rectas y vias: poligono exacto con shapely (en KiCad 7 el enum ERROR_LOC
        # de PCB_TRACK.TransformShapeToPolygon no esta expuesto en Python)
        if t.GetClass() == "PCB_VIA":
            c = t.GetPosition()
            g = Point(mm(c.x) - O, mm(c.y) - O).buffer(mm(t.GetWidth()) / 2, resolution=16)
            for k in layers:
                net_polys[k].setdefault(t.GetNetname(), []).append(g)
        else:
            a, e = t.GetStart(), t.GetEnd()
            g = LineString([(mm(a.x) - O, mm(a.y) - O), (mm(e.x) - O, mm(e.y) - O)]).buffer(
                mm(t.GetWidth()) / 2, resolution=12)
            for k, L in layers.items():
                if t.GetLayer() == L:
                    net_polys[k].setdefault(t.GetNetname(), []).append(g)
        if t.GetClass() == "PCB_VIA":
            c = t.GetPosition()
            vias.append(dict(net=t.GetNetname(), x=mm(c.x) - O, y=mm(c.y) - O, d=mm(t.GetWidth()),
                             drill=mm(t.GetDrillValue())))
            holes.append((mm(c.x) - O, mm(c.y) - O, mm(t.GetDrillValue()), False, "VIA"))
    for z in b.Zones():
        if z.GetIsRuleArea():
            continue
        for k, L in layers.items():
            if z.IsOnLayer(L):
                net_polys[k].setdefault(z.GetNetname(), []).extend(polyset(z.GetFilledPolysList(L)))
    keepouts = []
    for z in b.Zones():
        if z.GetIsRuleArea() and z.GetZoneName().startswith("ANTENA"):
            ol = z.Outline().Outline(0)
            keepouts.append(Polygon([(mm(ol.CPoint(j).x) - O, mm(ol.CPoint(j).y) - O) for j in range(ol.PointCount())]))
    for k in net_polys:
        net_polys[k] = {n: unary_union(v) for n, v in net_polys[k].items() if v}
    return net_polys, pads, vias, holes, keepouts


# ---------------------------------------------------------------------------
# TRAYECTORIAS
# ---------------------------------------------------------------------------
def rings(geom):
    out = []
    geoms = geom.geoms if hasattr(geom, "geoms") else [geom]
    for g in geoms:
        if g.is_empty:
            continue
        out.append(list(g.exterior.coords))
        out += [list(i.coords) for i in g.interiors]
    return out


def order_paths(paths):
    """Vecino mas cercano para reducir viajes en vacio."""
    left = list(paths)
    out, cur = [], (0.0, 0.0)
    while left:
        i = min(range(len(left)), key=lambda k: (left[k][0][0] - cur[0]) ** 2 + (left[k][0][1] - cur[1]) ** 2)
        pth = left.pop(i)
        # en un anillo cerrado, empezar en el punto mas cercano
        if pth[0] == pth[-1] and len(pth) > 3:
            j = min(range(len(pth) - 1), key=lambda k: (pth[k][0] - cur[0]) ** 2 + (pth[k][1] - cur[1]) ** 2)
            pth = pth[j:-1] + pth[:j + 1]
        out.append(pth)
        cur = pth[-1]
    return out


def isolation(copper):
    w = vbit_width(P["iso_depth"])
    step = w * (1 - P["iso_overlap"])
    paths, swept = [], []
    board = box(0, 0, W, H)
    for k in range(P["iso_passes"]):
        r = w / 2 + k * step
        g = copper.buffer(r, resolution=16)
        for ring in rings(g):
            ls = LineString(ring).intersection(board.buffer(-0.05))
            for part in (ls.geoms if hasattr(ls, "geoms") else [ls]):
                if part.length > 0.05 and part.geom_type == "LineString":
                    paths.append(list(part.coords))
                    swept.append(part.buffer(w / 2, resolution=8))
    return order_paths(paths), unary_union(swept), w


def pocket(poly, d, step_frac=0.6):
    """Vaciado por contornos concentricos (fresa plana de diametro d)."""
    paths, r = [], d / 2
    g = poly.buffer(-r)
    while not g.is_empty:
        paths += rings(g)
        g = g.buffer(-d * step_frac)
    return paths


def outline_paths():
    r = P["mill_d"] / 2
    g = box(0, 0, W, H).buffer(r, join_style=1, resolution=16)
    ring = list(g.exterior.coords)
    L = LineString(ring)
    # pestanas en el centro de cada lado
    tabs = [(W / 2, -r), (W / 2, H + r), (-r, H / 2), (W + r, H / 2)][:P["n_tabs"]]
    tab_d = [L.project(Point(t)) for t in tabs]
    return ring, L, tab_d


# ---------------------------------------------------------------------------
# G-CODE
# ---------------------------------------------------------------------------
def to_machine(x, y, side):
    """Diseno (vista superior, Y hacia abajo) -> maquina (X der., Y hacia el fondo)."""
    xm = P["X0"] + (W - x if side == "B" else x)
    ym = P["Y0"] + (H - y)
    return xm, ym


class G:
    def __init__(self, title, tool):
        # GRBL no admite parentesis anidados en un comentario: se cierran en el primer ")"
        title, tool = (t.replace("(", "[").replace(")", "]") for t in (title, tool))
        import textwrap
        self.l = ["( %s )" % t for t in textwrap.wrap(title, 72)] + ["( herramienta: %s )" % tool,
                  "( Rover Controller Cubiko - hardware/tools/cubiko_cam.py )",
                  "( X0 Y0 = esquina frontal izquierda del blank; Z0 = cobre )",
                  "G21 G90 G17 G94", "G0 Z%.3f" % P["travel_z"], "M3 S%d" % P["rpm"], "G4 P4"]
        self.cut_len = self.travel_len = 0.0
        self.plunges = 0
        self.pos = (0.0, 0.0)
        self.t = 0.0

    def rapid(self, x, y):
        self.travel_len += math.hypot(x - self.pos[0], y - self.pos[1])
        self.l.append("G0 X%.3f Y%.3f" % (x, y))
        self.pos = (x, y)

    def path(self, pts, z, feed, plunge, side):
        mpts = [to_machine(x, y, side) for (x, y) in pts]
        self.l.append("G0 Z%.3f" % P["safe_z"])
        self.rapid(*mpts[0])
        za = max(P["approach_z"], z + P["approach_z"]) if z < 0 else P["safe_z"]
        self.l.append("G0 Z%.3f" % za)
        self.l.append("G1 Z%.3f F%.0f" % (z, plunge))
        self.t += (za - z) / plunge
        self.plunges += 1
        first = True
        for (x, y) in mpts[1:]:
            d = math.hypot(x - self.pos[0], y - self.pos[1])
            self.cut_len += d
            self.t += d / feed
            self.l.append(("G1 X%.3f Y%.3f F%.0f" % (x, y, feed)) if first else ("X%.3f Y%.3f" % (x, y)))
            first = False
            self.pos = (x, y)
        self.l.append("G0 Z%.3f" % P["safe_z"])

    def drill(self, x, y, side, depth, feed):
        xm, ym = to_machine(x, y, side)
        self.rapid(xm, ym)
        self.l.append("G1 Z%.3f F%.0f" % (-depth, feed))
        self.l.append("G0 Z%.3f" % P["safe_z"])
        self.t += (depth + P["safe_z"]) / feed + 0.02
        self.plunges += 1

    def save(self, name):
        self.l += ["G0 Z%.3f" % P["travel_z"], "M5", "G0 X%.3f Y%.3f" % (P["X0"], P["Y0"] + H + 3), "M2"]
        self.t += self.travel_len / 1500.0
        grbl_valido(self.l, name)
        open(os.path.join(GDIR, name), "w").write("\n".join(self.l) + "\n")
        return dict(file=name, min=self.t, cut=self.cut_len, plunges=self.plunges)


def grbl_valido(lineas, nombre):
    """Revision de sintaxis GRBL 1.1: comentarios sin anidar, solo palabras validas, < 80 caracteres."""
    import re
    for i, l in enumerate(lineas, 1):
        if len(l) > 79:
            raise SystemExit("%s:%d linea de mas de 79 caracteres" % (nombre, i))
        prof, resto = 0, ""
        for ch in l:
            if ch == "(":
                if prof:
                    raise SystemExit("%s:%d parentesis anidado en comentario: %s" % (nombre, i, l))
                prof = 1
            elif ch == ")":
                if not prof:
                    raise SystemExit("%s:%d ')' sin abrir: %s" % (nombre, i, l))
                prof = 0
            elif not prof:
                resto += ch
        if prof:
            raise SystemExit("%s:%d comentario sin cerrar: %s" % (nombre, i, l))
        resto = resto.split(";")[0].replace(" ", "").upper()
        if resto and not re.fullmatch(r"([GMXYZFSP]-?\d+(\.\d+)?)+", resto):
            raise SystemExit("%s:%d palabra no valida para GRBL: %s" % (nombre, i, l))


def helix_hole(g, x, y, d, depth, side):
    """Barreno con fresa plana: circulos concentricos bajando por pasos."""
    r = (d - P["mill_d"]) / 2
    z = 0.0
    while z > -depth + 1e-6:
        z = max(z - P["mill_step"], -depth)
        if r < 0.05:
            g.drill(x, y, side, -z, P["mill_plunge"])
            continue
        pts = [(x + r * math.cos(a * math.pi / 18), y + r * math.sin(a * math.pi / 18)) for a in range(37)]
        g.path(pts, z, P["mill_feed"] * 0.6, P["mill_plunge"], side)


# ---------------------------------------------------------------------------
# SIMULACION / RENDER
# ---------------------------------------------------------------------------
SC = 20.0   # px/mm
COL = dict(bg=(28, 32, 38), sub=(176, 138, 80), cu=(222, 140, 70), cu_net=(240, 168, 90),
           hole=(15, 15, 15), path=(60, 200, 255), tab=(255, 80, 80), outline=(255, 255, 255))


def geom_mask(geom, size, flip):
    """Mascara (L) de una geometria con huecos: cada poligono se rasteriza aparte."""
    from PIL import ImageChops
    geoms = geom.geoms if hasattr(geom, "geoms") else [geom]
    mask = Image.new("L", size, 0)

    def T(pts):
        return [(((W - x) if flip else x) * SC + 40, y * SC + 40) for (x, y) in pts]
    for g in geoms:
        if g.is_empty or g.geom_type != "Polygon":
            continue
        tmp = Image.new("L", size, 0)
        d = ImageDraw.Draw(tmp)
        d.polygon(T(g.exterior.coords), fill=255)
        for i in g.interiors:
            d.polygon(T(i.coords), fill=0)
        mask = ImageChops.lighter(mask, tmp)
    return mask


def render(side, remaining, hole_geom, paths, flip, title, extra=None):
    size = (int(W * SC) + 80, int(H * SC) + 130)
    img = Image.new("RGB", size, COL["bg"])
    img.paste(Image.new("RGB", size, COL["sub"]), mask=geom_mask(box(0, 0, W, H), size, flip))
    img.paste(Image.new("RGB", size, COL["cu"]), mask=geom_mask(remaining, size, flip))
    img.paste(Image.new("RGB", size, COL["hole"]), mask=geom_mask(hole_geom, size, flip))
    dr = ImageDraw.Draw(img)

    def T(x, y):
        return (((W - x) if flip else x) * SC + 40, y * SC + 40)
    if paths:
        for pth in paths:
            dr.line([T(*p) for p in pth], fill=COL["path"], width=1)
    if extra:
        extra(dr, T)
    try:
        f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 34)
    except Exception:
        f = ImageFont.load_default()
    dr.text((40, int(H * SC) + 60), title, fill=(240, 240, 240), font=f)
    return img


def main():
    os.makedirs(GDIR, exist_ok=True)
    os.makedirs(SDIR, exist_ok=True)
    net_polys, pads, vias, holes, keepouts = load()
    rep = []
    w = vbit_width(P["iso_depth"])
    rep.append("Genmitsu Cubiko - CAM y simulacion de la tarjeta %s (%.0f x %.0f mm)" % (D.PROJECT, W, H))
    rep.append("V-bit %.0f grados punta %.2f mm a %.2f mm de profundidad -> ancho de corte %.3f mm (3 pasadas al 50 %%)"
               % (P["vbit_angle"], P["vbit_tip"], P["iso_depth"], w))
    hole_geom = unary_union([Point(x, y).buffer(d / 2, resolution=12) for (x, y, d, _, _) in holes])
    results, jobs = {}, []
    iso = {}
    for side in ("B", "F"):
        copper = unary_union(list(net_polys[side].values()))
        paths, swept, _ = isolation(copper)
        clad = box(0, 0, W, H)
        # bajo la antena de la ESP32-B se quita el cobre que no pertenece a ninguna red
        # (las pistas que cruzan la zona se respetan)
        ant = unary_union(keepouts) if keepouts else Polygon()
        ant_clear = ant.difference(copper.buffer(P["mill_d"] / 2 + 0.25)) if not ant.is_empty else ant
        remaining = clad.difference(swept).difference(hole_geom).difference(ant_clear)
        iso[side] = (paths, swept, remaining, ant_clear)
    # ---------------- verificacion electrica ----------------
    comps = {}
    for side in ("B", "F"):
        rem = iso[side][2]
        comps[side] = list(rem.geoms) if hasattr(rem, "geoms") else [rem]
    from shapely.strtree import STRtree
    trees = {s: STRtree(comps[s]) for s in comps}
    parent = {}

    def find(a):
        parent.setdefault(a, a)
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a, b):
        parent[find(a)] = find(b)

    def comp_at(side, geom):
        idx = trees[side].query(geom)
        best, area = None, 0.0
        for i in idx:
            a = comps[side][i].intersection(geom).area
            if a > area:
                best, area = i, a
        return best

    # nets que toca cada pieza de cobre
    shorts = []
    for side in ("B", "F"):
        for i, c in enumerate(comps[side]):
            touched = [n for n, g in net_polys[side].items() if n and c.intersects(g) and c.intersection(g).area > 0.002]
            if len(touched) > 1:
                shorts.append((side, touched, c.representative_point().coords[0]))
    for v in vias:
        ring = Point(v["x"], v["y"]).buffer(v["d"] / 2).difference(Point(v["x"], v["y"]).buffer(v["drill"] / 2 + 0.01))
        a, b = comp_at("F", ring), comp_at("B", ring)
        if a is None or b is None:
            shorts.append(("via", [v["net"]], (v["x"], v["y"])))
            continue
        union(("F", a), ("B", b))
    opens, bad_ring = [], []
    by_net = {}
    for p in pads:
        if not p["net"]:
            continue
        ring = Point(p["x"], p["y"]).buffer(p["size"] / 2 * 0.95).difference(Point(p["x"], p["y"]).buffer(p["drill"] / 2 + 0.01))
        c = comp_at(p["side"], ring)
        if c is None:
            opens.append((p["ref"], p["num"], p["net"], "anillo destruido"))
            continue
        by_net.setdefault(p["net"], set()).add(find((p["side"], c)))
        if (p["size"] - p["drill"]) / 2 < 0.3:
            bad_ring.append((p["ref"], p["num"], (p["size"] - p["drill"]) / 2))
    for n, roots in by_net.items():
        roots = {find(r) for r in roots}
        if len(roots) > 1:
            opens.append(("-", "-", n, "%d piezas separadas" % len(roots)))
    rep.append("")
    rep.append("Pads: %d   vias (pines): %d   taladros: %d" % (len(pads), len(vias), len(holes)))
    rep.append("Piezas de cobre tras el fresado: B=%d  F=%d" % (len(comps["B"]), len(comps["F"])))
    rep.append("CORTOS: %d" % len(shorts))
    for s in shorts[:20]:
        rep.append("   %s redes %s cerca de (%.1f, %.1f)" % (s[0], ",".join(s[1]), s[2][0], s[2][1]))
    rep.append("REDES ABIERTAS: %d" % len(opens))
    for o in opens[:20]:
        rep.append("   %s.%s %s: %s" % o)
    rep.append("Anillos < 0.3 mm: %d" % len(bad_ring))
    ok = not shorts and not opens

    # ---------------- G-code ----------------
    def tag(prefix):
        return prefix
    # LADO 1 (B arriba): fresa de 1 mm -> alineacion, barrenos grandes, antena
    TM = "fresa tipo maiz 1.0 mm"
    g = G("LADO 1 (cara inferior arriba) - fresa de 1.0 mm: pines de alineacion, barrenos de 1.2 mm o mas y despeje de antena", TM)
    for (x, y) in ALIGN:
        helix_hole(g, x, y, P["align_d"], P["align_depth"], "B")
    big = [(x, y, d) for (x, y, d, npth, ref) in holes if d > P["drill_max"] and (round(x, 2), round(y, 2)) not in [(round(a, 2), round(b, 2)) for a, b in ALIGN]]
    for (x, y, d) in big:
        helix_hole(g, x, y, max(d, P["mill_d"]), P["drill_depth"], "B")
    for k in (iso["B"][3].geoms if hasattr(iso["B"][3], "geoms") else [iso["B"][3]]):
        for pth in pocket(k.buffer(P["mill_d"] / 2), P["mill_d"]):
            g.path(pth, -P["antenna_depth"], P["mill_feed"], P["mill_plunge"], "B")
    jobs.append(g.save("L1_1_fresa1mm_alineacion_barrenos_antena_B.nc"))
    TV = "V-bit 20 grados punta 0.1 mm"
    g = G("LADO 1 - aislamiento cara inferior (B.Cu), espejado", TV)
    for pth in iso["B"][0]:
        g.path(pth, -P["iso_depth"], P["iso_feed"], P["iso_plunge"], "B")
    jobs.append(g.save("L1_2_vbit_aislamiento_B.nc"))
    groups = {d: [] for d in P["drill_bits"]}
    for (x, y, d, npth, ref) in holes:
        if d > P["drill_max"]:
            continue
        bit = min(P["drill_bits"], key=lambda b: abs(b - d) if b <= d + 0.05 else 9 + b)
        groups[bit].append((x, y))
    for i, (bit, pts) in enumerate(sorted(groups.items()), 3):
        g = G("LADO 1 - taladros de %.1f mm (%d agujeros)" % (bit, len(pts)), "broca de PCB %.1f mm" % bit)
        cur = (0, 0)
        left = list(pts)
        while left:
            j = min(range(len(left)), key=lambda k: (left[k][0] - cur[0]) ** 2 + (left[k][1] - cur[1]) ** 2)
            cur = left.pop(j)
            g.drill(cur[0], cur[1], "B", P["drill_depth"], P["drill_feed"])
        jobs.append(g.save("L1_%d_broca%.1f.nc" % (i, bit)))
    # LADO 2 (F arriba)
    g = G("LADO 2 (cara superior arriba) - aislamiento F.Cu", TV)
    for pth in iso["F"][0]:
        g.path(pth, -P["iso_depth"], P["iso_feed"], P["iso_plunge"], "F")
    jobs.append(g.save("L2_1_vbit_aislamiento_F.nc"))
    g = G("LADO 2 - fresa de 1.0 mm: despeje de antena y contorno con %d puentes" % P["n_tabs"], TM)
    for k in (iso["F"][3].geoms if hasattr(iso["F"][3], "geoms") else [iso["F"][3]]):
        for pth in pocket(k.buffer(P["mill_d"] / 2), P["mill_d"]):
            g.path(pth, -P["antenna_depth"], P["mill_feed"], P["mill_plunge"], "F")
    ring, L, tab_d = outline_paths()
    z = 0.0
    while z > -P["outline_depth"] + 1e-6:
        z = max(z - P["outline_depth"] / P["outline_passes"], -P["outline_depth"])
        if z < -(P["thickness"] - P["tab_h"]) - 1e-6:
            # en las pasadas profundas se sube sobre cada pestana
            segs, last = [], 0.0
            for d0 in sorted(tab_d):
                a, b = d0 - (P["tab_w"] + P["mill_d"]) / 2, d0 + (P["tab_w"] + P["mill_d"]) / 2
                segs.append((last, a))
                last = b
            segs.append((last, L.length))
            for (a, b) in segs:
                if b - a < 0.1:
                    continue
                n = max(2, int((b - a) / 1.0))
                pts = [L.interpolate(a + (b - a) * t / n).coords[0] for t in range(n + 1)]
                g.path(pts, z, P["mill_feed"], P["mill_plunge"], "F")
        else:
            g.path(ring, z, P["mill_feed"], P["mill_plunge"], "F")
    jobs.append(g.save("L2_2_fresa1mm_antena_contorno_F.nc"))

    # ---------------- render ----------------
    title_b = "LADO 1 - cara INFERIOR vista desde arriba en la maquina (espejada)"
    title_f = "LADO 2 - cara SUPERIOR vista desde arriba"
    render("B", iso["B"][2], hole_geom, None, True, title_b + "  -  cobre tras el fresado").save(os.path.join(SDIR, "lado1_B_resultado.png"))
    render("F", iso["F"][2], hole_geom, None, False, title_f + "  -  cobre tras el fresado").save(os.path.join(SDIR, "lado2_F_resultado.png"))
    render("B", iso["B"][2], hole_geom, iso["B"][0], True, title_b + "  -  trayectorias del V-bit").save(os.path.join(SDIR, "lado1_B_trayectorias.png"))

    def outline_extra(dr, T):
        dr.line([T(*p) for p in ring], fill=COL["outline"], width=3)
        for d0 in tab_d:
            x, y = L.interpolate(d0).coords[0]
            cx, cy = T(x, y)
            dr.rectangle([cx - 30, cy - 30, cx + 30, cy + 30], outline=COL["tab"], width=5)
    render("F", iso["F"][2], hole_geom, iso["F"][0], False, title_f + "  -  V-bit (azul), contorno y pestanas (rojo)",
           outline_extra).save(os.path.join(SDIR, "lado2_F_trayectorias.png"))
    # acercamiento a la zona mas densa (pines de la ESP32-A y bornas)
    for side, flip, nm in (("B", True, "lado1_B_zoom.png"),):
        img = Image.open(os.path.join(SDIR, "lado1_B_trayectorias.png"))
        x0 = ((W - 50) if flip else 0) * SC + 40
        img.crop((int(x0), int(10 * SC), int(x0 + 50 * SC), int(80 * SC))).save(os.path.join(SDIR, nm))

    # ---------------- archivos para FlatCAM / revision ----------------
    import subprocess, shutil
    gb = os.path.join(OUTDIR, "gerbers")
    shutil.rmtree(gb, ignore_errors=True)
    os.makedirs(gb)
    run = lambda *a: subprocess.run(["kicad-cli", *a], check=True, capture_output=True)
    run("pcb", "export", "gerbers", "-o", gb + "/", "--layers", "F.Cu,B.Cu,Edge.Cuts", "--use-drill-file-origin", PCB)
    run("pcb", "export", "drill", "-o", gb + "/", "--format", "excellon", "--drill-origin", "plot",
        "--generate-map", "--map-format", "pdf", PCB)
    run("pcb", "export", "pdf", "-o", os.path.join(OUTDIR, "cobre_inferior_espejo_1a1.pdf"), "--layers", "B.Cu,Edge.Cuts",
        "--black-and-white", "--mirror", PCB)
    run("pcb", "export", "pdf", "-o", os.path.join(OUTDIR, "cobre_superior_1a1.pdf"), "--layers", "F.Cu,Edge.Cuts",
        "--black-and-white", PCB)
    run("pcb", "export", "pdf", "-o", os.path.join(OUTDIR, "plantilla_montaje_1a1.pdf"), "--layers", "F.Fab,F.SilkS,Edge.Cuts",
        "--black-and-white", PCB)
    shutil.copy(os.path.join(HERE, "..", D.PROJECT, "bom.csv"), os.path.join(OUTDIR, "bom.csv"))
    # hoja resumen: las dos caras lado a lado
    a = Image.open(os.path.join(SDIR, "lado1_B_resultado.png"))
    b2 = Image.open(os.path.join(SDIR, "lado2_F_resultado.png"))
    sheet = Image.new("RGB", (a.width + b2.width + 40, a.height + 120), COL["bg"])
    sheet.paste(a, (0, 120))
    sheet.paste(b2, (a.width + 40, 120))
    try:
        fb = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 54)
    except Exception:
        fb = ImageFont.load_default()
    ImageDraw.Draw(sheet).text((40, 30), "Rover Controller Cubiko - simulacion del fresado: %s" %
                               ("0 cortos, 0 redes abiertas" if ok else "REVISAR"), fill=(240, 240, 240), font=fb)
    sheet.thumbnail((3000, 3000))
    sheet.save(os.path.join(SDIR, "resumen_simulacion.png"))

    rep.append("")
    rep.append("TRABAJOS (en este orden):")
    tot = 0.0
    for j in jobs:
        rep.append("  %-50s %6.1f min   corte %7.0f mm   bajadas %d" % (j["file"], j["min"], j["cut"], j["plunges"]))
        tot += j["min"]
    rep.append("  Tiempo total de maquina estimado: %.0f min (sin cambios de herramienta ni mapa de alturas)" % tot)
    rep.append("")
    rep.append("RESULTADO: %s" % ("OK - el fresado deja todas las redes completas y sin cortos" if ok else "REVISAR"))
    open(os.path.join(SDIR, "reporte.txt"), "w").write("\n".join(rep) + "\n")
    print("\n".join(rep))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
