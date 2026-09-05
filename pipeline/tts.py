#!/usr/bin/env python3
"""[1] 타입캐스트 TTS — script.json 의 lines 를 문장별 음성으로.

사용: python3 pipeline/tts.py <slug> [--gap 0.22]
산출: work/<slug>/tts/line_000.wav ... , narration.wav , timing.json
"""
import sys, os, json, subprocess, urllib.request, urllib.error, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import audio
import layout as L

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENDPOINT = "https://api.typecast.ai/v1/text-to-speech"
MODEL = "ssfm-v30"
DEFAULT_VOICE = "tc_691d49ccc47926d741f15913"   # 효은

# script.json 의 line["voice"] 로 지정하는 이름표
VOICES = {
    "duman":   "tc_663343dd0d6c33caad78de6f",  # 두만 — 기본 나레이션
    "jabbaba": "tc_62a89753894c1004cb577d04",  # 자바바 — 이전 대사 화자
    "yeseul":  "tc_66ab0e26ec23f325b7ad51df",  # 예슬 — 제3자 대사 전용 (현재 기본)
    "taesub":  "tc_62f223abb9d09c5b3131c7f2",  # 태섭
    "hyoeun":  "tc_691d49ccc47926d741f15913",
    "joonghyun": "tc_61cd3cc126463f411925e8a6",  # 중현 — 남성 나레이션
    "piljae":  "tc_68257f68bc6e3c161ab5078d",  # 필재 — 남성 나레이션
    "minuk":   "tc_68f0727fd62a5934102f7ec0",  # 민욱 — 남성 나레이션 (이전 main)
    "yongsik": "tc_5feb2085cca1a479e73bac37",  # 용식 — 남성 나레이션 (현재 main)
    "sehee":   "tc_611c3f692fac944dff493a04",  # 세희 — 여성 대사 (현재 sub1)
}

# ── 3화자 구성 (2026-08-28 확정 / main 은 2026-08-30 용식으로 교체) ──
# 기본 1 + 서브 2. 대사가 두 사람이면 서로 다른 서브를 준다.
#   main  : 나레이션 (민욱 — 08-30 용식으로 바꿨다가 08-31 되돌림)
#   sub1  : 대사 — 여성 (세희 — 2026-08-30 사용자 지시로 예슬에서 변경, 유지)
#   sub2  : 대사 — 남성 (중현). main 과 겹치지 않게 다른 화자를 쓴다
VOICES["main"] = VOICES["minuk"]
VOICES["sub1"] = VOICES["sehee"]
VOICES["sub2"] = VOICES["joonghyun"]

# 대사(제3자가 실제로 내뱉는 말)의 기본 화자. line["voice"]="sub2" 로 바꾼다
DIALOGUE_VOICE = "sub1"

# 끝의 "구독" 한 마디는 **여성 목소리**로 간다 (2026-08-28 사용자 확정).
# 본문 내내 남성 나레이션이라 마지막에 목소리가 바뀌면 귀가 한 번 열린다.
OUTRO_VOICE = "sub1"

# 마지막 "구독" 한 마디의 최종 배속 (본문은 L.SPEED).
# 1.5 는 끝이 짤려 들려서 1.15 로 내렸다 (2026-08-31 사용자 피드백).
OUTRO_SPEED = 1.15

# 문장 성격에 따라 톤을 바꾼다. 한 톤으로 쭉 가면 기계처럼 들린다.
def auto_emotion(text):
    t = text.strip()
    if t.endswith("?"):
        return "toneup", 1.5          # 질문은 끝을 올린다
    if t.endswith("!"):
        return "toneup", 1.8
    if any(t.endswith(x) for x in ("뿐.", "임.", "거.", "것.")):
        return "tonedown", 1.3        # 단정·여운은 내린다
    return "normal", 1.2


