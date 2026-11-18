#!/bin/bash
# Compila y corre la simulacion firmware <-> PCB en la PC (g++ >= 9).
set -e
cd "$(dirname "$0")"
CXX=${CXX:-g++}
FLAGS="-std=c++17 -Wall -Wextra -Wno-unused-parameter -I. -I../common"
$CXX $FLAGS test_traction.cpp -o /tmp/test_traction
$CXX $FLAGS test_servos.cpp -o /tmp/test_servos
rc=0
/tmp/test_traction || rc=1
/tmp/test_servos || rc=1
echo
python3 ../pi/rover_link.py selftest /tmp/rover_sample_tx.txt || rc=1
exit $rc
