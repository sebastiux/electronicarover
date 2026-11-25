# -*- coding: utf-8 -*-
"""
Rover Controller - definicion unica del diseno (fuente de verdad).

Todo el proyecto KiCad (simbolos, footprints, esquematico y PCB) se genera
a partir de este archivo. Si mides tus modulos y alguna cota no coincide,
corrige los valores de la seccion "GEOMETRIA DE MODULOS" y vuelve a correr:

    python3 hardware/tools/generate.py

Unidades: milimetros. Coordenadas de PCB con origen en la esquina superior
izquierda de la tarjeta, X hacia la derecha, Y hacia abajo (vista superior).
"""

PROJECT = "rover_controller"
REVISION = "1.2"
TITLE = "Rover Controller - RPi5 + 2x ESP32 + 3x L298N"

BOARD_W = 200.0
BOARD_H = 150.0

# ---------------------------------------------------------------------------
# GEOMETRIA DE MODULOS (verificar con calibrador antes de fabricar)
# ---------------------------------------------------------------------------

# Modulo L298N rojo (HW-095), 43 x 43 mm. Origen = centro del modulo,
# disipador hacia arriba (-Y), header logico hacia abajo (+Y).
L298N = {
    # Cotas segun el plano del modulo comprado: 43.90 x 43.90 mm, barrenos a 38.00 mm.
    # Otras fuentes dan 36.6 / 37 / 37.2 mm. Barreno de 4.0 mm centrado a +-18.75:
    # con tornillo M3 acepta cualquier separacion entre 36.5 y 38.5 mm.
    # Solo los 2 barrenos del lado del disipador: el lado de los pines queda fijo por
    # los 13 pines soldados (y ahi los barrenos de 4 mm cortarian la pista MOTOR_EN).
    "size": 43.9,
    "mount_holes": [(-18.75, -18.75), (18.75, -18.75)],
    "mount_drill": 4.0,
    # bornas de motor (se sustituyen por pines), paso 5.0/5.08 mm
    "OUT1": (-17.5, 1.0), "OUT2": (-17.5, 6.0),
    "OUT3": (17.5, 1.0), "OUT4": (17.5, 6.0),
    # borna de potencia de 3 vias
    "+12V": (-13.0, 17.5), "GND": (-8.0, 17.5), "+5V": (-3.0, 17.5),
    # header logico 1x6 (paso 2.54)
    "header_first": (1.55, 18.5),      # posicion de ENA
    "power_drill": 1.3, "power_pad": 2.6,
    "logic_drill": 1.1, "logic_pad": 1.8,
}

# ESP32 DevKit V1 30 pines. Origen = centro entre filas (version 25.4 mm).
# La fila derecha tiene doble juego de pads: 25.4 mm y 22.86 mm entre filas,
# asi sirve para las dos variantes de clones que existen.
ESP32 = {
    "pitch": 2.54,
    "row_left_x": -12.7,
    "row_right_x": 12.7,          # variante ancha (25.4 mm)
    "row_right_alt_x": 10.16,     # variante angosta (22.86 mm)
    "pins_per_side": 15,
    "drill": 1.0, "pad": 1.7,
    "outline": (-14.2, -27.0, 14.2, 24.5),   # x0,y0,x1,y1 (antena arriba, USB abajo)
    "antenna_keepout": (-14.2, -27.0, 14.2, -19.5),
}
ESP32_LEFT = ["EN", "VP/IO36", "VN/IO39", "IO34", "IO35", "IO32", "IO33", "IO25",
              "IO26", "IO27", "IO14", "IO12", "IO13", "GND", "VIN"]
ESP32_RIGHT = ["IO23", "IO22", "TX0/IO1", "RX0/IO3", "IO21", "IO19", "IO18", "IO5",
               "TX2/IO17", "RX2/IO16", "IO4", "IO2", "IO15", "GND", "3V3"]

# Raspberry Pi 5 bajo la PCB (estilo HAT). Origen = esquina sup. izq. del area HAT.
RPI = {
    "hat_w": 65.0, "hat_h": 56.5,
    "pi_w": 85.0, "pi_h": 56.0,
    "holes": [(3.5, 3.5), (61.5, 3.5), (3.5, 52.5), (61.5, 52.5)],
    "hole_drill": 2.75,
    "pin1": (8.37, 4.77),         # fila impar (interior)
    "row_even_y": 2.23,           # fila par (borde)
    "drill": 1.0, "pad": 1.7,
}
RPI_PINS = {
    1: "3V3", 2: "5V", 3: "GPIO2/SDA", 4: "5V", 5: "GPIO3/SCL", 6: "GND",
    7: "GPIO4/TXD2", 8: "GPIO14/TXD0", 9: "GND", 10: "GPIO15/RXD0",
    11: "GPIO17", 12: "GPIO18", 13: "GPIO27", 14: "GND", 15: "GPIO22",
    16: "GPIO23", 17: "3V3", 18: "GPIO24", 19: "GPIO10", 20: "GND",
    21: "GPIO9", 22: "GPIO25", 23: "GPIO11", 24: "GPIO8", 25: "GND",
    26: "GPIO7", 27: "ID_SD", 28: "ID_SC", 29: "GPIO5/RXD2", 30: "GND",
    31: "GPIO6", 32: "GPIO12", 33: "GPIO13", 34: "GND", 35: "GPIO19",
    36: "GPIO16", 37: "GPIO26", 38: "GPIO20", 39: "GND", 40: "GPIO21",
}

