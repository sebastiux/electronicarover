# Firmware: Rover Controller v1.1

| Carpeta | Qué contiene |
|---|---|
| `traction/` | ESP32-A: 6 motores (3× L298N), 6 encoders, enlace UART con la Pi |
| `servos/` | ESP32-B: 8 servos (50 Hz), voltaje de batería, enlace UART con la Pi |
| `common/` | Mapa de pines (`rover_pins.h`), protocolo y lógica de motores |
| `pi/rover_link.py` | Driver para la Raspberry Pi 5 y pruebas de banco |
| `test/` | Simulación del firmware sobre el netlist **real** de la PCB |

## Compilar y grabar

```bash
cd firmware
```

```bash
pio run
```

```bash
pio run -e traction -t upload
```

```bash
pio run -e servos -t upload
```

## Verificación firmware ↔ PCB (antes de fabricar)

```bash
python3 hardware/tools/export_board_model.py
```

```bash
firmware/test/run_tests.sh
```

`export_board_model.py` lee `rover_controller.kicad_pcb` y genera el modelo de la tarjeta. La simulación compila el firmware real con una capa que simula las funciones de Arduino y comprueba:

- Arranque seguro: `MOTOR_EN` en LOW, con pull-down y conectado a los 6 ENA/ENB.
- **Cada comando mueve el motor correcto con la polaridad correcta**: GPIO → L298N → bornera y header Pololu.
- Encoders: conector → divisor 10k/20k (nivel de 3.33 V) → GPIO → telemetría en el índice correcto.
- UART con TX/RX cruzados hacia el UART correcto de la Pi.
- Servos: GPIO → header (GND, V+, SIG), con pulsos de 800–2200 µs.
- Voltaje de batería: el divisor R22/R23 se lee con un error menor a 5 % de 9 a 14.4 V.
- Diodos Schottky en VIN, strapping pins, pines solo de entrada, ADC1 y canales LEDC.
- Watchdog, corte por bloqueo y checksums del protocolo.

El resultado de la última corrida está en `hardware/docs/verificacion_firmware_pcb.txt`: **87/87 OK**. Además, ambos firmwares compilan con PlatformIO (Arduino-ESP32 3.3) sin warnings.

## Raspberry Pi

`/boot/firmware/config.txt`:

```
dtoverlay=uart2-pi5
dtoverlay=uart0-pi5
usb_max_current_enable=1
```

- `uart2-pi5` es GPIO4/5 → ESP32-A, `/dev/ttyAMA2`.
- `uart0-pi5` es GPIO14/15 → ESP32-B, `/dev/ttyAMA0`. Así va en la tarjeta v1.2.

**En las 2 tarjetas de una cara y en la tarjeta Cubiko** la ESP32-B va por UART4 (GPIO12/13, pines 32 y 33). Cambia la segunda línea por `dtoverlay=uart4-pi5` y, antes de usar `rover_link.py`:

```bash
export ROVER_ESPB_PORT=/dev/ttyAMA4
```

El firmware de las ESP32 es el mismo en todas las versiones.

Pruebas en el banco, con las ruedas al aire:

```bash
python3 firmware/pi/rover_link.py test-motores
```

```bash
python3 firmware/pi/rover_link.py test-servos
```
