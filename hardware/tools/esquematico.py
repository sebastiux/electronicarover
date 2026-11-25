#!/usr/bin/env python3
"""Esquematico jerarquico y legible de la tarjeta Cubiko.

Sustituye al esquematico "de etiquetas" (todos los simbolos en rejilla) por una hoja
indice y 5 hojas por bloque funcional, con los componentes en serie unidos por cables,
notas de diseno y la lista de pines libres de cada modulo. Las redes conservan
exactamente los nombres de la PCB: se nombran con etiquetas globales o simbolos de
alimentacion (una etiqueta local en una subhoja cambiaria el nombre a /Hoja/RED).

Lo llama generate.py (variante cubiko). Tambien se puede correr solo:
    ROVER_VARIANT=cubiko python3 esquematico.py
y despues actualizar las rutas de la PCB ya ruteada con --pcb.
"""
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import generate as G  # noqa: E402

D = G.D
uid, f = G.uid, G.f
ROOT = uid("root-sheet")


def qt(s):
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'


def snap(v):
    return round(v / 1.27) * 1.27


# ---------------------------------------------------------------------------
#  Hoja
# ---------------------------------------------------------------------------
class Hoja:
    def __init__(self, nombre, archivo, pagina, titulo, comps, libs):
        self.nombre, self.archivo, self.pagina, self.titulo = nombre, archivo, pagina, titulo
        self.uuid = uid("hoja", nombre) if archivo else ROOT
        self.path = "/%s/%s" % (ROOT, self.uuid) if archivo else "/%s" % ROOT
        self.pcb_path = "/%s" % self.uuid if archivo else ""
        self.comps = comps
        self.libs = libs
        self.L = []
        self.used_libs = set()
        self.npwr = 0
        self.redes = {}          # red -> numero de pines de esta hoja
        self.cables = []         # tramos ((x0, y0), (x1, y1)); se parten al escribir
        self.puntos = set()      # pines, uniones, etiquetas y simbolos: ahi se parten los cables
        self.k = 0

    def _id(self, *p):
        self.k += 1
        return uid(self.nombre, self.k, *p)

    # ---- simbolos ----------------------------------------------------------
    def comp(self, ref, x, y, rot=0, mirror=False, props="auto"):
        c = self.comps[ref]
        lib_id = c["symbol"]
        self.used_libs.add(lib_id)
        x, y = snap(x), snap(y)
        sym_uuid = uid("sym", ref)
        c["sym_uuid"], c["sym_path"], c["hoja"] = sym_uuid, self.pcb_path + "/" + sym_uuid, self.nombre
        pins = self.pines(lib_id, x, y, rot, mirror)
        body = '  (symbol (lib_id %s) (at %s %s %d)%s (unit 1)' % (qt(lib_id), f(x), f(y), rot,
                                                                   " (mirror y)" if mirror else "")
        self.L.append(body)
        self.L.append('    (in_bom yes) (on_board yes) (dnp no)')
        self.L.append('    (uuid %s)' % sym_uuid)
        rp, vp = self._props_pos(lib_id, x, y, rot, mirror, pins)
        fa = 90 if rot in (90, 270) else 0      # KiCad suma el giro del simbolo al del texto
        if (rot + fa) % 360 == 180:             # y lo endereza invirtiendo la justificacion
            inv = {"left": "right", "right": "left", "top": "bottom", "bottom": "top"}
            rp, vp = (rp[0], rp[1], inv[rp[2]]), (vp[0], vp[1], inv[vp[2]])
        self.L.append('    (property "Reference" %s (at %s %s %d) (effects (font (size 1.27 1.27)) (justify %s)))'
                      % (qt(ref), f(rp[0]), f(rp[1]), fa, rp[2]))
        self.L.append('    (property "Value" %s (at %s %s %d) (effects (font (size 1.27 1.27)) (justify %s)))'
                      % (qt(c["value"]), f(vp[0]), f(vp[1]), fa, vp[2]))
        for k, v in (("Footprint", c["footprint"]), ("Datasheet", "~"), ("Descripcion", c.get("desc", "")),
                     ("MPN", c.get("mpn", c["value"]))):
            self.L.append('    (property %s %s (at %s %s 0) (effects (font (size 1.27 1.27)) hide))'
                          % (qt(k), qt(v), f(x), f(y)))
        for num in pins:
            self.L.append('    (pin %s (uuid %s))' % (qt(num), uid("pin", ref, num)))
        self.L.append('    (instances (project %s (path %s (reference %s) (unit 1))))'
                      % (qt(D.PROJECT), qt(self.path), qt(ref)))
        self.L.append('  )')
        # red de cada pin (para el chequeo y las marcas de "sin conectar")
        out = {}
        for num, (px, py, d) in pins.items():
            self.puntos.add((px, py))
            net = c["pins"].get(num, c["pins"].get(int(num)) if num.isdigit() else None)
            out[num] = (px, py, d, net)
            if net:
                self.redes[net] = self.redes.get(net, 0) + 1
        return out

    def pines(self, lib_id, x, y, rot, mirror):
        out = {}
        for (num, px, py, ang) in self.libs[lib_id][1]:
            a = math.radians(rot)
            rx, ry = px * math.cos(a) - py * math.sin(a), px * math.sin(a) + py * math.cos(a)
            ang2 = (ang + rot) % 360
            if mirror:
                rx = -rx
                ang2 = {0: 180, 180: 0}.get(ang2, ang2)
            t = math.radians(ang2)
            d = (round(-math.cos(t)), round(math.sin(t)))   # hacia afuera del simbolo (y hacia abajo)
            out[num] = (snap(x + rx), snap(y - ry), d)
        return out

    def _props_pos(self, lib_id, x, y, rot, mirror, pins):
        xs = [p[0] for p in pins.values()]
        ys = [p[1] for p in pins.values()]
        if lib_id.startswith("Connector:Screw"):
            cx = x + (2.54 if mirror else -2.54)
            return (cx, min(ys) - 2.54, "bottom"), (cx, max(ys) + 3.81, "top")
        if len(pins) <= 2 and len(set(round(v, 2) for v in xs)) == 1:      # 2 pines en vertical
            return (x + 2.54, y - 0.635, "left"), (x + 2.54, y + 1.905, "left")
        if len(pins) <= 2:                                                   # 2 pines en horizontal
            return (x, y - 3.175, "bottom"), (x, y + 3.81, "top")
        top, bot = min(ys), max(ys)
        if lib_id.startswith("Connector:Screw"):
            cx = x + (2.54 if mirror else -2.54)
            return (cx, top - 3.81, "bottom"), (cx, bot + 3.81, "top")
        return (x, top - 3.81, "bottom"), (x, bot + 3.81, "top")

    def potencia(self, nombre, x, y, d):
        """Simbolo GND/+5V en (x, y); d: hacia donde apunta el dibujo."""
        lib_id = "power:" + nombre
        self.used_libs.add(lib_id)
        self.npwr += 1
        if nombre == "GND":
            rot = {(0, 1): 0, (0, -1): 180, (-1, 0): 270, (1, 0): 90}[d]
        else:
            rot = {(0, -1): 0, (0, 1): 180, (-1, 0): 90, (1, 0): 270}[d]
        ref = "#PWR%s%02d" % (self.pagina, self.npwr)
        self.puntos.add((snap(x), snap(y)))
        su = self._id("pwr")
        self.L.append('  (symbol (lib_id %s) (at %s %s %d) (unit 1)' % (qt(lib_id), f(x), f(y), rot))
        self.L.append('    (in_bom yes) (on_board yes) (dnp no) (uuid %s)' % su)
        self.L.append('    (property "Reference" %s (at %s %s 0) (effects (font (size 1.27 1.27)) hide))'
                      % (qt(ref), f(x), f(y)))
        tx, ty = x + d[0] * 5.08, y + d[1] * 4.45
        self.L.append('    (property "Value" %s (at %s %s 0) (effects (font (size 1.27 1.27))))'
                      % (qt(nombre), f(tx), f(ty)))
        self.L.append('    (property "Footprint" "" (at %s %s 0) (effects (font (size 1.27 1.27)) hide))' % (f(x), f(y)))
        self.L.append('    (property "Datasheet" "" (at %s %s 0) (effects (font (size 1.27 1.27)) hide))' % (f(x), f(y)))
        self.L.append('    (pin "1" (uuid %s))' % self._id("pwrpin"))
        self.L.append('    (instances (project %s (path %s (reference %s) (unit 1))))'
                      % (qt(D.PROJECT), qt(self.path), qt(ref)))
        self.L.append('  )')

    # ---- primitivas --------------------------------------------------------
    def cable(self, *pts):
        pts = [(snap(a), snap(b)) for a, b in pts]
        for a, b in zip(pts, pts[1:]):
            if a != b:
                self.cables.append((a, b))

    def union(self, x, y):
        self.puntos.add((snap(x), snap(y)))
        self.L.append('  (junction (at %s %s) (diameter 0) (color 0 0 0 0) (uuid %s))' % (f(snap(x)), f(snap(y)), self._id("j")))

    def nc(self, x, y):
        self.L.append('  (no_connect (at %s %s) (uuid %s))' % (f(x), f(y), self._id("nc")))

    def etiqueta(self, net, x, y, d, forma="passive"):
        ang, just = {(-1, 0): (180, "right"), (1, 0): (0, "left"), (0, 1): (270, "right"), (0, -1): (90, "left")}[d]
        x, y = snap(x), snap(y)
        self.puntos.add((x, y))
        self.L.append('  (global_label %s (shape %s) (at %s %s %d) (fields_autoplaced) (effects (font (size 1.27 1.27)) (justify %s)) (uuid %s)'
                      % (qt(net), forma, f(x), f(y), ang, just, self._id("gl")))
        self.L.append('    (property "Intersheetrefs" "${INTERSHEET_REFS}" (at %s %s 0) (effects (font (size 1.27 1.27)) (justify %s) hide))'
                      % (f(x), f(y), just))
        self.L.append('  )')

    def texto(self, x, y, s, size=1.27, bold=False):
        self.L.append('  (text %s (at %s %s 0) (effects (font (size %s %s)%s) (justify left top)) (uuid %s))'
                      % (qt(s), f(x), f(y), f(size), f(size), " bold" if bold else "", self._id("t")))

    def marco(self, x0, y0, x1, y1, titulo):
        self.L.append('  (polyline (pts (xy %s %s) (xy %s %s) (xy %s %s) (xy %s %s) (xy %s %s)) (stroke (width 0.25) (type dash) (color 72 72 132 1)) (uuid %s))'
                      % (f(x0), f(y0), f(x1), f(y0), f(x1), f(y1), f(x0), f(y1), f(x0), f(y0), self._id("m")))
        self.texto(x0 + 1.27, y0 + 1.27, titulo, 2.0, True)

    def _cables_partidos(self):
        """KiCad solo une un cable por sus extremos: se parte cada tramo en todo punto de
        conexion que caiga en su interior (extremos de otros cables, pines, uniones...)."""
        pts = set(self.puntos)
        for a, b in self.cables:
            pts.add(a); pts.add(b)
        out = []
        for (x0, y0), (x1, y1) in self.cables:
            dentro = []
            for (px, py) in pts:
                if (px, py) in ((x0, y0), (x1, y1)):
                    continue
                if x0 == x1 == px and min(y0, y1) < py < max(y0, y1):
                    dentro.append((abs(py - y0), (px, py)))
                elif y0 == y1 == py and min(x0, x1) < px < max(x0, x1):
                    dentro.append((abs(px - x0), (px, py)))
            cad = [(x0, y0)] + [q for _, q in sorted(dentro)] + [(x1, y1)]
            for (a0, a1), (b0, b1) in zip(cad, cad[1:]):
                out.append('  (wire (pts (xy %s %s) (xy %s %s)) (stroke (width 0) (type default)) (uuid %s))'
                           % (f(a0), f(a1), f(b0), f(b1), uid(self.nombre, "w", a0, a1, b0, b1)))
        return out

    # ---- atajos ------------------------------------------------------------
    def punta(self, pin, largo=5.08, forma="passive", net=None):
        """Cable corto desde el pin hacia afuera y su etiqueta / simbolo / X de sin conectar."""
        px, py, d, red = pin
        red = net or red
        if red is None:
            self.nc(px, py)
            return
        ex, ey = px + d[0] * largo, py + d[1] * largo
        self.cable((px, py), (ex, ey))
        if red in ("GND", "+5V") and d[0] == 0:
            self.potencia(red, ex, ey, d)
        else:
            self.etiqueta(red, ex, ey, d, forma)

    def serie(self, a, b, red=None, x_etq=None, d_etq=(0, -1)):
        """Une 2 pines con un cable recto; con `red` pone la etiqueta global a mitad del cable."""
        ax, ay = a[0], a[1]
        bx, by = b[0], b[1]
        if red:
            mx, my = (snap((ax + bx) / 2), ay) if ay == by else (ax, snap((ay + by) / 2))
            self.cable((ax, ay), (mx, my), (bx, by))
            self.etiqueta(red, mx, my, d_etq)
        else:
            self.cable((ax, ay), (bx, by))

    def texto_archivo(self, comps_lib_blocks, titulo_doc):
        L = ['(kicad_sch (version 20230121) (generator eeschema)',
             '  (uuid %s)' % (uid("archivo", self.nombre) if self.archivo else ROOT),
             '  (paper "A4")',
             '  (title_block (title %s) (date "2026-11-25") (rev %s) (company "electronicarover")'
             % (qt(self.titulo), qt(D.REVISION)),
             '    (comment 3 %s)' % qt(titulo_doc),
             '    (comment 1 "Generado por hardware/tools/esquematico.py desde rover_design.py / rover_cubiko.py")',
             '    (comment 2 "Las redes se nombran con etiquetas globales: el nombre es el mismo que en la PCB")',
             '  )',
             '  (lib_symbols']
        for lib_id in sorted(self.used_libs):
            L.append("    " + comps_lib_blocks[lib_id].replace("\n", "\n    "))
        L.append('  )')
        L += self.L
        L += self._cables_partidos()
        if not self.archivo:
            L.append('  (sheet_instances (path "/" (page "1")))')
        L.append(')')
        return "\n".join(L) + "\n"


