# Tarjeta de tracción (una cara): fabricación y montaje

- **Tarjeta:** 96.2 × 110.5 mm, cobre solo abajo (B.Cu), rev. 2.2. Cabe en una placa de 10 × 15 cm.
- **Lleva:** ESP32-A, 3 bornas para los L298N, 2 bornas de encoders con sus 6 divisores, 5 V de entrada y la borna `PI` (UART2).
- **Arquitectura y cableado:** en `../DOS_TARJETAS.md`. **Piezas y medidas de pads y barrenos:** en `../LISTA_MATERIALES.md`.

## Reglas de diseño

- **Aislamiento de 2.0 mm** entre pistas, plano y piezas: el doble de la fresa de 1.0 mm.
- **Pistas:** sin cambio de ancho: 1.0 mm las de señal; +5V y GND de 1.5 mm en los tramos principales.
- **Se fresa con 2 pasadas por lado.** Con una sola pasada, las dos orillas de un hueco de 2.0 mm quedan borde con borde y puede quedar un hilo de cobre en medio. La segunda pasada va por el centro del hueco y lo deja limpio.
- **Lo que no puede llegar a 2.0 mm** (lo fija el paso de las piezas, no el diseño):
  - pads vecinos de una fila a 2.54 mm (headers de la ESP32, LED): **1.14 mm**;
  - la pista que entra a un pin, contra el pad del pin vecino: **1.34 mm** en los headers y **1.8 mm** en las bornas de 3.5 mm;
  - pistas que salen de pines vecinos de la ESP32: **1.54 mm** en el tramo en que van juntas (de 4 a 13 mm); en cuanto pueden se abren a 2.0 mm.
- **Todo el GND va en pistas**, además del plano: un anillo por la orilla de arriba, la derecha y abajo une J5, J9, los encoders y los L298N.
- **Sin tiras sueltas:** los huecos de más de 2 mm donde no entra el plano de GND llevan un relleno de cobre unido a una red vecina (`tools/anti_tiras.py`). En KiCad se ve como cobre extra junto a algunas pistas.
- **Orilla:** ningún cobre a menos de 2 mm del borde.
- **Barrenos:** solo 4 medidas: **1.0, 1.3, 1.5 y 3.2 mm**.

## Bornas (vistas por el lado de componentes)

| Borna | Orilla | Orden físico | Va a |
|---|---|---|---|
| J43 · J42 · J41 | izquierda | de arriba a abajo: EN, IN4, IN3, IN2, IN1, GND | L298N #3 (M5/M6) · #2 (M3/M4) · #1 (M1/M2). EN a ENA y ENB con cable en Y |
| J5 | arriba | de izquierda a derecha: **GND, +5V** (el +5V es el tornillo junto a C2) | Step-down 5 V |
| J9 `PI` | derecha | de arriba a abajo: **TXD2, RXD2, GND** | HAT de la Pi: pin 7 (GPIO4), pin 29 (GPIO5), pin 6 |
| J8 | abajo, izquierda | de izquierda a derecha: GND, +5V, A6, A5, A4 | Encoders de M6, M5 y M4 |
| J7 | abajo, derecha | de izquierda a derecha: A1, A2, A3, +5V, GND | Encoders de M1, M2 y M3 |

- J9 queda 9 mm adentro de la orilla derecha: sus cables entran por ese lado.
- Antes de conectar, comprueba con el multímetro que el tornillo GND de cada borna da continuidad con el GND de J5.

## Fabricación

**Archivos:** `gerbers/rover_traccion-B_Cu.gbl` (cobre), `-Edge_Cuts.gm1` (contorno) y `rover_traccion.drl` (barrenos).

### En una LPKF ProtoMat (CircuitPro)

1. Importa el cobre como capa **inferior** (Bottom), el contorno y el taladro. CircuitPro espeja la capa inferior; ya fresada, vista por el cobre debe verse como `cobre_espejo_1a1.pdf`.
2. Aislamiento con la **fresa plana de 1.0 mm** y **2 canales por lado** (el primero pegado al cobre y otro traslapado al 50 %, para un canal de 1.5 mm). En el diálogo de tecnología es la opción de aislamiento doble o de canales adicionales; el nombre cambia según la versión.
3. En la vista previa, los huecos entre pistas deben verse limpios, sin una línea de cobre en medio.
4. Brocas: 1.0, 1.3 y 1.5 mm. Los 4 barrenos de 3.2 mm los hace la fresa de contorno.
5. Tiempo aproximado: 30 a 50 min de máquina (son dos pasadas).

`sim/aislamiento_lpkf.png` es la simulación de ese aislamiento con 2 pasadas (vista por el lado de componentes): 0 cortos y 0 redes abiertas con un corte real de 0.8 a 1.1 mm. En verde, el cobre que queda sin conexión: el marco de 2 mm de la orilla, los pads de los pines de la ESP32 que no se usan y una isla ancha junto a los divisores. Con una sola pasada tampoco hay cortos, pero quedan hilos sueltos.

### En la Cubiko (G-code)

`gcode/fresa1mm_todo.nc` hace todo con la fresa de 1.0 mm (aislamiento en 2 pasadas, barrenos y contorno), ~102 min. La tarjeta queda en X 3–99.2 y Y 2–112.5: hace falta una placa de 10 × 15 cm con el lado largo en Y. Homing, cero XY en la esquina del blank, cero Z con la sonda y mapa de alturas.

## Montaje

**1. Los 4 cables por arriba** (`mapa_cables_1a1.pdf`, `cables.csv`). Cable aislado de 22 AWG por el lado de los componentes; cada punta entra por su barreno y se suelda por abajo. Ponlos **antes** que las bornas y los headers.

| Cable | Red | Largo con holgura | Dónde |
|---|---|---|---|
| W1 | GND | 28 mm | junto a J43, a lo largo de la borna: del tornillo GND hacia arriba |
| W2 | GND | 18 mm | arriba de la ESP32 (lado USB), encima de R21 |
| W3 | GND | 32 mm | junto a J41, a lo largo de la borna: une el GND de J42 con el de J41 |
| W4 | +5V | 57 mm | orilla inferior, justo arriba de J8 y J7: lleva el +5V de J7 a J8 |

Sin W1 y W3, los L298N #3 y #2 se quedan sin GND de referencia. Sin W2 se queda sin GND el pin 29 de la ESP32 y J43.

**2. Las piezas bajas.** Todas las resistencias van **acostadas** (7.62 mm entre patas). Los capacitores de 1 nF van con las patas abiertas a **5 mm**. D5 (1N5819): banda del lado de la ESP32. R21 va arriba de la ESP32. LED D3: el pad cuadrado (abajo) es el cátodo (pata corta) y va a GND.

**3. El resto.** Headers hembra 1x15 de la ESP32 (25.4 mm entre filas), C2 (la pata + al pad cuadrado) y las bornas.

**4. Pruebas antes de energizar** (sin módulos, con multímetro):
- 5V–GND en J5: no debe pitar.
- Entre el pin 1 (EN) y el pin 6 (GND) de J41, J42 y J43: unos 10 kΩ (es R21, el pull-down de MOTOR_EN).
- Con los L298N alimentados y sin la ESP32: el pin 1 de cada borna contra GND debe dar ~0 V, nunca 5 V. Quita los jumpers de ENA y ENB.
