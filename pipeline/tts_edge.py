#!/usr/bin/env python3
"""[1-대체] edge-tts 나레이션 — 타입캐스트가 막혔을 때 쓰는 무료 경로.

사용: python3 pipeline/tts_edge.py <slug>
      → work/<slug>/tts/line_000.wav ... 를 만들어 둔다.
      이어서 python3 pipeline/tts.py <slug> 를 돌리면 합성은 건너뛰고
      타이밍 계산·무음 정리·narration.wav 합치기만 수행한다.

Microsoft Edge 의 TTS 를 쓴다. 계정도 API 키도 결제도 필요 없다.
한국어 남성 뉴럴 보이스가 둘 있어 나레이션과 대사를 갈라 쓴다.

  ko-KR-InJoonNeural              나레이션 (기본)
  ko-KR-HyunsuMultilingualNeural  대사 전용 — 타입캐스트의 자바바 역할

톤은 script.json 의 emotion 과 문장 끝(§9 규칙)을 보고 rate/pitch 로 옮긴다.
타입캐스트의 emotion 파라미터가 없어서 완전히 같지는 않지만 결이 비슷하게 잡힌다.

설치: pip3 install edge-tts
"""
import sys, os, json, subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAR = "ko-KR-InJoonNeural"
DLG = "ko-KR-HyunsuMultilingualNeural"

# 최종 1.4배속을 감안한 기본 속도. 22문장 기준 원본 48초 → 최종 34초가 실측값이다.
# 문장 수가 늘면 여기를 올려 25~50초 구간에 맞춘다.
RATE_NORMAL, RATE_UP, RATE_DOWN, RATE_DLG = "+24%", "+26%", "+18%", "+30%"

# 앞뒤 무음 제거 + 문장 내부 정적 압축 (tts.py 의 trim_silence 와 같은 값)
AF = ("silenceremove=stop_periods=-1:stop_duration=0.05:"
      "stop_threshold=-38dB:detection=peak,"
      "silenceremove=start_periods=1:start_silence=0:"
      "start_threshold=-38dB:detection=peak,"
      "areverse,"
      "silenceremove=start_periods=1:start_silence=0:"
      "start_threshold=-38dB:detection=peak,"
      "areverse")


def tone(line):
    """문장 성격 → (보이스, 속도, 피치). tts.py 의 auto_emotion 과 같은 기준."""
    t = line["text"].strip()
    e = line.get("emotion")
    if line.get("dialogue"):
        return DLG, RATE_DLG, "+18Hz"
    if e == "toneup" or t.endswith("?") or t.endswith("!"):
        return NAR, RATE_UP, "+8Hz"
    if e == "tonedown" or any(t.endswith(x) for x in ("임.", "것.", "뿐.", "거.")):
        return NAR, RATE_DOWN, "-8Hz"
    return NAR, RATE_NORMAL, "+0Hz"


def main():
    if len(sys.argv) < 2:
        sys.exit("사용: python3 pipeline/tts_edge.py <slug>")
    slug = sys.argv[1]
    wd = os.path.join(ROOT, "work", slug)
    sc = json.load(open(os.path.join(wd, "script.json"), encoding="utf-8"))
    td = os.path.join(wd, "tts")
    os.makedirs(td, exist_ok=True)

    mp3 = os.path.join(td, "_t.mp3")
    tmp = os.path.join(td, "_f.wav")
    for i, line in enumerate(sc["lines"]):
        if isinstance(line, str):
            line = {"text": line}
        wav = os.path.join(td, f"line_{i:03d}.wav")
        if os.path.exists(wav):
            continue
        v, rate, pitch = tone(line)
        subprocess.run(["python3", "-m", "edge_tts", "--voice", v,
                        f"--rate={rate}", f"--pitch={pitch}",
                        f"--text={line['text']}", f"--write-media={mp3}"],
                       check=True, capture_output=True)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", mp3,
                        "-ar", "44100", "-ac", "1", "-af", AF, wav], check=True)
        # 필터를 거치면 ffmpeg 가 길이 미상 헤더를 써서 ffprobe 가 N/A 를 뱉는다.
        # 한 번 더 통과시켜 RIFF 길이를 확정한다.
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav,
                        "-c:a", "pcm_s16le", tmp], check=True)
        os.replace(tmp, wav)
        print(f"[{i+1}/{len(sc['lines'])}] {rate} {pitch} · {line['text'][:24]}")
    for p in (mp3, tmp):
        if os.path.exists(p):
            os.remove(p)
    print(f"\n✓ {len(sc['lines'])}구간 → {td}\n  이어서: python3 pipeline/tts.py {slug}")


if __name__ == "__main__":
    main()
