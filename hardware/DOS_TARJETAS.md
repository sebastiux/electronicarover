# Rover en 2 tarjetas de una cara: tracción y servos

Esta versión reparte el controlador en **2 tarjetas de una sola cara** (cobre solo abajo), unidas por bornas. Ninguna lleva soldaduras por arriba ni vías entre caras.

| Tarjeta | Lleva | Tamaño | Cables por arriba | Fresado |
|---|---|---|---|---|
| **Tracción** (`cnc_traccion/`) | ESP32-A, bornas de los 3 L298N, encoders | 96.2 × 110.5 mm | 4 | 30–50 min en LPKF · ~102 min en Cubiko |
| **Servos** (`cnc_servos/`) | ESP32-B, 8 servos (4 de dirección y 4 del brazo), batería | 73.5 × 100 mm | 0 | 15–30 min en LPKF · ~56 min en Cubiko |

- **Raspberry Pi 5:** coordina a las 2 ESP32. Va aparte, con un **HAT de bornas** (header hembra 2x20 sobre el GPIO). De ahí sale un cable de 3 hilos a la borna `PI` (J9) de cada tarjeta.
- **ESP32:** van en headers hembra 1x15, como antes. El firmware no cambia de pines.
- **Una sola fresa de 1.0 mm** para aislar, en **2 pasadas por lado**, con cualquier programa (LPKF CircuitPro, FlatCAM o el G-code de aquí). Las dos caben en placas de 10 × 15 cm.
- **Reglas en las 2 tarjetas:** aislamiento de **2.0 mm** (el doble de la fresa), pistas de 1.0 mm o más, relleno de cobre en los huecos que dejarían tiras sueltas, 2 mm libres en la orilla y barrenos de solo 1.0, 1.3, 1.5 y 3.2 mm. Junto a los pines a 2.54 mm el hueco no puede llegar a 2.0: queda en 1.14 mm entre pads vecinos, 1.34 mm entre una pista y el pad vecino y 1.54 mm entre pistas de pines vecinos. Lo revisan `tools/verifica_espacios.py` y `tools/sim_cam_union.py`.

## Diagrama de conexiones

Para entender el circuito completo (voltajes, señales y cada tarjeta por dentro) está `esquema_didactico/esquema_rover.pdf`.

```
                  Batería 3S ── fusible 15 A ── bloque de distribución (GND en estrella)
                                                  │
        ┌───────────────┬─────────────────────────┼──────────────────────┬────────────────┐
     3x L298N     step-down 5 V 5 A                                   BEC 6 V ≥10 A      J2 (medición)
   (12 V motores)  │        │          │                                  │                │
                   │        │          └── J5 tarjeta SERVOS              └── J6 SERVOS    └── tarjeta SERVOS
                   │        └── J5 tarjeta TRACCIÓN
                   └── HAT de bornas de la Pi (5V, GND) + TVS SA5.0A en esas bornas

   Pi (HAT) GND/TXD2/RXD2  ── 3 hilos ──  J9 tarjeta TRACCIÓN  (ESP32-A, UART2)
   Pi (HAT) GND/TXD4/RXD4  ── 3 hilos ──  J9 tarjeta SERVOS    (ESP32-B, UART4)
```

## Cableado de la Raspberry Pi (HAT de bornas)

| Borna del HAT (pin del GPIO) | Va a (tornillo, visto por el lado de componentes) |
|---|---|
| 5V (pines 2 y 4) | + del step-down 5 V (cable de 18 AWG o más) |
| GND (pin 6) | − del step-down y J9 de tracción, tornillo de **abajo** |
| GPIO5 = RXD2 (pin 29) | J9 de tracción, tornillo de **en medio** |
| GPIO4 = TXD2 (pin 7) | J9 de tracción, tornillo de **arriba** |
| GND (pin 34) | J9 de servos, tornillo **izquierdo** |
| GPIO12 = TXD4 (pin 32) | J9 de servos, tornillo de **en medio** |
| GPIO13 = RXD4 (pin 33) | J9 de servos, tornillo **derecho** |

- **TVS SA5.0A:** atorníllalo en las bornas 5V y GND del HAT. La banda (cátodo) va al 5V.
- **Cables UART:** trenzados (TX, RX y GND juntos), de menos de 50 cm.
- **`/boot/firmware/config.txt`:**
  - `dtoverlay=uart2-pi5` → `/dev/ttyAMA2`, tracción.
  - `dtoverlay=uart4-pi5` → `/dev/ttyAMA4`, servos.
  - `usb_max_current_enable=1`, porque la Pi se alimenta por el GPIO.
- **En la Pi, antes de usar `rover_link.py`:** `export ROVER_ESPB_PORT=/dev/ttyAMA4` (su valor por defecto es el UART0 de la tarjeta v1.2).

