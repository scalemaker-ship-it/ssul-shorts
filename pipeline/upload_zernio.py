#!/usr/bin/env python3
"""[8] Zernio API 로 유튜브(썰푸는휴지) 업로드·예약.

브라우저(Chrome MCP + Studio) 대신 쓰는 경로다. 제목·설명·첫 댓글·공개범위·
예약 시각을 한 번에 넘길 수 있어 달력/드롭다운 함정이 없다.

    python3 pipeline/upload_zernio.py <slug> --schedule 2026-08-28T07:00:00
    python3 pipeline/upload_zernio.py <slug> --publish        # 즉시 공개
    python3 pipeline/upload_zernio.py <slug>                  # DRY RUN

제목·설명·고정 댓글은 work/<slug>/upload.md 에서 읽는다.
"""
import argparse, json, os, re, sys, urllib.request, urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = "https://zernio.com/api/v1"
CT = "video/mp4"


def key():
    k = os.getenv("ZERNIO_API_KEY")
    if k:
        return k.strip()
    p = os.path.join(ROOT, ".env")
    for ln in open(p, encoding="utf-8"):
        if ln.strip().startswith("ZERNIO_API_KEY"):
            return ln.split("=", 1)[1].strip().strip('"').strip("'")
    sys.exit("ZERNIO_API_KEY 없음 — .env 를 확인하세요")


def api(method, path, k, body=None, raw=None, ctype=None):
    url = path if path.startswith("http") else BASE + path
    data, headers = None, {}
    if k:
        headers["Authorization"] = "Bearer " + k
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    elif raw is not None:
        data = raw
        headers["Content-Type"] = ctype or "application/octet-stream"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            t = r.read().decode()
            return json.loads(t) if t.strip().startswith(("{", "[")) else t
    except urllib.error.HTTPError as e:
        sys.exit(f"[Zernio] {method} {url} 실패 {e.code}: {e.read().decode()[:600]}")


def section(md, name):
    """upload.md 의 `## <name>` 블록을 다음 `## ` 전까지 뽑는다."""
    m = re.search(rf"^##\s*{re.escape(name)}\s*$(.*?)(?=^##\s|\Z)", md,
                  re.M | re.S)
    return m.group(1).strip() if m else ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slug")
    ap.add_argument("--schedule", help="ISO 예약 시각 (예: 2026-08-28T07:00:00)")
    ap.add_argument("--timezone", default="Asia/Seoul")
    ap.add_argument("--publish", action="store_true", help="즉시 공개")
    ap.add_argument("--visibility", default="public",
                    choices=["public", "unlisted", "private"])
    ap.add_argument("--no-comment", action="store_true", help="첫 댓글 생략")
    a = ap.parse_args()

    wd = os.path.join(ROOT, "work", a.slug)
    mp4 = os.path.join(wd, f"{a.slug}.mp4")
    if not os.path.exists(mp4):
        sys.exit(f"영상 없음: {mp4}")
    md = open(os.path.join(wd, "upload.md"), encoding="utf-8").read()

    title = section(md, "제목").strip()
    desc = section(md, "설명").strip()
    comment = section(md, "고정 댓글").strip()
    if not title:
        sys.exit("upload.md 에 '## 제목' 이 없음")
    if len(title) > 100:
        sys.exit(f"제목이 100자를 넘음 ({len(title)}자) — YouTube 한도")

    k = key()
    accs = api("GET", "/accounts", k)
    accs = accs.get("accounts", accs if isinstance(accs, list) else [])
    yt = [x for x in accs if str(x.get("platform")).lower() == "youtube"]
    if not yt:
        sys.exit("Zernio 에 연결된 유튜브 계정이 없음")
    acc = yt[0]
    acc_id = acc["_id"]
    print(f"▶ 계정: {acc.get('displayName')} (@{acc.get('username')})")

    size = os.path.getsize(mp4)
    pre = api("POST", "/media/presign", k,
              body={"filename": os.path.basename(mp4), "contentType": CT})
    up = pre.get("uploadUrl") or pre.get("upload_url")
    pub = pre.get("publicUrl") or pre.get("public_url")
    with open(mp4, "rb") as f:
        api("PUT", up, None, raw=f.read(), ctype=CT)
    print(f"  ✔ 업로드 {size/1e6:.1f}MB → {pub[:70]}...")

    # 이미지가 전부 생성물이라 합성 콘텐츠 고지를 켠다 (실사풍 인물이 나온다)
    ysd = {
        "title": title,
        "visibility": a.visibility,
        "madeForKids": False,
        "containsSyntheticMedia": True,
        "categoryId": "22",
    }
    if comment and not a.no_comment:
        ysd["firstComment"] = comment

    payload = {
        "content": desc,
        "mediaItems": [{"url": pub, "type": "video",
                        "filename": os.path.basename(mp4),
                        "size": size, "mimeType": CT}],
        "platforms": [{"platform": "youtube", "accountId": acc_id,
                       "platformSpecificData": ysd}],
    }
    if a.schedule:
        payload["scheduledFor"] = a.schedule
        payload["timezone"] = a.timezone
    elif a.publish:
        payload["publishNow"] = True

    if not a.schedule and not a.publish:
        print("\n[DRY RUN] 실제로 올리지 않음. 아래 페이로드로 나갑니다:")
        print(json.dumps(payload, ensure_ascii=False, indent=2)[:2000])
        return

    res = api("POST", "/posts", k, body=payload)
    when = f"예약 {a.schedule} ({a.timezone})" if a.schedule else "즉시 공개"
    print(f"\n✅ {when}")
    print(json.dumps(res, ensure_ascii=False, indent=2)[:900])


if __name__ == "__main__":
    main()
