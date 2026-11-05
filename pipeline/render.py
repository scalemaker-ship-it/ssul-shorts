#!/usr/bin/env python3
"""[2] 오버레이 렌더 — 자막 덩어리마다 '이미지 위에 얹을 층'을 만든다.

콘텐츠 이미지는 build.py 가 프레임마다 움직이며 그리므로, 여기서는 이미지를
그리지 않는다. 대신 이미지 자리를 **투명하게 비워둔** RGBA 층을 만든다.

사용: python3 pipeline/render.py <slug>
입력: work/<slug>/script.json , work/<slug>/tts/timing.json
산출: work/<slug>/frames/ov_NNN.png      (+ ov_NNN_c.png = 캐릭터판)
      work/<slug>/frames/manifest.json
"""
import sys, os, json, glob
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import layout as L
import layout_check
import subs

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def font(path, size):
    # 폰트 경로는 layout.py 에서 저장소 루트 기준 상대경로(fonts/...)
    return ImageFont.truetype(os.path.join(ROOT, path), size)


def fit_font(path, text, max_w, cap):
    """max_w 를 꽉 채우는 최대 크기를 찾는다 (cap 을 넘지 않음)."""
    lo, hi, best = 12, cap, 12
    while lo <= hi:
        mid = (lo + hi) // 2
        b = font(path, mid).getbbox(text)
        if b[2] - b[0] <= max_w:
            best, lo = mid, mid + 1
        else:
            hi = mid - 1
    return font(path, best)


def center_text(d, cx, y, text, f, fill, stroke=0):
    b = f.getbbox(text)
    d.text((cx - (b[2] - b[0]) / 2 - b[0], y), text, font=f, fill=fill,
           stroke_width=stroke, stroke_fill=(0, 0, 0, 255))


def tracked_width(text, f, track):
    return sum(f.getlength(c) for c in text) + track * max(0, len(text) - 1)


def center_tracked(d, cx, y, text, f, fill, track, stroke=0):
    """자간을 적용해 글자를 하나씩 그린다.

    외곽선과 본문을 두 번에 나눠 그린다 — 한 번에 그리면 다음 글자의 외곽선이
    앞 글자의 획을 덮어써서 자간이 좁을 때 글자가 뭉개진다.
    """
    x0 = cx - tracked_width(text, f, track) / 2
    for stroke_pass in (True, False):
        x = x0
        for c in text:
            if stroke_pass:
                if stroke:
                    d.text((x, y), c, font=f, fill=(0, 0, 0, 255),
                           stroke_width=stroke, stroke_fill=(0, 0, 0, 255))
            else:
                d.text((x, y), c, font=f, fill=fill)
            x += f.getlength(c) + track


def em_spans(text, ems):
    """문장 전체에서 강조어가 걸리는 구간 [(시작, 끝)] 을 찾는다. 겹치면 합친다."""
    spans = []
    for e in (ems or []):
        if not e:
            continue
        st = 0
        while True:
            i = text.find(e, st)
            if i < 0:
                break
            spans.append((i, i + len(e)))
            st = i + 1
    spans.sort()
    merged = []
    for a, b in spans:
        if merged and a <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], b))
        else:
            merged.append((a, b))
    return merged


def chunk_spans(chunk, offset, spans):
    """문장 기준 구간을 이 덩어리 안의 상대 구간으로 옮긴다.

    강조어가 **덩어리 경계에 걸치는 경우**가 흔하다("세월을 역주행" 이
    '…세월을' / '역주행했다고…' 로 잘린다). 문장 전체에서 구간을 잡아
    덩어리별로 잘라 넣어야 양쪽 다 강조된다.
    """
    out = []
    lo, hi = offset, offset + len(chunk)
    for a, b in spans:
        s2, e2 = max(a, lo), min(b, hi)
        if s2 < e2:
            out.append((s2 - lo, e2 - lo))
    return out


def split_runs(text, spans):
    """(문자열, 강조여부) 런으로 쪼갠다."""
    if not spans:
        return [(text, False)]
    runs, p = [], 0
    for a, b in spans:
        if a > p:
            runs.append((text[p:a], False))
        runs.append((text[a:b], True))
        p = b
    if p < len(text):
        runs.append((text[p:], False))
    return [r for r in runs if r[0]]


