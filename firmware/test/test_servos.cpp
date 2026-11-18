// Simulacion firmware ESP32-B (servos + bateria) sobre el netlist real de la PCB.
#include "Arduino.h"
#include "../servos/src/main.cpp"
#include "testlib.h"

static const char* ESP = "U3";
static void run_ms(int ms) { for (int t = 0; t < ms; ++t) { ++sim::now_ms; loop(); } }
static double pulse_us(int gpio) {
  auto& p = sim::pins[gpio];
  return p.pwm ? p.duty * (1e6 / p.freq) / ((1u << p.bits) - 1) : 0;
}

int main() {
  printf("Simulacion ESP32-B (servos) sobre el netlist de rover_controller.kicad_pcb\n");
  setup();

  section("UART con la Raspberry Pi");
  check_uart_path(ESP, Serial2.rx_pin, Serial2.tx_pin);

  section("Servos: GPIO -> header (GND, V+, SIG)");
  for (int n = 1; n <= 8; ++n) {
    int g = SERVO_PINS[n - 1];
    std::string net = sb::esp_net(ESP, g), hdr;
    for (auto& rp : sb::on_net(net)) if (rp.first[0] == 'J' && rp.second == "3") hdr = rp.first;
    bool pinout = !hdr.empty() && sb::net(hdr, "1") == "GND" && sb::net(hdr, "2") == "SERVO_V";
    CHECK(pinout && sb::value(hdr) == "SERVO" + std::to_string(n),
          "S%d: GPIO%d -> %s -> %s pin3 (SIG); pin1=%s pin2=%s", n, g, net.c_str(), hdr.c_str(),
          sb::net(hdr, "1").c_str(), sb::net(hdr, "2").c_str());
    CHECK(std::fabs(pulse_us(g) - 1500) < 2 && sim::pins[g].freq == 50, "S%d: arranca centrado (%.0f us @ %u Hz)", n, pulse_us(g), sim::pins[g].freq);
    Serial2.inject("A " + std::to_string(n) + " 0\n"); run_ms(2);
    double a0 = pulse_us(g);
    Serial2.inject("A " + std::to_string(n) + " 180\n"); run_ms(2);
    double a180 = pulse_us(g);
    Serial2.inject("S " + std::to_string(n) + " 5000\n"); run_ms(2);
    double lim = pulse_us(g);
    CHECK(std::fabs(a0 - 800) < 2 && std::fabs(a180 - 2200) < 2 && std::fabs(lim - 2200) < 2,
          "S%d: 0 grados=%.0f us, 180 grados=%.0f us, 5000 us se limita a %.0f us", n, a0, a180, lim);
  }

  section("Voltaje de bateria (XT60 -> fusible -> divisor -> ADC)");
  std::string sense = sb::esp_net(ESP, PIN_VBAT_SENSE);
  double rtop = 0, rbot = 0; std::string rt, rb;
  for (auto& rp : sb::on_net(sense)) {
    if (!sb::is_res(rp.first)) continue;
    std::string o = sb::other_end(rp.first, rp.second);
    if (o == "VBAT_F") { rtop = sb::ohms(rp.first); rt = rp.first; }
    if (o == "GND") { rbot = sb::ohms(rp.first); rb = rp.first; }
  }
  CHECK(rtop > 0 && rbot > 0, "GPIO%d -> %s: %s(%s) a VBAT_F y %s(%s) a GND", PIN_VBAT_SENSE, sense.c_str(),
        rt.c_str(), sb::value(rt).c_str(), rb.c_str(), sb::value(rb).c_str());
  for (double vbat : {9.0, 11.1, 12.6, 14.4}) {
    double vadc = vbat * rbot / (rtop + rbot);
    sim::pins[PIN_VBAT_SENSE].adc_mv = (uint32_t)(vadc * 1000 + 0.5);
    Serial2.out.clear(); Serial2.inject("?\n"); run_ms(2);
    auto v = nums(last_line(Serial2.out, "B"));
    double rep = v.empty() ? 0 : v[0] / 1000.0;
    bool low_ok = v.size() >= 2 && (v[1] == (vbat < 9.9 ? 1 : 0));
    CHECK(std::fabs(rep - vbat) < 0.05 * vbat && vadc < 3.1 && low_ok,
          "VBAT %.1f V -> ADC %.2f V (max 3.1 V) -> reporta %.2f V, alarma=%ld", vbat, vadc, rep, v.size() >= 2 ? v[1] : -1);
  }

  section("Alimentacion de las ESP32 (diodos Schottky en VIN)");
  for (const char* e : {"U2", "U3"}) {
    std::string vin = sb::net(e, "15");
    std::string d;
    for (auto& rp : sb::on_net(vin)) if (rp.first[0] == 'D') d = rp.first;
    bool ok = !d.empty() && sb::net(d, "1") == vin && sb::net(d, "2") == "+5V";
    CHECK(ok, "%s VIN=%s <- %s (catodo en VIN, anodo en +5V) %s", e, vin.c_str(), d.c_str(), sb::value(d).c_str());
  }

  section("Restricciones del ESP32");
  check_strapping(ESP);
  CHECK(sim::errors.empty(), "sin usos ilegales de GPIO en el firmware (%zu)", sim::errors.size());
  for (auto& e : sim::errors) printf("         - %s\n", e.c_str());
  printf("\nRESULTADO ESP32-B: %d OK, %d FALLAS\n", g_pass, g_fail);
  return g_fail ? 1 : 0;
}
