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
from rover_split_comun import FP_ESP32, FP_TB6, FP_TB5, FP_TB3, FP_TB2, MPN_TB2
FP_RV = "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P2.54mm_Vertical"

PROJECT = "rover_traccion"
REVISION = "2.0-T"
TITLE = "Rover - tarjeta de TRACCION (ESP32-A, 3x L298N, encoders)"

BOARD_W = 95.0
BOARD_H = 96.0

ESPA_POS = (37.7, 49.5, 180)          # vertical, USB arriba: fila IO23.. mira a las bornas
TB_X = 5.5
TB_Y = {"U6": 15.75, "U5": 43.25, "U4": 70.75}   # pad 1 (EN) de cada borna
TB_ORDER = ["EN", "IN4", "IN3", "IN2", "IN1", "GND"]   # de arriba a abajo
EN_X = 2.3                            # bus de EN por la orilla izquierda (planar)
ENC_TB_Y = BOARD_H - 5.0
ENC_TB = [("J7", 58.0, (1, 2, 3)), ("J8", 24.0, (6, 5, 4))]
# orden de pines de cada borna de encoders (izquierda -> derecha). J7 recibe el +5V por la
# derecha (A1 A2 A3 5V G) para que el +5V no cruce los canales A; J8 queda G 5V A6 A5 A4.
ENC_ORDEN = {"J7": ("A", "A", "A", "+5V", "GND"), "J8": ("GND", "+5V", "A", "A", "A")}
# Divisores 10k/20k + 1 nF: bloques R10k / R20k / C apilados (filas a DIV_DY mm), 13 mm entre
# bloques. M3..M1 a la derecha de la ESP32-A (DIVIDERS). M6..M4 en fila DEBAJO del modulo,
# junto a J8, con resistencias de pie (DIV_ABAJO): el plano de GND de cada bloque sale entre
# los pines de J8 a la franja de la orilla (bajo el modulo quedaba encerrado).
DIV_ABAJO = {6: 31.0, 5: 39.4, 4: 47.8}     # x del nodo de cada bloque
DIV_ABAJO_Y = 79.0                          # y del nodo (debajo del modulo)
#   (y de la fila R10k, x de la columna de nodos, lado, carril al pin, y de aterrizaje,
#    x del canal de la senal de 5 V, y de su carril inferior)
DIV_DY = 3.6
DIV_C = 2 * DIV_DY
DIVIDERS = {
    3: (47.1, 60.0, "R", 53.0, 47.1 + DIV_DY, 74.4, 81.7),
    2: (57.5, 60.0, "R", 55.0, 57.5, 72.4, 79.7),
    1: (67.9, 60.0, "R", 57.0, 67.9 + DIV_DY, 70.4, 77.7),
}
PI_TB = (BOARD_W - 5.5, 34.0, 90)    # J9 en la orilla derecha (pad 1 abajo)
CHASSIS_HOLES = [(3.5, 8.5), (86.0, 15.0), (13.5, 92.0), (BOARD_W - 3.5, 92.0)]
ALIGN_HOLES = []


def routing_reserved():
    """La orilla derecha queda para senales y GND: si el +5V baja por ahi a los encoders,
    encierra la borna PI (J9). Ese tramo se resuelve con un cable por arriba."""
    return [(BOARD_W - 13.0, 22.0, BOARD_W, BOARD_H, {"Default", "GND"}),
            # franja sobre la ESP32: solo GND y +5V (una senal ahi separaria el GND de abajo del modulo)
            (8.0, 8.0, 49.0, 27.0, {"GND", "PWR"}),
            # franja bajo las bornas de encoders: solo GND (es la salida del plano de los divisores)
            (14.0, ENC_TB_Y + 1.3, BOARD_W - 13.0, BOARD_H, {"GND"})]


def espa_left_y(name):
    return ESPA_POS[1] + 17.78 - 2.54 * ESP32_LEFT.index(name)