# ---------------------------------------------------------------------------
# NET CLASSES
# ---------------------------------------------------------------------------
# PCB de 2 capas (F.Cu arriba, B.Cu abajo).
LAYERS = 2
# FAB = "proto": prototipado por fresado CNC SIN barrenos metalizados, sin mascara
#   ni serigrafia. Cada pad conecta solo por la cara donde se suelda; la cara
#   superior solo lleva pistas de via a via; las vias son pines soldados arriba y
#   abajo (taladro 1.0 mm). El header de la Pi (montado abajo) conecta por ARRIBA.
# FAB = "pro": fabricacion industrial con PTH, mascara y serigrafia.
FAB = "proto"
TOP_SOLDERED = {"U1"}      # componentes montados abajo -> se sueldan (y conectan) arriba


def pad_side(ref):
    if FAB != "proto":
        return "BF"
    return "F" if ref in TOP_SOLDERED else "B"
NETCLASSES = [
    # name, track, clearance, via_d, via_drill, patterns
    ("BATT", 3.0, 0.5, 2.2, 1.0, ["VBAT_IN", "VBAT_F"]),
    ("MOTOR", 2.0, 0.4, 2.2, 1.0, ["M?_A", "M?_B"]),
    ("PWR", 2.0, 0.45, 2.2, 1.0, ["+5V", "SERVO_V"]),
    ("GND", 3.0, 0.45, 2.2, 1.0, ["GND"]),   # retorno de motores: igual que VBAT
]
# vias de 2.2/1.0 mm: en prototipado son un pin soldado arriba y abajo
DEFAULT_CLASS = (0.6, 0.45, 2.2, 1.0)

# ---------------------------------------------------------------------------
# GUIAS DE RUTEO (una capa)
# ---------------------------------------------------------------------------
def routing_reserved():
    """Zonas donde solo pasan senales (clase Default)."""
    out = [(20.0, 66.0, 186.0, 75.5, {"Default"})]          # corredor bajo los L298N
    for cx in L298N_CX:
        out.append((cx - 0.5, L298N_CY + 16.0, cx + 16.5, 66.0, {"Default"}))
    # franjas junto al header de la Pi: solo sus UART y GND (se aceptan nombres de red)
    out.append((147.6, 89.0, 196.0, 94.6, {"PI_TXD0", "PI_RXD0"}))
    out.append((139.0, 99.4, 196.0, 105.0, {"PI_TXD2", "PI_RXD2", "GND"}))
    # orilla derecha: unica salida de la UART de los pines exteriores de la Pi
    out.append((186.0, 62.0, 200.0, 150.0, {"PI_TXD0", "PI_RXD0", "GND"}))
    return out


