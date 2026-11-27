# -*- coding: utf-8 -*-
"""
Tarjeta de SERVOS (una sola cara): ESP32-B, 8 servos (4 de direccion + 4 del brazo) y
medicion de bateria.

- 8 headers 1x3 (SIG, V+, GND) bajo la ESP32-B, alimentados por J6 (BEC 6 V).
- J2: derivacion de bateria (divisor 100k/27k al ADC y LED rojo).
- J9 "PI": GND, TXD4 y RXD4 de la Raspberry (desde su HAT de bornas), con R15/R16 de 1k.
- J5: 5 V del step-down (ESP32-B por D6).
Geometria heredada de la Cubiko de 2 caras (zona de la ESP32-B), corrida al origen.

Uso: ROVER_VARIANT=servos python3 generate.py --route
"""
from rover_design import (ESP32_LEFT, ESP32_RIGHT, SERVOS,  # noqa: F401
                          ESPB_UART_TX, ESPB_UART_RX, ESPB_VBAT,
                          COMPONENTS, FP_R, FP_C, FP_CP10, FP_LED, FP_DO41, FP_MH, FP_SERVO,
                          add, esp_pin_number, pad_side)
from rover_split_comun import *  # noqa: F401,F403
from rover_split_comun import FP_ESP32, FP_TB3, FP_TB2, MPN_TB2

PROJECT = "rover_servos"
REVISION = "2.2-S"
TITLE = "Rover - tarjeta de SERVOS (ESP32-B, 8 servos, bateria)"

BOARD_W = 73.5
BOARD_H = 100.0

ESPB_POS = (31.0, 59.0, 270)          # horizontal, USB a la izquierda: fila IO23.. mira a los servos
ESPB_RIGHT_Y = ESPB_POS[1] + 12.7
SERVO_Y = BOARD_H - 2.75              # pad GND de cada header (SIG queda 5.08 arriba): el riel de GND
#                                       es tambien el bus de la orilla inferior (pasa bajo J9)
SERVO_X0, SERVO_PASO = 19.22, 5.08   # headers a 5.08 mm: cada conector de servo con su espacio
J6_POS = (65.5, BOARD_H - 3.4, 90)    # entrada 6 V (pad 1 GND abajo, pad 2 +6 V arriba)
PI_TB = (5.0, BOARD_H - 6.7, 0)       # J9 en la orilla inferior izquierda
GND_IZQ = 8.0                         # GND que baja por la izquierda (de J5 al riel)
GND_DER = 70.5                        # barra de GND de la orilla derecha (J6, C3, C4, J2)
GND_Y = ESPB_POS[1]                   # GND que cruza por debajo del modulo
LED_X = 59.0                          # R26 y D4, entre el servo 1 y la barra de +6 V
VBUS_X = 65.5                         # barra de +6 V (J6, C4, C3)
CHASSIS_HOLES = [(3.5, 4.0), (BOARD_W - 3.5, 4.0), (3.5, 64.0), (60.0, 47.0)]
ALIGN_HOLES = []


def espb_right_x(name):
    return ESPB_POS[0] + 17.78 - 2.54 * ESP32_RIGHT.index(name)


def servo_x(n):
    """x del header del servo n: en el mismo orden que sus pines, a SERVO_PASO."""
    orden = sorted(range(1, 9), key=lambda k: espb_right_x(SERVOS[k][0]))
    return SERVO_X0 + SERVO_PASO * orden.index(n)


