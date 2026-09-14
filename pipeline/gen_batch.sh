#!/usr/bin/env bash
# 1안 codex-image(gpt) 배치 — work/<slug>/prompts.tsv (번호\t프롬프트) 를 3워커로 돈다.
# FROG 등 특수 슬롯은 건너뛴다(대문자 단어 한 개 = 별도 처리). 실패는 fail.txt.
# 사용: nohup pipeline/gen_batch.sh <slug> [<slug2> ...] > /dev/null 2>&1 < /dev/null &
ROOT=/Users/kimyiseul/Desktop/kim/ssul
worker() {
  local D=$1 W=$2 n=0
  while IFS=$'\t' read -r num prompt; do
    n=$((n+1)); [ $((n % 3)) -ne "$W" ] && continue
    [[ "$prompt" =~ ^[A-Z]+$ ]] && continue
    out="$D/img/$num.png"; [ -s "$out" ] && continue
    if ~/.claude/skills/codex-image/scripts/gen.sh --prompt "$prompt" --out "$out" \
         --orientation landscape --width 1280 --height 800 </dev/null >"$D/log_$num.txt" 2>&1; then
      echo "ok $num" >> "$D/gen.out"
    else
      echo "$num" >> "$D/fail.txt"; echo "FAIL $num" >> "$D/gen.out"
    fi
  done < "$D/prompts.tsv"
}
for slug in "$@"; do
  D="$ROOT/work/$slug"; mkdir -p "$D/img"; rm -f "$D/fail.txt"
  for w in 0 1 2; do worker "$D" $w & done
  wait
done
