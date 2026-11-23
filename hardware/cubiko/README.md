# Rover Controller Cubiko: tarjeta para fresar en la Genmitsu Cubiko

Variante de la v1.2 adaptada al área de trabajo de la **Genmitsu Cubiko** (≈145–150 × 110 × 40 mm, husillo 775 de 75 W a 10 000 RPM máx., GRBL 1.1h).

- La tarjeta mide **136 × 96 mm**, en 2 caras, sin barrenos metalizados.
- Lleva la **Raspberry Pi 5** (debajo de la tarjeta), las **2 ESP32** y los **8 servos**.
- Los **3 L298N van en el chasis**, con sus bornas originales. Se conectan a la tarjeta con **bornas de tornillo en las orillas**.

![PCB](img/pcb_cubiko.png)

| Verificación | Resultado |
|---|---|
| DRC de KiCad | 0 violaciones, 0 conexiones pendientes |
| Conectividad **sin metalizado**: cada pad conecta solo por su cara de soldadura | 0 conexiones abiertas (38 vías-pin, todas con espacio libre para soldar el alambre por las 2 caras) |
| **Simulación del fresado** (`tools/cubiko_cam.py`): resta del cobre el ancho real del V-bit y los taladros | **0 cortos, 0 redes abiertas** |
| Firmware simulado sobre el netlist, con el cableado externo a los L298N y a los encoders | 87/87 OK (48 tracción + 39 servos) |
| G-code dentro del recorrido de la máquina | X 2–140 mm, Y 1–101 mm, Z −3.4 a 5 mm; comentarios y líneas válidos para GRBL (≤ 79 caracteres, sin paréntesis anidados) |
| Parámetros | **Modo prototipo:** 1 sola pasada de aislamiento con la V-bit del Fab Lab (20° × 0.1 a 0.10 mm), broca de 1.0 y fresa de 1.0 · **~2.8 h** de máquina |

![Simulación](sim/resumen_simulacion.png)

## Qué cambia respecto a la v1.2

| v1.2 (200 × 150) | Cubiko (136 × 96) |
|---|---|
| L298N soldados sobre la tarjeta | **L298N en el chasis**, conservando sus bornas azules; se cablean a 3 bornas de 7 vías |
| Batería por XT60 en la tarjeta | La batería **no entra a la tarjeta**: un arnés reparte batería → fusible → L298N, step-down 5 V y BEC 6 V. J2 solo mide la batería (< 10 mA). |
| Encoders alimentados por el 78M05 de cada L298N | Encoders alimentados por el **+5V de la tarjeta**, con 2 bornas de 5 vías |
| ESP32-B por UART0 de la Pi (GPIO14/15) | ESP32-B por **UART4 de la Pi (GPIO12/13, pines 32/33, `/dev/ttyAMA4`)**: el header queda pegado a la orilla y los pines exteriores no tienen salida |
| Firmware de las ESP32 | **Sin cambios**: misma asignación de pines |

Las ESP32 no usan WiFi; las dos hablan con la Pi por UART. Por eso, bajo la ESP32-A van los divisores de los encoders 4–6, que son resistencias acostadas y capacitores de disco. La ESP32-B conserva su zona libre de cobre bajo la antena.

## Conexiones

| Borna | Orilla | Pines (en orden) | Va a |
|---|---|---|---|
| J43 · L298N #3 (M5/M6) | izquierda, arriba | ENB, IN4, IN3, IN2, IN1, ENA, GND | Header lógico del L298N #3 (**quita los jumpers ENA/ENB**) y su borna GND |
| J42 · L298N #2 (M3/M4) | izquierda, centro | igual | L298N #2 |
| J41 · L298N #1 (M1/M2) | izquierda, abajo | igual | L298N #1 |
| J8 · ENC M6 M5 M4 | inferior izquierda | GND, +5V, A6, A5, A4 | Cables de encoder: verde = GND, azul = VCC, amarillo = A (el blanco/B no se usa) |
| J7 · ENC M1 M2 M3 | inferior centro | GND, +5V, A1, A2, A3 | igual |
| J6 · SERVO 6V | inferior derecha | −, + | Salida del BEC de 6 V |
| J5 · 5V IN | superior | +, − | Salida del step-down de 5 V / 5 A |
| J2 · BAT 12V | derecha | −, + | Batería **después del fusible** (solo medición) |
| J31–J38 · S1…S8 | abajo de la ESP32-B | SIG (arriba), V+, GND (abajo) | Servos |

