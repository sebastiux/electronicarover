#!/bin/bash
# Exporta fabricacion y documentacion. Requiere kicad-cli (KiCad 7+).
# Modo segun FAB en rover_design.py:
#   proto -> prototipado CNC: SOLO cobre (F.Cu/B.Cu) + contorno + taladros (un archivo, sin metalizar)
#   pro   -> fabricacion industrial (mascara, serigrafia, PTH)
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
PRJ="$ROOT/rover_controller"; FAB="$ROOT/fab"; DOC="$ROOT/docs"
PCB="$PRJ/rover_controller.kicad_pcb"; SCH="$PRJ/rover_controller.kicad_sch"
MODE=$(python3 -c "import sys; sys.path.insert(0,'$ROOT/tools'); import rover_design as D; print(D.FAB)")
mkdir -p "$FAB" "$DOC/img"
kicad-cli sch export pdf -o "$DOC/rover_controller_schematic.pdf" "$SCH" >/dev/null
cp "$PRJ/bom.csv" "$FAB/bom.csv"

if [ "$MODE" = "proto" ]; then
  OUT="$FAB/prototipado"; rm -rf "$OUT"; mkdir -p "$OUT"
  kicad-cli pcb export gerbers -o "$OUT/" --layers F.Cu,B.Cu,Edge.Cuts --use-drill-file-origin "$PCB" >/dev/null
  # un solo archivo de taladros (en prototipado nada se metaliza)
  kicad-cli pcb export drill -o "$OUT/" --format excellon --drill-origin plot \
    --generate-map --map-format pdf "$PCB" >/dev/null
  python3 - "$PCB" "$OUT/vias_pines.csv" <<'PY' 2>/dev/null | grep -v swig || true
import sys, pcbnew
b = pcbnew.LoadBoard(sys.argv[1])
bb = b.GetBoardEdgesBoundingBox()
x0, y0 = pcbnew.ToMM(bb.GetX()), pcbnew.ToMM(bb.GetY())
with open(sys.argv[2], "w") as f:
    f.write("Via;Red;X(mm desde esquina sup. izq.);Y(mm);Taladro(mm)\n")
    k = 0
    for t in b.GetTracks():
        if t.GetClass() == "PCB_VIA":
            k += 1
            p = t.GetPosition()
            f.write("V%d;%s;%.2f;%.2f;%.1f\n" % (k, t.GetNetname(), pcbnew.ToMM(p.x) - x0, pcbnew.ToMM(p.y) - y0, pcbnew.ToMM(t.GetDrillValue())))
print("vias:", k)
PY
  (cd "$OUT" && rm -f ../rover_controller_prototipado.zip && zip -q ../rover_controller_prototipado.zip ./*)
  rm -rf "$FAB/gerbers" "$FAB"/rover_controller_gerbers_2capas.zip
  kicad-cli pcb export pdf -o "$DOC/cobre_superior_FCu_1a1.pdf" --layers F.Cu,Edge.Cuts --black-and-white "$PCB" >/dev/null
  kicad-cli pcb export pdf -o "$DOC/cobre_inferior_BCu_espejo_1a1.pdf" --layers B.Cu,Edge.Cuts --black-and-white --mirror "$PCB" >/dev/null
  rm -f "$DOC/cobre_FCu_1a1.pdf" "$DOC/cobre_BCu_espejo_1a1.pdf"
else
  rm -rf "$FAB/gerbers" "$FAB/prototipado"; mkdir -p "$FAB/gerbers"
  kicad-cli pcb export gerbers -o "$FAB/gerbers/" --layers F.Cu,B.Cu,F.Mask,B.Mask,F.SilkS,B.SilkS,Edge.Cuts \
    --subtract-soldermask --use-drill-file-origin "$PCB" >/dev/null
  kicad-cli pcb export drill -o "$FAB/gerbers/" --format excellon --excellon-separate-th \
    --drill-origin plot --generate-map --map-format gerberx2 "$PCB" >/dev/null
  (cd "$FAB/gerbers" && rm -f ../rover_controller_gerbers_2capas.zip && zip -q ../rover_controller_gerbers_2capas.zip ./*)
  kicad-cli pcb export pdf -o "$DOC/cobre_FCu_1a1.pdf" --layers F.Cu,Edge.Cuts --black-and-white "$PCB" >/dev/null
  kicad-cli pcb export pdf -o "$DOC/cobre_BCu_espejo_1a1.pdf" --layers B.Cu,Edge.Cuts --black-and-white --mirror "$PCB" >/dev/null
fi
kicad-cli pcb export pdf -o "$DOC/plantilla_1a1.pdf" --layers F.Fab,F.SilkS,Edge.Cuts --black-and-white "$PCB" >/dev/null
for spec in "pcb_completa:F.Cu,B.Cu,F.SilkS,Edge.Cuts" "pcb_top:F.Cu,F.SilkS,Edge.Cuts" "pcb_bottom:B.Cu,Edge.Cuts"; do
  n=${spec%%:*}; l=${spec#*:}
  kicad-cli pcb export svg -o "$DOC/img/$n.svg" --layers "$l" --page-size-mode 2 --exclude-drawing-sheet "$PCB" >/dev/null
  command -v rsvg-convert >/dev/null && rsvg-convert -w 2400 -b white "$DOC/img/$n.svg" -o "$DOC/img/$n.png"
done
echo "Listo ($MODE): $FAB y $DOC"
