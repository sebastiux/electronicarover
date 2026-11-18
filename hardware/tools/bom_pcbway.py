#!/usr/bin/env python3
"""BOM para ensamble llave en mano (PCBWay u otro ensamblador THT).

Se ensambla todo excepto los 3 modulos L298N (U4-U6) y la Raspberry Pi 5.
Las ESP32 no se sueldan: se colocan sus zocalos (header hembra 1x15) y se enchufan.
Salida: fab/pcbway/rover_controller_BOM_PCBWay.xlsx y .csv, mas un resumen en stdout.
"""
import csv, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rover_design as D

OUT = os.path.join(HERE, "..", "fab", "pcbway")
PCB = os.path.join(HERE, "..", "rover_controller", D.PROJECT + ".kicad_pcb")

RES = {"10k": "10K", "20k": "20K", "1k": "1K", "100k": "100K", "27k": "27K",
       "2.2k": "2K2", "330": "330R", "470": "470R"}


def part(c):
    """-> (fabricante, MPN, descripcion, encapsulado, ensamblar, notas)"""
    ref, val, fp = c["ref"], c["value"], c["footprint"]
    if ref.startswith("R"):
        return ("Yageo", "MFR-25FBF52-" + RES[val], "Resistencia %s 1/4 W 1%% pelicula metalica" % val,
                "Axial DIN0207, paso 7.62 mm", True, "")
    if ref == "C1":
        return ("Panasonic", "EEU-FR1E102", "Electrolitico 1000 uF 25 V", "Radial D12.5 mm, paso 5 mm", True, "Polarizado")
    if ref in ("C2", "C3", "C4"):
        return ("Panasonic", "EEU-FR1A102", "Electrolitico 1000 uF 10 V", "Radial D10 mm, paso 5 mm", True, "Polarizado")
    if ref == "C5":
        return ("Vishay", "K104K15X7RF53L2", "Ceramico 100 nF 50 V X7R", "Disco, paso 5 mm", True, "")
    if ref.startswith("C"):
        return ("Vishay", "K102K15X7RF5TL2", "Ceramico 1 nF 50 V X7R", "Disco, paso 2.5 mm", True, "")
    if ref == "D1":
        return ("Littelfuse", "SA5.0A", "TVS 5 V 500 W unidireccional", "DO-15 axial, paso 10.16 mm", True, "Polarizado (banda = catodo)")
    if ref in ("D5", "D6"):
        return ("onsemi", "1N5819RLG", "Schottky 40 V 1 A", "DO-41 axial, paso 10.16 mm", True, "Polarizado (banda = catodo)")
    if ref in ("D2", "D3", "D4"):
        col = {"D2": ("rojo", "WP7113ID"), "D3": ("verde", "WP7113GD"), "D4": ("azul", "WP7113QBC/D")}[ref]
        return ("Kingbright", col[1], "LED 5 mm %s difuso" % col[0], "THT D5 mm, paso 2.54 mm", True, "Polarizado (pad cuadrado = catodo)")
    if ref == "F1":
        return ("Littelfuse", "Portafusible ATO PCB 2 pines (Pudenz)", "Portafusible para fusible de cuchilla ATO",
                "THT, 2 pines", True, "Incluir fusible ATO 15 A suelto (sin insertar)")
    if ref == "J1":
        return ("AMASS", "XT60-M", "Conector XT60 macho vertical (bateria)", "THT, paso 7.2 mm", True,
                "Lado biselado = (-), ver serigrafia")
    if fp.startswith("TerminalBlock"):
        return ("Phoenix Contact", "1729128", "Bornera 2 polos paso 5.08 mm (MKDS 1,5/2-5,08)", "THT, paso 5.08 mm",
                True, "Equivalente aceptado: KF301-2P / DG301")
    if ref.startswith("J2"):
        return ("Generico", "Header macho 1x6 2.54 mm recto", "Header macho 1x6, paso 2.54 mm, dorado", "THT", True, "")
    if ref.startswith("J3"):
        return ("Generico", "Header macho 1x3 2.54 mm recto", "Header macho 1x3, paso 2.54 mm, dorado", "THT", True, "")
    if ref == "U1":
        return ("Generico", "Header hembra 2x20 2.54 mm recto (8.5 mm)", "Zocalo para Raspberry Pi 5 (la Pi NO se incluye)",
                "THT 2x20", True, "Se monta en la CARA INFERIOR y se suelda por la superior")
    if ref in ("U2", "U3"):
        return ("Generico", "Header hembra 1x15 2.54 mm recto (8.5 mm)", "Zocalo para ESP32 DevKit V1 30 pines (2 por ESP32)",
                "THT 1x15", True, "Fila EXTERIOR (25.4 mm entre filas). La ESP32 se enchufa, no se suelda")
    if ref in ("U4", "U5", "U6"):
        return ("-", "Modulo L298N HW-095", "Puente H (lo instala el cliente)", "-", False, "NO ENSAMBLAR (DNP): dejar pads libres")
    if ref.startswith("H"):
        return None
    raise SystemExit("sin datos de compra para " + ref)


