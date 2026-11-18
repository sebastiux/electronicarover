// rover_protocol.h - Protocolo de texto Pi <-> ESP32 (una linea por mensaje)
//
//   <CMD> [arg1 arg2 ...][*HH]\n
//
// HH (opcional) = XOR en hexadecimal de todos los caracteres antes de '*'
// (estilo NMEA). Si viene, se valida; si no coincide, la linea se descarta.
//
// ESP32-A (traccion)                     ESP32-B (servos)
//   EN 0|1        habilitar motores        S n us        servo n (1..8) en us
//   M p1..p6      -1000..1000 por motor    A n grados    servo n en grados 0..180
//   STOP          rampa a 0 y deshabilita  ?             pedir estado
//   ?             pedir estado
// Respuestas / telemetria:
//   T c1..c6 v1..v6 f   cuentas y pulsos/s (signo = sentido) y banderas
//   B mv f              bateria en mV y banderas (ESP32-B)
//   ERR <texto>
#pragma once
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

namespace proto {

constexpr size_t MAX_LINE = 96;
constexpr int MAX_ARGS = 8;

struct Message {
  char cmd[8];
  int nargs;
  long args[MAX_ARGS];
};

inline uint8_t checksum(const char* s, size_t n) {
  uint8_t c = 0;
  for (size_t i = 0; i < n; ++i) c ^= (uint8_t)s[i];
  return c;
}

// Parsea una linea (sin '\n'). Devuelve false si esta mal formada o el
// checksum no coincide.
inline bool parse(const char* line, Message& m) {
  char buf[MAX_LINE + 1];
  size_t n = strnlen(line, MAX_LINE);
  if (n == 0 || n >= MAX_LINE) return false;
  memcpy(buf, line, n);
  buf[n] = 0;
  while (n && (buf[n - 1] == '\r' || buf[n - 1] == ' ')) buf[--n] = 0;
  char* star = strchr(buf, '*');
  if (star) {
    char* end = nullptr;
    long want = strtol(star + 1, &end, 16);
    if (end == star + 1 || *end != 0) return false;
    if ((uint8_t)want != checksum(buf, (size_t)(star - buf))) return false;
    *star = 0;
  }
  m.nargs = 0;
  m.cmd[0] = 0;
  char* save = nullptr;
  char* tok = strtok_r(buf, " ", &save);
  if (!tok || strlen(tok) >= sizeof(m.cmd)) return false;
  strcpy(m.cmd, tok);
  while ((tok = strtok_r(nullptr, " ", &save)) != nullptr) {
    if (m.nargs >= MAX_ARGS) return false;
    char* end = nullptr;
    long v = strtol(tok, &end, 10);
    if (end == tok || *end != 0) return false;
    m.args[m.nargs++] = v;
  }
  return true;
}

// Agrega "*HH\n" a un mensaje ya escrito en buf (len = longitud actual).
inline size_t finish(char* buf, size_t len, size_t cap) {
  uint8_t c = checksum(buf, len);
  int k = snprintf(buf + len, cap - len, "*%02X\n", c);
  return len + (k > 0 ? (size_t)k : 0);
}

// Acumula caracteres y entrega lineas completas.
class LineReader {
 public:
  // Devuelve true cuando hay una linea completa en line().
  bool feed(char ch) {
    if (ch == '\n') {
      buf_[len_] = 0;
      bool ok = !overflow_ && len_ > 0;
      len_ = 0;
      overflow_ = false;
      return ok;
    }
    if (len_ < MAX_LINE) buf_[len_++] = ch;
    else overflow_ = true;
    return false;
  }
  const char* line() const { return buf_; }

 private:
  char buf_[MAX_LINE + 1] = {0};
  size_t len_ = 0;
  bool overflow_ = false;
};

}  // namespace proto
