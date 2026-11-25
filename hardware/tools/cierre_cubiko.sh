#!/bin/sh
# Registro de los ajustes hechos a mano sobre la PCB Cubiko ya ruteada.
# (Si se vuelve a rutear con generate.py --route, hay que repetirlos.)
set -e
cd "$(dirname "$0")"
PCB=../rover_controller_cubiko/rover_controller_cubiko.kicad_pcb
# 1) Quitar los lazos de MOTOR_EN que duplicaban el bus de vias EN (2 vias-pin a 1.7 mm
#    en J41.6 y J42.6) y la via GND que quedaba bajo el separador de H3.
python3 limpia_cubiko.py $PCB
# 2) La via EN de J41.6 sube 0.65 mm (Y 88.25 -> 87.6) para librar la rondana de H3.
#    rover_cubiko.py ya la genera ahi; en la PCB ruteada se movio con un reemplazo de texto.
# 3) Verificacion
ROVER_VARIANT=cubiko python3 check_proto.py $PCB
ROVER_VARIANT=cubiko python3 vias_sobrantes.py $PCB
