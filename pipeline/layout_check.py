#!/usr/bin/env python3
"""레이아웃 잠금 — layout.py 가 잠금 스냅샷과 같은지 확인한다.

bystander 편을 만든 시점의 값이 기준이다. 이후 영상이 같은 화면으로 나오게
하려면 layout.py 를 건드릴 때마다 이 검사를 통과해야 한다.

    python3 pipeline/layout_check.py            # 확인만 (다르면 exit 1)
    python3 pipeline/layout_check.py --update   # 의도적으로 규격을 바꿨을 때 재잠금

render.py 가 렌더 전에 부르므로, 어긋난 채로는 프레임이 만들어지지 않는다.

검사는 두 겹이다:
  1) layout.py **소스**를 직접 파싱한 값 vs 잠금 파일
  2) 소스값 vs 실제 `import layout` 이 내놓는 값

2번이 필요한 이유 — macOS 시스템 파이썬은 바이트코드를
`~/Library/Caches/com.apple.python/` 에 캐시한다. 무효화 기준이 (mtime, 크기)라
`0.745` → `0.760` 처럼 **길이가 같은 값을 같은 초에 고치면 낡은 .pyc 가 그대로
쓰인다.** 소스는 새 값인데 렌더는 옛 값으로 도는 상태가 되므로 따로 잡아준다.
"""

import ast
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "layout.py"
LOCK = HERE / "layout.lock.json"


def _norm(v):
    """튜플/리스트 표기 차이를 없앤다 — JSON 왕복하면 튜플이 리스트가 되므로."""
    return [_norm(x) for x in v] if isinstance(v, (list, tuple)) else v


def _resolve(node, known):
    """리터럴 / 다른 상수 참조(TITLE_1 = WHITE) / f-string 조합(F_TITLE)을 값으로 편다."""
    try:
        return _norm(ast.literal_eval(node))
    except (ValueError, SyntaxError):
        pass
    if isinstance(node, ast.Name):
        return known.get(node.id)
    if isinstance(node, ast.JoinedStr):
        parts = []
        for p in node.values:
            if isinstance(p, ast.Constant):
                parts.append(str(p.value))
            elif isinstance(p, ast.FormattedValue):
                v = _resolve(p.value, known)
                if v is None:
                    return None
                parts.append(str(v))
            else:
                return None
        return "".join(parts)
    return None


def from_source() -> dict:
    """layout.py 소스를 파싱해 상수(대문자 이름)를 읽는다. import 를 타지 않는다."""
    tree = ast.parse(SRC.read_text(encoding="utf-8"))
    out = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            # W, H = 1080, 1920 처럼 여러 개를 한 줄에 대입하는 형태
            if isinstance(target, ast.Tuple) and isinstance(node.value, ast.Tuple):
                for t, v in zip(target.elts, node.value.elts):
                    if isinstance(t, ast.Name) and t.id.isupper():
                        val = _resolve(v, out)
                        if val is not None:
                            out[t.id] = val
                continue
            if not isinstance(target, ast.Name) or not target.id.isupper():
                continue
            val = _resolve(node.value, out)
            if val is not None:
                out[target.id] = val
    return dict(sorted(out.items()))


def from_import() -> dict:
    """실제로 import 했을 때의 값 — 낡은 바이트코드가 쓰이면 여기서 드러난다."""
    sys.path.insert(0, str(HERE))
    import layout

    return {k: _norm(getattr(layout, k)) for k in sorted(dir(layout)) if k.isupper()}


def purge_bytecode_cache() -> list:
    """낡은 .pyc 를 지운다 — 로컬 __pycache__ 와 macOS 사용자 캐시 양쪽."""
    removed = []
    local = HERE / "__pycache__"
    if local.exists():
        shutil.rmtree(local)
        removed.append(str(local))
    mac = Path.home() / "Library/Caches/com.apple.python" / str(HERE).lstrip("/")
    if mac.exists():
        shutil.rmtree(mac)
        removed.append(str(mac))
    return removed


def diff(cur, lock, left="잠금", right="현재"):
    msgs = []
    for k in sorted(set(lock) | set(cur)):
        if k not in cur:
            msgs.append(f"  - {k}: 사라짐 ({left} {lock[k]!r})")
        elif k not in lock:
            msgs.append(f"  + {k}: 새로 생김 ({cur[k]!r})")
        elif cur[k] != lock[k]:
            msgs.append(f"  ~ {k}: {left} {lock[k]!r} → {right} {cur[k]!r}")
    return msgs


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    src = from_source()

    if "--update" in argv:
        purge_bytecode_cache()
        LOCK.write_text(json.dumps(src, ensure_ascii=False, indent=2) + "\n")
        print(f"재잠금 완료 ({len(src)}개 상수) → {LOCK.relative_to(HERE.parent)}")
        return 0

    if not LOCK.exists():
        print(f"잠금 파일이 없다. 먼저 --update 로 만든다: {LOCK}")
        return 1

    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    msgs = diff(src, lock)
    if msgs:
        print("레이아웃이 잠금값과 다르다:")
        print("\n".join(msgs))
        print(
            "\n실수라면 layout.py 를 되돌린다.\n"
            "의도한 변경이면 docs/layout-lock.md 에 이유를 적고 --update 로 재잠금한다."
        )
        return 1

    # 소스는 맞는데 import 결과가 다르면 = 낡은 바이트코드가 쓰이고 있다
    live = from_import()
    stale = [k for k, v in src.items() if k in live and live[k] != v]
    if stale:
        removed = purge_bytecode_cache()
        print("낡은 바이트코드가 쓰이고 있었다 (소스와 import 값이 다름):")
        for k in stale:
            print(f"  ~ {k}: 소스 {src[k]!r} vs import {live[k]!r}")
        print("캐시를 지웠다:")
        for r in removed:
            print(f"  {r}")
        print("다시 실행하면 통과한다.")
        return 1

    print(f"레이아웃 일치 ({len(src)}개 상수)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
