#!/usr/bin/env python3
"""[1-대체] 내 목소리 TTS — 타입캐스트 대신 사용자 본인 목소리(로컬, 0원).

사용: ~/Desktop/kim/myvoice-tts/.venv/bin/python pipeline/tts_myvoice.py <slug>
      → work/<slug>/tts/line_000.wav ... 를 만들어 둔다.
      이어서 python3 pipeline/tts.py <slug> 를 돌리면 합성은 건너뛰고
      타이밍 계산·narration.wav 합치기만 수행한다 (tts_edge.py 와 같은 방식).

엔진은 Chatterbox Multilingual(MIT). 목소리 프로필은 myvoice-tts/voices/<이름>/ 에 있다.
script.json 의 "myvoice" 로 고른다 (기본 "이슬", 그 외 "경모" 등).
  나레이션              → narration.wav
  대사(dialogue)·아웃트로 → talk1.wav  (타입캐스트의 세희 자리)
  대사 줄에 "speaker": 2 / 3 → talk2.wav / talk3.wav (다른 캐릭터)
  "myvoice_narration": "talk1" → 나레이션을 밝은 캐릭터1 샘플로 (웃음톤, 10/4 사용자 요청.
     감정값만 올리는 건 음높이·억양이 거의 안 변했고, 샘플을 바꾸면 평균 음높이 +50Hz)
  대사 줄에 "speaker": 0 → 원래 기본 나레이션 샘플(narration.wav)로 대사를 읽는다
     (나레이션을 캐릭터로 바꾼 편에서 차분한 기본 목소리를 대화체로 쓸 때)
발음 사전 myvoice-tts/pron.json (예: 오징어게임 → 오징어께임) 이 읽기용 문장에 자동 적용된다.

샘플은 **녹음 원본 그대로**(앞 무음만 자름) 쓴다. 잡음 제거·음량 평준화를 거친
샘플은 화자 유사도가 0.77~0.83 으로 떨어져 남의 목소리처럼 들렸다(원본은 0.915).
잡음 제거는 샘플이 아니라 **생성된 음성**에 건다(myvoice-tts/clean.py).

문장마다: 생성 → DeepFilterNet 잡음 제거 → 받아쓰기로 말 끝 자르기 → 대본 일치율 검사.
일치율이 낮으면 시드를 바꿔 최대 3번 다시 만들고 가장 잘 맞은 것을 쓴다.

숫자는 못 읽는다(5,160만 → 깨짐, 90년대 → "겨울 년대"). 숫자가 든 줄은
"say" 에 한글로 풀어 쓴 읽기용 문장을 넣는다 — 자막은 "text" 의 숫자 그대로 나간다.
"""
import os, sys, json, shutil

os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")
import torch
import torchaudio as ta
from chatterbox.mtl_tts import ChatterboxMultilingualTTS

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MV = os.path.expanduser(os.environ.get("MYVOICE_DIR", "~/Desktop/kim/myvoice-tts"))
sys.path.insert(0, MV)
from clean import finalize, pron, voice_refs  # noqa: E402

NAR = {"mode": "narration", "exag": 0.5, "cfg": 0.5}
TALK = {"mode": "talk", "exag": 0.75, "cfg": 0.4}
TRIES = int(os.environ.get("MYVOICE_TRIES", 3))
GOOD = float(os.environ.get("MYVOICE_GOOD", 0.85))  # 일치율 GOOD 이상이면 바로 채택


def pick(line):
    """문장 성격 → 목소리·감정. 물음표/느낌표는 감정을 조금 올린다."""
    v = dict(TALK if (line.get("dialogue") or line.get("outro")) else NAR)
    if v["mode"] == "talk":
        v["mode"] = f"talk{line.get('speaker', 1)}"
    t = line["text"].strip()
    if line.get("emotion") == "toneup" or t.endswith(("?", "!")):
        v["exag"] = min(1.0, v["exag"] + 0.15)
    # 줄에 "exag" 를 주면 그 값으로(2026-10-17 "더 신나서 말하는 톤" — 나레이션 0.8·대사 0.95)
    if "exag" in line:
        v["exag"] = line["exag"]
    return v


def main():
    if len(sys.argv) < 2:
        sys.exit("사용: pipeline/tts_myvoice.py <slug>")
    slug = sys.argv[1]
    wd = os.path.join(ROOT, "work", slug)
    sc = json.load(open(os.path.join(wd, "script.json"), encoding="utf-8"))
    td = os.path.join(wd, "tts")
    os.makedirs(td, exist_ok=True)

    refs = voice_refs(sc.get("myvoice", "이슬"))
    refs["talk0"] = refs["narration"]
    if sc.get("myvoice_narration"):
        refs["narration"] = refs[sc["myvoice_narration"]]
    print(f"목소리: {sc.get('myvoice', '이슬')}")
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    model = ChatterboxMultilingualTTS.from_pretrained(device=device)
    raw = os.path.join(td, "_raw.wav")
    cand = os.path.join(td, "_cand.wav")
    n = len(sc["lines"])
    for i, line in enumerate(sc["lines"]):
        if isinstance(line, str):
            line = {"text": line}
        wav = os.path.join(td, f"line_{i:03d}.wav")
        if os.path.exists(wav):
            continue
        # 롱폼(2026-10-09 사용자 지시): 나레이션만 이슬, "voice" 가 붙은 질문·대사 줄은 타입캐스트(long_tts.py 가 채움)
        if sc.get("format") == "long" and line.get("voice"):
            continue
        v = pick(line)
        # "say" = TTS 가 읽을 문장(숫자를 한글로 풀어 쓴 것). 자막은 "text" 그대로
        say = line.get("say", line["text"])
        best = (-1.0, "")
        for k in range(TRIES):
            torch.manual_seed(7 + k)
            out = model.generate(pron(say), language_id="ko", audio_prompt_path=refs[v["mode"]],
                                 exaggeration=v["exag"], cfg_weight=v["cfg"])
            ta.save(raw, out.cpu(), model.sr)
            score, heard = finalize(raw, cand, say)
            if score > best[0]:
                best = (score, heard)
                shutil.copy(cand, wav)
                shutil.copy(raw, os.path.join(td, f"raw_{i:03d}.wav"))  # 다시 자를 수 있게 원본 보관
            if score >= GOOD:
                break
        who = "나레" if v["mode"] == "narration" else f"대사{v['mode'][4:]}"
        flag = "" if best[0] >= GOOD else "  ⚠ 확인 필요"
        print(f"[{i+1}/{n}] {who} {best[0]:.2f}×{k+1} · {say[:22]} → {best[1][:22]}{flag}",
              flush=True)
    for p in (raw, cand):
        if os.path.exists(p):
            os.remove(p)
    print(f"\n✓ {n}구간 → {td}\n  이어서: python3 pipeline/tts.py {slug}")


if __name__ == "__main__":
    main()
