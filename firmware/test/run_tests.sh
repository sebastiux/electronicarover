#!/bin/bash
# Compila y corre la simulacion firmware <-> PCB en la PC (g++ >= 9).
set -e
cd "$(dirname "$0")"
CXX=${CXX:-g++}
FLAGS="-std=c++17 -Wall -Wextra -Wno-unused-parameter -I. -I../common"
rc=0
# una pasada por cada PCB: v1.2 (board_model.h) y variantes (board_model_<variante>.h)
for model in board_model.h board_model_*.h; do
  [ -f "$model" ] || continue
  echo "################ $model"
  # las tarjetas separadas llevan una sola ESP32: cada una corre solo su prueba
  case "$model" in *servos*) pruebas="servos" ;; *traccion*) pruebas="traction" ;; *) pruebas="traction servos" ;; esac
  for t in $pruebas; do
    $CXX $FLAGS -DBOARD_MODEL_FILE="\"$model\"" test_$t.cpp -o /tmp/test_$t
    /tmp/test_$t || rc=1
  done
done
echo
python3 ../pi/rover_link.py selftest /tmp/rover_sample_tx.txt || rc=1
exit $rc
