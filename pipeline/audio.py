#!/usr/bin/env python3
"""오디오 마감 — build.py 가 쓰는 나레이션 마감 체인.

완급(PACING)은 2026-08-19 에 넣었다가 **되돌렸다**. 아래 PLAN 은 껐지만 남겨 둔다.

왜 필요했나 (2026-08-19 측정):
  · 완성본 라우드니스가 -25.5 LUFS 였다. 유튜브 기준은 -14 LUFS 이고 유튜브는
    큰 소리만 줄이고 작은 소리는 올려주지 않는다 → 피드에서 우리 것만 작게 들렸다.
  · 1.4배속 후 8.5자/초. 앵커가 5~6자/초, 빠른 유튜브 나레이션이 7자/초다.
  · 문장 간격 0.03초(배속 후 0.02초) → 문장 경계가 안 들렸다.
  · 타입캐스트 emotion 파라미터는 같은 문장 기준 toneup 313.7Hz / tonedown 307.7Hz,
    happy 와 sad 는 완전히 동일(320.0Hz)이었다. 감정 라벨로는 억양이 안 갈린다.
    → 그래서 '감정' 대신 '문장 역할별 완급'으로 리듬을 만든다.
"""
import re

# ── 완급 — 기본 꺼짐 ────────────────────────────────────────────
# True 로 바꾸면 문장 역할마다 배속과 쉼을 다르게 준다. 2026-08-19 에 한 번
# 켜 봤는데 "스피드가 별로"라는 판단이라 껐다. 되살릴 때는 layout.py 의
# SPEED 를 1.0 으로 같이 내려야 한다 — 안 그러면 이중으로 걸린다.
PACING = False

# 역할 → (그 문장 배속, 문장 뒤 쉼 초)
PLAN = {
    "hook":    (1.12, 0.30),   # 훅. 첫 문장은 또박또박
    "reveal":  (0.95, 0.42),   # 명칭 공개. 제일 느리게 + 뒤에 여백
    "stat":    (1.18, 0.24),   # 수치. 숫자는 흘리면 안 들린다
    "turn":    (1.10, 0.30),   # 반전
    "exclaim": (1.00, 0.34),   # 와, 헐
    "outro":   (1.02, 0.26),   # 마지막 여운
    "body":    (1.34, 0.10),   # 나열·설명. 여기서 시간을 번다
}

# 감탄 문장 앞에는 한 박자 쉬어준다 (앞 문장의 gap 에 더한다)
PRE_EXCLAIM_PAUSE = 0.18

# 마지막 문장 뒤 쉼 상한 — 뒤에 아무것도 없으니 여백을 길게 둘 이유가 없다
TAIL_GAP = 0.20

# 폰 스피커에서 또렷하게 → 작은 소리 끌어올리기 → 유튜브 기준 음량
POST_CHAIN = (
    "highpass=f=90,"                                    # 저역 웅웅거림
    "equalizer=f=250:t=q:w=1.0:g=-2,"                   # 먹먹함
    "equalizer=f=3000:t=q:w=1.2:g=4,"                   # 자음 또렷하게
    "acompressor=threshold=-20dB:ratio=3:attack=8:release=140:makeup=2,"
    "loudnorm=I=-14:TP=-1.5:LRA=11,"                    # 유튜브 기준
    # loudnorm 은 192kHz 로 뱉는다. 그대로 두면 AAC 가 96kHz 로 잡혀
    # 이전 편들(44.1kHz)과 규격이 어긋난다. 여기서 되돌린다.
    "aresample=44100"
)


def role(text, idx, total):
    t = (text or "").strip()

    if t.endswith("?"):
        return "hook" if idx == 0 else "turn"
    if t.endswith("!"):
        return "exclaim"
    if re.match(r"^(와|헐|진짜)[.…, ]", t):
        return "exclaim"

    # 반전 — 짧은 문장이어도 반전이면 반전이다. 명칭공개보다 먼저 본다.
    if re.match(r"^(근데|무서운 건|웃긴 건|사실|문제는|이유는|이런)", t):
        return "turn"
    if t.endswith("아니라") or t.endswith("아님.") or t.endswith("만은 아님."):
        return "turn"

    # 명칭 공개 — '○○이라고 불렸음/하는데/함', 또는 짧은 단독 명사문
    if re.search(r"(이|라)고\s*(불렸음|하는데|함|부름)", t):
        return "reveal"
    body = t.rstrip(".…")
    if len(body) <= 10 and len(body.split()) <= 3 and not re.search(r"\d", t) \
            and t.endswith("."):
        return "reveal"

    # 수치
    if re.search(r"\d+\s*(%|배|명|개|년|만|천|억|분|줄|통)", t):
        return "stat"

    if idx == total - 1:
        return "outro"
    return "body"


def pace(lines):
    """문장 리스트 → [(role, speed, gap)] . 감탄 앞 쉼까지 반영한 최종 값."""
    n = len(lines)
    roles = [role(t, i, n) for i, t in enumerate(lines)]
    out = []
    for i, r in enumerate(roles):
        sp, gap = PLAN[r]
        if i + 1 < n and roles[i + 1] == "exclaim":
            gap += PRE_EXCLAIM_PAUSE
        if i == n - 1:
            gap = min(gap, TAIL_GAP)   # 마지막 문장 뒤는 영상이 끝난다. 길게 둘 필요 없다
        out.append((r, sp, gap))
    return out
