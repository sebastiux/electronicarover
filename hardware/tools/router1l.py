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
JUMPER_COST_MM = 30.0  # penalizacion por puente (mm equivalentes)
JUMPER_MAX_MM = 45.0
JUMPER_MIN_MM = 3.0


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
    def __init__(self, board, classes, no_jumper_classes=("BATT", "MOTOR"), log=print):
        self.board = board
        self.classes = classes  # name -> (width, clearance)
        self.no_jumper = set(no_jumper_classes)
        self.log = log
        self.g = Grid(board)
        self.netcodes = {}
        self.jumpers = []
        self.failed = []
        self._build_obstacles()

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
                self.pads_by_net.setdefault(pad.GetNetname(), []).append((pad, shp))
        # zonas de exclusion (antenas)
        for z in b.Zones():
            if z.GetIsRuleArea() and z.GetDoNotAllowTracks():
                bb = z.GetBoundingBox()
                g.mark_rect(g.B, mm(bb.GetX()), mm(bb.GetY()), mm(bb.GetX() + bb.GetWidth()),
                            mm(bb.GetY() + bb.GetHeight()), -1)
                g.mark_rect(g.F, mm(bb.GetX()), mm(bb.GetY()), mm(bb.GetX() + bb.GetWidth()),
                            mm(bb.GetY() + bb.GetHeight()), -1)

    # ------------------------------------------------------------------
    def _dist(self, arr, code):
        foreign = (arr != 0) & (arr != code)
        return ndimage.distance_transform_edt(~foreign) * G

    def _pad_maxw(self, shp, dist, clr):
        x, y = (shp[1], shp[2]) if shp[0] == "c" else ((shp[1] + shp[3]) / 2, (shp[2] + shp[4]) / 2)
        i, j = self.g.ij(x, y)
        return 2 * (dist[i, j] - clr - RM - 0.05)

    def route_net(self, name, cls):
        w_cls, clr = self.classes[cls]
        code = self.code(name)
        pads = self.pads_by_net.get(name, [])
        if len(pads) < 2:
            return
        allow_j = cls not in self.no_jumper
        # arbol tipo Prim desde el pad mas grande
        def size(s):
            return 2 * s[3] if s[0] == "c" else max(s[3] - s[1], s[4] - s[2])

        def center(s):
            return (s[1], s[2]) if s[0] == "c" else ((s[1] + s[3]) / 2, (s[2] + s[4]) / 2)

        order = sorted(range(len(pads)), key=lambda k: -size(pads[k][1]))
        tree_pts = [center(pads[order[0]][1])]
        self.tree = np.zeros(self.g.B.shape, np.int8)
        self._mark_shape(self.tree, pads[order[0]][1], 1)
        remaining = order[1:]
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
            ok = self._connect(name, code, shp, w, clr, distB, allow_j, tree_pts)
            if not ok:
                self.failed.append((name, pad.GetParent().GetReference(), pad.GetNumber()))
                self.log("   !! no se pudo conectar %s -> %s.%s" % (name, pad.GetParent().GetReference(), pad.GetNumber()))
            tree_pts.append(center(shp))
            if ok:
                self._mark_shape(self.tree, shp, 1)

    # ------------------------------------------------------------------
    def _connect(self, name, code, shp, w, clr, distB, allow_j, tree_pts):
        g = self.g
        need = w / 2 + clr + RM
        freeB = distB >= need
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
            return False
        path = self._astar(freeB, src, tgt, (tx, ty), None)
        if path is None and allow_j:
            distF = self._dist(g.F, code)
            freeF = distF >= JUMPER_WIRE / 2 + JUMPER_CLR + RM
            viaok = (distB >= JUMPER_PAD / 2 + clr + RM) & (distF >= JUMPER_PAD / 2 + JUMPER_CLR + RM)
            path = self._astar(freeB, src, tgt, (tx, ty), (freeF, viaok))
        if path is None:
            return False
        self._commit(name, code, path, w, (tx, ty), freeB)
        for (i, j, jmp) in path[::8]:
            tree_pts.append(g.xy(i, j))
        return True

    def _astar(self, freeB, src, tgt, target_xy, jumper):
        g = self.g
        nx, ny = g.nx, g.ny
        fb = freeB.ravel().tobytes()
        tg = tgt.ravel().tobytes()
        if jumper is not None:
            ff = jumper[0].ravel().tobytes()
            vo = jumper[1].ravel().tobytes()
        ti, tj = g.ij(*target_xy)
        SQ2 = 1.41421356
        nbrs = [(-1, 0, 1.0), (1, 0, 1.0), (0, -1, 1.0), (0, 1, 1.0),
                (-1, -1, SQ2), (-1, 1, SQ2), (1, -1, SQ2), (1, 1, SQ2)]
        jcost = JUMPER_COST_MM / G
        jmax = int(JUMPER_MAX_MM / G)
        jmin = int(JUMPER_MIN_MM / G)

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
            prev[k] = (-1, 0)
            heap.append((h(i, j), 0.0, k))
        heapq.heapify(heap)
        closed = set()
        t0 = time.time()
        while heap:
            f, gc, k = heapq.heappop(heap)
            if k in closed:
                continue
            closed.add(k)
            if tg[k]:
                # reconstruir
                out = []
                while k != -1:
                    pk, jmp = prev[k]
                    out.append((k // nx, k % nx, jmp))
                    k = pk
                out.reverse()
                return out
            if time.time() - t0 > 60:
                return None
            i, j = divmod(k, nx)
            for di, dj, c in nbrs:
                ii, jj = i + di, j + dj
                if ii < 0 or jj < 0 or ii >= ny or jj >= nx:
                    continue
                kk = ii * nx + jj
                if not fb[kk] or kk in closed:
                    continue
                if di and dj and not (fb[i * nx + jj] and fb[ii * nx + j]):
                    continue
                ng = gc + c
                if ng < gs.get(kk, 1e18):
                    gs[kk] = ng
                    prev[kk] = (k, 0)
                    heapq.heappush(heap, (ng + h(ii, jj), ng, kk))
            if jumper is not None and vo[k]:
                for di, dj in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    crossed = False
                    pushed = 0
                    for L in range(1, jmax + 1):
                        ii, jj = i + di * L, j + dj * L
                        if ii < 0 or jj < 0 or ii >= ny or jj >= nx:
                            break
                        kk = ii * nx + jj
                        if not ff[kk]:
                            break
                        if not fb[kk]:
                            crossed = True
                            pushed = 0
                            continue
                        if crossed and L >= jmin and vo[kk] and pushed < 2 and kk not in closed:
                            ng = gc + jcost + L * 1.2
                            if ng < gs.get(kk, 1e18):
                                gs[kk] = ng
                                prev[kk] = (k, 1)
                                heapq.heappush(heap, (ng + h(ii, jj), ng, kk))
                            pushed += 1
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

    def _commit(self, name, code, path, w, target_xy, freeB):
        g = self.g
        b = self.board
        net = b.GetNetsByName()[name]
        # separar en tramos B y saltos de puente
        runs = [[(path[0][0], path[0][1])]]
        jumps = []
        for (i, j, jmp) in path[1:]:
            if jmp:
                jumps.append((runs[-1][-1], (i, j)))
                runs.append([(i, j)])
            else:
                runs[-1].append((i, j))
        for ri, run in enumerate(runs):
            pts = self._smooth(run, freeB)
            xy = [g.xy(i, j) for (i, j) in pts]
            if ri == len(runs) - 1:
                xy.append(target_xy)
            for a, c in zip(xy, xy[1:]):
                if abs(a[0] - c[0]) < 1e-6 and abs(a[1] - c[1]) < 1e-6:
                    continue
                t = pcbnew.PCB_TRACK(b)
                t.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(a[0]), pcbnew.FromMM(a[1])))
                t.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(c[0]), pcbnew.FromMM(c[1])))
                t.SetWidth(pcbnew.FromMM(w))
                t.SetLayer(pcbnew.B_Cu)
                t.SetNet(net)
                b.Add(t)
                g.mark_seg(g.B, a[0], a[1], c[0], c[1], w, code)
                g.mark_seg(self.tree, a[0], a[1], c[0], c[1], w, 1)
        for (a, c) in jumps:
            (xa, ya), (xc, yc) = g.xy(*a), g.xy(*c)
            for (x, y) in ((xa, ya), (xc, yc)):
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
            t = pcbnew.PCB_TRACK(b)
            t.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(xa), pcbnew.FromMM(ya)))
            t.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(xc), pcbnew.FromMM(yc)))
            t.SetWidth(pcbnew.FromMM(JUMPER_WIRE))
            t.SetLayer(pcbnew.F_Cu)
            t.SetNet(net)
            b.Add(t)
            g.mark_seg(g.F, xa, ya, xc, yc, JUMPER_WIRE, code)
            self.jumpers.append((name, xa, ya, xc, yc))


def route(board, classes, assignments, order_classes, log=print):
    """classes: {clase: (ancho, holgura)}, assignments: {red: clase}."""
    r = Router(board, classes, log=log)
    nets = [n for n in r.pads_by_net if len(r.pads_by_net[n]) > 1]

    def key(n):
        cls = assignments.get(n, "Default")
        pads = r.pads_by_net[n]
        xs = [p[0].GetPosition().x for p in pads]
        ys = [p[0].GetPosition().y for p in pads]
        span = (max(xs) - min(xs)) + (max(ys) - min(ys))
        return (order_classes.index(cls) if cls in order_classes else len(order_classes), span)

    for n in sorted(nets, key=key):
        cls = assignments.get(n, "Default")
        t0 = time.time()
        nj = len(r.jumpers)
        r.route_net(n, cls)
        log("  %-12s %-8s %5.1fs  puentes=%d" % (n, cls, time.time() - t0, len(r.jumpers) - nj))
    return r
