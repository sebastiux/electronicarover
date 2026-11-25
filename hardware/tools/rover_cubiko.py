# -*- coding: utf-8 -*-
"""
Variante "cubiko" del Rover Controller: tarjeta chica para fresar en la
Genmitsu Cubiko (area de trabajo ~145-150 x 110 mm).

Diferencias contra la v1.2 (rover_design.py):
- Los 3 L298N van FUERA de la tarjeta (en el chasis, con sus bornas originales).
  La tarjeta lleva en la orilla IZQUIERDA 3 bornas de 7 vias (paso 3.5 mm) con
  ENB, IN4, IN3, IN2, IN1, ENA y GND para cada modulo.
- Encoders: 3 bornas de 4 vias en la orilla INFERIOR (un par de motores por borna:
  GND, +5V, A del motor impar, A del motor par). Los encoders se alimentan del
  +5V de la tarjeta (ya no del 78M05 del L298N).
- La bateria NO entra a la tarjeta: el arnes reparte bateria -> fusible -> L298N,
  step-down 5V y BEC 6V. Solo entra una derivacion de bateria (J2) para medir el
  voltaje y prender el LED de 12 V.
- Firmware y asignacion de pines de las ESP32: SIN CAMBIOS.

Uso: ROVER_VARIANT=cubiko python3 generate.py --route
"""
from rover_design import (ESP32, ESP32_LEFT, ESP32_RIGHT, RPI, RPI_PINS, MOTORS,  # noqa: F401
                          ESPA_IN, ESPA_ENC, ESPA_UART_RX, ESPA_UART_TX, ESPA_MOTOR_EN,
                          SERVOS, ESPB_UART_TX, ESPB_UART_RX, ESPB_VBAT, COMPONENTS,
                          FP_R, FP_C, FP_C25, FP_CP10, FP_LED, FP_DO15, FP_DO41, FP_MH,
                          FP_SERVO, add, esp_pin_number, LAYERS, FAB, TOP_SOLDERED, pad_side)

PROJECT = "rover_controller_cubiko"
REVISION = "1.2-C"
TITLE = "Rover Controller Cubiko - RPi5 + 2x ESP32 (L298N externos)"

BOARD_W = 136.0
BOARD_H = 96.0

FP_TB7 = "TerminalBlock_Phoenix:TerminalBlock_Phoenix_PT-1,5-7-3.5-H_1x07_P3.50mm_Horizontal"
FP_TB5 = "TerminalBlock_Phoenix:TerminalBlock_Phoenix_PT-1,5-5-3.5-H_1x05_P3.50mm_Horizontal"
FP_RV = "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P2.54mm_Vertical"

# Las ESP32 NO usan WiFi (hablan con la Pi por UART): bajo la ESP32-A se permite cobre y
# piezas bajas (patio solo en las filas de pines); se conserva el keepout de antena de la B.
ESP32 = dict(ESP32, courtyard="rows")
RPI_PINS = {**RPI_PINS, 32: "GPIO12/TXD4", 33: "GPIO13/RXD4"}
ANTENNA_KEEPOUT_REFS = ("U3",)
TOP_GND_POUR = True
# en prototipado el anillo superior de un pad soldado abajo no conduce: un rayo de mas o de
# menos hacia el plano superior no importa
EXTRA_SEVERITIES = {"starved_thermal": "ignore"}     # el cobre que no se fresa arriba queda como plano de GND (no flotante)
FP_TB2 = "TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal"

# Reglas pensadas para fresado con V-bit (ver hardware/cubiko/README.md):
# pista minima 0.7 mm, separacion minima 0.5 mm, vias = pin de 1.0 mm soldado por ambas caras.
NETCLASSES = [
    # name, track, clearance, via_d, via_drill, patterns
    ("SERVO", 2.5, 0.5, 2.2, 1.0, ["SERVO_V"]),
    ("PWR", 1.5, 0.5, 2.2, 1.0, ["+5V"]),        # el tramo J5 -> Pi va pre-trazado a 2.0 mm
    ("GND", 1.2, 0.5, 2.2, 1.0, ["GND"]),     # el plano de GND inferior hace el trabajo pesado
]
DEFAULT_CLASS = (0.7, 0.5, 2.2, 1.0)

