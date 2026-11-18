// ESP32-A - TRACCION (Rover Controller v1.1)
// 6 motores Pololu 37D via 3x L298N, 6 encoders (canal A), enlace UART con la Pi.
//
// Seguridad:
//  - MOTOR_EN (con pull-down en la PCB) arranca en LOW: nada se mueve hasta "EN 1".
//  - Watchdog: si la Pi no manda comandos en WATCHDOG_MS, rampa a 0 y MOTOR_EN = LOW.
//  - Rampas de aceleracion y corte por bloqueo (encoder sin pulsos con PWM alto).
//  - NO usar Serial (UART0): GPIO1/TX0 maneja IN3 del L298N U4.
#include <Arduino.h>
#define ROVER_ESP32_A
#include "rover_pins.h"
#include "rover_protocol.h"
#include "motor_logic.h"
#include "pwm_compat.h"

namespace cfg {
constexpr uint32_t PWM_FREQ = 10000;      // L298N: hasta ~25 kHz; 10 kHz es buen compromiso
constexpr uint8_t PWM_BITS = 10;
constexpr uint32_t DUTY_MAX = (1u << PWM_BITS) - 1;
constexpr uint32_t CONTROL_MS = 10;
constexpr uint32_t TELEMETRY_MS = 50;
constexpr uint32_t WATCHDOG_MS = 300;
constexpr int RAMP_STEP = 25;             // 0 -> 1000 en 400 ms
constexpr uint32_t ENC_MIN_US = 60;       // filtro de glitches (senal real >= 370 us)
constexpr uint32_t BAUD = 115200;
}

static const uint8_t MOTOR_PINS[6][2] = {PIN_M1, PIN_M2, PIN_M3, PIN_M4, PIN_M5, PIN_M6};
static const uint8_t ENC_PINS[6] = {PIN_ENC1_A, PIN_ENC2_A, PIN_ENC3_A,
                                    PIN_ENC4_A, PIN_ENC5_A, PIN_ENC6_A};

static volatile uint32_t enc_pulses[6];
static volatile uint32_t enc_last_us[6];

// Una sola rutina de interrupcion con argumento (indice del encoder).
// (Las plantillas con IRAM_ATTR dan "dangerous relocation" en el enlazador Xtensa.)
static void IRAM_ATTR enc_isr(void* arg) {
  int i = (int)(intptr_t)arg;
  uint32_t t = micros();
  if (t - enc_last_us[i] >= cfg::ENC_MIN_US) {
    enc_last_us[i] = t;
    enc_pulses[i] = enc_pulses[i] + 1;
  }
}

static int target[6], output[6];
static int32_t position[6];        // cuentas con signo (sentido = sentido aplicado)
static uint32_t last_pulses[6], pps[6];
static uint8_t stalled_mask;
static bool enabled;
static uint32_t last_cmd_ms, last_ctrl_ms, last_tlm_ms;
static motor::StallDetector stall[6];
static proto::LineReader reader;

static void apply_outputs() {
  for (int i = 0; i < 6; ++i) {
    motor::Drive d = motor::drive(enabled ? output[i] : 0, cfg::DUTY_MAX);
    pwm_write(MOTOR_PINS[i][0], 2 * i, d.duty_a);
    pwm_write(MOTOR_PINS[i][1], 2 * i + 1, d.duty_b);
  }
  digitalWrite(PIN_MOTOR_EN, enabled ? HIGH : LOW);
}

static void send(const char* fmt_line) {
  char buf[proto::MAX_LINE + 8];
  size_t n = strnlen(fmt_line, proto::MAX_LINE);
  memcpy(buf, fmt_line, n);
  n = proto::finish(buf, n, sizeof(buf));
  Serial2.write((const uint8_t*)buf, n);
}

