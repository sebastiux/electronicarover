# -*- coding: utf-8 -*-
"""
Tarjeta de TRACCION (una sola cara): ESP32-A, bornas de los 3 L298N, encoders.

- 3 bornas de 6 vias (paso 3.5 mm) en la orilla izquierda: EN, IN4, IN3, IN2, IN1, GND.
  En cada modulo L298N se quitan los jumpers de ENA/ENB y los 2 pines se unen al hilo EN.
- 2 bornas de 5 vias para los encoders (orilla inferior) y sus divisores 10k/20k + 1 nF.
- J9 "PI": GND, TXD2 y RXD2 de la Raspberry (desde su HAT de bornas), con R13/R14 de 1k.
- J5: 5 V del step-down (ESP32-A por D5 y encoders).
Geometria heredada de la Cubiko de 2 caras (misma ESP32, bornas y divisores).

Uso: ROVER_VARIANT=traccion python3 generate.py --route
"""
from rover_design import (ESP32_LEFT, ESP32_RIGHT, MOTORS,  # noqa: F401
                          ESPA_IN, ESPA_ENC, ESPA_UART_RX, ESPA_UART_TX, ESPA_MOTOR_EN,
                          COMPONENTS, FP_R, FP_C25, FP_CP10, FP_LED, FP_DO41, FP_MH,
                          add, esp_pin_number, pad_side)
from rover_split_comun import *  # noqa: F401,F403
from rover_split_comun import FP_TB6, FP_TB5, FP_TB3, FP_TB2, MPN_TB2

PROJECT = "rover_traccion"
REVISION = "2.0-T"
TITLE = "Rover - tarjeta de TRACCION (ESP32-A, 3x L298N, encoders)"

BOARD_W = 92.0
BOARD_H = 96.0

ESPA_POS = (34.7, 49.5, 180)          # vertical, USB arriba: fila IO23.. mira a las bornas
TB_X = 5.5
TB_Y = {"U6": 15.75, "U5": 43.25, "U4": 70.75}   # pad 1 (EN) de cada borna
TB_ORDER = ["EN", "IN4", "IN3", "IN2", "IN1", "GND"]   # de arriba a abajo
EN_X = 2.3                            # bus de EN por la orilla izquierda (planar)
ENC_TB_Y = BOARD_H - 5.0
ENC_TB = [("J7", 50.0, (1, 2, 3)), ("J8", 22.0, (6, 5, 4))]
DIV_C = 6.4
DIVIDERS = {
    6: (40.0, 41.3, "L", 45.55, 46.4, 26.45, 80.4),
    5: (49.0, 41.3, "L", 44.35, 55.4, 27.65, 79.2),
    4: (58.0, 41.3, "L", 43.15, 58.0, 28.85, 78.0),
    3: (58.0, 56.0, "R", 51.65, 61.6, 68.4, 87.0),
    2: (67.0, 56.0, "R", 50.45, 67.0, 67.2, 85.8),
    1: (76.0, 56.0, "R", 49.25, 76.0, 66.0, 84.6),
}
PI_TB = (BOARD_W - 5.5, 34.0, 90)    # J9 en la orilla derecha (pad 1 abajo)
CHASSIS_HOLES = [(3.5, 8.5), (BOARD_W - 3.5, 4.0), (13.5, 92.0), (BOARD_W - 3.5, 92.0)]
ALIGN_HOLES = []


def espa_left_y(name):
    return ESPA_POS[1] + 17.78 - 2.54 * ESP32_LEFT.index(name)


