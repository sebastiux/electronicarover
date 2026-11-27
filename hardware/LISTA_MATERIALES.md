# Lista de materiales y medidas para soldar (2 tarjetas de una cara)

Aplica a la tarjeta de **tracción** (97 × 96 mm) y a la de **servos** (76 × 108 mm), rev. 2.1. Las cantidades salen de los `bom.csv` y de las PCB; las medidas de pads y barrenos, de los `.kicad_pcb`.

Resumen en una imagen: [`lista_materiales.png`](lista_materiales.png).

## 1. Pads y barrenos: cuánto miden y qué pata entra

El archivo de taladro trae solo 4 medidas: **1.0, 1.3, 1.5 y 3.2 mm**. Los barrenos de resistencias, capacitores, LED y diodos van todos a 1.0 mm (no hay de 0.8, 0.9 ni 1.1). No hay metalizado: el barreno final es el taladrado.

- **Anillo** = cobre que queda alrededor del barreno, por lado. En pads ovalados van 2 valores: a lo largo de la fila / a lo ancho.
- **Pata real** = medida de hoja de datos; entre paréntesis, la diagonal o el diámetro máximo que debe pasar.

| Pieza | Pad de cobre | Barreno real | Anillo | Pata real | Holgura | Resultado |
|---|---|---|---|---|---|---|
| Header hembra 1x15 (zócalo de la ESP32) | ovalado 1.4 × 2.2 mm | 1.0 mm | 0.20 / 0.60 mm | cola plana ~0.64 × 0.40 mm (0.75–0.86); cuadrada de 0.64 en algunas (0.91–0.95) | 0.05–0.25 mm | Entra |
| Header macho 1x3 (servo) | ovalado 1.4 × 2.2 mm | 1.0 mm | 0.20 / 0.60 mm | cuadrada 0.64 mm (0.90; máx. de norma 0.98) | 0.02–0.15 mm | Entra, justo |
| Resistencia 1/4 W acostada (7.62 mm) | redondo 2.2 mm | 1.0 mm | 0.60 mm | redonda 0.45–0.60 mm | 0.4–0.5 mm | Entra |
| Resistencia 1/4 W de pie (2.54 mm) | ovalado 1.4 × 2.2 mm | 1.0 mm | 0.20 / 0.60 mm | redonda 0.45–0.60 mm | 0.4–0.5 mm | Entra |
| Cerámico 1 nF (paso 2.5 mm) | ovalado 1.36 × 2.2 mm | 1.0 mm | 0.18 / 0.60 mm | redonda 0.4–0.6 mm | 0.4–0.6 mm | Entra |
| Cerámico 100 nF (paso 5 mm) | redondo 2.2 mm | 1.0 mm | 0.60 mm | redonda 0.4–0.6 mm | 0.4–0.6 mm | Entra |
| Electrolítico 1000 µF (paso 5 mm) | 2.2 mm | 1.0 mm | 0.60 mm | redonda 0.6 mm (0.55–0.65) | 0.35 mm | Entra, **si el cuerpo es de Ø10 mm** |
| Schottky 1N5819 (DO-41, 10.16 mm) | 2.2 mm | 1.0 mm | 0.60 mm | redonda 0.71–0.86 mm | 0.14 mm | Entra |
| LED de 5 mm (paso 2.54 mm) | 1.4 × 2.2 mm | 1.0 mm | 0.20 / 0.60 mm | cuadrada 0.5 mm (0.71; máx. de hoja 0.92) | 0.08–0.29 mm | Entra |
| Bornera de 3.5 mm (KF350 / Phoenix PT 1,5) | ovalado 2.36 × 2.4 mm | **1.3 mm** | 0.53 / 0.55 mm | Phoenix: redonda 0.9 mm. KF350: plana, hasta ~1.15 de diagonal | 0.15–0.40 mm | Entra |
| Bornera de 5.08 mm (KF301 / Phoenix MKDS 1,5) | 2.6 mm | **1.5 mm** | 0.55 mm | Phoenix: 0.9 × 0.9 (1.27). KF301: ~1.0 × 0.8 (1.28; hasta ~1.42) | 0.08–0.23 mm | Entra |
| Cable 22 AWG (puentes por arriba) | redondo 2.0 mm | 1.0 mm | 0.50 mm | sólido 0.64 mm; multifilar 0.76–0.80 mm | 0.2–0.36 mm | Entra |
| Tornillo M3 (montaje) | sin cobre | 3.2 mm | — | 3.0 mm | 0.2 mm | Entra |

**Qué se corrigió con esta revisión.** Los barrenos de las borneras estaban a la medida de las Phoenix originales (1.2 y 1.3 mm). Las genéricas KF350 y KF301 traen pines planos más gruesos y sin hoja de datos confiable, así que se abrieron a **1.3 y 1.5 mm**. El cobre del pad no cambió.

**Barrenos por tarjeta:**

| Tarjeta | 1.0 mm | 1.3 mm | 1.5 mm | 3.2 mm | Total |
|---|---|---|---|---|---|
| Tracción | 96 (80 de piezas + 16 de cables) | 31 | 2 | 4 | 133 |
| Servos | 80 (78 de piezas + 2 del cable) | 3 | 6 | 4 | 93 |