static void send_telemetry() {
  char line[proto::MAX_LINE];
  int k = snprintf(line, sizeof(line), "T");
  for (int i = 0; i < 6; ++i) k += snprintf(line + k, sizeof(line) - k, " %ld", (long)position[i]);
  for (int i = 0; i < 6; ++i) {
    long v = output[i] < 0 ? -(long)pps[i] : (long)pps[i];
    k += snprintf(line + k, sizeof(line) - k, " %ld", v);
  }
  snprintf(line + k, sizeof(line) - k, " %u", (unsigned)(stalled_mask | (enabled ? 0x80 : 0)));
  send(line);
}

static void disable_all() {
  enabled = false;
  for (int i = 0; i < 6; ++i) target[i] = output[i] = 0;
  apply_outputs();
}

static void handle(const proto::Message& m, uint32_t now) {
  last_cmd_ms = now;
  if (!strcmp(m.cmd, "EN") && m.nargs == 1) {
    if (m.args[0]) {
      stalled_mask = 0;
      for (int i = 0; i < 6; ++i) stall[i].reset(now);
      enabled = true;
    } else {
      disable_all();
    }
  } else if (!strcmp(m.cmd, "M") && m.nargs == 6) {
    for (int i = 0; i < 6; ++i) target[i] = motor::clamp_cmd(m.args[i]);
  } else if (!strcmp(m.cmd, "STOP")) {
    for (int i = 0; i < 6; ++i) target[i] = 0;
  } else if (!strcmp(m.cmd, "?")) {
    send_telemetry();
  } else {
    send("ERR cmd");
  }
}

void setup() {
  // Primero todo apagado: MOTOR_EN en LOW (la PCB ademas tiene pull-down de 10k)
  pinMode(PIN_MOTOR_EN, OUTPUT);
  digitalWrite(PIN_MOTOR_EN, LOW);
  for (int i = 0; i < 6; ++i) {
    pwm_attach(MOTOR_PINS[i][0], 2 * i, cfg::PWM_FREQ, cfg::PWM_BITS);
    pwm_attach(MOTOR_PINS[i][1], 2 * i + 1, cfg::PWM_FREQ, cfg::PWM_BITS);
    pinMode(ENC_PINS[i], INPUT);   // 34..39 no tienen pull-up; el divisor fija el nivel
    attachInterruptArg(digitalPinToInterrupt(ENC_PINS[i]), enc_isr, (void*)(intptr_t)i, RISING);
  }
  apply_outputs();
  Serial2.begin(cfg::BAUD, SERIAL_8N1, PIN_UART_RX, PIN_UART_TX);
  last_cmd_ms = last_ctrl_ms = last_tlm_ms = millis();
}

void loop() {
  uint32_t now = millis();
  while (Serial2.available()) {
    if (reader.feed((char)Serial2.read())) {
      proto::Message m;
      if (proto::parse(reader.line(), m)) handle(m, now);
      else send("ERR parse");
    }
  }
  if (enabled && now - last_cmd_ms > cfg::WATCHDOG_MS) {
    disable_all();             // la Pi dejo de hablar: todo a cero
  }
  if (now - last_ctrl_ms >= cfg::CONTROL_MS) {
    uint32_t dt = now - last_ctrl_ms;
    last_ctrl_ms = now;
    for (int i = 0; i < 6; ++i) {
      noInterrupts();
      uint32_t p = enc_pulses[i];
      interrupts();
      uint32_t d = p - last_pulses[i];
      last_pulses[i] = p;
      position[i] += (output[i] < 0) ? -(int32_t)d : (int32_t)d;
      pps[i] = d * 1000u / (dt ? dt : 1);
      int t = (stalled_mask & (1 << i)) ? 0 : target[i];
      output[i] = motor::ramp(output[i], t, cfg::RAMP_STEP);
      if (enabled && stall[i].update(output[i], pps[i], now)) {
        stalled_mask |= (1 << i);
        output[i] = 0;
      }
    }
    apply_outputs();
  }
  if (now - last_tlm_ms >= cfg::TELEMETRY_MS) {
    last_tlm_ms = now;
    send_telemetry();
  }
}