def preroutes():
    out = []
    ex = ESPA_POS[0] - 12.7
    lanes = {"U6": {4: 19.2, 3: 18.0, 2: 16.8, 1: 15.6},
             "U5": {1: 14.4, 2: 13.2, 3: 12.0, 4: None},
             "U4": {4: 15.6, 3: 16.8, 2: 18.0, 1: 19.2}}
    for k, ref in enumerate(("U4", "U5", "U6")):
        for j in range(1, 5):
            yt = TB_Y[ref] + 3.5 * TB_ORDER.index("IN%d" % j)
            yi = ESPA_POS[1] + 17.78 - 2.54 * ESP32_RIGHT.index(ESPA_IN[k][j - 1])
            xl = lanes[ref][j]
            pts = [(TB_X, yt), (xl, yt), (xl, yi), (ex, yi)] if xl else [(TB_X, yt), (ex - 1.6, yt), (ex, yi)]
            out.append(("%s_IN%d" % (ref, j), pts, 0.7))
    # EN de las 3 bornas: bus por la orilla, a la izquierda de los pads
    ys = sorted(TB_Y.values())
    out.append(("MOTOR_EN", [(TB_X, ys[0]), (EN_X, ys[0]), (EN_X, ys[-1]), (TB_X, ys[-1])], 0.7))
    out.append(("MOTOR_EN", [(EN_X, ys[1]), (TB_X, ys[1])], 0.7))
    # divisores de encoder (igual que la Cubiko)
    ex_l = ESPA_POS[0] + 12.7
    for m, (y, xn, side, lane, yl, xch, yb) in DIVIDERS.items():
        yp = espa_left_y(ESPA_ENC[m])
        d = -1 if side == "L" else 1
        out.append(("ENC%d_A" % m, [(ex_l, yp), (lane, yp), (lane, yl), (xn, yl)], 0.7))
        out.append(("ENC%d_A" % m, [(xn, y), (xn, y + 3.6), (xn, y + DIV_C)], 0.7))
        xg, xv, xa = xn + d * 2.5, xn + d * 5.0, xn + d * 7.62
        xt = enc_pin_x(m)
        out.append(("ENC%d_A5V" % m, [(xa, y), (xch, y), (xch, yb), (xt, yb), (xt, ENC_TB_Y)], 0.7))
    return out


def enc_pin_x(m):
    for ref, x, ms in ENC_TB:
        if m in ms:
            return x + 3.5 * (2 + ms.index(m))
    raise KeyError(m)


ROUTING_FIRST = ["U%d_IN%d" % (u, i) for u in (6, 5, 4) for i in (4, 3, 2, 1)] + \
    ["MOTOR_EN", "ESPA_RX", "ESPA_TX", "PI_TXD2", "PI_RXD2"] + \
    ["ENC%d_A" % m for m in range(1, 7)] + ["ENC%d_A5V" % m for m in range(1, 7)]
ROUTING_EARLY = {"GND": set(), "+5V": {"J5", "C2"}}


def external_nodes():
    """Cableado fuera de la tarjeta para la simulacion del firmware: bornas -> L298N
    (EN a ENA y ENB con cable en Y), salidas -> motores, cables Pololu -> encoders, y la
    Raspberry Pi (header virtual U1) por su HAT de bornas -> J9."""
    l298_pin = {"IN1": "9", "IN2": "10", "IN3": "11", "IN4": "12", "GND": "6"}
    out = []
    by_ref = {c["ref"]: c for c in COMPONENTS}
    for k, ref in enumerate(("U4", "U5", "U6")):
        tb = by_ref["J%d" % (41 + k)]
        for i, name in enumerate(TB_ORDER):
            if name == "EN":
                out += [(ref, "8", tb["pins"][i + 1]), (ref, "13", tb["pins"][i + 1])]
            else:
                out.append((ref, l298_pin[name], tb["pins"][i + 1]))
        ma, mb = 2 * k + 1, 2 * k + 2
        out += [(ref, "1", "EXT_M%d_A" % ma), (ref, "2", "EXT_M%d_B" % ma),
                (ref, "3", "EXT_M%d_A" % mb), (ref, "4", "EXT_M%d_B" % mb)]
    for m in range(1, 7):
        j = "J%d" % (20 + m)
        out += [(j, "1", "EXT_M%d_A" % m), (j, "2", "EXT_M%d_B" % m), (j, "3", "GND"), (j, "4", "+5V"),
                (j, "5", "ENC%d_A5V" % m)]
    out += [("U1", "7", "PI_TXD2"), ("U1", "29", "PI_RXD2"), ("U1", "6", "GND")]
    return out


