#!/usr/bin/env python3
"""[1-이슈쿠키 목소리] 채널 공용 TTS — GPT-SoVITS 세트 issuecookie_1009 (2026-10-09 사용자 지시, 휴지·란빵 공통).

사용: python3 pipeline/tts_issuecookie.py <slug>
  → work/<slug>/tts/line_NNN.wav (원속, -24 LUFS) 를 채운다.
  이어서 쇼츠는 python3 pipeline/tts.py <slug>, 롱폼은 python3 pipeline/long_tts.py <slug>
  가 합성 없이 이어 붙인다(타이밍·배속은 그쪽 그대로).

설치: ~/Desktop/kim/issuecookie-voice (github rudah77-png/issuecookie-voice, ./setup.sh)

줄 → 목소리
  나레이션                 → 01_narr_normal. 줄에 "tone": absurd·surprise·angry·sarcastic·serious 로 감정
  "dialogue": true (여성)  → 12_female      ("voice": "sub2" 면 남성 인물 07_char_official)
  "outro": true ("구독!")  → 12_female      (기존 OUTRO_VOICE 가 여성이었던 자리)
  "char": official·rude·plead 로 남성 인물 목소리 직접 지정 가능
읽는 문장 = 줄의 "say" → 없으면 "text" 의 숫자를 한글로 바꾼 것(num_ko). 자막은 "text" 그대로.
흐름: 문장마다 3테이크 → Whisper 로 고르기(make_test.py) → DeepFilterNet 15dB → -24 LUFS 44.1k
"""
import json, os, re, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MV = os.path.expanduser(os.environ.get("ISSUECOOKIE_DIR", "~/Desktop/kim/issuecookie-voice"))
SET = "issuecookie_1009"
PY_GSV = os.path.join(MV, "GPT-SoVITS", ".venv", "bin", "python")
PY_DF = os.path.join(MV, "enhance", ".venv", "bin", "python")
LUFS = -24.0

TONE = {"normal": "01_narr_normal", "absurd": "02_narr_absurd", "surprise": "03_narr_surprise",
        "angry": "04_narr_angry", "sarcastic": "05_narr_sarcastic", "serious": "06_narr_serious"}
CHAR = {"official": "07_char_official", "rude": "08_char_rude", "plead": "09_char_plead"}
FEMALE = "12_female"

# ───────── 숫자 → 한글 ─────────
DIG = "영일이삼사오육칠팔구"
NATIVE = {1: "한", 2: "두", 3: "세", 4: "네", 5: "다섯", 6: "여섯", 7: "일곱", 8: "여덟", 9: "아홉", 10: "열",
          11: "열한", 12: "열두", 20: "스무"}
NATIVE_UNIT = ("명", "개", "번", "살", "마리", "잔", "대", "곳", "가지", "달", "군데", "벌", "켤레", "그릇", "병", "채", "척", "권", "장")


def sino(n):
    if n == 0:
        return "영"
    out = ""
    for big, name in ((10 ** 12, "조"), (10 ** 8, "억"), (10 ** 4, "만"), (1, "")):
        q = n // big; n %= big
        if not q:
            continue
        s = ""
        for p, u in ((1000, "천"), (100, "백"), (10, "십"), (1, "")):
            d = q // p; q %= p
            if d:
                s += ("" if d == 1 and u else DIG[d]) + u
        if name == "만" and s == "일":
            s = ""
        out += s + name
    return out


