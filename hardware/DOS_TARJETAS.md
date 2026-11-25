# Rover en 2 tarjetas de una cara: tracción y servos

Esta versión reparte el controlador en **2 tarjetas de una sola cara** (cobre solo abajo), unidas por bornas. Ninguna lleva soldaduras por arriba ni vías entre caras.

| Tarjeta | Lleva | Tamaño | Cables por arriba | Fresado |
|---|---|---|---|---|
| **Tracción** (`cnc_traccion/`) | ESP32-A, bornas de los 3 L298N, encoders | 92 × 96 mm | 5 | ~74 min |
| **Servos** (`cnc_servos/`) | ESP32-B, 8 servos (4 de dirección y 4 del brazo), batería | 70 × 88 mm | 0 | ~43 min |

- **Raspberry Pi 5:** coordina a las 2 ESP32. Va aparte, con un **HAT de bornas** (header hembra 2x20 sobre el GPIO). De ahí sale un cable de 3 hilos a la borna `PI` (J9) de cada tarjeta.
- **ESP32:** van en headers hembra 1x15, como antes. El firmware no cambia de pines.

## Diagrama de conexiones

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

| Borna del HAT (pin del GPIO) | Va a |
|---|---|
| 5V (pines 2 y 4) | + del step-down 5 V (cable de 18 AWG o más) |
| GND (pin 6) | − del step-down y J9-1 de la tarjeta de tracción |
| GPIO4 = TXD2 (pin 7) | J9-2 de tracción |
| GPIO5 = RXD2 (pin 29) | J9-3 de tracción |
| GND (pin 34) | J9-1 de la tarjeta de servos |
| GPIO12 = TXD4 (pin 32) | J9-2 de servos |
| GPIO13 = RXD4 (pin 33) | J9-3 de servos |

- **TVS SA5.0A:** atorníllalo en las bornas 5V y GND del HAT. La banda (cátodo) va al 5V.
- **Cables UART:** trenzados (TX, RX y GND juntos), de menos de 50 cm.
- **`/boot/firmware/config.txt`:**
  - `dtoverlay=uart2-pi5` → `/dev/ttyAMA2`, tracción.
  - `dtoverlay=uart4-pi5` → `/dev/ttyAMA4`, servos.
  - `usb_max_current_enable=1`, porque la Pi se alimenta por el GPIO.

## Cableado de los L298N (bornas de 6 vías de la tarjeta de tracción)

| Pin de la borna | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| Señal | EN | IN4 | IN3 | IN2 | IN1 | GND |
| Pin del L298N | **ENA + ENB** | IN4 | IN3 | IN2 | IN1 | GND |

En cada módulo:
1. Quita los 2 jumpers de ENA y ENB.
2. Une los 2 pines de EN al hilo EN con un cable en Y.

MOTOR_EN tiene un pull-down de 10k en la tarjeta: ningún motor se mueve hasta que el firmware lo habilita.

## Qué se compra distinto a la versión de 2 caras

| Qué | Cantidad | Búsqueda en Mercado Libre |
|---|---|---|
| HAT de bornas para el GPIO de la Raspberry Pi (40 pines) | 1 | [hat bornas gpio raspberry](https://listado.mercadolibre.com.mx/hat-bornas-gpio-raspberry) · [breakout terminal raspberry](https://listado.mercadolibre.com.mx/raspberry-pi-gpio-terminal-block-breakout) |
| Placa fenólica FR1 **una cara** 10 × 15 cm | 2 (+1 de prueba) | [placa fenólica una cara 10x15](https://listado.mercadolibre.com.mx/placa-fenolica-una-cara-10x15) |
| Borna KF350 paso 3.5 mm, 3 vías (encastrable) | 10 | [KF350 3 pines](https://listado.mercadolibre.com.mx/bornera-kf350-3.5mm) |
| Borna KF350 paso 3.5 mm, 2 vías (encastrable) | 2 | (la misma búsqueda) |
| Borna KF301 paso 5.08 mm, 2 vías | 4 | [KF301 2 pines](https://listado.mercadolibre.com.mx/bornera-kf301-2-pines-5.08) |
| Cable aislado 22 AWG (para los 5 cables por arriba) | 1 m | [cable 22 awg](https://listado.mercadolibre.com.mx/cable-calibre-22-kit-colores) |

Cómo se arman las bornas encastrables:
- **L298N (6 vías):** 3 + 3, ×3 bornas → 6 bornas de 3 vías.
- **Encoders (5 vías):** 3 + 2, ×2 bornas → 2 de 3 vías y 2 de 2 vías.
- **PI (3 vías):** ×2 → 2 de 3 vías.

Lo que ya **no** hace falta: el header hembra 2x20 y los pines para vías. El resto de la lista (`cubiko/compras_mercadolibre.md`) sigue igual.

## Verificación

| Prueba | Tracción | Servos |
|---|---|---|
| DRC de KiCad | 0 violaciones, 0 pads sin conectar | 0 violaciones, 0 pads sin conectar |
| Conectividad con pads solo abajo y los cables por arriba | 0 conexiones abiertas | 0 conexiones abiertas |
| Esquemático contra PCB, pin por pin | 113 pines, 0 diferencias | 87 pines, 0 diferencias |
| Simulación del fresado (`tools/cubiko_cam.py`) | 0 cortos, 0 redes abiertas | 0 cortos, 0 redes abiertas |
| Firmware simulado sobre el netlist (UART por el HAT, EN en Y) | 48/48 | 38/38 |
| Simulador del Fab Lab (3 archivos, sin volteo) | Board done, 3 de 3 (~72 min) | Board done, 3 de 3 (~40 min) |

## Regenerar

```bash
cd hardware/tools
ROVER_VARIANT=traccion python3 generate.py --route    # o servos
ROVER_VARIANT=traccion python3 cubiko_cam.py
```

- **`generate.py --route`:** rutea la tarjeta y genera su esquemático jerárquico.
- **`cubiko_cam.py`:** genera los G-code y la simulación en `hardware/cnc_<tarjeta>/`.
- **Fuentes del diseño:** `tools/rover_traccion.py`, `tools/rover_servos.py` y `tools/rover_split_comun.py`.
