#!/usr/bin/env python3
"""Enlace Raspberry Pi 5 <-> ESP32 del Rover Controller v1.1.

  ESP32-A (traccion): /dev/ttyAMA2  (dtoverlay=uart2-pi5, GPIO4 TX / GPIO5 RX)
  ESP32-B (servos):   /dev/ttyAMA0  (dtoverlay=uart0-pi5, GPIO14 TX / GPIO15 RX)

Uso rapido (prueba en el banco, con ruedas al aire):
  python3 rover_link.py test-motores
  python3 rover_link.py test-servos
Requiere: pip install pyserial
"""
import sys
import threading
import time


def checksum(s: str) -> int:
    c = 0
    for ch in s.encode():
        c ^= ch
    return c


def frame(cmd: str) -> bytes:
    return ("%s*%02X\n" % (cmd, checksum(cmd))).encode()


def parse(line: str):
    """Devuelve (cmd, [ints]) o None si la linea esta mal o el checksum no coincide."""
    line = line.strip()
    if "*" in line:
        body, ck = line.rsplit("*", 1)
        try:
            if int(ck, 16) != checksum(body):
                return None
        except ValueError:
            return None
        line = body
    parts = line.split()
    if not parts:
        return None
    try:
        return parts[0], [int(x) for x in parts[1:]]
    except ValueError:
        return parts[0], parts[1:]


class Esp32Link:
    def __init__(self, port, baud=115200):
        import serial  # pyserial
        self.ser = serial.Serial(port, baud, timeout=0.05)
        self.last = {}
        self._run = True
        threading.Thread(target=self._rx, daemon=True).start()

    def _rx(self):
        buf = b""
        while self._run:
            buf += self.ser.read(256)
            while b"\n" in buf:
                raw, buf = buf.split(b"\n", 1)
                msg = parse(raw.decode(errors="replace"))
                if msg:
                    self.last[msg[0]] = (time.time(), msg[1])

    def send(self, cmd: str):
        self.ser.write(frame(cmd))

    def close(self):
        self._run = False
        self.ser.close()


class Traction(Esp32Link):
    """6 motores: valores -1000..1000. Hay que llamar drive() al menos cada 300 ms
    (watchdog del firmware); si no, los motores se detienen solos."""

    def __init__(self, port="/dev/ttyAMA2"):
        super().__init__(port)

    def enable(self, on=True):
        self.send("EN %d" % (1 if on else 0))

    def drive(self, m):
        assert len(m) == 6
        self.send("M " + " ".join(str(int(max(-1000, min(1000, v)))) for v in m))

    def telemetry(self):
        """(cuentas[6], pulsos_por_s[6], bloqueados_mask, habilitado)"""
        t = self.last.get("T")
        if not t or len(t[1]) < 13:
            return None
        v = t[1]
        return v[0:6], v[6:12], v[12] & 0x3F, bool(v[12] & 0x80)


class Servos(Esp32Link):
    def __init__(self, port="/dev/ttyAMA0"):
        super().__init__(port)

    def angle(self, n, deg):
        self.send("A %d %d" % (n, deg))

    def pulse_us(self, n, us):
        self.send("S %d %d" % (n, us))

    def battery_mv(self):
        b = self.last.get("B")
        return b[1][0] if b else None


def _test_motores():
    t = Traction()
    t.enable(True)
    try:
        for i in range(6):
            for sign in (1, -1):
                print("Motor M%d %s" % (i + 1, "adelante" if sign > 0 else "atras"))
                end = time.time() + 1.5
                while time.time() < end:
                    cmd = [0] * 6
                    cmd[i] = 400 * sign
                    t.drive(cmd)
                    time.sleep(0.1)
                print("   telemetria:", t.telemetry())
    finally:
        t.enable(False)
        t.close()


def _test_servos():
    s = Servos()
    for n in range(1, 9):
        for d in (90, 45, 135, 90):
            s.angle(n, d)
            time.sleep(0.4)
    time.sleep(0.3)
    print("Bateria: %s mV" % s.battery_mv())
    s.close()


def _selftest(sample="/tmp/rover_sample_tx.txt"):
    """Valida que el formato que emite el firmware se lee bien aqui."""
    assert parse(frame("EN 1").decode()) == ("EN", [1])
    ok = bad = 0
    for line in open(sample):
        m = parse(line)
        if m and m[0] in ("T", "B", "ERR"):
            ok += 1
        else:
            bad += 1
    assert parse("T 1 2*00") is None, "checksum incorrecto debe rechazarse"
    print("selftest: %d lineas del firmware validas, %d invalidas" % (ok, bad))
    return bad == 0 and ok > 0


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "test-motores":
        _test_motores()
    elif cmd == "test-servos":
        _test_servos()
    elif cmd == "selftest":
        sys.exit(0 if _selftest(*sys.argv[2:]) else 1)
    else:
        print(__doc__)
