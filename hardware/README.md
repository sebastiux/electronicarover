# Rover Controller v1.0: PCB de UNA capa (KiCad)

PCB de **una sola capa de cobre** de 200 × 150 mm. Los módulos se montan encima y la tarjeta los interconecta, así que los únicos cables que salen son los de **batería, motores/encoders, servos y reguladores**.

| Bloque | Módulo | Función |
|---|---|---|
| U1 | **Raspberry Pi 5**, debajo de la PCB con stacking header 2x20 | Cerebro |
| U2 | **ESP32 DevKit V1 30p** (ESP32-A, horizontal) | Tracción: 6 motores + 6 encoders |
| U3 | **ESP32 DevKit V1 30p** (ESP32-B, vertical) | 4 servos de dirección + 3 del brazo + 1 de reserva, voltaje de batería |
| U4–U6 | **3× L298N (HW-095)** con pines en vez de bornas | 6× Pololu 37D 12V 30:1 |
| J1 | **XT60 macho** | Batería LiPo 3S (Gens Ace 5000 mAh) |
| J3 / J4 / J5 / J6 | Borneras 5.08 mm | 12 V hacia el step-down de 5 V, 12 V hacia el BEC de servos, entrada de 5 V/5 A y entrada de servos a 6 V |
| J11–J16 + J21–J26 | Bornera + header 1x6 (cable Pololu) | Motores y encoders |
| J31–J38 | Header 1x3 (GND, V+, SIG) | Servos |

![PCB](docs/img/pcb_completa.png)

**Estado:** ruteada al 100 % en una capa. DRC de KiCad: **0 violaciones y 0 conexiones pendientes**. Lleva **43 puentes de alambre** (669 mm en total, el más largo de 62 mm), numerados W1–W43 en la serigrafía y listados en `fab/puentes_alambre.csv`.

| Vista | Archivo |
|---|---|
| Cobre (B.Cu) | `docs/img/pcb_cobre.png` |
| Montaje y puentes | `docs/img/pcb_montaje.png`, `docs/montaje_y_puentes.pdf` |
| Cobre espejado 1:1 para planchado/CNC | `docs/cobre_BCu_espejo_1a1.pdf` |
| Gerbers de 1 capa | `fab/rover_controller_gerbers_1capa.zip` |

**Tierra común:** existe una sola red `GND` que une batería, L298N, Pi, ESP32, servos y encoders. En la cara de cobre está además el plano de GND relleno.

## Cómo se fabrica una PCB de una capa

- **Cobre:** solo `B.Cu`, la cara de soldadura. Los componentes van del otro lado, en la cara superior.
- **Puentes de alambre:** donde dos pistas tendrían que cruzarse se usa un puente de alambre. Cada puente tiene dos barrenos y en KiCad aparece como un tramo **rojo en `F.Cu`**. **`F.Cu` no se fabrica**: solo indica dónde va cada alambre. La lista con coordenadas y largo está en `rover_controller/puentes_alambre.csv`; usa alambre aislado (AWG22–24 en señales, AWG18 en potencia).
- **Para hacerla en casa** (planchado, fotolito o CNC), usa `docs/cobre_BCu_espejo_1a1.pdf`. Es el cobre visto desde la cara de cobre, ya espejado, a escala 1:1.
- **Para mandarla a fabricar**, usa `fab/rover_controller_gerbers_1capa.zip`, con solo las capas B.Cu, B.Mask, F.SilkS, Edge.Cuts y los taladros. Se genera con `tools/export_fab.sh`.
- **Barrenos de montaje al chasis:** 8 M3 en las orillas (H1–H8), más los 4 M2.5 de la Raspberry Pi.

## Estructura

```
hardware/
├── rover_controller/          Proyecto KiCad (abrir rover_controller.kicad_pro)
│   ├── rover.kicad_sym / rover.pretty/   símbolos y footprints propios
│   ├── bom.csv                lista de materiales
│   └── puentes_alambre.csv    puentes de alambre (posición y largo)
├── tools/
│   ├── rover_design.py        FUENTE DE VERDAD: pines, redes, posiciones, cotas, guías de ruteo
│   ├── generate.py            genera el esquemático y la PCB (--route: rutea en una capa)
│   ├── router1l.py            ruteador de una capa con puentes de alambre
│   └── export_fab.sh          Gerbers, PDFs 1:1 e imágenes
└── docs/
firmware/common/rover_pins.h   mapa de pines para el firmware
```

Para regenerar, usa el Python de KiCad 7 o posterior con `numpy` y `scipy` instalados. El ruteo es determinista y tarda unos 25 minutos. Sin `--route` el script no sobrescribe una PCB ya ruteada.

```bash
python3 hardware/tools/generate.py --route
```

```bash
hardware/tools/export_fab.sh
```

## Antes de fabricar: verifica las cotas

