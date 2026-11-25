# -*- coding: utf-8 -*-
"""
Esquema didactico del rover (4 hojas A3): para ENTENDER el circuito, no para fabricarlo.

  1. Alimentacion: de donde sale cada voltaje.
  2. Senales: como la Raspberry Pi coordina a las 2 ESP32.
  3. Tarjeta de traccion por dentro.
  4. Tarjeta de servos por dentro.

Todos los pines, redes y valores se leen de rover_design.py (variantes traccion y servos), asi
que el esquema no se separa de la PCB. Colores: cada voltaje y cada tipo de senal tiene el suyo.

Uso:  cd hardware/tools && python3 esquema_didactico.py
Sale: hardware/esquema_didactico/esquema_rover.pdf y una PNG por hoja.
"""
import json, os, subprocess, sys
from xml.sax.saxutils import escape

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "esquema_didactico")
W, H = 420.0, 297.0
FONT = "Inter, 'DejaVu Sans', sans-serif"
MONO = "'DejaVu Sans Mono', monospace"

COL = dict(v12="#c62828", v6="#e65100", v5="#ad1457", gnd="#263238", uart="#2e7d32",
           ctl="#1565c0", enc="#6a1b9a", mot="#6d4c41", txt="#1f2328", mute="#5b6573",
           panel="#f7f9fb", borde="#c9d3dc", placa="#eef7ee", placa_b="#9cc79f",
           modulo="#fff8e1", modulo_b="#e0c36a", pi="#fde7ec", pi_b="#e39aac", esp="#e3f2fd",
           esp_b="#7fb1e3", parte="#ffffff")
ANCHO = dict(v12=1.1, v6=1.0, v5=0.9, gnd=0.8, uart=0.5, ctl=0.5, enc=0.5, mot=0.9)


# ---------------------------------------------------------------- datos del diseno
def datos(variante):
    code = ("import json, rover_design as D\n"
            "print('@@' + json.dumps([dict(ref=c['ref'], value=c['value'], "
            "pins={str(k): n for k, n in c['pins'].items()}) for c in D.build()]))")
    env = dict(os.environ, ROVER_VARIANT=variante)
    r = subprocess.run([sys.executable, "-c", code], cwd=HERE, env=env, capture_output=True, text=True)
    linea = [l for l in r.stdout.splitlines() if l.startswith("@@")]
    if not linea:
        sys.exit("no pude leer la variante %s:\n%s" % (variante, r.stderr[-2000:]))
    return {c["ref"]: c for c in json.loads(linea[0][2:])}


sys.path.insert(0, HERE)
import rover_design as D  # noqa: E402  (solo para nombres de pines y servos)

T = datos("traccion")
S = datos("servos")


def pin_esp(n):
    n = int(n)
    return D.ESP32_LEFT[n - 1] if n <= 15 else D.ESP32_RIGHT[n - 16]


def gpio(B, esp, net):
    """Nombre corto del GPIO de la ESP32 que lleva la red net."""
    for n, v in B[esp]["pins"].items():
        if v == net:
            nombre = pin_esp(n)
            return nombre.split("/")[-1] if "/" in nombre else nombre
    raise KeyError(net)


def pin_de(B, ref, net):
    return next(int(n) for n, v in B[ref]["pins"].items() if v == net)


def parte(B, **pins):
    """ref de la parte cuyos pines llevan exactamente esas redes (en cualquier orden)."""
    want = sorted(pins.values())
    for ref, c in B.items():
        if sorted(v for v in c["pins"].values() if v) == want and ref[0] in "RCD":
            return ref
    raise KeyError(pins)


def val(B, ref):
    return B[ref]["value"]