def preroutes():
    out = []
    ex = ESPA_POS[0] - 12.7
    lanes = {"U6": {4: 22.4, 3: 20.4, 2: 18.4, 1: 16.4},      # carriles a 2.0 mm (pista 1.0 + fresa 1.0)
             "U5": {1: 14.4, 2: 12.4, 3: 10.4, 4: None},
             "U4": {4: 16.4, 3: 18.4, 2: 20.4, 1: 22.4}}
    for k, ref in enumerate(("U4", "U5", "U6")):
        for j in range(1, 5):
            yt = TB_Y[ref] + 3.5 * TB_ORDER.index("IN%d" % j)
            yi = ESPA_POS[1] + 17.78 - 2.54 * ESP32_RIGHT.index(ESPA_IN[k][j - 1])
            xl = lanes[ref][j]
            pts = [(TB_X, yt), (xl, yt), (xl, yi), (ex, yi)] if xl else [(TB_X, yt), (ex - 1.6, yt), (ex, yi)]
            out.append(("%s_IN%d" % (ref, j), pts, 1.0))
    # EN de las 3 bornas: bus por la orilla, a la izquierda de los pads
    ys = sorted(TB_Y.values())
    out.append(("MOTOR_EN", [(TB_X, ys[0]), (EN_X, ys[0]), (EN_X, ys[-1]), (TB_X, ys[-1])], 1.0))
    out.append(("MOTOR_EN", [(EN_X, ys[1]), (TB_X, ys[1])], 1.0))
    # +5V junto a J5: J5 -> C2, J5 -> R25 -> anodo de D5 (caminos fijos, sin encerrar GND)
    out.append(("+5V", [(60.0, 5.6), (69.0, 5.6), (69.0, 8.0)], 1.5))
    out.append(("+5V", [(60.0, 5.6), (60.0, 10.0), (57.0, 13.0), (57.0, 15.0)], 1.5))
    out.append(("+5V", [(57.0, 15.0), (57.0, 21.0), (65.16, 21.0), (65.16, 27.2)], 1.5))
    # +5V a J7 pin 2: cable por arriba desde la pista de +5V que baja a J8 (x 24)
    # (el alambre va por arriba de los divisores, sin pasar sobre ningun pad)
    # J5 -> por la orilla de arriba y la derecha (por fuera de J9) -> pin +5V de J7
    out.append(("+5V", [(60.0, 5.6), (60.0, 2.4), (BOARD_W - 2.5, 2.4), (BOARD_W - 2.5, 86.0),
                        (enc_pin_tb("J7", "+5V"), 86.0), (enc_pin_tb("J7", "+5V"), ENC_TB_Y)], 1.5))
    # UART y MOTOR_EN hacia sus resistencias, en el mismo orden que los pines (sin cruces)
    xl = ESPA_POS[0] + 12.7
    out.append(("ESPA_RX", [(xl, espa_left_y("IO14")), (65.5, espa_left_y("IO14")), (65.5, 30.0), (69.0, 30.0)], 1.0))
    out.append(("ESPA_TX", [(xl, espa_left_y("IO27")), (67.6, espa_left_y("IO27")), (67.6, 34.0), (69.0, 34.0)], 1.0))
    out.append(("MOTOR_EN", [(xl, espa_left_y("IO13")), (53.0, espa_left_y("IO13")), (55.0, 34.8), (55.0, 33.0)], 1.0))
    # divisores de encoder (igual que la Cubiko)
    ex_l = ESPA_POS[0] + 12.7
    for m, (y, xn, side, lane, yl, xch, yb) in DIVIDERS.items():
        yp = espa_left_y(ESPA_ENC[m])
        d = -1 if side == "L" else 1
        out.append(("ENC%d_A" % m, [(ex_l, yp), (lane, yp), (lane, yl), (xn, yl)], 1.0))
        out.append(("ENC%d_A" % m, [(xn, y), (xn, y + DIV_DY), (xn, y + DIV_C)], 1.0))
        xa = xn - 2.54 if side == "L" else xn + 7.62
        xt = enc_pin_x(m)
        out.append(("ENC%d_A5V" % m, [(xa, y), (xch, y), (xch, yb), (xt, yb), (xt, ENC_TB_Y)], 1.0))
    # M6..M4: carril bajo el modulo -> nodo; nodo -> R20k y C; R10k (de pie) -> J8
    yb0 = DIV_ABAJO_Y
    for m, x in DIV_ABAJO.items():
        yp = espa_left_y(ESPA_ENC[m])
        out.append(("ENC%d_A" % m, [(ex_l, yp), (x, yp), (x, yb0)], 1.0))
        out.append(("ENC%d_A" % m, [(x, yb0), (x + 3.0, yb0), (x + 3.0, yb0 - 3.4)], 1.0))
        xt = enc_pin_x(m)
        yv = {6: 86.5, 5: 86.0, 4: 87.5}[m]      # cada bloque da vuelta a su altura (sin tocarse)
        out.append(("ENC%d_A5V" % m, [(x, yb0 + 2.54), (x, yv), (xt, yv + 1.5), (xt, ENC_TB_Y)], 1.0))
    return out


