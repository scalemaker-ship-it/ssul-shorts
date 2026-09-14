#!/usr/bin/env python3
"""효과음 뱅크 — 코드로 합성해 assets/sfx/<이름>.wav 를 만든다 (라이선스 문제 없음).

script.json 의 각 줄에 "sfx": "<이름>" 을 주면 build.py 가 그 문장이 **시작하는
시각**에 원속도로 얹는다. "shake": true 면 그 순간 화면이 흔들린다
(두둥·엥 은 자동으로 흔들림 포함). 2026-09-14 사용자 지시.

이름          쓰임
  dudung      황당한 사실·폭탄 발언 — 낮은 "두-둥" 두 방 (+흔들림)
  eng         어이없는 상황 — "엥?" 하듯 끝이 올라가는 짧은 톤 (+흔들림)
  ding        발견·규정 공개 — 맑은 "띠링"
  whoosh      장면 전환·시간 경과 — "휘익"
  cash        돈·금액·결제 — 계산대 "띠링-철컥"
  siren       경찰·견인·단속 — 짧은 "삐뽀" 두 번
  boing       코믹 반전 — 튕기는 "뿅"
  thud        문 닫힘·몰락·판결 — 둔탁한 한 방
  tick        긴장·대기 — 시계 "똑딱"
  pop         가벼운 강조 — 짧은 "톡"

사용: python3 pipeline/sfx.py            # 전부 생성
      python3 pipeline/sfx.py --play dudung
"""
import os, sys, wave, struct
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "sfx")
SR = 44100

# 흔들림이 기본으로 따라붙는 효과음
SHAKE_DEFAULT = {"dudung", "eng", "thud"}


def env(n, a=0.005, d=0.1, s=0.0, r=0.1, hold=0.0):
    """ADSR 봉투. n 샘플."""
    t = np.arange(n) / SR
    total = n / SR
    e = np.zeros(n)
    A, D, R = a, d, r
    H = max(0.0, total - A - D - R - hold)
    for i, x in enumerate(t):
        if x < A:
            e[i] = x / A
        elif x < A + D:
            e[i] = 1 - (1 - s) * (x - A) / D
        elif x < total - R:
            e[i] = s if hold or H else s
        else:
            e[i] = s * max(0.0, (total - x) / R)
    return e


def tone(freq, dur, wave_fn=np.sin, sweep_to=None, vib=0.0):
    n = int(SR * dur)
    t = np.arange(n) / SR
    if sweep_to is None:
        ph = 2 * np.pi * freq * t
    else:
        f = np.linspace(freq, sweep_to, n)
        ph = 2 * np.pi * np.cumsum(f) / SR
    if vib:
        ph = ph + vib * np.sin(2 * np.pi * 6 * t)
    return wave_fn(ph)


def noise(dur):
    return np.random.default_rng(7).uniform(-1, 1, int(SR * dur))


def lowpass(x, cutoff):
    # 1차 IIR — 간단한 저역 통과
    rc = 1 / (2 * np.pi * cutoff)
    a = (1 / SR) / (rc + 1 / SR)
    y = np.zeros_like(x)
    acc = 0.0
    for i, v in enumerate(x):
        acc += a * (v - acc)
        y[i] = acc
    return y


def mix(*parts):
    n = max(len(p) for p in parts)
    out = np.zeros(n)
    for p in parts:
        out[:len(p)] += p
    return out


def delay(x, sec):
    return np.concatenate([np.zeros(int(SR * sec)), x])


def norm(x, peak=0.9):
    m = np.max(np.abs(x)) or 1.0
    return x / m * peak


def save(name, x):
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, f"{name}.wav")
    x = np.clip(norm(x), -1, 1)
    with wave.open(p, "w") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(struct.pack("<%dh" % len(x), *(x * 32767).astype(np.int16)))
    return p


def hit(freq, dur, punch=1.0):
    """낮은 타격음 — 피치가 급히 떨어지는 사인 + 노이즈 클릭."""
    body = tone(freq * 2.2, dur, sweep_to=freq * 0.6) * env(int(SR * dur), 0.002, dur * 0.5, 0.15, dur * 0.4)
    click = lowpass(noise(0.03), 1800) * env(int(SR * 0.03), 0.001, 0.02, 0, 0.008) * 0.5 * punch
    return mix(body, click)