```
Batería 3S ─► fusible 15 A ─┬─► L298N #1, #2, #3 (+12V y GND, cable ≥ 18 AWG)
                            ├─► step-down 5V/5A ─► J5 (Pi 5, ESP32, encoders)
                            ├─► BEC 6V ≥10A ────► J6 (servos)
                            └─► J2 (medición de batería)
GND común: une las GND de los L298N, el step-down y el BEC en el negativo de la batería (estrella).
```

En el L298N deja puesto el jumper **5V-EN**, que alimenta su lógica, y quita los jumpers ENA/ENB.

**En la Raspberry Pi**, en `/boot/firmware/config.txt`:

```
dtoverlay=uart2-pi5
dtoverlay=uart4-pi5
usb_max_current_enable=1
```

Antes de correr el enlace con las ESP32:

```bash
export ROVER_ESPB_PORT=/dev/ttyAMA4
```

## Material y herramientas

| Qué | Especificación |
|---|---|
| Placa virgen | FR1 (fenólica) **doble cara**, 1.6 mm, cobre 35 µm. Recorta una de 150 × 100 a **142 × 100 mm**. Evita FR4: su polvo de fibra de vidrio es peligroso. |
| Martir | MDF o madera plana de ≥ 6 mm, atornillada a la cama |
| Sujeción | Cinta doble cara delgada en toda la placa: los clamps estorban en un blank de 100 mm |
| T1 V-bit | **20°, punta 0.1 mm**, zanco 3.175 mm (aislamiento de las 2 caras). Es la del Fab Lab. |
| T2 broca | **1.0 mm** de carburo para PCB: todos los agujeros de 0.8 a 1.1 mm |
| T3 fresa tipo maíz | **1.0 mm**: pines de alineación, barrenos de 1.2 mm o más, zona de antena y contorno |
| Pines de alineación | 2 pines de acero de **Ø3 mm** (sirven los zancos de brocas de 3 mm rotas) |
| Sonda | Placa de sonda de la Cubiko, con el caimán en el cobre |
| Software | **Candle** o **bCNC** para el mapa de alturas (autonivelado). Puedes usar **gSender** si tu versión ya tiene mapa de alturas. |

## Parámetros de fresado

Ya están dentro de los archivos `gcode/*.nc`. Si quieres regenerarlos con otros valores, cambia el diccionario `P` en `tools/cubiko_cam.py`.

| Operación | Herramienta | RPM | Avance | Bajada | Profundidad | Notas |
|---|---|---|---|---|---|---|
| Aislamiento B y F | V-bit 20° × 0.1 | 10 000 | **120 mm/min** | 60 mm/min | **−0.10 mm** | **1 pasada** (modo prototipo). Ancho de corte 0.135 mm. Sube a 2 mm entre trayectorias y baja rápido a 0.3 mm antes de entrar. |
| Taladros | broca 1.0 | 10 000 | — | 60 mm/min | −1.9 mm | Atraviesa 1.6 mm y entra 0.3 mm en la cinta / martir |
| Pines de alineación | fresa 1.0 | 10 000 | 72 mm/min (helicoidal) | 60 mm/min | −3.4 mm | 1.6 de placa + 1.8 en el MDF: el recorrido Z de la Cubiko termina en la cara del MDF de 2 mm. Ø3.0 mm. |
| Barrenos de 1.2 mm o más (bornas, M3, M2.5) | fresa 1.0 | 10 000 | 72 mm/min | 60 mm/min | −1.9 mm | Helicoidal, pasos de 0.3 mm |
| Despeje bajo la antena de la ESP32-B | fresa 1.0 | 10 000 | 120 mm/min | 60 mm/min | −0.12 mm | Solo el cobre que no es de ninguna red |
| Contorno | fresa 1.0 | 10 000 | 120 mm/min | 60 mm/min | −1.85 mm | 4 pasadas por fuera de la línea. 4 puentes de 3.1 mm con tope en Z −0.9 (quedan 0.7 mm). |

