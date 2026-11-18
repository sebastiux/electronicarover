#!/usr/bin/env python3
"""Exporta el netlist REAL de la PCB (.kicad_pcb) a firmware/test/board_model.h
para la simulacion firmware <-> PCB. Requiere el Python de KiCad (pcbnew)."""
import os, re, sys
import pcbnew
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rover_design as D

pcb = os.path.join(HERE, "..", "rover_controller", "rover_controller.kicad_pcb")
out = os.path.join(HERE, "..", "..", "firmware", "test", "board_model.h")
b = pcbnew.LoadBoard(pcb)

def gpio_of(name):
    m = re.search(r"IO(\d+)$", name)
    return int(m.group(1)) if m else -1

nodes = set()
values = {}
for fp in b.GetFootprints():
    ref = fp.GetReference()
    values[ref] = fp.GetValue()
    for p in fp.Pads():
        if p.GetNumber() and p.GetNetname():
            nodes.add((ref, p.GetNumber(), p.GetNetname()))
esp_names = {str(i + 1): n for i, n in enumerate(D.ESP32_LEFT)}
esp_names.update({str(i + 16): n for i, n in enumerate(D.ESP32_RIGHT)})
L = ["// Generado por hardware/tools/export_board_model.py desde rover_controller.kicad_pcb",
     "// NO editar a mano.", "#pragma once", "namespace board {",
     "struct Node { const char* ref; const char* pin; const char* net; };",
     "static const Node NODES[] = {"]
for (r, p, n) in sorted(nodes):
    L.append('  {"%s", "%s", "%s"},' % (r, p, n))
L.append("};")
L.append("struct Value { const char* ref; const char* value; };")
L.append("static const Value VALUES[] = {")
for r in sorted(values):
    L.append('  {"%s", "%s"},' % (r, values[r].replace('"', "'")))
L.append("};")
L.append("// pad del ESP32 DevKit -> GPIO (-1 = EN/GND/VIN/3V3)")
L.append("struct EspPad { const char* pin; int gpio; const char* name; };")
L.append("static const EspPad ESP_PADS[] = {")
for pin in sorted(esp_names, key=int):
    L.append('  {"%s", %d, "%s"},' % (pin, gpio_of(esp_names[pin]), esp_names[pin]))
L.append("};")
L.append("// pin fisico del header de la Raspberry Pi -> nombre")
L.append("struct PiPin { const char* pin; const char* name; };")
L.append("static const PiPin PI_PINS[] = {")
for n in range(1, 41):
    L.append('  {"%d", "%s"},' % (n, D.RPI_PINS[n]))
L.append("};")
L.append("}  // namespace board")
open(out, "w").write("\n".join(L) + "\n")
print("OK", out, len(nodes), "nodos")
