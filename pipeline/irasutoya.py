#!/usr/bin/env python3
"""いらすとや 캐릭터 받기 — 투명 PNG + 흰 테두리 → work/<slug>/img/ir_<이름>.png (2026-10-13)

  python3 pipeline/irasutoya.py search 囚人            # 후보 목록(번호·제목·파일명)
  python3 pipeline/irasutoya.py get <slug> judge 裁判官 [번호]   # 번호번째 후보를 ir_judge.png 로

쓰는 법: script.json 줄/컷에 "char": "ir_judge" (또는 {"name","side","scale"}) — to_remotion.py 가 overlay2 로 얹는다.
いらすとや 무료 이용 조건: 한 작품(영상 한 편)에 20장 이하.
"""
import io, json, os, re, sys, urllib.parse, urllib.request
from PIL import Image, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = {"User-Agent": "Mozilla/5.0 (Macintosh) Chrome/141"}


def search(q, n=8):
    u = "https://www.irasutoya.com/feeds/posts/default?alt=json&max-results=%d&q=%s" % (n, urllib.parse.quote(q))
    j = json.load(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=20))
    out = []
    for e in j["feed"].get("entry", []):
        imgs = re.findall(r'src="([^"]+\.png)"', e["content"]["$t"])
        if imgs:
            out.append((e["title"]["$t"], re.sub(r"/s\d+(-c)?/", "/s800/", imgs[0])))
    return out


def outline(im, pad=16, w=17):
    c = Image.new("RGBA", (im.width + 2 * pad, im.height + 2 * pad), (0, 0, 0, 0))
    c.paste(im, (pad, pad), im)
    a = c.getchannel("A").point(lambda v: 255 if v > 40 else 0).filter(ImageFilter.MaxFilter(w))
    out = Image.composite(Image.new("RGBA", c.size, (255, 255, 255, 255)), Image.new("RGBA", c.size, (255, 255, 255, 0)), a)
    out.alpha_composite(c)
    return out


def get(slug, name, q, idx=0):
    cands = search(q)
    title, url = cands[idx]
    im = Image.open(io.BytesIO(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30).read())).convert("RGBA")
    bb = im.getchannel("A").point(lambda v: 255 if v > 10 else 0).getbbox()
    dst = os.path.join(ROOT, "work", slug, "img", f"ir_{name}.png")
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    outline(im.crop(bb)).save(dst)
    print(f"✓ ir_{name}.png ← {title} ({url.split('/')[-1]})")


if __name__ == "__main__":
    if sys.argv[1] == "search":
        for i, (t, u) in enumerate(search(sys.argv[2])):
            print(i, t, u.split("/")[-1])
    else:
        get(sys.argv[2], sys.argv[3], sys.argv[4], int(sys.argv[5]) if len(sys.argv) > 5 else 0)
