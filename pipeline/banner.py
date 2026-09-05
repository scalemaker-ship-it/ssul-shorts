#!/usr/bin/env python3
"""채널 배너 생성 — 캐릭터 + 휴지 마스코트 조합.

유튜브 배너는 기기마다 보이는 범위가 다르다. 텍스트는 반드시 안전영역
(1235x338, 가운데 정렬) 안에 두고, 장식은 그 바깥으로 흘린다.

    2048 x 1152   전체 (TV)
    2048 x  423   데스크톱
    1235 x  338   안전영역 — 모바일에서 보이는 전부

사용: python3 pipeline/banner.py
산출: assets/banner.png
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import layout as L

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

W, H = 2048, 1152
SAFE_W, SAFE_H = 1235, 338
SAFE_X, SAFE_Y = (W - SAFE_W) // 2, (H - SAFE_H) // 2

BG      = (253, 209, 104)      # #FDD168 — 프로필과 같은 브랜드 노랑
INK     = (74, 38, 115)        # 캐릭터 머리색 계열 진보라 — 제목
INK_SUB = (120, 82, 40)        # 노랑 위에서 읽히는 갈색 — 부제
STREAK  = (255, 240, 190)      # 배경 사선 빛줄기 (캐릭터 원본 배경과 같은 결)

NAME    = "썰푸는휴지"
TAGLINE = "어 나도 그런데, 싶은 것들"
SUBLINE = "심리 · 관계 · 요즘 사회  |  30초"


def fit(path, text, max_w, cap):
    """max_w 를 넘지 않는 최대 폰트 크기를 찾는다."""
    lo, hi, best = 12, cap, 12
    while lo <= hi:
        mid = (lo + hi) // 2
        f = ImageFont.truetype(path, mid)
        b = f.getbbox(text)
        if b[2] - b[0] <= max_w:
            best, lo = mid, mid + 1
        else:
            hi = mid - 1
    return ImageFont.truetype(path, best)


def center(d, cx, y, text, f, fill):
    b = f.getbbox(text)
    d.text((cx - (b[2] - b[0]) / 2 - b[0], y - b[1]), text, font=f, fill=fill)
    return b[3] - b[1]


def paste_h(canvas, path, height, cx, cy):
    """이미지를 height 픽셀 높이로 맞춰 (cx, cy) 중심에 얹는다."""
    img = Image.open(path).convert("RGBA")
    w = int(img.width * height / img.height)
    img = img.resize((w, height), Image.LANCZOS)
    canvas.alpha_composite(img, (int(cx - w / 2), int(cy - height / 2)))


def main() -> int:
    canvas = Image.new("RGBA", (W, H), BG + (255,))
    d = ImageDraw.Draw(canvas)

    # 배경 사선 — 캐릭터 원본 배경에 있던 결을 그대로 살린다
    for i, (x0, y0, ln, wd) in enumerate(
        [(1500, 60, 320, 9), (1600, 150, 240, 6), (250, 830, 300, 9), (170, 940, 210, 6)]
    ):
        d.line([(x0, y0), (x0 + ln, y0 - ln)], fill=STREAK, width=wd)

    # 마스코트 — 안전영역을 침범하지 않게 바깥으로 뺀다.
    # 모바일에서는 안 보이고 데스크톱/TV 에서만 보인다.
    paste_h(canvas, os.path.join(ROOT, "assets", "tissue.png"), 520, 215, H // 2 + 10)
    paste_h(canvas, os.path.join(ROOT, "assets", "character.png"), 720, 1855, H // 2 + 80)

    # 텍스트 — 세 줄 전부 안전영역 안에 들어오도록 높이를 먼저 재고 수직 중앙 정렬
    cx = W // 2
    f_name = fit(L.F_TITLE, NAME, int(SAFE_W * 0.58), 140)
    f_tag = fit(L.F_TITLE, TAGLINE, int(SAFE_W * 0.52), 48)
    f_sub = fit(L.F_BAR, SUBLINE, int(SAFE_W * 0.46), 32)

    GAP1, GAP2 = 22, 14
    lines = [(NAME, f_name, INK), (TAGLINE, f_tag, INK_SUB), (SUBLINE, f_sub, INK_SUB)]
    heights = [f.getbbox(t)[3] - f.getbbox(t)[1] for t, f, _ in lines]
    block = sum(heights) + GAP1 + GAP2

    y = SAFE_Y + (SAFE_H - block) // 2
    for (text, f, color), gap in zip(lines, (GAP1, GAP2, 0)):
        y += center(d, cx, y, text, f, color) + gap

    out = os.path.join(ROOT, "assets", "banner.png")
    canvas.convert("RGB").save(out, quality=95)
    print(f"저장 {out}  ({W}x{H})")

    # 기기별로 어떻게 잘리는지 미리보기
    prev = os.path.join(ROOT, "codex-images")
    os.makedirs(prev, exist_ok=True)
    canvas.crop((0, (H - 423) // 2, W, (H + 423) // 2)).convert("RGB").save(
        os.path.join(prev, "_preview-banner-desktop.png")
    )
    canvas.crop((SAFE_X, SAFE_Y, SAFE_X + SAFE_W, SAFE_Y + SAFE_H)).convert("RGB").save(
        os.path.join(prev, "_preview-banner-safe.png")
    )
    print("미리보기: codex-images/_preview-banner-desktop.png, _preview-banner-safe.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
