// motor_logic.h - Logica de control independiente del hardware (testeable en PC)
#pragma once
#include <stdint.h>

namespace motor {

constexpr int CMD_MAX = 1000;

// Rampa de aceleracion: limita el cambio por paso para no exigir picos de
// corriente al L298N (el Pololu 37D pide hasta 5.5 A al arrancar).
inline int ramp(int current, int target, int max_step) {
  if (target > current + max_step) return current + max_step;
  if (target < current - max_step) return current - max_step;
  return target;
}

inline int clamp_cmd(long v) {
  if (v > CMD_MAX) return CMD_MAX;
  if (v < -CMD_MAX) return -CMD_MAX;
  return (int)v;
}

// Deteccion de bloqueo: PWM alto sin pulsos de encoder durante stall_ms.
class StallDetector {
 public:
  StallDetector(int min_cmd = 350, uint32_t stall_ms = 600, uint32_t min_pps = 20)
      : min_cmd_(min_cmd), stall_ms_(stall_ms), min_pps_(min_pps) {}
  // Devuelve true si el motor esta bloqueado.
  bool update(int cmd, uint32_t pps, uint32_t now_ms) {
    int a = cmd < 0 ? -cmd : cmd;
    if (a < min_cmd_ || pps >= min_pps_) {
      since_ = now_ms;
      return false;
    }
    return (now_ms - since_) >= stall_ms_;
  }
  void reset(uint32_t now_ms) { since_ = now_ms; }

 private:
  int min_cmd_;
  uint32_t stall_ms_, min_pps_;
  uint32_t since_ = 0;
};

// Salida hacia el L298N (modo "sign-magnitude" con EN fijo en HIGH):
//   v > 0 : IN_A = PWM, IN_B = 0      v < 0 : IN_A = 0, IN_B = PWM
//   v = 0 : IN_A = IN_B = 0  (freno rapido del L298N)
struct Drive {
  uint32_t duty_a;
  uint32_t duty_b;
};
inline Drive drive(int v, uint32_t duty_max) {
  uint32_t mag = (uint32_t)(v < 0 ? -v : v) * duty_max / CMD_MAX;
  if (v > 0) return {mag, 0};
  if (v < 0) return {0, mag};
  return {0, 0};
}

}  // namespace motor