# ---------------------------------------------------------------------------
#  Librerias
# ---------------------------------------------------------------------------
def librerias(comps, syms):
    blocks, pins = {}, {}
    ids = {c["symbol"] for c in comps} | {"power:GND", "power:+5V"}
    for lib_id in ids:
        lib, name = lib_id.split(":")
        if lib == "rover":
            txt, p = syms[name]
            block = txt.strip()
        else:
            block = G.lib_symbol_text(lib, name)
            p = G.parse_pins(block)
        block = block.replace('(symbol "%s"' % name, '(symbol "%s:%s"' % (lib, name), 1)
        blocks[lib_id] = block
        pins[lib_id] = (block, [(str(n), float(x), float(y), int(a)) for (n, x, y, a) in p])
    return blocks, pins


def libres(c, nombres):
    return [nombres[int(n) - 1] for n in sorted(c["pins"], key=lambda k: int(k)) if not c["pins"][n]]


# ---------------------------------------------------------------------------
#  Hojas
# ---------------------------------------------------------------------------
def hoja_alimentacion(h):
    # --- 5 V ---------------------------------------------------------------
    h.marco(12.7, 12.7, 147.32, 88.9, "Entrada 5 V (Pi 5, ESP32, encoders)")
    j5 = h.comp("J5", 22.86, 50.8, mirror=True)
    yv, yg = 27.94, 81.28
    h.cable(j5["1"][:2], (33.02, j5["1"][1]), (33.02, yv))
    h.cable(j5["2"][:2], (35.56, j5["2"][1]), (35.56, yg))
    h.cable((33.02, yv), (114.3, yv))
    h.cable((35.56, yg), (91.44, yg))
    h.potencia("+5V", 40.64, yv, (0, -1)); h.union(40.64, yv)
    h.potencia("GND", 43.18, yg, (0, 1)); h.union(43.18, yg)
    for x in (58.42, 73.66, 91.44):
        h.union(x, yv)
    h.union(58.42, yg); h.union(73.66, yg)
    c2 = h.comp("C2", 58.42, 55.88)
    h.cable((58.42, yv), c2["1"][:2]); h.cable(c2["2"][:2], (58.42, yg))
    d1 = h.comp("D1", 73.66, 55.88, rot=270)
    h.cable((73.66, yv), d1["1"][:2]); h.cable(d1["2"][:2], (73.66, yg))
    r25 = h.comp("R25", 91.44, 40.64)
    d3 = h.comp("D3", 91.44, 68.58, rot=90)
    h.cable((91.44, yv), r25["1"][:2])
    h.serie(r25["2"], d3["2"], "LED5_A", d_etq=(1, 0))
    h.cable(d3["1"][:2], (91.44, yg))
    d5 = h.comp("D5", 124.46, 40.64, rot=180)
    d6 = h.comp("D6", 124.46, 53.34, rot=180)
    h.cable((114.3, yv), (114.3, 40.64), (114.3, 53.34))
    h.union(114.3, 40.64)
    h.cable((114.3, 40.64), d5["2"][:2]); h.cable((114.3, 53.34), d6["2"][:2])
    h.punta(d5["1"], 5.08, "output"); h.punta(d6["1"], 5.08, "output")
    h.texto(15.24, 60.96, "Del step-down\n12 V -> 5 V 5 A")
    h.texto(101.6, 60.96, "D5/D6: VIN de cada ESP32.\nEl USB de una ESP32 no\nalimenta al resto.")
    # --- bateria -------------------------------------------------------------
    h.marco(152.4, 12.7, 284.48, 88.9, "Medicion de bateria 3S")
    j2 = h.comp("J2", 162.56, 45.72, mirror=True)
    h.punta(j2["1"], 2.54)
    yb = 25.4
    h.cable(j2["2"][:2], (175.26, j2["2"][1]), (175.26, yb), (259.08, yb))
    h.etiqueta("VBAT_F", 175.26, yb, (0, -1))
    h.union(193.04, yb)
    r22 = h.comp("R22", 193.04, 40.64)
    r23 = h.comp("R23", 193.04, 66.04)
    c5 = h.comp("C5", 208.28, 66.04)
    h.cable((193.04, yb), r22["1"][:2])
    yn = 53.34
    h.cable(r22["2"][:2], (193.04, yn), r23["1"][:2])
    h.cable((193.04, yn), (208.28, yn), (226.06, yn))
    h.cable((208.28, yn), c5["1"][:2])
    h.union(193.04, yn); h.union(208.28, yn)
    h.etiqueta("VBAT_SENSE", 226.06, yn, (1, 0), "output")
    h.punta(r23["2"], 2.54); h.punta(c5["2"], 2.54)
    r24 = h.comp("R24", 259.08, 40.64)
    d2 = h.comp("D2", 259.08, 66.04, rot=90)
    h.cable((259.08, yb), r24["1"][:2])
    h.serie(r24["2"], d2["2"], "LED12_A", d_etq=(1, 0))
    h.punta(d2["1"], 2.54)
    h.texto(154.94, 76.2, "R22/R23: 12.6 V -> 2.68 V al ADC (IO34 de la ESP32-B);\n"
                          "el ADC satura (3.3 V) con 15.5 V.  C5 100 nF estabiliza la lectura.\n"
                          "D2 + R24: LED rojo de bateria, ~5 mA.")
    # --- servos --------------------------------------------------------------
    h.marco(12.7, 93.98, 147.32, 165.1, "Servos 6 V (BEC)")
    j6 = h.comp("J6", 22.86, 127.0, mirror=True)
    yv2, yg2 = 106.68, 157.48
    h.cable(j6["2"][:2], (35.56, j6["2"][1]), (35.56, yv2))
    h.cable(j6["1"][:2], (33.02, j6["1"][1]), (33.02, yg2))
    h.cable((35.56, yv2), (91.44, yv2))
    h.etiqueta("SERVO_V", 99.06, yv2, (1, 0), "output")
    h.cable((91.44, yv2), (99.06, yv2))
    h.cable((33.02, yg2), (91.44, yg2))
    h.potencia("GND", 43.18, yg2, (0, 1)); h.union(43.18, yg2)
    for x in (58.42, 73.66):
        h.union(x, yv2); h.union(x, yg2)
    h.union(91.44, yv2)
    for ref, x in (("C3", 58.42), ("C4", 73.66)):
        c = h.comp(ref, x, 132.08)
        h.cable((x, yv2), c["1"][:2]); h.cable(c["2"][:2], (x, yg2))
    r26 = h.comp("R26", 91.44, 119.38)
    d4 = h.comp("D4", 91.44, 144.78, rot=90)
    h.cable((91.44, yv2), r26["1"][:2])
    h.serie(r26["2"], d4["2"], "LEDS_A", d_etq=(1, 0))
    h.cable(d4["1"][:2], (91.44, yg2))
    h.texto(15.24, 137.16, "Del BEC 6 V\n>= 10 A")
    h.texto(104.14, 127.0, "C3, C4 1000 uF:\npicos de arranque\nde los 8 servos.")
    # --- notas ---------------------------------------------------------------
    h.marco(152.4, 93.98, 284.48, 165.1, "Fuera de la tarjeta")
    h.texto(154.94, 101.6,
            "Bateria LiPo 3S (11.1 V nominal, 12.6 V llena)\n"
            "  -> XT60 -> fusible 15 A -> bloque de distribucion:\n"
            "       3x L298N (12 V de motores)\n"
            "       step-down 12 V -> 5 V 5 A  ->  J5\n"
            "       BEC 12 V -> 6 V >= 10 A    ->  J6\n"
            "       J2: solo medicion y LED (< 10 mA)\n"
            "La corriente de los motores NO pasa por la tarjeta.\n"
            "GND comun en estrella en el bloque de distribucion.\n\n"
            "C2 1000 uF y D1 SA5.0A (TVS) protegen el 5 V de la Pi.\n"
            "La Pi 5 se alimenta por el GPIO (pines 2 y 4): pon\n"
            "usb_max_current_enable=1 en /boot/firmware/config.txt.")


