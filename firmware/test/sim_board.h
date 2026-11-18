// Modelo de la tarjeta a partir del netlist real de la PCB (board_model.h)
#pragma once
#include <map>
#include <set>
#include <string>
#include <vector>
#include <cmath>
#include <cstdlib>
#include "board_model.h"

namespace sb {
using std::string;

inline string net(const string& ref, const string& pin) {
  for (auto& n : board::NODES) if (ref == n.ref && pin == n.pin) return n.net;
  return "";
}
inline std::vector<std::pair<string, string>> on_net(const string& net) {
  std::vector<std::pair<string, string>> v;
  for (auto& n : board::NODES) if (net == n.net) v.push_back({n.ref, n.pin});
  return v;
}
inline string value(const string& ref) {
  for (auto& v : board::VALUES) if (ref == v.ref) return v.value;
  return "";
}
inline double ohms(const string& ref) {
  string v = value(ref);
  double mult = 1, x = atof(v.c_str());
  for (char c : v) { if (c == 'k') mult = 1e3; if (c == 'M') mult = 1e6; }
  return x * mult;
}
// GPIO del ESP32 (U2/U3) conectado a una red, o -1
inline int esp_gpio_on(const string& esp, const string& netname) {
  for (auto& p : board::ESP_PADS)
    if (p.gpio >= 0 && net(esp, p.pin) == netname) return p.gpio;
  return -1;
}
inline string esp_net(const string& esp, int gpio) {
  for (auto& p : board::ESP_PADS) if (p.gpio == gpio) return net(esp, p.pin);
  return "";
}
inline string pi_name(const string& pin) {
  for (auto& p : board::PI_PINS) if (pin == p.pin) return p.name;
  return "";
}
// Otra terminal de un componente de 2 pines (resistencia/diodo)
inline string other_end(const string& ref, const string& pin) {
  return net(ref, pin == "1" ? "2" : "1");
}
inline bool is_res(const string& ref) { return ref.size() > 1 && ref[0] == 'R'; }
}  // namespace sb