def make_all():
    made = {}
    # 두둥 — 55Hz 한 방 + 0.22초 뒤 더 큰 한 방, 긴 꼬리
    made["dudung"] = mix(hit(60, 0.55) * 0.8, delay(hit(52, 0.9, 1.3), 0.22))
    # 엥? — 520→980Hz 로 급히 올라가는 톤, 비브라토, 짧게
    e = tone(520, 0.28, sweep_to=980, vib=0.35) * env(int(SR * 0.28), 0.01, 0.05, 0.7, 0.08)
    e2 = tone(1040, 0.28, sweep_to=1960, vib=0.35) * env(int(SR * 0.28), 0.01, 0.05, 0.4, 0.08) * 0.25
    made["eng"] = mix(e, e2)
    # 띠링 — 1319Hz + 1760Hz 두 종
    d1 = tone(1319, 0.5) * env(int(SR * 0.5), 0.002, 0.3, 0.2, 0.2)
    d2 = tone(1760, 0.6) * env(int(SR * 0.6), 0.002, 0.35, 0.2, 0.25)
    made["ding"] = mix(d1, delay(d2, 0.09))
    # 휘익 — 노이즈에 저역 통과 컷오프를 쓸어올리는 느낌 (두 구간 합성)
    w = noise(0.45)
    wa = lowpass(w, 600) * env(int(SR * 0.45), 0.05, 0.1, 0.8, 0.25)
    wb = lowpass(w, 3000) * env(int(SR * 0.45), 0.15, 0.1, 0.6, 0.15) * 0.6
    made["whoosh"] = mix(wa, wb)
    # 계산대 — 띠링 + 철컥(노이즈 클릭 두 번)
    c1 = tone(2093, 0.25) * env(int(SR * 0.25), 0.002, 0.15, 0.2, 0.08)
    c2 = tone(2637, 0.3) * env(int(SR * 0.3), 0.002, 0.18, 0.2, 0.1)
    k = lowpass(noise(0.04), 4000) * env(int(SR * 0.04), 0.001, 0.02, 0, 0.015)
    made["cash"] = mix(c1, delay(c2, 0.08), delay(k, 0.3), delay(k * 0.7, 0.36))
    # 삐뽀 — 880/660Hz 교대 두 번
    s = []
    for i, f in enumerate([880, 660, 880, 660]):
        s.append(delay(tone(f, 0.16, wave_fn=lambda p: np.sign(np.sin(p)) * 0.4 + np.sin(p) * 0.6)
                       * env(int(SR * 0.16), 0.005, 0.02, 0.9, 0.03), 0.17 * i))
    made["siren"] = mix(*s)
    # 뿅 — 급강하 톤 + 되튐
    b = tone(900, 0.22, sweep_to=180) * env(int(SR * 0.22), 0.002, 0.08, 0.5, 0.1)
    b2 = tone(300, 0.15, sweep_to=520, vib=0.5) * env(int(SR * 0.15), 0.005, 0.05, 0.5, 0.08) * 0.5
    made["boing"] = mix(b, delay(b2, 0.2))
    # 둔탁한 한 방
    made["thud"] = hit(48, 0.7, 1.4)
    # 똑딱
    tk = lowpass(noise(0.02), 5000) * env(int(SR * 0.02), 0.001, 0.01, 0, 0.008)
    made["tick"] = mix(tk, delay(tk * 0.7, 0.35))
    # 톡
    made["pop"] = tone(700, 0.08, sweep_to=350) * env(int(SR * 0.08), 0.001, 0.03, 0.3, 0.04)

    for name, x in made.items():
        save(name, x)
    return sorted(made)


if __name__ == "__main__":
    names = make_all()
    print(f"✓ 효과음 {len(names)}개 → {OUT}: {', '.join(names)}")
    if "--play" in sys.argv:
        import subprocess
        n = sys.argv[sys.argv.index("--play") + 1]
        subprocess.run(["afplay", os.path.join(OUT, f"{n}.wav")])
