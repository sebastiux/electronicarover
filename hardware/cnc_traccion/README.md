# Tarjeta de tracción (una cara): fresado y montaje

- **Tarjeta:** 92 × 96 mm, cobre solo abajo.
- **Lleva:** ESP32-A, 3 bornas para los L298N, 2 bornas de encoders con sus 6 divisores, 5 V de entrada y la borna `PI` (UART2).
- **Arquitectura y cableado:** en `../DOS_TARJETAS.md`.

## Reglas de diseño (verificadas con `tools/verifica_espacios.py`)

- **Pistas:** toda conexión de al menos **1.0 mm**; +5V y GND de 1.5 mm.
- **Pads:** de **2.2 mm** donde el paso lo permite; en headers de 2.54 mm, 1.84 mm. Las bornas de encoders llevan 2.0 mm para que entre pin y pin pase el plano de GND.
- **Espacio entre piezas:** al menos **1.0 mm de cobre libre** entre pads de piezas distintas, y 0.6 mm entre un barreno de cable y cualquier pad. Nada queda encimado.
- **GND sin rayos:** los pads de GND van unidos al plano en sólido. En la simulación se ven como un barreno dentro del cobre, sin anillo: el plano mismo es el pad, no está incompleto.

## Bornas

| Borna | Orilla | Pines | Va a |
|---|---|---|---|
| J43 · J42 · J41 | izquierda, de arriba a abajo | EN, IN4, IN3, IN2, IN1, GND | L298N #3 (M5/M6) · #2 (M3/M4) · #1 (M1/M2). EN a ENA y ENB con cable en Y |
| J8 | inferior izquierda | GND, +5V, A6, A5, A4 | Encoders de M6, M5 y M4 (cable Pololu: verde GND, azul VCC, amarillo A) |
| J7 | inferior derecha | GND, +5V, A1, A2, A3 | Encoders de M1, M2 y M3 |
| J5 | superior centro | +5V, GND | Step-down 5 V |
| J9 `PI` | derecha | **GND, RXD2, TXD2** | HAT de bornas de la Pi: pines **6, 29 y 7** |

## Divisores de los encoders

- **M1–M3:** a la derecha de la ESP32, con resistencias acostadas, a 5 mm entre filas y 13 mm entre bloques.
- **M4–M6:** en fila **debajo del módulo**, junto a J8, con las resistencias **de pie**. Así el plano de GND de cada bloque sale entre los pines de J8.

## Fresado en la Cubiko (sin voltear)

**Material:** FR1 de **una cara**, 1.6 mm. Pégalo con cinta doble cara al mártir, con el **cobre arriba**. La tarjeta queda en X 3–95 y Y 2–98 desde la esquina frontal izquierda del blank.

| # | Archivo | Herramienta | Tiempo |
|---|---|---|---|
| 1 | `gcode/1_vbit_aislamiento.nc` | V-bit 20° × 0.1 a −0.10 mm, 120 mm/min | 39 min |
| 2 | `gcode/2_broca1.0.nc` | broca 1.0 mm (111 agujeros) | 10 min |
| 3 | `gcode/3_fresa1mm_barrenos_contorno.nc` | fresa de 1.0 mm: barrenos de 1.2 mm o más, contorno con 4 puentes | 24 min |

1. Haz el homing y pon el **cero XY** en la esquina del blank.
2. Cero Z con la sonda y **mapa de alturas** sobre la tarjeta.
3. Corre los archivos 1, 2 y 3. Antes de cada uno: cambia la herramienta y haz el cero Z.
4. Corta los puentes y lija el borde.

- **Velocidades, profundidades y GRBL:** son los valores del Fab Lab, en `../cubiko/README.md`, "Parámetros de fresado".
- **Geometría:** el G-code va espejado (ves la cara de cobre desde arriba). `cobre_espejo_1a1.pdf` muestra cómo queda.

## Montaje

**1. Los 8 cables por arriba** (`mapa_cables_1a1.pdf`, `cables.csv`). Cable aislado de 22 AWG por el lado de los componentes. Cada punta entra por su barreno y se suelda **por abajo**.

| Cable | Red | Largo con holgura | Dónde |
|---|---|---|---|
| W1 | GND | 14 mm | sobre la ESP32, junto al USB |
| W2 | GND | 20 mm | bajo J43 |
| W3 | VIN_A | 22 mm | de D5 al pin VIN de la ESP32 |
| W4 | +5V | 24 mm | +5V hacia la orilla derecha (de ahí baja a J7) |
| W5 | GND | 25 mm | bajo J41 |
| W6 | GND | 16 mm | entre los divisores M4 y M5 |
| W7 | +5V | 41 mm | +5V a J8 (encoders) |
| W8 | +5V | 26 mm | +5V a J7 (encoders) |

Pon los cables **antes** que los headers de la ESP32: W1 y W3 pasan junto al módulo.

**2. Las piezas bajas.**
- Resistencias, capacitores de 1 nF y D5 (1N5819, banda del lado de la ESP32).
- Las de M4–M6 van **de pie**: el cuerpo sobre el pad cuadrado y la otra pata doblada hacia abajo.
- LED D3: el pad cuadrado es el cátodo (pata corta) y va a GND.

**3. El resto.** Headers hembra 1x15 de la ESP32 (fila exterior, 25.4 mm), C2 y las bornas.

**4. Prueba.** Sin módulos, mide continuidad 5V–GND: no debe pitar. Luego enciende con la fuente limitada en corriente.

## Simulación

- **`sim/reporte.txt`:** 0 cortos y 0 redes abiertas, contando los 8 cables.
- **`sim/resultado_cobre.png` y `sim/trayectorias.png`:** cómo queda el cobre y por dónde pasan las herramientas.

## Simulación en el Fab Lab (fablab.sebs.mx/cnc)

Los 3 archivos se corrieron en el gemelo de la Cubiko (modo *Simulation*): homing, material 142 × 100 × 1.6, cero XY en la esquina, Z0 con la sonda y mapa de alturas 11 × 8. Resultado: **Board done, 3 de 3**, sin errores de GRBL ni salidas del recorrido.

| Trabajos (estimación de la app) | `1_vbit` 39 min ✓ · `2_broca` 8 min ✓ · `3_fresa` 24 min ✓ |
|---|---|

Capturas en `sim/fablab/`, registro en `sim/fablab/registro.txt`.

![](sim/fablab/3_contorno_terminado.png)