def native(n):
    if n in NATIVE:
        return NATIVE[n]
    if 10 < n < 100:
        tens = {1: "열", 2: "스물", 3: "서른", 4: "마흔", 5: "쉰", 6: "예순", 7: "일흔", 8: "여든", 9: "아흔"}[n // 10]
        return tens + ("" if n % 10 == 0 else NATIVE.get(n % 10, ""))
    return sino(n)


def num_ko(t):
    PH = "공일이삼사오육칠팔구"  # 전화번호는 0 을 '공'으로, 사이 '-' 는 '다시'
    t = re.sub(r"(\d{2,4})-(\d{3,4})(?:-(\d{4}))?", lambda m: " 다시 ".join("".join(PH[int(c)] for c in g) for g in m.groups() if g), t)
    t = re.sub(r"(\d+)\.(\d+)", lambda m: sino(int(m[1])) + "점" + "".join(DIG[int(c)] for c in m[2]), t)
    t = t.replace("%", "퍼센트")
    for a, b in (("km/h", "킬로미터"), ("km", "킬로미터"), ("kg", "킬로그램"), ("cm", "센티미터"), ("mm", "밀리미터"), ("m", "미터")):
        t = re.sub(r"(?<=\d)\s?" + a + r"(?![a-zA-Z])", b, t)
    t = re.sub(r"(\d+)0대", lambda m: sino(int(m[1] + "0")) + "대", t)  # 50대(나이·연령대)는 한자어

    def one(m):
        n = int(m[1].replace(",", "")); unit = m[2] or ""
        if unit == "시" and n <= 12 or unit.startswith(NATIVE_UNIT) and not unit.startswith("개월") and n < 100:
            return native(n) + " " + unit
        return sino(n) + unit

    t = re.sub(r"(\d[\d,]*)\s?(개월|" + "|".join(sorted(NATIVE_UNIT + ("시",), key=len, reverse=True)) + r")?", one, t)
    t = re.sub(r"([십백천만억])\s+원", r"\1원", t)  # 20만원 — 금액은 붙여 읽는다(2026-10-10 사용자 지시)
    # 금액은 연음 그대로 적어 읽힌다 — "이십만 원" 처럼 끊지 말고 "이십마넌"(2026-10-10 사용자 지시: 금액은 무조건 마넌)
    for a, b in (("일억원", "이러권"), ("만원", "마넌"), ("천원", "처넌"), ("백원", "배권"), ("십원", "시번"), ("억원", "어권")):
        t = t.replace(a, b)
    return t.replace("육월", "유월").replace("십월", "시월")


def lufs(p):
    err = subprocess.run(["ffmpeg", "-hide_banner", "-i", p, "-af", "ebur128", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", err)[-1])


def ref_of(ln):
    if ln.get("outro"):
        return FEMALE
    if ln.get("dialogue") or ln.get("voice") in ("sub1", "sub2"):
        if ln.get("voice") == "sub2" or ln.get("char"):
            # 쇼츠 대사 기본 톤이 angry(따짐) 였다 → rude, happy·sad → plead, 그 외 official
            emo = ln.get("emotion", "angry")
            c = ln.get("char") or {"angry": "rude", "happy": "plead", "sad": "plead", "toneup": "plead"}.get(emo, "official")
            return CHAR.get(c, CHAR["official"])
        return FEMALE
    return TONE.get(ln.get("tone", "normal"), TONE["normal"])


def main():
    slug = sys.argv[1]
    wd = os.path.join(ROOT, "work", slug)
    sc = json.load(open(os.path.join(wd, "script.json"), encoding="utf-8"))
    lines = [x if isinstance(x, dict) else {"text": x} for x in sc["lines"]]
    td = os.path.join(wd, "tts"); os.makedirs(td, exist_ok=True)
    tmp = os.path.join(wd, "ic_tmp")
    # 지난 실행의 테이크가 남아 있으면 같은 L 번호의 옛 음성이 다시 뽑힌다(10-16 phish010 L002 에 L003 내용이 들어감)
    shutil.rmtree(tmp, ignore_errors=True); os.makedirs(tmp)

    segs, mp = [], {}
    for i, ln in enumerate(lines):
        if os.path.exists(os.path.join(td, f"line_{i:03d}.wav")):
            continue
        sid = f"L{i:03d}"
        say = ln.get("say") or num_ko(ln["text"])
        if ln.get("outro") and not ln.get("say") and len(say.strip("!~ ")) <= 3:
            say = "구독해 주세요!"  # 이 모델은 "구독!" 같은 아주 짧은 말을 뭉개거나 딴말로 만든다(10-09 시험)
        ref = ref_of(ln)
        segs.append({"id": sid, "speaker": "M" if ref.startswith("0") and "narr" in ref else "M2", "text": ln["text"], "tts_text": say})
        mp[sid] = ref
    print(f"[이슈쿠키] {len(lines)}문장 · 새로 {len(segs)}", flush=True)
    if segs:
        for s in segs:
            if re.search(r"\d", s["tts_text"]):
                print("  ⚠ 숫자 남음:", s["tts_text"])
        sub = os.path.join(tmp, "draft.json"); json.dump({"segments": segs}, open(sub, "w"), ensure_ascii=False)
        mpp = os.path.join(tmp, "map.json"); json.dump(mp, open(mpp, "w"))
        env = dict(os.environ, AUX_NORMAL="1", KEEP_PAUSES="1")  # 문장 안 쉼 살림(10-10 "띄어쓰기 이상")
        r = subprocess.run([PY_GSV, os.path.join(MV, "make_test.py"), sub, tmp, mpp,
                            "--narr-voice", f"{SET}/narr", "--char-voice", SET, "--takes", os.environ.get("IC_TAKES", "3")], env=env, text=True)
        if r.returncode != 0:
            sys.exit("이슈쿠키 합성 실패")
        r = subprocess.run([PY_DF, os.path.join(MV, "enhance", "clean.py"), os.path.join(tmp, "final_1x"),
                            os.path.join(tmp, "final_df"), "--atten", "15"], text=True)
        if r.returncode != 0:
            sys.exit("잡음 제거 실패")
        for s in segs:
            src = os.path.join(tmp, "final_df", f"{s['id']}.wav")
            dst = os.path.join(td, f"line_{int(s['id'][1:]):03d}.wav")
            gain = LUFS - lufs(src)
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", src, "-ar", "44100", "-ac", "1",
                            "-af", f"volume={gain:.2f}dB,alimiter=limit=0.95", dst], check=True)
        rep = open(os.path.join(tmp, "report.txt"), encoding="utf-8").read().splitlines()
        print("[이슈쿠키] " + rep[0])
        for l in rep[1:]:
            m = re.search(r"테이크\d (-?[\d.]+)", l)
            if m and float(m[1]) < 0.75:
                print("  ⚠ 받아쓰기 낮음(직접 들어볼 것):", l)
    print(f"✓ 이슈쿠키 목소리 → {td}")


if __name__ == "__main__":
    main()
