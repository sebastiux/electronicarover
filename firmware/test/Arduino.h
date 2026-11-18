// Arduino.h SIMULADO para pruebas en PC (subconjunto de Arduino-ESP32 3.x).
// Registra el estado de cada GPIO y marca como error los usos ilegales del ESP32.
#pragma once
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <stdio.h>
#include <string>
#include <deque>
#include <vector>

#define ESP_ARDUINO_VERSION_MAJOR 3
#define IRAM_ATTR
#define HIGH 1
#define LOW 0
#define INPUT 0x01
#define OUTPUT 0x03
#define INPUT_PULLUP 0x05
#define RISING 0x01
#define FALLING 0x02
#define CHANGE 0x03
#define SERIAL_8N1 0x800001c
#define ADC_11db 3

namespace sim {
struct Pin {
  int mode = -1;          // -1 sin configurar
  int level = 0;
  bool pwm = false;
  uint32_t freq = 0, bits = 0, duty = 0;
  void (*isr)() = nullptr;
  void (*isr_arg)(void*) = nullptr;
  void* arg = nullptr;
  int isr_mode = 0;
  void fire() { if (isr) isr(); if (isr_arg) isr_arg(arg); }
  uint32_t adc_mv = 0;
};
inline Pin pins[40];
inline uint32_t now_ms = 0, now_us_extra = 0;
inline std::vector<std::string> errors;
inline void error(const std::string& e) { errors.push_back(e); }
// Pines del ESP32-WROOM-32 expuestos en el DevKit V1 de 30 pines
inline bool exposed(int p) {
  static const int ok[] = {1, 2, 3, 4, 5, 12, 13, 14, 15, 16, 17, 18, 19, 21, 22, 23,
                           25, 26, 27, 32, 33, 34, 35, 36, 39};
  for (int v : ok) if (v == p) return true;
  return false;
}
inline bool input_only(int p) { return p >= 34 && p <= 39; }
inline void check_pin(int p, const char* what) {
  if (p < 0 || p >= 40 || !exposed(p)) error(std::string(what) + ": GPIO" + std::to_string(p) + " no existe en el DevKit de 30 pines");
}
}  // namespace sim

inline uint32_t millis() { return sim::now_ms; }
inline uint32_t micros() { return sim::now_ms * 1000u + sim::now_us_extra; }
inline void delay(uint32_t ms) { sim::now_ms += ms; }
inline void noInterrupts() {}
inline void interrupts() {}
inline int digitalPinToInterrupt(int p) { return p; }

inline void pinMode(uint8_t p, uint8_t m) {
  sim::check_pin(p, "pinMode");
  if (m == OUTPUT && sim::input_only(p)) sim::error("GPIO" + std::to_string(p) + " es solo de entrada y se configuro como OUTPUT");
  if (m == INPUT_PULLUP && sim::input_only(p)) sim::error("GPIO" + std::to_string(p) + " no tiene pull-up interno");
  sim::pins[p].mode = m;
}
inline void digitalWrite(uint8_t p, uint8_t v) {
  sim::check_pin(p, "digitalWrite");
  if (sim::pins[p].mode != OUTPUT) sim::error("digitalWrite en GPIO" + std::to_string(p) + " sin pinMode(OUTPUT)");
  sim::pins[p].level = v ? 1 : 0;
}
inline int digitalRead(uint8_t p) { return sim::pins[p].level; }
inline void attachInterrupt(int p, void (*f)(), int mode) {
  sim::check_pin(p, "attachInterrupt");
  sim::pins[p].isr = f;
  sim::pins[p].isr_mode = mode;
}
inline void attachInterruptArg(int p, void (*f)(void*), void* arg, int mode) {
  sim::check_pin(p, "attachInterruptArg");
  sim::pins[p].isr_arg = f;
  sim::pins[p].arg = arg;
  sim::pins[p].isr_mode = mode;
}
inline bool ledcAttach(uint8_t p, uint32_t freq, uint8_t bits) {
  sim::check_pin(p, "ledcAttach");
  if (sim::input_only(p)) sim::error("PWM en GPIO" + std::to_string(p) + " (solo entrada)");
  int used = 0;
  for (auto& q : sim::pins) used += q.pwm;
  if (used >= 16) sim::error("mas de 16 canales LEDC");
  sim::pins[p].pwm = true;
  sim::pins[p].freq = freq;
  sim::pins[p].bits = bits;
  sim::pins[p].mode = OUTPUT;
  return true;
}
inline bool ledcWrite(uint8_t p, uint32_t duty) {
  if (!sim::pins[p].pwm) sim::error("ledcWrite en GPIO" + std::to_string(p) + " sin ledcAttach");
  sim::pins[p].duty = duty;
  return true;
}
inline uint32_t analogReadMilliVolts(uint8_t p) {
  if (!(p >= 32 && p <= 39)) sim::error("ADC en GPIO" + std::to_string(p) + " no es ADC1 (ADC2 no funciona con WiFi)");
  return sim::pins[p].adc_mv;
}
inline void analogSetPinAttenuation(uint8_t, int) {}

class HardwareSerial {
 public:
  void begin(uint32_t baud, uint32_t, int8_t rx, int8_t tx) {
    baud_ = baud; rx_pin = rx; tx_pin = tx;
    sim::check_pin(rx, "UART RX");
    sim::check_pin(tx, "UART TX");
    if (sim::input_only(tx)) sim::error("UART TX en GPIO solo de entrada");
  }
  int available() { return (int)in.size(); }
  int read() { if (in.empty()) return -1; int c = in.front(); in.pop_front(); return c; }
  size_t write(const uint8_t* b, size_t n) { out.append((const char*)b, n); return n; }
  // lado "Raspberry Pi" de la simulacion
  void inject(const std::string& s) { for (char c : s) in.push_back(c); }
  int rx_pin = -1, tx_pin = -1;
  uint32_t baud_ = 0;
  std::deque<char> in;
  std::string out;
};
inline HardwareSerial Serial2;