def hoja_pi(h):
    u1 = h.comp("U1", 160.02, 101.6)
    for n, p in u1.items():
        if p[3] is None:
            h.nc(p[0], p[1])
    p2, p4 = u1["2"], u1["4"]
    xr = p2[0] + 7.62
    h.cable(p2[:2], (xr, p2[1])); h.cable(p4[:2], (xr, p4[1]))
    h.cable((xr, p4[1]), (xr, p2[1]), (xr, p2[1] - 5.08))
    h.union(xr, p2[1])
    h.potencia("+5V", xr, p2[1] - 5.08, (0, -1))
    for n in ("9", "25", "39"):
        h.punta(u1[n], 2.54)

    def uart(pin, ref, red_pi, forma):
        p = u1[pin]
        pin1_pi = h.comps[ref]["pins"][1] == red_pi
        izq = p[2][0] < 0
        x = p[0] + (-40.64 if izq else 40.64)
        rot = (270 if pin1_pi else 90) if izq else (90 if pin1_pi else 270)
        r = h.comp(ref, x, p[1], rot=rot)
        cerca = r["1"] if pin1_pi else r["2"]
        lejos = r["2"] if pin1_pi else r["1"]
        h.serie(p, cerca, red_pi)
        h.punta(lejos, 5.08, forma)
    uart("7", "R13", "PI_TXD2", "output")
    uart("29", "R14", "PI_RXD2", "input")
    uart("33", "R16", "PI_RXD4", "input")
    uart("32", "R15", "PI_TXD4", "output")
    h.texto(15.24, 15.24, "Raspberry Pi 5: header GPIO 2x20 (montado abajo; la Pi va debajo como HAT)", 2.0, True)
    h.texto(15.24, 22.86,
            "Enlaces serie Pi <-> ESP32, 3.3 V en los dos lados:\n"
            "  UART2  pin 7  GPIO4 TXD2  -> R13 1k -> ESP32-A RX (IO14)\n"
            "         pin 29 GPIO5 RXD2  <- R14 1k <- ESP32-A TX (IO27)\n"
            "         /dev/ttyAMA2  (config.txt: dtoverlay=uart2-pi5)\n"
            "  UART4  pin 32 GPIO12 TXD4 -> R15 1k -> ESP32-B RX (IO15)\n"
            "         pin 33 GPIO13 RXD4 <- R16 1k <- ESP32-B TX (IO2)\n"
            "         /dev/ttyAMA4  (config.txt: dtoverlay=uart4-pi5)\n"
            "Las 1k limitan la corriente si los 2 lados manejan la linea a la vez.")
    usados = sorted(int(n) for n, p in u1.items() if p[3])
    libres_ = [n for n in range(1, 41) if n not in usados and not D.RPI_PINS[n].startswith(("GND", "3V3", "5V"))]
    h.texto(15.24, 160.02,
            "Usados: pines %s.   GPIO libres (pin = nombre):\n%s"
            % (", ".join(map(str, usados)),
               "\n".join("  " + ",  ".join("%d=%s" % (n, D.RPI_PINS[n]) for n in libres_[i:i + 8])
                         for i in range(0, len(libres_), 8))))