# ---------------------------------------------------------------------------
# POSICIONES (mm, origen esquina superior izquierda, vista superior)
# ---------------------------------------------------------------------------
PI_ORIGIN = (BOARD_W - 65.0, 5.0)     # area HAT a la derecha (USB/ETH sobresalen); 5 mm libres arriba del header
ESPA_POS = (34.7, 49.5, 180)          # vertical, USB arriba: fila IO23.. mira a las bornas de los L298N
ESPB_POS = (101.0, 67.0, 270)         # horizontal, USB a la izquierda: fila IO23.. mira a los servos

TB_X = 5.5                            # columna de pads de las bornas de los L298N (orilla izquierda)
EN_VIA_X = 10.9                       # vias de MOTOR_EN: fuera del cuerpo de las bornas (acaba en X 9.1)
TB_Y = {"U6": 15.75, "U5": 43.25, "U4": 70.75}   # pad 1 (arriba) de cada borna
TB_ORDER = ["ENB", "IN4", "IN3", "IN2", "IN1", "ENA", "GND"]   # de arriba a abajo
ENC_TB_Y = BOARD_H - 5.0
# Bornas de encoders (5 vias): (ref, x del pad 1, motores en los pads 3, 4 y 5)
ENC_TB = [("J7", 50.0, (1, 2, 3)), ("J8", 22.0, (6, 5, 4))]
# Divisores 10k/20k + 1 nF, un bloque por encoder (ver DIVIDERS en preroutes):
#   M4..M6 bajo la ESP32-A (llegan a sus pines por la izquierda), M1..M3 a la derecha.
#   (fila y del bloque, x de la columna de nodos, lado, carril al pin, y de aterrizaje,
#    x del canal de la senal de 5 V, y de su carril inferior)
DIV_C = 6.4             # fila del capacitor dentro del bloque (R10k en y, R20k en y+3.6)
DIVIDERS = {
    6: (40.0, 41.3, "L", 45.55, 46.4, 26.45, 80.4),
    5: (49.0, 41.3, "L", 44.35, 55.4, 27.65, 79.2),
    4: (58.0, 41.3, "L", 43.15, 58.0, 28.85, 78.0),
    3: (58.0, 56.0, "R", 51.65, 61.6, 68.4, 87.0),
    2: (67.0, 56.0, "R", 50.45, 67.0, 67.2, 85.8),
    1: (76.0, 56.0, "R", 49.25, 76.0, 66.0, 84.6),
}
J6_X = 125.5                          # pad 1 (GND) de la entrada de servos, orilla inferior


def espa_left_y(name):
    """Y de un pin de la fila izquierda (EN, IO36..VIN) de la ESP32-A (rot 180)."""
    return ESPA_POS[1] + 17.78 - 2.54 * ESP32_LEFT.index(name)


def espb_right_x(name):
    """X de un pin de la fila IO23.. de la ESP32-B (rot 270, fila inferior)."""
    return ESPB_POS[0] + 17.78 - 2.54 * ESP32_RIGHT.index(name)


ESPB_RIGHT_Y = ESPB_POS[1] + 12.7
SERVO_Y = ESPB_RIGHT_Y + 9.4          # pad GND de cada header (rot 180: SIG queda 5.08 arriba)


def routing_reserved():
    return []


