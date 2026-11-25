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
from rover_split_comun import FP_TB3, FP_TB2, MPN_TB2
FP_RV = "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P2.54mm_Vertical"   # de pie: entra entre la ESP32 y J9

PROJECT = "rover_servos"
REVISION = "2.0-S"
TITLE = "Rover - tarjeta de SERVOS (ESP32-B, 8 servos, bateria)"

BOARD_W = 76.0
BOARD_H = 96.0

ESPB_POS = (31.0, 59.0, 270)          # horizontal, USB a la izquierda: fila IO23.. mira a los servos
ESPB_RIGHT_Y = ESPB_POS[1] + 12.7
SERVO_Y = ESPB_RIGHT_Y + 16.3         # pad GND de cada header (SIG queda 5.08 arriba)
SERVO_X0, SERVO_PASO = 23.0, 5.08     # headers a 5.08 mm: cada conector de servo con su espacio
J6_POS = (BOARD_W - 5.6, 80.0, 90)    # entrada 6 V en la orilla derecha (pad 1 GND abajo)
PI_TB = (5.0, BOARD_H - 5.0, 0)       # J9 en la orilla inferior izquierda, bajo IO15/IO2
CHASSIS_HOLES = [(3.5, 4.0), (BOARD_W - 3.5, 4.0), (3.5, 72.0), (BOARD_W - 3.5, 52.0)]
ALIGN_HOLES = []


def espb_right_x(name):
    return ESPB_POS[0] + 17.78 - 2.54 * ESP32_RIGHT.index(name)


def servo_x(n):
    """x del header del servo n: en el mismo orden que sus pines, a SERVO_PASO."""
    orden = sorted(range(1, 9), key=lambda k: espb_right_x(SERVOS[k][0]))
    return SERVO_X0 + SERVO_PASO * orden.index(n)


def preroutes():
    out = []
    xs = sorted(servo_x(n) for n in range(1, 9))
    for n in range(1, 9):
        x0, x1 = espb_right_x(SERVOS[n][0]), servo_x(n)
        # baja recto 2.5 mm, se abre en diagonal y llega recto al pad SIG
        out.append(("SERVO%d" % n, [(x0, ESPB_RIGHT_Y), (x0, ESPB_RIGHT_Y + 2.5), (x1, SERVO_Y - 8.5),
                                     (x1, SERVO_Y - 5.08)], 1.0))
    jx, jy, _ = J6_POS
    # 6 V: sube y luego a J6; GND: sigue y luego sube (sin acercarse entre si)
    out.append(("SERVO_V", [(x, SERVO_Y - 2.54) for x in xs] + [(xs[-1] + 3.0, SERVO_Y - 2.54),
                                                            (xs[-1] + 3.0, jy - 5.08), (jx, jy - 5.08)], 1.6))
    out.append(("GND", [(x, SERVO_Y) for x in xs] + [(jx - 4.4, SERVO_Y), (jx, jy)], 1.6))
    return out