def hoja_traccion(h):
    u2 = h.comp("U2", 99.06, 101.6)
    for n, p in u2.items():
        if n == "13":
            continue
        if p[3] is None:
            h.nc(p[0], p[1])
        else:
            h.punta(p, 5.08, "output" if p[3].startswith("U") or p[3] == "ESPA_TX"
                    else "input" if p[3].startswith("ENC") or p[3] == "ESPA_RX" else "passive")
    pe = u2["13"]
    xr = pe[0] - 22.86
    r21 = h.comp("R21", xr, pe[1] + 8.89)
    h.cable(pe[:2], (xr, pe[1]), (xr - 7.62, pe[1]))
    h.cable((xr, pe[1]), r21["1"][:2])
    h.union(xr, pe[1])
    h.etiqueta("MOTOR_EN", xr - 7.62, pe[1], (-1, 0), "output")
    h.punta(r21["2"], 2.54)
    modulo = {"EN": "ENA + ENB (cable en Y)", "ENB": "ENB", "IN4": "IN4", "IN3": "IN3", "IN2": "IN2", "IN1": "IN1", "ENA": "ENA", "GND": "GND logica"}
    for k, ref in enumerate(("J41", "J42", "J43")):
        y = 40.64 + 50.8 * k
        j = h.comp(ref, 200.66, y)
        for n, p in j.items():
            h.punta(p, 5.08, "input")
        c = h.comps[ref]
        h.texto(208.28, y - 11.43, "-> " + c["value"], 1.5, True)
        h.texto(208.28, y - 8.89, "\n".join("%d  %s" % (i + 1, modulo[t]) for i, t in enumerate(D.TB_ORDER)))
        m = re.search(r"\(([^)]*)\)", c.get("desc", ""))
        ab = m.group(1).split(" / ") if m else ["", ""]
        h.texto(240.3, y - 8.89, "motor A (IN1/IN2): %s\nmotor B (IN3/IN4): %s" % (ab[0], ab[-1]))
    h.texto(15.24, 15.24, "ESP32-A: traccion (3 L298N, 6 motores Pololu 37D)", 2.0, True)
    h.texto(15.24, 22.86,
            "Cada L298N maneja 2 motores: IN1/IN2 el A, IN3/IN4 el B (sentido y PWM).\n"
            "MOTOR_EN (IO13) habilita los 6 puentes. R21 10k lo deja en LOW al arrancar:\n"
            "ningun motor se mueve antes de que el firmware tome el control.\n"
            "En cada modulo quita los jumpers de ENA y ENB.\n"
            "TX0/IO1 (IN3 del #1) saca el log de arranque con MOTOR_EN en LOW: no mueve nada.")
    fr = libres(h.comps["U2"], D.ESP32_LEFT + D.ESP32_RIGHT)
    h.texto(15.24, 160.02,
            "Libres en la ESP32-A: %s\n"
            "IO12 debe estar en LOW al encender.  RX0/IO3 = USB.  EN = reset." % ", ".join(fr))