# ---------------------------------------------------------------- dibujo SVG
class Hoja:
    def __init__(self, num, total, titulo, sub):
        self.el = []
        self.num, self.total = num, total
        self.rect(0, 0, W, H, "#ffffff", None, rx=0)
        self.t(14, 15.5, titulo, 7.2, COL["txt"], weight=700)
        self.t(14, 22, sub, 3.4, COL["mute"])
        self.t(W - 14, H - 6, "Rover - esquema para entender el circuito  ·  hoja %d de %d" % (num, total),
               2.6, COL["mute"], anchor="end")
        self.t(14, H - 6, "Generado por hardware/tools/esquema_didactico.py desde rover_design.py "
               "(mismos pines y redes que las PCB)", 2.6, COL["mute"])

    # primitivas
    def raw(self, s):
        self.el.append(s)

    def rect(self, x, y, w, h, fill, stroke, rx=1.6, sw=0.35, dash=None):
        d = ' stroke-dasharray="%s"' % dash if dash else ""
        st = 'stroke="%s" stroke-width="%.2f"' % (stroke, sw) if stroke else 'stroke="none"'
        self.raw('<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" rx="%.2f" fill="%s" %s%s/>'
                 % (x, y, w, h, rx, fill, st, d))

    def t(self, x, y, s, size=3.0, color=None, anchor="start", weight=400, italic=False, mono=False, lh=1.32):
        color = color or COL["txt"]
        lines = str(s).split("\n")
        spans = "".join('<tspan x="%.2f" dy="%.2f">%s</tspan>' % (x, 0 if i == 0 else size * lh, escape(l))
                        for i, l in enumerate(lines))
        self.raw('<text x="%.2f" y="%.2f" font-family="%s" font-size="%.2f" fill="%s" text-anchor="%s" '
                 'font-weight="%d" xml:space="preserve"%s>%s</text>'
                 % (x, y, MONO if mono else FONT, size, color, anchor, weight,
                    ' font-style="italic"' if italic else "", spans))

    def wire(self, pts, kind, w=None, dash=None):
        d = " ".join("%s%.2f,%.2f" % ("M" if i == 0 else "L", x, y) for i, (x, y) in enumerate(pts))
        self.raw('<path d="%s" fill="none" stroke="%s" stroke-width="%.2f" stroke-linejoin="round" '
                 'stroke-linecap="round"%s/>' % (d, COL[kind], w or ANCHO.get(kind, 0.5),
                                                ' stroke-dasharray="%s"' % dash if dash else ""))

    def dot(self, x, y, kind):
        self.raw('<circle cx="%.2f" cy="%.2f" r="%.2f" fill="%s"/>' % (x, y, 0.55 + ANCHO.get(kind, .5) * .4, COL[kind]))

    def flecha(self, x, y, d, kind, s=1.6):
        pts = {"r": [(x, y), (x - s * 1.4, y - s * .8), (x - s * 1.4, y + s * .8)],
               "l": [(x, y), (x + s * 1.4, y - s * .8), (x + s * 1.4, y + s * .8)],
               "d": [(x, y), (x - s * .8, y - s * 1.4), (x + s * .8, y - s * 1.4)],
               "u": [(x, y), (x - s * .8, y + s * 1.4), (x + s * .8, y + s * 1.4)]}[d]
        self.raw('<polygon points="%s" fill="%s"/>' % (" ".join("%.2f,%.2f" % p for p in pts), COL[kind]))

    def tag(self, x, y, s, kind, anchor="start", size=2.6):
        """etiqueta de red: texto en el color de la red."""
        self.t(x, y + size * 0.35, s, size, COL[kind], anchor=anchor, weight=600)

    def panel(self, x, y, w, h, titulo, color=None):
        self.rect(x, y, w, h, COL["panel"], COL["borde"], rx=2.2, sw=0.35)
        self.t(x + 4, y + 7, titulo, 4.2, color or COL["txt"], weight=700)

    def nota(self, x, y, s, size=2.75, color=None):
        self.t(x, y, s, size, color or COL["mute"])

    def caja(self, x, y, w, h, titulo, cuerpo="", fill="modulo", stroke="modulo_b", ts=3.4, bs=2.6):
        self.rect(x, y, w, h, COL[fill], COL[stroke], rx=1.8, sw=0.45)
        self.t(x + w / 2, y + ts + 1.6, titulo, ts, COL["txt"], anchor="middle", weight=700)
        if cuerpo:
            self.t(x + w / 2, y + ts + 1.6 + bs * 1.7, cuerpo, bs, COL["mute"], anchor="middle")

    # componentes
    def resistor(self, x, y, o, ref, valor, kind="ctl", lado=1):
        if o == "v":
            self.wire([(x, y - 6), (x, y - 3.2)], kind); self.wire([(x, y + 3.2), (x, y + 6)], kind)
            self.rect(x - 1.3, y - 3.2, 2.6, 6.4, COL["parte"], COL["txt"], rx=0.3, sw=0.35)
            a = "start" if lado > 0 else "end"
            self.t(x + 2.6 * lado, y - 0.6, ref, 2.5, COL["txt"], anchor=a, weight=700)
            self.t(x + 2.6 * lado, y + 2.6, valor, 2.5, COL["mute"], anchor=a)
            return (x, y - 6), (x, y + 6)
        self.wire([(x - 6, y), (x - 3.2, y)], kind); self.wire([(x + 3.2, y), (x + 6, y)], kind)
        self.rect(x - 3.2, y - 1.3, 6.4, 2.6, COL["parte"], COL["txt"], rx=0.3, sw=0.35)
        self.t(x, y - 2.3, "%s  %s" % (ref, valor), 2.5, COL["txt"], anchor="middle", weight=600)
        return (x - 6, y), (x + 6, y)

    def cap(self, x, y, ref, valor, pol=False, kind="v5", lado=1):
        self.wire([(x, y - 5), (x, y - 0.8)], kind); self.wire([(x, y + 0.8), (x, y + 5)], "gnd")
        self.wire([(x - 2.3, y - 0.8), (x + 2.3, y - 0.8)], "gnd", 0.45)
        if pol:
            self.rect(x - 2.3, y + 0.55, 4.6, 0.7, COL["txt"], None, rx=0)
            self.t(x - 3.4, y - 1.6, "+", 2.6, COL["txt"], anchor="middle", weight=700)
        else:
            self.wire([(x - 2.3, y + 0.8), (x + 2.3, y + 0.8)], "gnd", 0.45)
        a = "start" if lado > 0 else "end"
        self.t(x + 3.2 * lado, y - 0.6, ref, 2.5, COL["txt"], anchor=a, weight=700)
        self.t(x + 3.2 * lado, y + 2.6, valor, 2.5, COL["mute"], anchor=a)
        return (x, y - 5), (x, y + 5)

    def diodo(self, x, y, d, ref, valor, led=None, kind="v5", kind_k=None):
        """d = sentido de la corriente (r, d, l, u): anodo -> catodo. led = color de la luz."""
        rot = {"r": 0, "d": 90, "l": 180, "u": 270}[d]
        luz = ""
        if led:
            luz = "".join('<path d="M%.2f,-2.2 L%.2f,-4.4" stroke="%s" stroke-width="0.35"/>'
                          '<polygon points="%.2f,-4.4 %.2f,-3.5 %.2f,-3.9" fill="%s"/>'
                          % (a, a + 1.4, led, a + 1.4, a + 0.6, a + 1.4, led) for a in (-0.6, 1.0))
        self.raw('<g transform="translate(%.2f,%.2f) rotate(%d)">'
                 '<path d="M-5,0 L-1.6,0" stroke="%s" stroke-width="%.2f"/>'
                 '<path d="M1.6,0 L5,0" stroke="%s" stroke-width="%.2f"/>'
                 '<polygon points="-1.6,-1.8 -1.6,1.8 1.6,0" fill="%s"/>'
                 '<path d="M1.6,-1.8 L1.6,1.8" stroke="%s" stroke-width="0.45"/>%s</g>'
                 % (x, y, rot, COL[kind], ANCHO[kind], COL[kind_k or kind], ANCHO[kind_k or kind],
                    led or COL["txt"], COL["txt"], luz))
        if d in "rl":
            self.t(x, y + 5.2, "%s  %s" % (ref, valor), 2.5, COL["txt"], anchor="middle", weight=600)
        else:
            ox = 6.0 if led else 3.2
            self.t(x + ox, y - 0.4, ref, 2.5, COL["txt"], weight=700)
            self.t(x + ox, y + 2.6, valor, 2.5, COL["mute"])
        dx, dy = {"r": (5, 0), "d": (0, 5), "l": (-5, 0), "u": (0, -5)}[d]
        return (x - dx, y - dy), (x + dx, y + dy)

    def tierra(self, x, y):
        self.wire([(x, y), (x, y + 1.6)], "gnd")
        for i, w_ in enumerate((2.4, 1.6, 0.8)):
            self.wire([(x - w_, y + 1.6 + i * 0.75), (x + w_, y + 1.6 + i * 0.75)], "gnd", 0.4)

    def borna(self, x, y, ref, titulo, pines, lado="r", paso=5.0, ancho=7.0):
        """borna de tornillo: pines = [(num, texto, kind)]. Devuelve {num: punto de conexion}."""
        n = len(pines)
        self.rect(x - ancho / 2, y - paso / 2 - 0.6, ancho, n * paso + 1.2, "#e8f0e0", "#7e9f6a", rx=1.0, sw=0.4)
        pos = {}
        for i, (num, txt, kind) in enumerate(pines):
            yy = y + i * paso
            self.raw('<circle cx="%.2f" cy="%.2f" r="1.5" fill="#ffffff" stroke="#555" stroke-width="0.3"/>'
                     '<path d="M%.2f,%.2f L%.2f,%.2f" stroke="#555" stroke-width="0.3"/>'
                     % (x, yy, x - 1.0, yy + 1.0, x + 1.0, yy - 1.0))
            cx = x + ancho / 2 if lado == "r" else x - ancho / 2
            tx = x - ancho / 2 - 1.2 if lado == "r" else x + ancho / 2 + 1.2
            self.t(tx, yy + 0.9, "%s %s" % (num, txt) if txt else str(num), 2.5, COL[kind] if kind else COL["txt"],
                   anchor="end" if lado == "r" else "start", weight=600)
            pos[num] = (cx, yy)
        self.t(x, y - paso / 2 - 2.0, ref, 2.8, COL["txt"], anchor="middle", weight=700)
        if titulo:
            self.t(x, y + n * paso - paso / 2 + 3.6, titulo, 2.4, COL["mute"], anchor="middle")
        return pos

    def esp32(self, x, y, ref, nombre, pines, paso=8.0, w=34.0):
        """pines: {num: (kind o None)}. Dibuja los 30 pines; devuelve {num: punto}."""
        h = 15 * paso + 6
        self.rect(x, y, w, h, COL["esp"], COL["esp_b"], rx=2.0, sw=0.5)
        self.t(x + w / 2, y + h / 2 - 6, nombre, 3.4, COL["txt"], anchor="middle", weight=700)
        self.t(x + w / 2, y + h / 2 - 1.5, "%s\nDevKit V1\n30 pines" % ref, 2.3, COL["mute"], anchor="middle")
        pos = {}
        for n in range(1, 31):
            izq = n <= 15
            i = (n - 1) % 15
            yy = y + 3 + paso / 2 + i * paso
            px = x if izq else x + w
            kind = pines.get(n)
            self.wire([(px, yy), (px - 2.5 if izq else px + 2.5, yy)], kind or "gnd", 0.4 if not kind else None)
            self.t(px + (1.4 if izq else -1.4), yy + 0.9, "%d %s" % (n, pin_esp(n)) if izq else "%s %d" % (pin_esp(n), n),
                   2.35, COL["txt"] if kind else "#9aa5b1", anchor="start" if izq else "end",
                   weight=600 if kind else 400)
            pos[n] = (px - 2.5 if izq else px + 2.5, yy)
        return pos

    def motor(self, x, y, nombre, sub=""):
        self.raw('<circle cx="%.2f" cy="%.2f" r="5" fill="#fff" stroke="%s" stroke-width="0.6"/>' % (x, y, COL["mot"]))
        self.t(x, y + 1.2, "M", 3.6, COL["mot"], anchor="middle", weight=700)
        self.t(x + 7, y - 0.5, nombre, 2.8, COL["txt"], weight=700)
        if sub:
            self.t(x + 7, y + 3, sub, 2.4, COL["mute"])

    def leyenda(self, x, y, items):
        for i, (kind, txt) in enumerate(items):
            yy = y + i * 4.6
            self.wire([(x, yy), (x + 8, yy)], kind)
            self.t(x + 10, yy + 0.9, txt, 2.6, COL["txt"])

    def svg(self):
        return ('<svg xmlns="http://www.w3.org/2000/svg" width="%dmm" height="%dmm" viewBox="0 0 %d %d">\n%s\n</svg>\n'
                % (W, H, W, H, "\n".join(self.el)))


