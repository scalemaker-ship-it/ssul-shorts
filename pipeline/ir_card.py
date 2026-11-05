#!/usr/bin/env python3
"""いらすとや 카드 이미지 — codex 이미지가 막혔을 때의 대체 이미지(2026-10-19).

  python3 pipeline/ir_card.py <slug>      # work/<slug>/cards.json → work/<slug>/img/01.png ...

cards.json = [ {
   "bg": "#FFE9A8",                              # 배경색(부드러운 방사형 그라데이션)
   "ir": [["stem", cx, h], ["stem", cx, h, true]], # work/_ir_lotto/cand/<stem>.png, cx=가로 중심(0~1), h=높이 비율, true=좌우반전
   "draw": ["balls"|"slip"],                     # 직접 그리는 소품(로또 공 6개 / 로또 용지)
   "label": "18억 대신 수령", "label_color": "#E53935",
   "law": ["형법 제355조", "횡령죄"]              # 있으면 검은 화면 흰 글씨 법조항 컷
 }, ... ]
いらすとや 무료 조건: 한 편 20장 이하 — 서로 다른 stem 수를 세서 넘으면 중단.
"""
import json, os, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAND = os.path.join(ROOT, "work", "_ir_lotto", "cand")
FONT = os.path.join(ROOT, "assets", "fonts", "JalnanGothic.otf")
W, H = 1080, 835   # render.py 이미지 영역(CONTENT 0.275~0.710)과 같은 비율
BALL_C = [(251, 196, 0), (105, 200, 242), (255, 114, 114), (170, 170, 170), (176, 216, 64)]  # 1~10,11~20,21~30,31~40,41~45


def hexrgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def background(col):
    c = hexrgb(col)
    im = Image.new("RGB", (W, H), c)
    glow = Image.new("L", (W, H), 0)
    ImageDraw.Draw(glow).ellipse((W * 0.1, H * 0.05, W * 0.9, H * 1.2), fill=255)
    glow = glow.filter(ImageFilter.GaussianBlur(120))
    light = Image.new("RGB", (W, H), tuple(min(255, int(v + (255 - v) * 0.6)) for v in c))
    return Image.composite(light, im, glow).convert("RGBA")


def outline(im, w=14):
    pad = w + 4
    c = Image.new("RGBA", (im.width + 2 * pad, im.height + 2 * pad), (0, 0, 0, 0))
    c.paste(im, (pad, pad), im)
    a = c.getchannel("A").point(lambda v: 255 if v > 40 else 0).filter(ImageFilter.MaxFilter(w | 1))
    out = Image.composite(Image.new("RGBA", c.size, (255, 255, 255, 255)), Image.new("RGBA", c.size, (0, 0, 0, 0)), a)
    out.alpha_composite(c)
    return out


def place_ir(canvas, stem, cx, h, flip=False, cy=None):
    im = Image.open(os.path.join(CAND, stem + ".png")).convert("RGBA")
    bbox = im.getbbox()
    im = im.crop(bbox)
    if flip:
        im = im.transpose(Image.FLIP_LEFT_RIGHT)
    th = int(H * h)
    im = im.resize((max(1, int(im.width * th / im.height)), th), Image.LANCZOS)
    im = outline(im)
    x = int(W * cx - im.width / 2)
    y = H - im.height + 10 if cy is None else int(H * cy - im.height / 2)
    canvas.alpha_composite(im, (x, y))


