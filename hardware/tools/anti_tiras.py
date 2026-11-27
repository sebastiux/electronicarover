# -*- coding: utf-8 -*-
"""
Relleno anti-tiras para fresar con UNA pasada de una fresa de 1.0 mm.

Un CAM que desplaza todo el cobre junto (LPKF CircuitPro, FlatCAM...) da una pasada a medio
diametro de cada orilla de cobre. Si entre dos cobres hay mas de 2 fresas (2.0 mm) las dos
pasadas no se juntan y en medio queda una TIRA de cobre suelta. Este paso busca esos huecos y
los rellena con cobre unido a una de las redes vecinas (de preferencia GND), a CLR de las demas:
el hueco queda de CLR (1.3 mm) y la fresa lo limpia completo. Solo rellena lo angosto
(menos de ANCHO_MIN); las islas anchas de cobre sin uso se quedan como estan.

Uso: ROVER_VARIANT=traccion python3 anti_tiras.py   (lo llama generate.py --route)
"""
import os, sys
_argv = sys.argv
sys.argv = sys.argv[:1]
import cubiko_cam as C
sys.argv = _argv
import pcbnew
from shapely.geometry import Point, box
from shapely.ops import unary_union

D = C.D
T = getattr(D, "UNA_FRESA", 1.0)
CLR = getattr(D, "CLR", 1.3)
BORDE = getattr(D, "BORDE", 0.5)
ANCHO_MIN = 1.5            # lo que quedaria suelto con menos de este ancho se rellena
O = 30.0                   # origen de la tarjeta en el .kicad_pcb
MARCA = "anti-tira"        # nombre de las zonas de relleno (para rehacerlas)


def tiras(todo, alcance=T):
    """Cobre que quedaria suelto y angosto tras fresar `alcance` mm desde cada orilla de cobre
    (T con una pasada por lado, 1.5 T con dos). todo = cobre de todas las redes y pads sin red."""
    copper = unary_union([g for g in todo.values() if not g.is_empty])
    marco = box(BORDE, BORDE, C.W - BORDE, C.H - BORDE)
    libre = marco.difference(copper.buffer(alcance, resolution=12))
    if libre.is_empty:
        return []
    ancho = libre.buffer(-ANCHO_MIN / 2, resolution=8).buffer(ANCHO_MIN / 2 + 0.02, resolution=8)
    fino = libre.difference(ancho)
    out = []
    for g in (fino.geoms if hasattr(fino, "geoms") else [fino]):
        if g.geom_type != "Polygon" or g.area < 0.2:
            continue
        if g.distance(marco.exterior) < 0.1:      # pegado al margen de la orilla: es parte del marco
            continue
        out.append(g)
    return out


def _carga_cobre():
    """C.load() con reintentos: pcbnew a veces devuelve un tablero a medio envolver al recargar."""
    for _ in range(6):
        try:
            return C.load()
        except AttributeError:
            continue
    return C.load()


def _carga_tablero():
    for _ in range(6):
        b = pcbnew.LoadBoard(C.PCB)
        C._TABLEROS.append(b)
        if hasattr(b, "Zones"):
            return b
    raise RuntimeError("pcbnew no pudo cargar " + C.PCB)


def main():
    board = _carga_tablero()
    viejas = [z for z in board.Zones() if z.GetZoneName() == MARCA]
    for z in viejas:
        board.Remove(z)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(C.PCB, board)
    if viejas:
        # tras quitar zonas, pcbnew ya no recarga bien el tablero en este proceso: seguir en uno nuevo
        sys.stdout.flush()
        os.execv(sys.executable, [sys.executable] + _argv)
    total = 0
    # primero lo que dejaria una pasada por lado y despues lo que dejarian dos (huecos de 3 a 4.5 mm)
    for vuelta in range(10):
        alcance = T if vuelta < 5 else 1.5 * T
        net_polys = _carga_cobre()[0]
        B = {n: g for n, g in net_polys["B"].items() if n and not g.is_empty}
        ts = tiras(net_polys["B"], alcance)
        if not ts:
            if vuelta < 5:
                continue
            break
        board = _carga_tablero()
        for t in ts:
            d = sorted((g.distance(t), n) for n, g in B.items())
            dmin = d[0][0]
            cerca = [n for dd, n in d if dd <= dmin + 0.25]
            red = "GND" if "GND" in cerca else cerca[0]
            # crece hasta tocar el cobre de su red; el relleno de KiCad lo recorta a CLR de las demas
            p = t.buffer(dmin + 0.15, resolution=8).intersection(box(BORDE, BORDE, C.W - BORDE, C.H - BORDE))
            for q in (p.geoms if hasattr(p, "geoms") else [p]):
                if q.geom_type != "Polygon" or q.area < 0.05:
                    continue
                z = pcbnew.ZONE(board)
                z.SetLayer(pcbnew.B_Cu)
                z.SetNet(board.FindNet(red))
                z.SetZoneName(MARCA)
                ol = z.Outline()
                ol.NewOutline()
                for (x, y) in list(q.simplify(0.02).exterior.coords)[:-1]:
                    ol.Append(pcbnew.FromMM(x + O), pcbnew.FromMM(y + O))
                z.SetLocalClearance(pcbnew.FromMM(CLR))
                z.SetMinThickness(pcbnew.FromMM(1.0))
                z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
                z.SetAssignedPriority(5)
                z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
                board.Add(z)
                total += 1
        pcbnew.ZONE_FILLER(board).Fill(board.Zones())
        pcbnew.SaveBoard(C.PCB, board)
    # la poda final va en un proceso nuevo (ver nota de arriba sobre recargar el tablero)
    sys.stdout.flush()
    os.execv(sys.executable, [sys.executable, _argv[0], "--poda=0", "--total=%d" % total])