_sch = [0]


def _sch_pos():
    i = _sch[0]
    _sch[0] += 1
    return (25.4 + 76.2 * (i % 10), 38.1 + 76.2 * (i // 10))


def build():
    COMPONENTS.clear()
    _sch[0] = 0
    espa = {i: None for i in range(1, 31)}
    espa[esp_pin_number("VIN")] = "VIN_A"
    espa[14] = espa[29] = "GND"
    for k, gp in ESPA_IN.items():
        for j, g in enumerate(gp):
            espa[esp_pin_number(g)] = "U%d_IN%d" % (k + 4, j + 1)
    for m, g in ESPA_ENC.items():
        espa[esp_pin_number(g)] = "ENC%d_A" % m
    espa[esp_pin_number(ESPA_MOTOR_EN)] = "MOTOR_EN"
    espa[esp_pin_number(ESPA_UART_TX)] = "ESPA_TX"
    espa[esp_pin_number(ESPA_UART_RX)] = "ESPA_RX"
    add("U2", "ESP32-A_Traccion", "rover:ESP32_DevKitV1_30P", "rover:ESP32_DevKitV1_30P_DualPitch",
        espa, ESPA_POS, _sch_pos(), desc="ESP32 DevKit V1 30 pines sobre 2x header hembra 1x15",
        mpn="ESP32 DevKit V1 + 2x header hembra 1x15")

    for k, ref in enumerate(("U4", "U5", "U6")):
        sig = {"EN": "MOTOR_EN", "GND": "GND"}
        for j in range(1, 5):
            sig["IN%d" % j] = "%s_IN%d" % (ref, j)
        pins = {i + 1: sig[name] for i, name in enumerate(TB_ORDER)}
        ma, mb = 2 * k + 1, 2 * k + 2
        add("J%d" % (41 + k), "L298N #%d (M%d/M%d)" % (k + 1, ma, mb), "Connector:Screw_Terminal_01x06", FP_TB6,
            pins, (TB_X, TB_Y[ref], 270), _sch_pos(),
            desc="Borna 6 vias paso 3.5 mm hacia el L298N #%d (%s / %s): EN IN4 IN3 IN2 IN1 GND"
                 % (k + 1, MOTORS[ma], MOTORS[mb]),
            mpn="Phoenix PT 1,5/6-3,5-H o KF350 3.5mm (3+3)")

    for ref, x, ms in ENC_TB:
        pins = {1: "GND", 2: "+5V"}
        for i, m in enumerate(ms):
            pins[3 + i] = "ENC%d_A5V" % m
        add(ref, "ENC M%d M%d M%d" % tuple(ms), "Connector:Screw_Terminal_01x05", FP_TB5,
            pins, (x, ENC_TB_Y, 0), _sch_pos(),
            desc="Borna 5 vias paso 3.5 mm: GND, +5V y canal A de los motores %s (cable Pololu: "
                 "verde GND, azul VCC, amarillo A)" % ", ".join("M%d" % m for m in ms),
            mpn="Phoenix PT 1,5/5-3,5-H o KF350 3.5mm (3+2)")

    for m, (y, xn, side, lane, yl, xch, yb) in DIVIDERS.items():
        if side == "L":
            r10, r20, cc = (xn - 7.62, y, 0), (xn, y + 3.6, 180), (xn, y + DIV_C, 180)
        else:
            r10, r20, cc = (xn + 7.62, y, 180), (xn, y + 3.6, 0), (xn, y + DIV_C, 0)
        add("R%d" % m, "10k", "Device:R", FP_R, {1: "ENC%d_A5V" % m, 2: "ENC%d_A" % m},
            r10, _sch_pos(), desc="Divisor encoder M%d (serie)" % m)
        add("R%d" % (m + 6), "20k", "Device:R", FP_R, {1: "ENC%d_A" % m, 2: "GND"},
            r20, _sch_pos(), desc="Divisor encoder M%d (a GND)" % m)
        add("C%d" % (10 + m), "1nF", "Device:C", FP_C25, {1: "ENC%d_A" % m, 2: "GND"},
            cc, _sch_pos(), desc="Filtro de ruido encoder M%d" % m)

    add("J5", "5V IN (buck 5V)", "Connector:Screw_Terminal_01x02", FP_TB2,
        {1: "+5V", 2: "GND"}, (64.0, 5.6, 180), _sch_pos(),
        desc="Entrada 5 V desde el step-down (ESP32-A y encoders)", mpn=MPN_TB2)
    add("C2", "1000uF 10V", "Device:C_Polarized", FP_CP10, {1: "+5V", 2: "GND"},
        (75.0, 17.0, 0), _sch_pos(), desc="Bulk 5V")
    add("R25", "330", "Device:R", FP_R, {1: "+5V", 2: "LED5_A"}, (52.0, 19.2, 0),
        _sch_pos(), desc="Resistencia LED 5V")
    add("D3", "LED verde 5V", "Device:LED", FP_LED, {1: "GND", 2: "LED5_A"},
        (69.04, 21.2, 180), _sch_pos(), desc="Indicador 5V")
    add("R21", "10k", "Device:R", FP_R, {1: "MOTOR_EN", 2: "GND"}, (52.0, 23.2, 0),
        _sch_pos(), desc="Pull-down MOTOR_EN (motores apagados durante el arranque)")
    add("D5", "1N5819", "Device:D_Schottky", FP_DO41, {1: "VIN_A", 2: "+5V"},
        (52.0, 27.2, 0), _sch_pos(), desc="Schottky +5V -> VIN ESP32-A", mpn="1N5819 DO-41")

    add("J9", "PI (UART2)", "Connector:Screw_Terminal_01x03", FP_TB3,
        {1: "GND", 2: "PI_TXD2", 3: "PI_RXD2"}, PI_TB, _sch_pos(),
        desc="Hacia el HAT de bornas de la Pi: 1 GND (pin 6), 2 TXD2 = GPIO4 (pin 7), 3 RXD2 = GPIO5 (pin 29)",
        mpn="Phoenix PT 1,5/3-3,5-H o KF350-3P 3.5mm")
    add("R13", "1k", "Device:R", FP_R, {1: "PI_TXD2", 2: "ESPA_RX"}, (66.0, 30.0, 0),
        _sch_pos(), desc="Serie UART Pi TXD2 -> ESP32-A RX")
    add("R14", "1k", "Device:R", FP_R, {1: "ESPA_TX", 2: "PI_RXD2"}, (66.0, 34.0, 0),
        _sch_pos(), desc="Serie UART ESP32-A TX -> Pi RXD2")

    for i, (x, y) in enumerate(CHASSIS_HOLES):
        add("H%d" % (i + 1), "M3", "Mechanical:MountingHole", FP_MH, {}, (x, y, 0), _sch_pos(),
            desc="Agujero de montaje M3")
    return COMPONENTS


def pcb_labels(silk, at, comps):
    silk("ROVER TRACCION v%s" % REVISION, 40.0, 9.8, 1.2, bold=True)
    for k, ref in enumerate(("U4", "U5", "U6")):
        x, y, _ = at("J%d" % (41 + k))
        silk("L298N #%d  M%d/M%d" % (k + 1, 2 * k + 1, 2 * k + 2), x + 5.6, y - 2.4, 0.8)
        for i, name in enumerate(TB_ORDER):
            silk(name, x + 6.6, y + 3.5 * i, 0.7)
    for ref, x, ms in ENC_TB:
        silk("ENC M%d M%d M%d" % tuple(ms), x + 7.0, ENC_TB_Y - 4.6, 0.8)
        silk("G 5V A%d A%d A%d" % tuple(ms), x + 7.0, ENC_TB_Y - 2.9, 0.65)
    x, y, _ = at("J5")
    silk("5V IN: + -", x - 2.54, y + 6.4, 0.8)
    x, y, _ = at("J9")
    silk("PI: GND TX RX", x - 7.4, y - 3.5, 0.8, rot=90)
    x, y, _ = at("U2")
    silk("ESP32-A (USB arriba)", x, y + 29.0, 0.9, bold=True)
