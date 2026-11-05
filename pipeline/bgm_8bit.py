#!/usr/bin/env python3
"""결혼준비 관리 페이지(경모·이슬 결혼준비)의 8비트 BGM 루프를 그대로 재현해 wav/mp3 로 굽는다.
원본: 페이지 JS — C장조 132BPM 8마디, 멜로디 square 0.028 / 베이스 triangle 0.07 / 하이햇 C7 0.006.
잔잔하게: 사각파 고음을 로우패스로 깎고(--soft), 전체 음량은 ffmpeg loudnorm 으로 맞춘다.
    python3 pipeline/bgm_8bit.py assets/bgm/wedding-8bit.mp3 [--sec 120]
"""
import sys, subprocess, tempfile, os, wave
import numpy as np

SR = 44100
EIGHTH = 60 / 132 / 2
MELODY = ("E5 G5 C6 G5 E5 G5 A5 G5 F5 A5 C6 A5 G5 F5 E5 D5 D5 G5 B5 G5 D5 G5 A5 B5 C6 - G5 E5 C5 - - - "
          "A4 C5 E5 A5 G5 E5 C5 E5 F5 E5 D5 C5 D5 E5 F5 A5 G5 F5 E5 D5 B4 D5 G5 B5 C6 - E5 G5 C6 - - -").split()
BASS = "C3 G3 C3 G3 F2 C3 F2 C3 G2 D3 G2 D3 C3 G2 C3 - A2 E3 A2 E3 F2 C3 F2 C3 G2 D3 G2 B2 C3 G2 C3 -".split()


def hz(n):
    if n == "-":
        return 0
    semi = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}[n[0]] + 12 * (int(n[-1]) + 1)
    return 440 * 2 ** ((semi - 69) / 12)


def tone(buf, f, t, dur, kind, vol):
    n = int((dur + 0.02) * SR)
    i0 = int(t * SR)
    tt = np.arange(n) / SR
    ph = (f * tt) % 1.0
    w = np.sign(np.sin(2 * np.pi * ph)) if kind == "square" else 4 * np.abs(ph - 0.5) - 1
    env = vol * np.exp(np.log(0.0008 / vol) * np.minimum(tt / dur, 1.0))
    env[tt > dur] = 0
    end = min(len(buf), i0 + n)
    buf[i0:end] += (w * env)[: end - i0]


def main():
    out = sys.argv[1]
    sec = float(sys.argv[sys.argv.index("--sec") + 1]) if "--sec" in sys.argv else 120
    buf = np.zeros(int((sec + 1) * SR))
    t, step = 0.0, 0
    while t < sec:
        m = hz(MELODY[step])
        if m:
            tone(buf, m, t, EIGHTH * 0.9, "square", 0.028)
        if step % 2 == 0:
            b = hz(BASS[step // 2])
            if b:
                tone(buf, b, t, EIGHTH * 1.8, "triangle", 0.07)
        if step % 4 == 2:
            tone(buf, hz("C7"), t, 0.03, "square", 0.006)
        t += EIGHTH
        step = (step + 1) % len(MELODY)
    buf = buf[: int(sec * SR)]
    buf /= max(1e-9, np.abs(buf).max()) / 0.8
    tmp = tempfile.mktemp(suffix=".wav")
    with wave.open(tmp, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((buf * 32767).astype(np.int16).tobytes())
    # 잔잔하게: 사각파 윗배음 깎고(lowpass 3.2k), 살짝 공간감, 원곡 수준 음량(-18 LUFS)으로 맞춤
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", tmp, "-af",
                    "lowpass=f=3200,aecho=0.8:0.6:60:0.18,loudnorm=I=-26:TP=-2,aformat=sample_rates=44100:channel_layouts=stereo",
                    "-b:a", "192k", out], check=True)
    os.remove(tmp)
    print(out)


if __name__ == "__main__":
    main()