def enc_pins(ref, ms):
    """pin -> red de una borna de encoders segun ENC_ORDEN."""
    out, k = {}, 0
    for i, t in enumerate(ENC_ORDEN[ref]):
        if t == "A":
            out[i + 1] = "ENC%d_A5V" % ms[k]
            k += 1
        else:
            out[i + 1] = t
    return out


def enc_pin_tb(ref, net):
    x, ms = next((x, ms) for r, x, ms in ENC_TB if r == ref)
    return x + 3.5 * (next(p for p, n in enc_pins(ref, ms).items() if n == net) - 1)


def enc_pin_x(m):
    for ref, x, ms in ENC_TB:
        if m in ms:
            pin = next(p for p, n in enc_pins(ref, ms).items() if n == "ENC%d_A5V" % m)
            return x + 3.5 * (pin - 1)
    raise KeyError(m)


ROUTING_FIRST = ["U%d_IN%d" % (u, i) for u in (6, 5, 4) for i in (4, 3, 2, 1)] + \
    ["ESPA_RX", "ESPA_TX", "PI_TXD2", "PI_RXD2"] + \
    ["ENC%d_A" % m for m in range(1, 7)] + ["ENC%d_A5V" % m for m in range(1, 7)]
ROUTING_EARLY = {"GND": set(), "+5V": {"J5", "C2"}}
# MOTOR_EN al final: su camino al bus de EN cruzaria la zona de arriba y aislaria GND
ROUTING_LATE = ["MOTOR_EN"]



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
    add("U2", "ESP32-A_Traccion", "rover:ESP32_DevKitV1_30P", FP_ESP32,
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

    for m, x in DIV_ABAJO.items():
        y0 = DIV_ABAJO_Y
        add("R%d" % m, "10k", "Device:R", FP_RV, {1: "ENC%d_A5V" % m, 2: "ENC%d_A" % m},
            (x, y0 + 2.54, 90), _sch_pos(), desc="Divisor encoder M%d (serie)" % m)
        add("R%d" % (m + 6), "20k", "Device:R", FP_RV, {1: "ENC%d_A" % m, 2: "GND"},
            (x + 3.0, y0, 0), _sch_pos(), desc="Divisor encoder M%d (a GND)" % m)
        add("C%d" % (10 + m), "1nF", "Device:C", FP_C25, {1: "ENC%d_A" % m, 2: "GND"},
            (x + 3.0, y0 - 3.4, 0), _sch_pos(), desc="Filtro de ruido encoder M%d" % m)

    for ref, x, ms in ENC_TB:
        pins = enc_pins(ref, ms)
        orden = " ".join(pins[i] if pins[i] in ("GND", "+5V") else "A" + pins[i][3] for i in range(1, 6))
        add(ref, "ENC M%d M%d M%d" % tuple(ms), "Connector:Screw_Terminal_01x05", FP_TB5,
            pins, (x, ENC_TB_Y, 0), _sch_pos(),
            desc="Borna 5 vias paso 3.5 mm: %s (cable Pololu: verde GND, azul VCC, amarillo A)" % orden,
            mpn="Phoenix PT 1,5/5-3,5-H o KF350 3.5mm (3+2)")

    for m, (y, xn, side, lane, yl, xch, yb) in DIVIDERS.items():
        if side == "L":
            fr = FP_RV
            r10, r20, cc = (xn - 2.54, y, 0), (xn, y + DIV_DY, 180), (xn, y + DIV_C, 180)
        else:
            fr = FP_R
            r10, r20, cc = (xn + 7.62, y, 180), (xn, y + DIV_DY, 0), (xn, y + DIV_C, 0)
        add("R%d" % m, "10k", "Device:R", fr, {1: "ENC%d_A5V" % m, 2: "ENC%d_A" % m},
            r10, _sch_pos(), desc="Divisor encoder M%d (serie)" % m)
        add("R%d" % (m + 6), "20k", "Device:R", fr, {1: "ENC%d_A" % m, 2: "GND"},
            r20, _sch_pos(), desc="Divisor encoder M%d (a GND)" % m)
        add("C%d" % (10 + m), "1nF", "Device:C", FP_C25, {1: "ENC%d_A" % m, 2: "GND"},
            cc, _sch_pos(), desc="Filtro de ruido encoder M%d" % m)

    add("J5", "5V IN (buck 5V)", "Connector:Screw_Terminal_01x02", FP_TB2,
        {1: "+5V", 2: "GND"}, (60.0, 5.6, 180), _sch_pos(),
        desc="Entrada 5 V desde el step-down (ESP32-A y encoders)", mpn=MPN_TB2)
    add("C2", "1000uF 10V", "Device:C_Polarized", FP_CP10, {1: "+5V", 2: "GND"},
        (69.0, 8.0, 0), _sch_pos(), desc="Bulk 5V")
    add("R25", "330", "Device:R", FP_R, {1: "+5V", 2: "LED5_A"}, (57.0, 15.0, 0),
        _sch_pos(), desc="Resistencia LED 5V")
    add("D3", "LED verde 5V", "Device:LED", FP_LED, {1: "GND", 2: "LED5_A"},
        (75.0, 17.0, 180), _sch_pos(), desc="Indicador 5V")
    add("R21", "10k", "Device:R", FP_R, {1: "MOTOR_EN", 2: "GND"}, (55.0, 33.0, 0),
        _sch_pos(), desc="Pull-down MOTOR_EN (motores apagados durante el arranque)")
    add("D5", "1N5819", "Device:D_Schottky", FP_DO41, {1: "VIN_A", 2: "+5V"},
        (55.0, 27.2, 0), _sch_pos(), desc="Schottky +5V -> VIN ESP32-A", mpn="1N5819 DO-41")

    add("J9", "PI (UART2)", "Connector:Screw_Terminal_01x03", FP_TB3,
        {1: "GND", 2: "PI_RXD2", 3: "PI_TXD2"}, PI_TB, _sch_pos(),
        desc="Hacia el HAT de bornas de la Pi: 1 GND (pin 6), 2 RXD2 = GPIO5 (pin 29), 3 TXD2 = GPIO4 (pin 7)",
        mpn="Phoenix PT 1,5/3-3,5-H o KF350-3P 3.5mm")
    add("R13", "1k", "Device:R", FP_R, {1: "PI_TXD2", 2: "ESPA_RX"}, (76.62, 30.0, 180),
        _sch_pos(), desc="Serie UART Pi TXD2 -> ESP32-A RX")
    add("R14", "1k", "Device:R", FP_R, {1: "ESPA_TX", 2: "PI_RXD2"}, (69.0, 34.0, 0),
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
        pins = enc_pins(ref, ms)
        silk(" ".join({"GND": "G", "+5V": "5V"}[pins[i]] if pins[i] in ("GND", "+5V") else "A" + pins[i][3]
                      for i in range(1, 6)),
             x + 7.0, ENC_TB_Y - 2.9, 0.65)
    x, y, _ = at("J5")
    silk("5V IN: + -", x - 2.54, y + 6.4, 0.8)
    x, y, _ = at("J9")
    silk("PI: GND RX TX", x - 7.4, y - 3.5, 0.8, rot=90)
    x, y, _ = at("U2")
    silk("ESP32-A (USB arriba)", x, y + 29.0, 0.9, bold=True)
