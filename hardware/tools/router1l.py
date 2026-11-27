# -*- coding: utf-8 -*-
"""
Ruteador para PCB de UNA sola capa de cobre (B.Cu).

- Todas las pistas van en B.Cu (cara de soldadura).
- Cuando una conexion no se puede hacer sin cruzar otra pista, coloca un
  PUENTE DE ALAMBRE recto por la cara de componentes. En KiCad el puente se
  representa como un segmento en F.Cu + dos vias (los dos barrenos donde se
  suelda el alambre). F.Cu NO se fabrica: solo sirve de guia de montaje.
- Algoritmo: rejilla de 0.25 mm, A* con 8 direcciones, holguras por clase de
  red mediante transformada de distancia, arbol tipo Prim por red,
  suavizado de trayectoria por linea de vista.

Requiere numpy y scipy en el Python de KiCad.
"""
import heapq
import math
import time

import numpy as np
import pcbnew
from scipy import ndimage

G = 0.25            # paso de la rejilla (mm)
RM = 0.75 * G       # margen de rasterizado

JUMPER_PAD = 2.0    # diametro del pad del barreno del puente
JUMPER_DRILL = 1.0  # taladro (alambre hasta AWG18)
JUMPER_WIRE = 0.8   # ancho del alambre en F.Cu (guia)
EDGE_EXTRA = 0.0    # mm extra de margen a la orilla (lo fija generate.py desde D.BORDE)
JUMPER_CLR = 0.3
VIA_COST_MM = 14.0       # costo de cada barreno de puente (mm equivalentes)
WIRE_COST_FACTOR = 2.5   # el alambre cuesta 2.5x por mm frente a la pista de cobre
HALO_COST = 3.0          # costo extra por celda pegada a pads de otras redes


def mm(v):
    return pcbnew.ToMM(v)


class Grid:
    def __init__(self, board):
        bb = board.GetBoardEdgesBoundingBox()
        self.x0 = mm(bb.GetX()) - 1.0
        self.y0 = mm(bb.GetY()) - 1.0
        self.bx0, self.by0 = mm(bb.GetX()), mm(bb.GetY())
        self.bx1, self.by1 = self.bx0 + mm(bb.GetWidth()), self.by0 + mm(bb.GetHeight())
        self.nx = int(math.ceil((mm(bb.GetWidth()) + 2.0) / G)) + 1
        self.ny = int(math.ceil((mm(bb.GetHeight()) + 2.0) / G)) + 1
        self.B = np.zeros((self.ny, self.nx), np.int32)
        self.E = np.zeros((self.ny, self.nx), np.int32)   # cobre "exacto" (centros dentro del cobre)
        self.F = np.zeros((self.ny, self.nx), np.int32)
        ys = self.y0 + np.arange(self.ny) * G
        xs = self.x0 + np.arange(self.nx) * G
        self.XX, self.YY = np.meshgrid(xs, ys)

    def ij(self, x, y):
        return int(round((y - self.y0) / G)), int(round((x - self.x0) / G))

    def xy(self, i, j):
        return self.x0 + j * G, self.y0 + i * G

    def window(self, xa, ya, xb, yb, pad):
        i0 = max(0, int((min(ya, yb) - pad - self.y0) / G) - 1)
        i1 = min(self.ny, int((max(ya, yb) + pad - self.y0) / G) + 2)
        j0 = max(0, int((min(xa, xb) - pad - self.x0) / G) - 1)
        j1 = min(self.nx, int((max(xa, xb) + pad - self.x0) / G) + 2)
        return i0, i1, j0, j1

    def mark_circle(self, arr, x, y, r, val, only_free=False, rm=RM):
        i0, i1, j0, j1 = self.window(x, y, x, y, r + abs(rm))
        X, Y = self.XX[i0:i1, j0:j1], self.YY[i0:i1, j0:j1]
        m = (X - x) ** 2 + (Y - y) ** 2 <= (r + rm) ** 2
        sub = arr[i0:i1, j0:j1]
        if only_free:
            m &= sub == 0
        sub[m] = val

    def mark_rect(self, arr, xa, ya, xb, yb, val, only_free=False, rm=RM):
        i0, i1, j0, j1 = self.window(xa, ya, xb, yb, abs(rm))
        X, Y = self.XX[i0:i1, j0:j1], self.YY[i0:i1, j0:j1]
        m = (X >= xa - rm) & (X <= xb + rm) & (Y >= ya - rm) & (Y <= yb + rm)
        sub = arr[i0:i1, j0:j1]
        if only_free:
            m &= sub == 0
        sub[m] = val

    def mark_seg(self, arr, xa, ya, xb, yb, w, val, rm=RM):
        r = w / 2 + rm
        i0, i1, j0, j1 = self.window(xa, ya, xb, yb, r)
        X, Y = self.XX[i0:i1, j0:j1], self.YY[i0:i1, j0:j1]
        dx, dy = xb - xa, yb - ya
        L2 = dx * dx + dy * dy
        if L2 == 0:
            t = np.zeros_like(X)
        else:
            t = np.clip(((X - xa) * dx + (Y - ya) * dy) / L2, 0, 1)
        d2 = (X - (xa + t * dx)) ** 2 + (Y - (ya + t * dy)) ** 2
        arr[i0:i1, j0:j1][d2 <= r * r] = val