def preroutes():
    out = []
    # abanico IN1..IN4 de las 3 bornas a la fila IO23.. de la ESP32-A (carriles fijos,
    # sin cruces): horizontal desde el pad, vertical en su carril, horizontal al pin
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
    # +5V de la Pi: J5 -> via -> cara superior -> pines 2 y 4 (fila exterior)
    ox, oy = PI_ORIGIN
    p2x, prow = ox + RPI["pin1"][0], oy + RPI["row_even_y"]
    vx, vy = 69.0, 3.6
    out.append(("+5V", [(64.0, 5.6), (vx, vy)], 2.0))
    out.append(("VIA", "+5V", vx, vy))
    out.append(("+5V", [(vx, vy), (p2x, vy), (p2x + 2.54, vy)], 2.0, "F.Cu"))
    out.append(("+5V", [(p2x, vy), (p2x, prow)], 1.5, "F.Cu"))
    out.append(("+5V", [(p2x + 2.54, vy), (p2x + 2.54, prow)], 1.5, "F.Cu"))
    # servos: SIG recta desde la ESP32-B, filas V+ y GND horizontales hacia J6
    xs = sorted(espb_right_x(SERVOS[n][0]) for n in range(1, 9))
    for n in range(1, 9):
        x = espb_right_x(SERVOS[n][0])
        out.append(("SERVO%d" % n, [(x, ESPB_RIGHT_Y), (x, SERVO_Y - 5.08)], 0.7))
    # J6 en la orilla inferior: pad 1 (GND) en J6_X, pad 2 (V+) 5.08 a la derecha
    out.append(("SERVO_V", [(x, SERVO_Y - 2.54) for x in xs] + [(J6_X + 3.0, SERVO_Y - 2.54), (J6_X + 5.08, SERVO_Y - 0.5), (J6_X + 5.08, ENC_TB_Y)], 1.6))
    out.append(("GND", [(x, SERVO_Y) for x in xs] + [(J6_X - 1.5, SERVO_Y), (J6_X, ENC_TB_Y)], 1.6))
    # divisores de encoder: pin -> carril -> nodo; nodo = R10k, R20k y C apilados;
    # GND del bloque por una via (plano superior); la senal de 5 V sale por un canal
    # lateral y llega a su borna por un carril propio (planar, todo en la cara inferior)
    ex_l = ESPA_POS[0] + 12.7
    for m, (y, xn, side, lane, yl, xch, yb) in DIVIDERS.items():
        yp = espa_left_y(ESPA_ENC[m])
        d = -1 if side == "L" else 1
        out.append(("ENC%d_A" % m, [(ex_l, yp), (lane, yp), (lane, yl), (xn, yl)], 0.7))
        out.append(("ENC%d_A" % m, [(xn, y), (xn, y + 3.6), (xn, y + DIV_C)], 0.7))
        xg, xv, xa = xn + d * 2.5, xn + d * 5.0, xn + d * 7.62
        out.append(("GND", [(xg, y + DIV_C), (xv, y + DIV_C), (xa, y + DIV_C), (xa, y + 3.6)], 0.8))
        out.append(("VIA", "GND", xv, y + DIV_C))
        xt = enc_pin_x(m)
        out.append(("ENC%d_A5V" % m, [(xa, y), (xch, y), (xch, yb), (xt, yb), (xt, ENC_TB_Y)], 0.7))
    # MOTOR_EN: cada ENA/ENB de las bornas sube por una via propia a un bus vertical
    # en la cara superior (en la inferior esa franja la ocupa el abanico IN1..IN4)
    ys = []
    for ref in ("U6", "U5", "U4"):
        for i in (0, 5):                      # ENB (pad 1) y ENA (pad 6)
            y0 = TB_Y[ref] + 3.5 * i
            # la via de J41.6 sube 0.65 mm: asi su anillo queda a > 3.5 mm del centro de H3
            # (la rondana M3 de 7 mm tocaria MOTOR_EN y lo uniria al chasis)
            y = y0 - 0.65 if (ref, i) == ("U4", 5) else y0
            out.append(("MOTOR_EN", [(TB_X, y0), (EN_VIA_X, y)], 0.8))
            out.append(("VIA", "MOTOR_EN", EN_VIA_X, y))
            ys.append(y)
    out.append(("MOTOR_EN", [(EN_VIA_X, y) for y in sorted(ys)], 0.8, "F.Cu"))
    return out


ROUTING_FIRST = ["U%d_IN%d" % (u, i) for u in (6, 5, 4) for i in (4, 3, 2, 1)] + \
    ["MOTOR_EN", "ESPB_TX", "ESPB_RX", "PI_TXD4", "PI_RXD4", "ESPA_RX", "ESPA_TX", "PI_TXD2", "PI_RXD2",
     "SERVO1", "SERVO2", "SERVO3", "SERVO4", "SERVO5", "SERVO6", "SERVO7", "SERVO8"] + \
    ["ENC%d_A" % m for m in range(1, 7)] + ["ENC%d_A5V" % m for m in range(1, 7)]