def main():
    os.makedirs(OUT, exist_ok=True)
    comps = D.build()
    groups = {}
    for c in comps:
        p = part(c)
        if p is None:
            continue
        key = p[:4] + (p[4], p[5])
        n = 2 if c["ref"] in ("U2", "U3") else 1   # 2 headers 1x15 por ESP32
        groups.setdefault(key, []).append((c["ref"], n))

    def refkey(r):
        return (r.rstrip("0123456789"), int(re.sub(r"\D", "", r) or 0))

    rows = []
    for key, refs in sorted(groups.items(), key=lambda kv: (not kv[0][4], refkey(min(r for r, _ in kv[1])))):
        mfr, mpn, desc, pkg, asm, notes = key
        refs = sorted(refs, key=lambda x: refkey(x[0]))
        side = "Bottom" if [r for r, _ in refs] == ["U1"] else "Top"
        rows.append([",".join(r for r, _ in refs), sum(n for _, n in refs), mfr, mpn, desc, pkg,
                     "THT", side, "Yes" if asm else "No (DNP)", notes])
    hdr = ["Item", "Designator", "Qty", "Manufacturer", "Manufacturer Part Number", "Description",
           "Package", "Type", "Side", "Assemble", "Notes"]
    rows = [[i + 1] + r for i, r in enumerate(rows)]
    with open(os.path.join(OUT, "rover_controller_BOM_PCBWay.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(hdr)
        w.writerows(rows)
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "BOM"
        ws.append(hdr)
        for r in rows:
            ws.append(r)
        for c in ws[1]:
            c.font = Font(bold=True, color="FFFFFF")
            c.fill = PatternFill("solid", fgColor="1F2430")
        for r in ws.iter_rows(min_row=2):
            if r[9].value != "Yes":
                for c in r:
                    c.fill = PatternFill("solid", fgColor="FDE2E2")
            for c in r:
                c.alignment = Alignment(vertical="top", wrap_text=True)
        for col, wd in zip("ABCDEFGHIJK", (5, 34, 5, 16, 36, 44, 26, 6, 8, 10, 44)):
            ws.column_dimensions[col].width = wd
        wb.save(os.path.join(OUT, "rover_controller_BOM_PCBWay.xlsx"))
    except ImportError:
        print("openpyxl no instalado: solo CSV")

    asm = [r for r in rows if r[9] == "Yes"]
    pieces = sum(r[2] for r in asm)
    joints = 0
    try:
        import pcbnew
        b = pcbnew.LoadBoard(PCB)
        asm_refs = {x for r in asm for x in r[1].split(",")}
        for fp in b.GetFootprints():
            if fp.GetReference() in asm_refs:
                joints += sum(1 for p in fp.Pads() if p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH)
    except Exception as e:
        print("(sin conteo de puntos de soldadura: %s)" % e)
    print("piezas=%d numeros_de_parte=%d puntos_THT=%d" % (pieces, len(asm), joints))


if __name__ == "__main__":
    main()
