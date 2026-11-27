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


def tiras(todo):
    """Cobre que quedaria suelto y angosto tras una pasada de fresa T por cada orilla.
    todo = cobre de todas las redes, tambien el de los pads sin red."""
    copper = unary_union([g for g in todo.values() if not g.is_empty])
    marco = box(BORDE, BORDE, C.W - BORDE, C.H - BORDE)
    libre = marco.difference(copper.buffer(T, resolution=12))
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


def main():
    board = pcbnew.LoadBoard(C.PCB)
    for z in list(board.Zones()):
        if z.GetZoneName() == MARCA:
            board.Remove(z)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(C.PCB, board)
    total = 0
    for vuelta in range(5):
        net_polys = C.load()[0]
        B = {n: g for n, g in net_polys["B"].items() if n and not g.is_empty}
        ts = tiras(net_polys["B"])
        if not ts:
            break
        board = pcbnew.LoadBoard(C.PCB)
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
                z.SetMinThickness(pcbnew.FromMM(0.3))
                z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
                z.SetAssignedPriority(5)
                z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
                board.Add(z)
                total += 1
        pcbnew.ZONE_FILLER(board).Fill(board.Zones())
        pcbnew.SaveBoard(C.PCB, board)
    net_polys = C.load()[0]
    quedan = tiras(net_polys["B"])
    print("Relleno anti-tiras: %d zonas; tiras angostas que quedan: %d %s"
          % (total, len(quedan), ["(%.1f, %.1f) %.2f mm2" % (g.representative_point().x, g.representative_point().y, g.area) for g in quedan[:8]]))


if __name__ == "__main__":
    main()