TOTAL = 4
LEYENDA = [("v12", "12 V batería (motores)"), ("v6", "6 V servos (BEC)"), ("v5", "5 V lógica (step-down)"),
           ("gnd", "GND común"), ("uart", "UART Pi ↔ ESP32"), ("ctl", "control / PWM"),
           ("enc", "encoders"), ("mot", "salidas a motores")]


# ================================================================ hoja 1: alimentacion
def hoja_alimentacion():
    h = Hoja(1, TOTAL, "1 · Alimentación: de dónde sale cada voltaje",
             "Una batería 3S alimenta todo. Cada rama lleva su positivo (color) y su GND (negro); todos los GND "
             "se juntan en un solo punto (estrella).")
    # bateria, fusible, distribucion
    h.caja(14, 128, 40, 30, "Batería LiPo 3S", "11.1 V nominal\n12.6 V llena\n9.9 V: alarma", "pi", "pi_b")
    yb = 137
    h.wire([(54, yb), (60, yb)], "v12"); h.rect(60, yb - 1.6, 10, 3.2, "#fff", COL["v12"], rx=0.8, sw=0.5)
    h.t(65, yb - 3, "Fusible 15 A", 2.5, COL["txt"], anchor="middle", weight=700)
    h.wire([(70, yb), (84, yb)], "v12"); h.wire([(54, yb + 3), (84, yb + 3)], "gnd")
    h.rect(84, 34, 18, 242, "#fbe9e7", "#d7a49a", rx=1.6, sw=0.45)
    h.t(93, 31, "Bloque de distribución", 2.6, COL["txt"], anchor="middle", weight=700)
    h.wire([(89, 40), (89, 270)], "v12", 1.6); h.wire([(97, 40), (97, 270)], "gnd", 1.6)
    h.t(89, 274, "+", 3.4, COL["v12"], anchor="middle", weight=700); h.t(97, 274, "−", 3.4, COL["gnd"], anchor="middle", weight=700)
    h.dot(89, yb, "v12"); h.dot(97, yb + 3, "gnd")

    def rama(y, x2, kind, etiqueta=None):
        h.wire([(89, y), (x2, y)], kind); h.dot(89, y, kind)
        h.wire([(97, y + 3), (x2, y + 3)], "gnd"); h.dot(97, y + 3, "gnd")
        if etiqueta:
            h.t(104, y - 1.4, etiqueta, 2.4, COL[kind], weight=600)

    # rama 1: L298N
    rama(52, 130, "v12", "12 V")
    h.caja(130, 40, 46, 30, "3 × L298N", "puentes H de los motores\nel 12 V NO pasa por\nlas tarjetas")
    h.wire([(176, 52), (196, 52)], "mot"); h.wire([(176, 55), (196, 55)], "mot")
    h.caja(196, 40, 52, 30, "6 motores Pololu 37D", "2 por cada L298N\nhasta 5.5 A c/u al arrancar\n(por eso la rampa)", "parte", "borde")
    # rama 2: step-down 5 V
    rama(112, 130, "v12", "12 V")
    h.caja(130, 100, 46, 30, "Step-down 5 V, 5 A", "12 V → 5 V\nla Pi pide hasta 5 A")
    xs = 186
    h.wire([(176, 112), (xs, 112)], "v5"); h.wire([(176, 115), (xs + 3, 115)], "gnd")
    for (yy, tit, cuerpo) in ((86, "Raspberry Pi 5 (HAT de bornas)", "5V → pines 2 y 4 · GND → pin 6\nTVS SA5.0A en esas bornas"),
                              (112, "Tracción · J5", "+5V → D5 → VIN de la ESP32-A\n+5V → encoders (J7, J8)"),
                              (138, "Servos · J5", "+5V → D6 → VIN de la ESP32-B")):
        h.wire([(xs, 112), (xs, yy), (210, yy)], "v5"); h.wire([(xs + 3, 115), (xs + 3, yy + 3), (210, yy + 3)], "gnd")
        h.caja(210, yy - 9, 74, 22, tit, cuerpo, "placa" if "J5" in tit else "pi", "placa_b" if "J5" in tit else "pi_b",
               ts=3.0, bs=2.5)
    h.dot(xs, 112, "v5"); h.dot(xs + 3, 115, "gnd")
    # rama 3: BEC 6 V
    rama(204, 130, "v12", "12 V")
    h.caja(130, 192, 46, 30, "BEC 6 V, ≥ 10 A", "12 V → 6 V\n8 servos de ~1.2 A al\narrancar")
    h.wire([(176, 204), (210, 204)], "v6"); h.wire([(176, 207), (210, 207)], "gnd")
    h.caja(210, 193, 74, 22, "Servos · J6 → SERVO_V", "C3 + C4 (1000 µF): picos\nLED azul D4: hay 6 V", "placa", "placa_b", ts=3.0, bs=2.5)
    h.wire([(284, 204), (300, 204)], "v6"); h.wire([(284, 207), (300, 207)], "gnd")
    h.caja(300, 193, 70, 22, "8 servos Power HD 1501MG", "V+ (rojo) y GND (café)\nde cada header", "parte", "borde", ts=3.0, bs=2.5)
    # rama 4: medicion de bateria
    rama(244, 210, "v12", "12 V (solo medición)")
    h.caja(210, 233, 74, 22, "Servos · J2 (BAT SENSE)", "divisor 100k / 27k → IO34\nLED rojo D2: hay batería", "placa", "placa_b", ts=3.0, bs=2.5)
    h.nota(104, 258, "Esta rama lleva menos de 10 mA:\ncable delgado, después del fusible.", 2.5)

    # explicaciones
    x0 = 300
    h.panel(x0, 34, 106, 70, "¿Por qué así?")
    h.nota(x0 + 4, 46, "• Los motores toman el 12 V directo del bloque:\n"
                       "  su corriente (hasta 30 A en total) nunca pasa\n  por las tarjetas fresadas.\n"
                       "• El 5 V (step-down) es para la lógica: Pi, las 2\n"
                       "  ESP32 y los encoders. Separado de los motores,\n  el ruido de las escobillas no reinicia nada.\n"
                       "• Los servos tienen su propio 6 V (BEC): al\n"
                       "  arrancar los 8 juntos piden varios amperes y\n  no deben tirar el 5 V de la Pi.\n"
                       "• D5 y D6 (Schottky 1N5819) dejan pasar el 5 V a\n"
                       "  cada ESP32, pero cuando la conectas por USB a la\n"
                       "  PC, su 5 V no regresa a la Pi ni a los encoders.\n"
                       "• GND en estrella: todos los negativos llegan al\n"
                       "  bloque. Así la Pi y las ESP32 comparten la misma\n  referencia para el UART.", 2.65, COL["txt"])
    h.panel(x0, 110, 106, 34, "Colores")
    h.leyenda(x0 + 6, 123, LEYENDA[:4])
    h.leyenda(x0 + 58, 123, LEYENDA[4:])
    h.panel(x0, 150, 106, 38, "Al encender por primera vez")
    h.nota(x0 + 4, 161, "1. Sin módulos: continuidad 5V–GND y 6V–GND\n   (no debe pitar).\n"
                        "2. Fuente limitada a 0.5 A: revisa 5 V en J5 y 6 V\n   en J6 antes de poner la Pi y las ESP32.\n"
                        "3. Los LED D3 (verde), D4 (azul) y D2 (rojo)\n   te dicen qué voltaje está presente.", 2.65, COL["txt"])
    return h


