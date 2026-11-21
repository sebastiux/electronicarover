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
  $CXX $FLAGS -DBOARD_MODEL_FILE="\"$model\"" test_traction.cpp -o /tmp/test_traction
  $CXX $FLAGS -DBOARD_MODEL_FILE="\"$model\"" test_servos.cpp -o /tmp/test_servos
  /tmp/test_traction || rc=1
  /tmp/test_servos || rc=1
done
echo
python3 ../pi/rover_link.py selftest /tmp/rover_sample_tx.txt || rc=1
exit $rc