def hoja_encoders(h):
    filas = (("J7", 50.8, (1, 2, 3)), ("J8", 119.38, (6, 5, 4)))
    for ref, y0, ms in filas:
        j = h.comp(ref, 27.94, y0, mirror=True)
        for n, p in j.items():
            h.punta(p, 5.08, "input")
        for k, m in enumerate(ms):
            xc = 76.2 + 66.04 * k
            yt = y0 - 12.7
            h.texto(xc - 12.7, yt - 13.97, "M%d" % m, 1.8, True)
            rs = h.comp("R%d" % m, xc, yt)
            rg = h.comp("R%d" % (m + 6), xc, yt + 20.32)
            cf = h.comp("C%d" % (m + 10), xc + 12.7, yt + 20.32)
            h.punta(rs["1"], 5.08, "input")
            yn = yt + 10.16
            h.cable(rs["2"][:2], (xc, yn), rg["1"][:2])
            h.cable((xc, yn), (xc + 12.7, yn), (xc + 25.4, yn))
            h.cable((xc + 12.7, yn), cf["1"][:2])
            h.union(xc, yn); h.union(xc + 12.7, yn)
            h.etiqueta("ENC%d_A" % m, xc + 25.4, yn, (1, 0), "output")
            h.punta(rg["2"], 2.54); h.punta(cf["2"], 2.54)
    h.texto(15.24, 15.24, "Encoders: canal A de los 6 motores (5 V -> 3.3 V)", 2.0, True)
    h.texto(15.24, 148.59,
            "Encoder Pololu 37D: VCC 5 V, canal A de 5 V.  Divisor 10k / 20k: 5 V -> 3.33 V (seguro para la ESP32).\n"
            "Filtro 10k || 20k = 6.7k con 1 nF: corte en ~24 kHz.  El canal A llega a ~2.7 kHz a 10 000 rpm\n"
            "del motor (16 ciclos por vuelta): pasa entero y el ruido de las escobillas se filtra.\n"
            "Solo se cablea el canal A (velocidad); el sentido lo conoce el firmware.\n"
            "Cable Pololu: verde GND, azul VCC, amarillo A, blanco B (sin usar).")


