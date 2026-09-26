#!/usr/bin/env bash
# codex-image: generate one PNG via `codex exec` built-in image tool.
#
# Usage:
#   gen.sh --prompt "<text>" --out <abs/path/to/file.png> \
#          [--orientation square|landscape|portrait|wide] \
#          [--width N --height N] [--ref <abs/path/to/ref.png>]
#
# Exits 0 and prints the saved path on success; non-zero with a reason on failure.
set -euo pipefail

PROMPT=""
OUT=""
ORIENTATION="square"
WIDTH=1024
HEIGHT=1024
REF=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --prompt)      PROMPT="$2"; shift 2;;
    --out)         OUT="$2"; shift 2;;
    --orientation) ORIENTATION="$2"; shift 2;;
    --width)       WIDTH="$2"; shift 2;;
    --height)      HEIGHT="$2"; shift 2;;
    --ref)         REF="$2"; shift 2;;
    *) echo "gen.sh: unknown arg: $1" >&2; exit 2;;
  esac
done

# --- preflight ---------------------------------------------------------------
if ! command -v codex >/dev/null 2>&1; then
  echo "ERROR: codex not installed. Run: npm i -g @openai/codex" >&2
  exit 3
fi
if [[ ! -f "$HOME/.codex/auth.json" ]]; then
  echo "ERROR: codex not authenticated. Run: codex login" >&2
  exit 4
fi
if [[ -z "$PROMPT" || -z "$OUT" ]]; then
  echo "ERROR: --prompt and --out are required." >&2
  exit 2
fi
if [[ -n "$REF" && ! -f "$REF" ]]; then
  echo "ERROR: reference image not found: $REF" >&2
  exit 5
fi

OUTDIR="$(dirname "$OUT")"
mkdir -p "$OUTDIR"
rm -f "$OUT"

# --- build the codex prompt --------------------------------------------------
# 코덱스(GPT)는 이미지 생성만 한다. 저장·이동·리사이즈·검증은 이 스크립트가 한다.
# 코덱스가 셸 명령을 돌리면 턴마다 문맥이 다시 들어가 장당 토큰이 5배 이상 뛴다.
read -r -d '' CODEX_PROMPT <<EOF2 || true
Use your built-in image generation tool to create exactly ONE image.

Subject / instruction:
"${PROMPT}"

Compose it for a ${ORIENTATION} aspect ratio (target ${WIDTH}x${HEIGHT}).
Do NOT run any shell commands. Do NOT save, move, resize or verify files.
After the image is generated, reply only: done
EOF2

# 이미지 품질은 내장 이미지 도구가 정하므로 앞단 에이전트는 가벼운 모델로 충분하다.
# 기본값(gpt-6-astra)으로 두면 장당 한도 소모가 커진다. 필요하면 CODEX_IMAGE_MODEL 로 덮어쓴다.
MODEL="${CODEX_IMAGE_MODEL:-gpt-5.6-luna}"
EFFORT="${CODEX_IMAGE_EFFORT:-low}"
GEN_ROOT="$HOME/.codex/generated_images"

# --- run codex ---------------------------------------------------------------
run_codex() {
  # NOTE: -i/--image is variadic (<FILE>...), so it would greedily swallow the
  # prompt if placed before it. Always pass the prompt as the leading positional
  # argument and put -i AFTER it.
  local args=(exec --json --skip-git-repo-check --dangerously-bypass-approvals-and-sandbox
              -m "$MODEL" -c model_reasoning_effort="$EFFORT" "$CODEX_PROMPT")
  [[ -n "$REF" ]] && args+=(-i "$REF")
  codex "${args[@]}" </dev/null
}

# 생성본을 목표 크기로: 비율 유지해 꽉 채우게 확대/축소한 뒤 가운데 크롭.
fit_to_size() {
  local src="$1" dst="$2" sw sh
  sw=$(sips -g pixelWidth "$src" | awk '/pixelWidth/{print $2}')
  sh=$(sips -g pixelHeight "$src" | awk '/pixelHeight/{print $2}')
  read -r nw nh < <(awk -v sw="$sw" -v sh="$sh" -v tw="$WIDTH" -v th="$HEIGHT" 'BEGIN{
    s = (tw/sw > th/sh) ? tw/sw : th/sh
    printf "%d %d\n", int(sw*s+0.999), int(sh*s+0.999) }')
  sips -s format png -z "$nh" "$nw" "$src" --out "$dst" >/dev/null
  sips -c "$HEIGHT" "$WIDTH" "$dst" >/dev/null
}

attempt() {
  local log tid img
  log="$(run_codex 2>&1)" || true
  # 동시 실행과 섞이지 않게 이 실행의 thread_id 폴더에서만 찾는다.
  tid="$(echo "$log" | grep -oE '"thread_id":"[^"]+"' | head -1 | cut -d'"' -f4)"
  if [[ -n "$tid" && -d "$GEN_ROOT/$tid" ]]; then
    img="$(ls -t "$GEN_ROOT/$tid"/*.png 2>/dev/null | head -1)"
    if [[ -n "$img" ]]; then
      fit_to_size "$img" "$OUT"
      if [[ -f "$OUT" ]] && file "$OUT" 2>/dev/null | grep -qi 'PNG image'; then
        return 0
      fi
    fi
  fi
  # surface the tail of codex output for diagnosis
  echo "$log" | tail -25 >&2
  return 1
}

if attempt; then
  echo "$OUT"
  exit 0
fi

echo "gen.sh: first attempt did not produce a valid PNG; retrying once..." >&2
if attempt; then
  echo "$OUT"
  exit 0
fi

echo "ERROR: codex did not produce a valid PNG at $OUT after 2 attempts." >&2
exit 1
