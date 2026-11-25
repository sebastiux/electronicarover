# -*- coding: utf-8 -*-
"""Ajustes comunes de las 2 tarjetas de una sola cara (traccion y servos).

- Cobre solo en la cara inferior (FR1 de una cara): todo se suelda por abajo.
- Si una conexion no cabe en una capa, el router la resuelve con un CABLE por arriba
  (puente de alambre aislado, como un componente: sus 2 puntas se sueldan por abajo).
- La Raspberry Pi 5 NO va en estas tarjetas: lleva un HAT de bornas (header hembra 2x20)
  y desde ahi un cable de 3 hilos (GND, TX, RX) a la borna "PI" de cada tarjeta.
"""
from rover_design import ESP32 as _ESP32, RPI_PINS as _RPI_PINS

LAYERS = 1                 # una capa + cables por arriba
FAB = "proto"
TOP_SOLDERED = set()       # nada se suelda por arriba
TOP_GND_POUR = False
ANTENNA_KEEPOUT_REFS = ()  # las ESP32 no usan WiFi (hablan por UART)
# ESP32 en 2 headers hembra 1x15 a 25.4 mm: UNA sola fila de pads por lado (sin la fila
# alterna de 22.86 mm, que a 1.27 mm de la otra encimaba los pads).
ESP32 = dict(_ESP32, courtyard="rows", una_fila=True)
FP_ESP32 = "rover:ESP32_DevKitV1_30P_1x15"
RPI_PINS = {**_RPI_PINS, 32: "GPIO12/TXD4", 33: "GPIO13/RXD4"}
EXTRA_SEVERITIES = {"starved_thermal": "ignore"}

FP_TB6 = "TerminalBlock_Phoenix:TerminalBlock_Phoenix_PT-1,5-6-3.5-H_1x06_P3.50mm_Horizontal"
FP_TB5 = "TerminalBlock_Phoenix:TerminalBlock_Phoenix_PT-1,5-5-3.5-H_1x05_P3.50mm_Horizontal"
FP_TB3 = "TerminalBlock_Phoenix:TerminalBlock_Phoenix_PT-1,5-3-3.5-H_1x03_P3.50mm_Horizontal"
FP_TB2 = "TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal"
MPN_TB2 = "Phoenix MKDS 1,5/2-5,08 o KF301-2P"

# Reglas para fresar TODO con una sola fresa plana de 1.0 mm (aislamiento, barrenos y contorno):
# la fresa abre un canal de 1 mm, asi que entre cobre de redes distintas debe haber >= 1.0 mm.
# Nuestro CAM (cubiko_cam.py) corta cada red por separado y en un hueco de 1.0 pasa por el centro.
# En un CAM que desplaza TODO el cobre junto (la app del Fab Lab, FlatCAM) se declara la fresa
# de 0.95 mm: asi encuentra camino en cada hueco de 1.0 con UNA pasada (ver cnc_*/README.md).
UNA_FRESA = 1.0            # diametro de la unica herramienta (mm)
CLR = 1.0                  # separacion entre pistas, plano y piezas
NETCLASSES = [
    ("SERVO", 2.5, CLR, 2.4, 1.0, ["SERVO_V"]),
    ("PWR", 1.5, CLR, 2.4, 1.0, ["+5V"]),
    ("GND", 1.5, CLR, 2.4, 1.0, ["GND"]),
]
DEFAULT_CLASS = (1.0, CLR, 2.4, 1.0)      # pista de 1.0 mm, separacion de 1.0 mm
ZONE_CLR = CLR             # el plano de GND tambien queda a 1.0 mm de todo lo demas
PAD_MIN = 2.2              # pads de 2.2 mm donde el paso lo permite (anillo de 0.6 mm)
PAD_GAP = 1.14             # entre pads de una fila a 2.54 mm: 1.14 mm libres, mas que la fresa de 1 mm
PAD_OVAL = True            # en paso de 2.54: pads ovalados 1.4 mm a lo largo de la fila x 2.2 mm
ZONE_FULL = True           # pads unidos al plano de GND sin rayos de alivio termico
MIN_PAD_ESPACIO = CLR      # cobre libre minimo entre pads de piezas distintas (verifica_espacios.py)
VIA_PAD_ESPACIO = CLR      # y entre el barreno de un cable y cualquier pad


def routing_reserved():
    return []


ROUTING_LATE = []
SCH_NOTES = []
