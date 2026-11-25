#!/usr/bin/env python3
"""Corrige la polaridad de los LED indicadores (D2, D3, D4) en una PCB ya ruteada.

El diseno original ponia el pin 1 (K, catodo, pad cuadrado) del LED hacia la
resistencia que viene de +5V/VBAT/SERVO_V y el pin 2 (A, anodo) a GND: el LED
quedaba en inversa y no encendia. Aqui cada LED gira 180 grados con el origen en
la posicion del antiguo pad 2: los pads intercambian lugar, las pistas no se tocan.
Las redes LEDx_K pasan a llamarse LEDx_A (ahora llegan al anodo).
Uso: python3 fix_leds.py tarjeta.kicad_pcb"""
import sys, subprocess, os
import pcbnew
pcb = os.path.abspath(sys.argv[1])
b = pcbnew.LoadBoard(pcb)
for ref in ("D2", "D3", "D4"):
    fp = b.FindFootprintByReference(ref)
    p1, p2 = fp.FindPadByNumber("1"), fp.FindPadByNumber("2")
    n1, n2 = p1.GetNet(), p2.GetNet()
    if n2.GetNetname() != "GND":
        print(ref, "ya corregido (pad 2 =", n2.GetNetname() + ")"); continue
    pos2 = p2.GetPosition()
    fp.SetOrientationDegrees(fp.GetOrientationDegrees() + 180)
    fp.SetPosition(pos2)
    p1.SetNet(n2); p2.SetNet(n1)
    print(ref, "-> rot %.0f en (%.2f, %.2f); pad1 %s, pad2 %s" % (fp.GetOrientationDegrees(),
          pcbnew.ToMM(pos2.x) - 30, pcbnew.ToMM(pos2.y) - 30, p1.GetNetname(), p2.GetNetname()))
pcbnew.SaveBoard(pcb, b)
txt = open(pcb).read()
for a in ("LED12", "LED5", "LEDS"):
    txt = txt.replace('"%s_K"' % a, '"%s_A"' % a)
open(pcb, "w").write(txt)
# SaveBoard reescribe el .kicad_pro con valores de fabrica: se restaura el del repositorio
pro = pcb[:-len(".kicad_pcb")] + ".kicad_pro"
subprocess.run(["git", "checkout", "--", pro], cwd=os.path.dirname(pcb), check=True)
