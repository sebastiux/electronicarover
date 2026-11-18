#!/bin/bash
# Exporta fabricacion (Gerbers de 2 capas + taladros) y documentacion.
# Requiere kicad-cli (KiCad 7+). Correr despues de generate.py --route.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
PRJ="$ROOT/rover_controller"
FAB="$ROOT/fab"
DOC="$ROOT/docs"
mkdir -p "$FAB/gerbers" "$DOC/img"
PCB="$PRJ/rover_controller.kicad_pcb"
SCH="$PRJ/rover_controller.kicad_sch"

kicad-cli sch export pdf -o "$DOC/rover_controller_schematic.pdf" "$SCH" >/dev/null

rm -f "$FAB/gerbers/"* "$FAB"/*.zip "$FAB/puentes_alambre.csv"
kicad-cli pcb export gerbers -o "$FAB/gerbers/" \
  --layers F.Cu,B.Cu,F.Mask,B.Mask,F.SilkS,B.SilkS,Edge.Cuts \
  --subtract-soldermask --use-drill-file-origin "$PCB" >/dev/null
kicad-cli pcb export drill -o "$FAB/gerbers/" --format excellon --excellon-separate-th \
  --drill-origin plot --generate-map --map-format gerberx2 "$PCB" >/dev/null
(cd "$FAB/gerbers" && zip -q ../rover_controller_gerbers_2capas.zip ./*)
cp "$PRJ/bom.csv" "$FAB/bom.csv"

# PDFs 1:1: cobre superior, cobre inferior (espejado, visto desde abajo) y plantilla de modulos
kicad-cli pcb export pdf -o "$DOC/cobre_FCu_1a1.pdf" --layers F.Cu,Edge.Cuts --black-and-white "$PCB" >/dev/null
kicad-cli pcb export pdf -o "$DOC/cobre_BCu_espejo_1a1.pdf" --layers B.Cu,Edge.Cuts --black-and-white --mirror "$PCB" >/dev/null
kicad-cli pcb export pdf -o "$DOC/plantilla_1a1.pdf" --layers F.Fab,F.SilkS,Edge.Cuts --black-and-white "$PCB" >/dev/null
rm -f "$DOC/montaje_y_puentes.pdf"

kicad-cli pcb export svg -o "$DOC/img/pcb_completa.svg" --layers F.Cu,B.Cu,F.SilkS,Edge.Cuts \
  --page-size-mode 2 --exclude-drawing-sheet "$PCB" >/dev/null
kicad-cli pcb export svg -o "$DOC/img/pcb_top.svg" --layers F.Cu,F.SilkS,Edge.Cuts \
  --page-size-mode 2 --exclude-drawing-sheet "$PCB" >/dev/null
kicad-cli pcb export svg -o "$DOC/img/pcb_bottom.svg" --layers B.Cu,Edge.Cuts \
  --page-size-mode 2 --exclude-drawing-sheet "$PCB" >/dev/null
rm -f "$DOC/img/pcb_cobre."* "$DOC/img/pcb_montaje."*
if command -v rsvg-convert >/dev/null; then
  for f in pcb_completa pcb_top pcb_bottom; do
    rsvg-convert -w 2400 -b white "$DOC/img/$f.svg" -o "$DOC/img/$f.png"
  done
fi
echo "Listo: $FAB y $DOC"
