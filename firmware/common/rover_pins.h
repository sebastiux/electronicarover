// rover_pins.h - Mapa de pines de la PCB Rover Controller v1.0
// Generado a partir de hardware/tools/rover_design.py (mantener sincronizado).
#pragma once

// ===========================================================================
// ESP32-A : TRACCION (U2)
// ===========================================================================
#if defined(ROVER_ESP32_A)

// Habilitacion global de los 6 canales (ENA/ENB de los 3 L298N).
// Tiene pull-down de 10k: los motores quedan APAGADOS hasta que el firmware
// ponga este pin en HIGH. GPIO12 es pin de strapping: el pull-down garantiza
// que arranque bien; no le pongas pull-up.
#define PIN_MOTOR_EN 12

// Control por motor: PWM en un IN y el otro en LOW (ENx = HIGH via MOTOR_EN).
//   avance:  IN_A = PWM, IN_B = 0      reversa: IN_A = 0, IN_B = PWM
//   freno:   IN_A = 1,   IN_B = 1      libre:   MOTOR_EN = 0 (afecta a todos)
//                          {IN_A, IN_B}
#define PIN_M1 {32, 33} // U4 OUT1/OUT2  - Delantero Izq
#define PIN_M2 {25, 26} // U4 OUT3/OUT4  - Delantero Der
#define PIN_M3 {27, 13} // U5 OUT1/OUT2  - Medio Izq
#define PIN_M4 {23, 22} // U5 OUT3/OUT4  - Medio Der
#define PIN_M5 {21, 19} // U6 OUT1/OUT2  - Trasero Izq
#define PIN_M6 {18, 5}  // U6 OUT3/OUT4  - Trasero Der

// Encoders Pololu 37D, canal A (divisor 10k/20k -> 3.3V). 64 CPR en el motor,
// 16 pulsos/vuelta por canal x 30 = 480 flancos de subida por vuelta de rueda.
// El canal B no esta cableado (sin GPIO libres); el sentido se toma del comando.
#define PIN_ENC1_A 36
#define PIN_ENC2_A 39
#define PIN_ENC3_A 34
#define PIN_ENC4_A 35
#define PIN_ENC5_A 14
#define PIN_ENC6_A 4

// UART2 <-> Raspberry Pi (Pi UART0, GPIO14/15, /dev/ttyAMA0)
#define PIN_UART_TX 17
#define PIN_UART_RX 16

// Header auxiliar J41
#define PIN_AUX_IO2 2   // strapping: no forzar HIGH al arrancar en modo descarga
#define PIN_AUX_IO15 15

#endif

// ===========================================================================
// ESP32-B : SERVOS + BRAZO (U3)
// ===========================================================================
#if defined(ROVER_ESP32_B)

#define PIN_SERVO1 32 // Direccion delantera izq
#define PIN_SERVO2 33 // Direccion delantera der
#define PIN_SERVO3 25 // Direccion trasera izq
#define PIN_SERVO4 26 // Direccion trasera der
#define PIN_SERVO5 27 // Brazo base
#define PIN_SERVO6 13 // Brazo hombro
#define PIN_SERVO7 23 // Brazo pinza
#define PIN_SERVO8 4  // Reserva

// Voltaje de bateria: divisor 100k / 27k (VBAT = Vadc * 127 / 27)
#define PIN_VBAT_SENSE 34
#define VBAT_DIVIDER_RATIO (127.0f / 27.0f)

// UART2 <-> Raspberry Pi (Pi UART2, GPIO4/5, /dev/ttyAMA2)
#define PIN_UART_TX 17
#define PIN_UART_RX 16

// Header auxiliar J42: 3V3, GND, SDA, SCL, IO18, IO19, IO35, IO39
#define PIN_I2C_SDA 21
#define PIN_I2C_SCL 22
#define PIN_AUX_IO18 18
#define PIN_AUX_IO19 19
#define PIN_AUX_IO35 35 // solo entrada
#define PIN_AUX_IO39 39 // solo entrada

#endif

// ===========================================================================
// RASPBERRY PI 5 (numeros BCM)
// ===========================================================================
// UART0 TX/RX = GPIO14/15 -> ESP32-A     (dtoverlay=uart0-pi5)
// UART2 TX/RX = GPIO4/5   -> ESP32-B     (dtoverlay=uart2-pi5)
// GPIO17 = HIGH -> reset ESP32-A (via Q1)   GPIO27 = HIGH -> reset ESP32-B (via Q2)
// I2C1 SDA/SCL = GPIO2/3 y GPIO22..25 en el header J43
