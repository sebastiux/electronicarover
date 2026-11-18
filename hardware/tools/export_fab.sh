#!/bin/bash
# Exporta archivos de fabricacion (Gerbers + taladros) y documentacion (PDF/PNG).
# Requiere kicad-cli (KiCad 7+). Correr DESPUES de rutear la PCB.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
PRJ="$ROOT/rover_controller"
FAB="$ROOT/fab"
DOC="$ROOT/docs"
mkdir -p "$FAB/gerbers" "$DOC/img"

PCB="$PRJ/rover_controller.kicad_pcb"
SCH="$PRJ/rover_controller.kicad_sch"

# Esquematico
kicad-cli sch export pdf -o "$DOC/rover_controller_schematic.pdf" "$SCH"

# Gerbers (capas estandar para JLCPCB/PCBWay) + taladros Excellon
kicad-cli pcb export gerbers -o "$FAB/gerbers/" \
  --layers F.Cu,B.Cu,F.Paste,B.Paste,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts \
  --subtract-soldermask --use-drill-file-origin "$PCB"
kicad-cli pcb export drill -o "$FAB/gerbers/" --format excellon --excellon-separate-th \
  --drill-origin plot --generate-map --map-format gerberx2 "$PCB"
(cd "$FAB/gerbers" && rm -f ../rover_controller_gerbers.zip && zip -q ../rover_controller_gerbers.zip ./*)
cp "$PRJ/bom.csv" "$FAB/bom.csv"

# Imagenes de la PCB
kicad-cli pcb export svg -o "$DOC/img/pcb_top.svg" --layers F.Cu,F.SilkS,Edge.Cuts \
  --page-size-mode 2 --exclude-drawing-sheet "$PCB" >/dev/null
kicad-cli pcb export svg -o "$DOC/img/pcb_bottom.svg" --layers B.Cu,Edge.Cuts \
  --page-size-mode 2 --exclude-drawing-sheet --mirror "$PCB" >/dev/null
kicad-cli pcb export svg -o "$DOC/img/pcb_assembly.svg" --layers F.SilkS,F.Fab,Edge.Cuts \
  --page-size-mode 2 --exclude-drawing-sheet --black-and-white "$PCB" >/dev/null
# Plantilla 1:1 para verificar modulos L298N/ESP32/RPi con papel antes de fabricar
kicad-cli pcb export pdf -o "$DOC/plantilla_1a1.pdf" --layers F.Fab,F.SilkS,Edge.Cuts,F.Cu \
  --black-and-white "$PCB" >/dev/null
if command -v rsvg-convert >/dev/null; then
  for f in pcb_top pcb_bottom pcb_assembly; do
    rsvg-convert -w 2400 -b white "$DOC/img/$f.svg" -o "$DOC/img/$f.png"
  done
fi
echo "Listo: $FAB y $DOC"