def preroutes():
    """Pistas trazadas a mano (geometria conocida), en coordenadas de tarjeta:
    lista de (red, [(x, y), ...], ancho).

    Abanico IN1..IN4 de los tres L298N hacia la fila superior de la ESP32-A:
    baja vertical desde el header, corre horizontal en un nivel propio y baja
    vertical al pin. Los niveles estan escalonados para que nada se cruce.
    Tambien el tramo de MOTOR_EN entre modulos (ENB de uno -> ENA del siguiente)."""
    hdr_y = L298N_CY + L298N["header_first"][1]
    ex0 = ESPA_POS[0] - 17.78
    ey = ESPA_POS[1] - 12.7
    out = []
    for k in range(3):
        cx = L298N_CX[k]
        for j in range(1, 5):
            hx = cx + L298N["header_first"][0] + 2.54 * j
            g = ESPA_IN[k][j - 1]
            ex = ex0 + 2.54 * ESP32_RIGHT.index(g)
            if k == 0:
                yl = 68.0 + 1.2 * (4 - j)
            elif k == 1:
                yl = 68.0 + 1.2 * (j - 1)
            else:
                yl = 72.8 + 1.2 * (j - 1)
            out.append(("U%d_IN%d" % (k + 4, j), [(hx, hdr_y), (hx, yl), (ex, yl), (ex, ey)], 0.6))
    # servos: SIG recta desde la ESP32-B, columnas V+ y GND verticales
    sx = ESPB_POS[0] + 25.08
    ys = [esp_pin_y(ESPB_POS, SERVOS[n][0]) for n in range(1, 9)]
    for n in range(1, 9):
        out.append(("SERVO%d" % n, [(ESPB_POS[0] + 12.7, ys[n - 1]), (sx - 5.08, ys[n - 1])], 0.6))
    # columnas partidas en cada pad (KiCad conecta pistas por sus extremos)
    # alimentacion de servos duplicada en las DOS caras (2 x 1.4 mm en paralelo)
    for lay in (("B.Cu", "F.Cu") if FAB != "proto" else ("B.Cu",)):
        out.append(("SERVO_V", [(sx - 2.54, 99.0)] + [(sx - 2.54, y) for y in ys], 1.4, lay))
        out.append(("GND", [(sx + 2.54, 99.0), (sx + 2.54, 101.0), (sx, 103.5)] + [(sx, y) for y in ys], 1.4, lay))
    # salida de la UART0 por los pines exteriores de la Pi (8 y 10): suben, corren
    # a la derecha en niveles distintos y bajan por la orilla a ambos lados del
    # agujero de montaje de la Pi
    px = 135.0 + RPI["pin1"][0]
    py = 93.5 + RPI["row_even_y"]
    p8, p10 = px + 2.54 * 3, px + 2.54 * 4
    if FAB != "proto":   # en prototipado el header de la Pi se conecta por la cara superior
        out.append(("PI_RXD0", [(p10, py), (p10, 93.3), (193.8, 93.3), (193.8, 104.0)], 0.6))
        out.append(("PI_TXD0", [(p8, py), (p8, 91.3), (198.9, 91.3), (198.9, 104.0)], 0.6))
    # prototipado: el pad +5V de cada L298N queda entre los buses de potencia y
    # MOTOR_EN; se le da una via propia para subir a la cara superior
    if FAB == "proto":
        for k in range(3):
            cx = L298N_CX[k]
            px5, py5 = cx + L298N["+5V"][0], L298N_CY + L298N["+5V"][1]
            vx, vy = cx - 1.2, py5 + 0.8
            out.append(("5V_U%d" % (k + 4), [(px5, py5), (vx, vy)], 0.8))
            out.append(("VIA", "5V_U%d" % (k + 4), vx, vy))
    for k in range(2):
        enb = L298N_CX[k] + L298N["header_first"][0] + 2.54 * 5
        ena = L298N_CX[k + 1] + L298N["header_first"][0]
        out.append(("MOTOR_EN", [(enb, hdr_y), (enb, 66.5), (ena, 66.5), (ena, hdr_y)], 0.6))
    return out


# orden de ruteo de senales: primero el abanico ESP32-A -> L298N (planar),
# luego el enable, las UART y el resto; los encoders cruzan con puentes.
ROUTING_FIRST = ["U%d_IN%d" % (u, i) for u in (4, 5, 6) for i in (1, 2, 3, 4)] + \
    ["MOTOR_EN", "PI_TXD2", "PI_RXD2", "ESPA_RX", "ESPA_TX",
     "PI_TXD0", "PI_RXD0", "ESPB_TX", "ESPB_RX",
     "SERVO1", "SERVO2", "SERVO3", "SERVO4", "SERVO5", "SERVO6", "SERVO7", "SERVO8"]
ROUTING_LATE = []

# pads que se rutean en la etapa de potencia (el resto de la red va al final)
ROUTING_EARLY = {
    "+5V": {"J5", "C2", "D1", "U1"},
    "SERVO_V": {"J6", "C3", "C4", "J31", "J32", "J33", "J34", "J35", "J36", "J37", "J38"},
}

# ---------------------------------------------------------------------------
# COMPONENTES
# ---------------------------------------------------------------------------
# Cada componente: ref, value, symbol(lib_id), footprint(lib:name),
#                  pins {pin: net | None(NC)}, pcb (x, y, rot), sch (x, y),
#                  extra campos para BOM.

FP_TB2 = "TerminalBlock:TerminalBlock_bornier-2_P5.08mm"
FP_R = "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal"
FP_CP10 = "Capacitor_THT:CP_Radial_D10.0mm_P5.00mm"
FP_CP12 = "Capacitor_THT:CP_Radial_D12.5mm_P5.00mm"
FP_C = "Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm"
FP_LED = "LED_THT:LED_D5.0mm"
FP_TO92 = "Package_TO_SOT_THT:TO-92_Inline_Wide"
FP_DO15 = "Diode_THT:D_DO-15_P10.16mm_Horizontal"
FP_FUSE = "Fuse:Fuseholder_Blade_ATO_Littelfuse_Pudenz_2_Pin"
FP_H1x3 = "Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical"
FP_H1x4 = "Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical"
FP_H1x6 = "Connector_PinHeader_2.54mm:PinHeader_1x06_P2.54mm_Vertical"
FP_H1x8 = "Connector_PinHeader_2.54mm:PinHeader_1x08_P2.54mm_Vertical"
FP_MH = "MountingHole:MountingHole_3.2mm_M3"
FP_XT60 = "Connector_AMASS:AMASS_XT60-M_1x02_P7.20mm_Vertical"
FP_SERVO = "rover:Servo_Header_1x03"
FP_C25 = "Capacitor_THT:C_Disc_D3.0mm_W1.6mm_P2.50mm"
FP_DO41 = "Diode_THT:D_DO-41_SOD81_P10.16mm_Horizontal"

