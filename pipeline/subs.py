#!/usr/bin/env python3
"""자막 청킹 — 한 문장을 10자 내외로 '자연스럽게' 끊는다.

기계적으로 10자에서 자르면 조사나 어절이 두 동강 난다.
어절(공백) 경계만 자르되, 목표 길이에 가장 가까워지는 지점을 고른다.
"""

import re

# 이 어절들은 앞 어절에 붙여 읽는 게 자연스럽다 (뒤로 넘기지 않는다)
GLUE = ("것.", "것", "거.", "거", "수", "때", "줄", "뿐.", "뿐", "만큼", "채", "적")

# 숫자(또는 숫자+억/만/천/백/조)로 끝나는 어절 뒤에 단위 어절이 오면
# 절대 가르지 않는다 — "2,792억 / 원을" 처럼 갈라지면 읽기가 끊긴다 (2026-08-30)
_NUM_TAIL = re.compile(r"[\d,.]+[억만천백조년원명개살주위번배]?$")
UNIT_HEAD = ("원", "년", "명", "개", "살", "톤", "배", "조", "억", "만", "천",
             "위", "일", "주", "시간", "분", "초", "퍼센트", "프로", "권", "장",
             "건", "쌍", "번", "달", "평", "리터", "킬로", "그램", "포인트")


def _sticky(prev, w):
    return bool(_NUM_TAIL.search(prev)) and w.startswith(UNIT_HEAD)


def chunk(text, target=10):
    """text 를 target 자 내외의 덩어리 리스트로."""
    words = text.split()
    if not words:
        return [text]

    out, cur = [], ""
    for i, w in enumerate(words):
        cand = f"{cur} {w}".strip()
        # 아직 목표에 못 미치면 계속 붙인다
        if len(cur) == 0:
            cur = cand
            continue
        # 붙였을 때와 안 붙였을 때 중 target 에 더 가까운 쪽
        if (abs(len(cand) - target) <= abs(len(cur) - target) or w in GLUE
                or _sticky(words[i - 1], w)):
            cur = cand
        else:
            out.append(cur)
            cur = w
    if cur:
        out.append(cur)

    # 너무 짧은 덩어리는 앞과 합친다 ("안 함." 처럼 홀로 뜨면 어색하다)
    i = 1
    while i < len(out):
        if len(out[i]) <= 6 and len(out[i - 1]) + len(out[i]) <= target + 8:
            out[i - 1] = f"{out[i - 1]} {out[i]}"
            out.pop(i)
        else:
            i += 1
    return out


def split_duration(chunks, total):
    """덩어리 글자수 비례로 시간을 나눈다 (읽는 속도가 일정하다고 보고)."""
    n = sum(len(c) for c in chunks) or 1
    ds = [total * len(c) / n for c in chunks]
    # 반올림 오차를 마지막에 몰아 총합을 보존
    ds = [round(d, 3) for d in ds]
    ds[-1] = round(total - sum(ds[:-1]), 3)
    return ds


if __name__ == "__main__":
    for s in [
        "사람이 많을수록 아무도 안 돕는 이유?",
        "사람이 많을수록 책임이 나눠진다고 느끼는 것.",
        "나쁜 사람은 없었음. 지목당한 사람이 없었을 뿐.",
        "파란 옷 입은 분, 하고 딱 집어야 함.",
    ]:
        cs = chunk(s)
        print(f"{s}\n  → {cs}  {[len(c) for c in cs]}\n")
