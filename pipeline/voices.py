#!/usr/bin/env python3
"""화자 고르기 — 후보 목소리로 같은 문장을 만들어 듣고 비교한다.

사용: python3 pipeline/voices.py                 # 기본 후보로 샘플 생성
      python3 pipeline/voices.py --text "문장"
      python3 pipeline/voices.py --list          # 전체 목소리 목록

산출: assets/voice_samples/<이름>.wav
고른 뒤 .env 의 TYPECAST_VOICE=tc_... 에 넣으면 tts.py 가 그걸 쓴다.
"""
import sys, os, json, urllib.request, urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TTS = "https://api.typecast.ai/v1/text-to-speech"
LIST = "https://api.typecast.ai/v1/voices"
MODEL = "ssfm-v30"

# 목록 API 에 언어 필드가 없어 한국어 화자는 이름으로 추린다
CANDIDATES = [
    "Sanghyun", "Juwan", "Byunghun", "Minuk", "Kangil", "Woony",
    "Seohyeon", "Okji", "Jungsook", "Daeun", "Hyoeun", "Moonjung", "Leehyun",
]
SAMPLE = "퇴근하고 아무것도 못 하는 사람 특징?"


def key():
    for ln in open(os.path.join(ROOT, ".env"), encoding="utf-8"):
        if ln.startswith("TYPECAST_API_KEY="):
            return ln.split("=", 1)[1].strip()
    sys.exit("TYPECAST_API_KEY 없음")


def voices(k):
    r = urllib.request.Request(LIST, headers={"X-API-KEY": k})
    return json.loads(urllib.request.urlopen(r, timeout=30).read())


def main():
    k = key()
    vs = voices(k)
    if "--list" in sys.argv:
        for v in vs:
            print(v["voice_id"], v["voice_name"], v["model"])
        return

    text = sys.argv[sys.argv.index("--text") + 1] if "--text" in sys.argv else SAMPLE
    out = os.path.join(ROOT, "assets", "voice_samples")
    os.makedirs(out, exist_ok=True)

    by_name = {}
    for v in vs:
        if v["model"] == MODEL:
            by_name.setdefault(v["voice_name"], v)

    made = []
    for name in CANDIDATES:
        v = by_name.get(name)
        if not v:
            print(f"  · {name}: 목록에 없음")
            continue
        body = json.dumps({"voice_id": v["voice_id"], "text": text,
                           "model": MODEL, "language": "kor",
                           "emotion": "normal"}).encode()
        req = urllib.request.Request(TTS, data=body, headers={
            "X-API-KEY": k, "Content-Type": "application/json"})
        try:
            data = urllib.request.urlopen(req, timeout=60).read()
        except urllib.error.HTTPError as e:
            print(f"  ✗ {name}: HTTP {e.code} {e.read()[:120]!r}")
            continue
        p = os.path.join(out, f"{name}.wav")
        open(p, "wb").write(data)
        made.append((name, v["voice_id"], p))
        print(f"  ✓ {name}  {v['voice_id']}")

    if made:
        print(f"\n샘플 {len(made)}개 → {out}")
        print("들어보고 고른 뒤 .env 에:  TYPECAST_VOICE=<voice_id>")


if __name__ == "__main__":
    main()