COMPONENTS = []

# Barrenos M3 en las orillas para atornillar la PCB al chasis
# (ademas de los 4 agujeros M2.5 de la Raspberry Pi).
CHASSIS_HOLES = [(4.0, 4.0), (68.0, 4.0), (132.0, 4.0), (196.0, 4.0),
                 (4.0, 45.0), (196.0, 45.0), (4.0, 93.5), (128.0, 146.0)]


def add(ref, value, symbol, footprint, pins, pcb, sch, **kw):
    if symbol == "Device:R":
        kw.setdefault("mpn", "Resistencia %s 1/4W (0.25W) THT pelicula metalica/carbon" % value)
    if symbol == "Device:LED":
        kw.setdefault("mpn", "LED 5mm THT tradicional (%s)" % value.split()[1])
    COMPONENTS.append(dict(ref=ref, value=value, symbol=symbol, footprint=footprint,
                           pins=pins, pcb=pcb, sch=sch, **kw))


# ---- L298N: centros en la PCB --------------------------------------------
L298N_CX = [36.0, 100.0, 164.0]
L298N_CY = 46.0

# ---- Mapeo de motores ------------------------------------------------------
# Ux -> (motor lado A (OUT1/OUT2), motor lado B (OUT3/OUT4))
MOTORS = {
    1: "Delantero Izq", 2: "Delantero Der",
    3: "Medio Izq", 4: "Medio Der",
    5: "Trasero Izq", 6: "Trasero Der",
}

# ---------------------------------------------------------------------------
# ASIGNACION DE PINES (pensada para UNA capa: el orden fisico de los pines
# coincide con el orden de los destinos, asi las pistas no se cruzan)
# ---------------------------------------------------------------------------
# ESP32-A (traccion) va HORIZONTAL bajo los L298N: su fila superior (IO23..3V3)
# mira a los headers logicos y los IN1..IN4 bajan "en abanico" sin cruzarse.
ESPA_IN = {  # indice L298N -> [IN1, IN2, IN3, IN4]
    0: ["IO23", "IO22", "TX0/IO1", "IO21"],
    1: ["IO19", "IO18", "IO5", "TX2/IO17"],
    2: ["RX2/IO16", "IO4", "IO2", "IO15"],
}
ESPA_ENC = {1: "VP/IO36", 2: "VN/IO39", 3: "IO34", 4: "IO35", 5: "IO32", 6: "IO33"}
ESPA_UART_RX = "IO14"
ESPA_UART_TX = "IO27"
ESPA_MOTOR_EN = "IO13"

# ESP32-B (servos) va vertical a la izquierda; cada header de servo queda a la
# MISMA altura que su GPIO (pista recta).
SERVOS = {  # n -> (gpio, descripcion)
    1: ("IO23", "Direccion DI"), 2: ("IO22", "Direccion DD"),
    3: ("IO21", "Direccion TI"), 4: ("IO19", "Direccion TD"),
    5: ("IO18", "Brazo base"), 6: ("TX2/IO17", "Brazo hombro"),
    7: ("RX2/IO16", "Brazo pinza"), 8: ("IO4", "Brazo codo/muneca"),
}
ESPB_UART_TX = "IO2"
ESPB_UART_RX = "IO15"
ESPB_VBAT = "IO34"

ESPA_POS = (98.0, 96.7, 90)     # horizontal: antena a la izquierda, USB a la derecha
ESPB_POS = (22.0, 124.0, 0)     # vertical: antena arriba, USB abajo


def esp_pin_number(name):
    if name in ESP32_LEFT:
        return ESP32_LEFT.index(name) + 1
    return ESP32_RIGHT.index(name) + 16


def esp_pin_y(pos, name):
    """Y de un pin de la fila derecha de una ESP32 vertical (rot 0)."""
    i = ESP32_RIGHT.index(name)
    return pos[1] - 17.78 + 2.54 * i


