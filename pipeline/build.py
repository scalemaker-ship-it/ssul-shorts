#!/usr/bin/env python3
"""[3] 최종 조립 — 이미지를 움직이며 그려 오버레이와 합성하고 mp4 로 뽑는다.

프레임을 디스크에 쓰지 않고 ffmpeg 표준입력으로 바로 흘려보낸다.

애니메이션 3종:
  · 등장   첫 이미지가 검정에서 서서히 밝아지며 살짝 축소되어 자리잡음
  · 설명   구간 내내 아주 천천히 확대/축소 (켄번스). 구간마다 방향을 번갈아 준다
  · 교체   다음 이미지가 오른쪽에서 밀고 들어옴

사용: python3 pipeline/build.py <slug> [--bgm assets/bgm.mp3] [--speed 1.3]
산출: work/<slug>/<slug>.mp4
"""
import sys, os, json, subprocess
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import audio
import layout as L

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CW = L.W                                    # 콘텐츠 창 폭
CH = L.px(L.CONTENT_BOT) - L.px(L.CONTENT_TOP)   # 콘텐츠 창 높이
CY = L.px(L.CONTENT_TOP)


def ease(x):
    """부드럽게 시작하고 부드럽게 끝나는 보간 (0..1)."""
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def cover(img, zoom, ox=0.0, oy=0.0):
    """콘텐츠 창을 채우도록 비율 유지 크롭 후, zoom 배로 확대해 크롭.

    ox/oy 는 -1..1 의 패닝 오프셋 — 확대로 생긴 여유분 안에서 크롭 위치를 민다.
    여유가 없으면(=zoom 1.0, 비율 일치) 자동으로 0 으로 눌린다.
    """
    src_r, box_r = img.width / img.height, CW / CH
    if src_r > box_r:
        nh, nw = CH, int(CH * src_r)
    else:
        nw, nh = CW, int(CW / src_r)
    nw, nh = int(nw * zoom), int(nh * zoom)
    im = img.resize((max(nw, CW), max(nh, CH)), Image.LANCZOS)
    mx, my = (im.width - CW) // 2, (im.height - CH) // 2
    x = int(mx + mx * max(-1.0, min(1.0, ox)))
    y = int(my + my * max(-1.0, min(1.0, oy)))
    return im.crop((x, y, x + CW, y + CH))


