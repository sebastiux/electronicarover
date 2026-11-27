# Tarjeta de servos (una cara): fabricación y montaje

- **Tarjeta:** 73.5 × 100 mm, cobre solo abajo (B.Cu), rev. 2.2. **Sin cables por arriba.**
- **Lleva:** ESP32-B, 8 headers de servo, entrada de 6 V, medición de batería, 5 V de entrada y la borna `PI` (UART4).
- **Arquitectura y cableado:** en `../DOS_TARJETAS.md`. **Piezas y medidas de pads y barrenos:** en `../LISTA_MATERIALES.md`.

## Reglas de diseño

Las mismas que la tarjeta de tracción (`../cnc_traccion/README.md`): aislamiento de **2.0 mm** para fresar con la fresa de 1.0 mm en **2 pasadas por lado**, pistas sin cambio de ancho, relleno en los huecos que dejarían tiras sueltas, 2 mm libres en la orilla y barrenos de **1.0, 1.3, 1.5 y 3.2 mm**.

- **Lo que no puede llegar a 2.0 mm** (paso de 2.54 mm): pads vecinos de los headers y de los LED y los rieles V+ y GND que pasan por los headers de servo (**1.14 mm**); la pista que entra a un pin contra el pad vecino (**1.34 mm**); las pistas de pines vecinos de la ESP32 en sus primeros 2 a 10 mm (**1.54 mm**).
- **Señales de servo en escalera:** cada pista se separa a 3.0 mm de su vecina en cuanto sale del pin y gira hacia su header en un nivel propio.
- **GND y +6 V en barras:** el GND cruza por debajo del módulo, baja por las dos orillas y cierra por el riel de los headers. El +6 V va de J6 a los dos capacitores por una barra de 2.4 mm. Ya no hay cable entre C3 y C4.

## Bornas y headers (vistos por el lado de componentes)

| Borna | Orilla | Orden físico | Va a |
|---|---|---|---|
| J5 | izquierda, arriba | de arriba a abajo: +5V, GND | Step-down 5 V |
| J2 | derecha, arriba | de arriba a abajo: **+batería, GND** | Derivación de batería después del fusible (solo medición) |
| J6 | derecha, abajo | de arriba a abajo: **+6V, GND** | BEC 6 V, ≥ 10 A |
| J9 `PI` | abajo, izquierda | de izquierda a derecha: GND, TXD4, RXD4 | HAT de la Pi: pin 34, pin 32 (GPIO12), pin 33 (GPIO13) |
| J38 … J31 | abajo, de izquierda a derecha | en cada header, de arriba a abajo: SIG, V+, GND | S8 codo/muñeca · S7 pinza · S6 hombro · S5 base · S4 TD · S3 TI · S2 DD · S1 DI |

J6 queda 8 mm adentro de la orilla derecha y J9, 7 mm arriba de la orilla inferior: sus cables entran por esos lados.

## Fabricación

**Archivos:** `gerbers/rover_servos-B_Cu.gbl`, `-Edge_Cuts.gm1` y `rover_servos.drl`.

**En la LPKF**, igual que la de tracción: cobre como capa inferior, fresa plana de 1.0 mm con **2 canales de aislamiento por lado**, brocas de 1.0, 1.3 y 1.5 mm. Unos 15 a 30 min de máquina.

`sim/aislamiento_lpkf.png`: simulación con 2 pasadas, 0 cortos y 0 redes abiertas con un corte real de 0.8 a 1.1 mm.

**En la Cubiko:** `gcode/fresa1mm_todo.nc` (~56 min, aislamiento en 2 pasadas). La tarjeta queda en X 3–76.5 y Y 2–102: hace falta una placa de 10 × 15 cm con el lado largo en Y.

## Montaje

1. **Piezas bajas.** Todas las resistencias van **acostadas**: R15 y R16 (1k) a la izquierda, entre la ESP32 y J9; R22–R24 arriba; R26 abajo a la derecha. C5 (100 nF). D6 (1N5819): banda hacia la ESP32.
2. **LEDs.** D2 (rojo, batería): cátodo (pad cuadrado, pata corta) **abajo**. D4 (azul, servos): cátodo **arriba**. Los dos cátodos van a GND.
3. **Headers hembra 1x15 de la ESP32** y **headers macho 1x3** de los servos.
4. **C3 y C4** (1000 µF 16 V, Ø10 mm, paso 5 mm), a la derecha: la pata + al pad cuadrado (izquierda), el – a la barra de GND de la orilla.
5. **Bornas.**
6. **Refuerza el riel de 6 V:** toda la corriente de los 8 servos pasa por el riel de 1.4 mm de los headers. Suelda un alambre de cobre desnudo (18 AWG) por el lado del cobre, a lo largo de los 8 pads centrales (V+) y hasta J6. Haz lo mismo con el riel de GND (los pads de la orilla). Sin refuerzo, no pases de 3 A (1 o 2 servos moviéndose).
7. **Prueba:** sin módulos, continuidad 6V–GND y 5V–GND: no deben pitar. El GND de J5, J2, J6 y J9 debe dar continuidad entre sí.