class Router:
    def __init__(self, board, classes, no_jumper_classes=("BATT", "MOTOR"), log=print, reserved=(),
                 two_layer=False, via_sizes=None, pad_side=None, via_cost_mm=3.0,
                 no_via_under_parts=False, via_pad_gap=0.0, min_w=0.5):
        self.board = board
        # pad_side(ref) -> "B", "F" o "BF": cara(s) por la que se puede soldar/conectar
        # cada pad. En PCB SIN metalizado (prototipado) un pad solo conecta por la
        # cara donde se suelda el componente.
        self.pad_side = pad_side or (lambda ref: "BF")
        self.via_cost_mm = via_cost_mm
        self.no_via_under_parts = no_via_under_parts
        self.via_pad_gap = via_pad_gap      # cobre libre minimo entre el anillo de un puente y CUALQUIER pad
        self.min_w = min_w                  # ancho minimo de pista (nunca se adelgaza por debajo)
        self.jw = max(JUMPER_WIRE, min_w)   # guia del cable en F.Cu: al menos el ancho minimo
        # two_layer=True: F.Cu es una capa de cobre real (PCB de 2 capas, vias normales)
        self.two_layer = two_layer
        self.via_sizes = via_sizes or {}
        self.treesF = {}
        self.classes = classes  # name -> (width, clearance)
        self.no_jumper = set(no_jumper_classes)
        self.log = log
        self.g = Grid(board)
        self.netcodes = {}
        self.jumpers = []
        self.failed = []
        self.trees = {}
        self._build_obstacles()
        # corredores reservados: (x0, y0, x1, y1, clases_permitidas) en mm absolutos
        self.reserved = []
        for (x0, y0, x1, y1, allowed) in reserved:
            m = (self.g.XX >= x0) & (self.g.XX <= x1) & (self.g.YY >= y0) & (self.g.YY <= y1)
            self.reserved.append((m, set(allowed)))
        self._bridge_twins()
        self.protected = set(t.m_Uuid.AsString() for t in board.GetTracks())

    def _rebuild(self):
        twins = self.twins
        # misma geometria: solo se limpian las rejillas (evita volver a pedir el bbox)
        for arr in (self.g.B, self.g.F, self.g.E):
            arr[:] = 0
        self._build_obstacles()
        self.twins = twins

    def rip(self, names):
        """Levanta (borra) las pistas/puentes ruteados de las redes dadas."""
        b = self.board
        names = set(names)
        for t in list(b.GetTracks()):
            if t.GetNetname() in names and t.m_Uuid.AsString() not in self.protected:
                b.Remove(t)
        for n in names:
            self.trees.pop(n, None)
            self.treesF.pop(n, None)
        self.jumpers = [j for j in self.jumpers if j[0] not in names]
        self._rebuild()

    def blockers(self, pad, radius=3.5, own=None):
        g = self.g
        x, y = mm(pad.GetPosition().x), mm(pad.GetPosition().y)
        i0, i1, j0, j1 = g.window(x, y, x, y, radius)
        sub = g.B[i0:i1, j0:j1]
        codes = set(int(c) for c in np.unique(sub) if c > 0 and c != own)
        out = []
        for name, ni in self.board.GetNetsByName().items():
            if ni.GetNetCode() in codes:
                out.append(str(name))
        return out

    # ------------------------------------------------------------------
    def code(self, netname):
        return self.board.GetNetsByName()[netname].GetNetCode()

    def _pad_shape(self, pad):
        c = pad.GetPosition()
        x, y = mm(c.x), mm(c.y)
        if pad.GetShape() == pcbnew.PAD_SHAPE_CIRCLE:
            return ("c", x, y, mm(pad.GetSize().x) / 2)
        bb = pad.GetBoundingBox()
        return ("r", mm(bb.GetX()), mm(bb.GetY()), mm(bb.GetX() + bb.GetWidth()), mm(bb.GetY() + bb.GetHeight()))

    def _mark_shape(self, arr, shp, val, rm=RM):
        if shp[0] == "c":
            self.g.mark_circle(arr, shp[1], shp[2], shp[3], val, rm=rm)
        else:
            self.g.mark_rect(arr, shp[1], shp[2], shp[3], shp[4], val, rm=rm)

    def _mark_hole(self, x, y, r):
        m = np.zeros(self.g.B.shape, np.int8)
        self.g.mark_circle(m, x, y, r + JUMPER_DRILL / 2 + 0.35, 1)
        self.noVia |= m.astype(bool)

    def _build_obstacles(self):
        g = self.g
        b = self.board
        # fuera de la tarjeta (con esquinas redondeadas de 3 mm)
        R = 3.0
        e = EDGE_EXTRA          # el cobre no se acerca a la orilla: clearance de la clase + e
        out = (g.XX < g.bx0 + e) | (g.XX > g.bx1 - e) | (g.YY < g.by0 + e) | (g.YY > g.by1 - e)
        for (cx, cy) in [(g.bx0 + R, g.by0 + R), (g.bx1 - R, g.by0 + R), (g.bx0 + R, g.by1 - R), (g.bx1 - R, g.by1 - R)]:
            corner = (np.abs(g.XX - cx) <= R + 0.01) & (np.abs(g.YY - cy) <= R + 0.01)
            corner &= (np.sign(g.XX - cx) == np.sign(cx - (g.bx0 + g.bx1) / 2)) & \
                       (np.sign(g.YY - cy) == np.sign(cy - (g.by0 + g.by1) / 2))
            out |= corner & ((g.XX - cx) ** 2 + (g.YY - cy) ** 2 > max(R - e, 0.0) ** 2)
        g.B[out] = -1
        g.F[out] = -1
        self.pads_by_net = {}
        self.twins = []
        seen = {}
        for fp in b.GetFootprints():
            ref = fp.GetReference()
            # los puentes son alambre AISLADO: pueden pasar por encima de componentes;
            # solo se evitan pads y barrenos (marcados abajo)
            for pad in fp.Pads():
                shp = self._pad_shape(pad)
                if pad.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH or not pad.GetNetname():
                    if pad.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
                        shp = ("c", mm(pad.GetPosition().x), mm(pad.GetPosition().y), mm(pad.GetDrillSize().x) / 2)
                    self._mark_shape(g.B, shp, -1)
                    self._mark_shape(g.F, shp, -1)
                    continue
                code = pad.GetNetCode()
                side = self.pad_side(ref)
                self._mark_shape(g.B, shp, code if "B" in side else -1)
                self._mark_shape(g.F, shp, code if "F" in side else -1)
                if "B" in side:
                    self._mark_shape(g.E, shp, code, rm=-0.06)
                key = (ref, pad.GetNumber())
                if key in seen:
                    self.twins.append((seen[key], pad))
                    continue
                seen[key] = pad
                self.pads_by_net.setdefault(pad.GetNetname(), []).append((pad, shp))
        self.P = g.B.copy()   # solo pads (para el costo de "halo")
        # mapa de barrenos: donde NO se puede poner el barreno de un puente
        self.noVia = np.zeros(g.B.shape, bool)
        for fp in b.GetFootprints():
            for pad in fp.Pads():
                if pad.GetDrillSize().x > 0:
                    self._mark_hole(mm(pad.GetPosition().x), mm(pad.GetPosition().y), mm(pad.GetDrillSize().x) / 2)
                if self.via_pad_gap > 0:
                    # tambien los pads de la MISMA red: el barreno del cable no se encima en un pad
                    rp = max(mm(pad.GetSize().x), mm(pad.GetSize().y)) / 2
                    m = np.zeros(g.B.shape, np.int8)
                    g.mark_circle(m, mm(pad.GetPosition().x), mm(pad.GetPosition().y),
                                  rp + JUMPER_PAD / 2 + 0.2 + self.via_pad_gap, 1)
                    self.noVia |= m.astype(bool)
            # el pin soldado de una via estorba bajo componentes de perfil bajo
            ref = fp.GetReference()
            if self.no_via_under_parts and not (ref.startswith("U") or ref.startswith("H")):
                cyd = fp.GetCourtyard(pcbnew.F_CrtYd)
                if cyd.OutlineCount():
                    bb = cyd.BBox()
                    m = np.zeros(g.B.shape, np.int8)
                    # el anillo de la via (radio 1.1) + 0.3 mm libres para el cautin al soldar el pin arriba
                    g.mark_rect(m, mm(bb.GetX()), mm(bb.GetY()), mm(bb.GetX() + bb.GetWidth()),
                                mm(bb.GetY() + bb.GetHeight()), 1, rm=1.4)
                    self.noVia |= m.astype(bool)
        # pistas y vias ya existentes (permite rutear de forma incremental)
        for t in b.GetTracks():
            code = t.GetNetCode()
            if t.GetClass() == "PCB_VIA":
                p = t.GetPosition()
                for arr in (g.B, g.F):
                    g.mark_circle(arr, mm(p.x), mm(p.y), mm(t.GetWidth()) / 2, code)
                g.mark_circle(g.E, mm(p.x), mm(p.y), mm(t.GetWidth()) / 2, code, rm=-0.06)
                self._mark_hole(mm(p.x), mm(p.y), JUMPER_DRILL / 2)
                if self.via_pad_gap > 0:      # barrenos pre-trazados: ningun cable nuevo se les encima
                    m = np.zeros(g.B.shape, np.int8)
                    g.mark_circle(m, mm(p.x), mm(p.y), mm(t.GetWidth()) / 2 + JUMPER_PAD / 2 + 0.2 + self.via_pad_gap, 1)
                    self.noVia |= m.astype(bool)
            else:
                arr = g.B if t.GetLayer() == pcbnew.B_Cu else g.F
                a, c = t.GetStart(), t.GetEnd()
                g.mark_seg(arr, mm(a.x), mm(a.y), mm(c.x), mm(c.y), mm(t.GetWidth()), code)
                if t.GetLayer() == pcbnew.B_Cu:
                    g.mark_seg(g.E, mm(a.x), mm(a.y), mm(c.x), mm(c.y), mm(t.GetWidth()), code, rm=-0.06)
        # zonas de exclusion (antenas)
        for z in b.Zones():
            if z.GetIsRuleArea() and (z.GetDoNotAllowTracks() or z.GetDoNotAllowVias()):
                bb = z.GetBoundingBox()
                if not z.GetDoNotAllowTracks():
                    # solo prohibe barrenos de puente: se marca en F (capa de alambres)
                    g.mark_rect(g.F, mm(bb.GetX()), mm(bb.GetY()), mm(bb.GetX() + bb.GetWidth()),
                                mm(bb.GetY() + bb.GetHeight()), -1)
                    continue
                bb = z.GetBoundingBox()
                g.mark_rect(g.B, mm(bb.GetX()), mm(bb.GetY()), mm(bb.GetX() + bb.GetWidth()),
                            mm(bb.GetY() + bb.GetHeight()), -1)
                g.mark_rect(g.F, mm(bb.GetX()), mm(bb.GetY()), mm(bb.GetX() + bb.GetWidth()),
                            mm(bb.GetY() + bb.GetHeight()), -1)

    def _bridge_twins(self):
        """Une los pads duplicados (fila doble del ESP32) antes de rutear nada."""
        g, b = self.g, self.board
        for p1, p2 in self.twins:
            a, c = p1.GetPosition(), p2.GetPosition()
            t = pcbnew.PCB_TRACK(b)
            t.SetStart(a)
            t.SetEnd(c)
            wt = max(0.8, self.min_w)
            t.SetWidth(pcbnew.FromMM(wt))
            t.SetLayer(pcbnew.B_Cu)
            t.SetNet(p1.GetNet())
            b.Add(t)
            g.mark_seg(g.B, mm(a.x), mm(a.y), mm(c.x), mm(c.y), wt, p1.GetNetCode())
            g.mark_seg(g.E, mm(a.x), mm(a.y), mm(c.x), mm(c.y), wt, p1.GetNetCode(), rm=-0.06)

    # ------------------------------------------------------------------
    def _dist(self, arr, code):
        foreign = (arr != 0) & (arr != code)
        return ndimage.distance_transform_edt(~foreign) * G

    def _pad_maxw(self, shp, dist, clr):
        x, y = (shp[1], shp[2]) if shp[0] == "c" else ((shp[1] + shp[3]) / 2, (shp[2] + shp[4]) / 2)
        i, j = self.g.ij(x, y)
        return 2 * (dist[i, j] - clr - RM - 0.05)

    def route_net(self, name, cls, pad_filter=None, relaxed=False):
        w_cls, clr = self.classes[cls]
        code = self.code(name)
        pads = self.pads_by_net.get(name, [])
        if len(pads) < 2:
            return
        self.relaxed = relaxed
        allow_j = cls not in self.no_jumper
        # arbol tipo Prim desde el pad mas grande
        def size(s):
            return 2 * s[3] if s[0] == "c" else max(s[3] - s[1], s[4] - s[2])

        def center(s):
            return (s[1], s[2]) if s[0] == "c" else ((s[1] + s[3]) / 2, (s[2] + s[4]) / 2)

        if name not in self.trees:
            order = sorted(range(len(pads)), key=lambda k: -size(pads[k][1]))
            # arbol inicial = cobre ya existente conectado al primer pad (pistas pre-trazadas)
            lab, _ = ndimage.label(self.g.E == code, structure=np.ones((3, 3)))
            c0 = center(pads[order[0]][1])
            i0, j0 = self.g.ij(*c0)
            t = np.zeros(self.g.B.shape, np.int8)
            done0 = {order[0]}
            pts0 = [c0]
            if lab[i0, j0]:
                t[lab == lab[i0, j0]] = 1
                for k2, (p2, s2) in enumerate(pads):
                    ii, jj = self.g.ij(*center(s2))
                    if lab[ii, jj] == lab[i0, j0]:
                        done0.add(k2)
                        pts0.append(center(s2))
            elif "B" in self.pad_side(pads[order[0]][0].GetParent().GetReference()):
                self._mark_shape(t, pads[order[0]][1], 1, rm=-0.06)
            self.trees[name] = [t, done0, pts0]
            tf = np.zeros(self.g.B.shape, np.int8)
            for k2 in done0:
                if "F" in self.pad_side(pads[k2][0].GetParent().GetReference()):
                    self._mark_shape(tf, pads[k2][1], 1, rm=-0.06)
            # vias ya existentes de esta red conectadas al arbol: tambien sirven en F
            if lab[i0, j0]:
                for t2 in self.board.GetTracks():
                    if t2.GetClass() == "PCB_VIA" and t2.GetNetCode() == code:
                        vx, vy = mm(t2.GetPosition().x), mm(t2.GetPosition().y)
                        vi, vj = self.g.ij(vx, vy)
                        if lab[vi, vj] == lab[i0, j0]:
                            self.g.mark_circle(tf, vx, vy, mm(t2.GetWidth()) / 2, 1, rm=-0.06)
            self.treesF[name] = tf
        self.tree, done, tree_pts = self.trees[name]
        self.treeF = self.treesF[name]
        remaining = [k for k in range(len(pads)) if k not in done
                     and (pad_filter is None or pad_filter(pads[k][0]))]
        while remaining:
            best = None
            for k in remaining:
                cx, cy = center(pads[k][1])
                d = min((cx - x) ** 2 + (cy - y) ** 2 for (x, y) in tree_pts)
                if best is None or d < best[0]:
                    best = (d, k)
            k = best[1]
            remaining.remove(k)
            pad, shp = pads[k]
            distB = self._dist(self.g.B, code)
            pside = self.pad_side(pad.GetParent().GetReference())
            if "B" in pside:
                w = min(w_cls, self._pad_maxw(shp, distB, clr))
            else:
                w = min(w_cls, self._pad_maxw(shp, self._dist(self.g.F, code), clr))
            if size(shp) < 2.0 and cls in ("BATT", "MOTOR", "PWR", "GND"):
                w = min(w, 1.4)
            if size(shp) < 2.0 and cls == "BATT":
                w = min(w, 0.8)   # ramas de senal (LED, divisor) de VBAT
            w = max(self.min_w, round(w * 10 - 0.5) / 10)
            ok = self._connect(name, code, shp, w, clr, distB, allow_j, tree_pts, cls)
            if not ok and not relaxed:
                self.failed.append((name, cls, pad.GetParent().GetReference(), pad.GetNumber()))
                self.log("   !! no se pudo conectar %s -> %s.%s" % (name, pad.GetParent().GetReference(), pad.GetNumber()))
            tree_pts.append(center(shp))
            if ok:
                if "B" in pside:
                    self._mark_shape(self.tree, shp, 1, rm=-0.06)
                if "F" in pside:
                    self._mark_shape(self.treeF, shp, 1, rm=-0.06)
                done.add(k)

    # ------------------------------------------------------------------
    def _connect(self, name, code, shp, w, clr, distB, allow_j, tree_pts, cls="Default"):
        g = self.g
        need = w / 2 + clr + RM
        freeB = distB >= need
        for (m, allowed) in self.reserved:
            if cls not in allowed and name not in allowed:
                freeB &= ~m
        tx, ty = (shp[1], shp[2]) if shp[0] == "c" else ((shp[1] + shp[3]) / 2, (shp[2] + shp[4]) / 2)
        # celdas objetivo: dentro del pad destino
        tgt = np.zeros_like(freeB)
        if shp[0] == "c":
            tr = max(shp[3] * 0.6, G)
            tgt = ((g.XX - tx) ** 2 + (g.YY - ty) ** 2 <= tr * tr)
        else:
            hw, hh = (shp[3] - shp[1]) * 0.3, (shp[4] - shp[2]) * 0.3
            tgt = (np.abs(g.XX - tx) <= max(hw, G)) & (np.abs(g.YY - ty) <= max(hh, G))
        tgt &= freeB
        # fuentes: cobre propio que no es este pad
        src = (self.tree == 1) & freeB & ~((g.XX - tx) ** 2 + (g.YY - ty) ** 2 <= 4.0)
        if not (self.two_layer and allow_j) and (not tgt.any() or not src.any()):
            self.log("     (sin %s libre para %s, w=%.1f)" % ("destino" if not tgt.any() else "origen", name, w))
            return False
        relaxed = getattr(self, "relaxed", False)
        # halo: pasar pegado a pads de otras redes cuesta mas (deja salida a esos pads)
        fpad = (self.P != 0) & (self.P != code) & (self.P != -1)
        dpad = ndimage.distance_transform_edt(~fpad) * G
        self.pen = ((dpad < need + 1.2) & ~tgt).astype(np.uint8).ravel().tobytes()
        freeF = None
        self.cur_via = self.via_sizes.get(cls, (JUMPER_PAD, JUMPER_DRILL))
        if self.two_layer and allow_j:
            vd, vdr = self.cur_via
            distF = self._dist(g.F, code)
            freeF = distF >= need
            viaok = (distB >= vd / 2 + clr + RM) & (distF >= vd / 2 + clr + RM) & ~self.noVia
            tgtF = np.zeros_like(freeB)
            if shp[0] == "c":
                tgtF = ((g.XX - tx) ** 2 + (g.YY - ty) ** 2 <= tr * tr)
            else:
                tgtF = (np.abs(g.XX - tx) <= max(hw, G)) & (np.abs(g.YY - ty) <= max(hh, G))
            tgtF &= freeF
            srcF = (self.treeF == 1) & freeF & ~((g.XX - tx) ** 2 + (g.YY - ty) ** 2 <= 4.0)
            self.extra = (tgtF, srcF)
            if not (tgt.any() or tgtF.any()) or not (src.any() or srcF.any()):
                self.extra = None
                self.log("     (sin destino/origen libre para %s)" % name)
                return False
            path = self._astar(freeB, src, tgt, (tx, ty), (freeF, viaok), 150.0 if relaxed else 60.0)
            self.extra = None
            if path is None:
                return False
            self._commit(name, code, path, w, (tx, ty), freeB, freeF)
            for (i, j, lay) in path[::8]:
                tree_pts.append(g.xy(i, j))
            return True
        path = self._astar(freeB, src, tgt, (tx, ty), None, 8.0)
        if path is None and allow_j:
            distF = self._dist(g.F, code)
            jclr = max(JUMPER_CLR, clr) if self.min_w >= 1.0 else JUMPER_CLR
            freeF = distF >= self.jw / 2 + jclr + RM
            viaok = (distB >= JUMPER_PAD / 2 + clr + RM) & (distF >= JUMPER_PAD / 2 + jclr + RM)
            viaok &= ~self.noVia
            for (m, allowed) in self.reserved:
                if cls not in allowed and name not in allowed:
                    viaok &= ~m
            path = self._astar(freeB, src, tgt, (tx, ty), (freeF, viaok), 150.0 if relaxed else 60.0)
        if path is None:
            return False
        self._commit(name, code, path, w, (tx, ty), freeB, freeF)
        for (i, j, lay) in path[::8]:
            tree_pts.append(g.xy(i, j))
        return True

    def _astar(self, freeB, src, tgt, target_xy, jumper, tlimit):
        """A* en B.Cu; con `jumper`, tambien en la capa de alambres (F) con costo alto."""
        g = self.g
        nx, ny = g.nx, g.ny
        N = nx * ny
        fb = freeB.ravel().tobytes()
        tg = tgt.ravel().tobytes()
        layers = 1
        if jumper is not None:
            ff = jumper[0].ravel().tobytes()
            vo = jumper[1].ravel().tobytes()
            layers = 2
        free = (fb, ff) if layers == 2 else (fb,)
        ti, tj = g.ij(*target_xy)
        SQ2 = 1.41421356
        nbrs = [(-1, 0, 1.0), (1, 0, 1.0), (0, -1, 1.0), (0, 1, 1.0),
                (-1, -1, SQ2), (-1, 1, SQ2), (1, -1, SQ2), (1, 1, SQ2)]
        lcost = (1.0, 1.15 if self.two_layer else WIRE_COST_FACTOR)
        extra = getattr(self, "extra", None)
        tgF = extra[0].ravel().tobytes() if extra is not None else None
        pen = self.pen
        vcost = (self.via_cost_mm if self.two_layer else VIA_COST_MM) / G

        def h(i, j):
            di, dj = abs(i - ti), abs(j - tj)
            return (di + dj) + (SQ2 - 2) * min(di, dj)

        gs = {}
        prev = {}
        heap = []
        si, sj = np.nonzero(src)
        for i, j in zip(si.tolist(), sj.tolist()):
            k = i * nx + j
            gs[k] = 0.0
            prev[k] = -1
            heap.append((h(i, j), 0.0, k))
        if extra is not None:
            si, sj = np.nonzero(extra[1])
            for i, j in zip(si.tolist(), sj.tolist()):
                k = N + i * nx + j
                gs[k] = 0.0
                prev[k] = -1
                heap.append((h(i, j), 0.0, k))
        heapq.heapify(heap)
        closed = set()
        t0 = time.time()
        it = 0
        while heap:
            f, gc, node = heapq.heappop(heap)
            if node in closed:
                continue
            closed.add(node)
            lay, k = divmod(node, N)
            if (lay == 0 and tg[k]) or (lay == 1 and tgF is not None and tgF[k]):
                out = []
                while node != -1:
                    l2, k2 = divmod(node, N)
                    out.append((k2 // nx, k2 % nx, l2))
                    node = prev[node]
                out.reverse()
                return out
            it += 1
            if (it & 1023) == 0 and time.time() - t0 > tlimit:
                return None
            i, j = divmod(k, nx)
            fr = free[lay]
            base = lay * N
            lc = lcost[lay]
            for di, dj, c in nbrs:
                ii, jj = i + di, j + dj
                if ii < 0 or jj < 0 or ii >= ny or jj >= nx:
                    continue
                kk = ii * nx + jj
                if not fr[kk]:
                    continue
                if di and dj and not (fr[i * nx + jj] and fr[ii * nx + j]):
                    continue
                nn = base + kk
                if nn in closed:
                    continue
                ng = gc + c * lc + (HALO_COST if (lay == 0 and pen[kk]) else 0.0)
                if ng < gs.get(nn, 1e18):
                    gs[nn] = ng
                    prev[nn] = node
                    heapq.heappush(heap, (ng + h(ii, jj), ng, nn))
            if layers == 2 and vo[k]:
                nn = (1 - lay) * N + k
                if nn not in closed and free[1 - lay][k]:
                    ng = gc + vcost
                    if ng < gs.get(nn, 1e18):
                        gs[nn] = ng
                        prev[nn] = node
                        heapq.heappush(heap, (ng + h(i, j), ng, nn))
        return None

    # ------------------------------------------------------------------
    def _los(self, free, a, b):
        (i0, j0), (i1, j1) = a, b
        n = int(max(abs(i1 - i0), abs(j1 - j0)) * 2) + 1
        for t in range(n + 1):
            f = t / n
            i = int(round(i0 + (i1 - i0) * f))
            j = int(round(j0 + (j1 - j0) * f))
            if not free[i, j]:
                return False
        return True

    def _smooth(self, pts, free):
        if len(pts) <= 2:
            return pts
        out = [pts[0]]
        k = 0
        while k < len(pts) - 1:
            best = k + 1
            # buscar el punto mas lejano con linea de vista (limitado para velocidad)
            for m in range(min(len(pts) - 1, k + 400), k + 1, -1):
                if self._los(free, pts[k], pts[m]):
                    best = m
                    break
            out.append(pts[best])
            k = best
        return out

    def _add_track(self, net, code, a, c, w, layer, arr):
        b = self.board
        t = pcbnew.PCB_TRACK(b)
        t.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(a[0]), pcbnew.FromMM(a[1])))
        t.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(c[0]), pcbnew.FromMM(c[1])))
        t.SetWidth(pcbnew.FromMM(w))
        t.SetLayer(layer)
        t.SetNet(net)
        b.Add(t)
        self.g.mark_seg(arr, a[0], a[1], c[0], c[1], w, code)
        if layer == pcbnew.B_Cu:
            self.g.mark_seg(self.g.E, a[0], a[1], c[0], c[1], w, code, rm=-0.06)
            self.g.mark_seg(self.tree, a[0], a[1], c[0], c[1], w, 1, rm=-0.06)
        elif getattr(self, "treeF", None) is not None:
            self.g.mark_seg(self.treeF, a[0], a[1], c[0], c[1], w, 1, rm=-0.06)

    def _commit(self, name, code, path, w, target_xy, freeB, freeF):
        g = self.g
        b = self.board
        net = b.GetNetsByName()[name]
        runs = [[path[0][2], [(path[0][0], path[0][1])]]]
        for (i, j, lay) in path[1:]:
            if lay != runs[-1][0]:
                runs.append([lay, [(i, j)]])
            else:
                runs[-1][1].append((i, j))
        for ri, (lay, run) in enumerate(runs):
            if lay == 0:
                pts = self._smooth(run, freeB)
                xy = [g.xy(i, j) for (i, j) in pts]
                if ri == len(runs) - 1:
                    xy.append(target_xy)
                for a, c in zip(xy, xy[1:]):
                    if abs(a[0] - c[0]) > 1e-6 or abs(a[1] - c[1]) > 1e-6:
                        self._add_track(net, code, a, c, w, pcbnew.B_Cu, g.B)
            else:
                pts = self._smooth(run, freeF)
                xy = [g.xy(i, j) for (i, j) in pts]
                if ri == len(runs) - 1:
                    xy.append(target_xy)
                vd, vdr = getattr(self, "cur_via", (JUMPER_PAD, JUMPER_DRILL))
                ends = []
                if ri > 0:
                    ends.append(xy[0])
                if ri < len(runs) - 1:
                    ends.append(xy[-1])
                if not self.two_layer:
                    ends = [xy[0], xy[-1]]
                    vd, vdr = JUMPER_PAD, JUMPER_DRILL
                for (x, y) in ends:
                    v = pcbnew.PCB_VIA(b)
                    v.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y)))
                    v.SetWidth(pcbnew.FromMM(vd))
                    v.SetDrill(pcbnew.FromMM(vdr))
                    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
                    v.SetNet(net)
                    b.Add(v)
                    g.mark_circle(g.B, x, y, vd / 2, code)
                    g.mark_circle(g.F, x, y, vd / 2, code)
                    g.mark_circle(self.tree, x, y, vd / 2, 1, rm=-0.06)
                    g.mark_circle(self.treeF, x, y, vd / 2, 1, rm=-0.06)
                    g.mark_circle(g.E, x, y, vd / 2, code, rm=-0.06)
                    self._mark_hole(x, y, vdr / 2)
                    if self.via_pad_gap > 0:      # el siguiente barreno de cable no se le encima
                        m = np.zeros(g.B.shape, np.int8)
                        g.mark_circle(m, x, y, vd + self.via_pad_gap, 1)
                        self.noVia |= m.astype(bool)
                L = 0.0
                for a, c in zip(xy, xy[1:]):
                    self._add_track(net, code, a, c, w if self.two_layer else self.jw, pcbnew.F_Cu, g.F)
                    L += math.hypot(c[0] - a[0], c[1] - a[1])
                self.jumpers.append((name, xy[0][0], xy[0][1], xy[-1][0], xy[-1][1], L))