# ================================================================ hoja 2: senales
def hoja_senales():
    h = Hoja(2, TOTAL, "2 · Señales: la Raspberry Pi coordina a las 2 ESP32",
             "La Pi manda órdenes de texto por 2 UART (una por tarjeta). Cada ESP32 genera los PWM y lee sus "
             "sensores; si la Pi deja de hablar, la tracción se detiene sola.")
    # Pi
    h.caja(14, 112, 64, 74, "Raspberry Pi 5", "", "pi", "pi_b")
    h.t(46, 124, "coordina: decide la velocidad\nde cada motor y la posición\nde cada servo", 2.5, COL["mute"], anchor="middle")
    h.t(46, 138, "HAT de bornas (GPIO 2x20)", 2.4, COL["txt"], anchor="middle", weight=700)
    pi_rows = [("pin 6  · GND", 144, "gnd"), ("pin 29 · GPIO5 RXD2", 149, "uart"), ("pin 7  · GPIO4 TXD2", 154, "uart"),
               ("pin 34 · GND", 166, "gnd"), ("pin 32 · GPIO12 TXD4", 171, "uart"), ("pin 33 · GPIO13 RXD4", 176, "uart")]
    for txt, yy, kind in pi_rows:
        h.t(76, yy + 0.9, txt, 2.4, COL[kind], anchor="end", weight=600, mono=True)
    # tarjeta de traccion
    tx, ty, tw, th = 112, 30, 118, 124
    h.rect(tx, ty, tw, th, COL["placa"], COL["placa_b"], rx=2.4, sw=0.6)
    h.t(tx + 4, ty + 7, "Tarjeta de TRACCIÓN", 4.0, COL["txt"], weight=700)
    ex, ey = 150, 52
    j9 = h.borna(tx + 12, 118, "J9", "PI (UART2)", [(1, "", "gnd"), (2, "", "uart"), (3, "", "uart")], lado="l", ancho=6)
    # Pi -> J9 sin cruces: GND (pin 6) a J9-1, RXD2 (pin 29) a J9-2, TXD2 (pin 7) a J9-3
    for (yy, k, xv, kind) in ((144, 1, 92, "gnd"), (149, 2, 97, "uart"), (154, 3, 102, "uart")):
        h.wire([(78, yy), (xv, yy), (xv, j9[k][1]), j9[k]], kind)
    h.flecha(79.5, 149, "l", "uart"); h.flecha(j9[3][0] - 0.2, j9[3][1], "r", "uart")
    h.t(46, 192, "cada UART: cable trenzado de 3 hilos, < 50 cm", 2.3, COL["uart"], anchor="middle")
    # J9 -> ESP32-A (dentro de la tarjeta)
    xr = tx + 15
    h.wire([(xr, j9[2][1]), (ex, j9[2][1])], "uart"); h.flecha(xr + 0.2, j9[2][1], "l", "uart")
    h.wire([(xr, j9[3][1]), (ex, j9[3][1])], "uart"); h.flecha(ex - 0.2, j9[3][1], "r", "uart")
    h.t(ex - 1.5, j9[2][1] - 1.0, "%s TX · R14" % gpio(T, "U2", "ESPA_TX"), 2.2, COL["uart"], anchor="end")
    h.t(ex - 1.5, j9[3][1] + 3.2, "%s RX · R13" % gpio(T, "U2", "ESPA_RX"), 2.2, COL["uart"], anchor="end")
    # ESP32-A
    h.caja(ex, ey, 36, 90, "ESP32-A", "", "esp", "esp_b")
    h.t(ex + 18, ey + 14, "genera 12 PWM\n(2 por motor) a\n10 kHz y cuenta\nlos pulsos de\nlos 6 encoders", 2.5, COL["mute"], anchor="middle")
    h.t(ex + 18, ey + 44, "MOTOR_EN arranca\nen LOW (R21 10k):\nnada se mueve\nhasta \"EN 1\"", 2.5, COL["ctl"], anchor="middle")
    # bornas L298N en la orilla derecha
    lx = 262
    filas = [("J41", "U4", "L298N #1", "M1", "Delantero izq.", "M2", "Delantero der.", 46),
             ("J42", "U5", "L298N #2", "M3", "Medio izq.", "M4", "Medio der.", 84),
             ("J43", "U6", "L298N #3", "M5", "Trasero izq.", "M6", "Trasero der.", 122)]
    ymot = {}
    for (jref, u, nom, ma, na, mb, nb, yy) in filas:
        ins = "  ".join(gpio(T, "U2", "%s_IN%d" % (u, k)) for k in (1, 2, 3, 4))
        h.wire([(ex + 36, yy), (lx, yy)], "ctl", 1.2)
        h.t(ex + 38, yy - 1.4, "IN1–IN4: " + ins, 2.25, COL["ctl"], weight=600)
        h.t(ex + 38, yy + 3.4, "+ EN + GND", 2.25, COL["ctl"])
        h.rect(tx + tw - 3, yy - 3.5, 6, 7, "#e8f0e0", "#7e9f6a", rx=0.8, sw=0.4)
        h.t(tx + tw, yy - 4.8, jref, 2.6, COL["txt"], anchor="middle", weight=700)
        h.caja(lx, yy - 13, 38, 26, nom, "ENA+ENB ← EN (Y)\nIN1/IN2 → motor A\nIN3/IN4 → motor B", ts=3.0, bs=2.35)
        h.wire([(lx - 14, 36), (lx - 14, yy - 9), (lx, yy - 9)], "v12")
        h.wire([(lx + 38, yy - 5), (330, yy - 5), (330, yy - 9)], "mot"); h.wire([(lx + 38, yy + 5), (330, yy + 5), (330, yy + 8)], "mot")
        h.motor(335, yy - 9, "%s  %s" % (ma, na), "OUT1/OUT2"); h.motor(335, yy + 8, "%s  %s" % (mb, nb), "OUT3/OUT4")
        ymot[ma] = yy - 9; ymot[mb] = yy + 8
    h.t(lx - 16, 35, "12 V del bloque", 2.4, COL["v12"], anchor="end", weight=600)
    # encoders de vuelta: cada motor baja de su circulo a su bus
    for (grupo, xb, yb, jref, jx, xin, ms) in (("M1–M3", 404, 166, "J7", 170, 170, ("M1", "M2", "M3")),
                                                ("M4–M6", 398, 160, "J8", 205, 180, ("M4", "M5", "M6"))):
        for m in ms:
            yy = ymot[m]
            h.wire([(335, yy + 5), (335, yy + 7.2), (xb, yy + 7.2)], "enc"); h.dot(xb, yy + 7.2, "enc")
        h.wire([(xb, ymot[ms[0]] + 7.2), (xb, yb), (jx, yb), (jx, ty + th)], "enc", 1.0)
        h.rect(jx - 4, ty + th - 3, 8, 6, "#e8f0e0", "#7e9f6a", rx=0.8, sw=0.4)
        h.t(jx - 5, ty + th - 0.2, jref, 2.6, COL["txt"], anchor="end", weight=700)
        h.t(jx + 3, yb + 3.6, "encoders %s: canal A + 5V + GND" % grupo, 2.35, COL["enc"], weight=600)
        h.wire([(jx, ty + th - 3), (jx, ty + th - 6), (xin, ty + th - 6), (xin, ey + 90)], "enc")
    h.t(ex + 60, ty + th - 7.5, "divisores 10k/20k: 5 V → 3.3 V", 2.3, COL["enc"])
    # tarjeta de servos
    sx, sy, sw_, sh = 112, 178, 118, 100
    h.rect(sx, sy, sw_, sh, COL["placa"], COL["placa_b"], rx=2.4, sw=0.6)
    h.t(sx + 4, sy + 7, "Tarjeta de SERVOS", 4.0, COL["txt"], weight=700)
    j9s = h.borna(sx + 12, 200, "J9", "PI (UART4)", [(1, "", "gnd"), (2, "", "uart"), (3, "", "uart")], lado="l", ancho=6)
    # Pi -> J9 sin cruces: GND (pin 34) a J9-1, TXD4 (pin 32) a J9-2, RXD4 (pin 33) a J9-3
    for (yy, k, xv, kind) in ((166, 1, 102, "gnd"), (171, 2, 97, "uart"), (176, 3, 92, "uart")):
        h.wire([(78, yy), (xv, yy), (xv, j9s[k][1]), j9s[k]], kind)
    h.flecha(j9s[2][0] - 0.2, j9s[2][1], "r", "uart"); h.flecha(79.5, 176, "l", "uart")
    bx, by = 150, 196
    h.caja(bx, by, 36, 66, "ESP32-B", "", "esp", "esp_b")
    h.t(bx + 18, by + 14, "8 PWM de servo\n(50 Hz, 800 a\n2200 µs) y lee\nla batería por\nel ADC (IO34)", 2.5, COL["mute"], anchor="middle")
    h.wire([(xr, j9s[2][1]), (bx, j9s[2][1])], "uart"); h.flecha(bx - 0.2, j9s[2][1], "r", "uart")
    h.wire([(xr, j9s[3][1]), (bx, j9s[3][1])], "uart"); h.flecha(xr + 0.2, j9s[3][1], "l", "uart")
    h.t(bx - 1.5, j9s[2][1] - 1.0, "%s RX · R15" % gpio(S, "U3", "ESPB_RX"), 2.2, COL["uart"], anchor="end")
    h.t(bx - 1.5, j9s[3][1] + 3.2, "%s TX · R16" % gpio(S, "U3", "ESPB_TX"), 2.2, COL["uart"], anchor="end")
    # servos
    for i, n in enumerate(range(1, 9)):
        fila, col = (0, i) if n <= 4 else (1, i - 4)
        x = 262 + col * 37
        y = 196 + fila * 44
        g, desc = D.SERVOS[n]
        desc = desc.replace("Direccion", "Dirección").replace("muneca", "muñeca")
        h.rect(x, y, 32, 20, "#fff", COL["borde"], rx=1.6, sw=0.45)
        h.t(x + 16, y + 6, "S%d · J%d" % (n, 30 + n), 2.8, COL["txt"], anchor="middle", weight=700)
        h.t(x + 16, y + 10.5, desc, 2.4, COL["mute"], anchor="middle")
        h.t(x + 16, y + 15.5, gpio(S, "U3", "SERVO%d" % n), 2.5, COL["ctl"], anchor="middle", weight=700)
    for fila in (0, 1):
        yy = 206 + fila * 44
        h.wire([(bx + 36, by + 20 + fila * 20), (240, by + 20 + fila * 20), (240, yy), (262, yy)], "ctl", 1.2)
        h.t(bx + 38, by + 18.6 + fila * 20, "4 señales PWM", 2.3, COL["ctl"])
    h.t(262, 192, "Dirección (las 4 ruedas de las esquinas)", 2.7, COL["txt"], weight=700)
    h.t(262, 236, "Brazo robot (4 ejes)", 2.7, COL["txt"], weight=700)
    # protocolo
    h.panel(14, 30, 92, 76, "Qué se dicen (115200 baud, 8N1)", COL["uart"])
    h.t(18, 42, "Pi → ESP32-A (tracción)", 2.7, COL["txt"], weight=700)
    h.t(18, 47, "EN 1            habilita motores\nM p1 … p6       −1000…1000 por motor\nSTOP            rampa a 0 y apaga\n"
                "T c1…c6 v1…v6 f ← cuentas y pulsos/s", 2.4, COL["txt"], mono=True)
    h.t(18, 71, "Pi → ESP32-B (servos)", 2.7, COL["txt"], weight=700)
    h.t(18, 76, "S n us           servo n en µs\nA n grados       servo n en grados\nB mv f         ← batería en mV",
        2.4, COL["txt"], mono=True)
    h.nota(18, 94, "Una línea de texto por mensaje; *HH opcional\n(checksum XOR, como NMEA).", 2.4)
    h.panel(14, 216, 92, 64, "Seguridad")
    h.nota(18, 227, "• Watchdog: si la Pi no manda nada en 300 ms,\n  la ESP32-A baja los motores a 0 y MOTOR_EN\n  a LOW.\n"
                    "• R21 10k mantiene MOTOR_EN en LOW mientras\n  la ESP32 arranca o se programa.\n"
                    "• Rampa: de 0 a 1000 en 400 ms (protege al\n  L298N del pico de arranque).\n"
                    "• Bloqueo: PWM alto sin pulsos de encoder\n  600 ms → avisa a la Pi.\n"
                    "• 1k en cada línea del UART: si un pin queda\n  mal configurado, limita la corriente.", 2.55, COL["txt"])
    return h


