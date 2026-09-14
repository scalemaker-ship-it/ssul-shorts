#!/usr/bin/env bash
D=/Users/kimyiseul/Desktop/kim/ssul/work/parking
for w in 0 1 2; do "$D/gen.sh" $w > "$D/worker_$w.out" 2>&1 & done
wait