def _anillos(z):
    ps = z.GetFilledPolysList(pcbnew.B_Cu)
    for i in range(ps.OutlineCount()):
        for o in [ps.Outline(i)] + [ps.Hole(i, h) for h in range(ps.HoleCount(i))]:
            yield [(pcbnew.ToMM(o.CPoint(k).x) - O, pcbnew.ToMM(o.CPoint(k).y) - O) for k in range(o.PointCount())]


def _punta_aguda(z, grados=20.0):
    """True si el relleno de la zona tiene una punta de menos de `grados` (astilla de cobre)."""
    import math
    for pts in _anillos(z):
        n = len(pts)
        for k in range(n):
            a, p, c = pts[k - 1], pts[k], pts[(k + 1) % n]
            v1, v2 = (a[0] - p[0], a[1] - p[1]), (c[0] - p[0], c[1] - p[1])
            l1, l2 = math.hypot(*v1), math.hypot(*v2)
            if l1 < 0.02 or l2 < 0.02:
                continue
            cs = max(-1.0, min(1.0, (v1[0] * v2[0] + v1[1] * v2[1]) / (l1 * l2)))
            if math.degrees(math.acos(cs)) < grados:
                return True
    return False


def poda(vuelta, total):
    """Quita los rellenos que dejan una astilla (punta aguda) o una isla sin conexion: vale mas una
    tira suelta junto a un pad que un pico de cobre que se levanta al fresar."""
    import re, tempfile
    from shapely.geometry import Polygon
    board = _carga_tablero()
    rep = os.path.join(tempfile.gettempdir(), "anti_tiras_%s.rpt" % D.PROJECT)
    pcbnew.WriteDRCReport(board, rep, pcbnew.EDA_UNITS_MILLIMETRES, True)
    txt = open(rep).read()
    islas = [Point(float(x) - O, float(y) - O)
             for x, y in re.findall(r"\[isolated_copper\][^@]*@\(([\d.]+) mm, ([\d.]+) mm\)", txt)]
    malas = []
    for z in board.Zones():
        if z.GetZoneName() != MARCA:
            continue
        ol = z.Outline().Outline(0)
        poly = Polygon([(pcbnew.ToMM(ol.CPoint(k).x) - O, pcbnew.ToMM(ol.CPoint(k).y) - O)
                        for k in range(ol.PointCount())]).buffer(0)
        if _punta_aguda(z) or any(poly.distance(q) < 0.05 for q in islas):
            malas.append(z)
    if malas and vuelta < 4:
        for z in malas:
            board.Remove(z)
        pcbnew.ZONE_FILLER(board).Fill(board.Zones())
        pcbnew.SaveBoard(C.PCB, board)
        sys.stdout.flush()
        os.execv(sys.executable, [sys.executable, _argv[0], "--poda=%d" % (vuelta + 1), "--total=%d" % (total - len(malas))])
    net_polys = _carga_cobre()[0]
    for nombre, alcance in (("1 pasada", T), ("2 pasadas", 1.5 * T)):
        quedan = tiras(net_polys["B"], alcance)
        print("Relleno anti-tiras: %d zonas; tiras angostas que quedan con %s por lado: %d %s"
              % (total, nombre, len(quedan), ["(%.1f, %.1f) %.2f mm2" % (g.representative_point().x, g.representative_point().y, g.area) for g in quedan[:8]]))


if __name__ == "__main__":
    args = dict(a.lstrip("-").split("=") for a in _argv[1:] if "=" in a)
    if "poda" in args:
        poda(int(args["poda"]), int(args["total"]))
    else:
        main()
