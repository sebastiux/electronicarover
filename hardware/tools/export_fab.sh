#!/bin/bash
# Exporta fabricacion (Gerbers de UNA capa + taladros) y documentacion.
# Requiere kicad-cli (KiCad 7+). Correr despues de generate.py --route.
#
# PCB de una sola capa:
#   - Cobre: SOLO B.Cu (cara de soldadura).
#   - F.Cu NO se fabrica: contiene los puentes de alambre (guia de montaje,
#     ver docs/puentes_alambre.pdf y rover_controller/puentes_alambre.csv).
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
PRJ="$ROOT/rover_controller"
FAB="$ROOT/fab"
DOC="$ROOT/docs"
mkdir -p "$FAB/gerbers" "$DOC/img"
PCB="$PRJ/rover_controller.kicad_pcb"
SCH="$PRJ/rover_controller.kicad_sch"

kicad-cli sch export pdf -o "$DOC/rover_controller_schematic.pdf" "$SCH" >/dev/null

rm -f "$FAB/gerbers/"*
kicad-cli pcb export gerbers -o "$FAB/gerbers/" \
  --layers B.Cu,B.Mask,F.SilkS,Edge.Cuts --use-drill-file-origin "$PCB" >/dev/null
kicad-cli pcb export drill -o "$FAB/gerbers/" --format excellon --excellon-separate-th \
  --drill-origin plot --generate-map --map-format gerberx2 "$PCB" >/dev/null
(cd "$FAB/gerbers" && rm -f ../rover_controller_gerbers_1capa.zip && zip -q ../rover_controller_gerbers_1capa.zip ./*)
cp "$PRJ/bom.csv" "$FAB/bom.csv"
[ -f "$PRJ/puentes_alambre.csv" ] && cp "$PRJ/puentes_alambre.csv" "$FAB/"

# PDF para planchado / fotolito: cobre B.Cu ESPEJADO (visto desde la cara de cobre), escala 1:1
kicad-cli pcb export pdf -o "$DOC/cobre_BCu_espejo_1a1.pdf" --layers B.Cu,Edge.Cuts \
  --black-and-white --mirror "$PCB" >/dev/null
# Guia de montaje: serigrafia + puentes de alambre (F.Cu) vistos desde arriba
kicad-cli pcb export pdf -o "$DOC/montaje_y_puentes.pdf" --layers F.SilkS,F.Cu,Edge.Cuts \
  "$PCB" >/dev/null
kicad-cli pcb export pdf -o "$DOC/plantilla_1a1.pdf" --layers F.Fab,F.SilkS,Edge.Cuts \
  --black-and-white "$PCB" >/dev/null

# Imagenes
kicad-cli pcb export svg -o "$DOC/img/pcb_cobre.svg" --layers B.Cu,Edge.Cuts \
  --page-size-mode 2 --exclude-drawing-sheet "$PCB" >/dev/null
kicad-cli pcb export svg -o "$DOC/img/pcb_completa.svg" --layers B.Cu,F.Cu,F.SilkS,Edge.Cuts \
  --page-size-mode 2 --exclude-drawing-sheet "$PCB" >/dev/null
kicad-cli pcb export svg -o "$DOC/img/pcb_montaje.svg" --layers F.SilkS,F.Fab,F.Cu,Edge.Cuts \
  --page-size-mode 2 --exclude-drawing-sheet "$PCB" >/dev/null
if command -v rsvg-convert >/dev/null; then
  for f in pcb_cobre pcb_completa pcb_montaje; do
    rsvg-convert -w 2400 -b white "$DOC/img/$f.svg" -o "$DOC/img/$f.png"
  done
fi
rm -f "$DOC/img/pcb_top."* "$DOC/img/pcb_bottom."* "$DOC/img/pcb_assembly."*
echo "Listo: $FAB y $DOC"