## Cableado de los L298N (bornas de 6 vías de la tarjeta de tracción)

| Pin de la borna | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| Señal | EN | IN4 | IN3 | IN2 | IN1 | GND |
| Pin del L298N | **ENA + ENB** | IN4 | IN3 | IN2 | IN1 | GND |

En cada módulo:
1. Quita los 2 jumpers de ENA y ENB.
2. Une los 2 pines de EN al hilo EN con un cable en Y.

MOTOR_EN tiene un pull-down de 10k en la tarjeta: ningún motor se mueve hasta que el firmware lo habilita.

## Qué se compra

La lista completa con cantidades, y las medidas de cada pad y barreno, están en [`LISTA_MATERIALES.md`](LISTA_MATERIALES.md). Lo que cambia respecto a la versión de 2 caras:

| Qué | Cantidad | Búsqueda en Mercado Libre |
|---|---|---|
| HAT de bornas para el GPIO de la Raspberry Pi (40 pines) | 1 | [hat bornas gpio raspberry](https://listado.mercadolibre.com.mx/hat-bornas-gpio-raspberry) · [breakout terminal raspberry](https://listado.mercadolibre.com.mx/raspberry-pi-gpio-terminal-block-breakout) |
| Placa fenólica FR1 **una cara** 10 × 15 cm | 2 (+1 de prueba) | [placa fenólica una cara 10x15](https://listado.mercadolibre.com.mx/placa-fenolica-una-cara-10x15) |
| Borna KF350 paso 3.5 mm, 3 vías (encastrable, barreno de 1.3 mm) | 10 | [KF350 3 pines](https://listado.mercadolibre.com.mx/bornera-kf350-3.5mm) |
| Borna KF350 paso 3.5 mm, 2 vías (encastrable) | 2 | (la misma búsqueda) |
| Borna KF301 paso 5.08 mm, 2 vías (barreno de 1.5 mm) | 4 | [KF301 2 pines](https://listado.mercadolibre.com.mx/bornera-kf301-2-pines-5.08) |
| Cable aislado 22 AWG (para los 4 cables por arriba) | 1 m | [cable 22 awg](https://listado.mercadolibre.com.mx/cable-calibre-22-kit-colores) |

Cómo se arman las bornas encastrables:
- **L298N (6 vías):** 3 + 3, ×3 bornas → 6 bornas de 3 vías.
- **Encoders (5 vías):** 3 + 2, ×2 bornas → 2 de 3 vías y 2 de 2 vías.
- **PI (3 vías):** ×2 → 2 de 3 vías.

Lo que ya **no** hace falta: el header hembra 2x20 y los pines para vías. El resto de la lista (`cubiko/compras_mercadolibre.md`) sigue igual.

## Verificación

| Prueba | Tracción | Servos |
|---|---|---|
| DRC de KiCad (aislamiento 2.0 mm, orilla 2 mm) | 0 violaciones, 0 pads sin conectar | 0 violaciones, 0 pads sin conectar |
| Esquemático contra PCB, pin por pin | 113 pines, 0 diferencias | 87 pines, 0 diferencias |
| Aislamiento como lo hace la LPKF (`tools/sim_cam_union.py`), 1 y 2 pasadas, corte real de 0.8 a 1.1 mm | 0 cortos, 0 redes abiertas | 0 cortos, 0 redes abiertas |
| Fresado con el G-code de la Cubiko (`tools/cubiko_cam.py`) | 0 cortos, 0 redes abiertas | 0 cortos, 0 redes abiertas |
| Pistas de menos de 1 mm · cobre a menos de 2 mm de la orilla | 0 · 0 | 0 · 0 |
| Brocas | 1.0, 1.3, 1.5 y 3.2 mm | 1.0, 1.3, 1.5 y 3.2 mm |
| Firmware simulado sobre el netlist (UART por el HAT, EN en Y) | 48/48 | 38/38 |

## Regenerar

```bash
cd hardware/tools
ROVER_VARIANT=traccion python3 generate.py --route    # o servos
ROVER_VARIANT=traccion python3 cubiko_cam.py
```

- **`generate.py --route`:** rutea la tarjeta y genera su esquemático jerárquico.
- **`cubiko_cam.py`:** genera los Gerbers, `fresa1mm_todo.nc` y la simulación en `hardware/cnc_<tarjeta>/`.
- **`sim_cam_union.py`:** simula el aislamiento de un programa genérico (LPKF, FlatCAM) con la fresa de 1.0 mm (`PASADAS=2` para las 2 pasadas por lado).
- **Fuentes del diseño:** `tools/rover_traccion.py`, `tools/rover_servos.py` y `tools/rover_split_comun.py`.
