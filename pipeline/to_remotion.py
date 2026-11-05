#!/usr/bin/env python3
"""[영상화] 템플릿1 대본·음성을 Remotion(templates/2) 으로 렌더 — 컷 확대·펀치·흔들림·댓글 카드.

2026-10-10 사용자 지시: 레퍼런스(한입썰 https://www.youtube.com/shorts/AoAK3YS2I8c)처럼
"이미지 확대, 효과음, 리모션 사용해서 좀 더 영상처럼" · 슬라이드 넘어갈 때 소리는 넣지 않는다.

사용: python3 pipeline/to_remotion.py <slug> [--no-render]
  전제: work/<slug>/script.json · img/NN.png · tts/line_NNN.wav + timing.json (tts.py 까지 끝난 상태)
산출: templates/2/public/<slug>/*.png · <slug>-mix.mp3 · <slug>-chunks.srt · src/<slug>Data.ts (Root 등록)
      → work/<slug>/<slug>.mp4

script.json 줄 옵션
  "img": n                        그 줄 첫 컷
  "clip": "c_raw"                 촬영본 컷(work/<slug>/clips/c_raw.mp4, 1080 정사각·무음) — cuts 안에서도 img 대신 쓴다
  "cuts": [{"img": n, "chunk": k, "punch": 0.12, "shake": true, "sticker": "shock",
            "focus": [x, y, zoom]}]   자막 덩어리 k 번째부터 바뀌는 컷(문장 안에서 여러 컷)
  "punch"/"shake"/"sticker"/"dim"  그 줄 첫 컷에 거는 연출
  "sfx": "dudung" | ["scratch_vinyl", "crowd_laugh"]  문장 시작 효과음 — 샘플러 이름(assets/sfx/ic/_목록.txt) 그대로 OK(여러 개면 0.25초 간격)(감정 포인트에만 — 전환음은 없음)
  "comment": {...}                 하단 댓글 카드(다음 댓글까지 유지)
"""
import json, math, os, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import audio, subs
import layout as L

ROOT = os.path.dirname(HERE)
T2 = os.path.join(ROOT, "templates", "2")
FPS = 30
SFX_VOL = {"sizzle": 0.75, "dudung": 0.8, "thud": 0.8, "eng": 0.5, "ding": 0.45, "cash": 0.5, "siren": 0.4,
           "whoosh": 0.45, "boing": 0.5, "tick": 0.5, "pop": 0.4}
CARD_STYLES = ["yt", "fm", "nate", "naver", "dc", "instiz"]
# 카메라 이동 프리셋 [x, y, 배율] → [x, y, 배율] (2026-10-10 "왼>오, 좌하>우상, 확대>축소 등 다채롭게")
MOVES = {
    "ZIN": [[0.5, 0.5, 1.0], [0.5, 0.5, 1.28]],
    "ZOUT": [[0.5, 0.5, 1.32], [0.5, 0.5, 1.0]],
    "LR": [[0.1, 0.5, 1.15], [0.9, 0.5, 1.15]],
    "RL": [[0.9, 0.5, 1.15], [0.1, 0.5, 1.15]],
    "BLTR": [[0.2, 0.8, 1.3], [0.8, 0.2, 1.3]],
    "TRBL": [[0.8, 0.2, 1.3], [0.2, 0.8, 1.3]],
    "TLBR": [[0.2, 0.2, 1.3], [0.8, 0.8, 1.3]],
    "BRTL": [[0.8, 0.8, 1.3], [0.2, 0.2, 1.3]],
}
MOVE_CYCLE = ["ZIN", "LR", "BLTR", "ZOUT", "RL", "TLBR", "ZIN", "TRBL", "ZOUT", "BRTL"]


SFX_REL = 0.56  # 효과음 음량 = 나레이션의 0.56배 (2026-10-10 0.8 → 30% 줄임)
# 2026-10-11 이슈쿠키 효과음 샘플러 141개(assets/sfx/ic/, 번호표 _목록.txt) 를 쓴다 — 감정 이름은 샘플러 소리로 바꿔 낸다.
#   script.json "sfx" 에 샘플러 파일 이름(예 "crowd_laugh", "scratch_vinyl")을 바로 써도 된다. qping 은 핑 스티커 전용이라 합성음 유지
SFX_ALIAS = {"click": "click_ui", "dudung": "hit_dun_dun", "pang": "pop_long",
             "dingring": "correct_notif", "sparkle": "notify_fairy"}


def sfx_path(name):
    name = SFX_ALIAS.get(name, name)
    for d in ("ic", ""):
        p = os.path.join(ROOT, "assets", "sfx", d, f"{name}.wav")
        if os.path.exists(p):
            return p
    return None


