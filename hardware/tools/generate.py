#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Genera el proyecto KiCad completo del Rover Controller:

  hardware/rover_controller/
      rover_controller.kicad_pro / .kicad_sch / .kicad_pcb
      rover.kicad_sym   (simbolos propios)
      rover.pretty/     (footprints propios: L298N, ESP32, RPi5)
      sym-lib-table, fp-lib-table

Uso (requiere KiCad 7+ con su python, que trae el modulo pcbnew):
    python3 hardware/tools/generate.py            # sch + pcb sin rutear
    python3 hardware/tools/generate.py --route    # + ruteo de una capa

El ruteo (--route) usa router1l.py: UNA sola capa de cobre (B.Cu) + puentes de
alambre (dibujados en F.Cu solo como guia). Requiere numpy y scipy.
"""
import json
import math
import os
import re
import subprocess
import sys
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rover_design as D  # noqa: E402

OUT = os.path.normpath(os.path.join(HERE, "..", D.PROJECT))
KICAD_SYM_DIR = os.environ.get("KICAD7_SYMBOL_DIR", "/usr/share/kicad/symbols")
KICAD_FP_DIR = os.environ.get("KICAD7_FOOTPRINT_DIR", "/usr/share/kicad/footprints")
NS = uuid.UUID("6f1c1d1e-0000-4000-8000-0000000c0de5")


def uid(*parts):
    return str(uuid.uuid5(NS, "/".join(str(p) for p in parts)))


def q(s):
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"') + '"'


def f(v):
    s = ("%.4f" % v).rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


# ============================================================================
#  SIMBOLOS PROPIOS
# ============================================================================
def box_symbol(name, ref, left, right, width=20.32, value=None, fp="", descr=""):
    """left/right: lista de (numero, nombre) o None para hueco."""
    n = max(len(left), len(right))
    h = 2.54 * (n + 1)
    top = h / 2.0
    top = round(top / 1.27) * 1.27
    hw = width / 2.0
    lines = []
    lines.append('  (symbol %s (in_bom yes) (on_board yes)' % q(name))
    lines.append('    (property "Reference" %s (at 0 %s 0) (effects (font (size 1.27 1.27))))'
                 % (q(ref), f(top + 1.27)))
    lines.append('    (property "Value" %s (at 0 %s 0) (effects (font (size 1.27 1.27))))'
                 % (q(value or name), f(top - h - 1.27)))
    lines.append('    (property "Footprint" %s (at 0 0 0) (effects (font (size 1.27 1.27)) hide))' % q(fp))
    lines.append('    (property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))')
    lines.append('    (property "Description" %s (at 0 0 0) (effects (font (size 1.27 1.27)) hide))' % q(descr))
    lines.append('    (symbol %s' % q(name + "_0_1"))
    lines.append('      (rectangle (start %s %s) (end %s %s) (stroke (width 0.254) (type default)) (fill (type background)))'
                 % (f(-hw), f(top), f(hw), f(top - h)))
    lines.append('    )')
    lines.append('    (symbol %s' % q(name + "_1_1"))
    pins = []
    for side, plist in (("L", left), ("R", right)):
        for i, p in enumerate(plist):
            if p is None:
                continue
            num, pname = p
            y = top - 2.54 * (i + 1)
            if side == "L":
                x, ang = -hw - 2.54, 0
            else:
                x, ang = hw + 2.54, 180
            pins.append((num, x, y, ang))
            lines.append('      (pin passive line (at %s %s %d) (length 2.54) (name %s (effects (font (size 1.27 1.27)))) (number %s (effects (font (size 1.27 1.27)))))'
                         % (f(x), f(y), ang, q(pname), q(num)))
    lines.append('    )')
    lines.append('  )')
    return "\n".join(lines), pins


def custom_symbols():
    syms = {}
    # L298N
    left = [("1", "OUT1"), ("2", "OUT2"), ("3", "OUT3"), ("4", "OUT4"), None,
            ("5", "+12V"), ("6", "GND"), ("7", "+5V")]
    right = [("8", "ENA"), ("9", "IN1"), ("10", "IN2"), ("11", "IN3"), ("12", "IN4"), ("13", "ENB")]
    syms["L298N_Module"] = box_symbol("L298N_Module", "U", left, right, 15.24,
                                      fp="rover:L298N_Module_Pins",
                                      descr="Modulo L298N HW-095 montado con pines")
    # ESP32
    left = [(str(i + 1), n) for i, n in enumerate(D.ESP32_LEFT)]
    right = [(str(i + 16), n) for i, n in enumerate(D.ESP32_RIGHT)]
    syms["ESP32_DevKitV1_30P"] = box_symbol("ESP32_DevKitV1_30P", "U", left, right, 20.32,
                                            fp="rover:ESP32_DevKitV1_30P_DualPitch",
                                            descr="ESP32 DevKit V1 (DOIT) 30 pines")
    # RPi
    left = [(str(n), D.RPI_PINS[n]) for n in range(1, 41, 2)]
    right = [(str(n), D.RPI_PINS[n]) for n in range(2, 41, 2)]
    syms["RaspberryPi5_GPIO"] = box_symbol("RaspberryPi5_GPIO", "U", left, right, 25.4,
                                           fp="rover:RPi5_HAT_Header_2x20",
                                           descr="Raspberry Pi 5 - header GPIO 40 pines")
    # Pololu
    left = [("1", "M+ (rojo)"), ("2", "M- (negro)"), ("3", "GND (verde)"),
            ("4", "VCC (azul)"), ("5", "A (amarillo)"), ("6", "B (blanco)")]
    syms["Pololu_37D_Encoder"] = box_symbol("Pololu_37D_Encoder", "J", left, [], 17.78,
                                            descr="Conector cable Pololu 37D con encoder")
    syms["XT60_Battery"] = box_symbol("XT60_Battery", "J", [("1", "- (biselado)"), ("2", "+ (recto)")], [], 12.7,
                                      fp="Connector_AMASS:AMASS_XT60-M_1x02_P7.20mm_Vertical",
                                      descr="Conector XT60 macho para bateria")
    syms["Servo_Header"] = box_symbol("Servo_Header", "J",
                                      [("1", "GND"), ("2", "V+"), ("3", "SIG")], [], 7.62,
                                      descr="Servo 3 pines")
    syms["Aux_Header_4"] = box_symbol("Aux_Header_4", "J",
                                      [(str(i), "P%d" % i) for i in range(1, 5)], [], 5.08)
    syms["Aux_Header_8"] = box_symbol("Aux_Header_8", "J",
                                      [(str(i), "P%d" % i) for i in range(1, 9)], [], 5.08)
    return syms


def lib_symbol_text(lib, name):
    path = os.path.join(KICAD_SYM_DIR, lib + ".kicad_sym")
    txt = open(path, encoding="utf-8").read()
    i = txt.find('(symbol "%s"' % name)
    if i < 0:
        raise RuntimeError("simbolo %s:%s no encontrado" % (lib, name))
    depth, j = 0, i
    in_str = False
    while True:
        ch = txt[j]
        if ch == '"' and txt[j - 1] != "\\":
            in_str = not in_str
        elif not in_str:
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    break
        j += 1
    block = txt[i:j + 1]
    if "(extends" in block:
        raise RuntimeError("simbolo con extends no soportado: " + name)
    return block


def parse_pins(block):
    pins = []
    for m in re.finditer(r'\(pin \w+ \w+\s*\(at ([-\d.]+) ([-\d.]+) (\d+)\)\s*\(length ([\d.]+)\)'
                         r'.*?\(number "([^"]+)"', block, re.S):
        pins.append((m.group(5), float(m.group(1)), float(m.group(2)), int(m.group(3))))
    return pins


def parse_props(block):
    props = {}
    for m in re.finditer(r'\(property "([^"]+)" "([^"]*)" \(at ([-\d.]+) ([-\d.]+) (\d+)\)', block):
        props[m.group(1)] = (float(m.group(3)), float(m.group(4)), int(m.group(5)))
    return props


# ============================================================================
#  FOOTPRINTS PROPIOS
# ============================================================================
def fp_header(name, descr, tags):
    return ['(footprint %s (version 20221018) (generator pcbnew)' % q(name),
            '  (layer "F.Cu")',
            '  (descr %s)' % q(descr),
            '  (tags %s)' % q(tags),
            '  (attr through_hole)']


def fp_text(kind, text, x, y, layer, size=1.0, hide=False):
    return ('  (fp_text %s %s (at %s %s) (layer %s)%s (effects (font (size %s %s) (thickness %s))))'
            % (kind, q(text), f(x), f(y), q(layer), " hide" if hide else "", f(size), f(size), f(size * 0.15)))


def fp_rect(x0, y0, x1, y1, layer, w=0.12):
    return ('  (fp_rect (start %s %s) (end %s %s) (stroke (width %s) (type default)) (fill none) (layer %s))'
            % (f(x0), f(y0), f(x1), f(y1), f(w), q(layer)))


def fp_line(x0, y0, x1, y1, layer, w=0.12):
    return ('  (fp_line (start %s %s) (end %s %s) (stroke (width %s) (type default)) (layer %s))'
            % (f(x0), f(y0), f(x1), f(y1), f(w), q(layer)))


def fp_pad(num, x, y, size, drill, shape="circle"):
    return ('  (pad %s thru_hole %s (at %s %s) (size %s %s) (drill %s) (layers "*.Cu" "*.Mask"))'
            % (q(num), shape, f(x), f(y), f(size), f(size), f(drill)))


def fp_npth(x, y, drill):
    return ('  (pad "" np_thru_hole circle (at %s %s) (size %s %s) (drill %s) (layers "*.Cu" "*.Mask"))'
            % (f(x), f(y), f(drill), f(drill), f(drill)))


def footprint_l298n():
    g = D.L298N
    s = g["size"] / 2
    L = fp_header("L298N_Module_Pins",
                  "Modulo L298N rojo (HW-095) 43x43mm montado con pines en lugar de bornas. "
                  "VERIFICAR cotas imprimiendo 1:1 antes de fabricar.",
                  "L298N module motor driver")
    L.append(fp_text("reference", "REF**", 0, -s - 1.5, "F.SilkS", 1.2))
    L.append(fp_text("value", "L298N_Module", 0, 0, "F.Fab", 1.2))
    L.append(fp_rect(-s, -s, s, s, "F.SilkS", 0.15))
    L.append(fp_rect(-s, -s, s, s, "F.Fab", 0.1))
    L.append(fp_rect(-s - 0.5, -s - 0.5, s + 0.5, s + 0.5, "F.CrtYd", 0.05))
    # disipador (referencia)
    L.append(fp_rect(-11.5, -s, 11.5, -s + 9, "F.Fab", 0.1))
    L.append(fp_text("user", "DISIPADOR", 0, -s + 4.5, "F.SilkS", 1.0))
    for (x, y) in g["mount_holes"]:
        L.append(fp_npth(x, y, g["mount_drill"]))
    pd, pp = g["power_drill"], g["power_pad"]
    num = 1
    for key in ("OUT1", "OUT2", "OUT3", "OUT4", "+12V", "GND", "+5V"):
        x, y = g[key]
        L.append(fp_pad(str(num), x, y, pp, pd, "rect" if num in (1, 3, 5) else "circle"))
        lx = x + (3.6 if x < 0 else -3.6) if key.startswith("OUT") else x
        ly = y if key.startswith("OUT") else y - 2.9
        L.append(fp_text("user", key, lx, ly, "F.SilkS", 0.8))
        num += 1
    hx, hy = g["header_first"]
    for i, key in enumerate(("ENA", "IN1", "IN2", "IN3", "IN4", "ENB")):
        x = hx + 2.54 * i
        L.append(fp_pad(str(8 + i), x, hy, g["logic_pad"], g["logic_drill"], "rect" if i == 0 else "circle"))
        L.append(fp_text("user", key, x, hy - 2.2, "F.SilkS", 0.6))
    L.append(fp_text("user", "Quitar jumpers ENA/ENB", 0, 10.5, "F.SilkS", 0.8))
    L.append(fp_text("user", "${REFERENCE}", 0, -6, "F.Fab", 1.0))
    L.append(")")
    return "\n".join(L)


def footprint_esp32():
    g = D.ESP32
    L = fp_header("ESP32_DevKitV1_30P_DualPitch",
                  "ESP32 DevKit V1 (DOIT) 30 pines. Fila derecha doble: 25.4mm o 22.86mm entre filas. "
                  "Soldar el header hembra en la fila que coincida con tu placa.",
                  "ESP32 DevKit DOIT 30 pin")
    x0, y0, x1, y1 = g["outline"]
    L.append(fp_text("reference", "REF**", 0, y0 - 1.5, "F.SilkS", 1.2))
    L.append(fp_text("value", "ESP32_DevKitV1_30P", 0, 0, "F.Fab", 1.0))
    L.append(fp_rect(x0, y0, x1, y1, "F.SilkS", 0.15))
    L.append(fp_rect(x0, y0, x1, y1, "F.Fab", 0.1))
    L.append(fp_rect(x0 - 0.5, y0 - 0.5, x1 + 0.5, y1 + 0.5, "F.CrtYd", 0.05))
    ax0, ay0, ax1, ay1 = g["antenna_keepout"]
    L.append(fp_rect(ax0, ay0, ax1, ay1, "F.SilkS", 0.12))
    L.append(fp_text("user", "ANTENA", 0, (ay0 + ay1) / 2, "F.SilkS", 1.0))
    L.append(fp_text("user", "USB", 0, y1 - 2.5, "F.SilkS", 1.0))
    n = g["pins_per_side"]
    ytop = -g["pitch"] * (n - 1) / 2
    for i in range(n):
        y = ytop + g["pitch"] * i
        L.append(fp_pad(str(i + 1), g["row_left_x"], y, g["pad"], g["drill"], "rect" if i == 0 else "circle"))
        L.append(fp_pad(str(i + 16), g["row_right_x"], y, g["pad"], g["drill"]))
        L.append(fp_pad(str(i + 16), g["row_right_alt_x"], y, g["pad"], g["drill"]))
        L.append(fp_text("user", D.ESP32_LEFT[i].split("/")[-1], g["row_left_x"] + 3.6, y, "F.SilkS", 0.6))
        L.append(fp_text("user", D.ESP32_RIGHT[i].split("/")[-1], g["row_right_alt_x"] - 3.8, y, "F.SilkS", 0.6))
    L.append(fp_text("user", "25.4", g["row_right_x"], ytop - 2.6, "F.SilkS", 0.7))
    L.append(fp_text("user", "22.86", g["row_right_alt_x"] - 0.6, ytop - 4.0, "F.SilkS", 0.7))
    L.append(")")
    return "\n".join(L)


def footprint_servo():
    """Header 1x3 para servo (GND, V+, SIG) con patio ajustado a 2.54 mm, para poder
    apilar conectores de servo uno junto al otro como en un shield de servos."""
    L = fp_header("Servo_Header_1x03", "Header macho 1x3 2.54mm para servo (GND, V+, SIG)",
                  "servo header 1x3")
    L.append(fp_text("reference", "REF**", 0, -2.2, "F.SilkS", 0.8, hide=True))
    L.append(fp_text("value", "Servo", 0, 7.0, "F.Fab", 0.8))
    L.append(fp_rect(-1.27, -1.27, 1.27, 6.35, "F.Fab", 0.1))
    L.append(fp_rect(-1.25, -1.6, 1.25, 6.68, "F.CrtYd", 0.05))
    for i in range(3):
        L.append(fp_pad(str(i + 1), 0, 2.54 * i, 1.7, 1.0, "rect" if i == 0 else "circle"))
    L.append(")")
    return "\n".join(L)


def footprint_rpi():
    g = D.RPI
    L = fp_header("RPi5_HAT_Header_2x20",
                  "Raspberry Pi 5 montada DEBAJO de la PCB (estilo HAT). PCB de una capa: usar "
                  "stacking header 2x20 de pines largos insertado desde abajo y soldado por la "
                  "cara de cobre. Agujeros M2.5 58x49mm.",
                  "raspberry pi 5 hat gpio")
    L.append(fp_text("reference", "REF**", 4, 9, "F.SilkS", 1.2))
    L.append(fp_text("value", "RaspberryPi5", 30, 30, "F.Fab", 1.5))
    L.append(fp_rect(0, 0, g["pi_w"], g["pi_h"], "F.Fab", 0.1))
    L.append(fp_rect(0, 0, g["hat_w"], g["hat_h"], "F.SilkS", 0.15))
    # patio solo alrededor del header: el resto del area de la Pi admite componentes
    # de perfil bajo (resistencias/transistores con patas cortadas al ras)
    px0 = g["pin1"][0] - 1.6
    L.append(fp_rect(px0, g["row_even_y"] - 1.6, px0 + 2.54 * 19 + 3.2, g["pin1"][1] + 1.6, "F.CrtYd", 0.05))
    L.append(fp_text("user", "RASPBERRY PI 5 (montada debajo)", 32.5, 22, "F.SilkS", 2.0))
    L.append(fp_text("user", "Stacking header 2x20 (pines largos) desde ABAJO", 32.5, 27, "F.SilkS", 1.4))
    L.append(fp_text("user", "soldar por la cara de cobre - standoffs M2.5", 32.5, 31, "F.SilkS", 1.2))
    L.append(fp_text("user", "USB/ETH ->", 60, 45, "F.SilkS", 1.5))
    for (x, y) in g["holes"]:
        L.append(fp_npth(x, y, g["hole_drill"]))
    px, py = g["pin1"]
    for n in range(1, 41):
        idx = (n - 1) // 2
        x = px + 2.54 * idx
        y = py if n % 2 == 1 else g["row_even_y"]
        L.append(fp_pad(str(n), x, y, g["pad"], g["drill"], "rect" if n == 1 else "circle"))
    L.append(fp_text("user", "1", px - 2.0, py + 0.2, "F.SilkS", 0.8))
    L.append(fp_text("user", "40", px + 2.54 * 19 + 2.4, g["row_even_y"], "F.SilkS", 0.8))
    L.append(")")
    return "\n".join(L)


# ============================================================================
#  ESQUEMATICO
# ============================================================================
GRID = 1.27


def snap(v):
    return round(v / GRID) * GRID


def write_symbol_lib(syms):
    out = ['(kicad_symbol_lib (version 20220914) (generator kicad_symbol_editor)']
    for name, (txt, _) in syms.items():
        out.append(txt)
    out.append(')')
    open(os.path.join(OUT, "rover.kicad_sym"), "w", encoding="utf-8").write("\n".join(out) + "\n")


def write_schematic(comps, syms):
    root = uid("root-sheet")
    lib_blocks = {}
    pin_defs = {}
    prop_defs = {}
    for c in comps:
        lib, name = c["symbol"].split(":")
        if c["symbol"] in lib_blocks:
            continue
        if lib == "rover":
            txt, pins = syms[name]
            block = txt.strip()
            pin_defs[c["symbol"]] = pins
        else:
            block = lib_symbol_text(lib, name)
            pin_defs[c["symbol"]] = parse_pins(block)
        prop_defs[c["symbol"]] = parse_props(block)
        # renombrar el simbolo raiz a lib:name (los sub-simbolos conservan el nombre)
        block = block.replace('(symbol "%s"' % name, '(symbol "%s:%s"' % (lib, name), 1)
        lib_blocks[c["symbol"]] = block

    L = ['(kicad_sch (version 20230121) (generator eeschema)',
         '  (uuid %s)' % root,
         '  (paper "A1")',
         '  (title_block (title %s) (date "2026-11-17") (rev %s) (company "electronicarover")'
         % (q(D.TITLE), q(D.REVISION)),
         '    (comment 1 "Generado por hardware/tools/generate.py - no editar a mano, editar rover_design.py")'
         ,
         '  )',
         '  (lib_symbols']
    for b in lib_blocks.values():
        L.append("    " + b.replace("\n", "\n    "))
    L.append('  )')

    used_nets = {}
    for c in comps:
        sx, sy = snap(c["sch"][0]), snap(c["sch"][1])
        sym_uuid = uid("sym", c["ref"])
        c["sym_uuid"] = sym_uuid
        props = prop_defs[c["symbol"]]
        fp = c["footprint"]
        L.append('  (symbol (lib_id %s) (at %s %s 0) (unit 1)' % (q(c["symbol"]), f(sx), f(sy)))
        L.append('    (in_bom yes) (on_board yes) (dnp no)')
        L.append('    (uuid %s)' % sym_uuid)
        rx, ry, rr = props.get("Reference", (0, 2.54, 0))
        vx, vy, vr = props.get("Value", (0, -2.54, 0))
        L.append('    (property "Reference" %s (at %s %s %d) (effects (font (size 1.27 1.27))))'
                 % (q(c["ref"]), f(sx + rx), f(sy - ry), rr))
        L.append('    (property "Value" %s (at %s %s %d) (effects (font (size 1.27 1.27))))'
                 % (q(c["value"]), f(sx + vx), f(sy - vy), vr))
        L.append('    (property "Footprint" %s (at %s %s 0) (effects (font (size 1.27 1.27)) hide))'
                 % (q(fp), f(sx), f(sy)))
        L.append('    (property "Datasheet" "~" (at %s %s 0) (effects (font (size 1.27 1.27)) hide))' % (f(sx), f(sy)))
        L.append('    (property "Descripcion" %s (at %s %s 0) (effects (font (size 1.27 1.27)) hide))'
                 % (q(c.get("desc", "")), f(sx), f(sy)))
        L.append('    (property "MPN" %s (at %s %s 0) (effects (font (size 1.27 1.27)) hide))'
                 % (q(c.get("mpn", c["value"])), f(sx), f(sy)))
        for (num, px, py, ang) in pin_defs[c["symbol"]]:
            L.append('    (pin %s (uuid %s))' % (q(num), uid("pin", c["ref"], num)))
        L.append('    (instances (project %s (path "/%s" (reference %s) (unit 1))))'
                 % (q(D.PROJECT), root, q(c["ref"])))
        L.append('  )')
        # etiquetas en cada pin
        for (num, px, py, ang) in pin_defs[c["symbol"]]:
            ex, ey = sx + px, sy - py
            net = c["pins"].get(num) if num in c["pins"] else c["pins"].get(int(num)) if num.isdigit() else None
            key_present = (num in c["pins"]) or (num.isdigit() and int(num) in c["pins"])
            if not key_present and c["pins"]:
                raise RuntimeError("%s pin %s sin asignar" % (c["ref"], num))
            if net is None:
                L.append('  (no_connect (at %s %s) (uuid %s))' % (f(ex), f(ey), uid("nc", c["ref"], num)))
                continue
            used_nets.setdefault(net, 0)
            used_nets[net] += 1
            # direccion hacia afuera del simbolo
            d = {0: (-1, 0), 180: (1, 0), 90: (0, 1), 270: (0, -1)}[ang]
            wx, wy = ex + d[0] * 2.54, ey + d[1] * 2.54
            L.append('  (wire (pts (xy %s %s) (xy %s %s)) (stroke (width 0) (type default)) (uuid %s))'
                     % (f(ex), f(ey), f(wx), f(wy), uid("w", c["ref"], num)))
            lang, just = {(-1, 0): (180, "right"), (1, 0): (0, "left"),
                          (0, 1): (270, "right"), (0, -1): (90, "left")}[d]
            L.append('  (label %s (at %s %s %d) (fields_autoplaced) (effects (font (size 1.27 1.27)) (justify %s bottom)) (uuid %s))'
                     % (q(net), f(wx), f(wy), lang, just, uid("lbl", c["ref"], num)))

    # textos de bloque
    notes = [
        (20.32, 30.48, "ALIMENTACION: Bateria 12V (3S) -> fusible 15A -> L298N + salidas a step-down 5V/5A y BEC 6V servos"),
        (170.18, 40.64, "RASPBERRY PI 5 (debajo de la PCB, header hembra 2x20)"),
        (304.8, 50.8, "ESP32-A: TRACCION (6 motores, 6 encoders canal A, MOTOR_EN)"),
        (431.8, 50.8, "ESP32-B: SERVOS (4 direccion + 3 brazo + 1 reserva), VBAT"),
        (170.18, 165.1, "UART Pi<->ESP32 (1k serie) y reset de ESP32 desde la Pi (Q1/Q2)"),
        (20.32, 220.98, "PUENTES H L298N (ENA/ENB = MOTOR_EN, quitar jumpers del modulo; pin +5V del modulo sin conectar)"),
        (20.32, 292.1, "CONECTORES DE MOTOR: bornera 2P + header 1x6 compatible con cable Pololu 37D"),
        (20.32, 378.46, "DIVISORES DE ENCODER 5V -> 3.3V (10k / 20k)"),
        (320.04, 378.46, "SERVOS (Power HD 1501MG) - rail SERVO_V 6V independiente"),
    ]
    for (x, y, t) in notes:
        L.append('  (text %s (at %s %s 0) (effects (font (size 2 2) (thickness 0.4) bold) (justify left bottom)) (uuid %s))'
                 % (q(t), f(x), f(y), uid("txt", t)))
    L.append('  (sheet_instances (path "/" (page "1")))')
    L.append(')')
    open(os.path.join(OUT, D.PROJECT + ".kicad_sch"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    # chequeo: toda red con >= 2 conexiones
    lonely = [n for n, k in used_nets.items() if k < 2]
    if lonely:
        raise RuntimeError("Redes con un solo pin: %s" % lonely)
    return used_nets


# ============================================================================
#  PROYECTO
# ============================================================================
def write_tables():
    open(os.path.join(OUT, "sym-lib-table"), "w").write(
        '(sym_lib_table\n  (lib (name "rover")(type "KiCad")(uri "${KIPRJMOD}/rover.kicad_sym")(options "")(descr "Rover Controller"))\n)\n')
    open(os.path.join(OUT, "fp-lib-table"), "w").write(
        '(fp_lib_table\n  (lib (name "rover")(type "KiCad")(uri "${KIPRJMOD}/rover.pretty")(options "")(descr "Rover Controller"))\n)\n')


def netclass_json(name, track, clr, vd, vdr):
    return {
        "bus_width": 12, "clearance": clr, "diff_pair_gap": 0.25, "diff_pair_via_gap": 0.25,
        "diff_pair_width": 0.2, "line_style": 0, "microvia_diameter": 0.3, "microvia_drill": 0.1,
        "name": name, "pcb_color": "rgba(0, 0, 0, 0.000)", "schematic_color": "rgba(0, 0, 0, 0.000)",
        "track_width": track, "via_diameter": vd, "via_drill": vdr, "wire_width": 6,
    }


def write_project(netnames):
    path = os.path.join(OUT, D.PROJECT + ".kicad_pro")
    classes = [netclass_json("Default", *D.DEFAULT_CLASS)]
    classes[0]["priority"] = 2147483647
    assignments = {}
    for (name, tw, clr, vd, vdr, pats) in D.NETCLASSES:
        classes.append(netclass_json(name, tw, clr, vd, vdr))
        for n in netnames:
            for p in pats:
                if re.fullmatch(p.replace("+", r"\+").replace("?", "."), n):
                    assignments[n] = name
    pro = {
        "board": {
            "design_settings": {
                "defaults": {"board_outline_line_width": 0.1, "copper_line_width": 0.2,
                             "copper_text_size_h": 1.5, "copper_text_size_v": 1.5,
                             "copper_text_thickness": 0.3, "silk_line_width": 0.15,
                             "silk_text_size_h": 1.0, "silk_text_size_v": 1.0,
                             "silk_text_thickness": 0.15},
                "rules": {"min_clearance": 0.2, "min_track_width": 0.2, "min_via_diameter": 0.6,
                          "min_through_hole_diameter": 0.3, "min_hole_to_hole": 0.25,
                          "min_copper_edge_clearance": 0.4, "min_hole_clearance": 0.25,
                          "min_silk_clearance": 0.0, "solder_mask_to_copper_clearance": 0.0,
                          "min_text_height": 0.5, "min_text_thickness": 0.08},
                "rule_severities": {"silk_over_copper": "ignore", "silk_overlap": "ignore",
                                    "silk_edge_clearance": "ignore", "text_height": "ignore",
                                    "text_thickness": "ignore", "lib_footprint_issues": "ignore",
                                    "lib_footprint_mismatch": "ignore"},
                "track_widths": [0.0, 0.3, 0.5, 1.0, 2.0, 3.0],
                "via_dimensions": [{"diameter": 0.0, "drill": 0.0}, {"diameter": 0.8, "drill": 0.4},
                                   {"diameter": 1.2, "drill": 0.6}, {"diameter": 1.6, "drill": 0.8}],
            },
        },
        "meta": {"filename": D.PROJECT + ".kicad_pro", "version": 1},
        "net_settings": {
            "classes": classes,
            "meta": {"version": 3},
            "net_colors": None,
            "netclass_assignments": assignments,
            "netclass_patterns": [],
        },
        "pcbnew": {"last_paths": {}, "page_layout_descr_file": ""},
        "schematic": {"legacy_lib_dir": "", "legacy_lib_list": []},
        "sheets": [[uid("root-sheet"), ""]],
        "text_variables": {},
    }
    json.dump(pro, open(path, "w"), indent=2)
    return assignments


# ============================================================================
#  PCB
# ============================================================================
def build_pcb(comps, netnames, assignments, route=False):
    import pcbnew
    from pcbnew import VECTOR2I, FromMM

    def P(x, y):
        return VECTOR2I(FromMM(x + OX), FromMM(y + OY))

    OX, OY = 30.0, 30.0
    pcb_path = os.path.join(OUT, D.PROJECT + ".kicad_pcb")
    board = pcbnew.BOARD()
    ds = board.GetDesignSettings()
    board.SetCopperLayerCount(2)

    # titulo
    tb = board.GetTitleBlock()
    tb.SetTitle(D.TITLE)
    tb.SetRevision(D.REVISION)
    tb.SetCompany("electronicarover")
    tb.SetDate("2026-11-17")

    netmap = {}
    for n in netnames:
        ni = pcbnew.NETINFO_ITEM(board, n)
        board.Add(ni)
        netmap[n] = ni

    # contorno con esquinas redondeadas
    W, H, R = D.BOARD_W, D.BOARD_H, 3.0
    segs = [((R, 0), (W - R, 0)), ((W, R), (W, H - R)), ((W - R, H), (R, H)), ((0, H - R), (0, R))]
    for (a, b) in segs:
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(P(*a))
        s.SetEnd(P(*b))
        s.SetLayer(pcbnew.Edge_Cuts)
        s.SetWidth(FromMM(0.1))
        board.Add(s)
    k = R - R / math.sqrt(2)
    arcs = [((0, R), (k, k), (R, 0)), ((W - R, 0), (W - k, k), (W, R)),
            ((W, H - R), (W - k, H - k), (W - R, H)), ((R, H), (k, H - k), (0, H - R))]
    for (a0, am, a1) in arcs:
        a = pcbnew.PCB_SHAPE(board)
        a.SetShape(pcbnew.SHAPE_T_ARC)
        a.SetArcGeometry(P(*a0), P(*am), P(*a1))
        a.SetLayer(pcbnew.Edge_Cuts)
        a.SetWidth(FromMM(0.1))
        board.Add(a)

    fps = {}
    for c in comps:
        lib, name = c["footprint"].split(":")
        libdir = os.path.join(OUT, "rover.pretty") if lib == "rover" else os.path.join(KICAD_FP_DIR, lib + ".pretty")
        fp = pcbnew.FootprintLoad(libdir, name)
        if fp is None:
            raise RuntimeError("footprint no encontrado " + c["footprint"])
        fp.SetFPID(pcbnew.LIB_ID(lib, name))
        fp.SetReference(c["ref"])
        fp.SetValue(c["value"])
        fp.SetPath(pcbnew.KIID_PATH("/" + c["sym_uuid"]))
        x, y, rot = c["pcb"]
        fp.SetPosition(P(x, y))
        fp.SetOrientationDegrees(rot)
        board.Add(fp)
        for pad in fp.Pads():
            num = pad.GetNumber()
            if num == "":
                continue
            key = int(num) if num.isdigit() else num
            net = c["pins"].get(key)
            if net:
                pad.SetNet(netmap[net])
        fp.Reference().SetTextSize(VECTOR2I(FromMM(1.0), FromMM(1.0)))
        fp.Reference().SetTextThickness(FromMM(0.15))
        fps[c["ref"]] = fp

    # textos de serigrafia
    def silk(text, x, y, size=1.2, layer=pcbnew.F_SilkS, rot=0, bold=False):
        t = pcbnew.PCB_TEXT(board)
        t.SetText(text)
        t.SetPosition(P(x, y))
        t.SetLayer(layer)
        t.SetTextSize(VECTOR2I(FromMM(size), FromMM(size)))
        t.SetTextThickness(FromMM(size * (0.2 if bold else 0.15)))
        t.SetTextAngleDegrees(rot)
        board.Add(t)

    silk("ROVER CONTROLLER v%s  -  RPi5 + 2xESP32 + 3xL298N  -  1 CAPA" % D.REVISION, 100, 21.0, 1.4, bold=True)
    for m in range(1, 7):
        c = next(cc for cc in comps if cc["ref"] == "J%d" % (10 + m))
        x = c["pcb"][0] - 2.54
        silk("M%d %s" % (m, D.MOTORS[m]), x, 11.6, 0.9)
        side = c.get("side", "A")
        silk("M-  M+" if side == "A" else "M+  M-", x, 1.4, 0.8)
        h = next(cc for cc in comps if cc["ref"] == "J%d" % (20 + m))
        if side == "A":
            silk("B A V G - +", h["pcb"][0] - 6.35, 18.7, 0.7)
        else:
            silk("+ - G V A B", h["pcb"][0] + 6.35, 18.7, 0.7)
    # polaridad / etiquetas (posiciones en funcion de rover_design)
    def at(ref):
        return next(cc for cc in comps if cc["ref"] == ref)["pcb"]
    silk("BAT", 13.0, 74.6, 1.0, bold=True)
    silk("-", 12.6, 78.0, 1.6, bold=True)
    silk("+", 12.6, 85.2, 1.6, bold=True)
    silk("XT60", 7.0, 91.8, 0.9)
    x, y, _ = at("J3")
    silk("- 12V>5V +", x + 2.54, y + 5.4, 0.8)
    x, y, _ = at("J4")
    silk("+ 12V>BEC -", x + 2.54, y + 5.4, 0.8)
    x, y, _ = at("J6")
    silk("V+  SERVO 6V  -", x - 2.54, y - 5.4, 0.8)
    x, y, _ = at("J5")
    silk("+ 5V/5A IN -", x - 5.2, y - 2.54, 0.8, rot=90)
    x, y, _ = at("J31")
    silk("SIG V+ GND", x - 2.54, y - 2.4, 0.7)
    for n in range(1, 9):
        x, y, _ = at("J%d" % (30 + n))
        silk("S%d" % n, x + 2.4, y, 0.8)
    x, y, _ = at("U2")
    silk("ESP32-A TRACCION (antena izq, USB der)", x, y - 15.6, 1.0, bold=True)
    x, y, _ = at("U3")
    silk("ESP32-B SERVOS", x, y - 28.6, 1.0, bold=True)
    silk("ENCODERS 5V->3V3", 98.0, 125.6, 0.8)

    # zonas de GND en ambas caras
    def zone(layer, netname, pts, prio=0, clearance=0.4):
        z = pcbnew.ZONE(board)
        z.SetLayer(layer)
        z.SetNet(netmap[netname])
        ol = z.Outline()
        ol.NewOutline()
        for (x, y) in pts:
            ol.Append(FromMM(x + OX), FromMM(y + OY))
        z.SetLocalClearance(FromMM(clearance))
        z.SetMinThickness(FromMM(0.3))
        z.SetThermalReliefGap(FromMM(0.5))
        z.SetThermalReliefSpokeWidth(FromMM(0.8))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
        z.SetAssignedPriority(prio)
        board.Add(z)
        return z

    rect = [(0.5, 0.5), (W - 0.5, 0.5), (W - 0.5, H - 0.5), (0.5, H - 0.5)]
    # una sola capa de cobre: plano de GND solo en B.Cu (cara de soldadura)
    zone(pcbnew.B_Cu, "GND", rect, clearance=0.5)

    # keepout de cobre bajo las antenas de los ESP32
    for ref in ("U2", "U3"):
        x, y, _ = next(cc for cc in comps if cc["ref"] == ref)["pcb"]
        ax0, ay0, ax1, ay1 = D.ESP32["antenna_keepout"]
        z = pcbnew.ZONE(board)
        z.SetIsRuleArea(True)
        z.SetDoNotAllowCopperPour(True)
        # sin plano de cobre bajo la antena; se permiten pistas finas
        z.SetDoNotAllowTracks(False)
        z.SetDoNotAllowVias(True)
        z.SetDoNotAllowPads(False)
        z.SetDoNotAllowFootprints(False)
        ls = pcbnew.LSET()
        ls.AddLayer(pcbnew.F_Cu)
        ls.AddLayer(pcbnew.B_Cu)
        z.SetLayerSet(ls)
        ol = z.Outline()
        ol.NewOutline()
        for (px, py) in [(ax0, ay0), (ax1, ay0), (ax1, ay1), (ax0, ay1)]:
            ol.Append(FromMM(x + px + OX), FromMM(y + py + OY))
        z.SetZoneName("ANTENA_" + ref)
        board.Add(z)

    pcbnew.SaveBoard(pcb_path, board)
    return pcb_path


# ============================================================================
#  RUTEO DE UNA CAPA
# ============================================================================
def route_board(relaxed_pass=True):
    import pcbnew
    import router1l
    pcb_path = os.path.join(OUT, D.PROJECT + ".kicad_pcb")
    board = pcbnew.LoadBoard(pcb_path)
    for t in list(board.GetTracks()):
        board.Remove(t)
    nets_by_name = board.GetNetsByName()
    for (net, pts, w) in D.preroutes():
        for a, c in zip(pts, pts[1:]):
            t = pcbnew.PCB_TRACK(board)
            t.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(a[0] + 30.0), pcbnew.FromMM(a[1] + 30.0)))
            t.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(c[0] + 30.0), pcbnew.FromMM(c[1] + 30.0)))
            t.SetWidth(pcbnew.FromMM(w))
            t.SetLayer(pcbnew.B_Cu)
            t.SetNet(nets_by_name[net])
            board.Add(t)
    classes = {"Default": D.DEFAULT_CLASS[:2]}
    assignments = {}
    for (name, tw, clr, vd, vdr, pats) in D.NETCLASSES:
        classes[name] = (tw, clr)
    # clases a partir de rover_design (no depender del .kicad_pro cacheado)
    assignments = write_project(D.nets())
    ox, oy = 30.0, 30.0
    reserved = [(x0 + ox, y0 + oy, x1 + ox, y1 + oy, a) for (x0, y0, x1, y1, a) in D.routing_reserved()]
    r = router1l.route(board, classes, assignments, relaxed_pass=relaxed_pass,
                       reserved=reserved, early_refs=D.ROUTING_EARLY, late=D.ROUTING_LATE,
                       first=D.ROUTING_FIRST)
    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())
    pcbnew.SaveBoard(pcb_path, board)
    write_project(D.nets())
    # lista de puentes de alambre
    with open(os.path.join(OUT, "puentes_alambre.csv"), "w") as fh:
        fh.write("Puente;Red;X1(mm);Y1(mm);X2(mm);Y2(mm);Largo(mm)\n")
        for k, (n, xa, ya, xb, yb, L) in enumerate(r.jumpers, 1):
            fh.write("W%d;%s;%.2f;%.2f;%.2f;%.2f;%.1f\n" % (k, n, xa - 30, ya - 30, xb - 30, yb - 30, L))
    print("Puentes de alambre: %d   Fallidas: %d" % (len(r.jumpers), len(r.failed)))
    for f_ in r.failed:
        print("  FALLO", f_)
    return r


def write_bom(comps):
    groups = {}
    for c in comps:
        key = (c["value"], c["footprint"], c.get("mpn", c["value"]))
        groups.setdefault(key, []).append(c)
    rows = ["Cant;Referencias;Valor;Footprint;Parte sugerida;Descripcion"]
    for (val, fp, mpn), cs in sorted(groups.items(), key=lambda kv: kv[1][0]["ref"]):
        refs = ",".join(sorted((c["ref"] for c in cs), key=lambda r: (r.rstrip("0123456789"), int(re.sub(r"\D", "", r) or 0))))
        rows.append("%d;%s;%s;%s;%s;%s" % (len(cs), refs, val, fp, mpn, cs[0].get("desc", "")))
    open(os.path.join(OUT, "bom.csv"), "w", encoding="utf-8").write("\n".join(rows) + "\n")


def main():
    route = "--route" in sys.argv
    os.makedirs(os.path.join(OUT, "rover.pretty"), exist_ok=True)
    comps = D.build()
    syms = custom_symbols()
    write_symbol_lib(syms)
    for name, txt in (("L298N_Module_Pins", footprint_l298n()),
                      ("ESP32_DevKitV1_30P_DualPitch", footprint_esp32()),
                      ("RPi5_HAT_Header_2x20", footprint_rpi()),
                      ("Servo_Header_1x03", footprint_servo())):
        open(os.path.join(OUT, "rover.pretty", name + ".kicad_mod"), "w").write(txt + "\n")
    write_tables()
    used = write_schematic(comps, syms)
    write_bom(comps)
    netnames = D.nets()
    print("Componentes: %d  Redes: %d" % (len(comps), len(netnames)))
    build_pcb(comps, netnames, None, route)
    # SaveBoard sobrescribe el .kicad_pro: escribir el nuestro despues
    write_project(netnames)
    if route:
        route_board()
    print("OK ->", OUT)


if __name__ == "__main__":
    main()