def build():
    COMPONENTS.clear()
    # ======================= RASPBERRY PI 5 =================================
    pi = {n: None for n in range(1, 41)}
    for n in (2, 4):
        pi[n] = "+5V"
    for n in (9, 25, 39):                 # GND de la fila interior (el resto esta unido dentro de la Pi)
        pi[n] = "GND"
    pi[7] = "PI_TXD2"      # UART2 -> ESP32-A (fila interior)
    pi[29] = "PI_RXD2"
    pi[8] = "PI_TXD0"      # UART0 -> ESP32-B (fila exterior)
    pi[10] = "PI_RXD0"
    add("U1", "RaspberryPi5_GPIO", "rover:RaspberryPi5_GPIO", "rover:RPi5_HAT_Header_2x20",
        pi, (135.0, 93.5, 0), (190.5, 76.2),
        desc="Header hembra 2x20 en la cara inferior (Pi 5 debajo); o stacking header para acceder a los GPIO por arriba",
        mpn="Header hembra 2x20 2.54mm (o stacking header 2x20)")

    # ======================= ESP32-A (traccion) =============================
    espa = {i: None for i in range(1, 31)}
    espa[esp_pin_number("VIN")] = "VIN_A"     # via diodo D5 (evita retroalimentar por USB)
    espa[14] = "GND"
    espa[29] = "GND"
    for k, gp in ESPA_IN.items():
        for j, g in enumerate(gp):
            espa[esp_pin_number(g)] = "U%d_IN%d" % (k + 4, j + 1)
    for m, g in ESPA_ENC.items():
        espa[esp_pin_number(g)] = "ENC%d_A" % m
    espa[esp_pin_number(ESPA_MOTOR_EN)] = "MOTOR_EN"
    espa[esp_pin_number(ESPA_UART_TX)] = "ESPA_TX"
    espa[esp_pin_number(ESPA_UART_RX)] = "ESPA_RX"
    add("U2", "ESP32-A_Traccion", "rover:ESP32_DevKitV1_30P", "rover:ESP32_DevKitV1_30P_DualPitch",
        espa, ESPA_POS, (330.2, 76.2),
        desc="ESP32 DevKit V1 30 pines sobre 2x header hembra 1x15",
        mpn="ESP32 DevKit V1 CP2102 + 2x header hembra 1x15")

    # ======================= ESP32-B (servos) ===============================
    espb = {i: None for i in range(1, 31)}
    espb[esp_pin_number("VIN")] = "VIN_B"     # via diodo D6
    espb[14] = "GND"
    espb[29] = "GND"
    for n, (g, _) in SERVOS.items():
        espb[esp_pin_number(g)] = "SERVO%d" % n
    espb[esp_pin_number(ESPB_VBAT)] = "VBAT_SENSE"
    espb[esp_pin_number(ESPB_UART_TX)] = "ESPB_TX"
    espb[esp_pin_number(ESPB_UART_RX)] = "ESPB_RX"
    add("U3", "ESP32-B_Servos", "rover:ESP32_DevKitV1_30P", "rover:ESP32_DevKitV1_30P_DualPitch",
        espb, ESPB_POS, (457.2, 76.2),
        desc="ESP32 DevKit V1 30 pines sobre 2x header hembra 1x15",
        mpn="ESP32 DevKit V1 CP2102 + 2x header hembra 1x15")

    # ======================= L298N x3 + motores =============================
    for k in range(3):
        ref = "U%d" % (k + 4)
        ma, mb = 2 * k + 1, 2 * k + 2
        v5 = "5V_%s" % ref   # regulador 78M05 del propio modulo -> encoders
        pins = {1: "M%d_A" % ma, 2: "M%d_B" % ma, 3: "M%d_A" % mb, 4: "M%d_B" % mb,
                5: "VBAT_F", 6: "GND", 7: v5,
                8: "MOTOR_EN", 9: "%s_IN1" % ref, 10: "%s_IN2" % ref,
                11: "%s_IN3" % ref, 12: "%s_IN4" % ref, 13: "MOTOR_EN"}
        cx = L298N_CX[k]
        add(ref, "L298N_Module", "rover:L298N_Module", "rover:L298N_Module_Pins",
            pins, (cx, L298N_CY, 0), (38.1 + 101.6 * k, 241.3),
            desc="Modulo L298N (bornas sustituidas por pines, quitar jumpers ENA/ENB, "
                 "dejar el jumper 5V-EN: su +5V alimenta los encoders)",
            mpn="Modulo puente H L298N (HW-095)")
        for side, m in (("A", ma), ("B", mb)):
            if side == "A":
                tb_x, hd_x, hd_rot = cx - 17.0, cx - 17.0, -90
                tb_pins = {1: "M%d_A" % m, 2: "M%d_B" % m}
            else:
                tb_x, hd_x, hd_rot = cx + 22.08, cx + 17.0, 90
                tb_pins = {1: "M%d_B" % m, 2: "M%d_A" % m}
            add("J%d" % (10 + m), "Motor M%d" % m, "Connector:Screw_Terminal_01x02", FP_TB2,
                tb_pins, (tb_x, 6.0, 180),
                (38.1 + 101.6 * k + (0 if side == "A" else 50.8), 304.8),
                side=side, desc="Bornera 2P 5.08mm motor M%d (%s)" % (m, MOTORS[m]),
                mpn="KF301-2P / DG301 5.08mm")
            add("J%d" % (20 + m), "Pololu37D_M%d" % m, "rover:Pololu_37D_Encoder", FP_H1x6,
                {1: "M%d_A" % m, 2: "M%d_B" % m, 3: "GND", 4: v5, 5: "ENC%d_A5V" % m, 6: None},
                (hd_x, 16.0, hd_rot),
                (38.1 + 101.6 * k + (0 if side == "A" else 50.8), 335.28),
                side=side, desc="Header 1x6 macho: cable Pololu 37D (M+, M-, GND, VCC, A, B)",
                mpn="Header macho 1x6 2.54mm")

    # ======================= Divisores de encoder (bajo la ESP32-A) =========
    DIV_X0, DIV_PITCH = (70.0, 10.0) if FAB == "proto" else (76.0, 8.0)
    for m in range(1, 7):
        x = DIV_X0 + DIV_PITCH * (m - 1)
        add("R%d" % m, "10k", "Device:R", FP_R,
            {1: "ENC%d_A5V" % m, 2: "ENC%d_A" % m}, (x, 125.62, 90),
            (20.32 + 25.4 * (m - 1), 391.16), desc="Divisor encoder (serie)")
        add("R%d" % (m + 6), "20k", "Device:R", FP_R,
            {1: "ENC%d_A" % m, 2: "GND"}, (x + 4.0, 118.0, -90),
            (30.48 + 25.4 * (m - 1), 391.16), desc="Divisor encoder (a GND)")

    # filtro RC del encoder: 1 nF del nodo ENCx_A a GND (con el 10k forma ~16 us)
    for m in range(1, 7):
        x = DIV_X0 + DIV_PITCH * (m - 1)
        add("C%d" % (10 + m), "1nF", "Device:C", FP_C25,
            {1: "ENC%d_A" % m, 2: "GND"}, (x, 114.5, 0),
            (25.4 * (m - 1) + 22.86, 406.4), desc="Filtro de ruido encoder M%d" % m)

    # diodos Schottky en el VIN de cada ESP32: con el USB conectado a la PC no se
    # retroalimenta el +5V de la Pi (ni el USB desde el regulador)
    add("D5", "1N5819", "Device:D_Schottky", FP_DO41, {1: "VIN_A", 2: "+5V"},
        ((125.0, 131.0, 0) if FAB == "proto" else (106.0, 131.0, 0)), (365.76, 205.74),
        desc="Schottky +5V -> VIN ESP32-A", mpn="1N5819 DO-41")
    add("D6", "1N5819", "Device:D_Schottky", FP_DO41, {1: "VIN_B", 2: "+5V"},
        (40.0, 146.0, 0), (391.16, 205.74), desc="Schottky +5V -> VIN ESP32-B", mpn="1N5819 DO-41")

    # ======================= UART Pi <-> ESP32 (1k en serie) ===============
    add("R13", "1k", "Device:R", FP_R, {1: "PI_TXD2", 2: "ESPA_RX"}, ((144.62, 108.0, 180) if FAB == "proto" else (131.62, 113.0, 180)),
        (190.5, 175.26), desc="Serie UART Pi TXD2 -> ESP32-A RX")
    add("R14", "1k", "Device:R", FP_R, {1: "ESPA_TX", 2: "PI_RXD2"}, ((137.0, 112.0, 0) if FAB == "proto" else (124.0, 116.5, 0)),
        (200.66, 175.26), desc="Serie UART ESP32-A TX -> Pi RXD2")
    add("R15", "1k", "Device:R", FP_R, {1: "PI_TXD0", 2: "ESPB_RX"}, (62.0, 137.0, -90),
        (210.82, 175.26), desc="Serie UART Pi TXD0 -> ESP32-B RX")
    add("R16", "1k", "Device:R", FP_R, {1: "ESPB_TX", 2: "PI_RXD0"}, (66.0, 137.0, -90),
        (220.98, 175.26), desc="Serie UART ESP32-B TX -> Pi RXD0")

    # ======================= MOTOR_EN pull-down =============================
    add("R21", "10k", "Device:R", FP_R, {1: "MOTOR_EN", 2: "GND"}, (126.0, 102.5, -90),
        (365.76, 175.26), desc="Pull-down MOTOR_EN (motores apagados durante el arranque)")

    # ======================= Alimentacion 12V ===============================
    # XT60 macho vertical (soldar las copas en barrenos de 4.5 mm). La bateria
    # Gens Ace 3S trae XT60 hembra. Convencion XT60: lado RECTO = (+),
    # lado BISELADO = (-). En el footprint AMASS el pad 1 es el lado biselado.
    add("J1", "XT60 BAT 12V", "rover:XT60_Battery", FP_XT60,
        {1: "GND", 2: "VBAT_IN"}, (7.0, 78.0, -90), (25.4, 50.8),
        desc="Conector XT60 macho para bateria LiPo 3S (lado biselado = -)",
        mpn="AMASS XT60 macho (copas para soldar) / XT60-M")
    add("F1", "ATO 15A", "Device:Fuse", FP_FUSE, {1: "VBAT_IN", 2: "VBAT_F"},
        (18.0, 81.0, 0), (55.88, 50.8), desc="Portafusible ATO para PCB + fusible 15A",
        mpn="Littelfuse/Pudenz 2 pin ATO holder")
    add("C1", "1000uF 25V", "Device:C_Polarized", FP_CP12, {1: "VBAT_F", 2: "GND"},
        (43.0, 81.0, 180), (116.84, 55.88), desc="Bulk VBAT")
    add("J3", "12V OUT -> buck 5V", "Connector:Screw_Terminal_01x02", FP_TB2,
        {1: "GND", 2: "VBAT_F"}, (51.0, 80.0, 0), (86.36, 50.8),
        desc="Salida 12V protegida hacia el step-down de 5V/5A", mpn="KF301-2P 5.08mm")
    add("J4", "12V OUT -> BEC servos", "Connector:Screw_Terminal_01x02", FP_TB2,
        {1: "VBAT_F", 2: "GND"}, (62.0, 80.0, 0), (86.36, 68.58),
        desc="Salida 12V protegida hacia el BEC de servos 6V", mpn="KF301-2P 5.08mm")
    add("R22", "100k", "Device:R", FP_R, {1: "VBAT_F", 2: "VBAT_SENSE"}, (13.0, 90.0, 0),
        (497.84, 175.26), desc="Divisor VBAT (alto)")
    add("R23", "27k", "Device:R", FP_R, {1: "VBAT_SENSE", 2: "GND"}, (13.0, 93.5, 0),
        (497.84, 198.12), desc="Divisor VBAT (bajo)")
    add("C5", "100nF", "Device:C", FP_C, {1: "VBAT_SENSE", 2: "GND"}, (24.0, 92.0, 0),
        (510.54, 198.12), desc="Filtro ADC VBAT")
    add("R24", "2.2k", "Device:R", FP_R, {1: "VBAT_F", 2: "LED12_A"}, (52.0, 88.0, 0),
        (139.7, 48.26), desc="Resistencia LED 12V")
    add("D2", "LED rojo 12V", "Device:LED", FP_LED, {1: "GND", 2: "LED12_A"},
        (65.54, 88.0, 180), (139.7, 60.96), desc="Indicador 12V")

    # ======================= Alimentacion 5V ================================
    add("J5", "5V IN (buck 5V 5A)", "Connector:Screw_Terminal_01x02", FP_TB2,
        {1: "+5V", 2: "GND"}, (129.0, 86.08, 90), (25.4, 101.6),
        desc="Entrada 5V/5A desde step-down (alimenta Pi 5 y ESP32)",
        mpn="KF301-2P 5.08mm")
    add("C2", "1000uF 10V", "Device:C_Polarized", FP_CP10, {1: "+5V", 2: "GND"},
        (136.0, 82.0, 0), (55.88, 106.68), desc="Bulk 5V")
    add("D1", "SA5.0A", "Device:D_Zener", FP_DO15, {1: "+5V", 2: "GND"},
        (147.0, 84.0, 0), (76.2, 106.68), desc="TVS 5V (proteccion Pi)", mpn="SA5.0A DO-15")
    add("R25", "330", "Device:R", FP_R, {1: "+5V", 2: "LED5_A"}, (163.0, 84.0, 0),
        (101.6, 99.06), desc="Resistencia LED 5V")
    add("D3", "LED verde 5V", "Device:LED", FP_LED, {1: "GND", 2: "LED5_A"},
        (176.54, 84.0, 180), (101.6, 111.76), desc="Indicador 5V")

    # ======================= Servos (junto a la ESP32-B) ====================
    sx = ESPB_POS[0] + 25.08     # x del pad GND de cada header (SIG queda 5.08 a la izquierda)
    for n in range(1, 9):
        g, d = SERVOS[n]
        add("J%d" % (30 + n), "SERVO%d" % n, "rover:Servo_Header", FP_SERVO,
            {1: "GND", 2: "SERVO_V", 3: "SERVO%d" % n},
            (sx, esp_pin_y(ESPB_POS, g), -90), (330.2 + 30.48 * (n - 1), 391.16),
            desc="Servo %d - %s (GND, V+, SIG)" % (n, d), mpn="Header macho 1x3 2.54mm")
    add("J6", "SERVO PWR IN (6V)", "Connector:Screw_Terminal_01x02", FP_TB2,
        {1: "GND", 2: "SERVO_V"}, (sx + 2.54, 99.0, 180), (25.4, 139.7),
        desc="Entrada BEC servos 6V", mpn="KF301-2P 5.08mm")
    add("C3", "1000uF 10V", "Device:C_Polarized", FP_CP10, {1: "SERVO_V", 2: "GND"},
        (sx + 5.0, 111.0, 0), (55.88, 144.78), desc="Bulk servos")
    add("C4", "1000uF 10V", "Device:C_Polarized", FP_CP10, {1: "SERVO_V", 2: "GND"},
        (sx + 5.0, 123.0, 0), (66.04, 144.78), desc="Bulk servos")
    add("R26", "470", "Device:R", FP_R, {1: "SERVO_V", 2: "LEDS_A"}, (sx + 5.0, 131.0, 0),
        (101.6, 137.16), desc="Resistencia LED servos")
    add("D4", "LED azul SERVO", "Device:LED", FP_LED, {1: "GND", 2: "LEDS_A"},
        (sx + 19.54, 131.0, 180), (101.6, 149.86), desc="Indicador rail servos")

    # ======================= Agujeros de montaje ============================
    for i, (x, y) in enumerate(CHASSIS_HOLES):
        add("H%d" % (i + 1), "M3", "Mechanical:MountingHole", FP_MH, {}, (x, y, 0),
            (543.56 + 12.7 * i, 25.4), desc="Agujero de montaje M3")
    return COMPONENTS