def runs_width(runs, fbase, fem, track):
    w, n = 0.0, 0
    for t, em in runs:
        f = fem if em else fbase
        w += sum(f.getlength(c) for c in t)
        n += len(t)
    return w + track * max(0, n - 1)


def draw_runs(d, cx, baseline, runs, fbase, fem, color, em_color, track, stroke=0):
    """런을 **베이스라인 기준**으로 이어 그린다.

    폰트마다 ascent 가 달라서 같은 y 로 그리면 강조 글자만 위아래로 뜬다.
    외곽선과 본문을 두 번에 나눠 그리는 이유는 center_tracked 와 같다.
    """
    x0 = cx - runs_width(runs, fbase, fem, track) / 2
    for stroke_pass in (True, False):
        x = x0
        for t, em in runs:
            f = fem if em else fbase
            y = baseline - f.getmetrics()[0]
            for c in t:
                if stroke_pass:
                    if stroke:
                        d.text((x, y), c, font=f, fill=(0, 0, 0, 255),
                               stroke_width=stroke, stroke_fill=(0, 0, 0, 255))
                else:
                    d.text((x, y), c, font=f, fill=(em_color if em else color))
                x += f.getlength(c) + track


def em_fill(name):
    return L.EM_YELLOW if str(name).startswith(("y", "노")) else L.EM_GREEN