def hoja_servos(h):
    u3 = h.comp("U3", 76.2, 101.6)
    for n, p in u3.items():
        if p[3] is None:
            h.nc(p[0], p[1])
        else:
            h.punta(p, 5.08, "output" if p[3].startswith("SERVO") or p[3] == "ESPB_TX"
                    else "input" if p[3] in ("ESPB_RX", "VBAT_SENSE") else "passive")
    for k in range(8):
        ref = "J%d" % (31 + k)
        x = 177.8 if k < 4 else 254.0
        y = 43.18 + 27.94 * (k % 4)
        j = h.comp(ref, x, y)
        for n, p in j.items():
            h.punta(p, 5.08, "input" if p[3] and p[3].startswith("SERVO") and p[3] != "SERVO_V" else "passive")
        h.texto(x + 6.35, y - 1.27, h.comps[ref].get("desc", "").split("(")[0].strip().replace(" - ", "\n"))
    h.texto(15.24, 15.24, "ESP32-B: 8 servos y medicion de bateria", 2.0, True)
    h.texto(15.24, 22.86,
            "PWM de 3.3 V directo de la ESP32 (los Power HD 1501MG lo aceptan).\n"
            "V+ = SERVO_V (6 V del BEC, hoja Alimentacion); GND comun.\n"
            "Header 1x3: SIG arriba, V+ al centro, GND abajo.\n"
            "VBAT_SENSE (IO34): bateria por el divisor 100k/27k.")
    fr = libres(h.comps["U3"], D.ESP32_LEFT + D.ESP32_RIGHT)
    h.texto(15.24, 160.02,
            "Libres en la ESP32-B: %s\n"
            "IO36, IO39, IO35 y IO34: solo entrada.  IO12 en LOW al arrancar.  TX0/RX0 = USB."
            % ", ".join(fr))


# ---------------------------------------------------------------------------
#  Tarjetas de una cara (traccion / servos)
# ---------------------------------------------------------------------------
def bloque_pi(h, x0, y0, j9, r_tx, r_rx, uart, pin_tx, pin_rx, pin_gnd):
    """J9 (borna hacia el HAT de la Pi) -> resistencias de 1k -> etiquetas de la ESP32."""
    h.marco(x0, y0, x0 + 132.08, y0 + 71.12, "Enlace con la Raspberry Pi (%s)" % uart)
    j = h.comp(j9, x0 + 12.7, y0 + 20.32, mirror=True)
    h.punta(j["1"], 2.54)
    c = h.comps
    p2, p3 = j["2"], j["3"]
    red2, red3 = c[j9]["pins"][2], c[j9]["pins"][3]
    # la resistencia de cada pin es la que tiene su red (el orden de J9 cambia entre tarjetas)
    r_tx, r_rx = [next(r for r in (r_tx, r_rx) if red in c[r]["pins"].values()) for red in (red2, red3)]
    # pin 2: TX de la Pi -> R -> RX de la ESP32
    xa, ya = p2[0] + 17.78, p2[1] + 12.7
    ra = h.comp(r_tx, xa + 3.81, ya, rot=90 if c[r_tx]["pins"][1] == red2 else 270)
    lado_pi = ra["1"] if c[r_tx]["pins"][1] == red2 else ra["2"]
    lado_esp = ra["2"] if lado_pi is ra["1"] else ra["1"]
    h.cable(p2[:2], (xa, p2[1]), (xa, p2[1] + 5.08), (xa, ya), lado_pi[:2])
    h.etiqueta(red2, xa, p2[1] + 5.08, (1, 0))
    h.punta(lado_esp, 7.62, "output")
    # pin 3: RX de la Pi <- R <- TX de la ESP32
    xb, yb = p3[0] + 10.16, p3[1] + 25.4
    rb = h.comp(r_rx, xb + 3.81, yb, rot=90 if c[r_rx]["pins"][1] == red3 else 270)
    lado_pi = rb["1"] if c[r_rx]["pins"][1] == red3 else rb["2"]
    lado_esp = rb["2"] if lado_pi is rb["1"] else rb["1"]
    h.cable(p3[:2], (xb, p3[1]), (xb, yb - 7.62), (xb, yb), lado_pi[:2])
    h.etiqueta(red3, xb, yb - 7.62, (1, 0))
    h.punta(lado_esp, 7.62, "input")
    filas = []
    for k, red in ((2, red2), (3, red3)):
        pin = pin_tx if "TXD" in red else pin_rx
        filas.append("  J9-%d %s  %s  %s (pin %d)" % (k, "TX" if "TXD" in red else "RX",
                                                     "<-" if "TXD" in red else "->", D.RPI_PINS[pin], pin))
    h.texto(x0 + 2.54, y0 + 50.8,
            "%s viene del HAT de bornas montado en la Raspberry Pi 5\n"
            "(header hembra 2x20 sobre el GPIO):\n"
            "  J9-1 GND  <-  GND (pin %d)\n%s\n"
            "Cable de 3 hilos trenzado, < 50 cm.  1k en serie: protegen los 2 lados." %
            (uart, pin_gnd, "\n".join(filas)))


def nota_fuera(h, x0, y0, x1, y1, extra):
    h.marco(x0, y0, x1, y1, "Fuera de la tarjeta")
    h.texto(x0 + 2.54, y0 + 7.62,
            "Bateria LiPo 3S -> fusible 15 A -> bloque de distribucion:\n"
            "   3x L298N (12 V de motores, NO pasa por las tarjetas)\n"
            "   step-down 12 V -> 5 V 5 A: Raspberry Pi (por su HAT de\n"
            "      bornas, con el TVS SA5.0A en esas bornas) y J5 de\n"
            "      cada tarjeta\n"
            "   BEC 12 V -> 6 V >= 10 A: J6 de la tarjeta de servos\n"
            "GND comun en estrella en el bloque de distribucion.\n" + extra)


def hoja_alim_traccion(h):
    h.marco(12.7, 12.7, 147.32, 88.9, "Entrada 5 V (ESP32-A y encoders)")
    j5 = h.comp("J5", 22.86, 50.8, mirror=True)
    yv, yg = 27.94, 81.28
    h.cable(j5["1"][:2], (33.02, j5["1"][1]), (33.02, yv))
    h.cable(j5["2"][:2], (35.56, j5["2"][1]), (35.56, yg))
    h.cable((33.02, yv), (114.3, yv))
    h.cable((35.56, yg), (91.44, yg))
    h.potencia("+5V", 40.64, yv, (0, -1)); h.union(40.64, yv)
    h.potencia("GND", 43.18, yg, (0, 1)); h.union(43.18, yg)
    for x in (58.42, 91.44):
        h.union(x, yv)
    h.union(58.42, yg)
    c2 = h.comp("C2", 58.42, 55.88)
    h.cable((58.42, yv), c2["1"][:2]); h.cable(c2["2"][:2], (58.42, yg))
    r25 = h.comp("R25", 91.44, 40.64)
    d3 = h.comp("D3", 91.44, 68.58, rot=90)
    h.cable((91.44, yv), r25["1"][:2])
    h.serie(r25["2"], d3["2"], "LED5_A", d_etq=(1, 0))
    h.cable(d3["1"][:2], (91.44, yg))
    d5 = h.comp("D5", 124.46, 40.64, rot=180)
    h.cable((114.3, yv), (114.3, 40.64), d5["2"][:2])
    h.punta(d5["1"], 5.08, "output")
    h.texto(15.24, 60.96, "Del step-down\n12 V -> 5 V")
    h.texto(101.6, 55.88, "D5 1N5819: VIN de la ESP32-A.\nEl USB de la ESP32 no\nalimenta los encoders.\n\n"
                          "+5V tambien alimenta los\nencoders (J7/J8, pin 2).")
    bloque_pi(h, 152.4, 12.7, "J9", "R13", "R14", "UART2", 7, 29, 6)
    nota_fuera(h, 12.7, 93.98, 284.48, 165.1,
               "\nEn cada L298N: quita los jumpers de ENA y ENB y une los 2 pines al hilo EN de su borna (cable en Y).")