SCH_NOTES = [
    (20.32, 30.48, "ALIMENTACION: Bateria 3S por XT60 -> fusible 15A -> L298N + salidas a step-down 5V/5A y BEC 6V. GND COMUN"),
    (170.18, 40.64, "RASPBERRY PI 5 (debajo de la PCB, header hembra 2x20)"),
    (304.8, 50.8, "ESP32-A: TRACCION (6 motores, 6 encoders canal A, MOTOR_EN)"),
    (431.8, 50.8, "ESP32-B: SERVOS (4 direccion + 3 brazo + 1 reserva), VBAT, UART"),
    (170.18, 165.1, "UART Pi<->ESP32 con 1k en serie (UART2->ESP32-A, UART0->ESP32-B)"),
    (20.32, 220.98, "PUENTES H L298N (ENA/ENB = MOTOR_EN, quitar jumpers ENA/ENB; el +5V del modulo alimenta los encoders)"),
    (20.32, 292.1, "CONECTORES DE MOTOR: bornera 2P + header 1x6 compatible con cable Pololu 37D"),
    (20.32, 378.46, "DIVISORES DE ENCODER 5V -> 3.3V (10k / 20k)"),
    (320.04, 378.46, "SERVOS (Power HD 1501MG) - rail SERVO_V 6V independiente"),
]


