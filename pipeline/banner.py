#!/usr/bin/env python3
"""채널 배너 생성 — 휴지 판사가 재판하는 법정 장면.

유튜브 배너는 기기마다 보이는 범위가 다르다. **캐릭터도 텍스트도 전부**
안전영역(1235x338, 가운데) 안에 들어와야 한다. 2026-09-18 개정 전에는
마스코트를 일부러 안전영역 바깥에 뒀는데, 모바일에서 노란 배경에 글씨만
남아 "다 짤렸다"는 지적을 받았다. 이제는 안쪽에 넣는다.

    2048 x 1152   전체 (TV)
    2048 x  423   데스크톱
    1235 x  338   안전영역 — 모바일에서 보이는 전부

원본 장면은 codex-image 로 만든 `assets/court.png`(1536x864, 위아래를 비운
프레이밍)이다. 캐릭터+법대만 키로 떼어 안전영역 안에 앉히고, 벽/바닥은
빈 구간을 늘려 배너 크기를 채운다.

사용: python3 pipeline/banner.py
산출: assets/banner.png
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import layout as L

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "assets", "court.png")

W, H = 2048, 1152
SAFE_W, SAFE_H = 1235, 338
SAFE_X, SAFE_Y = (W - SAFE_W) // 2, (H - SAFE_H) // 2   # 406, 407

FLOOR_Y = 730            # 배너에서 벽/바닥 경계 (안전영역 아래끝 745 보다 위)
CHAR_H = 290             # 캐릭터+법대 높이 — 안전영역(338) 안에 여유 있게
CHAR_X = 470             # 캐릭터 왼쪽 시작 (안전영역 406 보다 안쪽)

# 원본(assets/court.png) 측정값
SRC_FLOOR = 611
SRC_CHAR = (246, 238, 700, 611)   # 캐릭터 + 법대, 바닥선까지
SRC_EMPTY = (1000, 1500)          # 벽/바닥을 늘려 쓸 빈 구간 x 범위

INK = (74, 38, 115)       # 캐릭터 눈 색 계열 진보라 — 채널명
INK_SUB = (120, 82, 40)   # 노랑 위에서 읽히는 갈색 — 부제

NAME = "법푸는휴지"
TAGLINE = "법 하나로 판이 뒤집힘"
SUBLINE = "노쇼 · 갑질 · 환불 · 층간소음  |  40초"


def fit(path, text, max_w, cap):
    path = os.path.join(ROOT, path)
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


def background(src):
    """빈 벽/바닥 구간을 늘려 2048x1152 배경을 만든다."""
    x0, x1 = SRC_EMPTY
    wall = src.crop((x0, 0, x1, SRC_FLOOR)).resize((W, FLOOR_Y), Image.LANCZOS)
    floor = src.crop((x0, SRC_FLOOR, x1, src.height)).resize((W, H - FLOOR_Y), Image.LANCZOS)
    bg = Image.new("RGB", (W, H))
    bg.paste(wall, (0, 0))
    bg.paste(floor, (0, FLOOR_Y))
    return bg


def cutout(src):
    """캐릭터+법대를 벽 색으로 키잉해 알파로 떼어낸다."""
    crop = src.crop(SRC_CHAR)
    wall = src.getpixel((SRC_EMPTY[0], 200))
    out = crop.convert("RGBA")
    px = out.load()
    w, h = out.size
    for y in range(h):
        for x in range(w):
            r, g, b, _ = px[x, y]
            if abs(r - wall[0]) + abs(g - wall[1]) + abs(b - wall[2]) < 60:
                px[x, y] = (r, g, b, 0)
    nw = int(round(w * CHAR_H / h))
    return out.resize((nw, CHAR_H), Image.LANCZOS)


def main() -> int:
    src = Image.open(SRC).convert("RGB")
    canvas = background(src).convert("RGBA")

    char = cutout(src)
    canvas.alpha_composite(char, (CHAR_X, FLOOR_Y - CHAR_H))

    d = ImageDraw.Draw(canvas)

    tx0 = CHAR_X + char.width + 70
    tx1 = SAFE_X + SAFE_W - 20
    cx = (tx0 + tx1) // 2
    max_w = tx1 - tx0

    f_name = fit(L.F_TITLE, NAME, int(max_w * 0.95), 150)
    f_tag = fit(L.F_TITLE, TAGLINE, int(max_w * 0.80), 52)
    f_sub = fit(L.F_BAR, SUBLINE, int(max_w * 0.78), 34)

    GAP1, GAP2 = 24, 16
    lines = [(NAME, f_name, INK), (TAGLINE, f_tag, INK_SUB), (SUBLINE, f_sub, INK_SUB)]
    heights = [f.getbbox(t)[3] - f.getbbox(t)[1] for t, f, _ in lines]
    block = sum(heights) + GAP1 + GAP2

    y = SAFE_Y + (SAFE_H - block) // 2
    for (text, f, color), gap in zip(lines, (GAP1, GAP2, 0)):
        y += center(d, cx, y, text, f, color) + gap

    out = os.path.join(ROOT, "assets", "banner.png")
    canvas.convert("RGB").save(out, quality=95)
    print(f"저장 {out}  ({W}x{H})")

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
