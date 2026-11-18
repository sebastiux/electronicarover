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

    def mark_circle(self, arr, x, y, r, val, only_free=False):
        i0, i1, j0, j1 = self.window(x, y, x, y, r + RM)
        X, Y = self.XX[i0:i1, j0:j1], self.YY[i0:i1, j0:j1]
        m = (X - x) ** 2 + (Y - y) ** 2 <= (r + RM) ** 2
        sub = arr[i0:i1, j0:j1]
        if only_free:
            m &= sub == 0
        sub[m] = val

    def mark_rect(self, arr, xa, ya, xb, yb, val, only_free=False):
        i0, i1, j0, j1 = self.window(xa, ya, xb, yb, RM)
        X, Y = self.XX[i0:i1, j0:j1], self.YY[i0:i1, j0:j1]
        m = (X >= xa - RM) & (X <= xb + RM) & (Y >= ya - RM) & (Y <= yb + RM)
        sub = arr[i0:i1, j0:j1]
        if only_free:
            m &= sub == 0
        sub[m] = val

    def mark_seg(self, arr, xa, ya, xb, yb, w, val):
        r = w / 2 + RM
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
    def __init__(self, board, classes, no_jumper_classes=("BATT", "MOTOR"), log=print, reserved=()):
        self.board = board
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

    def _mark_shape(self, arr, shp, val):
        if shp[0] == "c":
            self.g.mark_circle(arr, shp[1], shp[2], shp[3], val)
        else:
            self.g.mark_rect(arr, shp[1], shp[2], shp[3], shp[4], val)

    def _build_obstacles(self):
        g = self.g
        b = self.board
        # fuera de la tarjeta (con esquinas redondeadas de 3 mm)
        R = 3.0
        out = (g.XX < g.bx0) | (g.XX > g.bx1) | (g.YY < g.by0) | (g.YY > g.by1)
        for (cx, cy) in [(g.bx0 + R, g.by0 + R), (g.bx1 - R, g.by0 + R), (g.bx0 + R, g.by1 - R), (g.bx1 - R, g.by1 - R)]:
            corner = (np.abs(g.XX - cx) <= R + 0.01) & (np.abs(g.YY - cy) <= R + 0.01)
            corner &= (np.sign(g.XX - cx) == np.sign(cx - (g.bx0 + g.bx1) / 2)) & \
                       (np.sign(g.YY - cy) == np.sign(cy - (g.by0 + g.by1) / 2))
            out |= corner & ((g.XX - cx) ** 2 + (g.YY - cy) ** 2 > R * R)
        g.B[out] = -1
        g.F[out] = -1
        self.pads_by_net = {}
        self.twins = []
        seen = {}
        for fp in b.GetFootprints():
            ref = fp.GetReference()
            # bajo componentes de perfil bajo no pueden pasar puentes de alambre
            if not (ref.startswith("U") or ref.startswith("H")):
                cy = fp.GetCourtyard(pcbnew.F_CrtYd)
                if cy.OutlineCount():
                    bb = cy.BBox()
                    g.mark_rect(g.F, mm(bb.GetX()), mm(bb.GetY()), mm(bb.GetX() + bb.GetWidth()),
                                mm(bb.GetY() + bb.GetHeight()), -1)
            for pad in fp.Pads():
                shp = self._pad_shape(pad)
                if pad.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH or not pad.GetNetname():
                    if pad.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
                        shp = ("c", mm(pad.GetPosition().x), mm(pad.GetPosition().y), mm(pad.GetDrillSize().x) / 2)
                    self._mark_shape(g.B, shp, -1)
                    self._mark_shape(g.F, shp, -1)
                    continue
                code = pad.GetNetCode()
                self._mark_shape(g.B, shp, code)
                self._mark_shape(g.F, shp, code)
                key = (ref, pad.GetNumber())
                if key in seen:
                    self.twins.append((seen[key], pad))
                    continue
                seen[key] = pad
                self.pads_by_net.setdefault(pad.GetNetname(), []).append((pad, shp))
        self.P = g.B.copy()   # solo pads (para el costo de "halo")
        # pistas y vias ya existentes (permite rutear de forma incremental)
        for t in b.GetTracks():
            code = t.GetNetCode()
            if t.GetClass() == "PCB_VIA":
                p = t.GetPosition()
                for arr in (g.B, g.F):
                    g.mark_circle(arr, mm(p.x), mm(p.y), mm(t.GetWidth()) / 2, code)
            else:
                arr = g.B if t.GetLayer() == pcbnew.B_Cu else g.F
                a, c = t.GetStart(), t.GetEnd()
                g.mark_seg(arr, mm(a.x), mm(a.y), mm(c.x), mm(c.y), mm(t.GetWidth()), code)
        # zonas de exclusion (antenas)
        for z in b.Zones():
            if z.GetIsRuleArea() and z.GetDoNotAllowTracks():
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
            t.SetWidth(pcbnew.FromMM(0.8))
            t.SetLayer(pcbnew.B_Cu)
            t.SetNet(p1.GetNet())
            b.Add(t)
            g.mark_seg(g.B, mm(a.x), mm(a.y), mm(c.x), mm(c.y), 0.8, p1.GetNetCode())

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
            t = np.zeros(self.g.B.shape, np.int8)
            self._mark_shape(t, pads[order[0]][1], 1)
            self.trees[name] = [t, {order[0]}, [center(pads[order[0]][1])]]
        self.tree, done, tree_pts = self.trees[name]
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
            w = min(w_cls, self._pad_maxw(shp, distB, clr))
            if size(shp) < 2.0 and cls in ("BATT", "MOTOR", "PWR", "GND"):
                w = min(w, 1.4)
            w = max(0.5, round(w * 10 - 0.5) / 10)
            ok = self._connect(name, code, shp, w, clr, distB, allow_j, tree_pts, cls)
            if not ok and not relaxed:
                self.failed.append((name, cls, pad.GetParent().GetReference(), pad.GetNumber()))
                self.log("   !! no se pudo conectar %s -> %s.%s" % (name, pad.GetParent().GetReference(), pad.GetNumber()))
            tree_pts.append(center(shp))
            if ok:
                self._mark_shape(self.tree, shp, 1)
                done.add(k)

    # ------------------------------------------------------------------
    def _connect(self, name, code, shp, w, clr, distB, allow_j, tree_pts, cls="Default"):
        g = self.g
        need = w / 2 + clr + RM
        freeB = distB >= need
        for (m, allowed) in self.reserved:
            if cls not in allowed:
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
        if not tgt.any() or not src.any():
            self.log("     (sin %s libre para %s, w=%.1f)" % ("destino" if not tgt.any() else "origen", name, w))
            return False
        relaxed = getattr(self, "relaxed", False)
        # halo: pasar pegado a pads de otras redes cuesta mas (deja salida a esos pads)
        fpad = (self.P != 0) & (self.P != code) & (self.P != -1)
        dpad = ndimage.distance_transform_edt(~fpad) * G
        self.pen = ((dpad < need + 1.2) & ~tgt).astype(np.uint8).ravel().tobytes()
        path = self._astar(freeB, src, tgt, (tx, ty), None, 8.0)
        freeF = None
        if path is None and allow_j:
            distF = self._dist(g.F, code)
            freeF = distF >= JUMPER_WIRE / 2 + JUMPER_CLR + RM
            viaok = (distB >= JUMPER_PAD / 2 + clr + RM) & (distF >= JUMPER_PAD / 2 + JUMPER_CLR + RM)
            for (m, allowed) in self.reserved:
                if cls not in allowed:
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
        lcost = (1.0, WIRE_COST_FACTOR)
        pen = self.pen
        vcost = VIA_COST_MM / G

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
            if lay == 0 and tg[k]:
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
        self.g.mark_seg(self.tree, a[0], a[1], c[0], c[1], w, 1)

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
                for (x, y) in (xy[0], xy[-1]):
                    v = pcbnew.PCB_VIA(b)
                    v.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y)))
                    v.SetWidth(pcbnew.FromMM(JUMPER_PAD))
                    v.SetDrill(pcbnew.FromMM(JUMPER_DRILL))
                    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
                    v.SetNet(net)
                    b.Add(v)
                    g.mark_circle(g.B, x, y, JUMPER_PAD / 2, code)
                    g.mark_circle(g.F, x, y, JUMPER_PAD / 2, code)
                    g.mark_circle(self.tree, x, y, JUMPER_PAD / 2, 1)
                L = 0.0
                for a, c in zip(xy, xy[1:]):
                    self._add_track(net, code, a, c, JUMPER_WIRE, pcbnew.F_Cu, g.F)
                    L += math.hypot(c[0] - a[0], c[1] - a[1])
                self.jumpers.append((name, xy[0][0], xy[0][1], xy[-1][0], xy[-1][1], L))


def route(board, classes, assignments, order_classes=None, log=print, relaxed_pass=True,
          reserved=(), early_refs=None):
    """classes: {clase: (ancho, holgura)}, assignments: {red: clase}.

    Orden: BATT, MOTOR, PWR (solo pads de potencia), GND de potencia,
    senales largas, senales cortas, resto de +5V y GND, pasada relajada.
    early_refs: {red: set(referencias)} pads que van en la etapa de potencia.
    """
    r = Router(board, classes, log=log, reserved=reserved)
    nets = [n for n in r.pads_by_net if len(r.pads_by_net[n]) > 1]
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
    sig = [n for n in nets if cls(n) == "Default"]
    longs = sorted([n for n in sig if span(n) > 60], key=span, reverse=True)
    shorts = sorted([n for n in sig if span(n) <= 60], key=span)
    stages += [(n, "Default", None) for n in longs + shorts]
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
    r.failed = []
    for n in nets:
        t = r.trees.get(n)
        done = t[1] if t else set()
        for k, (pad, shp) in enumerate(r.pads_by_net[n]):
            if k not in done:
                r.failed.append((n, pad.GetParent().GetReference(), pad.GetNumber()))
    return r
