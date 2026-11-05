#!/usr/bin/env python3
"""문장 시작 효과음 6종 — 코드로 합성(라이선스 걱정 없음). 2026-10-10 사용자 지시.

  click     클릭 (일반 문장)
  knife     칼 가는 소리 "스릉" (화남·어이없는 문제 제기)
  dudung    두둥 (기존 assets/sfx/dudung.wav — 문제 제기·충격)
  pang      팡 (숫자·사실 강조)
  dingring  띠링 (알림·질문·정보)
  sparkle   뾰로롱 (해결하는 문장)
  qping     물음표 핑 "띵-딩" (물음표로 끝나는 문장 — 화면에 노란 ? 핑과 같이)

사용: python3 pipeline/sfx_pack.py   → assets/sfx/<name>.wav (44.1k mono)
음량은 여기서 맞추지 않는다 — to_remotion.py 가 렌더 때 나레이션 실제 음량의 0.8배로 맞춘다.
"""
import os, subprocess
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SR = 44100
rng = np.random.default_rng(3)


def t(sec):
    return np.arange(int(sec * SR)) / SR


def env(n, a=0.003, d=0.2):
    x = np.arange(n) / SR
    return np.minimum(1, x / a) * np.exp(-x / d)


def bandnoise(n, lo, hi):
    f = np.fft.rfft(rng.standard_normal(n))
    fr = np.fft.rfftfreq(n, 1 / SR)
    f[(fr < lo) | (fr > hi)] = 0
    y = np.fft.irfft(f, n)
    return y / (np.abs(y).max() + 1e-9)


def click():
    n = int(0.06 * SR)
    y = bandnoise(n, 1500, 9000) * env(n, 0.0005, 0.006)
    y += 0.6 * np.sin(2 * np.pi * 2400 * t(0.06)) * env(n, 0.0005, 0.01)
    return y


def knife():
    # 금속 날이 숫돌·칼집을 긁고 나가는 "스릉~" — 위로 쓸리는 대역 잡음 + 고음 금속 울림
    d = 0.75
    n = int(d * SR)
    x = t(d)
    sweep = np.zeros(n)
    seg = int(0.03 * SR)
    for k in range(0, n - seg, seg // 2):          # 중심 주파수가 3k → 8k 로 올라가며 긁힌다
        c = 3000 + 5000 * (k / n)
        w = bandnoise(seg, c * 0.8, c * 1.25) * np.hanning(seg)
        sweep[k:k + seg] += w
    scrape = sweep * np.minimum(1, x / 0.05) * np.exp(-np.maximum(0, x - 0.35) / 0.12)
    ring = sum(a * np.sin(2 * np.pi * f * x + p) for f, a, p in
               ((4180, 0.5, 0.0), (6230, 0.35, 1.1), (8890, 0.25, 2.3), (11500, 0.15, 0.7)))
    ring = ring * np.where(x > 0.3, np.exp(-(x - 0.3) / 0.25), 0) * np.minimum(1, np.maximum(0, x - 0.28) / 0.02)
    return 0.8 * scrape / (np.abs(scrape).max() + 1e-9) + 0.5 * ring


def pang():
    d = 0.45
    n = int(d * SR)
    x = t(d)
    thump = np.sin(2 * np.pi * (180 * np.exp(-x / 0.05) + 55) * x) * env(n, 0.001, 0.09)
    burst = bandnoise(n, 800, 7000) * env(n, 0.0008, 0.05)
    return thump + 0.7 * burst


def dingring():
    d = 0.9
    x = t(d)
    def bell(f, start):
        y = np.zeros_like(x)
        m = x >= start
        xx = x[m] - start
        y[m] = (np.sin(2 * np.pi * f * xx) + 0.35 * np.sin(2 * np.pi * f * 2.76 * xx) + 0.15 * np.sin(2 * np.pi * f * 5.4 * xx)) \
            * np.minimum(1, xx / 0.003) * np.exp(-xx / 0.32)
        return y
    return bell(1319, 0) + bell(1760, 0.13)          # E6 → A6 "띠-링"


def sparkle():
    # 뾰로롱 — 빠르게 올라가는 반짝 아르페지오 + 은은한 꼬리
    d = 1.0
    x = t(d)
    y = np.zeros_like(x)
    notes = [1047, 1319, 1568, 2093, 2637, 3136]       # C6 E6 G6 C7 E7 G7
    for i, f in enumerate(notes):
        st = i * 0.055
        m = x >= st
        xx = x[m] - st
        y[m] += (np.sin(2 * np.pi * f * xx) + 0.3 * np.sin(2 * np.pi * f * 2 * xx + 0.5)) \
            * np.minimum(1, xx / 0.002) * np.exp(-xx / 0.22) * (0.7 + 0.06 * i)
    shimmer = bandnoise(len(x), 6000, 12000) * 0.08 * np.exp(-x / 0.4) * np.minimum(1, x / 0.1)
    return y + shimmer


def qping():
    # 물음표 핑 "띵-딩" — 짧고 높은 두 음 + 살짝 올라가는 꼬리(게임 핑 느낌의 자체 합성)
    d = 0.5
    x = t(d)
    y = np.zeros_like(x)
    for f, st, dec in ((1568, 0.0, 0.09), (2349, 0.085, 0.16)):
        m = x >= st
        xx = x[m] - st
        bend = f * (1 + 0.02 * np.minimum(1, xx / 0.05))
        y[m] += (np.sin(2 * np.pi * bend * xx) + 0.25 * np.sin(2 * np.pi * bend * 3 * xx)) \
            * np.minimum(1, xx / 0.002) * np.exp(-xx / dec)
    return y


def save(name, y):
    y = y / (np.abs(y).max() + 1e-9) * 0.9
    out = os.path.join(ROOT, "assets", "sfx", f"{name}.wav")
    pcm = (np.clip(y, -1, 1) * 32767).astype(np.int16).tobytes()
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "s16le", "-ar", str(SR), "-ac", "1", "-i", "-", out],
                   input=pcm, check=True)
    print("✓", out, f"{len(y) / SR:.2f}s")


if __name__ == "__main__":
    for name, fn in (("click", click), ("knife", knife), ("pang", pang), ("dingring", dingring), ("sparkle", sparkle), ("qping", qping)):
        save(name, fn())
