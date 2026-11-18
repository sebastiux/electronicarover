#!/bin/bash
# Registro del cierre manual de la v1.2 (prototipado). Tras `generate.py --route`
# quedaron 6 pads sin conectar; se cerraron con fix_proto.py en este orden.
# Si se vuelve a rutear desde cero el resultado puede cambiar: revisa con
# check_proto.py y ajusta coordenadas/redes antes de reutilizar estos comandos.
set -e
cd "$(dirname "$0")"
P=../rover_controller/rover_controller.kicad_pcb
f() { python3 fix_proto.py $P $P "$@"; }
# 1) divisor del encoder 6 (C16/R6/R12)
f --drop ENC6_A5V --drop ENC5_A --drop ENC5_A5V --route ENC6_A --route ENC6_A5V --route ENC5_A --route ENC5_A5V
# 2) UART2 de la Pi: GND de los pines 25/39 con via propia, libera la salida del pin 29
f --dropbox "GND:155,97,197,106" --drop PI_RXD2 --drop PI_TXD2 \
  --via "GND:173.85,101.5" --track "GND:F:1.0:173.85,98.27/173.85,101.5" \
  --via "GND:191.63,101.5" --track "GND:F:1.0:191.63,98.27/191.63,101.5" \
  --route PI_RXD2 --route PI_TXD2
# 3) +5V del encoder 5 (J25.4)
f --drop ENC4_A5V --drop ENC5_A5V --route 5V_U6 --route ENC4_A5V --route ENC5_A5V
# 4) GND de U5: la pista de 12 V sube para dejar lugar a una via de GND
f --dropbox "VBAT_F:86.9,58,147.9,62" --drop 5V_U5 \
  --track "VBAT_F:B:3.0:83.95,60.45/86.5,57.2/96.5,57.2/100,58.8/147.95,60.45" --route 5V_U5
f --drop 5V_U5 --via "GND:92,60.6" --track "GND:B:1.2:92,63.5/92,60.6" \
  --track "GND:F:1.2:92,60.6/87,46/84,42/76,40" --via "GND:76,40" --route 5V_U5
python3 check_proto.py $P
