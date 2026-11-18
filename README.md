# electronicarover

Electrónica del rover: Raspberry Pi 5 como cerebro, 2× ESP32 esclavas (tracción y servos) y 3× L298N para 6 motores Pololu 37D.

- [`hardware/`](hardware/README.md): PCB portadora en KiCad (esquemático, PCB, footprints propios, generador en Python).
- [`firmware/common/rover_pins.h`](firmware/common/rover_pins.h): mapa de pines de la PCB para el firmware.
