#!/usr/bin/env python3
"""[롱폼 2] 16:9 모션그래픽 렌더 — script.json + tts/timing.json → final.mp4

화면 구성 (1920x1080, 30fps)
  배경   : 줄마다 지정한 img 를 Ken Burns(천천히 줌·팬). 이미지가 바뀌면 줌 펀치 크로스페이드.
           카드형 그래픽이 뜨는 줄은 배경을 흐리게(초점 이동) 바꾼다.
  그래픽 : 줄의 "gfx" 타입별 모션그래픽(카운터·도장·타임라인·체크리스트 등). 같은 타입이
           이어지면 다시 등장하지 않고 상태만 바뀐다(타임라인 점등, 체크 추가 등).
  고정   : 좌상단 챕터 태그, 우상단 채널명, 하단 자막, 맨 아래 진행 바, 필름 그레인·비네트.
  효과음 : 그래픽 이벤트(도장·체크·질문 등)와 장면 전환에만. BGM 은 나레이션에 덕킹.

사용: python3 pipeline/long_build.py <slug> [--preview 0:20] [--no-open]
"""
import sys, os, json, math, random, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import audio

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W, H, FPS = 1920, 1080, 30
SR = 44100

F_BODY = os.path.join(ROOT, "fonts", "Pretendard-SemiBold.ttf")
F_MED = os.path.join(ROOT, "fonts", "Pretendard-Medium.ttf")
F_BIG = os.path.join(ROOT, "fonts", "JalnanGothic.otf")

WHITE = (255, 255, 255, 255)
SUB = (178, 188, 202, 255)
DIM = (120, 128, 140, 255)
YEL = (255, 196, 0, 255)
RED = (255, 75, 75, 255)
GRN = (52, 209, 122, 255)
PANEL = (16, 19, 26, 228)
BLACK = (10, 10, 12, 255)
CHANNEL = "법푸는휴지"

# 배경을 흐리게 깔 그래픽 타입 (카드가 주인공인 줄)
FOCUS_TYPES = {"question", "card", "law", "sms", "calc", "formula", "invoice",
               "check", "end", "rows3", "counter", "stamp", "title", "triangle", "clock",
               "pic", "vs", "bigtext", "web", "cup", "flow"}

_fc = {}
def font(path, size):
    k = (path, size)
    if k not in _fc:
        _fc[k] = ImageFont.truetype(path, size)
    return _fc[k]


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))

def eo(x):  # ease out cubic
    x = clamp(x); return 1 - (1 - x) ** 3

def eob(x):  # ease out back
    x = clamp(x); c1 = 1.70158; c3 = c1 + 1
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2

def eio(x):
    x = clamp(x); return 3 * x * x - 2 * x * x * x


def won(n):
    return f"{int(round(n)):,}"


def tw(text, f):
    return f.getlength(text)


def ctext(d, cx, y, text, f, fill, anchor="mt"):
    d.text((cx, y), text, font=f, fill=fill, anchor=anchor)


def panel(w, h, fill=PANEL, r=34, border=(255, 255, 255, 38)):
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w - 1, h - 1), r, fill=fill, outline=border, width=2)
    return im, d


def fade(im, a):
    if a >= 0.999:
        return im
    a = clamp(a)
    al = im.getchannel("A").point(lambda v: int(v * a))
    im = im.copy(); im.putalpha(al)
    return im


# ───────────────────────── 그래픽 타입 ─────────────────────────
# 모두 (g, lt, dur, cont) → RGBA 이미지. lt = 줄 시작부터 경과초, cont = 앞 줄과 같은 타입(이어짐)

