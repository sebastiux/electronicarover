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
REVISION = "1.0"
TITLE = "Rover Controller - RPi5 + 2x ESP32 + 3x L298N"

BOARD_W = 200.0
BOARD_H = 150.0

# ---------------------------------------------------------------------------
# GEOMETRIA DE MODULOS (verificar con calibrador antes de fabricar)
# ---------------------------------------------------------------------------

# Modulo L298N rojo (HW-095), 43 x 43 mm. Origen = centro del modulo,
# disipador hacia arriba (-Y), header logico hacia abajo (+Y).
L298N = {
    "size": 43.0,
    "mount_holes": [(-18.3, -18.3), (18.3, -18.3), (-18.3, 18.3), (18.3, 18.3)],
    "mount_drill": 3.2,
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
# PCB de UNA capa (cobre solo en B.Cu): pistas anchas y holguras generosas,
# aptas para fabricacion casera (planchado/CNC) o comercial.
# Las "vias" son los barrenos de los puentes de alambre (pad 2.0 / taladro 1.0).
NETCLASSES = [
    # name, track, clearance, via_d, via_drill, patterns
    ("BATT", 3.0, 0.5, 2.0, 1.0, ["VBAT_IN", "VBAT_F"]),
    ("MOTOR", 2.0, 0.4, 2.0, 1.0, ["M?_A", "M?_B"]),
    ("PWR", 2.0, 0.4, 2.0, 1.0, ["+5V", "SERVO_V"]),
    ("GND", 1.5, 0.4, 2.0, 1.0, ["GND"]),
]
DEFAULT_CLASS = (0.6, 0.4, 2.0, 1.0)

# ---------------------------------------------------------------------------
# GUIAS DE RUTEO (una capa)
# ---------------------------------------------------------------------------
def routing_reserved():
    """Corredor de senales bajo los headers logicos de los L298N: ahi no pasan
    pistas de potencia, para que la ESP32-A llegue a IN1..IN4/ENA/ENB."""
    out = [(20.0, 66.0, 186.0, 75.5, {"Default"})]
    for cx in L298N_CX:
        out.append((cx - 0.5, L298N_CY + 16.0, cx + 16.5, 66.0, {"Default"}))
    return out


# pads que se rutean en la etapa de potencia (el resto de la red va al final)
ROUTING_EARLY = {
    "+5V": {"J5", "C2", "D1", "U1"},
    "SERVO_V": {"J6", "J7", "C3", "C4", "J31", "J32", "J33", "J34", "J35", "J36", "J37", "J38"},
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

COMPONENTS = []

# Barrenos M3 en las orillas para atornillar la PCB al chasis
# (ademas de los 4 agujeros M2.5 de la Raspberry Pi).
CHASSIS_HOLES = [(4.0, 4.0), (68.0, 4.0), (132.0, 4.0), (196.0, 4.0),
                 (4.0, 45.0), (196.0, 45.0), (4.0, 146.0), (128.0, 146.5)]


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

# ESP32-A (traccion): pines de control de cada L298N
ESPA_IN = {  # (L298N index) -> [IN1, IN2, IN3, IN4] GPIO
    0: ["IO32", "IO33", "IO25", "IO26"],
    1: ["IO27", "IO13", "IO23", "IO22"],
    2: ["IO21", "IO19", "IO18", "IO5"],
}
ESPA_ENC = {1: "VP/IO36", 2: "VN/IO39", 3: "IO34", 4: "IO35", 5: "IO14", 6: "IO4"}

# ESP32-B (servos + brazo)
SERVOS = {  # n -> (gpio, descripcion)
    1: ("IO32", "Direccion DI"), 2: ("IO33", "Direccion DD"),
    3: ("IO25", "Direccion TI"), 4: ("IO26", "Direccion TD"),
    5: ("IO27", "Brazo base"), 6: ("IO13", "Brazo hombro"),
    7: ("IO23", "Brazo pinza"), 8: ("IO4", "Reserva"),
}


def esp_pin_number(name):
    if name in ESP32_LEFT:
        return ESP32_LEFT.index(name) + 1
    return ESP32_RIGHT.index(name) + 16


def build():
    COMPONENTS.clear()
    # ======================= RASPBERRY PI 5 =================================
    pi = {n: None for n in range(1, 41)}
    for n, name in RPI_PINS.items():
        if name == "GND":
            pi[n] = "GND"
        elif name == "5V":
            pi[n] = "+5V"
        elif name == "3V3":
            pi[n] = "+3V3_PI"
    pi[3] = "PI_SDA"
    pi[5] = "PI_SCL"
    pi[8] = "PI_TXD0"
    pi[10] = "PI_RXD0"
    pi[7] = "PI_TXD2"
    pi[29] = "PI_RXD2"
    pi[11] = "PI_RST_A"
    pi[13] = "PI_RST_B"
    pi[15] = "PI_GPIO22"
    pi[16] = "PI_GPIO23"
    pi[18] = "PI_GPIO24"
    pi[22] = "PI_GPIO25"
    add("U1", "RaspberryPi5_GPIO", "rover:RaspberryPi5_GPIO", "rover:RPi5_HAT_Header_2x20",
        pi, (135.0, 93.5, 0), (190.5, 76.2),
        desc="Header hembra 2x20 (montar en cara INFERIOR, Pi 5 debajo)",
        mpn="Header hembra 2x20 2.54mm (o stacking header 2x20)")

    # ======================= ESP32-A (traccion) =============================
    espa = {i: None for i in range(1, 31)}
    espa[esp_pin_number("EN")] = "ESPA_EN"
    espa[esp_pin_number("VIN")] = "+5V"
    espa[14] = "GND"
    espa[29] = "GND"
    espa[esp_pin_number("3V3")] = "+3V3_A"
    for k, gp in ESPA_IN.items():
        for j, g in enumerate(gp):
            espa[esp_pin_number(g)] = "U%d_IN%d" % (k + 4, j + 1)
    for m, g in ESPA_ENC.items():
        espa[esp_pin_number(g)] = "ENC%d_A" % m
    espa[esp_pin_number("IO12")] = "MOTOR_EN"
    espa[esp_pin_number("TX2/IO17")] = "ESPA_TX"
    espa[esp_pin_number("RX2/IO16")] = "ESPA_RX"
    espa[esp_pin_number("IO2")] = "AUXA_IO2"
    espa[esp_pin_number("IO15")] = "AUXA_IO15"
    add("U2", "ESP32-A_Traccion", "rover:ESP32_DevKitV1_30P", "rover:ESP32_DevKitV1_30P_DualPitch",
        espa, (42.0, 124.0, 0), (330.2, 76.2),
        desc="ESP32 DevKit V1 30 pines sobre 2x header hembra 1x15",
        mpn="ESP32 DevKit V1 CP2102 + 2x header hembra 1x15")

    # ======================= ESP32-B (servos) ===============================
    espb = {i: None for i in range(1, 31)}
    espb[esp_pin_number("EN")] = "ESPB_EN"
    espb[esp_pin_number("VIN")] = "+5V"
    espb[14] = "GND"
    espb[29] = "GND"
    espb[esp_pin_number("3V3")] = "+3V3_B"
    for n, (g, _) in SERVOS.items():
        espb[esp_pin_number(g)] = "SERVO%d" % n
    espb[esp_pin_number("IO34")] = "VBAT_SENSE"
    espb[esp_pin_number("TX2/IO17")] = "ESPB_TX"
    espb[esp_pin_number("RX2/IO16")] = "ESPB_RX"
    espb[esp_pin_number("IO21")] = "AUXB_SDA"
    espb[esp_pin_number("IO22")] = "AUXB_SCL"
    espb[esp_pin_number("IO18")] = "AUXB_IO18"
    espb[esp_pin_number("IO19")] = "AUXB_IO19"
    espb[esp_pin_number("IO35")] = "AUXB_IO35"
    espb[esp_pin_number("VN/IO39")] = "AUXB_IO39"
    add("U3", "ESP32-B_Servos", "rover:ESP32_DevKitV1_30P", "rover:ESP32_DevKitV1_30P_DualPitch",
        espb, (106.0, 124.0, 0), (457.2, 76.2),
        desc="ESP32 DevKit V1 30 pines sobre 2x header hembra 1x15",
        mpn="ESP32 DevKit V1 CP2102 + 2x header hembra 1x15")

    # ======================= L298N x3 + motores =============================
    for k in range(3):
        ref = "U%d" % (k + 4)
        ma, mb = 2 * k + 1, 2 * k + 2
        pins = {1: "M%d_A" % ma, 2: "M%d_B" % ma, 3: "M%d_A" % mb, 4: "M%d_B" % mb,
                5: "VBAT_F", 6: "GND", 7: None,
                8: "MOTOR_EN", 9: "%s_IN1" % ref, 10: "%s_IN2" % ref,
                11: "%s_IN3" % ref, 12: "%s_IN4" % ref, 13: "MOTOR_EN"}
        cx = L298N_CX[k]
        add(ref, "L298N_Module", "rover:L298N_Module", "rover:L298N_Module_Pins",
            pins, (cx, L298N_CY, 0), (38.1 + 101.6 * k, 241.3),
            desc="Modulo L298N (bornas sustituidas por pines, quitar jumpers ENA/ENB)",
            mpn="Modulo puente H L298N (HW-095)")
        # conectores por motor
        for side, m in (("A", ma), ("B", mb)):
            # Una sola capa: los pines de motor del header y de la bornera quedan
            # alineados sobre OUT1/OUT3 para no cruzar las lineas del encoder.
            if side == "A":
                tb_x, hd_x, hd_rot = cx - 17.0, cx - 17.0, -90
                tb_pins = {1: "M%d_A" % m, 2: "M%d_B" % m}
            else:
                tb_x, hd_x, hd_rot = cx + 22.08, cx + 17.0, 90
                tb_pins = {1: "M%d_B" % m, 2: "M%d_A" % m}
            # bornera (rot 180: entrada de cable hacia el borde superior)
            add("J%d" % (10 + m), "Motor M%d" % m, "Connector:Screw_Terminal_01x02", FP_TB2,
                tb_pins, (tb_x, 6.0, 180),
                (38.1 + 101.6 * k + (0 if side == "A" else 50.8), 304.8),
                side=side, desc="Bornera 2P 5.08mm motor M%d (%s)" % (m, MOTORS[m]),
                mpn="KF301-2P / DG301 5.08mm")
            # header compatible con cable Pololu 37D (rojo, negro, verde, azul, amarillo, blanco)
            add("J%d" % (20 + m), "Pololu37D_M%d" % m, "rover:Pololu_37D_Encoder", FP_H1x6,
                {1: "M%d_A" % m, 2: "M%d_B" % m, 3: "GND", 4: "+5V", 5: "ENC%d_A5V" % m, 6: None},
                (hd_x, 16.0, hd_rot),
                (38.1 + 101.6 * k + (0 if side == "A" else 50.8), 335.28),
                side=side, desc="Header 1x6 macho: cable Pololu 37D (M+, M-, GND, VCC, A, B)",
                mpn="Header macho 1x6 2.54mm")

    # ======================= Divisores de encoder ===========================
    col_x = [60.0, 64.5, 69.0, 73.5, 78.0, 82.5]
    for m in range(1, 7):
        add("R%d" % m, "10k", "Device:R", FP_R,
            {1: "ENC%d_A5V" % m, 2: "ENC%d_A" % m}, (col_x[m - 1], 100.0, -90),
            (20.32 + 25.4 * (m - 1), 391.16), desc="Divisor encoder (serie)")
        add("R%d" % (m + 6), "20k", "Device:R", FP_R,
            {1: "ENC%d_A" % m, 2: "GND"}, (col_x[m - 1], 111.0, -90),
            (30.48 + 25.4 * (m - 1), 391.16), desc="Divisor encoder (a GND)")

    # ======================= UART Pi <-> ESP32 ==============================
    add("R13", "1k", "Device:R", FP_R, {1: "PI_TXD0", 2: "ESPA_RX"}, (col_x[0], 122.0, -90),
        (190.5, 175.26), desc="Serie UART Pi TXD0 -> ESP32-A RX2")
    add("R14", "1k", "Device:R", FP_R, {1: "ESPA_TX", 2: "PI_RXD0"}, (col_x[1], 122.0, -90),
        (200.66, 175.26), desc="Serie UART ESP32-A TX2 -> Pi RXD0")
    add("R15", "1k", "Device:R", FP_R, {1: "PI_TXD2", 2: "ESPB_RX"}, (col_x[2], 122.0, -90),
        (210.82, 175.26), desc="Serie UART Pi TXD2 -> ESP32-B RX2")
    add("R16", "1k", "Device:R", FP_R, {1: "ESPB_TX", 2: "PI_RXD2"}, (col_x[3], 122.0, -90),
        (220.98, 175.26), desc="Serie UART ESP32-B TX2 -> Pi RXD2")

    # ======================= Reset de ESP32 desde la Pi =====================
    add("R17", "1k", "Device:R", FP_R, {1: "PI_RST_A", 2: "QA_B"}, (col_x[4], 122.0, -90),
        (238.76, 175.26), desc="Base Q1")
    add("R18", "1k", "Device:R", FP_R, {1: "PI_RST_B", 2: "QB_B"}, (col_x[5], 122.0, -90),
        (264.16, 175.26), desc="Base Q2")
    add("R19", "10k", "Device:R", FP_R, {1: "QA_B", 2: "GND"}, (col_x[0], 133.0, -90),
        (248.92, 185.42), desc="Pull-down base Q1")
    add("R20", "10k", "Device:R", FP_R, {1: "QB_B", 2: "GND"}, (col_x[1], 133.0, -90),
        (274.32, 185.42), desc="Pull-down base Q2")
    add("Q1", "2N3904", "Device:Q_NPN_EBC", FP_TO92, {1: "GND", 2: "QA_B", 3: "ESPA_EN"},
        (60.0, 145.0, 0), (246.38, 200.66), desc="Reset ESP32-A (Pi GPIO17)")
    add("Q2", "2N3904", "Device:Q_NPN_EBC", FP_TO92, {1: "GND", 2: "QB_B", 3: "ESPB_EN"},
        (68.0, 145.0, 0), (271.78, 200.66), desc="Reset ESP32-B (Pi GPIO27)")

    # ======================= MOTOR_EN pull-down =============================
    add("R21", "10k", "Device:R", FP_R, {1: "MOTOR_EN", 2: "GND"}, (col_x[2], 133.0, -90),
        (365.76, 175.26), desc="Pull-down MOTOR_EN (motores apagados durante el arranque)")

    # ======================= Sensor de bateria ==============================
    add("R22", "100k", "Device:R", FP_R, {1: "VBAT_F", 2: "VBAT_SENSE"}, (col_x[3], 133.0, -90),
        (497.84, 175.26), desc="Divisor VBAT (alto)")
    add("R23", "27k", "Device:R", FP_R, {1: "VBAT_SENSE", 2: "GND"}, (col_x[4], 133.0, -90),
        (497.84, 198.12), desc="Divisor VBAT (bajo)")
    add("C5", "100nF", "Device:C", FP_C, {1: "VBAT_SENSE", 2: "GND"}, (77.0, 145.0, 0),
        (510.54, 198.12), desc="Filtro ADC VBAT")

    # ======================= Alimentacion ===================================
    # XT60 macho vertical (soldar las copas en barrenos de 4.5 mm). La bateria
    # Gens Ace 3S trae XT60 hembra. Convencion XT60: lado RECTO = (+),
    # lado BISELADO = (-). En el footprint AMASS el pad 1 es el lado biselado.
    add("J1", "XT60 BAT 12V", "rover:XT60_Battery", FP_XT60,
        {1: "GND", 2: "VBAT_IN"}, (7.0, 79.0, -90), (25.4, 50.8),
        desc="Conector XT60 macho para bateria LiPo 3S (lado biselado = -)",
        mpn="AMASS XT60 macho (copas para soldar) / XT60-M")
    add("F1", "ATO 15A", "Device:Fuse", FP_FUSE, {1: "VBAT_IN", 2: "VBAT_F"},
        (19.0, 82.0, 0), (55.88, 50.8), desc="Portafusible ATO para PCB + fusible 15A",
        mpn="Littelfuse/Pudenz 2 pin ATO holder")
    add("J3", "12V OUT -> buck 5V", "Connector:Screw_Terminal_01x02", FP_TB2,
        {1: "GND", 2: "VBAT_F"}, (6.0, 102.0, -90), (86.36, 50.8),
        desc="Salida 12V protegida hacia el step-down de 5V/5A", mpn="KF301-2P 5.08mm")
    add("J4", "12V OUT -> BEC servos", "Connector:Screw_Terminal_01x02", FP_TB2,
        {1: "VBAT_F", 2: "GND"}, (6.0, 113.0, -90), (86.36, 68.58),
        desc="Salida 12V protegida hacia el BEC de servos 6V", mpn="KF301-2P 5.08mm")
    add("C1", "1000uF 25V", "Device:C_Polarized", FP_CP12, {1: "VBAT_F", 2: "GND"},
        (22.0, 93.0, 180), (116.84, 55.88), desc="Bulk VBAT")
    add("D2", "LED rojo 12V", "Device:LED", FP_LED, {1: "LED12_K", 2: "GND"},
        (18.0, 108.0, 0), (139.7, 60.96), desc="Indicador 12V")
    add("R24", "2.2k", "Device:R", FP_R, {1: "VBAT_F", 2: "LED12_K"}, (16.0, 113.0, 0),
        (139.7, 48.26), desc="Resistencia LED 12V")

    add("J5", "5V IN (buck 5V 5A)", "Connector:Screw_Terminal_01x02", FP_TB2,
        {1: "+5V", 2: "GND"}, (195.0, 84.08, 90), (25.4, 101.6),
        desc="Entrada 5V/5A desde step-down (alimenta Pi 5, ESP32 y encoders)",
        mpn="KF301-2P 5.08mm")
    add("C2", "1000uF 10V", "Device:C_Polarized", FP_CP10, {1: "+5V", 2: "GND"},
        (178.0, 87.0, 0), (55.88, 106.68), desc="Bulk 5V")
    add("D1", "SA5.0A", "Device:D_Zener", FP_DO15, {1: "+5V", 2: "GND"},
        (157.0, 90.0, 0), (76.2, 106.68), desc="TVS 5V (proteccion Pi)", mpn="SA5.0A DO-15")
    add("D3", "LED verde 5V", "Device:LED", FP_LED, {1: "LED5_K", 2: "GND"},
        (172.0, 80.0, 0), (101.6, 111.76), desc="Indicador 5V")
    add("R25", "330", "Device:R", FP_R, {1: "+5V", 2: "LED5_K"}, (161.0, 80.0, 0),
        (101.6, 99.06), desc="Resistencia LED 5V")

    add("J6", "SERVO PWR IN (6V)", "Connector:Screw_Terminal_01x02", FP_TB2,
        {1: "SERVO_V", 2: "GND"}, (118.08, 78.0, 180), (25.4, 139.7),
        desc="Entrada BEC servos 6V #1", mpn="KF301-2P 5.08mm")
    add("J7", "SERVO PWR IN (6V)", "Connector:Screw_Terminal_01x02", FP_TB2,
        {1: "GND", 2: "SERVO_V"}, (129.08, 78.0, 180), (25.4, 157.48),
        desc="Entrada BEC servos 6V #2 (en paralelo)", mpn="KF301-2P 5.08mm")
    add("C3", "1000uF 10V", "Device:C_Polarized", FP_CP10, {1: "SERVO_V", 2: "GND"},
        (113.0, 89.0, 0), (55.88, 144.78), desc="Bulk servos")
    add("C4", "1000uF 10V", "Device:C_Polarized", FP_CP10, {1: "SERVO_V", 2: "GND"},
        (125.0, 89.0, 0), (66.04, 144.78), desc="Bulk servos")
    add("D4", "LED azul SERVO", "Device:LED", FP_LED, {1: "LEDS_K", 2: "GND"},
        (140.0, 88.0, 0), (101.6, 149.86), desc="Indicador rail servos")
    add("R26", "470", "Device:R", FP_R, {1: "SERVO_V", 2: "LEDS_K"}, (138.5, 82.0, 0),
        (101.6, 137.16), desc="Resistencia LED servos")

    # ======================= Servos =========================================
    for n in range(1, 9):
        g, d = SERVOS[n]
        add("J%d" % (30 + n), "SERVO%d" % n, "rover:Servo_Header", FP_H1x3,
            {1: "GND", 2: "SERVO_V", 3: "SERVO%d" % n},
            (70.0 + 5.08 * (n - 1), 77.0, 0), (330.2 + 30.48 * (n - 1), 391.16),
            desc="Servo %d - %s (GND, V+, SIG)" % (n, d), mpn="Header macho 1x3 2.54mm")

    # ======================= Headers auxiliares =============================
    add("J41", "AUX ESP32-A", "rover:Aux_Header_4", FP_H1x4,
        {1: "+3V3_A", 2: "GND", 3: "AUXA_IO2", 4: "AUXA_IO15"}, (24.0, 132.0, 0),
        (330.2, 160.02), desc="Header auxiliar ESP32-A", mpn="Header macho 1x4")
    add("J42", "AUX ESP32-B (I2C)", "rover:Aux_Header_8", FP_H1x8,
        {1: "+3V3_B", 2: "GND", 3: "AUXB_SDA", 4: "AUXB_SCL", 5: "AUXB_IO18",
         6: "AUXB_IO19", 7: "AUXB_IO35", 8: "AUXB_IO39"}, (125.0, 108.0, 0),
        (457.2, 160.02), desc="Header auxiliar ESP32-B (I2C + GPIO)", mpn="Header macho 1x8")
    add("J43", "AUX RPi (I2C)", "rover:Aux_Header_8", FP_H1x8,
        {1: "+3V3_PI", 2: "GND", 3: "PI_SDA", 4: "PI_SCL", 5: "PI_GPIO22",
         6: "PI_GPIO23", 7: "PI_GPIO24", 8: "PI_GPIO25"}, (140.0, 78.0, 90),
        (238.76, 139.7), desc="Header auxiliar Raspberry Pi (I2C + GPIO)", mpn="Header macho 1x8")

    # ======================= Agujeros de montaje ============================
    for i, (x, y) in enumerate(CHASSIS_HOLES):
        add("H%d" % (i + 1), "M3", "Mechanical:MountingHole", FP_MH, {}, (x, y, 0),
            (543.56 + 12.7 * i, 25.4), desc="Agujero de montaje M3")
    return COMPONENTS


def nets():
    s = set()
    for c in COMPONENTS:
        for n in c["pins"].values():
            if n:
                s.add(n)
    return sorted(s)