Las posiciones de los pines del **L298N** son las medidas típicas del HW-095 (43 × 43 mm, agujeros M3 a 36.6 mm). **Imprime `docs/plantilla_1a1.pdf` al 100 %** y pon encima los L298N (ya sin bornas), las ESP32 y la Pi. Si algo no coincide, corrige el diccionario `L298N`, `ESP32` o `RPI` en `rover_design.py` y vuelve a generar.

La fila doble de pads de cada ESP32 acepta clones con 25.4 o 22.86 mm entre filas.

## Montaje

### L298N

1. Desuelda las 3 bornas azules y el header 1x6 (`ENA IN1 IN2 IN3 IN4 ENB`).
2. **Quita los jumpers ENA/ENB.** En la PCB van a `MOTOR_EN`.
3. **Deja puesto el jumper 5V-EN.** El regulador 78M05 del módulo alimenta su lógica, y su pin **+5V alimenta los dos encoders** de ese módulo.
4. Suelda header macho por arriba del módulo, con los pines saliendo por abajo, en las 7 posiciones de potencia y las 6 lógicas. Monta el módulo con standoffs M3.

### Raspberry Pi 5

En una PCB de una capa no se puede soldar un header por la cara de los componentes. Por eso:

1. Usa un **stacking header 2x20 de pines largos**. Insértalo **desde abajo**, deja unos 3 mm entre el cuerpo y la PCB y suéldalo por la **cara de cobre**.
2. La Pi se enchufa por debajo al lado hembra del header. Usa standoffs M2.5: 11 mm, o 16–18 mm con el Active Cooler.
3. Los pines largos sobresalen por arriba de la PCB. Ahí puedes conectar con cables Dupont los GPIO que quedan libres (I2C, etc.).

### ESP32

Van sobre headers hembra 1x15, así que se pueden quitar.

- **ESP32-A** va horizontal, con la antena a la izquierda y el USB a la derecha.
- **ESP32-B** va vertical, con la antena arriba y el USB abajo.

## Arquitectura eléctrica

```
Batería 3S (XT60) ─► F1 15 A ─► VBAT_F ─┬─► L298N +12V (x3)
                                         ├─► J3 ─► step-down 5V/5A ─► J5 ─► +5V (Pi 5, ESP32)
                                         └─► J4 ─► BEC 6V ≥10A ─────► J6 ─► SERVO_V (8 servos)
L298N (regulador 78M05 del módulo) ─► +5V de los encoders de sus 2 motores
```

- **Pi 5 por GPIO:** en `/boot/firmware/config.txt` agrega `usb_max_current_enable=1`. Además corre `sudo rpi-eeprom-config -e` y pon `PSU_MAX_CURRENT=5000`. Para proteger la Pi hay un TVS SA5.0A (D1) y 1000 µF (C2).
- **UART sin cables:** la Pi tiene UART2 (GPIO4/5, `/dev/ttyAMA2`) hacia la ESP32-A y UART0 (GPIO14/15, `/dev/ttyAMA0`) hacia la ESP32-B, con 1k en serie. Activa `dtoverlay=uart2-pi5` y `dtoverlay=uart0-pi5`.
- **Asignación de pines** (ver `firmware/common/rover_pins.h`): está pensada para que la placa de una capa se pueda rutear.
  - En la ESP32-A, los IN1–IN4 de los tres L298N siguen el mismo orden que la fila de pines, así que las pistas bajan en abanico sin cruzarse.
  - En la ESP32-B, cada servo queda a la misma altura que su GPIO.
- **`MOTOR_EN`** (IO13 de la ESP32-A, con pull-down) habilita los 6 canales. Los motores no se mueven mientras arranca la ESP32.
- **Encoders:** solo el canal A, con divisor 10k/20k de 5 V a 3.3 V.
- **Batería:** IO34 de la ESP32-B, con divisor 100k/27k. Corta los motores si la LiPo baja de 3.3 V por celda (9.9 V).

### Componentes discretos

- Resistencias de **1/4 W** de orificio pasante.
- **LEDs de 5 mm:** D2 rojo (12 V), D3 verde (5 V) y D4 azul (servos).
- Electrolíticos radiales, TVS en encapsulado DO-15 y portafusible ATO.

## ⚠️ Limitaciones

1. **L298N vs. Pololu 37D:** el motor pide hasta **5.5 A** cuando se bloquea y el L298N soporta unos 2 A continuos por canal. Además pierde 2–3 V. Usa rampas de PWM y detecta bloqueos con el encoder.
2. Con una sola capa hacen falta **puentes de alambre**: revisa `puentes_alambre.csv`. Coloca los puentes **antes** que los módulos, porque algunos pasan por debajo de los L298N o de las ESP32.
3. **ESP32-A:** GPIO1 (TX0) maneja un IN del L298N. No uses `Serial.print()` mientras controlas los motores; para telemetría usa `Serial2` hacia la Pi.
4. No hay protección contra polaridad inversa. Respeta la polaridad del XT60: lado recto = +, lado biselado = −.