ROUTING_LATE = []


def external_nodes():
    """Cableado FUERA de la tarjeta (para la simulacion del firmware): bornas J41-J43 ->
    header logico de cada L298N, salidas OUT1..4 -> motores, y cable Pololu de cada motor
    (J21..J26 virtuales: 1 M+, 2 M-, 3 GND, 4 VCC, 5 A) -> bornas de encoders J7/J8."""
    l298_pin = {"ENA": "8", "IN1": "9", "IN2": "10", "IN3": "11", "IN4": "12", "ENB": "13", "GND": "6"}
    out = []
    by_ref = {c["ref"]: c for c in COMPONENTS}
    for k, ref in enumerate(("U4", "U5", "U6")):
        tb = by_ref["J%d" % (41 + k)]
        for i, name in enumerate(TB_ORDER):
            out.append((ref, l298_pin[name], tb["pins"][i + 1]))
        ma, mb = 2 * k + 1, 2 * k + 2
        out += [(ref, "1", "EXT_M%d_A" % ma), (ref, "2", "EXT_M%d_B" % ma),
                (ref, "3", "EXT_M%d_A" % mb), (ref, "4", "EXT_M%d_B" % mb)]
    for m in range(1, 7):
        j = "J%d" % (20 + m)
        out += [(j, "1", "EXT_M%d_A" % m), (j, "2", "EXT_M%d_B" % m), (j, "3", "GND"), (j, "4", "+5V"),
                (j, "5", "ENC%d_A5V" % m)]
    return out


def enc_pin_x(m):
    for ref, x, ms in ENC_TB:
        if m in ms:
            return x + 3.5 * (2 + ms.index(m))
    raise KeyError(m)
ROUTING_EARLY = {
    "GND": set(),            # GND al final: primero senales, el plano conecta casi todo
    "+5V": {"J5", "C2", "D1", "U1"},
    "SERVO_V": {"J6", "C3", "C4", "J31", "J32", "J33", "J34", "J35", "J36", "J37", "J38"},
}


# H1 y el barreno superior derecho de la Pi son simetricos respecto a X = W/2:
# se usan como pines de alineacion para voltear la placa en la Cubiko.
ALIGN_HOLES = [(3.5, PI_ORIGIN[1] + 3.5), (BOARD_W - 3.5, PI_ORIGIN[1] + 3.5)]
CHASSIS_HOLES = [ALIGN_HOLES[0], (40.0, 4.0), (13.5, 92.0), (133.0, 70.0)]

_sch = [0]


