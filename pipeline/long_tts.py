#!/usr/bin/env python3
"""[롱폼 1] 타입캐스트 TTS — 롱폼(16:9) 전용.

쇼츠용 tts.py 와 다른 점:
  · 배속을 여기서 문장마다 걸고(script.json "speed", 기본 1.1) timing 도 배속 후 기준으로 낸다.
    → long_build.py 는 오디오를 다시 늘이거나 줄이지 않는다.
  · 문장 사이 쉼이 길다(롱폼은 숨이 필요하다). 챕터가 바뀌는 줄 앞, 질문 뒤는 더 쉰다.

사용: python3 pipeline/long_tts.py <slug>
산출: work/<slug>/tts/line_000.wav(원본) · sped_000.wav(배속) · narration.wav · timing.json
"""
import sys, os, json, subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tts as T

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

GAP = 0.32          # 기본 문장 간 쉼 (배속 후 초)
GAP_CHAPTER = 0.65  # 다음 줄이 새 챕터면
GAP_QUESTION = 0.45 # 질문 줄 뒤
LEAD_IN = 0.6       # 첫 문장 전 (타이틀이 먼저 뜨게)
TAIL = 1.8          # 마지막 문장 뒤 (엔드 카드)


def main():
    slug = sys.argv[1]
    wd = os.path.join(ROOT, "work", slug)
    sc = json.load(open(os.path.join(wd, "script.json"), encoding="utf-8"))
    speed = float(sc.get("speed", 1.1))
    key = T.env("TYPECAST_API_KEY")
    base_voice = T.VOICES.get(sc.get("voice", "main"), T.VOICES["main"])
    td = os.path.join(wd, "tts")
    os.makedirs(td, exist_ok=True)

    lines = sc["lines"]
    timing, parts, t = [], [], LEAD_IN
    for i, ln in enumerate(lines):
        text = ln["text"]
        vname = ln.get("voice", "")
        v = T.VOICES.get(vname, base_voice)
        emo, inten = T.auto_emotion(text)
        emo, inten = ln.get("emotion", emo), ln.get("intensity", inten)
        raw = os.path.join(td, f"line_{i:03d}.wav")
        if not os.path.exists(raw):
            if not key:
                sys.exit("TYPECAST_API_KEY 없음")
            print(f"[{i+1}/{len(lines)}] {vname or 'main'} {emo} · {text[:28]}", flush=True)
            if not T.tts(text, raw, key, v, emo, inten):
                sys.exit(f"TTS 실패: {text}")
            T.trim_silence(raw)
        sped = os.path.join(td, f"sped_{i:03d}.wav")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", raw,
                        "-af", f"atempo={speed},aresample=44100", "-ac", "1", sped], check=True)
        d = T.dur(sped)
        if i == len(lines) - 1:
            g = TAIL
        elif lines[i + 1].get("chap") is not None and lines[i + 1].get("chap") != "":
            g = GAP_CHAPTER
        elif text.strip().endswith("?"):
            g = GAP_QUESTION
        else:
            g = GAP
        timing.append({"i": i, "text": text, "start": round(t, 3), "dur": round(d, 3),
                       "end": round(t + d + g, 3)})
        parts.append((sped, g))
        t += d + g

    # 합치기: 앞 여백 + (문장 + 쉼)*
    lst = os.path.join(td, "concat.txt")
    def sil(p, sec):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                        "anullsrc=r=44100:cl=mono", "-t", f"{sec:.3f}", p], check=True)
    with open(lst, "w") as f:
        p0 = os.path.join(td, "_lead.wav"); sil(p0, LEAD_IN); f.write(f"file '{p0}'\n")
        for k, (p, g) in enumerate(parts):
            f.write(f"file '{p}'\n")
            ps = os.path.join(td, f"_sil_{k:03d}.wav"); sil(ps, g); f.write(f"file '{ps}'\n")
    narr = os.path.join(td, "narration.wav")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                    "-i", lst, "-c", "copy", narr], check=True)
    json.dump(timing, open(os.path.join(td, "timing.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(f"✓ 롱폼 TTS {len(parts)}줄 · 총 {t:.1f}초 ({int(t//60)}분 {t%60:.0f}초) · 배속 {speed}")


if __name__ == "__main__":
    main()