def env(key, default=None):
    v = os.environ.get(key)
    if v:
        return v
    p = os.path.join(ROOT, ".env")
    if os.path.exists(p):
        for ln in open(p):
            if ln.startswith(key + "="):
                return ln.split("=", 1)[1].strip()
    return default


def tts(text, out_wav, key, voice, emotion="normal", intensity=1.2, retries=3):
    body = json.dumps({
        "voice_id": voice, "text": text, "model": MODEL,
        "language": "kor", "emotion": emotion,
        "emotion_intensity": intensity,
    }).encode()
    req = urllib.request.Request(ENDPOINT, data=body, headers={
        "X-API-KEY": key, "Content-Type": "application/json"})
    for a in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                data = r.read()
            open(out_wav, "wb").write(data)
            return True
        except urllib.error.HTTPError as e:
            print(f"  HTTP {e.code}: {e.read()[:200]!r}")
            if e.code in (400, 401, 403):
                return False
        except Exception as e:
            print(f"  재시도 {a+1}/{retries}: {e}")
        time.sleep(2 * (a + 1))
    return False


def trim_silence(path):
    """앞뒤 무음을 잘라내고, 문장 안 긴 정적도 0.10초로 압축한다.

    타입캐스트 결과물은 앞뒤로 0.2~0.5초씩 여백이 붙어 나온다.
    쇼츠에서는 이 여백이 그대로 늘어짐이 되므로 공격적으로 없앤다.
    """
    tmp = path + ".trim.wav"
    af = (
        # 문장 내부의 정적 → 0.05초로 압축 (숨 쉬는 티만 남긴다)
        "silenceremove=stop_periods=-1:stop_duration=0.05:"
        "stop_threshold=-38dB:detection=peak,"
        # 앞쪽 무음 완전 제거
        "silenceremove=start_periods=1:start_silence=0:"
        "start_threshold=-38dB:detection=peak,"
        # 뒤집어서 같은 처리 → 뒤쪽 무음 제거
        "areverse,"
        "silenceremove=start_periods=1:start_silence=0:"
        "start_threshold=-38dB:detection=peak,"
        "areverse"
    )
    r = subprocess.run(["ffmpeg", "-y", "-i", path, "-af", af, tmp],
                       capture_output=True)
    if r.returncode == 0 and os.path.getsize(tmp) > 1000:
        os.replace(tmp, path)
    elif os.path.exists(tmp):
        os.remove(tmp)


def dur(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", path],
        capture_output=True, text=True).stdout.strip()
    return float(out) if out else 0.0