def balls(canvas, nums=(3, 11, 24, 33, 41, 45), y=None):
    d = ImageDraw.Draw(canvas)
    f = ImageFont.truetype(FONT, 58)
    r = 66
    y = y or int(H * 0.30)
    gap = 160
    x0 = W / 2 - gap * (len(nums) - 1) / 2
    for i, n in enumerate(nums):
        c = BALL_C[min((n - 1) // 10, 4)]
        x = x0 + i * gap
        d.ellipse((x - r - 5, y - r - 5, x + r + 5, y + r + 5), fill=(255, 255, 255))
        d.ellipse((x - r, y - r, x + r, y + r), fill=c)
        d.ellipse((x - r * 0.55, y - r * 0.75, x - r * 0.05, y - r * 0.35), fill=tuple(min(255, v + 60) for v in c))
        d.text((x, y + 2), str(n), font=f, anchor="mm", fill=(255, 255, 255), stroke_width=4, stroke_fill=(60, 60, 60))


def slip(canvas, cx=0.5, cy=0.52, rot=-8):
    sw, sh = 420, 560
    s = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
    d = ImageDraw.Draw(s)
    d.rounded_rectangle((0, 0, sw - 1, sh - 1), 18, fill=(255, 253, 245), outline=(200, 60, 60), width=8)
    d.rectangle((8, 8, sw - 9, 92), fill=(220, 60, 60))
    d.text((sw / 2, 52), "로또 6/45", font=ImageFont.truetype(FONT, 56), anchor="mm", fill="white")
    f = ImageFont.truetype(FONT, 30)
    for row in range(5):
        for col in range(7):
            n = row * 7 + col + 1
            x, y = 42 + col * 56, 140 + row * 70
            hit = n in (3, 11, 24, 33)
            d.rectangle((x - 20, y - 22, x + 20, y + 22), outline=(220, 90, 90), width=3, fill=(40, 40, 40) if hit else None)
            d.text((x, y), str(n), font=f, anchor="mm", fill="white" if hit else (200, 70, 70))
    d.text((sw / 2, 515), "1,000원", font=ImageFont.truetype(FONT, 40), anchor="mm", fill=(120, 120, 120))
    s = s.rotate(rot, resample=Image.BICUBIC, expand=True)
    s = outline(s, 10)
    canvas.alpha_composite(s, (int(W * cx - s.width / 2), int(H * cy - s.height / 2)))


def label(canvas, text, color="#E53935"):
    f = ImageFont.truetype(FONT, 92)
    d = ImageDraw.Draw(canvas)
    while d.textlength(text, font=f) > W - 120 and f.size > 40:
        f = ImageFont.truetype(FONT, f.size - 4)
    d.text((W / 2, 92), text, font=f, anchor="mm", fill=hexrgb(color), stroke_width=12, stroke_fill=(255, 255, 255))


def law(lines):
    im = Image.new("RGBA", (W, H), (12, 12, 14, 255))
    d = ImageDraw.Draw(im)
    f1 = ImageFont.truetype(FONT, 70)
    f2 = ImageFont.truetype(FONT, 120)
    d.text((W / 2, H * 0.36), lines[0], font=f1, anchor="mm", fill=(200, 200, 200))
    big = lines[1]
    while d.textlength(big, font=f2) > W - 120:
        f2 = ImageFont.truetype(FONT, f2.size - 6)
    d.text((W / 2, H * 0.58), big, font=f2, anchor="mm", fill=(251, 255, 86))
    return im


def render(slug):
    wd = os.path.join(ROOT, "work", slug)
    cards = json.load(open(os.path.join(wd, "cards.json")))
    stems = {it[0] for c in cards for it in c.get("ir", [])}
    if len(stems) > 20:
        sys.exit(f"いらすとや {len(stems)}장 — 한 편 20장 초과(무료 조건)")
    os.makedirs(os.path.join(wd, "img"), exist_ok=True)
    for i, c in enumerate(cards, 1):
        if c.get("law"):
            im = law(c["law"])
        else:
            im = background(c.get("bg", "#FFF1C9"))
            for dr in c.get("draw", []):
                if dr == "balls":
                    balls(im)
                elif dr == "slip":
                    slip(im, *c.get("slip_at", (0.5, 0.52)))
            for it in c.get("ir", []):
                place_ir(im, it[0], it[1], it[2], flip=len(it) > 3 and it[3], cy=it[4] if len(it) > 4 else None)
            if c.get("label"):
                label(im, c["label"], c.get("label_color", "#E53935"))
        im.convert("RGB").save(os.path.join(wd, "img", f"{i:02d}.png"))
    print(f"✓ {slug}: 카드 {len(cards)}장 · いらすとや {len(stems)}종")


if __name__ == "__main__":
    for s in sys.argv[1:]:
        render(s)