def pcb_labels(silk, at, comps):
    """Textos de serigrafia (posiciones en funcion de los componentes)."""
    silk("ROVER CONTROLLER v%s  -  RPi5 + 2xESP32 + 3xL298N  -  %d CAPAS" % (REVISION, LAYERS), 100, 21.0, 1.4, bold=True)
    for m in range(1, 7):
        c = next(cc for cc in comps if cc["ref"] == "J%d" % (10 + m))
        x = c["pcb"][0] - 2.54
        silk("M%d %s" % (m, MOTORS[m]), x, 11.6, 0.9)
        side = c.get("side", "A")
        silk("M-  M+" if side == "A" else "M+  M-", x, 1.4, 0.8)
        h = next(cc for cc in comps if cc["ref"] == "J%d" % (20 + m))
        if side == "A":
            silk("B A V G - +", h["pcb"][0] - 6.35, 18.7, 0.7)
        else:
            silk("+ - G V A B", h["pcb"][0] + 6.35, 18.7, 0.7)
    # polaridad / etiquetas (posiciones en funcion de rover_design)
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
    silk("ESP32-B SERVOS", x, y - 23.3, 1.0, bold=True)
    silk("ENCODERS 5V->3V3", 98.0, 125.6, 0.8)


def nets():
    s = set()
    for c in COMPONENTS:
        for n in c["pins"].values():
            if n:
                s.add(n)
    return sorted(s)


# ---------------------------------------------------------------------------
# VARIANTES: ROVER_VARIANT=cubiko -> tarjeta chica para fresar en la Genmitsu
# Cubiko (L298N fuera de la tarjeta, bornas en las orillas). Ver rover_cubiko.py
# ---------------------------------------------------------------------------
import os as _os
VARIANT = _os.environ.get("ROVER_VARIANT", "v1.2")
if VARIANT == "cubiko":
    from rover_cubiko import *  # noqa: E402,F401,F403
elif VARIANT == "traccion":
    from rover_traccion import *  # noqa: E402,F401,F403
elif VARIANT == "servos":
    from rover_servos import *  # noqa: E402,F401,F403
