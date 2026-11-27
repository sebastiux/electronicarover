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
                          COMPONENTS, FP_R, FP_C, FP_CP10, FP_LED, FP_DO41, FP_MH,
                          add, esp_pin_number, pad_side)
from rover_split_comun import *  # noqa: F401,F403
from rover_split_comun import FP_ESP32, FP_TB6, FP_TB5, FP_TB3, FP_TB2, MPN_TB2
FP_RV = "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P2.54mm_Vertical"

PROJECT = "rover_traccion"
REVISION = "2.2-T"
TITLE = "Rover - tarjeta de TRACCION (ESP32-A, 3x L298N, encoders)"

BOARD_W = 96.2
BOARD_H = 110.5

ESPA_POS = (44.5, 49.5, 180)          # vertical, USB arriba: fila IO23.. mira a las bornas
TB_X = 6.4
# pad 1 (EN) de cada borna. J42 va centrada con sus 4 pines de la ESP32 (abanico corto) y J41 a 4.6 mm de J42.
TB_Y = {"U6": 15.75, "U5": 42.02, "U4": 64.12}
TB_ORDER = ["EN", "IN4", "IN3", "IN2", "IN1", "GND"]   # de arriba a abajo
EN_X = 2.7                            # bus de EN por la orilla izquierda (planar)
ENC_TB_Y = BOARD_H - 6.7              # deja pasar el bus de GND entre los pads y la orilla
YF = ENC_TB_Y - 5.0                   # tramo inferior del +5V (y del cable de +5V a J8)
YB = ENC_TB_Y + 3.95                  # bus de GND de la orilla inferior
ENC_TB = [("J7", 64.0, (1, 2, 3)), ("J8", 26.4, (6, 5, 4))]
# orden de pines de cada borna de encoders (izquierda -> derecha). J7 recibe el +5V por la
# derecha (A1 A2 A3 5V G) para que el +5V no cruce los canales A; J8 queda G 5V A6 A5 A4.
ENC_ORDEN = {"J7": ("A", "A", "A", "+5V", "GND"), "J8": ("GND", "+5V", "A", "A", "A")}
# Divisores 10k/20k + 1 nF.
# M6..M4, DEBAJO del modulo: tres bloques en fila. En cada uno la R de 10k y la de 20k van
# acostadas en vertical y un bus de GND horizontal pasa ENTRE sus pads (bajo el cuerpo): asi el GND
# cruza las tres cadenas de senal sin cables.
DIV_ABAJO = {6: 31.8, 5: 43.6, 4: 55.4}     # x del nodo (R10k) de cada bloque
DIV_ABAJO_Y = 77.0                          # y de la fila de nodos
DIV_CARRIL = {6: 47.6, 5: 50.6, 4: 53.6}    # x de su carril bajo el modulo (a 3 mm)
DIV_GIRO = {6: 71.0, 5: 74.0, 4: None}      # y donde cada carril gira hacia su bloque
DIV_R20 = 4.3                               # R10k -> R20k
DIV_CX = 7.6                                # R10k -> capacitor
DIV_BUS = DIV_ABAJO_Y + 3.81                # y del bus de GND (centro de las resistencias)
# M3..M1, a la derecha de la ESP32-A: bloques R10k / R20k / C apilados (filas a DIV_DY mm) y un bus
# de GND vertical que pasa entre los pads de las resistencias.
#   (y de la fila R10k, x de la columna de nodos, lado, carril al pin, y de aterrizaje,
#    x del canal de la senal de 5 V, y de su carril inferior)
DIV_DY = 4.2
DIV_C = 2 * DIV_DY
DIVIDERS = {
    3: (51.2, 70.4, "R", 60.8, 51.2 + DIV_DY, 87.7, 94.6),
    2: (63.8, 70.4, "R", 63.8, 63.8, 84.7, 91.6),
    1: (76.4, 70.4, "R", 66.8, 76.4 + DIV_DY, 81.7, 88.6),
}
DIV_BUS_X = 70.4 + 3.81               # bus de GND de los divisores de la derecha
GND_X = 78.41                         # GND que baja entre los pads de R13 y R14
FEED_X = 90.7                         # +5V que baja a los encoders (por fuera de J9 y de los divisores)
ANILLO_X = BOARD_W - 2.5              # GND por la orilla: de J5, por arriba y por la derecha, al bus de abajo
TRONCO_X = 66.58                      # GND de J5 que baja entre los pads de D5
PI_TB = (87.0, 42.5, 90)              # J9 junto a la orilla derecha (pad 1 = GND abajo)
R13_Y, R14_Y = 34.2, 38.5
CHASSIS_HOLES = [(3.5, 8.5), (89.8, 7.2), (15.0, 99.0), (85.5, 103.0)]
ALIGN_HOLES = []