def preroutes():
    """Todo va en pistas fijas (sin cables): senales en escalera a 3.0 mm, GND y +6 V en barras."""
    out = []

    def T(net, pts, w=1.0):
        out.append((net, pts, w))

    yr = ESPB_RIGHT_Y                                     # fila de abajo (pines 16..30)
    yl = ESPB_POS[1] - 12.7                               # fila de arriba (pines 1..15)
    ys = SERVO_Y - 5.08                                   # pads SIG
    px = {n: espb_right_x(SERVOS[n][0]) for n in range(1, 9)}
    hx = {n: servo_x(n) for n in range(1, 9)}
    # ---- senales de servo: cada pista se separa a 3.0 mm de su vecina en cuanto sale del pin y
    # gira a su header en un nivel propio (escalera): fuera de los pines el hueco es de 2.0 mm o mas
    # (en cada grupo de pines vecinos se abre primero la de la derecha; las pistas acaban 0.2 mm antes
    #  del centro del pad SIG para no acercarse al riel de +6 V mas que el propio pad)
    ye = ys - 0.2

    def abre(x, y, x2):                                   # diagonal a 45 grados de (x, y) a x2
        return [(x, y), (x2, y + abs(x2 - x))]

    T("SERVO8", [(px[8], yr), (px[8], 81.3), (hx[8], 81.3), (hx[8], ye)])
    T("SERVO7", [(px[7], yr)] + abre(px[7], 75.4, px[7] + 0.46) + [(px[7] + 0.46, 84.3), (hx[7], 84.3), (hx[7], ye)])
    T("SERVO6", [(px[6], yr)] + abre(px[6], 73.9, hx[6]) + [(hx[6], ye)])
    T("SERVO5", [(px[5], yr)] + abre(px[5], 77.4, hx[5]) + [(hx[5], ye)])
    T("SERVO4", [(px[4], yr)] + abre(px[4], 75.6, 37.5) + [(37.5, 84.0), (hx[4], 84.0), (hx[4], ye)])
    T("SERVO3", [(px[3], yr)] + abre(px[3], 73.9, 40.5) + [(40.5, 81.0), (hx[3], 81.0), (hx[3], ye)])
    T("SERVO2", [(px[2], yr), (px[2], 78.3), (hx[2], 78.3), (hx[2], ye)])
    T("SERVO1", [(px[1], yr), (px[1], 75.3), (hx[1], 75.3), (hx[1], ye)])
    # ---- UART: salen hacia la izquierda, RX arriba y TX abajo, a R15/R16 (acostadas) y a J9
    xt, xr = espb_right_x("IO2"), espb_right_x("IO15")
    jx9, jy9 = PI_TB[0], PI_TB[1]
    T("ESPB_RX", [(xr, yr), (xr, 75.3), (9.0, 75.3)])
    T("ESPB_TX", [(xt, yr), (xt, 78.3), (13.2, 78.3), (13.2, 79.0)])
    T("PI_TXD4", [(9.0, 82.92), (9.0, 84.5), (jx9 + 3.5, 85.0), (jx9 + 3.5, jy9)])
    T("PI_RXD4", [(13.2, 86.62), (13.2, 88.4), (jx9 + 7.0, 89.6), (jx9 + 7.0, jy9)])
    # ---- +5V, VIN, medicion de bateria
    T("+5V", [(5.6, 20.0), (10.5, 20.0), (13.22, 22.72), (13.22, 24.84)], 1.5)
    T("VIN_B", [(13.22, 35.0), (13.22, yl)])
    xv = ESPB_POS[0] + 17.78 - 2.54 * ESP32_LEFT.index(next(n for n in ESP32_LEFT if ESPB_VBAT in n))
    T("VBAT_SENSE", [(xv, yl), (xv, 30.0)])                       # C5, R23 y R22 sobre esta pista
    jx2 = BOARD_W - 5.6
    T("VBAT_F", [(jx2, 20.92), (xv - 7.62, 20.92), (xv - 7.62, 30.0)])
    T("LED12_A", [(55.0, 28.54), (55.0, 31.86)])
    # ---- +6 V de servos: riel de los headers, barra a J6 y a los 2 capacitores, LED
    xs = sorted(hx.values())
    jx, jy, _ = J6_POS
    T("SERVO_V", [(x, SERVO_Y - 2.54) for x in xs] + [(xs[-1] + 2.2, SERVO_Y - 2.54)], 1.4)
    T("SERVO_V", [(xs[-1] + 2.2, SERVO_Y - 2.54), (xs[-1] + 4.74, SERVO_Y - 5.08)], 1.4)
    T("SERVO_V", [(xs[-1] + 4.74, SERVO_Y - 5.08), (jx, jy - 5.08)], 2.4)
    T("SERVO_V", [(jx, jy - 5.08), (VBUS_X, 72.0)], 2.4)
    T("SERVO_V", [(LED_X, 87.0), (LED_X, 90.0), (xs[-1] + 4.74, SERVO_Y - 5.08)])
    T("LEDS_A", [(LED_X, 79.38), (LED_X, 76.2)])
    # ---- GND: todo en cobre
    xg = espb_right_x("IO15") - 2.54                      # los 2 pines GND de la ESP32 (uno por fila)
    T("GND", [(xg, yl), (xg, yr)])                        # unidos por debajo del modulo
    T("GND", [(GND_IZQ, GND_Y), (GND_DER, GND_Y)], 1.5)   # cruza bajo el modulo, de lado a lado
    T("GND", [(5.6, 25.08), (GND_IZQ, 27.48), (GND_IZQ, 68.5), (4.4, 72.1), (4.4, SERVO_Y)], 1.5)   # J5 -> riel
    T("GND", [(4.4, jy9), (jx9, jy9)])                    # J9 pin 1
    T("GND", [(4.4, SERVO_Y)] + [(x, SERVO_Y) for x in xs] + [(60.0, SERVO_Y), (61.5, jy), (jx, jy)], 1.4)
    T("GND", [(jx, jy), (GND_DER, jy), (GND_DER, 28.6), (jx2, 26.0)], 1.5)     # J6 -> C4 -> C3 -> J2
    T("GND", [(LED_X, 73.66), (LED_X, GND_Y)])              # catodo del LED de servos
    T("GND", [(xv + 7.62, 36.5), (xv + 7.62, 38.5), (GND_DER, 38.5)])          # R23
    T("GND", [(xv + 5.0, 42.0), (xv + 7.62, 39.38)])                            # C5
    T("GND", [(55.0, 34.4), (55.0, 38.5)])                                     # catodo del LED de bateria
    return out