# ================================================================ hoja 3: traccion por dentro
def hoja_traccion():
    h = Hoja(3, TOTAL, "3 · Tarjeta de TRACCIÓN por dentro",
             "ESP32-A, bornas de los 3 L298N, 6 divisores de encoder, entrada de 5 V y enlace UART2 con la Pi. "
             "Números de pin y valores tal cual están en la PCB.")
    # --- panel A: entrada 5 V
    h.panel(14, 28, 128, 92, "1 · Entrada 5 V")
    j5 = h.borna(28, 52, "J5", "del step-down", [(1, "+5V", "v5"), (2, "GND", "gnd")], lado="r")
    yv, yg = 46, 106
    h.wire([j5[1], (j5[1][0] + 3, j5[1][1]), (j5[1][0] + 3, yv), (122, yv)], "v5")
    h.wire([j5[2], (j5[2][0] + 1.5, j5[2][1]), (j5[2][0] + 1.5, yg), (122, yg)], "gnd")
    c2 = parte(T, a="+5V", b="GND") if False else "C2"
    a, b = h.cap(52, 76, c2, val(T, c2).replace("uF", " µF"), pol=True)
    h.wire([(52, yv), a], "v5"); h.wire([b, (52, yg)], "gnd"); h.dot(52, yv, "v5"); h.dot(52, yg, "gnd")
    r25 = parte(T, a="+5V", b="LED5_A"); d3 = parte(T, a="GND", b="LED5_A")
    a, b = h.resistor(74, 60, "v", r25, val(T, r25), "v5")
    h.wire([(74, yv), a], "v5"); h.dot(74, yv, "v5")
    da, dk = h.diodo(74, 84, "d", d3, "LED verde", led="#2e7d32", kind="v5", kind_k="gnd")
    h.wire([b, da], "v5"); h.wire([dk, (74, yg)], "gnd"); h.dot(74, yg, "gnd")
    d5 = parte(T, a="VIN_A", b="+5V")
    da, dk = h.diodo(104, 64, "d", d5, "1N5819", kind="v5")
    h.wire([(104, yv), da], "v5"); h.dot(104, yv, "v5")
    h.wire([dk, (104, 76)], "v5"); h.tag(106, 76, "VIN_A → pin 15 (VIN) ESP32-A", "v5", size=2.3)
    h.wire([(122, yv), (122, 40)], "v5"); h.tag(120, 37.5, "+5V → encoders (J7-4, J8-2)", "v5", anchor="end", size=2.3)
    h.tierra(122, yg)
    h.nota(18, 114, "C2: reserva para picos.  D3: \"hay 5 V\" (~9 mA).  D5: el 5 V entra a la ESP32 pero\n"
                    "el del USB no regresa a la tarjeta cuando la programas.", 2.4)
    # --- panel B: UART2
    h.panel(14, 126, 128, 68, "2 · Enlace con la Pi (UART2)", COL["uart"])
    j9 = h.borna(62, 146, "J9", "PI (UART2)", [(1, "GND", "gnd"), (2, "RXD2", "uart"), (3, "TXD2", "uart")], lado="r")
    for k, txt in ((1, "Pi pin 6 (GND)"), (2, "Pi pin 29 (GPIO5)"), (3, "Pi pin 7 (GPIO4)")):
        h.t(46, j9[k][1] + 0.9, txt, 2.4, COL["mute"], anchor="end")
    h.wire([j9[1], (76, j9[1][1])], "gnd"); h.tierra(76, j9[1][1])
    r14 = parte(T, a="ESPA_TX", b="PI_RXD2"); r13 = parte(T, a="PI_TXD2", b="ESPA_RX")
    a, b = h.resistor(86, j9[2][1], "h", r14, val(T, r14), "uart"); h.wire([j9[2], a], "uart"); h.wire([b, (110, j9[2][1])], "uart")
    h.flecha(j9[2][0] + 3.6, j9[2][1], "l", "uart")
    h.tag(111, j9[2][1], "%s = TX" % gpio(T, "U2", "ESPA_TX"), "uart")
    a, b = h.resistor(86, j9[3][1] + 4, "h", r13, val(T, r13), "uart")
    h.wire([j9[3], (74, j9[3][1]), (74, j9[3][1] + 4), a], "uart"); h.wire([b, (110, j9[3][1] + 4)], "uart")
    h.flecha(110, j9[3][1] + 4, "r", "uart")
    h.tag(111, j9[3][1] + 4, "%s = RX" % gpio(T, "U2", "ESPA_RX"), "uart")
    h.nota(18, 182, "El TX de uno va al RX del otro (cruzado). 1k en serie: si un pin queda como\n"
                    "salida por error, la corriente queda en ~3 mA y nada se daña.", 2.4)
    # --- panel C: ESP32-A
    h.panel(148, 28, 104, 166, "3 · ESP32-A")
    tipo = {}
    for n, net in T["U2"]["pins"].items():
        if not net:
            continue
        tipo[int(n)] = ("gnd" if net == "GND" else "v5" if net.startswith("VIN") else "uart" if "ESPA" in net
                        else "enc" if net.startswith("ENC") else "ctl")
    ep = h.esp32(178, 38, "U2", "ESP32-A", tipo, paso=9.6, w=42)
    for n, (x, y) in ep.items():
        net = T["U2"]["pins"].get(str(n))
        if not net:
            continue
        izq = n <= 15
        txt = {"VIN_A": "VIN_A (D5)", "MOTOR_EN": "MOTOR_EN (J41-43)"}.get(net, net)
        if net.startswith("ENC"):
            txt = net.replace("_A", "") + " (M%s)" % net[3]
        if "_IN" in net:
            u, k = net.split("_IN")
            txt = "%s → %s-%d" % (net.replace("U4", "#1").replace("U5", "#2").replace("U6", "#3"),
                                  {"U4": "J41", "U5": "J42", "U6": "J43"}[u], pin_de(T, {"U4": "J41", "U5": "J42", "U6": "J43"}[u], net))
        h.t(x - 0.8 if izq else x + 0.8, y + 0.9, txt, 2.25, COL[tipo[n]], anchor="end" if izq else "start", weight=600)
    h.nota(152, 190, "Gris = pin libre. IO12 libre: debe estar en LOW al arrancar.", 2.3)
    # --- panel D: bornas L298N
    h.panel(258, 28, 148, 166, "4 · Bornas de los L298N (1 por módulo)")
    r21 = parte(T, a="MOTOR_EN", b="GND")
    xen = 272
    ys = (46, 84, 122)
    for (jref, u, nom, yy) in (("J41", "U4", "L298N #1  (M1 / M2)", ys[0]), ("J42", "U5", "L298N #2  (M3 / M4)", ys[1]),
                               ("J43", "U6", "L298N #3  (M5 / M6)", ys[2])):
        pins = [(k, {1: "EN", 6: "GND"}.get(k, T[jref]["pins"][str(k)].split("_")[-1]),
                 "ctl" if k < 6 else "gnd") for k in range(1, 7)]
        jp = h.borna(300, yy, jref, None, pins, lado="r", paso=4.6)
        h.wire([(xen, jp[1][1]), (296.5 - 7, jp[1][1])], "ctl")
        h.dot(xen, jp[1][1], "ctl")
        for k in range(2, 6):
            h.t(286, jp[k][1] + 0.9, "", 2)
        # modulo
        mx = 322
        h.rect(mx, yy - 5, 40, 30, COL["modulo"], COL["modulo_b"], rx=1.6, sw=0.45)
        h.t(mx + 20, yy - 6.6, nom, 2.6, COL["txt"], anchor="middle", weight=700)
        rows = [("ENA", 1, -1.6), ("ENB", 1, 1.6), ("IN4", 2, 0), ("IN3", 3, 0), ("IN2", 4, 0), ("IN1", 5, 0), ("GND", 6, 0)]
        for lbl, k, dy in rows:
            yr = jp[k][1] + dy
            h.t(mx + 1.8, yr + 0.9, lbl, 2.2, COL["txt"], weight=600)
            h.raw('<circle cx="%.2f" cy="%.2f" r="0.6" fill="%s"/>' % (mx, yr, COL["txt"]))
            kind = "gnd" if k == 6 else "ctl"
            if k == 1:
                h.wire([(mx - 6, jp[1][1]), (mx - 6, yr), (mx, yr)], kind, 0.45)
            else:
                h.wire([jp[k], (mx, yr)], kind, 0.45)
        h.wire([jp[1], (mx - 6, jp[1][1])], "ctl", 0.45); h.dot(mx - 6, jp[1][1], "ctl")
        h.t(mx - 3, jp[1][1] - 2.4, "Y", 2.2, COL["ctl"], anchor="middle", weight=700)
        h.t(mx + 24, yy + 6, "quita los 2\njumpers de\nENA/ENB y une\nambos al EN", 2.2, COL["mute"], anchor="middle")
        h.t(mx + 42, yy + 2, "OUT1/OUT2\n→ motor A\n(izquierdo)\n\nOUT3/OUT4\n→ motor B\n(derecho)", 2.2, COL["mot"])
    h.wire([(xen, ys[0] - 4), (xen, ys[2] + 6)], "ctl")
    h.tag(xen - 1, ys[0] - 6, "MOTOR_EN (%s)" % gpio(T, "U2", "MOTOR_EN"), "ctl", anchor="start", size=2.4)
    a, b = h.resistor(xen, ys[2] + 12, "v", r21, val(T, r21), "ctl", lado=-1)
    h.wire([b, (xen, ys[2] + 20)], "gnd"); h.tierra(xen, ys[2] + 20)
    # tabla de verdad
    ty0 = 162
    h.t(262, ty0, "Cómo se mueve cada motor (EN = 1):", 2.7, COL["txt"], weight=700)
    h.t(262, ty0 + 5, "IN1     IN2     motor A\nPWM     0       gira en un sentido (velocidad = PWM)\n0       PWM     gira al revés\n"
                      "0       0       freno          EN = 0 → motor suelto", 2.4, COL["txt"], mono=True)
    h.nota(262, ty0 + 25, "IN3/IN4 hacen lo mismo con el motor B. Si un lado gira al revés, invierte OUT1/OUT2.", 2.3)
    # --- panel E: encoders
    h.panel(14, 200, 392, 84, "5 · Encoders: bajar el canal A de 5 V a 3.3 V (6 divisores iguales)", COL["enc"])
    # un divisor en detalle
    r1 = parte(T, a="ENC1_A5V", b="ENC1_A"); r7 = parte(T, a="ENC1_A", b="GND")
    c11 = [r for r, c in T.items() if r.startswith("C") and sorted(c["pins"].values()) == ["ENC1_A", "GND"]][0]
    h.t(22, 215, "J7-%d" % pin_de(T, "J7", "ENC1_A5V"), 2.6, COL["txt"], weight=700)
    h.tag(22, 219, "ENC1_A5V (0 / 5 V)", "enc")
    h.wire([(48, 219), (56, 219), (56, 222)], "enc")
    a, b = h.resistor(56, 228, "v", r1, val(T, r1), "enc")
    h.wire([b, (56, 240)], "enc"); h.dot(56, 240, "enc")
    a2, b2 = h.resistor(56, 252, "v", r7, val(T, r7), "enc", lado=-1)
    h.wire([(56, 240), a2], "enc"); h.wire([b2, (56, 266), (72, 266)], "gnd")
    a3, b3 = h.cap(72, 252, c11, val(T, c11), kind="enc")
    h.wire([(56, 240), (72, 240), a3], "enc"); h.wire([b3, (72, 266)], "gnd"); h.tierra(64, 266)
    h.wire([(72, 240), (92, 240)], "enc"); h.flecha(92, 240, "r", "enc")
    h.tag(94, 240, "ENC1_A → %s" % gpio(T, "U2", "ENC1_A"), "enc")
    h.nota(96, 250, "V = 5 V × 20k / (10k + 20k) = 3.33 V\n(la ESP32 aguanta 3.6 V como máximo)\n"
                    "10k ∥ 20k = 6.7k con 1 nF: filtro a ~24 kHz.\nLa señal real llega a ~2.7 kHz: pasa entera.", 2.4, COL["txt"])
    # tabla
    x0, y0 = 172, 214
    cols = [("Motor", 0), ("Borna-pin", 22), ("10k", 44), ("20k", 58), ("1 nF", 72), ("GPIO", 88), ("Rueda", 106)]
    for txt, dx in cols:
        h.t(x0 + dx, y0, txt, 2.6, COL["txt"], weight=700)
    ruedas = {1: "delantera izq.", 2: "delantera der.", 3: "media izq.", 4: "media der.", 5: "trasera izq.", 6: "trasera der."}
    for m in range(1, 7):
        yy = y0 + 5 + m * 4.8 - 4.8
        j = "J7" if m <= 3 else "J8"
        ra = parte(T, a="ENC%d_A5V" % m, b="ENC%d_A" % m); rb = parte(T, a="ENC%d_A" % m, b="GND")
        cc = [r for r, c in T.items() if r.startswith("C") and sorted(c["pins"].values()) == ["ENC%d_A" % m, "GND"]][0]
        fila = ["M%d" % m, "%s-%d" % (j, pin_de(T, j, "ENC%d_A5V" % m)), ra, rb, cc, gpio(T, "U2", "ENC%d_A" % m), ruedas[m]]
        for (txt, dx), v in zip(cols, fila):
            h.t(x0 + dx, yy, v, 2.5, COL["enc"] if dx == 88 else COL["txt"], weight=600 if dx in (0, 88) else 400)
    h.t(x0 + 140, y0, "Bornas de encoders", 2.6, COL["txt"], weight=700)
    h.t(x0 + 140, y0 + 5, "J7: 1 A(M1) · 2 A(M2) · 3 A(M3)\n    4 +5V · 5 GND\nJ8: 1 GND · 2 +5V\n    3 A(M6) · 4 A(M5) · 5 A(M4)",
        2.4, COL["txt"], mono=True)
    h.nota(x0 + 140, y0 + 28, "Cable Pololu 37D: verde GND, azul VCC,\namarillo canal A, blanco canal B (sin usar:\n"
                              "el sentido lo sabe el firmware).", 2.35)
    return h