def routing_reserved():
    return [(BOARD_W - 13.0, 22.0, BOARD_W, BOARD_H, {"Default", "GND"}),
            (8.0, 8.0, 56.0, 27.0, {"GND", "PWR", "Default"}),
            (14.0, ENC_TB_Y + 1.3, BOARD_W - 13.0, BOARD_H, {"GND"})]


def espa_left_y(name):
    return ESPA_POS[1] + 17.78 - 2.54 * ESP32_LEFT.index(name)


def preroutes():
    out = []
    ex = ESPA_POS[0] - 12.7           # fila de pines que mira a las bornas (x 31.8)
    xl = ESPA_POS[0] + 12.7           # fila de pines que mira a los divisores (x 57.2)

    def T(net, pts, w=1.0):
        out.append((net, pts, w))

    def cable(net, a, b):
        """Puente de alambre por arriba: 2 pads (vias) y la guia en F.Cu."""
        out.append(("VIA", net, a[0], a[1]))
        out.append(("VIA", net, b[0], b[1]))
        out.append((net, [a, b], 1.0, "F.Cu"))

    # ---- IN1..IN4 de las 3 bornas -------------------------------------------------------
    # J43 (arriba) y J41 (abajo): carriles a 3.0 mm (pista 1.0 + hueco 2.0). J42: abanico corto.
    lanes = {"U6": {4: 28.1, 3: 25.1, 2: 22.1, 1: 19.1},
             "U4": {4: 19.1, 3: 22.1, 2: 25.1, 1: 28.1}}
    for k, ref in enumerate(("U4", "U5", "U6")):
        for j in range(1, 5):
            yt = TB_Y[ref] + 3.5 * TB_ORDER.index("IN%d" % j)
            yi = ESPA_POS[1] + 17.78 - 2.54 * ESP32_RIGHT.index(ESPA_IN[k][j - 1])
            if ref == "U5":
                pts = [(TB_X, yt), (8.0, yt), (18.5, yi), (ex, yi)]
            else:
                x = lanes[ref][j]
                pts = [(TB_X, yt), (x, yt), (x, yi), (ex, yi)]
            T("%s_IN%d" % (ref, j), pts)
    # ---- MOTOR_EN -----------------------------------------------------------------------
    ys = sorted(TB_Y.values())
    T("MOTOR_EN", [(TB_X, ys[0]), (EN_X, ys[0]), (EN_X, ys[-1]), (TB_X, ys[-1])])
    T("MOTOR_EN", [(EN_X, ys[1]), (TB_X, ys[1])])
    # del bus de EN (J43-1) al pin IO13: por arriba del modulo y entrando al pin por DEBAJO de el.
    # R21 (pull-down) va montada sobre el tramo vertical.
    ym = espa_left_y("IO13")
    T("MOTOR_EN", [(TB_X, TB_Y["U6"]), (8.5, TB_Y["U6"] - 2.75), (8.5, 6.5), (46.0, 6.5),
                   (46.0, ym), (xl, ym)])
    # ---- +5V ----------------------------------------------------------------------------
    T("+5V", [(67.0, 7.0), (76.5, 7.0), (76.5, 18.5)], 1.5)                 # J5 -> C2 -> R25
    T("+5V", [(76.5, 18.5), (71.66, 23.34), (71.66, 25.8)], 1.5)            # -> anodo de D5
    # de ahi a los encoders: sigue a la derecha, baja por fuera de J9 y de los divisores y entra a J7
    x7 = enc_pin_tb("J7", "+5V")
    T("+5V", [(76.5, 7.0), (83.5, 7.0), (FEED_X, 7.0 + FEED_X - 83.5), (FEED_X, YF), (x7 + 2.2, YF)])   # rodea el barreno H2
    T("+5V", [(x7 + 2.2, YF), (x7, YF), (x7, ENC_TB_Y)])       # al pin entra con 1.0 mm
    # +5V a J8: cable fijo por arriba, del tramo de +5V que llega a J7 al pin +5V de J8
    xb = enc_pin_tb("J8", "+5V") - 0.3
    cable("+5V", (x7 + 2.2, YF), (xb, YF))
    T("+5V", [(xb, YF), (xb + 0.3, YF + 1.5), (xb + 0.3, ENC_TB_Y)])
    T("LED5_A", [(84.12, 18.5), (84.12, 24.46)])
    # ---- VIN, UART ----------------------------------------------------------------------
    yv = espa_left_y("VIN")
    T("VIN_A", [(xl, yv), (58.7, yv), (61.5, yv - 2.8), (61.5, 25.8)])
    yr, yt_ = espa_left_y("IO14"), espa_left_y("IO27")
    T("ESPA_RX", [(xl, yr), (58.8, yr), (60.8, yr - 2.0), (71.0, yr - 2.0), (71.0, R13_Y), (74.6, R13_Y)])
    T("ESPA_TX", [(xl, yt_), (74.6, yt_), (74.6, R14_Y)])
    xp, yp1 = PI_TB[0], PI_TB[1]
    T("PI_TXD2", [(82.22, R13_Y), (84.5, R13_Y), (85.8, yp1 - 7.0), (xp, yp1 - 7.0)])
    T("PI_RXD2", [(82.22, R14_Y), (85.0, R14_Y), (85.5, yp1 - 3.5), (xp, yp1 - 3.5)])
    # ---- GND: todo en cobre, con pistas fijas (el plano solo rellena) ----------------------
    yg = espa_left_y("GND")
    # tronco: J5 -> entre los pads de D5 -> rama a la derecha -> entre los pads de R13/R14 -> J9
    T("GND", [(61.92, 7.0), (61.92, 11.0), (TRONCO_X, 15.66), (TRONCO_X, 30.0)], 1.5)
    T("GND", [(TRONCO_X, 30.0), (84.12, 30.0)], 1.5)
    # anillo: de J5 por la orilla de arriba y la derecha al bus de la orilla inferior (sin puentes)
    T("GND", [(61.92, 7.0), (61.92, 2.5), (ANILLO_X - 1.5, 2.5), (ANILLO_X, 4.0), (ANILLO_X, YB - 1.25),
              (ANILLO_X - 1.5, YB + 0.25), (92.0, YB + 0.25)])     # esquinas en chaflan (la tarjeta va redondeada)
    T("GND", [(xl, yg), (TRONCO_X, yg), (TRONCO_X, 30.0)])                    # pin GND (14) de la ESP32
    T("GND", [(81.5, 11.5), (80.31, 12.69), (80.31, 30.0)])                    # C2 (pasa bajo R25)
    T("GND", [(84.12, 27.0), (84.12, 30.0)])                                   # catodo del LED
    T("GND", [(GND_X, 30.0), (GND_X, 47.5)])
    T("GND", [(GND_X, yp1), (xp, yp1)], 1.5)                                   # J9 pin 1
    # isla de arriba (entre MOTOR_EN y las bornas): pin GND (29) de la ESP32, por dentro del modulo
    T("GND", [(ex, yg), (ex + 3.6, yg), (ex + 3.6, 15.0)])
    T("GND", [(14.0, 15.0), (42.2, 15.0)])
    T("GND", [(49.8, 15.0), (56.92, 15.0), (61.92, 10.0)])
    T("GND", [(53.62, 15.0), (53.62, 20.0)])                                   # R21
    cable("GND", (42.2, 15.0), (49.8, 15.0))                                   # salta MOTOR_EN
    # GND de las bornas de los L298N: J43 a la isla de arriba, J42 al GND de J41, J41 al bus inferior
    g6, g5, g4 = TB_Y["U6"] + 17.5, TB_Y["U5"] + 17.5, TB_Y["U4"] + 17.5
    T("GND", [(TB_X, g6), (14.0, g6 + 0.25)])
    cable("GND", (14.0, g6 + 0.25), (14.0, 15.0))
    T("GND", [(TB_X, g5), (12.5, g5)])
    T("GND", [(TB_X, g4), (12.5, g4 + 0.28)])
    cable("GND", (12.5, g5), (12.5, g4 + 0.28))
    # bus de GND de la orilla inferior: J41, J8, divisores de abajo, J7 y el anillo de la derecha
    T("GND", [(TB_X, g4), (TB_X, YB), (92.0, YB)], 1.5)
    T("GND", [(enc_pin_tb("J8", "GND"), YB), (enc_pin_tb("J8", "GND"), ENC_TB_Y)])
    T("GND", [(enc_pin_tb("J7", "GND"), YB), (enc_pin_tb("J7", "GND"), ENC_TB_Y)])
    # ---- divisores M3..M1 (derecha) ------------------------------------------------------
    y4, y3, y2 = espa_left_y(ESPA_ENC[3]), espa_left_y(ESPA_ENC[2]), espa_left_y(ESPA_ENC[1])
    for m, (y, xn, side, lane, yl, xch, yb) in DIVIDERS.items():
        yp = espa_left_y(ESPA_ENC[m])
        if m == 3:        # sube en diagonal en cuanto sale del pin
            pts = [(xl, yp), (58.8, yp), (lane, yp - 2.0), (lane, yl), (xn, yl)]
        elif m == 2:      # recto, y baja a su fila al final
            pts = [(xl, yp), (66.3, yp), (66.3 + (yl - yp), yl), (xn, yl)]
        else:             # baja en diagonal y sigue por su carril
            pts = [(xl, yp), (60.0, yp), (62.5, yp + 2.5), (lane, yp + 2.5), (lane, yl), (xn, yl)]
        T("ENC%d_A" % m, pts)
        T("ENC%d_A" % m, [(xn, y), (xn, y + DIV_DY), (xn, y + DIV_C)])
        xt = enc_pin_x(m)
        T("ENC%d_A5V" % m, [(xn + 7.62, y), (xch, y), (xch, yb), (xt, yb), (xt, ENC_TB_Y)])
        T("GND", [(DIV_BUS_X, y + DIV_DY), (xn + 7.62, y + DIV_DY)])
        T("GND", [(DIV_BUS_X, y + DIV_C), (xn + 5.0, y + DIV_C)])
    T("GND", [(GND_X, 47.5), (DIV_BUS_X, 47.5), (DIV_BUS_X, DIVIDERS[1][0] + DIV_C)])
    # ---- divisores M6..M4 (debajo del modulo) --------------------------------------------
    yb0 = DIV_ABAJO_Y
    bajada = {6: None, 5: 88.5, 4: 91.5}        # y del tramo horizontal de cada senal hacia J8
    for m, x in DIV_ABAJO.items():
        yp = espa_left_y(ESPA_ENC[m])
        xc, yg_ = DIV_CARRIL[m], DIV_GIRO[m]
        if yg_ is None:
            T("ENC%d_A" % m, [(xl, yp), (xc, yp), (xc, 70.0), (x, 70.0 + (x - xc)), (x, yb0)])
        else:                                    # carril a 3 mm bajo el modulo y giro escalonado
            T("ENC%d_A" % m, [(xl, yp), (xc, yp), (xc, yg_), (x, yg_), (x, yb0)])
        T("ENC%d_A" % m, [(x, yb0), (x + DIV_R20, yb0), (x + DIV_CX, yb0)])
        xt = enc_pin_x(m)
        ya = yb0 + 7.62
        if bajada[m] is None:
            T("ENC%d_A5V" % m, [(x, ya), (x, 90.0), (xt, 90.0 + (xt - x)), (xt, ENC_TB_Y)])
        else:
            T("ENC%d_A5V" % m, [(x, ya), (x, bajada[m]), (xt, bajada[m]), (xt, ENC_TB_Y)])
        T("GND", [(x + DIV_R20, DIV_BUS), (x + DIV_R20, ya)])
        T("GND", [(x + DIV_CX, DIV_BUS), (x + DIV_CX, yb0 + 5.0)])
    x6, x4 = DIV_ABAJO[6], DIV_ABAJO[4]
    T("GND", [(x6 + DIV_R20, DIV_BUS), (x4 + DIV_CX, DIV_BUS)])
    T("GND", [(x4 + DIV_R20, yb0 + 7.62), (x4 + DIV_R20, YB)], 1.5)
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
ROUTING_LATE = []
# GND y +5V van completas en pistas fijas (preroutes): el router no las toca
ROUTING_SKIP = {"GND", "+5V"}



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
        add("R%d" % m, "10k", "Device:R", FP_R, {1: "ENC%d_A5V" % m, 2: "ENC%d_A" % m},
            (x, y0 + 7.62, 90), _sch_pos(), desc="Divisor encoder M%d (serie)" % m)
        add("R%d" % (m + 6), "20k", "Device:R", FP_R, {1: "ENC%d_A" % m, 2: "GND"},
            (x + DIV_R20, y0, 270), _sch_pos(), desc="Divisor encoder M%d (a GND)" % m)
        add("C%d" % (10 + m), "1nF", "Device:C", FP_C, {1: "ENC%d_A" % m, 2: "GND"},
            (x + DIV_CX, y0, 270), _sch_pos(), desc="Filtro de ruido encoder M%d" % m)

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
        add("C%d" % (10 + m), "1nF", "Device:C", FP_C, {1: "ENC%d_A" % m, 2: "GND"},
            cc, _sch_pos(), desc="Filtro de ruido encoder M%d" % m)

    add("J5", "5V IN (buck 5V)", "Connector:Screw_Terminal_01x02", FP_TB2,
        {1: "+5V", 2: "GND"}, (67.0, 7.0, 180), _sch_pos(),
        desc="Entrada 5 V desde el step-down (ESP32-A y encoders)", mpn=MPN_TB2)
    add("C2", "1000uF 16V", "Device:C_Polarized", FP_CP10, {1: "+5V", 2: "GND"},
        (76.5, 11.5, 0), _sch_pos(), desc="Bulk 5V", mpn="1000uF 16V radial, cuerpo de 10 mm de diametro, paso 5 mm")
    add("R25", "330", "Device:R", FP_R, {1: "+5V", 2: "LED5_A"}, (76.5, 18.5, 0),
        _sch_pos(), desc="Resistencia LED 5V")
    add("D3", "LED verde 5V", "Device:LED", FP_LED, {1: "GND", 2: "LED5_A"},
        (84.12, 27.0, 90), _sch_pos(), desc="Indicador 5V")
    add("R21", "10k", "Device:R", FP_R, {1: "MOTOR_EN", 2: "GND"}, (46.0, 20.0, 0),
        _sch_pos(), desc="Pull-down MOTOR_EN (motores apagados durante el arranque)")
    add("D5", "1N5819", "Device:D_Schottky", FP_DO41, {1: "VIN_A", 2: "+5V"},
        (61.5, 25.8, 0), _sch_pos(), desc="Schottky +5V -> VIN ESP32-A", mpn="1N5819 DO-41")

    add("J9", "PI (UART2)", "Connector:Screw_Terminal_01x03", FP_TB3,
        {1: "GND", 2: "PI_RXD2", 3: "PI_TXD2"}, PI_TB, _sch_pos(),
        desc="Hacia el HAT de bornas de la Pi: 1 GND (pin 6), 2 RXD2 = GPIO5 (pin 29), 3 TXD2 = GPIO4 (pin 7)",
        mpn="Phoenix PT 1,5/3-3,5-H o KF350-3P 3.5mm")
    add("R13", "1k", "Device:R", FP_R, {1: "PI_TXD2", 2: "ESPA_RX"}, (82.22, R13_Y, 180),
        _sch_pos(), desc="Serie UART Pi TXD2 -> ESP32-A RX")
    add("R14", "1k", "Device:R", FP_R, {1: "ESPA_TX", 2: "PI_RXD2"}, (74.6, R14_Y, 0),
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
    silk("5V IN: - +", x - 2.54, y + 6.4, 0.8)        # izquierda GND, derecha +5V (pad 1, junto a C2)
    x, y, _ = at("J9")
    silk("PI: TX RX GND", x - 7.4, y - 3.5, 0.8, rot=270)   # de arriba a abajo: TXD2, RXD2, GND
    x, y, _ = at("U2")
    silk("ESP32-A (USB arriba)", x, y + 29.0, 0.9, bold=True)