def main():
    if len(sys.argv) < 2:
        sys.exit("사용: python3 pipeline/build.py <slug> [--bgm <path>] [--speed 1.3]")
    slug = sys.argv[1]
    # BGM — 기본은 assets/bgm.mp3 (2026-08-31 사용자 확정: 잔잔하게 항상 깐다).
    # --bgm <path> 로 곡을 바꾸고, --no-bgm 으로 끈다.
    bgm = sys.argv[sys.argv.index("--bgm") + 1] if "--bgm" in sys.argv \
        else os.path.join(ROOT, "assets", "bgm.mp3")
    if "--no-bgm" in sys.argv or not os.path.exists(bgm):
        bgm = None
    speed = float(sys.argv[sys.argv.index("--speed") + 1]) if "--speed" in sys.argv else L.SPEED
    # 시작음 — assets/chime.wav 가 있으면 자동으로 맨 앞에 얹는다. --no-chime 로 끈다.
    chime = os.path.join(ROOT, "assets", "chime.wav")
    if "--no-chime" in sys.argv or not os.path.exists(chime):
        chime = None

    wd = os.path.join(ROOT, "work", slug)
    man = json.load(open(os.path.join(wd, "frames", "manifest.json"), encoding="utf-8"))
    # 편별 style override (motion 등). 없으면 빈 dict.
    sc = json.load(open(os.path.join(wd, "script.json"), encoding="utf-8"))
    narr = os.path.join(wd, "tts", "narration.wav")
    total = man[-1]["start"] + man[-1]["dur"]

    # ── 이미지 구간: 같은 이미지를 쓰는 연속 자막을 하나로 묶는다 ──
    segs = []
    for m in man:
        if segs and segs[-1]["img"] == m["img"]:
            segs[-1]["end"] = m["start"] + m["dur"]
        else:
            segs.append({"img": m["img"], "start": m["start"],
                         "end": m["start"] + m["dur"]})

    cache = {}
    def load(p):
        if p not in cache:
            cache[p] = Image.open(p).convert("RGB") if p else None
        return cache[p]

    ov_cache = {}
    def overlay(path):
        if path not in ov_cache:
            ov_cache[path] = Image.open(path).convert("RGBA")
        return ov_cache[path]

    out = os.path.join(wd, f"{slug}.mp4")
    vf = f"setpts=PTS/{speed},format=yuv420p"
    cmd = ["ffmpeg", "-y",
           "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{L.W}x{L.H}", "-r", str(L.FPS), "-i", "-",
           "-i", narr]
    # 완급은 tts.py 가 문장별로 이미 걸어 놨다. speed 는 1.0 이면 건드리지 않는다.
    tempo = f"atempo={speed}," if abs(speed - 1.0) > 1e-6 else ""
    # 마감 체인 — 폰 스피커 EQ → 컴프 → 유튜브 기준 -14 LUFS (audio.py 가 단일 출처)
    # 나레이션은 배속+마감 체인을 먼저 통과시키고, 그 위에 차임·BGM 을
    # **원속도로** 얹는다 — 같이 배속하면 종소리는 딸깍, 음악은 피치가 뜬다.
    # amix 는 normalize=0: 트랙이 늘어도 나레이션 음량이 내려가지 않는다.
    extras = []          # (입력 앞에 붙는 ffmpeg 인자, 필터 라벨)
    idx = 2
    filters = [f"[1:a]{tempo}{audio.POST_CHAIN}[n]"]
    mix = ["[n]"]
    if chime:
        # 시작 '띵~'. adelay 0 = 맨 앞.
        extras += ["-i", chime]
        filters.append(f"[{idx}:a]volume=0.45,adelay=0|0[c]")
        mix.append("[c]")
        idx += 1
    if bgm:
        # 잔잔한 배경음 — 나레이션을 방해하지 않는 낮은 볼륨 + 1초 페이드인.
        extras += ["-stream_loop", "-1", "-i", bgm]
        # 0.10 은 곡 원본이 조용해서(-21dB) 사실상 안 들렸다 → 0.30 (2026-08-31).
        # 나레이션(-14 LUFS)보다 ~17dB 아래 — 잔잔하지만 들리는 수준.
        filters.append(f"[{idx}:a]volume=0.30,afade=t=in:d=1.0[b]")
        mix.append("[b]")
        idx += 1
    if len(mix) > 1:
        filters.append("".join(mix) +
                       f"amix=inputs={len(mix)}:duration=first:normalize=0[a]")
        cmd += extras + ["-filter_complex", ";".join(filters),
                         "-map", "0:v", "-map", "[a]"]
    else:
        cmd += ["-filter_complex", f"[1:a]{tempo}{audio.POST_CHAIN}[a]",
                "-map", "0:v", "-map", "[a]"]
    cmd += ["-vf", vf, "-c:v", "libx264", "-preset", "medium", "-crf", "20",
            "-c:a", "aac", "-b:a", "192k", "-shortest", out]

    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                            stderr=subprocess.PIPE)

    nframes = int(total * L.FPS)
    mi = 0
    for fi in range(nframes):
        t = fi / L.FPS
        while mi + 1 < len(man) and t >= man[mi]["start"] + man[mi]["dur"]:
            mi += 1
        m = man[mi]

        canvas = Image.new("RGB", (L.W, L.H), (0, 0, 0))

        # 현재 이미지 구간과 진행도
        si = 0
        for i, s in enumerate(segs):
            if t >= s["start"]:
                si = i
        s = segs[si]
        span = max(0.001, s["end"] - s["start"])
        p = (t - s["start"]) / span

        img = load(s["img"])
        if img is not None:
            # 설명 구간의 움직임. 기본은 확대↔축소 교대(레이아웃 잠금값)이고,
            # script.json 의 "style": {"motion": true} 를 주면 구간마다 확대·축소·
            # 좌우 패닝·대각 패닝을 돌려써서 슬라이드쇼처럼 보이지 않게 한다.
            style = sc.get("style") or {}
            if style.get("motion"):
                amp = float(style.get("ken_zoom", L.KEN_ZOOM * 1.9))
                e = ease(p)
                mode = si % 5
                if mode == 0:      # 천천히 밀고 들어가기
                    zoom, ox, oy = 1.0 + amp * e, 0.0, 0.0
                elif mode == 1:    # 빠지기
                    zoom, ox, oy = 1.0 + amp * (1 - e), 0.0, 0.0
                elif mode == 2:    # 확대한 채로 왼→오 패닝
                    zoom, ox, oy = 1.0 + amp, -0.7 + 1.4 * e, 0.0
                elif mode == 3:    # 확대한 채로 오→왼 패닝
                    zoom, ox, oy = 1.0 + amp, 0.7 - 1.4 * e, 0.0
                else:              # 살짝 들어가며 위→아래
                    zoom, ox, oy = 1.0 + amp * (0.35 + 0.65 * e), 0.0, -0.6 + 1.2 * e
                cur = cover(img, zoom, ox, oy)
            else:
                if si % 2 == 0:
                    zoom = 1.0 + L.KEN_ZOOM * p
                else:
                    zoom = 1.0 + L.KEN_ZOOM * (1 - p)
                cur = cover(img, zoom)

            dt = t - s["start"]
            if si == 0 and dt < L.INTRO_SEC:
                # 등장: 검정에서 밝아지며 살짝 축소되어 자리잡음
                k = ease(dt / L.INTRO_SEC)
                intro = cover(img, zoom + (1 - k) * 0.06)
                cur = Image.blend(Image.new("RGB", (CW, CH), (0, 0, 0)), intro, k)
                canvas.paste(cur, (0, CY))
            elif si > 0 and dt < L.SLIDE_SEC:
                k = ease(dt / L.SLIDE_SEC)
                prev = load(segs[si - 1]["img"])
                kind = (si % 4) if (sc.get("style") or {}).get("motion") else 0
                if kind == 0:       # 좌로 밀기 — 기본
                    if prev is not None:
                        canvas.paste(cover(prev, 1.0), (int(-CW * k), CY))
                    canvas.paste(cur, (int(CW * (1 - k)), CY))
                elif kind == 1:     # 크로스페이드
                    base = cover(prev, 1.0) if prev is not None else Image.new("RGB", (CW, CH), (0, 0, 0))
                    canvas.paste(Image.blend(base, cur, k), (0, CY))
                elif kind == 2:     # 줌 푸시 — 새 이미지가 커진 채 들어와 자리잡음
                    if prev is not None:
                        canvas.paste(cover(prev, 1.0), (0, CY))
                    zin = cover(img, zoom + (1 - k) * 0.22)
                    base = cover(prev, 1.0) if prev is not None else Image.new("RGB", (CW, CH), (0, 0, 0))
                    canvas.paste(Image.blend(base, zin, min(1.0, k * 1.4)), (0, CY))
                else:               # 위로 밀기
                    if prev is not None:
                        canvas.paste(cover(prev, 1.0), (0, CY - int(CH * k)))
                    canvas.paste(cur, (0, CY + int(CH * (1 - k))))
            else:
                canvas.paste(cur, (0, CY))
        else:
            canvas.paste((127, 127, 127), (0, CY, CW, CY + CH))

        ov = overlay(m["char"] if (m["char"] and t < L.CHAR_SEC) else m["base"])
        frame = Image.alpha_composite(canvas.convert("RGBA"), ov).convert("RGB")

        try:
            proc.stdin.write(frame.tobytes())
        except BrokenPipeError:
            break

    proc.stdin.close()
    err = proc.stderr.read().decode(errors="ignore")
    if proc.wait() != 0:
        print(err[-1500:])
        sys.exit("ffmpeg 실패")

    d = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "format=duration", "-of", "csv=p=0", out],
                       capture_output=True, text=True).stdout.strip()
    print(f"✓ {out}  ({float(d):.1f}초 · {speed}배속 · "
          f"자막 {len(man)}장 · 이미지 {len(segs)}구간 · {nframes}프레임)")

    # 만들었으면 항상 재생 창을 띄운다 — 눈으로 확인하지 않고 넘어가는 일이 없게.
    # 끄고 싶으면 --no-open 을 주거나 SSUL_NO_OPEN=1 을 걸면 된다.
    if "--no-open" not in sys.argv and not os.environ.get("SSUL_NO_OPEN"):
        subprocess.run(["open", out])


if __name__ == "__main__":
    main()