def _sch_pos():
    i = _sch[0]
    _sch[0] += 1
    return (25.4 + 76.2 * (i % 10), 38.1 + 76.2 * (i // 10))


def build():
    COMPONENTS.clear()
    _sch[0] = 0
    ox, oy = PI_ORIGIN
    # ======================= RASPBERRY PI 5 =================================
    pi = {n: None for n in range(1, 41)}
    for n in (2, 4):
        pi[n] = "+5V"
    for n in (9, 25, 39):                     # GND de la fila interior (salen hacia abajo)
        pi[n] = "GND"
    pi[7], pi[29] = "PI_TXD2", "PI_RXD2"      # UART2 -> ESP32-A
    pi[32], pi[33] = "PI_TXD4", "PI_RXD4"     # UART4 (GPIO12/13, /dev/ttyAMA4) -> ESP32-B
    add("U1", "RaspberryPi5_GPIO", "rover:RaspberryPi5_GPIO", "rover:RPi5_HAT_Header_2x20",
        pi, (ox, oy, 0), _sch_pos(),
        desc="Header hembra 2x20 en la cara inferior (Pi 5 debajo)", mpn="Header hembra 2x20 2.54mm")

    # ======================= ESP32-A (traccion) =============================
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

    # ======================= ESP32-B (servos) ===============================
    espb = {i: None for i in range(1, 31)}
    espb[esp_pin_number("VIN")] = "VIN_B"
    espb[14] = espb[29] = "GND"
    for n, (g, _) in SERVOS.items():
        espb[esp_pin_number(g)] = "SERVO%d" % n
    espb[esp_pin_number(ESPB_VBAT)] = "VBAT_SENSE"
    espb[esp_pin_number(ESPB_UART_TX)] = "ESPB_TX"
    espb[esp_pin_number(ESPB_UART_RX)] = "ESPB_RX"
    add("U3", "ESP32-B_Servos", "rover:ESP32_DevKitV1_30P", "rover:ESP32_DevKitV1_30P_DualPitch",
        espb, ESPB_POS, _sch_pos(), desc="ESP32 DevKit V1 30 pines sobre 2x header hembra 1x15",
        mpn="ESP32 DevKit V1 + 2x header hembra 1x15")

    # ======================= Bornas hacia los L298N (orilla izquierda) =======
    for k, ref in enumerate(("U4", "U5", "U6")):
        sig = {"ENB": "MOTOR_EN", "ENA": "MOTOR_EN", "GND": "GND"}
        for j in range(1, 5):
            sig["IN%d" % j] = "%s_IN%d" % (ref, j)
        pins = {i + 1: sig[name] for i, name in enumerate(TB_ORDER)}
        ma, mb = 2 * k + 1, 2 * k + 2
        add("J%d" % (41 + k), "L298N #%d (M%d/M%d)" % (k + 1, ma, mb), "Connector:Screw_Terminal_01x07", FP_TB7,
            pins, (TB_X, TB_Y[ref], 270), _sch_pos(),
            desc="Borna 7 vias paso 3.5 mm hacia el L298N #%d (%s / %s): ENB IN4 IN3 IN2 IN1 ENA GND"
                 % (k + 1, MOTORS[ma], MOTORS[mb]),
            mpn="Phoenix PT 1,5/7-3,5-H (1984662) o KF350-7P 3.5mm")

    # ======================= Bornas de encoders (orilla inferior) ============
    for ref, x, ms in ENC_TB:
        pins = {1: "GND", 2: "+5V"}
        for i, m in enumerate(ms):
            pins[3 + i] = "ENC%d_A5V" % m
        add(ref, "ENC M%d M%d M%d" % tuple(ms), "Connector:Screw_Terminal_01x05", FP_TB5,
            pins, (x, ENC_TB_Y, 0), _sch_pos(),
            desc="Borna 5 vias paso 3.5 mm: GND, +5V y canal A de los motores %s (cable Pololu: "
                 "verde GND, azul VCC, amarillo A)" % ", ".join("M%d" % m for m in ms),
            mpn="Phoenix PT 1,5/5-3,5-H (1984646) o KF350-5P 3.5mm")

    # ======================= Divisores de encoder ===========================
    for m, (y, xn, side, lane, yl, xch, yb) in DIVIDERS.items():
        # R10k: pad 1 = 5V del encoder (lejos del nodo), pad 2 = nodo
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

    # ======================= Alimentacion 5V (orilla superior) ===============
    add("J5", "5V IN (buck 5V 5A)", "Connector:Screw_Terminal_01x02", FP_TB2,
        {1: "+5V", 2: "GND"}, (64.0, 5.6, 180), _sch_pos(),
        desc="Entrada 5V/5A desde step-down (alimenta Pi 5, ESP32 y encoders)", mpn="Phoenix MKDS 1,5/2-5,08 o KF301-2P")
    add("C2", "1000uF 10V", "Device:C_Polarized", FP_CP10, {1: "+5V", 2: "GND"},
        (75.0, 17.0, 0), _sch_pos(), desc="Bulk 5V")
    add("D1", "SA5.0A", "Device:D_Zener", FP_DO15, {1: "+5V", 2: "GND"},
        (52.0, 15.0, 0), _sch_pos(), desc="TVS 5V (proteccion Pi)", mpn="SA5.0A DO-15")
    add("R25", "330", "Device:R", FP_R, {1: "+5V", 2: "LED5_A"}, (52.0, 19.2, 0),
        _sch_pos(), desc="Resistencia LED 5V")
    add("D3", "LED verde 5V", "Device:LED", FP_LED, {1: "GND", 2: "LED5_A"},
        (69.04, 21.2, 180), _sch_pos(), desc="Indicador 5V")
    add("R21", "10k", "Device:R", FP_R, {1: "MOTOR_EN", 2: "GND"}, (52.0, 23.2, 0),
        _sch_pos(), desc="Pull-down MOTOR_EN (motores apagados durante el arranque)")
    add("D5", "1N5819", "Device:D_Schottky", FP_DO41, {1: "VIN_A", 2: "+5V"},
        (52.0, 27.2, 0), _sch_pos(), desc="Schottky +5V -> VIN ESP32-A", mpn="1N5819 DO-41")
    add("D6", "1N5819", "Device:D_Schottky", FP_DO41, {1: "VIN_B", 2: "+5V"},
        (79.0, 47.0, 0), _sch_pos(), desc="Schottky +5V -> VIN ESP32-B", mpn="1N5819 DO-41")

    # ======================= UART Pi <-> ESP32 (1k en serie) ===============
    add("R13", "1k", "Device:R", FP_R, {1: "PI_TXD2", 2: "ESPA_RX"}, (80.0, 26.0, 0),
        _sch_pos(), desc="Serie UART Pi TXD2 -> ESP32-A RX")
    add("R14", "1k", "Device:R", FP_R, {1: "ESPA_TX", 2: "PI_RXD2"}, (80.0, 30.0, 0),
        _sch_pos(), desc="Serie UART ESP32-A TX -> Pi RXD2")
    add("R15", "1k", "Device:R", FP_R, {1: "ESPB_RX", 2: "PI_TXD4"}, (95.0, 40.0, 90),
        _sch_pos(), desc="Serie UART Pi TXD4 (GPIO12) -> ESP32-B RX")
    add("R16", "1k", "Device:R", FP_R, {1: "ESPB_TX", 2: "PI_RXD4"}, (98.5, 40.0, 90),
        _sch_pos(), desc="Serie UART ESP32-B TX -> Pi RXD4 (GPIO13)")

    # ======================= Medicion de bateria (orilla derecha) ===========
    add("J2", "BAT SENSE (12V)", "Connector:Screw_Terminal_01x02", FP_TB2,
        {1: "GND", 2: "VBAT_F"}, (BOARD_W - 5.6, 34.0, 90), _sch_pos(),
        desc="Derivacion de bateria despues del fusible (solo medicion y LED, < 10 mA)",
        mpn="Phoenix MKDS 1,5/2-5,08 o KF301-2P")
    add("R22", "100k", "Device:R", FP_R, {1: "VBAT_F", 2: "VBAT_SENSE"}, (104.0, 20.0, 0),
        _sch_pos(), desc="Divisor VBAT (alto)")
    add("R23", "27k", "Device:R", FP_R, {1: "VBAT_SENSE", 2: "GND"}, (104.0, 24.0, 0),
        _sch_pos(), desc="Divisor VBAT (bajo)")
    add("C5", "100nF", "Device:C", FP_C, {1: "VBAT_SENSE", 2: "GND"}, (104.0, 28.0, 0),
        _sch_pos(), desc="Filtro ADC VBAT")
    add("R24", "2.2k", "Device:R", FP_R, {1: "VBAT_F", 2: "LED12_A"}, (104.0, 15.6, 0),
        _sch_pos(), desc="Resistencia LED 12V")
    add("D2", "LED rojo 12V", "Device:LED", FP_LED, {1: "GND", 2: "LED12_A"},
        (118.04, 15.6, 180), _sch_pos(), desc="Indicador bateria")

    # ======================= Servos (debajo de la ESP32-B) ==================
    for n in range(1, 9):
        g, d = SERVOS[n]
        add("J%d" % (30 + n), "SERVO%d" % n, "rover:Servo_Header", FP_SERVO,
            {1: "GND", 2: "SERVO_V", 3: "SERVO%d" % n}, (espb_right_x(g), SERVO_Y, 180), _sch_pos(),
            desc="Servo %d - %s (SIG arriba, GND abajo)" % (n, d), mpn="Header macho 1x3 2.54mm")
    add("J6", "SERVO PWR IN (6V)", "Connector:Screw_Terminal_01x02", FP_TB2,
        {1: "GND", 2: "SERVO_V"}, (J6_X, ENC_TB_Y, 0), _sch_pos(),
        desc="Entrada BEC servos 6V", mpn="Phoenix MKDS 1,5/2-5,08 o KF301-2P")
    add("C3", "1000uF 10V", "Device:C_Polarized", FP_CP10, {1: "SERVO_V", 2: "GND"},
        (127.5, 44.5, 0), _sch_pos(), desc="Bulk servos")
    add("C4", "1000uF 10V", "Device:C_Polarized", FP_CP10, {1: "SERVO_V", 2: "GND"},
        (83.0, 89.0, 0), _sch_pos(), desc="Bulk servos")
    add("R26", "470", "Device:R", FP_R, {1: "SERVO_V", 2: "LEDS_A"}, (104.0, 44.0, 0),
        _sch_pos(), desc="Resistencia LED servos")
    add("D4", "LED azul SERVO", "Device:LED", FP_LED, {1: "GND", 2: "LEDS_A"},
        (118.04, 44.0, 180), _sch_pos(), desc="Indicador rail servos")

    # ======================= Agujeros de montaje ============================
    for i, (x, y) in enumerate(CHASSIS_HOLES):
        add("H%d" % (i + 1), "M3", "Mechanical:MountingHole", FP_MH, {}, (x, y, 0), _sch_pos(),
            desc="Agujero de montaje M3")
    return COMPONENTS


SCH_NOTES = [
    (25.4, 20.32, "ROVER CONTROLLER CUBIKO: tarjeta de logica (Pi 5 + 2x ESP32). Los L298N van en el chasis "
                  "y se conectan por bornas; la bateria no entra a la tarjeta (solo J2 para medirla). GND COMUN"),
]


def pcb_labels(silk, at, comps):
    W = BOARD_W
    silk("ROVER CONTROLLER CUBIKO v%s" % REVISION, 40.0, 0.0 + 9.8, 1.2, bold=True)
    for k, ref in enumerate(("U4", "U5", "U6")):
        x, y, _ = at("J%d" % (41 + k))
        ma, mb = 2 * k + 1, 2 * k + 2
        silk("L298N #%d  M%d/M%d" % (k + 1, ma, mb), x + 5.6, y - 2.4, 0.8, rot=0)
        for i, name in enumerate(TB_ORDER):
            silk(name, x + 6.6, y + 3.5 * i, 0.7)
    for ref, x, ms in ENC_TB:
        silk("ENC M%d M%d M%d" % tuple(ms), x + 7.0, ENC_TB_Y - 4.6, 0.8)
        silk("G 5V A%d A%d A%d" % tuple(ms), x + 7.0, ENC_TB_Y - 2.9, 0.65)
    x, y, _ = at("J5")
    silk("5V/5A IN: + -", x - 2.54, y + 6.4, 0.8)
    x, y, _ = at("J6")
    silk("SERVO 6V: - +", x + 2.54, y - 6.4, 0.8)
    x, y, _ = at("J2")
    silk("BAT 12V", x - 7.4, y - 2.5, 0.8, rot=90)
    for n in range(1, 9):
        x, y, _ = at("J%d" % (30 + n))
        silk("S%d" % n, x, y + 2.3, 0.7)
    silk("SIG", min(at("J%d" % (30 + n))[0] for n in range(1, 9)) - 3.4, SERVO_Y - 5.08, 0.7)
    silk("V+", min(at("J%d" % (30 + n))[0] for n in range(1, 9)) - 3.4, SERVO_Y - 2.54, 0.7)
    silk("GND", min(at("J%d" % (30 + n))[0] for n in range(1, 9)) - 3.4, SERVO_Y, 0.7)
    x, y, _ = at("U2")
    silk("ESP32-A TRACCION (USB arriba)", x, y + 29.0, 0.9, bold=True)
    x, y, _ = at("U3")
    silk("ESP32-B SERVOS (USB izq)", x + 2.0, y - 16.0, 0.9, bold=True)
    silk("ENC 5V->3V3", 60.0, 55.0, 0.7)