def hoja_alim_servos(h):
    h.marco(12.7, 12.7, 101.6, 60.96, "Entrada 5 V (ESP32-B)")
    j5 = h.comp("J5", 22.86, 35.56, mirror=True)
    d6 = h.comp("D6", 60.96, 35.56, rot=180)
    h.cable(j5["1"][:2], d6["2"][:2])
    h.potencia("+5V", 40.64, 35.56, (0, -1))
    h.punta(j5["2"], 2.54)
    h.punta(d6["1"], 5.08, "output")
    h.texto(15.24, 45.72, "Del step-down 12 V -> 5 V.  D6 1N5819: VIN de la ESP32-B;\nel USB de la ESP32 no regresa al 5 V.")
    # servos 6 V
    h.marco(12.7, 66.04, 147.32, 165.1, "Servos 6 V (BEC)")
    j6 = h.comp("J6", 22.86, 104.14, mirror=True)
    yv2, yg2 = 81.28, 152.4
    h.cable(j6["2"][:2], (35.56, j6["2"][1]), (35.56, yv2))
    h.cable(j6["1"][:2], (33.02, j6["1"][1]), (33.02, yg2))
    h.cable((35.56, yv2), (99.06, yv2))
    h.etiqueta("SERVO_V", 99.06, yv2, (1, 0), "output")
    h.cable((33.02, yg2), (91.44, yg2))
    h.potencia("GND", 43.18, yg2, (0, 1)); h.union(43.18, yg2)
    for x in (58.42, 73.66):
        h.union(x, yv2); h.union(x, yg2)
    h.union(91.44, yv2)
    for ref, x in (("C3", 58.42), ("C4", 73.66)):
        c = h.comp(ref, x, 116.84)
        h.cable((x, yv2), c["1"][:2]); h.cable(c["2"][:2], (x, yg2))
    r26 = h.comp("R26", 91.44, 99.06)
    d4 = h.comp("D4", 91.44, 129.54, rot=90)
    h.cable((91.44, yv2), r26["1"][:2])
    h.serie(r26["2"], d4["2"], "LEDS_A", d_etq=(1, 0))
    h.cable(d4["1"][:2], (91.44, yg2))
    h.texto(15.24, 114.3, "Del BEC 6 V\n>= 10 A")
    h.texto(104.14, 111.76, "C3, C4 1000 uF:\npicos de arranque\nde los 8 servos.\n\nD4 + R26 470:\nLED azul.")
    # bateria
    h.marco(106.68, 12.7, 284.48, 60.96, "Medicion de bateria 3S")
    j2 = h.comp("J2", 116.84, 35.56, mirror=True)
    h.punta(j2["1"], 2.54)
    yb = 20.32
    h.cable(j2["2"][:2], (129.54, j2["2"][1]), (129.54, yb), (215.9, yb))
    h.etiqueta("VBAT_F", 129.54, yb, (0, -1))
    h.union(147.32, yb)
    r22 = h.comp("R22", 147.32, 30.48)
    r23 = h.comp("R23", 147.32, 48.26)
    c5 = h.comp("C5", 162.56, 48.26)
    h.cable((147.32, yb), r22["1"][:2])
    yn = 39.37
    h.cable(r22["2"][:2], (147.32, yn), r23["1"][:2])
    h.cable((147.32, yn), (162.56, yn), (180.34, yn))
    h.cable((162.56, yn), c5["1"][:2])
    h.union(147.32, yn); h.union(162.56, yn)
    h.etiqueta("VBAT_SENSE", 180.34, yn, (1, 0), "output")
    h.punta(r23["2"], 2.54); h.punta(c5["2"], 2.54)
    r24 = h.comp("R24", 215.9, 30.48)
    d2 = h.comp("D2", 215.9, 48.26, rot=90)
    h.cable((215.9, yb), r24["1"][:2])
    h.serie(r24["2"], d2["2"], "LED12_A", d_etq=(1, 0))
    h.punta(d2["1"], 2.54)
    h.texto(231.14, 25.4, "R22/R23: 12.6 V -> 2.68 V\nal ADC (IO34).  Satura\n(3.3 V) con 15.5 V.\n"
                          "C5 estabiliza la lectura.\nD2 + R24: LED rojo, ~5 mA.")
    bloque_pi(h, 152.4, 66.04, "J9", "R15", "R16", "UART4", 32, 33, 34)
    nota_fuera(h, 152.4, 139.7, 284.48, 165.1, "")


