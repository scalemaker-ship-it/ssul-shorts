#!/usr/bin/env python3
"""커뮤니티 게시물용 「알아두면 손해 안 보는 법」 캐러셀 카드(1080×1080, 4~5장).

    python3 pipeline/card.py cards/<slug>/card.json   → cards/<slug>/01.png …

card.json:
{ "bg": "bg.png",                       # 앞장 배경(생성 이미지), card.json 기준 상대경로
  "cover": ["택시가 승차거부할 때", "이렇게 말해보세요"],   # 앞장 후킹 문장(줄 단위)
  "cover_em": ["이렇게 말해보세요"],     # 노랑으로 칠할 줄
  "pages": [ { "head": "…", "lines": ["…"], "quote": "…", "em": ["…"] }, … ] }
"""
import json, os, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
F = lambda n, s: ImageFont.truetype(os.path.join(ROOT, "fonts", n), s)
TITLE, BODY, EM = "JalnanGothic.otf", "Pretendard-SemiBold.ttf", "BMEULJIROTTF.ttf"
W = H = 1080
PAD = 84
YEL, WHITE, BG, SUB = (251, 255, 86), (255, 255, 255), (18, 18, 22), (170, 170, 180)
TAG = "알아두면 손해 안 보는 법"
CH = "법푸는휴지"


def wrap(d, text, font, maxw):
    out, cur = [], ""
    for w in text.split(" "):
        t = (cur + " " + w).strip()
        if d.textlength(t, font=font) <= maxw:
            cur = t
        else:
            out.append(cur); cur = w
    out.append(cur)
    return out


def tag(d, y, dark=False):
    f = F(BODY, 34)
    tw = d.textlength(TAG, font=f)
    d.rounded_rectangle([PAD, y, PAD + tw + 44, y + 58], 29, fill=YEL)
    d.text((PAD + 22, y + 9), TAG, font=f, fill=(20, 20, 20))


def footer(d, i, n):
    f = F(BODY, 30)
    d.text((PAD, H - 78), f"@{CH}", font=f, fill=SUB)
    s = f"{i} / {n}"
    d.text((W - PAD - d.textlength(s, font=f), H - 78), s, font=f, fill=SUB)


def cover(spec, base, n):
    bg = Image.open(os.path.join(base, spec["bg"])).convert("RGB").resize((W, H))
    # 아래쪽을 어둡게 — 글자가 사진 위에서 읽히게
    shade = Image.new("L", (W, H))
    sd = ImageDraw.Draw(shade)
    for y in range(H):
        sd.line([(0, y), (W, y)], fill=int(90 + 150 * max(0, (y - H * 0.25) / (H * 0.75))))
    img = Image.composite(Image.new("RGB", (W, H), (0, 0, 0)), bg, shade)
    d = ImageDraw.Draw(img)
    tag(d, PAD)
    f = F(TITLE, 104)
    lines = spec["cover"]
    lh = 132
    nl = sum(len(wrap(d, ln, f, W - PAD * 2)) for ln in lines)
    y = H - 150 - lh * nl
    for ln in lines:
        col = YEL if ln in spec.get("cover_em", []) else WHITE
        for sub in wrap(d, ln, f, W - PAD * 2):
            d.text((PAD + 3, y + 4), sub, font=f, fill=(0, 0, 0))
            d.text((PAD, y), sub, font=f, fill=col)
            y += lh
    f2 = F(BODY, 32)
    d.text((PAD, H - 78), f"@{CH}", font=f2, fill=(220, 220, 220))
    s = "옆으로 넘겨보기 →"
    d.text((W - PAD - d.textlength(s, font=f2), H - 78), s, font=f2, fill=YEL)
    return img


def page(p, i, n):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    fh, fq, fb = F(TITLE, 84), F(EM, 60), F(BODY, 54)
    ops = []                                   # (y, kind, payload) — 높이 먼저 재고 가운데 정렬
    y = 0
    ops.append((y, "num", f"{i - 1:02d}")); y += 70
    for sub in wrap(d, p["head"], fh, W - PAD * 2):
        ops.append((y, "head", sub)); y += 104
    y += 40
    if p.get("quote"):
        ql = wrap(d, p["quote"], fq, W - PAD * 2 - 80)
        bh = 80 * len(ql) + 64
        ops.append((y, "quote", (ql, bh))); y += bh + 84
    for ln in p.get("lines", []):
        em = any(e in ln for e in p.get("em", []))
        num = ln[:1] in "①②③④⑤→"
        subs = wrap(d, ln, fb, W - PAD * 2 - (0 if num else 44))
        for k, sub in enumerate(subs):
            ops.append((y, "line", (sub, em, num, k))); y += 74
        y += 26
    top = max(PAD, (H - 90 - y) // 2)
    for oy, kind, v in ops:
        yy = top + oy
        if kind == "num":
            d.text((PAD, yy), v, font=F(TITLE, 46), fill=YEL)
        elif kind == "head":
            d.text((PAD, yy), v, font=fh, fill=WHITE)
        elif kind == "quote":
            ql, bh = v
            d.rounded_rectangle([PAD, yy, W - PAD, yy + bh], 30, fill=YEL)
            d.polygon([(PAD + 70, yy + bh), (PAD + 124, yy + bh), (PAD + 58, yy + bh + 44)], fill=YEL)
            for k, q in enumerate(ql):
                d.text((PAD + 40, yy + 32 + 80 * k), q, font=fq, fill=(20, 20, 20))
        else:
            sub, em, num, k = v
            x = PAD if num else PAD + 44
            if k == 0 and not num:
                d.text((PAD, yy), "·", font=fb, fill=YEL)
            if num and k > 0:
                x = PAD + 58
            d.text((x, yy), sub, font=fb, fill=YEL if em else WHITE)
    footer(d, i, n)
    return img


def main(path):
    spec = json.load(open(path))
    base = os.path.dirname(os.path.abspath(path))
    n = 1 + len(spec["pages"])
    imgs = [cover(spec, base, n)] + [page(p, k + 2, n) for k, p in enumerate(spec["pages"])]
    for k, im in enumerate(imgs, 1):
        out = os.path.join(base, f"{k:02d}.png")
        im.save(out)
        print(out)


if __name__ == "__main__":
    main(sys.argv[1])
