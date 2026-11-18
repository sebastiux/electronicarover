// Simulacion firmware ESP32-A (traccion) sobre el netlist real de la PCB.
#include "Arduino.h"
#include "../traction/src/main.cpp"
#include "testlib.h"

static const char* ESP = "U2";

static void run_ms(int ms, int heartbeat_every = 0, const std::string& hb = "") {
  for (int t = 0; t < ms; ++t) {
    ++sim::now_ms;
    if (heartbeat_every && t % heartbeat_every == 0) Serial2.inject(hb);
    loop();
  }
}
// valor (0..1) que la ESP32 pone en la red: PWM o nivel digital
static double esp_drive(const std::string& netname, bool& known) {
  int g = sb::esp_gpio_on(ESP, netname);
  known = g >= 0;
  if (!known) return 0;
  auto& p = sim::pins[g];
  if (p.pwm) return p.duty / double((1u << p.bits) - 1);
  return p.level;
}
// Modelo L298N: OUTn = VS * IN (si EN = 1); si EN = 0 la salida queda abierta
static bool l298_out(const std::string& u, const std::string& out, double& v) {
  int o = atoi(out.c_str());
  std::string in = std::to_string(8 + o), en = (o <= 2) ? "8" : "13";
  bool k1, k2;
  double e = esp_drive(sb::net(u, en), k1), i = esp_drive(sb::net(u, in), k2);
  if (!k1 || !k2) return false;
  if (e < 0.5) return false;   // alta impedancia
  v = i;
  return true;
}
static double net_voltage(const std::string& netname, bool& driven) {
  driven = false;
  for (auto& rp : sb::on_net(netname)) {
    if (rp.first[0] == 'U' && atoi(rp.second.c_str()) >= 1 && atoi(rp.second.c_str()) <= 4) {
      double v;
      if (l298_out(rp.first, rp.second, v)) { driven = true; return v; }
    }
  }
  return 0;
}
// Voltaje (fraccion de VBAT) entre M+ (pin 1, rojo) y M- (pin 2, negro) del header Pololu
static double motor_v(int m) {
  std::string j = "J" + std::to_string(20 + m);
  bool d1, d2;
  double a = net_voltage(sb::net(j, "1"), d1), b = net_voltage(sb::net(j, "2"), d2);
  return (d1 && d2) ? a - b : 0.0;
}
static int enc_gpio_of_motor(int m, double& vhigh, std::string& path) {
  std::string j = "J" + std::to_string(20 + m);
  std::string n5 = sb::net(j, "5");
  for (auto& rp : sb::on_net(n5)) {
    if (!sb::is_res(rp.first)) continue;
    std::string node = sb::other_end(rp.first, rp.second);
    double rt = sb::ohms(rp.first), rb = 0;
    std::string rbname, cap;
    for (auto& q : sb::on_net(node)) {
      if (sb::is_res(q.first) && q.first != rp.first && sb::other_end(q.first, q.second) == "GND") { rb = sb::ohms(q.first); rbname = q.first; }
      if (q.first[0] == 'C' && sb::other_end(q.first, q.second) == "GND") cap = q.first + " " + sb::value(q.first);
    }
    vhigh = rb > 0 ? 5.0 * rb / (rt + rb) : 5.0;
    path = rp.first + "(" + sb::value(rp.first) + ") / " + rbname + "(" + sb::value(rbname) + ") / " + cap;
    return sb::esp_gpio_on(ESP, node);
  }
  return -1;
}

