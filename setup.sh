#!/usr/bin/env bash
# 처음 한 번 실행 — 파이썬 패키지 설치, .env 준비, 효과음 생성, 설치 점검.
#   ./setup.sh          기본(TTS·렌더·조립)
#   ./setup.sh --sdxl   로컬 이미지 생성 모델까지 (약 7GB 다운로드)
set -e
cd "$(dirname "$0")"

command -v ffmpeg >/dev/null || { echo "✗ ffmpeg 가 없습니다. macOS: brew install ffmpeg / Ubuntu: sudo apt install ffmpeg"; exit 1; }
python3 -m pip install -r requirements.txt

[ -f .env ] || { cp .env.example .env; echo "→ .env 를 만들었습니다. TYPECAST_API_KEY 를 채워 주세요."; }

python3 pipeline/sfx.py                 # 효과음을 코드로 합성 (assets/sfx/)
python3 pipeline/layout_check.py        # 화면 규격 잠금 점검

if [ "$1" = "--sdxl" ]; then
  python3 -m venv sdvenv
  sdvenv/bin/pip install -r requirements-sdxl.txt huggingface_hub
  mkdir -p models/lora
  sdvenv/bin/python - <<'PY'
from huggingface_hub import hf_hub_download
hf_hub_download("SG161222/RealVisXL_V5.0", "RealVisXL_V5.0_fp16.safetensors", local_dir="models")
hf_hub_download("ByteDance/SDXL-Lightning", "sdxl_lightning_8step_lora.safetensors", local_dir="models/lora")
PY
fi

[ -f assets/bgm.mp3 ] || echo "ℹ BGM 없음 — 쓰고 싶으면 저작권 무료 곡을 assets/bgm.mp3 로 넣으세요 (없으면 BGM 없이 렌더)."
echo "✓ 준비 완료. README 의 '빠르게 시작하기' 를 따라 첫 편을 만들어 보세요."
