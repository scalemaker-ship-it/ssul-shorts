#!/usr/bin/env bash
# 1안 codex-image(gpt). 워커 $1 = 0..2, 13장을 3으로 나눠 돈다. 실패 장은 fail.txt 에 기록.
W=${1:-0}
D=/Users/kimyiseul/Desktop/kim/ssul/work/parking
mkdir -p "$D/img"
n=0
while IFS=$'\t' read -r num prompt; do
  n=$((n+1))
  [ $((n % 3)) -ne "$W" ] && continue
  out="$D/img/$num.png"
  [ -s "$out" ] && continue
  if ~/.claude/skills/codex-image/scripts/gen.sh --prompt "$prompt" --out "$out" \
       --orientation landscape --width 1280 --height 800 </dev/null >"$D/log_$num.txt" 2>&1; then
    echo "ok $num"
  else
    echo "$num" >> "$D/fail.txt"; echo "FAIL $num"
  fi
done < "$D/prompts.tsv"