int main() {
  printf("Simulacion ESP32-A (traccion) sobre el netlist de rover_controller.kicad_pcb\n");
  setup();

  section("Arranque seguro");
  std::string en_net = sb::esp_net(ESP, PIN_MOTOR_EN);
  int en_targets = 0; bool pulldown = false;
  for (auto& rp : sb::on_net(en_net)) {
    bool l298 = rp.first == "U4" || rp.first == "U5" || rp.first == "U6";
    if (l298 && (rp.second == "8" || rp.second == "13")) ++en_targets;
    if (sb::is_res(rp.first) && sb::other_end(rp.first, rp.second) == "GND") pulldown = true;
  }
  CHECK(sim::pins[PIN_MOTOR_EN].level == 0, "MOTOR_EN (GPIO%d) en LOW despues de setup()", PIN_MOTOR_EN);
  CHECK(en_targets == 6, "MOTOR_EN llega a los 6 ENA/ENB de los L298N (%d)", en_targets);
  CHECK(pulldown, "MOTOR_EN tiene pull-down a GND en la PCB (motores apagados al encender)");
  bool all_zero = true;
  for (int m = 1; m <= 6; ++m) all_zero &= std::fabs(motor_v(m)) < 1e-9;
  CHECK(all_zero, "ningun motor recibe voltaje al arrancar");

  section("UART con la Raspberry Pi");
  check_uart_path(ESP, Serial2.rx_pin, Serial2.tx_pin);

  section("Encoders: conector Pololu -> divisor -> GPIO");
  int enc_gpio[7];
  for (int m = 1; m <= 6; ++m) {
    double vh; std::string path;
    enc_gpio[m] = enc_gpio_of_motor(m, vh, path);
    bool fw = enc_gpio[m] == ENC_PINS[m - 1];
    CHECK(fw && vh > 2.475 && vh < 3.6, "M%d: header J%d pin5 -> %s -> GPIO%d (firmware ENC%d=GPIO%d), nivel alto %.2f V",
          m, 20 + m, path.c_str(), enc_gpio[m], m, ENC_PINS[m - 1], vh);
    CHECK((sim::pins[enc_gpio[m]].isr != nullptr || sim::pins[enc_gpio[m]].isr_arg != nullptr) && sim::pins[enc_gpio[m]].isr_mode == RISING,
          "M%d: interrupcion RISING configurada en GPIO%d", m, enc_gpio[m]);
  }

  section("Cada comando de motor mueve el motor correcto, con la polaridad correcta");
  for (int m = 1; m <= 6; ++m) {
    for (int sign : {+1, -1}) {
      long cmd[6] = {0, 0, 0, 0, 0, 0};
      cmd[m - 1] = 700 * sign;
      char buf[64];
      snprintf(buf, sizeof buf, "M %ld %ld %ld %ld %ld %ld\n", cmd[0], cmd[1], cmd[2], cmd[3], cmd[4], cmd[5]);
      Serial2.inject("EN 1\n");
      // 1 s con latido cada 100 ms y pulsos de encoder (200 pps) en el motor movido
      for (int t = 0; t < 1000; ++t) {
        ++sim::now_ms;
        if (t % 100 == 0) Serial2.inject(buf);
        if (t % 5 == 0) sim::pins[enc_gpio[m]].fire();
        loop();
      }
      double v[7];
      bool others_off = true;
      for (int k = 1; k <= 6; ++k) { v[k] = motor_v(k); if (k != m && std::fabs(v[k]) > 1e-6) others_off = false; }
      CHECK(std::fabs(v[m] - 0.7 * sign) < 0.01 && others_off,
            "M %+d en motor %d -> conector M%d (J%d/J%d) recibe %+.2f x VBAT en M+ (rojo); los demas 0",
            700 * sign, m, m, 10 + m, 20 + m, v[m]);
      Serial2.inject("STOP\n");
      run_ms(500, 100, "STOP\n");
    }
  }

  section("Telemetria de encoders (cuenta en el motor correcto)");
  Serial2.inject("EN 1\n");
  run_ms(10);
  long before[6];
  {
    Serial2.out.clear(); Serial2.inject("?\n"); run_ms(2);
    auto v = nums(last_line(Serial2.out, "T"));
    for (int i = 0; i < 6; ++i) before[i] = v.size() > (size_t)i ? v[i] : 0;
  }
  for (int m = 1; m <= 6; ++m) {
    for (int k = 0; k < 50; ++k) { ++sim::now_ms; sim::pins[enc_gpio[m]].fire(); if (k % 10 == 0) Serial2.inject("M 0 0 0 0 0 0\n"); loop(); }
    run_ms(20);
  }
  Serial2.out.clear(); Serial2.inject("?\n"); run_ms(2);
  auto tv = nums(last_line(Serial2.out, "T"));
  for (int m = 1; m <= 6; ++m)
    CHECK(tv.size() >= 13 && tv[m - 1] - before[m - 1] == 50, "50 pulsos en el encoder de M%d -> telemetria cuenta %ld en la posicion %d",
          m, tv.size() >= 13 ? tv[m - 1] - before[m - 1] : -1, m);

  section("Seguridad");
  Serial2.inject("EN 1\nM 800 0 0 0 0 0\n");
  run_ms(50);
  run_ms(400);   // sin latidos
  CHECK(sim::pins[PIN_MOTOR_EN].level == 0 && std::fabs(motor_v(1)) < 1e-9,
        "watchdog: sin comandos de la Pi por >300 ms -> MOTOR_EN=LOW y motores en 0");
  Serial2.out.clear();
  Serial2.inject("EN 1\n");
  for (int t = 0; t < 1200; ++t) { ++sim::now_ms; if (t % 100 == 0) Serial2.inject("M 800 0 0 0 0 0\n"); loop(); }
  auto st = nums(last_line(Serial2.out, "T"));
  CHECK(st.size() >= 13 && (st[12] & 1) && std::fabs(motor_v(1)) < 1e-9,
        "bloqueo: PWM 800 sin pulsos de encoder -> motor 1 cortado (banderas=0x%lX)", st.size() >= 13 ? st[12] : -1);
  Serial2.out.clear();
  Serial2.inject("M 100 0 0 0 0 0*00\n");
  run_ms(2);
  CHECK(Serial2.out.find("ERR parse") != std::string::npos, "linea con checksum incorrecto se rechaza");
  // checksum correcto
  const char* ok_cmd = "EN 0";
  char ck[32]; snprintf(ck, sizeof ck, "%s*%02X\n", ok_cmd, proto::checksum(ok_cmd, strlen(ok_cmd)));
  Serial2.out.clear(); Serial2.inject(ck); run_ms(2);
  CHECK(Serial2.out.find("ERR") == std::string::npos && sim::pins[PIN_MOTOR_EN].level == 0, "linea con checksum correcto se acepta");

  section("Restricciones del ESP32");
  check_strapping(ESP);
  int pwm_count = 0; bool freq_ok = true;
  for (auto& p : sim::pins) if (p.pwm) { ++pwm_count; freq_ok &= p.freq <= 25000; }
  CHECK(pwm_count == 12, "12 canales PWM (LEDC tiene 16)");
  CHECK(freq_ok, "frecuencia de PWM <= 25 kHz (limite practico del L298N)");
  CHECK(sim::errors.empty(), "sin usos ilegales de GPIO en el firmware (%zu)", sim::errors.size());
  for (auto& e : sim::errors) printf("         - %s\n", e.c_str());

  // lineas reales del firmware para probar el script de la Pi
  Serial2.out.clear();
  Serial2.inject("EN 1\n?\nXYZ\n");
  run_ms(120, 50, "M 100 -100 0 0 0 0\n");
  if (FILE* f = fopen("/tmp/rover_sample_tx.txt", "w")) { fputs(Serial2.out.c_str(), f); fclose(f); }
  printf("\nRESULTADO ESP32-A: %d OK, %d FALLAS\n", g_pass, g_fail);
  return g_fail ? 1 : 0;
}