### Mide esto antes de fresar

Las medidas de las patas vienen de hojas de datos y de valores típicos, no de tus piezas. Cuatro cosas dependen de lo que te llegue:

1. **ESP32 DevKit de 30 pines: 25.4 mm entre filas.** La tarjeta solo tiene esa opción. El módulo correcto mide ~28.2–28.5 mm de ancho. Si el tuyo mide ~25.5 mm de ancho, sus filas van a 22.86 mm y no entra.
2. **Fresa de 1.0 mm sin desgaste.** Si corta 0.9 mm, los barrenos salen 0.1 mm más chicos y los pines de header (0.90 mm de diagonal) y el 1N5819 pueden no entrar. Mídela: no menos de 0.98 mm.
3. **Electrolíticos de Ø10 mm con paso de 5 mm** (10×13, 10×16, 10×17 o 10×20). Los de Ø8 mm traen paso de 3.5 mm y no coinciden.
4. **Borneras:** mide el ancho y el grosor del pin. Si la diagonal pasa de 1.2 mm (KF350) o de 1.4 mm (KF301), avísame para abrir más ese barreno.

Lo más seguro: fresa primero en un retazo una fila de barrenos de 1.0, 1.3 y 1.5 mm y presenta un header, un LED, el 1N5819 y una bornera de cada tipo.

### Al soldar

- Los pads ovalados tienen 0.2 mm de anillo a lo largo de la fila y 0.6 mm a lo ancho: apoya el cautín en el lado largo, 2–3 s por pata.
- El FR1 suelta el cobre con el calor y con la fuerza. No fuerces una pata que no baja; repasa ese barreno.
- **Barrenos de montaje de tracción:** junto a J43 (esquina superior izquierda) la pista de MOTOR_EN pasa a 3.9 mm del centro, y en la esquina inferior derecha el +5V pasa a 4.4 mm. Ahí usa tornillo sin rondana metálica del lado del cobre, o separador y rondana de nylon. En los demás barrenos el cobre más cercano que no es GND está a 6.7 mm o más.
- Suelda los headers de la ESP32 con el módulo insertado como guía. Para sacar la ESP32, haz palanca pareja en los dos extremos.

## 2. Piezas soldadas

### Tarjeta de tracción

| Pieza | Cantidad | Referencias |
|---|---|---|
| Resistencia 10k, 1/4 W | 7 | R1, R2, R3, R21 (acostadas) · R4, R5, R6 (de pie) |
| Resistencia 20k, 1/4 W | 6 | R7, R8, R9 (acostadas) · R10, R11, R12 (de pie) |
| Resistencia 1k, 1/4 W | 2 | R13, R14 |
| Resistencia 330 Ω, 1/4 W | 1 | R25 |
| Capacitor cerámico 1 nF (102), paso 2.5 mm | 6 | C11–C16 |
| Electrolítico 1000 µF 16 V, Ø10 mm, paso 5 mm | 1 | C2 |
| LED 5 mm verde | 1 | D3 |
| Schottky 1N5819 (DO-41) | 1 | D5 |
| Header hembra 1x15, paso 2.54 mm | 2 | U2 (zócalo de la ESP32-A) |
| Bornera KF350 de 3 vías, paso 3.5 mm | 9 | J41, J42, J43 (3+3 cada una) · J7, J8 (una cada una) · J9 |
| Bornera KF350 de 2 vías, paso 3.5 mm | 2 | J7, J8 (3+2) |
| Bornera KF301 de 2 vías, paso 5.08 mm | 1 | J5 |
| Cable 22 AWG para los 8 puentes | ~25 cm | W1–W8 (7 de GND y 1 de +5V) |

### Tarjeta de servos

| Pieza | Cantidad | Referencias |
|---|---|---|
| Resistencia 1k, 1/4 W | 2 | R15, R16 (de pie) |
| Resistencia 100k, 1/4 W | 1 | R22 |
| Resistencia 27k, 1/4 W | 1 | R23 |
| Resistencia 2.2k, 1/4 W | 1 | R24 |
| Resistencia 470 Ω, 1/4 W | 1 | R26 |
| Capacitor cerámico 100 nF (104), paso 5 mm | 1 | C5 |
| Electrolítico 1000 µF 16 V, Ø10 mm, paso 5 mm | 2 | C3, C4 |
| LED 5 mm rojo | 1 | D2 |
| LED 5 mm azul | 1 | D4 |
| Schottky 1N5819 (DO-41) | 1 | D6 |
| Header hembra 1x15, paso 2.54 mm | 2 | U3 (zócalo de la ESP32-B) |
| Header macho 1x3, paso 2.54 mm | 8 | J31–J38 (servos) |
| Bornera KF350 de 3 vías, paso 3.5 mm | 1 | J9 |
| Bornera KF301 de 2 vías, paso 5.08 mm | 3 | J2, J5, J6 |
| Cable 22 AWG para 1 puente | ~2 cm | W1 (6 V, entre C3 y C4) |