def active_rms(path, af=None):
    """소리가 나는 구간(최대 대비 -40dB 이상, 10ms 창)의 RMS"""
    import numpy as np
    cmd = ["ffmpeg", "-v", "error", "-i", path] + (["-af", af] if af else []) + ["-f", "f32le", "-ac", "1", "-ar", "44100", "-"]
    y = np.frombuffer(subprocess.run(cmd, capture_output=True).stdout, np.float32)
    if not len(y):
        return 0.0
    w = 441
    fr = np.sqrt(np.mean(y[: len(y) // w * w].reshape(-1, w) ** 2, axis=1))
    act = fr[fr > fr.max() * 0.01]
    return float(np.sqrt(np.mean(act ** 2))) if len(act) else 0.0


def ms(t):
    return int(round(t * 1000))


def srt_time(t):
    h, r = divmod(ms(t), 3600000)
    m, r = divmod(r, 60000)
    s, r = divmod(r, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{r:03d}"


def camel(slug):
    return "".join(p.capitalize() for p in slug.replace("-", "_").split("_"))


def main():
    slug = sys.argv[1]
    wd = os.path.join(ROOT, "work", slug)
    sc = json.load(open(os.path.join(wd, "script.json"), encoding="utf-8"))
    tm = json.load(open(os.path.join(wd, "tts", "timing.json"), encoding="utf-8"))
    sp = L.SPEED
    pub = os.path.join(T2, "public")
    os.makedirs(os.path.join(pub, slug), exist_ok=True)

    # ── 자막 덩어리 · 컷 · 효과음 · 댓글 (전부 배속 후 시각) ──
    cues, scenes, sfx, cards = [], [], [], []
    used = set()
    used_clips = set()
    for i, t in enumerate(tm):
        ln = sc["lines"][t.get("i", i)]
        ln = ln if isinstance(ln, dict) else {"text": ln}
        chunks = subs.chunk(ln["text"], L.SUB_CHUNK)   # 자막은 대본(script.json) 기준 — timing.json 문구는 낡을 수 있다
        durs = subs.split_duration(chunks, t["dur"])
        st = [t["start"] + sum(durs[:k]) for k in range(len(chunks))]
        for c, a, d in zip(chunks, st, durs):
            cues.append((a / sp, (a + d) / sp, c))
        line_start = t["start"] / sp
        # 물음표 문장 → 노란 ? 핑 + "띵-딩" (2026-10-10). 대사 제외
        #   style.qping=false 면 끈다 (2026-10-13 "물음표 구리니까 빼고")
        if ln["text"].strip().endswith("?") and not ln.get("dialogue") and sc.get("style", {}).get("qping", True):
            ln = dict(ln, sticker="ping", sfx="qping")
        cut_list = [dict(img=ln.get("img"), clip=ln.get("clip"), chunk=0, punch=ln.get("punch"), shake=ln.get("shake"),
                         sticker=ln.get("sticker"), dim=ln.get("dim"), focus=ln.get("focus"), move=ln.get("move"),
                         char=ln.get("char"))] + list(ln.get("cuts", []))
        for cu in cut_list:
            k = min(cu.get("chunk", 0), len(chunks) - 1)
            if cu.get("sfx"):
                sfx.append((st[k] / sp, cu["sfx"]))   # 컷이 바뀌는 순간 효과음
            if cu.get("clip"):
                # 촬영본 컷 — work/<slug>/clips/<이름>.mp4 (1080 정사각·무음으로 미리 잘라 둔다)
                clip = f"{cu['clip']}.mp4"
                used_clips.add(clip)
                s = {"startMs": ms(st[k] / sp), "video": f"{slug}/{clip}"}
                if scenes and scenes[-1]["startMs"] == s["startMs"]:
                    scenes[-1] = s
                else:
                    scenes.append(s)
                continue
            if not cu.get("img"):
                continue
            img = f"{int(cu['img']):02d}.png"
            used.add(img)
            s = {"startMs": ms(st[k] / sp), "image": f"{slug}/{img}"}
            if cu.get("punch"):
                s["punchAtMs"] = 0
                s["punchScale"] = cu["punch"]
            if cu.get("shake"):
                s["shake"] = {"atMs": 0, "amount": 16}
            if cu.get("sticker"):
                s["stickers"] = [{"kind": cu["sticker"], "x": 0.82, "y": 0.2, "atMs": 150,
                                  **({"size": 0.62} if cu["sticker"] == "ping" else {})}]
            if cu.get("dim"):
                s["dim"] = {"fromMs": 400, "amount": 0.45}
            if cu.get("char"):
                # 캐릭터 누끼 오버레이 (2026-10-13, いらすとや) — "char": "ir_judge" 또는 {"name","side","scale"}
                #   work/<slug>/img/<name>.png (투명 PNG). 한 작품 20장 이하가 いらすとや 무료 조건
                ch = cu["char"] if isinstance(cu["char"], dict) else {"name": cu["char"]}
                cimg = f"{ch['name']}.png"
                used.add(cimg)
                s["overlay2"] = {"image": f"{slug}/{cimg}", "atMs": 120, "side": ch.get("side", "right"),
                                 "scale": ch.get("scale", 0.3)}
            if cu.get("focus"):
                # 부분 확대 — 전체에서 그 지점으로 다가간다
                x, y, z = cu["focus"]
                s["camera"] = {"from": [0.5, 0.5, 1.0], "to": [x, y, z]}
            else:
                mv = cu.get("move") or MOVE_CYCLE[len(scenes) % len(MOVE_CYCLE)]
                f, t = MOVES[mv]
                s["camera"] = {"from": f, "to": t}
            if scenes and scenes[-1]["startMs"] == s["startMs"]:
                scenes[-1] = s
            else:
                scenes.append(s)
        # 나레이션 문장 시작마다 효과음 (2026-10-10 — 해결=sparkle, 화남·어이없음=dudung(knife 는 10-10 사용자 제외), 숫자=pang,
        #   알림·질문=dingring, 그 외 click). 대사·아웃트로는 기본값 없음. 끄려면 "sfx": ""
        if "sfx" not in ln and not (ln.get("dialogue") or ln.get("outro")):
            ln = dict(ln, sfx="click")
        if ln.get("sfx"):
            names = ln["sfx"] if isinstance(ln["sfx"], list) else [ln["sfx"]]
            for j, nm in enumerate(names):
                sfx.append((line_start + 0.25 * j, nm))
        if ln.get("comment"):
            if cards:
                cards[-1]["hideMs"] = ms(line_start)
            cm = ln["comment"]
            cards.append({"text": cm["text"], "style": CARD_STYLES[len(cards) % len(CARD_STYLES)],
                          **({"likes": cm["likes"], "dislikes": 0} if "likes" in cm else {}), "showMs": ms(line_start), "hideMs": 0})
    total = tm[-1]["start"] / sp + tm[-1]["dur"] / sp + 0.35
    if cards:
        cards[-1]["hideMs"] = ms(total)

    for f in used:
        shutil.copy(os.path.join(wd, "img", f), os.path.join(pub, slug, f))
    for f in used_clips:
        shutil.copy(os.path.join(wd, "clips", f), os.path.join(pub, slug, f))
    with open(os.path.join(pub, f"{slug}-chunks.srt"), "w", encoding="utf-8") as f:
        for n, (a, b, c) in enumerate(cues, 1):
            f.write(f"{n}\n{srt_time(a)} --> {srt_time(b)}\n{c}\n\n")

    # ── 소리: 나레이션(배속+마감) + BGM + 감정 포인트 효과음 ──
    narr = os.path.join(wd, "tts", "narration.wav")
    bgm = os.path.join(ROOT, "assets", "bgm.mp3")
    cmd = ["ffmpeg", "-y", "-v", "error", "-i", narr]
    fl = [f"[0:a]atempo={sp},{audio.POST_CHAIN}[n]"]
    mix = ["[n]"]
    idx = 1
    if os.path.exists(bgm) and "--no-bgm" not in sys.argv:
        cmd += ["-stream_loop", "-1", "-i", bgm]
        bv = sc.get("style", {}).get("bgm_vol", 0.30)
        fl.append(f"[{idx}:a]volume={bv},afade=t=in:d=1.0[b]"); mix.append("[b]"); idx += 1
    # 촬영본 컷의 현장음(고기 굽는 소리) — 그 컷이 화면에 있는 동안만 깐다. 무음 클립(-an)은 건너뜀
    cv = sc.get("style", {}).get("clip_vol", 0.5)
    for n, scn in enumerate(scenes):
        if not scn.get("video"):
            continue
        src = os.path.join(wd, "clips", os.path.basename(scn["video"]))
        has_a = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index",
                                "-of", "csv=p=0", src], capture_output=True, text=True).stdout.strip()
        if not has_a or cv <= 0:
            continue
        a = scn["startMs"] / 1000
        b = scenes[n + 1]["startMs"] / 1000 if n + 1 < len(scenes) else total
        d, dl = b - a, ms(a)
        cmd += ["-stream_loop", "-1", "-i", src]
        fl.append(f"[{idx}:a]atrim=0:{d:.3f},asetpts=PTS-STARTPTS,volume={cv},"
                  f"afade=t=in:d=0.08,afade=t=out:st={max(0, d - 0.12):.3f}:d=0.12,adelay={dl}|{dl}[c{idx}]")
        mix.append(f"[c{idx}]"); idx += 1
    narr_rms = active_rms(narr, f"atempo={sp},{audio.POST_CHAIN}")
    for t0, name in sfx:
        p = sfx_path(name)
        if not p:
            print(f"! 효과음 없음: {name}")
            continue
        cmd += ["-i", p]
        d = ms(t0)
        # 효과음 = 나레이션 음량 × 0.8 (2026-10-10 사용자 지시) — 소리마다 실제 음량을 재서 맞춘다
        g = SFX_REL * narr_rms / max(active_rms(p), 1e-6)
        fl.append(f"[{idx}:a]volume={g:.3f},adelay={d}|{d}[s{idx}]"); mix.append(f"[s{idx}]"); idx += 1
    fl.append("".join(mix) + f"amix=inputs={len(mix)}:duration=first:normalize=0,atrim=0:{total:.2f}[a]")
    cmd += ["-filter_complex", ";".join(fl), "-map", "[a]", "-ar", "44100", "-b:a", "192k",
            os.path.join(pub, f"{slug}-mix.mp3")]
    subprocess.run(cmd, check=True)

    # ── 제목: 템플릿1(render.py) 타이틀을 그대로 떠서 이미지로 (2026-10-10 "기존 휴지 타이틀 스타일 유지") ──
    import render
    # 영역도 템플릿1 그대로(제목 0~528 · 이미지 528~1363) — 2026-10-10 "타이틀 위치 기존 레이아웃 유지"
    ov = render.build_overlay(sc, " ")
    y1, y2 = L.px(L.CONTENT_TOP), L.px(L.CONTENT_BOT)
    title = ov.crop((0, 0, L.W, y1)).convert("RGB")
    title.save(os.path.join(pub, slug, "title.png"))

    # ── Data.ts + Root 등록 ──
    name = camel(slug)
    data = {
        "titleLine1": sc.get("title_line1", ""), "titleLine2": sc.get("title_line2", ""),
        "titleFit": "equal", "titleImage": f"{slug}/title.png", "zones": {"title": y1, "stage": y2 - y1},
        "audio": f"{slug}-mix.mp3", "srt": f"{slug}-chunks.srt",
        "captionStyle": "tissue", "sceneFadeFrames": 0,
        "durationInFrames": math.ceil(total * FPS),
        "scenes": scenes,
    }
    if cards:
        data["commentCards"] = cards
    ts = (f'import type {{ ShortData }} from "./videoTypes";\n\n'
          f'// 자동 생성 — pipeline/to_remotion.py ({slug}). 손으로 고치지 말고 script.json 을 고친다\n'
          f'export const {slug}Data: ShortData = {json.dumps(data, ensure_ascii=False, indent=2)};\n')
    open(os.path.join(T2, "src", f"{slug}Data.ts"), "w", encoding="utf-8").write(ts)
    root = os.path.join(T2, "src", "Root.tsx")
    r = open(root, encoding="utf-8").read()
    if f"{slug}Data" not in r:
        imp = f'import {{ {slug}Data }} from "./{slug}Data";\n'
        r = r.replace('import { Composition } from "remotion";\n', 'import { Composition } from "remotion";\n' + imp, 1)
        comp = (f'      <Composition\n        id="Short{name}"\n        component={{Short}}\n'
                f'        durationInFrames={{{slug}Data.durationInFrames}}\n        fps={{30}}\n        width={{1080}}\n'
                f'        height={{1920}}\n        defaultProps={{{{ data: {slug}Data }}}}\n      />\n')
        k = r.rfind("    </>")
        r = r[:k] + comp + r[k:]
        open(root, "w", encoding="utf-8").write(r)
    print(f"✓ Remotion 데이터 — 컷 {len(scenes)} · 자막 {len(cues)} · 효과음 {len(sfx)} · 댓글 {len(cards)} · {total:.1f}초")
    if "--no-render" in sys.argv:
        return
    out = os.path.join(T2, "out", f"{slug}.mp4")
    subprocess.run(["npx", "remotion", "render", "src/index.ts", f"Short{name}", out,
                    "--timeout=120000", "--concurrency=4", "--log=error"], cwd=T2, check=True)
    dst = os.path.join(wd, f"{slug}.mp4")
    shutil.copy(out, dst)
    print(f"✓ {dst}")
    if "--no-open" not in sys.argv:
        subprocess.run(["open", dst])


if __name__ == "__main__":
    main()
