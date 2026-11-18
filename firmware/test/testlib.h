// Utilidades comunes de las pruebas de simulacion
#pragma once
#include <cstdio>
#include <string>
#include <vector>
#include <cmath>
#include "sim_board.h"

inline int g_pass = 0, g_fail = 0;
#define CHECK(cond, ...) do { \
    if (cond) { ++g_pass; printf("  [OK]   "); } else { ++g_fail; printf("  [FALLA] "); } \
    printf(__VA_ARGS__); printf("\n"); } while (0)

inline void section(const char* s) { printf("\n== %s\n", s); }

// Ultima linea que empieza con `prefix` en lo que transmitio la ESP32 (sin *HH)
inline std::string last_line(const std::string& out, const std::string& prefix) {
  std::string best;
  size_t pos = 0;
  while (pos < out.size()) {
    size_t e = out.find('\n', pos);
    if (e == std::string::npos) break;
    std::string l = out.substr(pos, e - pos);
    if (l.rfind(prefix, 0) == 0) best = l;
    pos = e + 1;
  }
  size_t star = best.find('*');
  if (star != std::string::npos) best = best.substr(0, star);
  return best;
}
inline std::vector<long> nums(const std::string& l) {
  std::vector<long> v;
  const char* p = l.c_str();
  while (*p && *p != ' ') ++p;
  while (*p) { char* e; long x = strtol(p, &e, 10); if (e == p) break; v.push_back(x); p = e; }
  return v;
}

// Revisa la ruta UART ESP32 <-> Pi en el netlist: RX del ESP32 debe llegar (via
// resistencia serie) a un TXD de la Pi y TX a un RXD del mismo UART.
inline void check_uart_path(const char* esp, int rx, int tx) {
  auto follow = [&](int gpio, std::string& via) -> std::string {
    std::string n = sb::esp_net(esp, gpio);
    for (auto& rp : sb::on_net(n)) {
      if (!sb::is_res(rp.first)) continue;
      std::string o = sb::other_end(rp.first, rp.second);
      for (auto& q : sb::on_net(o))
        if (q.first == "U1") { via = rp.first + " (" + sb::value(rp.first) + ")"; return sb::pi_name(q.second) + " [pin " + q.second + "]"; }
    }
    return "";
  };
  std::string v1, v2;
  std::string a = follow(rx, v1), b = follow(tx, v2);
  CHECK(a.find("TXD") != std::string::npos, "%s RX=GPIO%d <- %s <- Pi %s", esp, rx, v1.c_str(), a.c_str());
  CHECK(b.find("RXD") != std::string::npos, "%s TX=GPIO%d -> %s -> Pi %s", esp, tx, v2.c_str(), b.c_str());
  CHECK(!a.empty() && !b.empty() && a.substr(a.find("XD"), 3) == b.substr(b.find("XD"), 3),
        "RX y TX usan el mismo UART de la Pi");
}

// Pines de arranque (strapping) del ESP32: ninguno debe quedar forzado por la PCB
inline void check_strapping(const char* esp) {
  struct S { int g; const char* rule; };
  const S straps[] = {{2, "debe quedar en LOW/flotante para grabar por USB"},
                      {5, "pull-up interno; no forzar LOW"},
                      {12, "debe quedar en LOW al arrancar (si no: flash a 1.8 V y no arranca)"},
                      {15, "solo cambia el log de arranque"}};
  for (auto& s : straps) {
    std::string n = sb::esp_net(esp, s.g);
    std::string desc = n.empty() ? "sin conectar" : n;
    bool forced_high = false;
    for (auto& rp : sb::on_net(n)) {
      if (sb::is_res(rp.first)) {
        std::string o = sb::other_end(rp.first, rp.second);
        if (o.find("3V3") != std::string::npos || o == "+5V") forced_high = true;
      }
    }
    // destinos de alta impedancia (entradas del L298N, servos, UART con 1k a la Pi)
    CHECK(!forced_high, "%s GPIO%-2d -> %-10s (%s)", esp, s.g, desc.c_str(), s.rule);
  }
}