ROUTING_FIRST = ["ESPB_TX", "ESPB_RX", "PI_TXD4", "PI_RXD4"] + ["SERVO%d" % n for n in range(1, 9)]
ROUTING_EARLY = {"GND": set(),
                 "SERVO_V": {"J6", "C3", "C4", "J31", "J32", "J33", "J34", "J35", "J36", "J37", "J38"}}


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
    add("U3", "ESP32-B_Servos", "rover:ESP32_DevKitV1_30P", "rover:ESP32_DevKitV1_30P_DualPitch",
        espb, ESPB_POS, _sch_pos(), desc="ESP32 DevKit V1 30 pines sobre 2x header hembra 1x15",
        mpn="ESP32 DevKit V1 + 2x header hembra 1x15")

    add("J9", "PI (UART4)", "Connector:Screw_Terminal_01x03", FP_TB3,
        {1: "GND", 2: "PI_TXD4", 3: "PI_RXD4"}, PI_TB, _sch_pos(),
        desc="Hacia el HAT de bornas de la Pi: 1 GND (pin 34), 2 TXD4 = GPIO12 (pin 32), 3 RXD4 = GPIO13 (pin 33)",
        mpn="Phoenix PT 1,5/3-3,5-H o KF350-3P 3.5mm")
    add("R15", "1k", "Device:R", FP_RV, {1: "ESPB_RX", 2: "PI_TXD4"}, (16.5, 75.0, 270),
        _sch_pos(), desc="Serie UART Pi TXD4 (GPIO12) -> ESP32-B RX")
    add("R16", "1k", "Device:R", FP_RV, {1: "ESPB_TX", 2: "PI_RXD4"}, (20.0, 75.5, 270),
        _sch_pos(), desc="Serie UART ESP32-B TX -> Pi RXD4 (GPIO13)")

    add("J5", "5V IN (buck 5V)", "Connector:Screw_Terminal_01x02", FP_TB2,
        {1: "+5V", 2: "GND"}, (5.6, 20.0, 270), _sch_pos(),
        desc="Entrada 5 V desde el step-down (ESP32-B)", mpn=MPN_TB2)
    add("D6", "1N5819", "Device:D_Schottky", FP_DO41, {1: "VIN_B", 2: "+5V"},
        (13.22, 35.0, 90), _sch_pos(), desc="Schottky +5V -> VIN ESP32-B", mpn="1N5819 DO-41")

    add("J2", "BAT SENSE (12V)", "Connector:Screw_Terminal_01x02", FP_TB2,
        {1: "GND", 2: "VBAT_F"}, (BOARD_W - 5.6, 26.0, 90), _sch_pos(),
        desc="Derivacion de bateria despues del fusible (solo medicion y LED, < 10 mA)", mpn=MPN_TB2)
    add("R22", "100k", "Device:R", FP_R, {1: "VBAT_F", 2: "VBAT_SENSE"}, (34.0, 12.0, 0),
        _sch_pos(), desc="Divisor VBAT (alto)")
    add("R23", "27k", "Device:R", FP_R, {1: "VBAT_SENSE", 2: "GND"}, (34.0, 16.0, 0),
        _sch_pos(), desc="Divisor VBAT (bajo)")
    add("C5", "100nF", "Device:C", FP_C, {1: "VBAT_SENSE", 2: "GND"}, (34.0, 20.0, 0),
        _sch_pos(), desc="Filtro ADC VBAT")
    add("R24", "2.2k", "Device:R", FP_R, {1: "VBAT_F", 2: "LED12_A"}, (34.0, 7.6, 0),
        _sch_pos(), desc="Resistencia LED 12V")
    add("D2", "LED rojo 12V", "Device:LED", FP_LED, {1: "GND", 2: "LED12_A"},
        (48.04, 7.6, 180), _sch_pos(), desc="Indicador bateria")

    for n in range(1, 9):
        g, d = SERVOS[n]
        add("J%d" % (30 + n), "SERVO%d" % n, "rover:Servo_Header", FP_SERVO,
            {1: "GND", 2: "SERVO_V", 3: "SERVO%d" % n}, (servo_x(n), SERVO_Y, 180), _sch_pos(),
            desc="Servo %d - %s (SIG arriba, GND abajo)" % (n, d), mpn="Header macho 1x3 2.54mm")
    add("J6", "SERVO PWR IN (6V)", "Connector:Screw_Terminal_01x02", FP_TB2,
        {1: "GND", 2: "SERVO_V"}, J6_POS, _sch_pos(), desc="Entrada BEC servos 6V", mpn=MPN_TB2)
    add("C3", "1000uF 10V", "Device:C_Polarized", FP_CP10, {1: "SERVO_V", 2: "GND"},
        (62.0, 40.0, 0), _sch_pos(), desc="Bulk servos")
    add("C4", "1000uF 10V", "Device:C_Polarized", FP_CP10, {1: "SERVO_V", 2: "GND"},
        (66.0, 62.0, 0), _sch_pos(), desc="Bulk servos")
    add("R26", "470", "Device:R", FP_R, {1: "SERVO_V", 2: "LEDS_A"}, (57.0, 33.0, 90),
        _sch_pos(), desc="Resistencia LED servos")
    add("D4", "LED azul SERVO", "Device:LED", FP_LED, {1: "GND", 2: "LEDS_A"},
        (51.0, 25.38, 0), _sch_pos(), desc="Indicador rail servos")

    for i, (x, y) in enumerate(CHASSIS_HOLES):
        add("H%d" % (i + 1), "M3", "Mechanical:MountingHole", FP_MH, {}, (x, y, 0), _sch_pos(),
            desc="Agujero de montaje M3")
    return COMPONENTS


def pcb_labels(silk, at, comps):
    silk("ROVER SERVOS v%s" % REVISION, 40.0, 3.0, 1.0, bold=True)
    x, y, _ = at("J5")
    silk("5V IN: + -", x - 2.54, y + 6.4, 0.8)
    x, y, _ = at("J6")
    silk("SERVO 6V: - +", x - 7.4, y - 2.5, 0.8, rot=90)
    x, y, _ = at("J2")
    silk("BAT 12V", x - 7.4, y - 2.5, 0.8, rot=90)
    x, y, _ = at("J9")
    silk("PI: GND TX RX", x + 3.5, y - 4.6, 0.8)
    for n in range(1, 9):
        x, y, _ = at("J%d" % (30 + n))
        silk("S%d" % n, x, y + 2.3, 0.7)
    x, y, _ = at("U3")
    silk("ESP32-B (USB izq)", x + 2.0, y - 16.0, 0.9, bold=True)
