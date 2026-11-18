// ESP32-B - SERVOS + BRAZO + BATERIA (Rover Controller v1.1)
// 8 servos Power HD 1501MG (50 Hz), voltaje de bateria por ADC1, UART con la Pi.
#include <Arduino.h>
#define ROVER_ESP32_B
#include "rover_pins.h"
#include "rover_protocol.h"
#include "pwm_compat.h"

namespace cfg {
constexpr uint32_t SERVO_FREQ = 50;
constexpr uint8_t SERVO_BITS = 16;
constexpr uint32_t PERIOD_US = 1000000 / SERVO_FREQ;
constexpr uint32_t US_MIN = 800, US_MAX = 2200, US_CENTER = 1500;  // 1501MG
constexpr uint32_t BAT_MS = 200;
constexpr uint32_t BAUD = 115200;
constexpr uint32_t VBAT_LOW_MV = 9900;     // 3S LiPo: 3.3 V por celda
}

static const uint8_t SERVO_PINS[8] = {PIN_SERVO1, PIN_SERVO2, PIN_SERVO3, PIN_SERVO4,
                                      PIN_SERVO5, PIN_SERVO6, PIN_SERVO7, PIN_SERVO8};
static uint32_t servo_us[8];
static uint32_t last_bat_ms;
static proto::LineReader reader;

static uint32_t us_to_duty(uint32_t us) {
  return (uint32_t)((uint64_t)us * ((1u << cfg::SERVO_BITS) - 1) / cfg::PERIOD_US);
}

static void set_servo(int i, long us) {
  if (us < (long)cfg::US_MIN) us = cfg::US_MIN;
  if (us > (long)cfg::US_MAX) us = cfg::US_MAX;
  servo_us[i] = (uint32_t)us;
  pwm_write(SERVO_PINS[i], i, us_to_duty(servo_us[i]));
}

static void send(const char* line) {
  char buf[proto::MAX_LINE + 8];
  size_t n = strnlen(line, proto::MAX_LINE);
  memcpy(buf, line, n);
  n = proto::finish(buf, n, sizeof(buf));
  Serial2.write((const uint8_t*)buf, n);
}

static uint32_t read_vbat_mv() {
  uint32_t acc = 0;
  for (int k = 0; k < 8; ++k) acc += analogReadMilliVolts(PIN_VBAT_SENSE);
  return (uint32_t)((acc / 8) * VBAT_DIVIDER_RATIO);
}

static void send_status() {
  char line[proto::MAX_LINE];
  uint32_t mv = read_vbat_mv();
  snprintf(line, sizeof(line), "B %lu %u", (unsigned long)mv, mv < cfg::VBAT_LOW_MV ? 1u : 0u);
  send(line);
}

static void handle(const proto::Message& m) {
  if (!strcmp(m.cmd, "S") && m.nargs == 2 && m.args[0] >= 1 && m.args[0] <= 8) {
    set_servo((int)m.args[0] - 1, m.args[1]);
  } else if (!strcmp(m.cmd, "A") && m.nargs == 2 && m.args[0] >= 1 && m.args[0] <= 8) {
    long deg = m.args[1] < 0 ? 0 : (m.args[1] > 180 ? 180 : m.args[1]);
    set_servo((int)m.args[0] - 1, cfg::US_MIN + deg * (long)(cfg::US_MAX - cfg::US_MIN) / 180);
  } else if (!strcmp(m.cmd, "?")) {
    send_status();
  } else {
    send("ERR cmd");
  }
}

void setup() {
  for (int i = 0; i < 8; ++i) {
    pwm_attach(SERVO_PINS[i], i, cfg::SERVO_FREQ, cfg::SERVO_BITS);
    set_servo(i, cfg::US_CENTER);
  }
  analogSetPinAttenuation(PIN_VBAT_SENSE, ADC_11db);
  Serial2.begin(cfg::BAUD, SERIAL_8N1, PIN_UART_RX, PIN_UART_TX);
  last_bat_ms = millis();
}

void loop() {
  while (Serial2.available()) {
    if (reader.feed((char)Serial2.read())) {
      proto::Message m;
      if (proto::parse(reader.line(), m)) handle(m);
      else send("ERR parse");
    }
  }
  uint32_t now = millis();
  if (now - last_bat_ms >= cfg::BAT_MS) {
    last_bat_ms = now;
    send_status();
  }
}
