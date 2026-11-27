# Tarjeta de tracción (una cara): fabricación y montaje

- **Tarjeta:** 97 × 96 mm, cobre solo abajo (B.Cu), rev. 2.1.
- **Lleva:** ESP32-A, 3 bornas para los L298N, 2 bornas de encoders con sus 6 divisores, 5 V de entrada y la borna `PI` (UART2).
- **Arquitectura y cableado:** en `../DOS_TARJETAS.md`. **Piezas y medidas de pads y barrenos:** en `../LISTA_MATERIALES.md`.

## Reglas de diseño

Pensadas para aislar con **una fresa plana de 1.0 mm en una pasada**, con cualquier programa (LPKF CircuitPro, FlatCAM, o el G-code de este repositorio).

- **Aislamiento de 1.3 mm** entre pistas, plano y piezas: 0.3 mm más que la fresa. Con huecos de exactamente 1.0 mm el programa no mete la fresa y la pista queda unida al plano.
- **Pistas:** las mismas que antes: 1.0 mm o más; +5V y GND de 1.5 mm.
- **Única excepción:** los pads vecinos de una fila a 2.54 mm (headers de la ESP32, piezas de pie) quedan a 1.14 mm. No pueden separarse más sin adelgazar el pad.
- **Sin tiras sueltas:** donde entre dos cobres quedaban más de 2 mm, las dos pasadas de la fresa no se juntaban y dejaban una tira de cobre suelta en medio. Esos huecos llevan ahora un relleno de cobre unido a una de las redes vecinas, así el hueco es de 1.3 mm y se limpia completo (`tools/anti_tiras.py`). En KiCad se ve como cobre extra junto a algunas pistas; las pistas no cambiaron de ancho.
- **Orilla:** ningún cobre a menos de 2 mm del borde.
- **Barrenos:** solo 4 medidas: **1.0, 1.3, 1.5 y 3.2 mm**. No hay de 0.8, 0.9 ni 1.1.
- **GND sin rayos:** los pads de GND van unidos al plano en sólido.

## Bornas (vistas por el lado de componentes)

| Borna | Orilla | Orden físico | Va a |
|---|---|---|---|
| J43 · J42 · J41 | izquierda | de arriba a abajo: EN, IN4, IN3, IN2, IN1, GND | L298N #3 (M5/M6) · #2 (M3/M4) · #1 (M1/M2). EN a ENA y ENB con cable en Y |
| J5 | arriba | de izquierda a derecha: **GND, +5V** (el +5V es el tornillo junto a C2) | Step-down 5 V |
| J9 `PI` | derecha | de arriba a abajo: **TXD2, RXD2, GND** | HAT de la Pi: pin 7 (GPIO4), pin 29 (GPIO5), pin 6 |
| J8 | abajo, izquierda | de izquierda a derecha: GND, +5V, A6, A5, A4 | Encoders de M6, M5 y M4 |
| J7 | abajo, derecha | de izquierda a derecha: A1, A2, A3, +5V, GND | Encoders de M1, M2 y M3 |

Antes de conectar, comprueba con el multímetro que el tornillo GND de cada borna da continuidad con el plano grande de cobre.

## Fabricación

**Archivos:** `gerbers/rover_traccion-B_Cu.gbl` (cobre), `-Edge_Cuts.gm1` (contorno) y `rover_traccion.drl` (barrenos).

### En una LPKF ProtoMat (CircuitPro)

1. Importa el cobre como capa **inferior** (Bottom), el contorno y el taladro. CircuitPro espeja la capa inferior; ya fresada, vista por el cobre debe verse como `cobre_espejo_1a1.pdf`.
2. Aislamiento con la **fresa plana de 1.0 mm**, una pasada. En la vista previa no debe marcar zonas sin aislar.
3. Brocas: 1.0, 1.3 y 1.5 mm. Los 4 barrenos de 3.2 mm los hace la fresa de contorno.
4. Tiempo aproximado: 15 a 30 min de máquina.

`sim/aislamiento_lpkf.png` es la simulación de ese aislamiento (vista por el lado de componentes): 0 cortos y 0 redes abiertas con un corte real de 0.8 a 1.1 mm. En verde, el cobre que queda sin conexión: el marco de 2 mm de la orilla, los pads de los pines de la ESP32 que no se usan y una isla ancha entre los divisores.

### En la Cubiko (G-code)

`gcode/fresa1mm_todo.nc` hace todo con la fresa de 1.0 mm, ~71 min. FR1 de una cara con el cobre arriba; la tarjeta queda en X 3–100 y Y 2–98. Homing, cero XY en la esquina del blank, cero Z con la sonda y mapa de alturas.

## Montaje

**1. Los 8 cables por arriba** (`mapa_cables_1a1.pdf`, `cables.csv`). Cable aislado de 22 AWG por el lado de los componentes; cada punta entra por su barreno y se suelda por abajo. Ponlos **antes** que los headers de la ESP32: W2 pasa junto al extremo USB del módulo.

| Cable | Red | Largo con holgura | Dónde |
|---|---|---|---|
| W1 | GND | 21 mm | junto a J5 (entrada 5 V) |
| W2 | GND | 46 mm | arriba de la ESP32 (lado USB), hacia la borna J43 |
| W3 | GND | 27 mm | a la derecha de la ESP32, entre R21 y los divisores |
| W4 | GND | 26 mm | orilla izquierda, junto a J41 |
| W5 | GND | 16 mm | arriba de los divisores M6 y M5 |
| W6 | GND | 16 mm | arriba de los divisores M5 y M4 |
| W7 | GND | 38 mm | entre los divisores M1–M3 |
| W8 | +5V | 53 mm | +5V de J7 a J8, por la orilla inferior |

MOTOR_EN ya no lleva cable: va por cobre.

**2. Las piezas bajas.** Resistencias, capacitores de 1 nF y D5 (1N5819, banda del lado de la ESP32). Las de M4–M6 van **de pie**. LED D3: el pad cuadrado es el cátodo (pata corta) y va a GND.

**3. El resto.** Headers hembra 1x15 de la ESP32 (25.4 mm entre filas), C2 (la pata + al pad cuadrado) y las bornas.

**4. Pruebas antes de energizar** (sin módulos, con multímetro):
- 5V–GND en J5: no debe pitar.
- Entre el pin 1 (EN) y el pin 6 (GND) de J41, J42 y J43: unos 10 kΩ (es R21, el pull-down de MOTOR_EN).
- Con los L298N alimentados y sin la ESP32: el pin 1 de cada borna contra GND debe dar ~0 V, nunca 5 V. Quita los jumpers de ENA y ENB.