**Revisa en GRBL** (envía `$$`) antes del primer trabajo:
- **`$30`** debe ser la RPM máxima del husillo (10 000). Si es 1000, cambia `rpm` en `cubiko_cam.py` o pon `$30=10000`.
- **`$32=0`**: modo láser apagado.
- **`$110`, `$111` y `$112`** deben ser ≥ 1500 mm/min: los viajes en vacío usan G0.

**Por qué estos valores:** son los que trae por defecto la app CNC del Fab Lab (<https://fablab.sebs.mx/cnc/>), calibrados en esta misma máquina.
- **Ancho del corte.** El V-bit corta más ancho entre más baja: 0.1 + 2·d·tan 10° → a 0.10 mm da 0.135 mm. La separación mínima del diseño es 0.5 mm.
- **Pasadas.** En **modo prototipo** se da **1 sola pasada**: el tiempo baja de ~6.4 h a ~2.8 h. Cada red queda rodeada por un corte cerrado de 0.135 mm, y la simulación confirma 0 cortos. El costo, como advierte el Fab Lab, es que entre dos pistas puede quedar un **hilo de cobre suelto** (aislado, no conecta nada). Antes de soldar, revisa la placa con lupa y raspa con cúter cualquier hilo que se haya levantado. Si prefieres la limpieza del Fab Lab, pon `iso_passes=3` en `tools/cubiko_cam.py` y regenera.
- **Profundidad.** El cobre mide 35 µm. 0.10 mm lo atraviesa siempre que se use el **mapa de alturas**: la cama de la Cubiko no es plana.
- **Brocas.** Una sola broca de 1.0 mm para todo lo que mide entre 0.6 y 1.15 mm, como en el flujo del Fab Lab. Lo más grande lo abre la fresa de 1.0 mm en círculo.

### Si prefieres FlatCAM

Usa los Gerbers de `gerbers/`. Los equivalentes son:

| Operación | Valores |
|---|---|
| Isolation | V-shape, punta 0.1 mm, ángulo 20°, Cut Z −0.10 mm, Passes 3, Overlap 50 %, Feedrate X-Y 120 mm/min, Feedrate Z 60 mm/min, Travel Z 2.0 mm, Spindle 10 000 |
| Lado 1 | Abre `B_Cu`, el `.drl` y `Edge_Cuts`. Espéjalos con el **Double-Sided Tool**: Mirror Axis **Y**, referencia **Box** = `Edge_Cuts` (eje vertical al centro de la tarjeta, igual que los pines de alineación). El lado 2 (`F_Cu`) no se espeja. |
| Drilling | Cut Z −1.9 mm, Feedrate Z 60 mm/min, Travel Z 1.0 mm |
| Cutout | Tool 1.0 mm, Cut Z −1.85 mm, Multi-depth 0.46 mm, Gaps 4, Gap size 3.1 mm |

## Paso a paso

Hay 5 archivos, en este orden. El tiempo estimado es **~2.8 h** de máquina, más cambios de herramienta y mapas de alturas.

| # | Archivo | Herramienta | Tiempo |
|---|---|---|---|
| 1 | `L1_1_fresa1mm_alineacion_barrenos_antena_B.nc` | fresa 1.0 | 20 min |
| 2 | `L1_2_vbit_aislamiento_B.nc` | V-bit 20° | 59 min |
| 3 | `L1_3_broca1.0.nc` | broca 1.0 (266 agujeros) | 24 min |
| — | **voltear la placa** | | |
| 4 | `L2_1_vbit_aislamiento_F.nc` | V-bit 20° | 48 min |
| 5 | `L2_2_fresa1mm_antena_contorno_F.nc` | fresa 1.0 | 19 min |

### Lado 1: cara inferior hacia arriba

1. Pega el blank de 142 × 100 sobre el martir con cinta doble cara en toda la superficie. El lado largo va en X. Déjalo cerca del origen de la máquina, para que X llegue a 141 mm.
2. **Cero XY** en la esquina frontal izquierda del blank. **Anota las coordenadas de máquina (MPos)** de ese cero: no lo vuelvas a mover en todo el proceso, ni al voltear.
3. Monta la fresa de 1.0 y haz el **cero Z con la sonda** sobre el cobre. Corre el **archivo 1**: pines de alineación, barrenos grandes y despeje de antena.
4. Cambia al V-bit y haz el cero Z con la sonda. Haz el **mapa de alturas** sobre 136 × 96 mm: malla de 10 × 8 puntos (~14 mm), con el origen en X3 Y2. Corre el **archivo 2** aplicando el mapa.
5. Monta la broca de 1.0, haz el cero Z y corre el **archivo 3**. El taladrado no necesita mapa de alturas.
6. Aspira el polvo.

### Voltear: cómo se alinean las 2 caras

La cara inferior (lado 1) se fresa **espejada** y en ella se taladra **todo**. La cara superior (lado 2) va sin espejo. La placa se voltea **de izquierda a derecha**, sobre el eje vertical que pasa por el centro de la tarjeta (X = 3 + 68 = 71 mm desde el cero).

Dos barrenos son simétricos respecto a ese eje: **H1**, en (3.5, 8.5) mm de la tarjeta, y el barreno superior derecho de la Pi, en (132.5, 8.5). Al voltear, cada uno cae donde estaba el otro. Los dos se hacen en el archivo 1.

7. Despega la placa **sin mover la cama ni el cero XY**.
8. Voltéala de izquierda a derecha y pégala con cinta nueva. Para que quede en su lugar, usa una de estas opciones:
   - **A. Pines (mecánica):** el archivo 1 también barrenó el MDF en esas dos posiciones. Mete 2 pines de Ø3 en el MDF, ensarta la placa volteada, pégala y **saca los pines** antes de cortar.
   - **B. Asistente de la app del Fab Lab** (*Origin → Align with 2 holes*):
     1. Carga en la app los Gerbers de la tarjeta (`gerbers/…F_Cu.gtl`, `…Edge_Cuts.gm1`, `….drl`) junto con los archivos `L2_*.nc`. Pon el material en 142 × 100 y la posición del diseño en **X 3, Y 2**.
     2. Elige como hoyos A y B: **Ø3.00 en (6.50, 89.50)** (H1) y **Ø3.00 en (135.50, 89.50)** (Pi).
     3. Con *Go to where it should be* y el jog, **centra la fresa sobre cada barreno**.
     4. La app calcula el **giro y el desplazamiento reales** y los aplica a todos los trabajos del lado 2.
     5. Si la distancia medida entre barrenos difiere más de 0.3 mm del diseño, la app avisa: revisa que sean los barrenos correctos.

     Con esta opción no necesitas pines. Si usas pines, la alineación sirve de doble revisión: debe dar ~0° y ~0 mm.

### Lado 2: cara superior hacia arriba

9. Haz el cero Z con la sonda y un **mapa de alturas nuevo**, porque la placa cambió de posición. **No toques el cero XY.**
10. Corre el **archivo 4** (V-bit, cara superior) con el mapa aplicado.
11. Cambia a la fresa de 1.0, haz el cero Z y corre el **archivo 5**: despeje de antena y contorno con 4 puentes.
12. Corta las pestañas con cúter o segueta y lija el borde.

**Antes de la placa real**, haz una prueba en un retazo: un cuadro de 20 × 20 mm con el aislamiento.
- **El canal debe medir ~0.14 mm de ancho** y verse sin cobre al fondo.
- **Si quedan puentes de cobre:** baja 0.02 mm la profundidad (`iso_depth`).
- **Si el canal sale de más de 0.25 mm:** súbela.

## Simulación en el simulador del Fab Lab

Los 5 archivos se corrieron en el gemelo de la Cubiko de <https://fablab.sebs.mx/cnc/> (modo *Simulation*). Se siguió el mismo procedimiento de este README:

| Paso | Lado 1 (cara inferior) | Lado 2 (cara superior) |
|---|---|---|
| Homing, material 142 × 100 × 1.6, cero XY en la esquina | ✓ | ✓, el **mismo** cero |
| Alineación con H1 y el barreno de la Pi | — | ✓: 0.000°, 0 mm (en simulación la placa no se mueve) |
| Z0 con la sonda | cobre en Z máquina −36.43 | ídem |
| Mapa de alturas de 11 × 8 | **0.36 mm de diferencia** (−0.17 a +0.19): sin mapa, el corte de 0.10 mm no sale parejo | ídem |
| Trabajos (modo prototipo, 1 pasada) | `L1_1` "20 min, atraviesa y entra 1.80 mm en el MDF" ✓ · `L1_2` "59 min, 0.10 mm bajo el cobre" ✓ · `L1_3` "18 min" ✓ | `L2_1` "48 min" ✓ · `L2_2` "18 min, entra 0.25 mm en el MDF" ✓ |
| Resultado | **Board done**, 3 de 3 | **Board done**, 2 de 2 |

**Qué encontró el simulador y ya está corregido:**
- **Comentarios con paréntesis anidados.** GRBL los rechaza ("Unrecognized G-code letter") y el trabajo no arranca.
- **Líneas de más de 80 caracteres.** Exceden el buffer de GRBL.
- **Pines de alineación a −4.6 mm.** Se salían del recorrido Z, que acaba en la cara del MDF. Ahora van a −3.4 mm.

Capturas en `sim/fablab/`, registros en `sim/fablab/registro_lado*.txt`. El script que maneja la app es `tools/fablab_sim/sim_fablab.js` (Playwright).

| Lado 1 terminado (vista desde arriba, espejado) | Lado 2 terminado, con contorno y puentes |
|---|---|
| ![](sim/fablab/3_lado1_taladros_terminado.png) | ![](sim/fablab/5_lado2_contorno_terminado.png) |

## Montaje

1. **Vías-pin (38): así se vuelve de 2 caras.** Las caras se unen con un alambre soldado en cada vía.
   - **El hueco:** cada vía es un barreno de 1.0 mm con anillo de cobre de 0.6 mm en las dos caras.
   - **El alambre:** usa alambre de cobre estañado de 0.5–0.6 mm. Sirven los recortes de las patas de resistencias, o un pin de header de 0.64 mm.
   - **Cómo soldarlo:**
     1. Mete el alambre y dóblalo un poco en la cara de abajo para que no se caiga.
     2. Suelda arriba, voltea y suelda abajo.
     3. Corta a ras las dos caras y revisa continuidad entre los dos anillos.
   - **Espacio:** ninguna vía queda bajo el cuerpo de una pieza; cada anillo tiene al menos 0.3 mm libres respecto al patio de cualquier componente. Así el cautín entra por arriba aunque ya estén puestas las piezas.
   - **Bajo la ESP32-A** hay vías: suéldalas antes que los zócalos 1x15.
   - **Orden:** primero todas las vías y después los componentes.
2. **Bajo la ESP32-A** van los divisores de los encoders 4–6. Suéldalos (resistencias acostadas y capacitores de disco) **antes** que los headers hembra de la ESP32-A.
3. El resto de los componentes, de menor a mayor altura. Todos se sueldan **por abajo**, menos el **header 2x20 de la Pi**: va abajo y se suelda **por arriba**.
4. Las ESP32 van en headers hembra **1x15 en la fila exterior** (25.4 mm entre filas). La fila doble de pads también acepta clones de 22.86 mm.
5. **Pruebas sin módulos:** continuidad 5V–GND y SERVO_V–GND (no debe pitar). Luego enciende con fuente limitada en corriente.

## Notas y límites

- **H1** se taladra a Ø3.0 porque es pin de alineación. Para atornillar usa M2.5, o agrándalo a 3.2 con broca después de terminar.
- **Rail de servos con cobre de 35 µm:** las pistas V+/GND de los servos y de J6 miden 1.6–2.5 mm. Para más de 5 A continuos, **estáñalas** o suelda encima un alambre desnudo de 1 mm².
- **Plano de GND superior:** el cobre que no se fresa arriba queda unido a GND por las vías. No queda flotando.
- **Dónde se configura:** la tarjeta se genera desde `tools/rover_cubiko.py`, y el CAM y la simulación desde `tools/cubiko_cam.py`. Los comandos están abajo.

```bash
cd hardware/tools
```

```bash
ROVER_VARIANT=cubiko python3 generate.py --route
```

```bash
ROVER_VARIANT=cubiko python3 cubiko_cam.py
```