def route(board, classes, assignments, order_classes=None, log=print, relaxed_pass=True,
          reserved=(), early_refs=None, late=(), first=(), two_layer=False, via_sizes=None,
          pad_side=None, via_cost_mm=3.0, no_via_under_parts=False, via_pad_gap=0.0, min_w=0.5, skip=()):
    """classes: {clase: (ancho, holgura)}, assignments: {red: clase}.

    Orden: BATT, MOTOR, PWR (solo pads de potencia), GND de potencia,
    senales largas, senales cortas, resto de +5V y GND, pasada relajada.
    early_refs: {red: set(referencias)} pads que van en la etapa de potencia.
    """
    r = Router(board, classes, log=log, reserved=reserved, two_layer=two_layer, via_sizes=via_sizes,
               pad_side=pad_side, via_cost_mm=via_cost_mm, no_via_under_parts=no_via_under_parts,
               via_pad_gap=via_pad_gap, min_w=min_w)
    # skip: redes que la variante ya trae completas en pistas fijas (el router no las toca)
    nets = [n for n in r.pads_by_net if len(r.pads_by_net[n]) > 1 and n not in skip]
    early_refs = early_refs or {}

    def span(n):
        pads = r.pads_by_net[n]
        xs = [p[0].GetPosition().x for p in pads]
        ys = [p[0].GetPosition().y for p in pads]
        return mm((max(xs) - min(xs)) + (max(ys) - min(ys)))

    def big(pad):
        return max(mm(pad.GetSize().x), mm(pad.GetSize().y)) >= 2.0

    def cls(n):
        return assignments.get(n, "Default")

    def early(n):
        refs = early_refs.get(n)
        if refs is None:
            return big
        return lambda pad: pad.GetParent().GetReference() in refs

    stages = []
    for c in ("BATT", "MOTOR"):
        stages += [(n, c, None) for n in sorted(nets, key=span) if cls(n) == c]
    stages += [(n, "PWR", early(n)) for n in nets if cls(n) == "PWR"]
    stages += [(n, "GND", early(n)) for n in nets if cls(n) == "GND"]
    sig = [n for n in nets if cls(n) == "Default" and n not in late and n not in first]
    stages += [(n, "Default", None) for n in first if n in nets]
    longs = sorted([n for n in sig if span(n) > 60], key=span, reverse=True)
    shorts = sorted([n for n in sig if span(n) <= 60], key=span)
    stages += [(n, "Default", None) for n in longs + shorts]
    stages += [(n, "Default", None) for n in late if n in nets]
    stages += [(n, cls(n), None) for n in nets if cls(n) in ("PWR", "GND")]
    for (n, c, flt) in stages:
        t0 = time.time()
        nj = len(r.jumpers)
        r.route_net(n, c, flt)
        log("  %-12s %-8s %5.1fs  puentes=%d" % (n, c, time.time() - t0, len(r.jumpers) - nj))
    # pasada relajada
    pending = list(dict.fromkeys((f[0], f[1]) for f in r.failed)) if relaxed_pass else []
    r.failed = []
    for (n, c) in pending:
        t0 = time.time()
        r.route_net(n, c, None, relaxed=True)
        log("  (relajada) %-12s %5.1fs" % (n, time.time() - t0))
    # rip-up & reroute de lo que siga fallando (solo se levantan senales)
    def pending_list():
        out = []
        for n in nets:
            t = r.trees.get(n)
            done = t[1] if t else set()
            for k, (pad, shp) in enumerate(r.pads_by_net[n]):
                if k not in done:
                    out.append((n, pad))
        return out

    ripped_count = {}
    for it in range(3):
        pend = pending_list()
        if not pend:
            break
        for (n, pad) in pend:
            t = r.trees.get(n)
            if t and any(p is pad for (p, s_) in []):
                continue
            bl = [b for b in r.blockers(pad, own=r.code(n))
                  if cls(b) == "Default" and ripped_count.get(b, 0) < 2]
            if not bl:
                continue
            for b in bl:
                ripped_count[b] = ripped_count.get(b, 0) + 1
            log("  rip-up para %s (%s.%s): %s" % (n, pad.GetParent().GetReference(), pad.GetNumber(), ", ".join(bl)))
            r.rip(bl)
            r.route_net(n, cls(n), None, relaxed=True)
            for b in bl:
                r.route_net(b, "Default", None, relaxed=True)
    r.failed = []
    for n in nets:
        t = r.trees.get(n)
        done = t[1] if t else set()
        for k, (pad, shp) in enumerate(r.pads_by_net[n]):
            if k not in done:
                r.failed.append((n, pad.GetParent().GetReference(), pad.GetNumber()))
    return r