# ---------------------------------------------------------------------------
def escribir(comps, syms, out_dir, titulo_doc):
    blocks, libs = librerias(comps, syms)
    by_ref = {c["ref"]: c for c in comps}
    if D.VARIANT == "traccion":
        defs = [("Alimentacion y Pi", "1_alimentacion_pi.kicad_sch", "2", "Entrada 5 V y enlace UART2 con la Pi", hoja_alim_traccion),
                ("ESP32-A traccion", "2_esp32a_traccion.kicad_sch", "3", "ESP32-A y bornas de los L298N", hoja_traccion),
                ("Encoders", "3_encoders.kicad_sch", "4", "Encoders: divisores 5 V -> 3.3 V", hoja_encoders)]
        intro = ("Tarjeta de una sola cara.  La Raspberry Pi 5 va aparte con un HAT de bornas y llega por J9 (UART2).\n"
                 "Los 3 L298N, la bateria y el step-down van en el chasis y llegan por bornas.\n"
                 "Doble clic en una hoja para entrar.  Los nombres de red son los de la PCB.")
    elif D.VARIANT == "servos":
        defs = [("Alimentacion, bateria y Pi", "1_alimentacion_pi.kicad_sch", "2", "5 V, servos 6 V, bateria y enlace UART4", hoja_alim_servos),
                ("ESP32-B servos", "2_esp32b_servos.kicad_sch", "3", "ESP32-B y 8 servos", hoja_servos)]
        intro = ("Tarjeta de una sola cara.  La Raspberry Pi 5 va aparte con un HAT de bornas y llega por J9 (UART4).\n"
                 "8 servos: 4 de direccion y 4 del brazo.  El BEC 6 V y la bateria llegan por bornas.\n"
                 "Doble clic en una hoja para entrar.  Los nombres de red son los de la PCB.")
    else:
        defs = [("Alimentacion", "1_alimentacion.kicad_sch", "2", "Alimentacion 5 V, servos 6 V y bateria", hoja_alimentacion),
                ("Raspberry Pi 5", "2_raspberry_pi.kicad_sch", "3", "Raspberry Pi 5 y UART a las ESP32", hoja_pi),
                ("ESP32-A traccion", "3_esp32a_traccion.kicad_sch", "4", "ESP32-A y bornas de los L298N", hoja_traccion),
                ("Encoders", "4_encoders.kicad_sch", "5", "Encoders: divisores 5 V -> 3.3 V", hoja_encoders),
                ("ESP32-B servos", "5_esp32b_servos.kicad_sch", "6", "ESP32-B, servos y bateria", hoja_servos)]
        intro = ("Raspberry Pi 5 (debajo, como HAT) + ESP32-A traccion + ESP32-B servos.\n"
                 "Los 3 L298N, la bateria, el step-down 5 V y el BEC 6 V van en el chasis y llegan por bornas.\n"
                 "Doble clic en una hoja para entrar.  Los nombres de red son los de la PCB.")
    hojas = []
    for (n, a, p, t, fn) in defs:
        h = Hoja(n, a, p, t, by_ref, libs)
        fn(h)
        hojas.append(h)
    # raiz: hojas, agujeros de montaje y tabla de interfaces
    root = Hoja("raiz", None, "1", "Indice", by_ref, libs)
    for k, h in enumerate(hojas):
        x, y = 15.24 + 91.44 * (k % 3), 45.72 + 33.02 * (k // 3)
        w, hh = 76.2, 22.86
        root.L.append('  (sheet (at %s %s) (size %s %s) (fields_autoplaced)' % (f(x), f(y), f(w), f(hh)))
        root.L.append('    (stroke (width 0.1524) (type solid)) (fill (color 0 0 0 0.0000))')
        root.L.append('    (uuid %s)' % h.uuid)
        root.L.append('    (property "Sheetname" %s (at %s %s 0) (effects (font (size 1.5 1.5) bold) (justify left bottom)))'
                      % (qt(h.nombre), f(x), f(y - 0.7)))
        root.L.append('    (property "Sheetfile" %s (at %s %s 0) (effects (font (size 1.27 1.27)) (justify left top)))'
                      % (qt(h.archivo), f(x), f(y + hh + 0.6)))
        root.L.append('    (instances (project %s (path %s (page %s))))' % (qt(D.PROJECT), qt("/" + ROOT), qt(h.pagina)))
        root.L.append('  )')
        root.texto(x + 1.27, y + 2.54, "Hoja %s\n%s" % (h.pagina, h.titulo), 1.27)
    for k, ref in enumerate(("H1", "H2", "H3", "H4")):
        root.comp(ref, 220.98 + 15.24 * k, 88.9)
    root.texto(205.74, 76.2, "Barrenos M3\n(H1: pin de alineacion)", 1.27)
    root.texto(15.24, 15.24, titulo_doc, 2.54, True)
    root.texto(15.24, 22.86, intro, 1.27)
    filas = []
    for net in sorted({n for h in hojas for n in h.redes}):
        en = [h.nombre for h in hojas if net in h.redes]
        if len(en) > 1:
            filas.append("%s:  %s" % (net, ",  ".join(en)))
    root.texto(15.24, 116.84, "Senales entre bloques (lo que cruzaria entre tarjetas si se separan)", 1.5, True)
    col = (len(filas) + 1) // 2
    root.texto(15.24, 121.92, "\n".join(filas[:col]), 1.27)
    root.texto(127.0, 121.92, "\n".join(filas[col:]), 1.27)
    # escribir
    for h in hojas + [root]:
        name = h.archivo or (D.PROJECT + ".kicad_sch")
        open(os.path.join(out_dir, name), "w", encoding="utf-8").write(h.texto_archivo(blocks, titulo_doc))
    # chequeo: todos los componentes colocados, toda red con 2 o mas pines
    falta = [c["ref"] for c in comps if "sym_path" not in c]
    if falta:
        raise RuntimeError("componentes sin hoja: %s" % falta)
    cuenta = {}
    for h in hojas:
        for n, k in h.redes.items():
            cuenta[n] = cuenta.get(n, 0) + k
    solas = [n for n, k in cuenta.items() if k < 2]
    if solas:
        raise RuntimeError("redes con un solo pin: %s" % solas)
    return [[ROOT, ""]] + [[h.uuid, h.nombre] for h in hojas]


def actualizar_pcb(pcb, comps):
    """Pone en la PCB ruteada las rutas jerarquicas (/hoja/simbolo) de cada huella."""
    txt = open(pcb, encoding="utf-8").read()
    n = 0
    for c in comps:
        old = '(path "/%s")' % c["sym_uuid"]
        new = '(path "%s")' % c["sym_path"]
        if old in txt:
            txt = txt.replace(old, new, 1); n += 1
        elif new in txt:
            n += 1
    open(pcb, "w", encoding="utf-8").write(txt)
    return n


if __name__ == "__main__":
    comps = D.build()
    syms = G.custom_symbols()
    G.SHEETS = escribir(comps, syms, G.OUT, D.TITLE)
    G.write_project(D.nets())
    if "--pcb" in sys.argv:
        pcb = os.path.join(G.OUT, D.PROJECT + ".kicad_pcb")
        print("huellas enlazadas:", actualizar_pcb(pcb, comps), "de", len(comps))
    print("OK esquematico ->", G.OUT)
