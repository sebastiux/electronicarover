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
ESP32 = dict(_ESP32, courtyard="rows")
RPI_PINS = {**_RPI_PINS, 32: "GPIO12/TXD4", 33: "GPIO13/RXD4"}
EXTRA_SEVERITIES = {"starved_thermal": "ignore"}

FP_TB6 = "TerminalBlock_Phoenix:TerminalBlock_Phoenix_PT-1,5-6-3.5-H_1x06_P3.50mm_Horizontal"
FP_TB5 = "TerminalBlock_Phoenix:TerminalBlock_Phoenix_PT-1,5-5-3.5-H_1x05_P3.50mm_Horizontal"
FP_TB3 = "TerminalBlock_Phoenix:TerminalBlock_Phoenix_PT-1,5-3-3.5-H_1x03_P3.50mm_Horizontal"
FP_TB2 = "TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal"
MPN_TB2 = "Phoenix MKDS 1,5/2-5,08 o KF301-2P"

# Reglas de fresado con V-bit: pistas de 1.0 mm minimo, 0.5 mm de separacion
NETCLASSES = [
    ("SERVO", 2.5, 0.5, 2.4, 1.0, ["SERVO_V"]),
    ("PWR", 1.5, 0.5, 2.4, 1.0, ["+5V"]),
    ("GND", 1.5, 0.5, 2.4, 1.0, ["GND"]),
]
DEFAULT_CLASS = (1.0, 0.5, 2.4, 1.0)      # toda conexion de al menos 1.0 mm
PAD_MIN = 2.2              # pads de 2.2 mm donde el paso lo permite (anillo de 0.6 mm)
PAD_GAP = 0.7              # separacion minima entre pads de una misma pieza
ZONE_FULL = True           # pads unidos al plano de GND sin rayos de alivio termico
MIN_PAD_ESPACIO = 1.0      # cobre libre minimo entre pads de piezas distintas (verifica_espacios.py)
VIA_PAD_ESPACIO = 0.6      # cobre libre minimo entre el barreno de un cable y cualquier pad


def routing_reserved():
    return []


ROUTING_LATE = []
SCH_NOTES = []
