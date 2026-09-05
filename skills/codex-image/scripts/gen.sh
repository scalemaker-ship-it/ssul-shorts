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
read -r -d '' CODEX_PROMPT <<EOF || true
Use your built-in image generation tool to create an image.

Subject / instruction:
"${PROMPT}"

Hard requirements:
- Save the FINAL PNG to EXACTLY this absolute path: ${OUT}
- Final image dimensions: ${WIDTH}x${HEIGHT} pixels, PNG format.
- Compose the image natively for a ${ORIENTATION} aspect ratio (do not just stretch a square).
  Prefer cropping/composing over distortion when resizing to the exact pixels above.
- Use ONLY the built-in image generation tool plus local tools (sips). Do NOT call any
  external or paid APIs, and do NOT write throwaway scripts that hit network image services.
- When finished, print ONLY the saved file path on the last line.
EOF

# --- run codex ---------------------------------------------------------------
run_codex() {
  # NOTE: -i/--image is variadic (<FILE>...), so it would greedily swallow the
  # prompt if placed before it. Always pass the prompt as the leading positional
  # argument and put -i AFTER it.
  if [[ -n "$REF" ]]; then
    codex exec --dangerously-bypass-approvals-and-sandbox "$CODEX_PROMPT" -i "$REF"
  else
    codex exec --dangerously-bypass-approvals-and-sandbox "$CODEX_PROMPT"
  fi
}

attempt() {
  local log
  log="$(run_codex 2>&1)" || true
  if [[ -f "$OUT" ]] && file "$OUT" 2>/dev/null | grep -qi 'PNG image'; then
    return 0
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
