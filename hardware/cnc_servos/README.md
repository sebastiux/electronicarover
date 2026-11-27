# Tarjeta de servos (una cara): fabricación y montaje

- **Tarjeta:** 76 × 108 mm, cobre solo abajo (B.Cu), rev. 2.1.
- **Lleva:** ESP32-B, 8 headers de servo, entrada de 6 V, medición de batería, 5 V de entrada y la borna `PI` (UART4).
- **Arquitectura y cableado:** en `../DOS_TARJETAS.md`. **Piezas y medidas de pads y barrenos:** en `../LISTA_MATERIALES.md`.

## Reglas de diseño

Las mismas que la tarjeta de tracción (`../cnc_traccion/README.md`): aislamiento de **1.3 mm** para fresa de 1.0 mm, pistas sin cambio de ancho, relleno en los huecos que dejarían tiras sueltas, 2 mm libres en la orilla y barrenos de **1.0, 1.3, 1.5 y 3.2 mm**.

- **Excepción a 1.14 mm:** los pads vecinos de cada header y los rieles V+ y GND que pasan por ellos (van a 2.54 mm).
- **La tarjeta creció 12 mm a lo largo:** con 1.3 mm de aislamiento, el abanico de 8 señales que baja de la ESP32 a los headers necesita 23 mm para abrir.

## Bornas y headers (vistos por el lado de componentes)

| Borna | Orilla | Orden físico | Va a |
|---|---|---|---|
| J5 | izquierda, arriba | de arriba a abajo: +5V, GND | Step-down 5 V |
| J2 | derecha, arriba | de arriba a abajo: **+batería, GND** | Derivación de batería después del fusible (solo medición) |
| J6 | derecha, abajo | de arriba a abajo: +6V, GND | BEC 6 V, ≥ 10 A |
| J9 `PI` | abajo, izquierda | de izquierda a derecha: GND, TXD4, RXD4 | HAT de la Pi: pin 34, pin 32 (GPIO12), pin 33 (GPIO13) |
| J38 … J31 | abajo, de izquierda a derecha | en cada header, de arriba a abajo: SIG, V+, GND | S8 codo/muñeca · S7 pinza · S6 hombro · S5 base · S4 TD · S3 TI · S2 DD · S1 DI |

## Fabricación

**Archivos:** `gerbers/rover_servos-B_Cu.gbl`, `-Edge_Cuts.gm1` y `rover_servos.drl`. En la LPKF, igual que la de tracción: cobre como capa inferior, fresa plana de 1.0 mm en una pasada, brocas de 1.0, 1.3 y 1.5 mm. Unos 10 a 20 min de máquina.

`sim/aislamiento_lpkf.png`: 0 cortos y 0 redes abiertas con un corte real de 0.8 a 1.1 mm.

**En la Cubiko:** `gcode/fresa1mm_todo.nc` (~48 min), pero la tarjeta mide 108 mm y el blank de 100 mm ya no alcanza en ese sentido: hace falta una placa de 15 cm puesta a lo largo en Y, o usar la LPKF.

## Montaje

1. **Cable W1** (6 V, 17 mm con holgura): entre C3 y C4, por arriba. Ver `mapa_cables_1a1.pdf`.
2. **R15 y R16 (1k) van de pie**, debajo de la ESP32, del lado de J9.
3. **Piezas bajas:** R22–R26, C5, D6 (banda hacia la ESP32), LEDs D2 y D4 (pad cuadrado = cátodo, a GND).
4. **Headers hembra 1x15 de la ESP32** y **headers macho 1x3** de los servos.
5. **C3 y C4** (1000 µF 16 V, Ø10 mm, paso 5 mm): la pata + al pad cuadrado.
6. **Bornas.**
7. **Refuerza el riel de 6 V:** toda la corriente de los 8 servos pasa por el riel de 1.4 mm de los headers. Suelda un alambre de cobre desnudo (18 AWG) por el lado del cobre, a lo largo de los 8 pads centrales (V+) y hasta J6. Sin refuerzo, no pases de 3 A (1 o 2 servos moviéndose).
8. **Prueba:** sin módulos, continuidad 6V–GND y 5V–GND: no deben pitar.