### Total a comprar para las 2 tarjetas

| Pieza | Cantidad |
|---|---|
| Resistencias 1/4 W | 22: 10k ×7 · 20k ×6 · 1k ×4 · 100k ×1 · 27k ×1 · 2.2k ×1 · 330 Ω ×1 · 470 Ω ×1 |
| Capacitor cerámico 1 nF (102) | 6 |
| Capacitor cerámico 100 nF (104) | 1 |
| Electrolítico 1000 µF 16 V, Ø10 mm, paso 5 mm | 3 |
| Schottky 1N5819 | 2 |
| LED 5 mm | 3: verde, rojo y azul |
| Header hembra 1x15 | 4 (o 2 tiras 1x40: de cada una salen 2 tramos) |
| Header macho 1x3 | 8 (1 tira 1x40) |
| Bornera KF350 de 3 vías | 10 |
| Bornera KF350 de 2 vías | 2 |
| Bornera KF301 de 2 vías | 4 |

Si compras un kit de resistencias, revisa que traiga 20k y 27k: muchos no las incluyen.

## 3. Módulos y electrónica que va fuera de las tarjetas

| Pieza | Cantidad | Nota |
|---|---|---|
| ESP32 DevKit V1 de 30 pines, 25.4 mm entre filas | 2 | Enchufadas en los headers 1x15 |
| Raspberry Pi 5 | 1 | Se alimenta por el GPIO desde el step-down |
| Tarjeta microSD para la Pi (16 GB o más) | 1 | |
| HAT de bornas de tornillo para el GPIO de 40 pines | 1 | De ahí salen los 2 cables UART y entra el 5 V |
| Diodo TVS SA5.0A | 1 | En las bornas 5V y GND del HAT, banda al 5V |
| Módulo L298N | 3 | Sin los jumpers de ENA y ENB |
| Motor Pololu 37D de 12 V con encoder | 6 | Solo se usa el canal A del encoder |
| Servo de 3 hilos a 6 V (el firmware está ajustado al Power HD 1501MG) | 8 | 4 de dirección y 4 del brazo |
| Cable USB de datos para grabar las ESP32 | 1 | Micro-USB o USB-C según el módulo |

## 4. Alimentación y cableado

| Pieza | Cantidad | Nota |
|---|---|---|
| Batería LiPo 3S (11.1 V) con XT60 | 1 | El diseño se pensó para una de 5000 mAh |
| Cargador balanceador para LiPo 3S | 1 | Si no lo tienes |
| Portafusible ATO en línea | 1 | En el positivo, entre batería y bloque |
| Fusible ATO de 15 A | 1 (+2 de repuesto) | |
| Bloque de distribución, positivo y negativo | 1 de 2 polos | 6 salidas por polo: 3 L298N, step-down, BEC y la derivación a J2 |
| Step-down 12 V → 5 V, 5 A | 1 | Alimenta el HAT de la Pi y el J5 de cada tarjeta |
| Empalme para repartir el 5 V a 3 destinos | 2 conectores de 5 vías (uno para + y uno para GND) | O soldar y cubrir con termocontráctil |
| BEC 12 V → 6 V, 10 A o más | 1 | A J6 de la tarjeta de servos |
| Conector XT60 | 1 par (+1 de repuesto) | |
| Cable de silicón 14–16 AWG, rojo y negro | ~2 m de cada color | Batería, fusible, bloque, L298N, step-down, BEC y J6 |
| Cable 18 AWG, rojo y negro | ~0.5 m de cada color | Del step-down al HAT de la Pi |
| Cable 22 AWG de colores | 1 kit | Bornas ↔ L298N (18 hilos), 2 cables UART de 3 hilos, J2, los dos J5 y los puentes |
| Cables con terminal Dupont hembra | 18 puntas (un kit de 40 alcanza) | 12 para IN1–IN4 y 6 para los 3 cables en Y de EN |

## 5. Mecánica y fresado

| Pieza | Cantidad | Nota |
|---|---|---|
| Placa fenólica FR1 de **una cara**, 10 × 15 cm, 1.6 mm | 2 (+1 de prueba) | Una por tarjeta |
| Fresa plana de 1.0 mm, zanco de 3.175 mm | 1 (+1 de repuesto) | La única herramienta; el filo debe cortar al menos 2 mm |
| Cinta doble cara delgada | 1 rollo | |
| Mártir de MDF de 6 mm | 1 | |
| Separador M3 con tornillos (tarjetas al chasis) | 8 | 4 por tarjeta, de 6 mm o más de alto |
| Separador M3 con tornillos (L298N al chasis) | 12 | 4 por módulo |
| Separador M2.5 con tornillos (Raspberry Pi) | 4 | 8 si además fijas el HAT |

**Herramienta y consumibles que no están en la lista:** cautín y soldadura, multímetro, vernier, termocontráctil, lija y una fuente limitada en corriente para la primera prueba.

**Ya no se usan** (eran de la versión de 2 caras): header hembra 2x20, pines para vías, placa de doble cara, fresa en V, brocas y pasadores de alineación.