# ================================================================ hoja 4: servos por dentro
def hoja_servos():
    h = Hoja(4, TOTAL, "4 · Tarjeta de SERVOS por dentro",
             "ESP32-B, 8 headers de servo con su riel de 6 V, medición de batería, entrada de 5 V y enlace "
             "UART4 con la Pi.")
    # panel A: 5 V
    h.panel(14, 28, 128, 50, "1 · Entrada 5 V")
    j5 = h.borna(28, 50, "J5", "del step-down", [(1, "+5V", "v5"), (2, "GND", "gnd")], lado="r")
    d6 = parte(S, a="VIN_B", b="+5V")
    da, dk = h.diodo(70, j5[1][1], "r", d6, "1N5819", kind="v5")
    h.wire([j5[1], da], "v5"); h.wire([dk, (92, j5[1][1])], "v5"); h.flecha(92, j5[1][1], "r", "v5")
    h.tag(94, j5[1][1], "VIN_B → pin 15", "v5", size=2.4)
    h.wire([j5[2], (40, j5[2][1]), (40, 66)], "gnd"); h.tierra(40, 66)
    h.nota(50, 66, "D6: el USB de la ESP32 no regresa al 5 V.", 2.4)
    # panel B: UART4
    h.panel(14, 84, 128, 66, "2 · Enlace con la Pi (UART4)", COL["uart"])
    j9 = h.borna(62, 104, "J9", "PI (UART4)", [(1, "GND", "gnd"), (2, "TXD4", "uart"), (3, "RXD4", "uart")], lado="r")
    for k, txt in ((1, "Pi pin 34 (GND)"), (2, "Pi pin 32 (GPIO12)"), (3, "Pi pin 33 (GPIO13)")):
        h.t(46, j9[k][1] + 0.9, txt, 2.4, COL["mute"], anchor="end")
    h.wire([j9[1], (76, j9[1][1])], "gnd"); h.tierra(76, j9[1][1])
    r15 = parte(S, a="ESPB_RX", b="PI_TXD4"); r16 = parte(S, a="ESPB_TX", b="PI_RXD4")
    a, b = h.resistor(86, j9[2][1], "h", r15, val(S, r15), "uart"); h.wire([j9[2], a], "uart"); h.wire([b, (110, j9[2][1])], "uart")
    h.flecha(110, j9[2][1], "r", "uart"); h.tag(111, j9[2][1], "%s = RX" % gpio(S, "U3", "ESPB_RX"), "uart")
    a, b = h.resistor(86, j9[3][1] + 4, "h", r16, val(S, r16), "uart")
    h.wire([j9[3], (74, j9[3][1]), (74, j9[3][1] + 4), a], "uart"); h.wire([b, (110, j9[3][1] + 4)], "uart")
    h.flecha(j9[3][0] + 3.6 + 4, j9[3][1] + 4, "l", "uart")
    h.tag(111, j9[3][1] + 4, "%s = TX" % gpio(S, "U3", "ESPB_TX"), "uart")
    h.nota(18, 140, "Igual que en tracción: cruzado y con 1k en serie.", 2.4)
    # panel C: bateria
    h.panel(14, 156, 128, 128, "3 · Batería: medir 12 V con un pin de 3.3 V", COL["v12"])
    j2 = h.borna(28, 178, "J2", "derivación\nde batería", [(2, "VBAT", "v12"), (1, "GND", "gnd")], lado="r")
    yb, yg = 172, 262
    h.wire([j2[2], (j2[2][0] + 3, j2[2][1]), (j2[2][0] + 3, yb), (110, yb)], "v12")
    h.wire([j2[1], (j2[1][0] + 1.5, j2[1][1]), (j2[1][0] + 1.5, yg), (110, yg)], "gnd")
    r22 = parte(S, a="VBAT_F", b="VBAT_SENSE"); r23 = parte(S, a="VBAT_SENSE", b="GND")
    c5 = [r for r, c in S.items() if r.startswith("C") and sorted(c["pins"].values()) == ["GND", "VBAT_SENSE"]][0]
    a, b = h.resistor(56, 190, "v", r22, val(S, r22), "v12", lado=-1)
    h.wire([(56, yb), a], "v12"); h.dot(56, yb, "v12")
    h.wire([b, (56, 206)], "ctl"); h.dot(56, 206, "ctl")
    a, b = h.resistor(56, 224, "v", r23, val(S, r23), "ctl", lado=-1)
    h.wire([(56, 206), a], "ctl"); h.wire([b, (56, yg)], "gnd"); h.dot(56, yg, "gnd")
    a, b = h.cap(70, 224, c5, val(S, c5).replace("nF", " nF"), kind="ctl")
    h.wire([(56, 206), (70, 206), a], "ctl"); h.wire([b, (70, yg)], "gnd"); h.dot(70, yg, "gnd")
    h.wire([(70, 206), (82, 206)], "ctl"); h.flecha(82, 206, "r", "ctl")
    h.tag(84, 206, "VBAT_SENSE → %s" % gpio(S, "U3", "VBAT_SENSE"), "ctl", size=2.4)
    r24 = parte(S, a="VBAT_F", b="LED12_A"); d2 = parte(S, a="GND", b="LED12_A")
    a, b = h.resistor(110, 186, "v", r24, val(S, r24), "v12", lado=-1)
    h.wire([(110, yb), a], "v12")
    da, dk = h.diodo(110, 236, "d", d2, "LED rojo", led="#c62828", kind="v12", kind_k="gnd")
    h.wire([b, da], "v12"); h.wire([dk, (110, yg)], "gnd"); h.tierra(90, yg)
    h.nota(84, 213, "12.6 V × 27k / 127k\n= 2.68 V en el ADC.\nSatura con 15.5 V.\nC5 estabiliza.", 2.3, COL["txt"])
    h.nota(18, 274, "D2 + R24: \"hay batería\" (~5 mA). Bajo 9.9 V la ESP32-B avisa a la Pi (B mv 1).", 2.35)
    # panel D: riel de 6 V
    h.panel(148, 28, 258, 50, "4 · Riel de 6 V de los servos (SERVO_V)", COL["v6"])
    j6 = h.borna(162, 52, "J6", "BEC 6 V", [(2, "+6V", "v6"), (1, "GND", "gnd")], lado="r")
    yv, yg2 = 44, 70
    h.wire([j6[2], (j6[2][0] + 3, j6[2][1]), (j6[2][0] + 3, yv), (330, yv)], "v6")
    h.wire([j6[1], (j6[1][0] + 1.5, j6[1][1]), (j6[1][0] + 1.5, yg2), (330, yg2)], "gnd")
    for xc, ref in ((196, "C3"), (222, "C4")):
        a, b = h.cap(xc, 57, ref, val(S, ref).replace("uF", " µF"), pol=True, kind="v6")
        h.wire([(xc, yv), a], "v6"); h.wire([b, (xc, yg2)], "gnd"); h.dot(xc, yv, "v6"); h.dot(xc, yg2, "gnd")
    r26 = parte(S, a="SERVO_V", b="LEDS_A"); d4 = parte(S, a="GND", b="LEDS_A")
    a, b = h.resistor(256, yv + 6, "v", r26, val(S, r26), "v6")
    h.wire([(256, yv), a], "v6"); h.dot(256, yv, "v6")
    da, dk = h.diodo(256, yv + 17, "d", d4, "LED azul", led="#1565c0", kind="v6", kind_k="gnd")
    h.wire([b, da], "v6"); h.wire([dk, (256, yg2)], "gnd"); h.dot(256, yg2, "gnd")
    h.wire([(330, yv), (338, yv)], "v6"); h.flecha(338, yv, "r", "v6"); h.tag(340, yv, "V+ de J31…J38 (pin 2)", "v6", size=2.4)
    h.wire([(330, yg2), (338, yg2)], "gnd"); h.flecha(338, yg2, "r", "gnd"); h.tag(340, yg2, "GND de J31…J38 (pin 1)", "gnd", size=2.4)
    h.nota(292, 56, "C3, C4: absorben el pico\nde arranque de los servos.", 2.35)
    # panel E: ESP32-B y servos
    h.panel(148, 84, 258, 200, "5 · ESP32-B y los 8 servos")
    tipo = {}
    for n, net in S["U3"]["pins"].items():
        if net:
            tipo[int(n)] = ("gnd" if net == "GND" else "v5" if net.startswith("VIN") else "uart" if "ESPB" in net
                            else "ctl")
    ep = h.esp32(184, 94, "U3", "ESP32-B", tipo, paso=11.0)
    for n, (x, y) in ep.items():
        net = S["U3"]["pins"].get(str(n))
        if net and n <= 15:
            h.t(x - 0.8, y + 0.9, {"VIN_B": "VIN_B (D6)", "VBAT_SENSE": "VBAT_SENSE"}.get(net, net), 2.3,
                COL[tipo[n]], anchor="end", weight=600)
    xh, xv, xg = 300, 307, 310
    ys = []
    for n in range(1, 9):
        net = "SERVO%d" % n
        x, y = ep[pin_de(S, "U3", net)]
        g, desc = D.SERVOS[n]
        desc = desc.replace("Direccion", "Dirección").replace("muneca", "muñeca")
        # header 1x3: SIG a la altura del pin, V+ y GND debajo
        h.rect(xh - 2.6, y - 2.0, 5.2, 10.0, "#e8f0e0", "#7e9f6a", rx=0.8, sw=0.4)
        for i, (lbl, kind) in enumerate((("3 SIG", "ctl"), ("2 V+", "v6"), ("1 GND", "gnd"))):
            yy = y + i * 3.0
            h.raw('<rect x="%.2f" y="%.2f" width="1.6" height="1.6" fill="#555"/>' % (xh - 0.8, yy - 0.8))
            if i:
                h.t(xh - 3.6, yy + 0.8, lbl, 2.1, COL[kind], anchor="end", weight=600)
                h.wire([(xh + 2.6, yy), (xv if i == 1 else xg, yy)], kind, 0.6)
                h.dot(xv if i == 1 else xg, yy, kind)
        h.wire([(x, y), (xh - 2.6, y)], "ctl")
        h.t(x + 1.0, y - 0.9, "SERVO%d" % n, 2.2, COL["ctl"], weight=600)
        h.t(xh - 3.6, y - 0.9, "J%d" % (30 + n), 2.3, COL["txt"], anchor="end", weight=700)
        h.t(xg + 6, y + 1.0, "S%d · %s" % (n, desc), 2.7, COL["txt"], weight=700)
        h.t(xg + 6, y + 5.0, "%s → J%d-3 (SIG)" % (gpio(S, "U3", net), 30 + n), 2.3, COL["ctl"])
        ys.append(y)
    h.wire([(xv, ys[0] + 3), (xv, ys[-1] + 14)], "v6", 0.8)
    h.wire([(xg, ys[0] + 6), (xg, ys[-1] + 14)], "gnd", 0.8)
    h.tag(xv, ys[-1] + 17, "SERVO_V", "v6", anchor="end", size=2.3)
    h.tag(xg + 1, ys[-1] + 17, "GND", "gnd", size=2.3)
    h.nota(152, 275, "Cada servo recibe un pulso cada 20 ms (50 Hz): 800 µs = un extremo, 1500 µs = centro,\n"
                     "2200 µs = otro extremo. El PWM de 3.3 V de la ESP32 lo aceptan directo.", 2.4, COL["txt"])
    for n, (x, y) in ep.items():
        net = S["U3"]["pins"].get(str(n))
        if net and n > 15 and not net.startswith("SERVO"):
            h.t(x + 0.8, y - 0.8, net, 2.2, COL[tipo[n]], weight=600)
    return h


def main():
    os.makedirs(OUT, exist_ok=True)
    svgs = []
    for i, f in enumerate((hoja_alimentacion, hoja_senales, hoja_traccion, hoja_servos), 1):
        h = f()
        p = os.path.join(OUT, "hoja%d.svg" % i)
        open(p, "w", encoding="utf-8").write(h.svg())
        svgs.append(p)
        subprocess.run(["rsvg-convert", "-d", "150", "-p", "150", "-b", "white", "-o", p[:-4] + ".png", p], check=True)
    pdf = os.path.join(OUT, "esquema_rover.pdf")
    subprocess.run(["rsvg-convert", "-f", "pdf", "-o", pdf] + svgs, check=True)
    print("OK ->", pdf)


if __name__ == "__main__":
    main()