def paste_character(im, top=None):
    """이미지 영역 상단에 걸치도록 캐릭터를 중앙 배치.

    흰 바(style.bar)가 있으면 top 으로 바 하단을 받아 그 밑에 건다 —
    바 위에 그리면 캐릭터가 바 글자를 가린다.
    """
    p = os.path.join(ROOT, "assets", "character.png")
    if not os.path.exists(p):
        return
    ch = Image.open(p).convert("RGBA")
    h = L.px(L.CHAR_H)
    w = max(1, int(ch.width * h / ch.height))
    ch = ch.resize((w, h), Image.LANCZOS)
    if top is not None:
        # 흰 바 밑에 통째로 건다 — 걸치게 두면 캐릭터가 바 글자를 가린다
        im.alpha_composite(ch, (L.W // 2 - w // 2, top))
    else:
        bottom = L.px(L.CONTENT_TOP + L.CHAR_OVERLAP)
        im.alpha_composite(ch, (L.W // 2 - w // 2, bottom - h))


# ── 하단 댓글 카드 (2026-10-10 사용자 지시 "템플릿 2처럼 하단에 댓글") ──
# 문장에 "comment": {"nick": "ㅇㅇ", "text": "...", "likes": 14} 를 달면 그 문장부터
# 다음 댓글이 나올 때까지 이미지 아래 검은 영역에 유튜브 댓글 모양 카드가 뜬다.
CARD_X, CARD_Y, CARD_W = 60, 1400, 960
AVATAR_COL = [(255, 138, 101), (129, 199, 132), (100, 181, 246), (186, 104, 200), (255, 213, 79)]


def draw_comment(im, cm, k=0):
    d = ImageDraw.Draw(im)
    fn = font(f"{L.FONT_DIR}/Pretendard-SemiBold.ttf", 34)
    ft = font(f"{L.FONT_DIR}/Pretendard-SemiBold.ttf", 46)
    fl = font(f"{L.FONT_DIR}/Pretendard-Medium.ttf", 32)
    # 줄바꿈 — 카드 폭 안에서 어절 단위
    words, lines, cur = cm["text"].split(" "), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if ft.getlength(t) > CARD_W - 190 and cur:
            lines.append(cur); cur = w
        else:
            cur = t
    lines.append(cur)
    h = 150 + 60 * len(lines)
    d.rounded_rectangle((CARD_X, CARD_Y, CARD_X + CARD_W, CARD_Y + h), 30, fill=(255, 255, 255, 255))
    col = AVATAR_COL[k % len(AVATAR_COL)]
    d.ellipse((CARD_X + 34, CARD_Y + 34, CARD_X + 118, CARD_Y + 118), fill=col + (255,))
    d.text((CARD_X + 76, CARD_Y + 76), cm.get("nick", "ㅇㅇ")[:1], font=fn, fill=(255, 255, 255, 255), anchor="mm")
    d.text((CARD_X + 146, CARD_Y + 40), "@" + cm.get("nick", "익명"), font=fn, fill=(110, 110, 118, 255))
    for i, ln in enumerate(lines):
        d.text((CARD_X + 146, CARD_Y + 88 + i * 60), ln, font=ft, fill=(15, 15, 18, 255))
    if cm.get("likes"):
        d.text((CARD_X + 146, CARD_Y + 100 + len(lines) * 60), f"♡ {cm['likes']}", font=fl, fill=(110, 110, 118, 255))


# ── 하단 설명 라벨 (2026-10-18 사용자 지시 "하단에 설명 타이틀") ──
# 문장에 "label": {"title": "1위 맥도날드 체코", "desc": "좋아요 34만 7천"} 을 달면 그 문장부터
# 다음 label 이 나올 때까지 이미지 아래 검은 영역에 흰 제목 칩 + 설명 박스가 뜬다.
# "label": null 을 주면 거기서 내린다. 카드뉴스(룩스) 하단 설명 형식.
def draw_label(im, lb):
    d = ImageDraw.Draw(im)
    ft = font(L.F_TITLE, 56)
    fd = font(f"{L.FONT_DIR}/Pretendard-SemiBold.ttf", 44)
    cx, y = L.W // 2, 1420
    t = lb.get("title", "")
    if t:
        b = ft.getbbox(t)
        w, h = b[2] - b[0], b[3] - b[1]
        d.rectangle((cx - w / 2 - 28, y, cx + w / 2 + 28, y + h + 36), fill=(255, 255, 255, 255))
        d.text((cx - w / 2 - b[0], y + 18 - b[1]), t, font=ft, fill=(10, 10, 12, 255))
        y += h + 36 + 22
    desc = lb.get("desc", "")
    if desc:
        b = fd.getbbox(desc)
        w, h = b[2] - b[0], b[3] - b[1]
        d.rectangle((cx - w / 2 - 24, y, cx + w / 2 + 24, y + h + 30), fill=(255, 255, 255, 235))
        d.text((cx - w / 2 - b[0], y + 15 - b[1]), desc, font=fd, fill=(30, 30, 34, 255))


def build_overlay(sc, sub_text, character=False, spans=None, em_color=None,
                  bar_text=None, dialogue=False, comment=None, label=None):
    """이미지 위에 얹을 층. 콘텐츠 영역은 투명하게 비워둔다."""
    im = Image.new("RGBA", (L.W, L.H), (0, 0, 0, 255))
    c_top, c_bot = L.px(L.CONTENT_TOP), L.px(L.CONTENT_BOT)
    # 콘텐츠 창을 뚫는다
    im.paste((0, 0, 0, 0), (0, c_top, L.W, c_bot))

    d = ImageDraw.Draw(im)
    cx = L.W // 2
    inner = L.W - L.SIDE_PAD * 2

    # ── 흰 바 (style.bar) — 타이틀 밑, 이미지 상단에 걸치는 흰 배경 한 줄 ──
    # 레퍼런스(N잡연구소) 템플릿의 서브타이틀 바. 첫 문장(타이틀 나레이션)을
    # 읽는 동안만 얹힌다 — main() 이 그 구간의 덩어리에만 bar_text 를 넘긴다.
    bar_bot = c_top
    if bar_text:
        bar_bot = c_top + L.px(L.BAR_H)
        im.paste(L.BAR_BG + (255,), (0, c_top, L.W, bar_bot))
        # 댓글 수 — style.bar_count 를 주면 제목 뒤에 파란 "(000)" 이 붙는다
        cnt = (sc.get("style") or {}).get("bar_count")
        cnt = f" ({int(cnt)})" if cnt else ""
        bf = fit_font(L.F_BAR, bar_text + cnt, L.W - L.BAR_PAD * 2, L.SZ_BAR)
        b = bf.getbbox(bar_text + cnt)
        y = c_top + (L.px(L.BAR_H) - (b[3] - b[1])) // 2 - b[1]
        x = cx - (b[2] - b[0]) / 2 - b[0]
        d.text((x, y), bar_text, font=bf, fill=L.BAR_TEXT + (255,))
        if cnt:
            d.text((x + bf.getlength(bar_text), y), cnt, font=bf,
                   fill=L.BAR_CNT + (255,))

    # ── 상단 타이틀 2행 (같은 크기로 통일, 자간 TITLE_TRACK) ─────
    # 모바일 플레이어가 좌우를 살짝 잘라먹으므로 TITLE_PAD 여백을 반드시 지킨다.
    t_inner = L.W - L.TITLE_PAD * 2
    band_h = L.px(L.TITLE_MID) - L.px(L.TITLE_TOP)

    def fit_tracked(text, cap):
        lo, hi, best = 12, cap, 12
        while lo <= hi:
            mid = (lo + hi) // 2
            if tracked_width(text, font(L.F_TITLE, mid), L.TITLE_TRACK) <= t_inner:
                best, lo = mid, mid + 1
            else:
                hi = mid - 1
        return best

    t_size = min(fit_tracked(sc[k], L.SZ_TITLE)
                 for k in ("title_line1", "title_line2"))
    f = font(L.F_TITLE, t_size)
    for text, y_r, color in (
        (sc["title_line1"], L.TITLE_TOP, L.TITLE_1),
        (sc["title_line2"], L.TITLE_MID, L.TITLE_2),
    ):
        b = f.getbbox(text)
        y = L.px(y_r) + (band_h - (b[3] - b[1])) // 2 - b[1]
        center_tracked(d, cx, y, text, f, color, L.TITLE_TRACK,
                       stroke=L.TITLE_STROKE)

    # ── 나레이션 자막 ────────────────────────────────────
    # 기본은 이미지 바로 밑 검정 영역에 흰 글씨 1줄(레이아웃 잠금값).
    # script.json 의 "style": {"sub_box": true} 를 주면 대신 **이미지 안쪽**에
    # 검은 사각 박스를 깔고 흰 글씨를 얹는다. 박스는 페더 0 — 모서리를 굴리거나
    # 흐리지 않는다. 실사 사진 위에서 외곽선만으로는 안 읽히는 경우에 쓴다.
    if sub_text:
        style = sc.get("style") or {}
        sub_box = bool(style.get("sub_box"))
        # 대사(목소리가 바뀌는 줄)는 글꼴·색을 바꿔 화면에서도 구분한다 (2026-08-31)
        sub_font = L.F_DLG if dialogue else L.F_SUB
        sub_fill = (L.DLG_C + (255,)) if dialogue else (255, 255, 255, 255)
        sub_cap = int(L.SZ_SUB * L.EM_SIZE_R) if dialogue else L.SZ_SUB
        if sub_box:
            sf = font(sub_font, sub_cap)
            while tracked_width(sub_text, sf, L.SUB_TRACK) > inner and sf.size > 32:
                sf = font(sub_font, sf.size - 2)
            b = sf.getbbox(sub_text)
            tw = tracked_width(sub_text, sf, L.SUB_TRACK)
            th = b[3] - b[1]
            pad_x, pad_y = 26, 18
            # 박스 바닥을 이미지 안쪽 하단에 붙인다(워터마크 위로 여유를 둔다).
            box_bot = L.px(L.CONTENT_BOT) - 24
            box_top = box_bot - th - pad_y * 2
            im.paste((0, 0, 0, 255),
                     (int(cx - tw / 2 - pad_x), int(box_top),
                      int(cx + tw / 2 + pad_x), int(box_bot)))
            y = box_top + pad_y - b[1]
            runs = split_runs(sub_text, spans)
            if not dialogue and any(e for _, e in runs):
                # 강조가 있는 덩어리만 런 렌더로 간다 — 없으면 아래 기존 경로
                # 그대로라서 잠금 규격의 화면이 한 픽셀도 안 바뀐다.
                ef = font(L.F_EM, max(12, int(sf.size * L.EM_SIZE_R)))
                while (runs_width(runs, sf, ef, L.SUB_TRACK) > inner
                       and sf.size > 32):
                    sf = font(L.F_SUB, sf.size - 2)
                    ef = font(L.F_EM, max(12, int(sf.size * L.EM_SIZE_R)))
                draw_runs(d, cx, y + sf.getmetrics()[0], runs, sf, ef,
                          (255, 255, 255, 255), em_fill(em_color),
                          L.SUB_TRACK, stroke=0)
            else:
                center_tracked(d, cx, y, sub_text, sf, sub_fill,
                               L.SUB_TRACK, stroke=0)
        else:
            sf = font(sub_font, sub_cap)
            while tracked_width(sub_text, sf, L.SUB_TRACK) > inner and sf.size > 32:
                sf = font(sub_font, sf.size - 2)
            b = sf.getbbox(sub_text)
            y = L.px(L.SUB_CENTER) - (b[3] - b[1]) // 2 - b[1]
            center_tracked(d, cx, y, sub_text, sf, sub_fill,
                           L.SUB_TRACK, stroke=L.SUB_STROKE)

    # ── 워터마크 (반투명) ─────────────────────────────────
    # 기본은 이미지 안쪽 하단(WM_Y). 다만 sub_box 를 쓰면 자막 박스가 같은 자리에
    # 오므로 겹친다 — 그 경우 이미지 **상단**으로 올린다.
    # style.watermark 로 편별 override (빈 문자열 = 표기 없음 — 란빵 등 다른 계정용, 2026-09-16)
    wm_text = (sc.get("style") or {}).get("watermark", L.WATERMARK)
    if wm_text:
        wf = font(L.F_CH, L.WM_SIZE)
        b = wf.getbbox(wm_text)
        wm_y = L.px(L.WM_Y)
        if (sc.get("style") or {}).get("sub_box"):
            wm_y = bar_bot + 18          # 흰 바가 있으면 그 밑으로 내려간다
        d.text((cx - (b[2] - b[0]) / 2 - b[0], wm_y), wm_text,
               font=wf, fill=(255, 255, 255, L.WM_ALPHA),
               stroke_width=3, stroke_fill=(0, 0, 0, 120))

    # ── 하단 채널 프로필 ──────────────────────────────────
    if L.SHOW_EMBLEM:
        pr, py = L.px(L.PROFILE_R), L.px(L.PROFILE_Y)
        prof = os.path.join(ROOT, "assets", "profile.png")
        if os.path.exists(prof):
            p = Image.open(prof).convert("RGB").resize((pr * 2, pr * 2), Image.LANCZOS)
            mask = Image.new("L", (pr * 2, pr * 2), 0)
            ImageDraw.Draw(mask).ellipse([0, 0, pr * 2, pr * 2], fill=255)
            im.paste(p, (cx - pr, py - pr), mask)
        else:
            d.ellipse([cx - pr, py - pr, cx + pr, py + pr], outline=(90, 90, 90, 255), width=4)

        if sc.get("channel"):
            center_text(d, cx, L.px(L.CHANNEL_Y), sc["channel"],
                        font(L.F_CH, L.SZ_CH), L.CHANNEL_C)

    if character:
        paste_character(im, top=bar_bot if bar_text else None)
    if comment:
        draw_comment(im, comment[0], comment[1])
    if label:
        draw_label(im, label)
    return im


def main():
    if len(sys.argv) < 2:
        sys.exit("사용: python3 pipeline/render.py <slug>")
    if layout_check.main([]) != 0:
        sys.exit("레이아웃이 잠금값과 달라 렌더를 멈춘다.")
    slug = sys.argv[1]
    wd = os.path.join(ROOT, "work", slug)
    sc = json.load(open(os.path.join(wd, "script.json"), encoding="utf-8"))
    timing = json.load(open(os.path.join(wd, "tts", "timing.json"), encoding="utf-8"))

    imgs = sorted(glob.glob(os.path.join(wd, "img", "*.png"))
                  + glob.glob(os.path.join(wd, "img", "*.jpg")))
    if not imgs:
        print("! img/ 가 비어 있음 — 회색 배경으로 렌더")

    out = os.path.join(wd, "frames")
    os.makedirs(out, exist_ok=True)
    for f in glob.glob(os.path.join(out, "*.png")):
        os.remove(f)

    has_char = os.path.exists(os.path.join(ROOT, "assets", "character.png"))
    # style.bar — 흰 바 문구. true 면 hook 에서 'ㄷㄷ' 류 꼬리를 뗀 문장을 쓴다.
    bar_conf = (sc.get("style") or {}).get("bar")
    bar_text = None
    if bar_conf:
        bar_text = bar_conf if isinstance(bar_conf, str) else \
            sc.get("hook", "").replace("ㄷㄷ", "").replace("ㅎ", "").strip()
    manifest, n, t = [], 0, 0.0
    cur_cm, cm_k = None, -1
    cur_lb = None
    # 문장마다 시작 효과음 — 2026-10-10 도입('휙'), 2026-10-16 사용자 지시로 기본 끔
    # ("화면 지나갈 때 툭툭 치는 소리 다 제외"). 다시 켜려면 style.line_sfx: "whoosh"
    line_sfx = (sc.get("style") or {}).get("line_sfx", "")
    for i, tl in enumerate(timing):
        # script.json 의 line["img"] (1-based) 를 우선, 없으면 순환 배정
        if imgs and tl.get("img"):
            img_i = min(int(tl["img"]) - 1, len(imgs) - 1)
        else:
            img_i = i % len(imgs) if imgs else -1
        # 강조어는 script.json 의 line["em"] 이 들고 있다 (timing 에는 없다)
        li = tl.get("i", i)
        ln = sc["lines"][li] if li < len(sc["lines"]) else {}
        ln = ln if isinstance(ln, dict) else {}
        emc = ln.get("em_color")
        if ln.get("comment"):
            cm_k += 1
            cur_cm = (ln["comment"], cm_k)
        if "label" in ln:
            cur_lb = ln["label"]
        norm = " ".join(tl["text"].split())
        spans = em_spans(norm, ln.get("em"))
        chunks = subs.chunk(tl["text"], L.SUB_CHUNK)
        durs = subs.split_duration(chunks, tl["dur"])
        pos = 0
        for c, dur in zip(chunks, durs):
            off = norm.find(c, pos)
            if off < 0:
                off = pos
            pos = off + len(c)
            csp = chunk_spans(c, off, spans)
            # 흰 바는 첫 문장(타이틀 나레이션)을 읽는 동안만 얹힌다
            bt = bar_text if i == 0 else None
            dlg = bool(ln.get("dialogue"))
            base = os.path.join(out, f"ov_{n:03d}.png")
            build_overlay(sc, c, spans=csp, em_color=emc,
                          bar_text=bt, dialogue=dlg, comment=cur_cm, label=cur_lb).save(base)
            char = None
            if has_char:
                char = os.path.join(out, f"ov_{n:03d}_c.png")
                build_overlay(sc, c, character=True, spans=csp,
                              em_color=emc, bar_text=bt, dialogue=dlg, comment=cur_cm, label=cur_lb).save(char)
            # 효과음·흔들림은 문장 시작에만 — 첫 덩어리에만 실어 보낸다 (2026-09-14)
            first = (c == chunks[0])
            sfx = ln.get("sfx") if first else None
            if first and not sfx and i > 0 and not ln.get("outro") and line_sfx:
                sfx = line_sfx
            shake = ln.get("shake") if first else None
            manifest.append({"base": base, "char": char, "text": c,
                             "img": imgs[img_i] if img_i >= 0 else None,
                             "line": i, "start": round(t, 3), "dur": dur,
                             "sfx": sfx, "shake": shake})
            t += dur
            n += 1

    json.dump(manifest, open(os.path.join(out, "manifest.json"), "w",
                             encoding="utf-8"), ensure_ascii=False, indent=2)
    note = " (+캐릭터판)" if has_char else ""
    print(f"✓ 오버레이 {n}장{note} · {len(timing)}문장 · 이미지 {len(imgs)}장 → {out}")


if __name__ == "__main__":
    main()
