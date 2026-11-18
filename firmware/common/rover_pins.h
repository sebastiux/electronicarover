// rover_pins.h - Mapa de pines de la PCB Rover Controller v1.0 (2 capas)
// Fuente: hardware/tools/rover_design.py (mantener sincronizado).
//
// Las asignaciones estan elegidas para que el ruteo de la PCB quede limpio:
// el orden fisico de los pines de la ESP32 coincide con el orden de los
// destinos. Los UART del ESP32 se remapean (Serial2.begin(baud, cfg, RX, TX)).
#pragma once

// ===========================================================================
// ESP32-A : TRACCION (U2, montada horizontal bajo los L298N)
// ===========================================================================
#if defined(ROVER_ESP32_A)

// Habilitacion global de los 6 canales (ENA/ENB de los 3 L298N).
// Pull-down de 10k: los motores quedan APAGADOS hasta que el firmware ponga
// este pin en HIGH (los IN pueden "parpadear" durante el arranque sin efecto).
#define PIN_MOTOR_EN 13

// Control por motor: PWM en un IN y el otro en LOW (EN = HIGH via MOTOR_EN).
//   avance:  IN_A = PWM, IN_B = 0      reversa: IN_A = 0, IN_B = PWM
//   freno:   IN_A = 1,   IN_B = 1      libre:   MOTOR_EN = 0 (afecta a todos)
//                          {IN_A, IN_B}
#define PIN_M1 {23, 22} // U4 IN1/IN2 -> OUT1/OUT2  Delantero Izq
#define PIN_M2 {1, 21}  // U4 IN3/IN4 -> OUT3/OUT4  Delantero Der  (GPIO1 = TX0!)
#define PIN_M3 {19, 18} // U5 IN1/IN2               Medio Izq
#define PIN_M4 {5, 17}  // U5 IN3/IN4               Medio Der
#define PIN_M5 {16, 4}  // U6 IN1/IN2               Trasero Izq
#define PIN_M6 {2, 15}  // U6 IN3/IN4               Trasero Der
// OJO: GPIO1 (TX0) maneja un IN del L298N: NO uses Serial.print() en la
// ESP32-A una vez arrancado el control (usa Serial2 hacia la Pi para telemetria).

// Encoders Pololu 37D, canal A (divisor 10k/20k -> 3.3V). 16 pulsos por vuelta
// del motor por canal x 30 = 480 flancos de subida por vuelta de rueda.
// El canal B no esta cableado; el sentido se toma del comando.
#define PIN_ENC1_A 36
#define PIN_ENC2_A 39
#define PIN_ENC3_A 34
#define PIN_ENC4_A 35
#define PIN_ENC5_A 32
#define PIN_ENC6_A 33

// UART <-> Raspberry Pi (Pi UART2: GPIO4 TX / GPIO5 RX, /dev/ttyAMA2)
#define PIN_UART_RX 14
#define PIN_UART_TX 27
// Serial2.begin(115200, SERIAL_8N1, PIN_UART_RX, PIN_UART_TX);

#endif

// ===========================================================================
// ESP32-B : SERVOS + BRAZO (U3, vertical a la izquierda)
// ===========================================================================
#if defined(ROVER_ESP32_B)

#define PIN_SERVO1 23 // Direccion delantera izq
#define PIN_SERVO2 22 // Direccion delantera der
#define PIN_SERVO3 21 // Direccion trasera izq
#define PIN_SERVO4 19 // Direccion trasera der
#define PIN_SERVO5 18 // Brazo base
#define PIN_SERVO6 17 // Brazo hombro
#define PIN_SERVO7 16 // Brazo pinza
#define PIN_SERVO8 4  // Reserva

// Voltaje de bateria: divisor 100k / 27k (VBAT = Vadc * 127 / 27)
#define PIN_VBAT_SENSE 34
#define VBAT_DIVIDER_RATIO (127.0f / 27.0f)

// UART <-> Raspberry Pi (Pi UART0: GPIO14 TX / GPIO15 RX, /dev/ttyAMA0)
#define PIN_UART_RX 15
#define PIN_UART_TX 2   // GPIO2 tambien enciende el LED azul de la placa
// Serial2.begin(115200, SERIAL_8N1, PIN_UART_RX, PIN_UART_TX);

#endif

// ===========================================================================
// RASPBERRY PI 5 (numeros BCM) - /boot/firmware/config.txt:
//   dtoverlay=uart0-pi5   # GPIO14/15 -> ESP32-B  (/dev/ttyAMA0)
//   dtoverlay=uart2-pi5   # GPIO4/5   -> ESP32-A  (/dev/ttyAMA2)
//   usb_max_current_enable=1
// El resto de los GPIO quedan libres: los pines largos del stacking header
// sobresalen por arriba de la PCB y se puede conectar ahi con cables Dupont.
// ===========================================================================