def main():
    if len(sys.argv) < 2:
        sys.exit("사용: python3 pipeline/tts.py <slug> [--gap 0.22]")
    slug = sys.argv[1]
    # audio.PACING 이 꺼져 있으면 전 문장 같은 간격(원래 동작).
    if "--gap" in sys.argv:
        flat_gap = float(sys.argv[sys.argv.index("--gap") + 1])
    else:
        flat_gap = None if audio.PACING else 0.03

    key = env("TYPECAST_API_KEY")
    # .env 의 TYPECAST_VOICE 는 '유라' 처럼 사람 이름이 들어있는 경우가 있어
    # voice_id 형식(tc_...)일 때만 사용한다
    voice = env("TYPECAST_VOICE", "") or ""
    voice = voice if voice.startswith("tc_") else DEFAULT_VOICE
    if not key:
        sys.exit("TYPECAST_API_KEY 없음 — .env 를 확인하세요")

    wd = os.path.join(ROOT, "work", slug)
    sc = json.load(open(os.path.join(wd, "script.json"), encoding="utf-8"))
    # script.json 의 "voice" 로 그 편의 기본 화자를 바꿀 수 있다 (예: "joonghyun")
    if sc.get("voice") in VOICES:
        voice = VOICES[sc["voice"]]
        print(f"화자: {sc['voice']}")
    td = os.path.join(wd, "tts")
    os.makedirs(td, exist_ok=True)

    lines_text = [(l["text"] if isinstance(l, dict) else l) for l in sc["lines"]]
    plan = audio.pace(lines_text)

    timing, t = [], 0.0
    parts = []
    for i, line in enumerate(sc["lines"]):
        # line 은 문자열이거나 {"text","voice","emotion","intensity","img"} 객체
        if isinstance(line, str):
            line = {"text": line}
        text = line["text"]
        # dialogue:true 면 화자를 자바바로 강제하고, 실제 말하듯 세게 연출한다
        dialogue = bool(line.get("dialogue"))
        vname = line.get("voice") or (DIALOGUE_VOICE if dialogue else "")
        if line.get("outro"):
            vname = line.get("voice") or OUTRO_VOICE
        v = VOICES.get(vname, voice)
        emo, inten = auto_emotion(text)
        if dialogue:
            emo, inten = "toneup", 2.0
        emo = line.get("emotion", emo)
        inten = line.get("intensity", inten)

        wav = os.path.join(td, f"line_{i:03d}.wav")
        if not os.path.exists(wav):
            tag = f" [{vname}]" if vname else ""
            print(f"[{i+1}/{len(sc['lines'])}]{tag} {emo}·{inten} · {text[:24]}...")
            if not tts(text, wav, key, v, emo, inten):
                sys.exit(f"TTS 실패: {text}")
            trim_silence(wav)
        # ── 완급 — 문장 역할마다 배속과 뒤 쉼을 다르게 준다 ──
        r, sp, g = plan[i]
        if flat_gap is not None:            # 예전 동작
            sp, g = 1.0, flat_gap
        # 끝의 "구독" 한 마디는 본문보다 빠르게 스친다. build 가 전체에 L.SPEED 를
        # 다시 걸므로, 최종 OUTRO_SPEED 가 되도록 여기서 비율만 미리 준다.
        outro = bool(line.get("outro"))
        if outro:
            sp = OUTRO_SPEED / L.SPEED
            g = 0.0
        if dialogue:
            g += 0.14                       # 대사는 앞뒤로 숨을 준다
        use = wav
        if abs(sp - 1.0) > 1e-6 or outro:
            use = os.path.join(td, f"paced_{i:03d}.wav")
            # 아웃트로는 뒤에 0.3초 숨을 붙인다 — 영상이 음성 끝에서 바로 끊겨
            # "구독"이 짤려 들리는 것을 막는다 (2026-08-31)
            af = f"atempo={sp}" + (",apad=pad_dur=0.3" if outro else "")
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav,
                            "-af", af, use], check=True)
        d = dur(use)
        timing.append({"i": i, "text": text, "start": round(t, 3),
                       "dur": round(d + g, 3), "img": line.get("img"),
                       "role": r})
        t += d + g
        parts.append((use, g))

    # 문장 사이 쉼을 넣어 하나로 합치기 (쉼 길이가 문장마다 다르다)
    lst = os.path.join(td, "concat.txt")
    with open(lst, "w") as f:
        for k, (p, g) in enumerate(parts):
            f.write(f"file '{p}'\n")
            sil = os.path.join(td, f"_sil_{k:03d}.wav")
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi",
                            "-i", "anullsrc=r=44100:cl=mono", "-t", f"{g:.3f}", sil],
                           check=True)
            f.write(f"file '{sil}'\n")
    narr = os.path.join(td, "narration.wav")
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0",
                    "-i", lst, "-c", "copy", narr], capture_output=True)

    json.dump(timing, open(os.path.join(td, "timing.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    chars = sum(len(x.replace(" ", "")) for x in lines_text)
    mode = f"고정간격 {flat_gap}s" if flat_gap is not None else "역할별 완급"
    print(f"✓ TTS {len(parts)}구간 · 총 {t:.1f}초 · {chars/t:.1f}자/초 ({mode}) → {narr}")


if __name__ == "__main__":
    main()