def g_title(g, lt, dur, cont):
    im = Image.new("RGBA", (1600, 420), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    f1, f2 = font(F_BIG, 112), font(F_BIG, 84)
    a1, a2 = eo(lt / 0.45), eo((lt - 0.3) / 0.45)
    l1 = Image.new("RGBA", im.size, (0, 0, 0, 0)); ImageDraw.Draw(l1).text((800, 60), g["l1"], font=f1, fill=WHITE, anchor="mt", stroke_width=3, stroke_fill=(0, 0, 0, 200))
    im.alpha_composite(fade(l1, a1), (0, int(40 * (1 - a1))))
    l2 = Image.new("RGBA", im.size, (0, 0, 0, 0)); d2 = ImageDraw.Draw(l2)
    d2.text((800, 215), g["l2"], font=f2, fill=YEL, anchor="mt", stroke_width=3, stroke_fill=(0, 0, 0, 200))
    im.alpha_composite(fade(l2, a2), (0, int(40 * (1 - a2))))
    u = eio((lt - 0.7) / 0.5)
    if u > 0:
        wl = tw(g["l2"], f2)
        x0 = 800 - wl / 2
        d.rounded_rectangle((x0, 330, x0 + wl * u, 342), 6, fill=YEL)
    return im


def g_counter(g, lt, dur, cont):
    im, d = panel(1240, 400)
    ctext(d, 620, 48, g["label"], font(F_BODY, 44), SUB)
    delay = g.get("delay", 0.15)
    p = eo((lt - delay) / 1.1)
    v = g["from"] + (g["to"] - g["from"]) * p
    col = YEL if p >= 1 else WHITE
    fb = font(F_BIG, 132)
    txt = won(v) + g.get("unit", "")
    y = 150
    if g.get("strike_from"):
        fs = font(F_BIG, 56)
        s = won(g["from"]) + g.get("unit", "")
        ctext(d, 620, 128, s, fs, DIM)
        sw = tw(s, fs); k = eo((lt - 0.05) / 0.35)
        d.line((620 - sw / 2 - 8, 158, 620 - sw / 2 - 8 + (sw + 16) * k, 158), fill=RED, width=7)
        y = 205
    ctext(d, 620, y, txt, fb, col)
    return im


def g_stamp(g, lt, dur, cont):
    im = Image.new("RGBA", (1300, 560), (0, 0, 0, 0))
    t0 = 0.2
    if lt >= t0:
        k = clamp((lt - t0) / 0.18)
        s = 1.9 - 0.9 * eo(k)
        st = Image.new("RGBA", (900, 260), (0, 0, 0, 0)); d = ImageDraw.Draw(st)
        d.rounded_rectangle((8, 8, 891, 251), 30, outline=RED, width=12, fill=(255, 75, 75, 40))
        d.text((450, 130), g["big"], font=font(F_BIG, 150), fill=RED, anchor="mm")
        st = st.rotate(-6, expand=True, resample=Image.BICUBIC)
        st = st.resize((int(st.width * s), int(st.height * s)), Image.BILINEAR)
        st = fade(st, clamp(k * 3))
        im.alpha_composite(st, (650 - st.width // 2, 200 - st.height // 2))
    a = eo((lt - 0.6) / 0.4)
    if a > 0:
        l = Image.new("RGBA", im.size, (0, 0, 0, 0))
        ImageDraw.Draw(l).text((650, 440), g["small"], font=font(F_BIG, 64), fill=WHITE, anchor="mm")
        im.alpha_composite(fade(l, a))
    return im


def g_rows3(g, lt, dur, cont):
    rows = g["rows"]
    im = Image.new("RGBA", (1100, 480), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    f = font(F_BIG, 62)
    on = g.get("on", -1)
    for i, r in enumerate(rows):
        a = 1.0 if cont else eo((lt - i * 0.14) / 0.35)
        if a <= 0:
            continue
        y = 20 + i * 150 + int((1 - a) * 30)
        lit = g.get("all") and lt > 0.2 + i * 0.35 or i == on
        if g.get("all"):
            k = eo((lt - 0.2 - i * 0.35) / 0.25)
        else:
            k = eo(lt / 0.3) if i == on else 0
        fill = tuple(int(PANEL[j] + (YEL[j] - PANEL[j]) * k) for j in range(3)) + (int(228 * a),)
        tc = BLACK if k > 0.5 else (WHITE if on < 0 or g.get("all") else DIM)
        pad = int(18 * k)
        d.rounded_rectangle((60 - pad, y - pad // 2, 1040 + pad, y + 120 + pad // 2), 60, fill=fill,
                            outline=(255, 255, 255, int(40 * a)), width=2)
        d.text((550, y + 60), r, font=f, fill=tc[:3] + (int(255 * a),), anchor="mm")
        if i == on and not g.get("all"):
            pencil(im, ellipse_pts(550, y + 60, 490, 84, seed=i + 4), clamp((lt - 0.35) / 0.6), w=8)
    return im


def g_timeline(g, lt, dur, cont):
    pts = g["points"]; n = len(pts)
    im = Image.new("RGBA", (1700, 420), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((40, 60, 1660, 340), 34, fill=(12, 14, 20, 170))
    x0, x1, y = 150, 1550, 150
    xs = [x0 + (x1 - x0) * i / (n - 1) for i in range(n)]
    d.line((x0, y, x1, y), fill=(255, 255, 255, 70), width=8)
    frm, on = g.get("from", 0), g["on"]
    p = eo((lt - 0.1) / 0.9)
    lit = frm + (on - frm) * p            # 몇 번째 점까지 불이 들어왔나 (실수)
    if lit > 0:
        seg = lit - 1
        xe = xs[0] + (xs[-1] - xs[0]) * clamp(seg / (n - 1))
        d.line((x0, y, xe, y), fill=YEL, width=8)
    for i, x in enumerate(xs):
        k = clamp(lit - i)
        r = 18 + 8 * eob(k) if k > 0 else 16
        col = YEL if k > 0 else (90, 96, 108, 255)
        d.ellipse((x - r, y - r, x + r, y + r), fill=col, outline=(0, 0, 0, 180), width=3)
        for j, ln in enumerate(pts[i].split("\n")):
            f = font(F_BIG, 46) if j == 0 else font(F_BODY, 40)
            c = (WHITE if j == 0 else SUB) if k > 0 else DIM
            d.text((x, y + 50 + j * 60), ln, font=f, fill=c, anchor="mt", stroke_width=2, stroke_fill=(0, 0, 0, 160))
    return im


def g_bar(g, lt, dur, cont):
    im, d = panel(1560, 360)
    total = g["total"]; x0, x1, y0, y1 = 80, 1480, 170, 260
    d.rounded_rectangle((x0, y0, x1, y1), 20, fill=(255, 255, 255, 25))
    acc = 0
    for i, (lab, val, col) in enumerate(g["parts"]):
        k = eo((lt - 0.1 - i * 0.55) / 0.6)
        if k <= 0:
            break
        w = (x1 - x0) * val / total
        xa = x0 + (x1 - x0) * acc / total
        rgb = tuple(int(col[j:j + 2], 16) for j in (1, 3, 5)) + (255,)
        d.rounded_rectangle((xa, y0, xa + max(24, w * k), y1), 20, fill=rgb)
        la = eo((lt - 0.4 - i * 0.55) / 0.3)
        if la > 0:
            f = font(F_BIG, 44)
            cx = xa + w / 2
            d.text((cx, y0 - 30), lab, font=f, fill=rgb[:3] + (int(255 * la),), anchor="mb")
        acc += val
    d.text((780, 300), g.get("total_label", ""), font=font(F_BODY, 38), fill=SUB, anchor="mt")
    return im


def g_question(g, lt, dur, cont):
    im, d = panel(1420, 460, fill=(20, 22, 30, 238), border=(255, 196, 0, 140))
    k = eob(lt / 0.4)
    r = int(78 * clamp(k, 0, 1.2))
    d.ellipse((130 - r, 230 - r, 130 + r, 230 + r), fill=YEL)
    if lt > 0.1:
        d.text((130, 232), g["q"], font=font(F_BIG, 64), fill=BLACK, anchor="mm")
    lines = g["text"].split("\n")
    for i, ln in enumerate(lines):
        a = eo((lt - 0.15 - i * 0.15) / 0.35)
        if a <= 0:
            continue
        l = Image.new("RGBA", im.size, (0, 0, 0, 0))
        ImageDraw.Draw(l).text((260, 150 + i * 110), ln, font=font(F_BIG, 76), fill=WHITE, anchor="lt")
        im.alpha_composite(fade(l, a), (int(40 * (1 - a)), 0))
    return im


def _node(d, cx, cy, label, col):
    d.rounded_rectangle((cx - 150, cy - 55, cx + 150, cy + 55), 55, fill=(26, 30, 40, 240), outline=col, width=4)
    d.text((cx, cy), label, font=font(F_BIG, 52), fill=WHITE, anchor="mm")


def _dash(d, a, b, col, w=6, seg=22):
    L = math.dist(a, b); n = int(L // seg)
    for i in range(0, n, 2):
        p = (a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n)
        q = (a[0] + (b[0] - a[0]) * (i + 1) / n, a[1] + (b[1] - a[1]) * (i + 1) / n)
        d.line((p, q), fill=col, width=w)


def g_triangle(g, lt, dur, cont):
    im = Image.new("RGBA", (1500, 620), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    A, B, C = (330, 480), (1170, 480), (750, 110)     # 차주, 정비소, 보험사
    k = 1.0 if cont else eo(lt / 0.6)
    ax = A[0] + (B[0] - A[0]) * k
    d.line((A, (ax, A[1])), fill=YEL, width=8)
    d.text(((A[0] + B[0]) / 2, 440), "수리 의뢰", font=font(F_BODY, 40), fill=YEL, anchor="mb")
    if k > 0.6:
        _dash(d, C, B, (200, 206, 216, 255))
        d.text((1060, 230), "수리 계약?", font=font(F_BODY, 40), fill=SUB, anchor="lm")
        _dash(d, C, A, (120, 126, 136, 255))
        d.text((520, 230), "\"보험사한테 받으세요\"", font=font(F_BODY, 36), fill=DIM, anchor="rm")
    _node(d, *A, "차주", WHITE); _node(d, *B, "정비소", WHITE); _node(d, *C, "보험사", WHITE)
    if g.get("x"):
        x = eo((lt - 0.5) / 0.3)
        if x > 0:
            cx, cy, s = (C[0] + B[0]) / 2, (C[1] + B[1]) / 2, 62 * x
            d.line((cx - s, cy - s, cx + s, cy + s), fill=RED, width=16)
            d.line((cx - s, cy + s, cx + s, cy - s), fill=RED, width=16)
            if x > 0.9:
                d.text((cx + 90, cy + 30), "증거 없음", font=font(F_BIG, 46), fill=RED, anchor="lm")
    return im


def g_card(g, lt, dur, cont):
    lines = g["body"].split("\n")
    h = 190 + 88 * len(lines)
    im, d = panel(1360, h)
    d.text((80, 64), g["head"], font=font(F_BIG, 64), fill=YEL, anchor="lt")
    d.rounded_rectangle((80, 150, 80 + 160 * eo(lt / 0.4), 156), 3, fill=YEL)
    for i, ln in enumerate(lines):
        a = eo((lt - 0.25 - i * 0.3) / 0.35)
        if a <= 0:
            continue
        col = YEL if ln.startswith("→") else WHITE
        l = Image.new("RGBA", im.size, (0, 0, 0, 0))
        ImageDraw.Draw(l).text((80, 190 + i * 88), ln, font=font(F_BODY, 56), fill=col, anchor="lt")
        im.alpha_composite(fade(l, a), (int(30 * (1 - a)), 0))
        if ln.startswith("→"):
            pencil(im, underline_pts(130, 80 + tw(ln, font(F_BODY, 56)), 190 + i * 88 + 70, seed=i + 2),
                   clamp((lt - 0.55 - i * 0.3) / 0.45), w=8)
    return im


def g_law(g, lt, dur, cont):
    lines = g["body"].split("\n")
    h = 230 + 90 * len(lines)
    im, d = panel(1460, h, fill=(244, 241, 234, 245), border=(0, 0, 0, 0), r=18)
    d.rectangle((0, 0, 1460, 18), fill=(40, 60, 110, 255))
    d.text((80, 70), g["head"], font=font(F_BIG, 58), fill=(28, 40, 80, 255), anchor="lt")
    d.line((80, 160, 1380, 160), fill=(0, 0, 0, 60), width=3)
    for i, ln in enumerate(lines):
        a = 1.0 if cont else eo((lt - 0.2 - i * 0.3) / 0.35)
        if a > 0:
            d.text((80, 200 + i * 90), ln, font=font(F_BODY, 54), fill=(20, 22, 28, int(255 * a)), anchor="lt")
    if g.get("stamp"):
        k = clamp((lt - 0.3) / 0.18)
        if k > 0:
            s = 1.8 - 0.8 * eo(k)
            st = Image.new("RGBA", (760, 150), (0, 0, 0, 0)); sd = ImageDraw.Draw(st)
            sd.rounded_rectangle((6, 6, 753, 143), 20, outline=RED, width=9)
            sd.text((380, 76), g["stamp"], font=font(F_BIG, 58), fill=RED, anchor="mm")
            st = st.rotate(-5, expand=True, resample=Image.BICUBIC)
            st = st.resize((int(st.width * s), int(st.height * s)), Image.BILINEAR)
            big = Image.new("RGBA", (im.width + 400, im.height + 300), (0, 0, 0, 0))
            big.alpha_composite(im, (200, 150))
            big.alpha_composite(fade(st, clamp(k * 3)), (200 + 1100 - st.width // 2, 150 + h + 40 - st.height // 2))
            return big
    return im


def g_formula(g, lt, dur, cont):
    parts = g["parts"]
    f = font(F_BIG, 70)
    widths = [tw(p, f) + (90 if p not in "=×" else 20) for p in parts]
    total = sum(widths) + 30 * (len(parts) - 1)
    im = Image.new("RGBA", (int(total) + 60, 260), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    x = 30
    for i, (p, w) in enumerate(zip(parts, widths)):
        a = eob((lt - i * 0.15) / 0.35)
        if a > 0:
            hl = i == g.get("hl")
            y = 130 + int((1 - clamp(a)) * 40)
            if p not in "=×":
                fill = YEL if hl and lt > 0.9 else PANEL
                d.rounded_rectangle((x, y - 75, x + w, y + 75), 40, fill=fill, outline=(255, 255, 255, 50), width=2)
                d.text((x + w / 2, y), p, font=f, fill=BLACK if hl and lt > 0.9 else WHITE, anchor="mm")
            else:
                d.text((x + w / 2, y), p, font=f, fill=SUB, anchor="mm")
        x += w + 30
    return im


def g_calc(g, lt, dur, cont):
    rows = g["rows"]
    im, d = panel(1300, 150 + 110 * len(rows))
    for i, r in enumerate(rows):
        a = eo((lt - 0.2 - i * 0.55) / 0.35)
        if a <= 0:
            continue
        last = i == len(rows) - 1
        if last:
            d.line((80, 70 + i * 110, 1220, 70 + i * 110), fill=(255, 255, 255, int(90 * a)), width=3)
        f = font(F_BIG, 62) if last else font(F_BODY, 54)
        col = YEL if last else (WHITE if i == 0 else SUB)
        d.text((650 + int(20 * (1 - a)), 85 + i * 110 + (10 if last else 0)), r, font=f,
               fill=col[:3] + (int(255 * a),), anchor="mt")
    return im


def g_clock(g, lt, dur, cont):
    im = Image.new("RGBA", (1300, 560), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    cx, cy, R = 650, 220, 170
    d.ellipse((cx - R, cy - R, cx + R, cy + R), fill=(20, 24, 32, 235), outline=WHITE, width=8)
    for k in range(12):
        a = k * math.pi / 6
        r1 = R - 18 if k % 3 else R - 34
        d.line((cx + r1 * math.sin(a), cy - r1 * math.cos(a), cx + (R - 8) * math.sin(a), cy - (R - 8) * math.cos(a)),
               fill=SUB, width=6 if k % 3 == 0 else 3)
    p = eio((lt - 0.2) / 1.6)
    ang_m = math.radians(360 * 3 * (1 - p) + 60)       # 분침이 거꾸로 감기며 표준시간으로
    ang_h = math.radians(30 * 3 * (1 - p) + 100)
    d.line((cx, cy, cx + (R - 40) * math.sin(ang_m), cy - (R - 40) * math.cos(ang_m)), fill=YEL, width=10)
    d.line((cx, cy, cx + (R - 80) * math.sin(ang_h), cy - (R - 80) * math.cos(ang_h)), fill=WHITE, width=14)
    d.ellipse((cx - 14, cy - 14, cx + 14, cy + 14), fill=YEL)
    a = eo((lt - 0.5) / 0.4)
    l = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(l).text((650, 450), g["label"], font=font(F_BIG, 54), fill=WHITE, anchor="mt",
                           stroke_width=3, stroke_fill=(0, 0, 0, 200))
    im.alpha_composite(fade(l, a))
    return im


def g_invoice(g, lt, dur, cont):
    rows = g["rows"]
    h = 200 + 100 * len(rows)
    im, d = panel(1100, h, fill=(246, 244, 238, 250), border=(0, 0, 0, 0), r=14)
    d.text((70, 50), "정비명세서", font=font(F_BIG, 56), fill=(20, 22, 28, 255), anchor="lt")
    d.line((70, 135, 1030, 135), fill=(0, 0, 0, 120), width=3)
    f = font(F_BODY, 50)
    for i, r in enumerate(rows):
        y = 170 + i * 100
        for k, hi in enumerate(g.get("hl", [])):
            if hi == i:
                p = eio((lt - 0.3 - k * 0.35) / 0.35)
                if p > 0:
                    d.rounded_rectangle((55, y - 6, 55 + 980 * p, y + 70), 8, fill=(255, 214, 0, 150))
        d.text((80, y + 32), r, font=f, fill=(20, 22, 28, 255), anchor="lm")
        d.text((1010, y + 32), "₩ · · · · ·", font=f, fill=(110, 110, 110, 255), anchor="rm")
        if i in g.get("strike", []):
            p = eo((lt - 0.5) / 0.3)
            if p > 0:
                d.line((65, y + 34, 65 + 960 * p, y + 34), fill=RED, width=8)
                if p >= 1:
                    d.rounded_rectangle((830, y - 4, 1030, y + 68), 12, fill=RED)
                    d.text((930, y + 32), "제외", font=font(F_BIG, 46), fill=WHITE, anchor="mm")
    return im


def g_tag(g, lt, dur, cont):
    im = Image.new("RGBA", (1300, 560), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    s = 1.0 if cont else eob(lt / 0.4)
    tag = Image.new("RGBA", (560, 260), (0, 0, 0, 0)); td = ImageDraw.Draw(tag)
    struck = g.get("strike") and lt > 0.4
    col = (120, 120, 120, 255) if struck else YEL
    td.rounded_rectangle((60, 0, 559, 259), 30, fill=col)
    td.polygon([(0, 130), (70, 10), (70, 250)], fill=col)
    td.ellipse((70, 112, 106, 148), fill=(0, 0, 0, 160))
    td.text((320, 132), g["text"], font=font(F_BIG, 140), fill=BLACK, anchor="mm")
    tag = tag.rotate(-4, expand=True, resample=Image.BICUBIC)
    if s != 1.0:
        s = max(0.05, s)
        tag = tag.resize((int(tag.width * s), int(tag.height * s)), Image.BILINEAR)
    im.alpha_composite(tag, (650 - tag.width // 2, 170 - tag.height // 2))
    if g.get("strike"):
        p = eo((lt - 0.4) / 0.25)
        if p > 0:
            d.line((330, 60, 330 + 640 * p, 60 + 230 * p), fill=RED, width=20)
    a = eo((lt - 0.3) / 0.4)
    l = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(l).text((650, 380), g["sub"], font=font(F_BIG, 54),
                           fill=RED if g.get("strike") else WHITE, anchor="mt", stroke_width=3, stroke_fill=(0, 0, 0, 200))
    im.alpha_composite(fade(l, a))
    return im


def g_sms(g, lt, dur, cont):
    im, d = panel(1180, 560, fill=(236, 239, 244, 248), border=(0, 0, 0, 0), r=40)
    d.rectangle((0, 0, 1180, 100), fill=(210, 215, 224, 255))
    d.rounded_rectangle((0, 0, 1180, 100), 40, fill=(210, 215, 224, 255))
    d.text((590, 50), "정비소에 보낼 문자 예시", font=font(F_BODY, 40), fill=(40, 44, 52, 255), anchor="mm")
    full = g["msg"]
    n = int(len(full) * eio((lt - 0.3) / 1.6))
    shown = full[:n]
    f = font(F_BODY, 50)
    lines = shown.split("\n")
    bw = max([tw(x, f) for x in full.split("\n")]) + 80
    bh = 70 * len(full.split("\n")) + 50
    x1 = 1120; x0 = x1 - bw; y0 = 150
    if lt > 0.2:
        d.rounded_rectangle((x0, y0, x1, y0 + bh), 34, fill=(59, 130, 246, 255))
        for i, ln in enumerate(lines):
            d.text((x0 + 40, y0 + 30 + i * 70), ln, font=f, fill=WHITE, anchor="lt")
        if n >= len(full):
            d.text((x1, y0 + bh + 18), "전송됨 ✓", font=font(F_BODY, 34), fill=(90, 96, 110, 255), anchor="rt")
    return im


def g_check(g, lt, dur, cont):
    items = g["items"]; n = g["n"]
    im, d = panel(1440, 150 + 125 * len(items))
    for i, it in enumerate(items):
        a = 1.0 if cont else eo((lt - i * 0.12) / 0.35)
        y = 75 + i * 125
        checked = i < n
        just = i == n - 1
        k = eob((lt - 0.1) / 0.3) if just else (1.0 if checked else 0.0)
        box = (80, y, 170, y + 90)
        d.rounded_rectangle(box, 18, outline=(GRN if checked else (150, 156, 168, 255))[:3] + (int(255 * a),), width=6,
                            fill=(52, 209, 122, int(60 * clamp(k))) if checked else None)
        if checked and k > 0:
            s = clamp(k, 0, 1.2)
            pts = [(98, y + 45), (120, y + 45 + 22 * s), (158, y + 45 - 30 * s)]
            d.line(pts, fill=GRN, width=12, joint="curve")
        col = WHITE if checked else (150, 156, 168, 255)
        d.text((210, y + 45), it, font=font(F_BIG, 56), fill=col[:3] + (int(255 * a),), anchor="lm")
        if just and n > 0:
            pencil(im, underline_pts(210, 210 + tw(it, font(F_BIG, 56)), y + 82, seed=i + 11), clamp((lt - 0.35) / 0.45), w=7)
    return im


def g_end(g, lt, dur, cont):
    im = Image.new("RGBA", (1600, 600), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    a1 = eo(lt / 0.5); a2 = eo((lt - 0.4) / 0.5); a3 = eo((lt - 1.0) / 0.5)
    l = Image.new("RGBA", im.size, (0, 0, 0, 0)); ld = ImageDraw.Draw(l)
    ld.text((800, 90), g.get("l1", "명세서 + 문자 기록"), font=font(F_BIG, 110), fill=WHITE, anchor="mt", stroke_width=3, stroke_fill=(0, 0, 0, 200))
    im.alpha_composite(fade(l, a1), (0, int(30 * (1 - a1))))
    l = Image.new("RGBA", im.size, (0, 0, 0, 0)); ld = ImageDraw.Draw(l)
    ld.text((800, 250), g.get("l2", "= 따질 수 있는 근거"), font=font(F_BIG, 90), fill=YEL, anchor="mt", stroke_width=3, stroke_fill=(0, 0, 0, 200))
    im.alpha_composite(fade(l, a2), (0, int(30 * (1 - a2))))
    l = Image.new("RGBA", im.size, (0, 0, 0, 0)); ld = ImageDraw.Draw(l)
    src = g.get("src", "출처: 수원지방법원 2020. 8. 27. 선고 2019나63515 판결  ·  개별 사안은 전문가 상담을 권합니다")
    fs = font(F_MED, 32)
    if tw(src, fs) > 1540 and " · " in src:  # 넘치면 가운데 · 에서 두 줄로
        parts = src.split(" · ")
        k = min(range(1, len(parts)), key=lambda j: abs(len(" · ".join(parts[:j])) - len(src) / 2))
        src = " · ".join(parts[:k]) + "\n" + " · ".join(parts[k:])
    ld.multiline_text((800, 450), src, font=fs, fill=SUB, anchor="ma", align="center", spacing=12)
    im.alpha_composite(fade(l, a3))
    return im


# ── 쉬운 설명용: 그림 + 한 줄 (40~50대도 한눈에) ──
PIC_DIR = None
_pc = {}
def pic_img(name, size):
    k = (name, size)
    if k not in _pc:
        im = Image.open(os.path.join(PIC_DIR, name + ".png")).convert("RGB").resize((size, size), Image.LANCZOS)
        m = Image.new("L", (size, size), 0)
        ImageDraw.Draw(m).rounded_rectangle((0, 0, size - 1, size - 1), 36, fill=255)
        rgba = im.convert("RGBA"); rgba.putalpha(m)
        _pc[k] = rgba
    return _pc[k]


def fitfont(texts, path, size, maxw=830):
    while size > 40 and max(tw(t, font(path, size)) for t in texts) > maxw:
        size -= 4
    return font(path, size)


def g_pic(g, lt, dur, cont):
    im, d = panel(1560, 640)
    k = eob(lt / 0.45)
    sz = 560
    p = pic_img(g["pic"], sz)
    s = clamp(0.85 + 0.15 * k, 0.5, 1.05)
    ps = p.resize((int(sz * s), int(sz * s)), Image.BILINEAR)
    im.alpha_composite(fade(ps, clamp(lt / 0.25)), (40 + (sz - ps.width) // 2, 40 + (sz - ps.height) // 2))
    tx = 680
    a1 = eo((lt - 0.2) / 0.35)
    l = Image.new("RGBA", im.size, (0, 0, 0, 0)); ld = ImageDraw.Draw(l)
    ld.text((tx, 150), g.get("cap", ""), font=font(F_BODY, 56), fill=SUB, anchor="lt")
    im.alpha_composite(fade(l, a1), (int(30 * (1 - a1)), 0))
    a2 = eob((lt - 0.45) / 0.4)
    if a2 > 0:
        col = RED if g.get("red") else YEL
        lines = g.get("big", "").split("\n")
        fb = fitfont(lines, F_BIG, 96)
        l = Image.new("RGBA", im.size, (0, 0, 0, 0)); ld = ImageDraw.Draw(l)
        for i, ln in enumerate(lines):
            ld.text((tx, 250 + i * 118), ln, font=fb, fill=col, anchor="lt")
        sc_ = clamp(a2, 0, 1.1)
        im.alpha_composite(fade(l, clamp(a2)), (int(40 * (1 - clamp(a2))), 0))
        if lt > 0.9:
            last = lines[-1]; yl = 250 + (len(lines) - 1) * 118 + fb.size + 14
            pencil(im, underline_pts(tx, tx + min(820, tw(last, fb)), yl, seed=len(last)), clamp((lt - 0.9) / 0.45), w=8)
    return im


def g_vs(g, lt, dur, cont):
    im, d = panel(1560, 640)
    p = pic_img(g["pic"], 560)
    im.alpha_composite(fade(p, clamp(lt / 0.25)), (40, 40))
    tx = 680
    a1 = eo((lt - 0.1) / 0.35)
    if a1 > 0:
        fa = fitfont([g["a"]], F_BIG, 78)
        d.text((tx, 120), g["a"], font=fa, fill=(170, 176, 188, int(255 * a1)), anchor="lt")
        k = eo((lt - 0.7) / 0.3)
        if k > 0:
            w = tw(g["a"], fa)
            d.line((tx - 6, 162, tx - 6 + (w + 12) * k, 162), fill=RED, width=9)
    a2 = eo((lt - 0.8) / 0.3)
    if a2 > 0:
        d.text((tx, 250), "↓", font=font(F_BODY, 90), fill=(255, 255, 255, int(255 * a2)), anchor="lt")
    a3 = eob((lt - 1.1) / 0.4)
    if a3 > 0:
        l = Image.new("RGBA", im.size, (0, 0, 0, 0))
        ImageDraw.Draw(l).text((tx, 390), g["b"], font=fitfont([g["b"]], F_BIG, 96), fill=YEL, anchor="lt")
        im.alpha_composite(fade(l, clamp(a3)), (int(40 * (1 - clamp(a3))), 0))
    return im


def g_bigtext(g, lt, dur, cont):
    im = Image.new("RGBA", (1600, 460), (0, 0, 0, 0))
    a1 = eo(lt / 0.35)
    l = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(l).text((800, 60), g["top"], font=font(F_BIG, 64), fill=WHITE, anchor="mt", stroke_width=3, stroke_fill=(0, 0, 0, 200))
    im.alpha_composite(fade(l, a1), (0, int(30 * (1 - a1))))
    k = clamp((lt - 0.35) / 0.25)
    if k > 0:
        s = 1.5 - 0.5 * eo(k)
        t = Image.new("RGBA", (1600, 240), (0, 0, 0, 0))
        ImageDraw.Draw(t).text((800, 120), g["big"], font=font(F_BIG, 150), fill=YEL, anchor="mm", stroke_width=5, stroke_fill=(0, 0, 0, 220))
        t = t.resize((int(1600 * s), int(240 * s)), Image.BILINEAR)
        im.alpha_composite(fade(t, clamp(k * 2)), (800 - t.width // 2, 290 - t.height // 2)) if t.width <= 1600 else \
            im.alpha_composite(fade(t.crop(((t.width - 1600) // 2, 0, (t.width - 1600) // 2 + 1600, t.height)), clamp(k * 2)), (0, max(0, 290 - t.height // 2)))
    if lt > 0.75 and g.get("pencil", True):
        wb = min(1500, tw(g["big"], font(F_BIG, 150)))
        pencil(im, underline_pts(800 - wb / 2, 800 + wb / 2, 385, seed=len(g["big"])), clamp((lt - 0.75) / 0.45), w=9)
    return im


# ───────────────────────── 색연필 ─────────────────────────
PENCIL = (240, 70, 55)
_pgrain = {}


def _grain(size):
    if size not in _pgrain:
        rnd = np.random.default_rng(7)
        g = rnd.uniform(0.45, 1.0, (size[1], size[0])).astype(np.float32)
        _pgrain[size] = g
    return _pgrain[size]


def pencil(im, pts, prog, col=PENCIL, w=7, seed=1):
    """pts 경로를 prog(0~1)만큼 색연필 질감으로 그린다 — 겹친 가는 선 3가닥 + 종이 결"""
    if prog <= 0 or len(pts) < 2:
        return
    n = max(2, int(len(pts) * clamp(prog)))
    rnd = random.Random(seed)
    lay = Image.new("RGBA", im.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    for k, (ww, al) in enumerate(((w, 210), (max(2, w - 3), 160), (max(2, w - 4), 120))):
        ox, oy = rnd.uniform(-2.5, 2.5), rnd.uniform(-2.5, 2.5)
        ph = rnd.uniform(0, 6.28)
        q = [(x + ox + 1.6 * math.sin(i * 0.35 + ph), y + oy + 1.6 * math.cos(i * 0.29 + ph)) for i, (x, y) in enumerate(pts[:n])]
        d.line(q, fill=col + (al,), width=ww, joint="curve")
    a = np.asarray(lay.getchannel("A")).astype(np.float32) * _grain(im.size)
    lay.putalpha(Image.fromarray(a.clip(0, 255).astype(np.uint8)))
    im.alpha_composite(lay)


def underline_pts(x0, x1, y, seed=1):
    rnd = random.Random(seed)
    tilt = rnd.uniform(-6, 6)
    pts = [(x0 - 14 + (x1 - x0 + 28) * t, y + tilt * (t - 0.5) + 5 * math.sin(t * 3.1)) for t in [i / 60 for i in range(61)]]
    back = [(x1 + 6 - (x1 - x0 + 10) * t * 0.55, y + 12 + tilt * (0.5 - t) * 0.5) for t in [i / 30 for i in range(31)]]
    return pts + back  # 쭉 긋고 살짝 되돌아오는 두 번째 획


def ellipse_pts(cx, cy, rx, ry, seed=1):
    rnd = random.Random(seed)
    a0 = math.radians(rnd.uniform(195, 220))
    out = []
    for i in range(121):
        t = i / 120
        th = a0 + t * math.radians(385)
        r = 1 + 0.035 * math.sin(3 * th + seed) + 0.05 * t
        out.append((cx + rx * r * math.cos(th), cy - 6 * t + ry * r * math.sin(th)))
    return out


# ───────────────────────── 홈페이지 화면 ─────────────────────────
WEB_DIR = None
_web = {}


def web_img(name):
    if name not in _web:
        im = Image.open(os.path.join(WEB_DIR, name + ".jpg")).convert("RGB")
        im = im.crop((6, 6, im.width - 6, im.height - 6))  # 캡처 테두리(작업 창 보라 테두리) 제거
        d = ImageDraw.Draw(im)
        # 캡처에 찍힌 확장 프로그램 배지(오른쪽 위) 지우기 — 옆 색으로 덮는다
        c = im.getpixel((im.width - 420, 20))
        d.rectangle((im.width - 400, 0, im.width, 120), fill=c)
        _web[name] = im
    return _web[name]


def g_web(g, lt, dur, cont):
    """브라우저 창 → 0.5s 뒤 focus 로 확대 → 색연필 동그라미. focus 는 캡처 원본 px (x0,y0,x1,y1)"""
    WW, BAR = 1360, 54
    src = web_img(g["shot"])
    VH = int(WW * src.height / src.width)
    im = Image.new("RGBA", (WW + 20, VH + BAR + 20), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((10, 10, WW + 9, VH + BAR + 9), 18, fill=(245, 246, 248, 255), outline=(255, 255, 255, 90), width=2)
    for k, c in enumerate(((255, 95, 87), (255, 189, 46), (40, 200, 64))):
        d.ellipse((34 + k * 30, 30, 50 + k * 30, 46), fill=c + (255,))
    d.rounded_rectangle((150, 22, WW - 120, 54), 16, fill=(255, 255, 255, 255))
    d.text((176, 38), g.get("url", ""), font=font(F_MED, 24), fill=(70, 74, 82, 255), anchor="lm")
    f = g.get("focus")
    z = eio(clamp((lt - 0.45) / 0.8)) if f else 0.0
    if f:
        fw, fh = f[2] - f[0], f[3] - f[1]
        vw = max(fw * 1.9, src.width / g.get("zmax", 2.2))
        vw = min(vw, src.width); vh = vw * src.height / src.width
        cx, cy = (f[0] + f[2]) / 2, (f[1] + f[3]) / 2
        tx0 = min(max(0, cx - vw / 2), src.width - vw); ty0 = min(max(0, cy - vh / 2), src.height - vh)
        x0 = tx0 * z; y0 = ty0 * z; w_ = src.width + (vw - src.width) * z; h_ = src.height + (vh - src.height) * z
    else:
        x0, y0, w_, h_ = 0, 0, src.width, src.height
    view = src.resize((WW, VH), Image.BILINEAR, box=(x0, y0, x0 + w_, y0 + h_)).convert("RGBA")
    if f:
        sx, sy = WW / w_, VH / h_
        rx0, ry0 = (f[0] - x0) * sx, (f[1] - y0) * sy
        rx1, ry1 = (f[2] - x0) * sx, (f[3] - y0) * sy
        pr = clamp((lt - 1.15) / 0.6)
        if g.get("mark", "circle") == "underline":
            pencil(view, underline_pts(rx0, rx1, ry1 + 2, seed=len(g["shot"])), pr, w=8, seed=3)
        else:
            pencil(view, ellipse_pts((rx0 + rx1) / 2, (ry0 + ry1) / 2, (rx1 - rx0) / 2 + 34, (ry1 - ry0) / 2 + 26, seed=len(g["shot"])), pr, w=8, seed=3)
    mask = Image.new("L", (WW, VH), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, -20, WW - 1, VH - 1), 16, fill=255)
    im.paste(view, (10, BAR + 10), mask)
    if g.get("note"):
        a = eo((lt - 1.4) / 0.35)
        if a > 0:
            fn = font(F_BIG, 46)
            tw_ = tw(g["note"], fn)
            l = Image.new("RGBA", im.size, (0, 0, 0, 0)); ld = ImageDraw.Draw(l)
            bx = WW // 2 - tw_ // 2 - 36
            low = f and (f[1] + f[3]) / 2 > src.height * 0.5  # 강조 부위가 아래쪽이면 글씨는 위로
            ny = BAR + 40 if low else VH + BAR - 96
            ld.rounded_rectangle((bx, ny, bx + tw_ + 72, ny + 80), 40, fill=PENCIL + (245,))
            ld.text((WW // 2 + 10, ny + 40), g["note"], font=fn, fill=WHITE, anchor="mm")
            im.alpha_composite(fade(l, a), (0, int(20 * (1 - a))))
    return im


# ───────────────────────── 물컵 인포그래픽 ─────────────────────────
def g_cup(g, lt, dur, cont):
    """1년 병원비 한도 = 컵. stage 1: 컵이 차고 넘친다(?), stage 2: 넘친 만큼 돌려받는 돈이 올라간다"""
    im, d = panel(1500, 620)
    st = g.get("stage", 1)
    t0 = -10 if (st == 2 and cont) else 0  # 2단계가 이어지면 컵은 이미 가득
    lt2 = lt - t0
    d.text((750, 50), g.get("head", "1년 동안 낸 병원비  200만 원"), font=font(F_BIG, 54), fill=WHITE, anchor="mt")
    gx0, gx1, bx0, bx1, gtop, gbot = 260, 620, 300, 580, 160, 510
    poly = [(gx0, gtop), (gx1, gtop), (bx1, gbot), (bx0, gbot)]
    fill = eio(clamp((lt2 - 0.2) / 1.1))
    lvl = gbot - (gbot - gtop) * fill
    m = Image.new("L", im.size, 0); ImageDraw.Draw(m).polygon(poly, fill=255)
    wat = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(wat).rectangle((0, min(gbot, lvl + 4 * math.sin(lt * 6)), 1500, gbot), fill=(70, 160, 255, 215))
    wat.putalpha(Image.fromarray(np.minimum(np.asarray(wat.getchannel("A")), np.asarray(m))))
    im.alpha_composite(wat)
    d.line(poly + [poly[0]], fill=(255, 255, 255, 235), width=7, joint="curve")
    # 한도 = 컵 가장자리
    d.text((440, 575), g.get("limit", "컵 크기 = 내 한도 89만 원"), font=font(F_BIG, 40), fill=YEL, anchor="mm")
    # 넘침 물줄기 → 오른쪽 상자
    over = clamp((lt2 - 1.25) / 0.5)
    bxa, bya, bxb, byb = 900, 200, 1400, 540
    if over > 0:
        rnd = random.Random(int(lt * 30))
        for k in range(14):
            tt = ((lt * 1.6 + k / 14) % 1.0) * over
            x = gx1 + (bxa + 120 - gx1) * tt
            y = gtop - 30 * math.sin(math.pi * tt) + (bya + 60 - gtop) * tt * tt
            r = 9 + rnd.uniform(-2, 2)
            d.ellipse((x - r, y - r, x + r, y + r), fill=(110, 185, 255, 230))
    d.rounded_rectangle((bxa, bya, bxb, byb), 30, fill=(255, 255, 255, 18), outline=(255, 255, 255, 120), width=3)
    d.text(((bxa + bxb) // 2, bya + 40), "돌려받는 돈", font=font(F_BIG, 48), fill=WHITE, anchor="mt")
    if st == 1:
        q = clamp((lt2 - 1.6) / 0.3)
        if q > 0:
            l = Image.new("RGBA", im.size, (0, 0, 0, 0))
            ImageDraw.Draw(l).text(((bxa + bxb) // 2, 400), "?", font=font(F_BIG, 150), fill=YEL, anchor="mm")
            im.alpha_composite(fade(l, q))
    else:
        k = eo(clamp((lt - 0.15) / 0.9))
        val = int(g.get("back_n", 1110000) * k)
        d.text(((bxa + bxb) // 2, 400), won(val // 10000 * 10000) if k < 1 else g.get("back", "111만 원"),
               font=font(F_BIG, 92), fill=YEL, anchor="mm", stroke_width=3, stroke_fill=(0, 0, 0, 200))
        wv = tw(g.get("back", "111만 원"), font(F_BIG, 92))
        pencil(im, underline_pts((bxa + bxb) / 2 - wv / 2, (bxa + bxb) / 2 + wv / 2, 465, seed=5), clamp((lt - 1.0) / 0.5), w=8)
    return im


# ───────────────────────── 서류 흐름도 ─────────────────────────
def g_flow(g, lt, dur, cont):
    im, d = panel(1500, 600)
    d.text((750, 46), g.get("head", "서류는 병원이 보험회사로 직접"), font=font(F_BIG, 54), fill=WHITE, anchor="mt")
    hx, hy = 260, 350
    a0 = eo(lt / 0.4)
    d.rounded_rectangle((hx - 150, hy - 110, hx + 150, hy + 110), 34, fill=(255, 255, 255, int(235 * a0)))
    d.text((hx, hy - 22), "병원", font=font(F_BIG, 64), fill=(20, 24, 32, int(255 * a0)), anchor="mm")
    d.text((hx, hy + 52), "진료 기록", font=font(F_MED, 32), fill=(90, 96, 110, int(255 * a0)), anchor="mm")
    names = g.get("to", ["보험회사 A", "보험회사 B", "보험회사 C"])
    ys = [190, 350, 510]
    for i, (nm, ty) in enumerate(zip(names, ys)):
        a = eo((lt - 0.25 - i * 0.15) / 0.35)
        if a <= 0:
            continue
        tx = 1180
        d.line((hx + 160, hy, tx - 170, ty), fill=(255, 255, 255, int(90 * a)), width=4)
        d.rounded_rectangle((tx - 160, ty - 58, tx + 200, ty + 58), 28, fill=(255, 196, 0, int(240 * a)))
        d.text((tx + 20, ty), nm, font=font(F_BIG, 46), fill=(20, 20, 20, int(255 * a)), anchor="mm")
        # 날아가는 서류
        for k in range(2):
            p = ((lt - 0.6 - i * 0.2) * 0.8 + k * 0.5) % 1.0
            if lt < 0.6 + i * 0.2:
                continue
            x = hx + 160 + (tx - 170 - hx - 160) * p
            y = hy + (ty - hy) * p
            d.rounded_rectangle((x - 22, y - 28, x + 22, y + 28), 6, fill=(255, 255, 255, 255), outline=(60, 60, 70, 255), width=2)
            for r in range(3):
                d.line((x - 12, y - 14 + r * 12, x + 12, y - 14 + r * 12), fill=(150, 150, 160, 255), width=3)
    if lt > 1.4:
        wv = tw(g.get("head", "서류는 병원이 보험회사로 직접"), font(F_BIG, 54))
        pencil(im, underline_pts(750 - wv / 2, 750 + wv / 2, 118, seed=9), clamp((lt - 1.4) / 0.5), w=7)
    return im



GFX = {k[2:]: v for k, v in globals().items() if k.startswith("g_")}

# 그래픽 위치(중심 y) — 자막과 겹치지 않게 위쪽으로
CY = {"timeline": 500, "title": 470, "end": 480, "pic": 450, "vs": 450, "web": 455, "cup": 440, "flow": 440}
CY_DEFAULT = 460


# ───────────────────────── 자막 ─────────────────────────
def sub_chunks(text, maxc=26):
    import re
    parts = re.split(r"(?<=[,.?!])\s+", text.strip())
    out = []
    for p in parts:
        while len(p) > maxc + 6:
            # 가운데 근처 공백에서 자른다
            mid = len(p) // 2
            sp = [i for i, c in enumerate(p) if c == " "]
            cut = min(sp, key=lambda i: abs(i - mid)) if sp else mid
            out.append(p[:cut].strip()); p = p[cut:].strip()
        out.append(p)
    # 너무 짧은 조각은 앞과 합친다
    merged = []
    for c in out:
        if merged and len(c) < 8 and len(merged[-1]) + len(c) <= maxc + 6:
            merged[-1] += " " + c
        else:
            merged.append(c)
    return merged


SUB_CX = 960  # 진행자 캐릭터가 있으면 왼쪽으로 민다


def draw_sub(layer, text, lt):
    d = ImageDraw.Draw(layer)
    f = font(F_BODY, 50)
    a = eo(lt / 0.12)
    wtxt = tw(text, f)
    x0, x1 = SUB_CX - wtxt / 2 - 36, SUB_CX + wtxt / 2 + 36
    y = 925 + int(8 * (1 - a))
    d.rounded_rectangle((x0, y, x1, y + 84), 18, fill=(0, 0, 0, int(165 * a)))
    d.text((SUB_CX, y + 42), text, font=f, fill=(255, 255, 255, int(255 * a)), anchor="mm")


# ───────────────────────── 진행자 캐릭터 ─────────────────────────
HOST_H = 380


def load_host(wd, hcfg):
    """work/<slug>/<dir>/<pose>.png (RGBA) → 높이 HOST_H 로 맞춘 이미지 사전"""
    import glob
    out = {}
    for fp in glob.glob(os.path.join(wd, hcfg.get("dir", "host"), "*.png")):
        k = os.path.splitext(os.path.basename(fp))[0]
        if k.endswith("_raw"):
            continue
        im = Image.open(fp).convert("RGBA")
        bb = im.getbbox()
        if bb:
            im = im.crop(bb)
        out[k] = im.resize((int(im.width * HOST_H / im.height), HOST_H), Image.LANCZOS)
    return out


def draw_host(fr, im, lt, t):
    """오른쪽 아래. 포즈가 바뀌면 0.25s 팝, 평소엔 살짝 위아래로 흔들린다"""
    s = 0.85 + 0.15 * eob(clamp(lt / 0.25))
    if s < 0.999:
        im = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.BILINEAR)
    bob = int(6 * math.sin(t * 2.4))
    x = 1890 - im.width
    fr.alpha_composite(im, (x, H - 14 - im.height + bob))


# ───────────────────────── 배경 ─────────────────────────
class Bg:
    def __init__(self, path):
        im = Image.open(path).convert("RGB")
        s = max(1920 * 1.0 / im.width, 1200 * 1.0 / im.height)
        im = im.resize((int(im.width * s) + 1, int(im.height * s) + 1), Image.LANCZOS)
        self.sharp = im
        self.blur = im.filter(ImageFilter.GaussianBlur(10))

    def frame(self, p, kind, blur=False, punch=1.0):
        """p: 샷 진행도 0~1, kind: Ken Burns 방향 번호"""
        im = self.blur if blur else self.sharp
        bw, bh = im.size
        z0, z1 = [(1.0, 1.12), (1.12, 1.0), (1.06, 1.14), (1.1, 1.02)][kind % 4]
        z = (z0 + (z1 - z0) * eio(p)) * punch
        vw = min(bw, 1920 / z)                 # 배경은 1920x1200 이상으로 깔려 있다
        vh = vw * H / W
        pans = [(0.5, 0.5, 0.5, 0.5), (0.35, 0.5, 0.65, 0.5), (0.6, 0.45, 0.4, 0.55), (0.5, 0.6, 0.5, 0.4)]
        px0, py0, px1, py1 = pans[(kind // 2 + kind) % 4]
        cx = (px0 + (px1 - px0) * eio(p))
        cy = (py0 + (py1 - py0) * eio(p))
        x = (bw - vw) * cx; y = (bh - vh) * cy
        return im.resize((W, H), Image.BILINEAR, box=(x, y, x + vw, y + vh))


def build_vignette():
    yy, xx = np.mgrid[0:H, 0:W]
    r = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
    a = np.clip((r - 0.55) / 0.9, 0, 1) ** 1.6 * 200
    v = np.zeros((H, W, 4), np.uint8); v[..., 3] = a.astype(np.uint8)
    return Image.fromarray(v, "RGBA")


def build_grain(n=6, amp=14):
    rng = np.random.default_rng(3)
    out = []
    for _ in range(n):
        g = rng.integers(0, 255, (H // 2, W // 2), dtype=np.uint8)
        im = Image.fromarray(g, "L").resize((W, H), Image.BILINEAR)
        rgba = Image.merge("RGBA", (im, im, im, Image.new("L", (W, H), amp)))
        out.append(rgba)
    return out


# ───────────────────────── 메인 ─────────────────────────
def main():
    slug = sys.argv[1]
    wd = os.path.join(ROOT, "work", slug)
    sc = json.load(open(os.path.join(wd, "script.json"), encoding="utf-8"))
    tm = json.load(open(os.path.join(wd, "tts", "timing.json"), encoding="utf-8"))
    lines = sc["lines"]
    global PIC_DIR, SUB_CX, WEB_DIR
    PIC_DIR = os.path.join(wd, "pic")
    WEB_DIR = os.path.join(wd, "web")
    hosts = load_host(wd, sc["host"]) if sc.get("host") else {}
    if hosts:
        SUB_CX = 860
    hdef = sc.get("host", {}).get("default", "talk")
    pose_of = [ln.get("pose") or hdef for ln in lines]
    total = tm[-1]["end"]
    t_from, t_to = 0.0, total
    if "--preview" in sys.argv:
        a, b = sys.argv[sys.argv.index("--preview") + 1].split(":")
        t_from, t_to = float(a), min(total, float(b))

    # 줄 구간: 화면은 다음 줄 시작 전까지 이 줄을 보여준다
    seg = []
    for i, t in enumerate(tm):
        s = 0.0 if i == 0 else t["start"] - 0.05
        e = total if i == len(tm) - 1 else tm[i + 1]["start"] - 0.05
        seg.append((s, e))

    # 샷(같은 이미지가 이어지는 구간)
    shots = []
    for i, ln in enumerate(lines):
        if shots and shots[-1]["img"] == ln["img"]:
            shots[-1]["e"] = seg[i][1]
        else:
            shots.append({"img": ln["img"], "s": seg[i][0], "e": seg[i][1], "kind": len(shots)})
    bgs = {}
    for sh in shots:
        if sh["img"] not in bgs:
            bgs[sh["img"]] = Bg(os.path.join(wd, sc.get("img_dir", "img"), f"{sh['img']:02d}.png"))

    # 챕터
    chap_at, cur = [], ""
    for i, ln in enumerate(lines):
        if ln.get("chap") is not None and "chap" in ln:
            cur = ln["chap"]
        chap_at.append(cur)

    # 자막 조각 타이밍
    subs = []
    for i, ln in enumerate(lines):
        if ln["gfx"]["type"] == "question":
            continue
        ch = sub_chunks(ln["text"], 22 if sc.get("host") else 26)
        st, du = tm[i]["start"], tm[i]["dur"]
        tot = sum(len(c) for c in ch)
        acc = 0
        for c in ch:
            s = st + du * acc / tot
            acc += len(c)
            e = st + du * acc / tot
            subs.append((s, e + (0.25 if c is ch[-1] else 0), c))

    # 효과음 이벤트 + 흔들림/플래시
    ev, shakes, flashes = [], [], []
    for i, ln in enumerate(lines):
        s = seg[i][0] if i else tm[0]["start"]
        g = ln["gfx"]; ty = g["type"]
        prev = lines[i - 1]["gfx"]["type"] if i else None
        if ln.get("sfx"):
            ev.append((s, ln["sfx"], 0.55))
        if ty == "question": ev.append((s, "pop", 0.6))
        if ty == "vs": ev.append((s + 0.7, "tick", 0.5)); ev.append((s + 1.1, "ding", 0.45))
        if ty == "stamp": ev.append((s + 0.2, "thud", 0.8)); shakes.append(s + 0.2); flashes.append(s + 0.2)
        if ty == "counter" and g.get("shake"):
            tt = s + g.get("delay", 0.15) + 1.1; ev.append((tt, "thud", 0.8)); shakes.append(tt); flashes.append(tt)
        if ty == "check" and g["n"] > 0: ev.append((s + 0.1, "ding", 0.5))
        if ty == "invoice" and g.get("strike"): ev.append((s + 0.5, "tick", 0.6))
        if ty == "tag" and g.get("strike"): ev.append((s + 0.4, "thud", 0.7)); shakes.append(s + 0.4)
        if ty == "tag" and not g.get("strike"): ev.append((s, "pop", 0.5))
        if ty == "triangle" and g.get("x"): ev.append((s + 0.5, "thud", 0.6))
        if ty == "law" and g.get("stamp"): ev.append((s + 0.3, "thud", 0.8)); shakes.append(s + 0.3)
        if ty == "timeline": ev.append((s + 0.15, "tick", 0.45))
        if ty == "rows3" and (g.get("on", -1) >= 0): ev.append((s + 0.05, "tick", 0.45))
        if ty == "web": ev.append((s + 1.15, "tick", 0.5))
        if ty == "cup" and g.get("stage") == 2: ev.append((s + 0.15, "cash", 0.5))
        if ty in ("card", "law", "calc", "formula", "sms", "invoice", "bar", "counter", "pic", "vs", "bigtext") and prev != ty and not ln.get("sfx"):
            ev.append((s, "pop", 0.3))
    for k, sh in enumerate(shots[1:], 1):
        if not any(abs(e[0] - sh["s"]) < 0.25 for e in ev):
            ev.append((sh["s"] - 0.12, "whoosh", 0.35))

    vign = build_vignette()
    grain = build_grain()
    dark = Image.new("RGBA", (W, H), (0, 0, 0, 105))
    dark_focus = Image.new("RGBA", (W, H), (0, 0, 0, 150))

    def line_at(t):
        for i, (s, e) in enumerate(seg):
            if s <= t < e:
                return i
        return len(seg) - 1

    def shot_at(t):
        for k, sh in enumerate(shots):
            if sh["s"] <= t < sh["e"]:
                return k
        return len(shots) - 1

    def bg_for(k, t, blur, punch=1.0):
        sh = shots[k]
        p = clamp((t - sh["s"]) / max(0.1, sh["e"] - sh["s"]))
        return bgs[sh["img"]].frame(p, sh["kind"], blur, punch)

    def focus_of(i):
        return lines[i]["gfx"]["type"] in FOCUS_TYPES

    def render(t):
        i = line_at(t); lt = t - seg[i][0]
        k = shot_at(t)
        sh = shots[k]
        # 배경 (초점 전환 0.3s)
        fb = focus_of(i)
        fprev = focus_of(i - 1) if i > 0 else fb
        mixf = eo(lt / 0.3) if fb != fprev else 1.0
        if mixf < 1.0:
            b_now = bg_for(k, t, fb); b_old = bg_for(k, t, fprev)
            bg = Image.blend(b_old, b_now, mixf)
        else:
            bg = bg_for(k, t, fb)
        # 샷 전환 — 새 샷은 1.08 → 1.0 줌 펀치하며 0.4s 크로스페이드
        ts = t - sh["s"]
        if k > 0 and ts < 0.4:
            pk = eo(ts / 0.4)
            nb = bg_for(k, t, fb, punch=1.08 - 0.08 * pk)
            ob = bg_for(k - 1, t, focus_of(max(0, i - 1)))
            bg = Image.blend(ob, nb, pk)
        fr = bg.convert("RGBA")
        fr.alpha_composite(dark_focus if fb else dark)
        fr.alpha_composite(vign)

        # 그래픽
        g = lines[i]["gfx"]; ty = g["type"]
        cont = i > 0 and lines[i - 1]["gfx"]["type"] == ty and ty in ("timeline", "rows3", "check", "law", "tag", "triangle", "invoice", "cup")
        if i > 0 and not cont and lt < 0.18:
            pg = lines[i - 1]["gfx"]
            pim = GFX[pg["type"]](pg, seg[i - 1][1] - seg[i - 1][0], 99, False)
            a = 1 - lt / 0.18
            pim = fade(pim, a)
            cy = CY.get(pg["type"], CY_DEFAULT) - int(30 * (1 - a))
            fr.alpha_composite(pim, (960 - pim.width // 2, cy - pim.height // 2))
        gim = GFX[ty](g, lt, seg[i][1] - seg[i][0], cont)
        if not cont:
            ent = clamp(lt / 0.35)
            s = 0.94 + 0.06 * eob(ent)
            if s < 0.999:
                gim = gim.resize((max(1, int(gim.width * s)), max(1, int(gim.height * s))), Image.BILINEAR)
            gim = fade(gim, clamp(lt / 0.2))
            dy = int(24 * (1 - eo(ent)))
        else:
            dy = 0
        cy = CY.get(ty, CY_DEFAULT) + dy
        fr.alpha_composite(gim, (960 - gim.width // 2, cy - gim.height // 2))

        # 진행자
        if hosts:
            pz = pose_of[i] if pose_of[i] in hosts else hdef
            j = i
            while j > 0 and pose_of[j - 1] == pose_of[i]:
                j -= 1
            if pz in hosts:
                draw_host(fr, hosts[pz], t - seg[j][0], t)

        # 자막
        for s0, e0, c in subs:
            if s0 <= t < e0:
                draw_sub(fr, c, t - s0)
                break

        d = ImageDraw.Draw(fr)
        # 챕터 태그
        ch = chap_at[i]
        if ch:
            first = next(j for j in range(len(lines)) if chap_at[j] == ch)
            ca = eo((t - seg[first][0]) / 0.4)
            fch = font(F_BIG, 40)
            wch = tw(ch, fch)
            x = 60 - int(40 * (1 - ca))
            d.rounded_rectangle((x, 52, x + wch + 56, 124), 36, fill=YEL[:3] + (int(255 * ca),))
            d.text((x + 28, 89), ch, font=fch, fill=BLACK[:3] + (int(255 * ca),), anchor="lm")
        # 채널명
        d.text((1860, 88), sc.get("channel", CHANNEL), font=font(F_BIG, 36), fill=(255, 255, 255, 150), anchor="rm")
        # 진행 바
        d.rectangle((0, H - 8, W, H), fill=(255, 255, 255, 40))
        d.rectangle((0, H - 8, int(W * t / total), H), fill=YEL)

        fr.alpha_composite(grain[int(t * FPS) % len(grain)])

        # 흔들림
        for s0 in shakes:
            if 0 <= t - s0 < 0.32:
                amp = 14 * (1 - (t - s0) / 0.32)
                rnd = random.Random(int(t * FPS))
                ox, oy = int(rnd.uniform(-amp, amp)), int(rnd.uniform(-amp, amp))
                sh_im = Image.new("RGBA", (W, H), (0, 0, 0, 255))
                sh_im.paste(fr.resize((int(W * 1.03), int(H * 1.03)), Image.BILINEAR), (ox - int(W * 0.015), oy - int(H * 0.015)))
                fr = sh_im
                break
        for s0 in flashes:
            if 0 <= t - s0 < 0.12:
                fr = Image.blend(fr, Image.new("RGBA", (W, H), (255, 255, 255, 255)), 0.45 * (1 - (t - s0) / 0.12))
        return fr.convert("RGB")

    # ── 오디오 ──
    out_dir = wd
    sfx_arr = np.zeros(int((total + 1) * SR), np.float32)
    cache = {}
    for t0, name, vol in ev:
        if name not in cache:
            p = os.path.join(ROOT, "assets", "sfx", f"{name}.wav")
            raw = subprocess.run(["ffmpeg", "-v", "error", "-i", p, "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"],
                                 capture_output=True).stdout
            cache[name] = np.frombuffer(raw, np.float32)
        x = cache[name] * vol
        a0 = max(0, int(t0 * SR)); a1 = min(len(sfx_arr), a0 + len(x))
        sfx_arr[a0:a1] += x[:a1 - a0]
    sfx_wav = os.path.join(out_dir, "sfx.wav")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-", sfx_wav],
                   input=np.clip(sfx_arr, -1, 1).tobytes(), check=True)

    narr = os.path.join(wd, "tts", "narration.wav")
    bgm = os.path.join(ROOT, "assets", "bgm.mp3")
    mix = os.path.join(out_dir, "mix.m4a")
    fc = (f"[0:a]{audio.POST_CHAIN},asplit=2[n][sc];"
          f"[1:a]aloop=loop=-1:size=2e9,atrim=0:{total:.2f},volume=0.16,aresample=44100[b];"
          f"[b][sc]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=400[bd];"
          f"[2:a]volume=0.9,aresample=44100[s];"
          f"[n][bd][s]amix=inputs=3:normalize=0:duration=first,alimiter=limit=0.95[out]")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", narr, "-i", bgm, "-i", sfx_wav,
                    "-filter_complex", fc, "-map", "[out]", "-c:a", "aac", "-b:a", "192k", mix], check=True)

    # ── 비디오 ──
    name = "preview.mp4" if "--preview" in sys.argv else "final.mp4"
    out = os.path.join(wd, name)
    n0, n1 = int(t_from * FPS), int(t_to * FPS)
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-", "-ss", f"{t_from:.3f}", "-t", f"{t_to - t_from:.3f}", "-i", mix,
           "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "medium", "-crf", "19",
           "-pix_fmt", "yuv420p", "-c:a", "copy", "-shortest", "-movflags", "+faststart", out]
    pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    import time
    t_start = time.time()
    for fi in range(n0, n1):
        pr.stdin.write(render(fi / FPS).tobytes())
        if (fi - n0) % 300 == 0:
            el = time.time() - t_start
            print(f"  프레임 {fi - n0}/{n1 - n0} · {el:.0f}s", flush=True)
    pr.stdin.close(); pr.wait()
    print(f"✓ {out} ({t_to - t_from:.1f}s)")
    if "--no-open" not in sys.argv:
        subprocess.run(["open", out])


if __name__ == "__main__":
    main()