ROUTING_FIRST = ["ESPB_TX", "ESPB_RX", "PI_TXD4", "PI_RXD4"] + ["SERVO%d" % n for n in range(1, 9)]
ROUTING_EARLY = {"GND": set(),
                 "SERVO_V": {"J6", "C3", "C4", "J31", "J32", "J33", "J34", "J35", "J36", "J37", "J38"}}
# GND, +5V y +6 V van completas en pistas fijas (preroutes): el router no las toca
ROUTING_SKIP = {"GND", "+5V", "SERVO_V"}


def external_nodes():
    """Raspberry Pi (header virtual U1) por su HAT de bornas -> J9."""
    return [("U1", "32", "PI_TXD4"), ("U1", "33", "PI_RXD4"), ("U1", "34", "GND")]


_sch = [0]


def _sch_pos():
    i = _sch[0]
    _sch[0] += 1
    return (25.4 + 76.2 * (i % 10), 38.1 + 76.2 * (i // 10))


def build():
    COMPONENTS.clear()
    _sch[0] = 0
    espb = {i: None for i in range(1, 31)}
    espb[esp_pin_number("VIN")] = "VIN_B"
    espb[14] = espb[29] = "GND"
    for n, (g, _) in SERVOS.items():
        espb[esp_pin_number(g)] = "SERVO%d" % n
    espb[esp_pin_number(ESPB_VBAT)] = "VBAT_SENSE"
    espb[esp_pin_number(ESPB_UART_TX)] = "ESPB_TX"
    espb[esp_pin_number(ESPB_UART_RX)] = "ESPB_RX"
    add("U3", "ESP32-B_Servos", "rover:ESP32_DevKitV1_30P", FP_ESP32,
        espb, ESPB_POS, _sch_pos(), desc="ESP32 DevKit V1 30 pines sobre 2x header hembra 1x15",
        mpn="ESP32 DevKit V1 + 2x header hembra 1x15")

    add("J9", "PI (UART4)", "Connector:Screw_Terminal_01x03", FP_TB3,
        {1: "GND", 2: "PI_TXD4", 3: "PI_RXD4"}, PI_TB, _sch_pos(),
        desc="Hacia el HAT de bornas de la Pi: 1 GND (pin 34), 2 TXD4 = GPIO12 (pin 32), 3 RXD4 = GPIO13 (pin 33)",
        mpn="Phoenix PT 1,5/3-3,5-H o KF350-3P 3.5mm")
    add("R15", "1k", "Device:R", FP_R, {1: "ESPB_RX", 2: "PI_TXD4"}, (9.0, 75.3, 270),
        _sch_pos(), desc="Serie UART Pi TXD4 (GPIO12) -> ESP32-B RX")
    add("R16", "1k", "Device:R", FP_R, {1: "ESPB_TX", 2: "PI_RXD4"}, (13.2, 79.0, 270),
        _sch_pos(), desc="Serie UART ESP32-B TX -> Pi RXD4 (GPIO13)")

    add("J5", "5V IN (buck 5V)", "Connector:Screw_Terminal_01x02", FP_TB2,
        {1: "+5V", 2: "GND"}, (5.6, 20.0, 270), _sch_pos(),
        desc="Entrada 5 V desde el step-down (ESP32-B)", mpn=MPN_TB2)
    add("D6", "1N5819", "Device:D_Schottky", FP_DO41, {1: "VIN_B", 2: "+5V"},
        (13.22, 35.0, 90), _sch_pos(), desc="Schottky +5V -> VIN ESP32-B", mpn="1N5819 DO-41")

    add("J2", "BAT SENSE (12V)", "Connector:Screw_Terminal_01x02", FP_TB2,
        {1: "GND", 2: "VBAT_F"}, (BOARD_W - 5.6, 26.0, 90), _sch_pos(),
        desc="Derivacion de bateria despues del fusible (solo medicion y LED, < 10 mA)", mpn=MPN_TB2)
    add("R22", "100k", "Device:R", FP_R, {1: "VBAT_F", 2: "VBAT_SENSE"}, (33.54, 30.0, 0),
        _sch_pos(), desc="Divisor VBAT (alto)")
    add("R23", "27k", "Device:R", FP_R, {1: "VBAT_SENSE", 2: "GND"}, (41.16, 36.5, 0),
        _sch_pos(), desc="Divisor VBAT (bajo)")
    add("C5", "100nF", "Device:C", FP_C, {1: "VBAT_SENSE", 2: "GND"}, (41.16, 42.0, 0),
        _sch_pos(), desc="Filtro ADC VBAT")
    add("R24", "2.2k", "Device:R", FP_R, {1: "VBAT_F", 2: "LED12_A"}, (55.0, 20.92, 270),
        _sch_pos(), desc="Resistencia LED 12V")
    add("D2", "LED rojo 12V", "Device:LED", FP_LED, {1: "GND", 2: "LED12_A"},
        (55.0, 34.4, 90), _sch_pos(), desc="Indicador bateria")

    for n in range(1, 9):
        g, d = SERVOS[n]
        add("J%d" % (30 + n), "SERVO%d" % n, "rover:Servo_Header", FP_SERVO,
            {1: "GND", 2: "SERVO_V", 3: "SERVO%d" % n}, (servo_x(n), SERVO_Y, 180), _sch_pos(),
            desc="Servo %d - %s (SIG arriba, GND abajo)" % (n, d), mpn="Header macho 1x3 2.54mm")
    add("J6", "SERVO PWR IN (6V)", "Connector:Screw_Terminal_01x02", FP_TB2,
        {1: "GND", 2: "SERVO_V"}, J6_POS, _sch_pos(), desc="Entrada BEC servos 6V", mpn=MPN_TB2)
    add("C3", "1000uF 16V", "Device:C_Polarized", FP_CP10, {1: "SERVO_V", 2: "GND"},
        (VBUS_X, 72.0, 0), _sch_pos(), desc="Bulk servos", mpn="1000uF 16V radial, cuerpo de 10 mm de diametro, paso 5 mm")
    add("C4", "1000uF 16V", "Device:C_Polarized", FP_CP10, {1: "SERVO_V", 2: "GND"},
        (VBUS_X, 83.0, 0), _sch_pos(), desc="Bulk servos", mpn="1000uF 16V radial, cuerpo de 10 mm de diametro, paso 5 mm")
    add("R26", "470", "Device:R", FP_R, {1: "SERVO_V", 2: "LEDS_A"}, (LED_X, 87.0, 90),
        _sch_pos(), desc="Resistencia LED servos")
    add("D4", "LED azul SERVO", "Device:LED", FP_LED, {1: "GND", 2: "LEDS_A"},
        (LED_X, 73.66, 270), _sch_pos(), desc="Indicador rail servos")

    for i, (x, y) in enumerate(CHASSIS_HOLES):
        add("H%d" % (i + 1), "M3", "Mechanical:MountingHole", FP_MH, {}, (x, y, 0), _sch_pos(),
            desc="Agujero de montaje M3")
    return COMPONENTS


def pcb_labels(silk, at, comps):
    silk("ROVER SERVOS v%s" % REVISION, 40.0, 3.0, 1.0, bold=True)
    x, y, _ = at("J5")
    silk("5V IN: + -", x - 2.54, y + 6.4, 0.8)
    x, y, _ = at("J6")
    silk("6V: - +", x - 7.0, y - 2.5, 0.8, rot=90)
    x, y, _ = at("J2")
    silk("BAT 12V", x - 7.4, y - 2.5, 0.8, rot=90)
    x, y, _ = at("J9")
    silk("PI: GND TX RX", x + 3.5, y - 3.3, 0.8)
    for n in range(1, 9):
        x, y, _ = at("J%d" % (30 + n))
        silk("S%d" % n, x, y + 2.3, 0.7)
    x, y, _ = at("U3")
    silk("ESP32-B (USB izq)", x + 2.0, y - 16.0, 0.9, bold=True)
