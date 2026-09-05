---
name: codex-image
description: >-
  자연어 이미지 생성 요청을 codex exec의 내장 이미지 생성 도구로 CLI 처리해 PNG를 만들고 인라인으로
  보여준 뒤 ./codex-images/ 에 저장한다. 텍스트→이미지, 참조이미지 편집(이미지+텍스트→이미지),
  비율 키워드(유튜브 썸네일·인스타 세로 등), 여러 장(N장) 생성을 지원한다.
  트리거 예 — "고양이 기사 이미지 만들어줘", "~그려줘", "~이미지 생성해줘",
  "유튜브 썸네일 만들어줘", "인스타용 세로 이미지", "이 사진을 지브리 스타일로 바꿔줘",
  "/codex-image". 단일 정지 이미지 전용 — "영상/비디오" 요청에는 발동하지 말 것(make-ai-video 담당).
---

# codex-image

`codex exec`의 **내장 이미지 생성 도구**를 호출해 정지 이미지(PNG)를 만든다.
OpenAI API 키는 필요 없다 — codex의 ChatGPT 인증(`~/.codex/auth.json`)을 사용한다.

## 발동 / 비발동

- **발동**: 사용자가 정지 이미지를 만들거나 그려달라고 할 때, 썸네일/아이콘/일러스트/사진풍 이미지
  요청, 기존 이미지를 다른 스타일로 바꿔달라는 편집 요청.
- **비발동**: "영상/비디오/유튜브 영상 만들어줘"는 이 스킬이 아니라 `make-ai-video`.
  - **"썸네일 만들어줘" / 채널 브랜드 유튜브 썸네일**(본인 캐릭터 + CTR 카피 + 텍스트 합성)은
    `make-thumbnail` 스킬이 담당한다 → 이 경우 codex-image는 발동하지 말 것.
  - codex-image는 그 외 일반 정지 이미지/일러스트/아이콘/스타일 변환용. (make-thumbnail이
    내부적으로 codex-image의 gen.sh를 호출해 배경을 만든다.)

## 절차

### 1. 요청 파싱
사용자 메시지에서 다음을 뽑는다.
- **prompt**: 무엇을 그릴지. 한국어면 그대로 써도 되지만, 더 좋은 결과를 위해 핵심 묘사를 영어로
  옮겨 구체화한다(스타일·색·구도·조명 등을 적절히 보강).
- **N (장수)**: "3장", "여러 개" 등. 기본 1. 5장 이상이면 토큰/시간 비용을 한 번 안내하고 확인받는다.
- **비율**: 아래 표로 매핑.
- **참조이미지**: "이 사진을", "첨부", 파일 경로가 있으면 편집 모드. 경로가 불명확하면 사용자에게 묻는다.

### 2. 비율 매핑

| 사용자 표현 | --orientation | --width × --height |
|---|---|---|
| (기본/미지정) | square | 1024 × 1024 |
| "유튜브 썸네일", "16:9", "가로" | landscape | 1280 × 720 |
| "인스타 스토리", "세로", "9:16", "릴스", "쇼츠" | portrait | 1080 × 1920 |
| "인스타 피드", "정사각" | square | 1080 × 1080 |
| "와이드", "배너" | wide | 1920 × 1080 |

### 3. 슬러그 생성
prompt에서 영문 kebab-case 슬러그를 만든다(예: "고양이 기사" → `cat-knight`). 출력은
**현재 작업 디렉토리의** `./codex-images/<slug>-NN.png` (NN = 01부터 연번).

### 4. 생성 호출
각 장마다 래퍼 스크립트를 호출한다. 절대경로로 `--out`을 넘긴다.

```bash
~/.claude/skills/codex-image/scripts/gen.sh \
  --prompt "<영어로 구체화한 프롬프트>" \
  --out "$(pwd)/codex-images/<slug>-01.png" \
  --orientation landscape --width 1280 --height 720
```

참조이미지 편집이면 `--ref <절대경로>`를 추가한다.

N장이면 같은 명령을 `-01`, `-02`, … 로 N번 호출한다(각 호출이 codex exec 1회 = 약 30~60초).
변형을 원하면 프롬프트에 "variation N, slightly different composition" 같은 힌트를 더한다.

### 5. 결과 표시
각 생성 후 PNG를 **Read로 인라인 표시**해 품질을 자가검증하고, 저장 경로를 안내한다.
스크립트가 비정상 종료(PNG 미생성)하면 stderr의 codex 로그를 보고 원인(콘텐츠 정책 거부 등)을
사용자에게 전달하고 프롬프트 수정을 제안한다.

## 비용/성능 메모
- 1장 ≈ 24k 토큰, 30~60초. N장은 선형 증가.
- codex 이미지 도구는 호출당 1장 → N장은 반드시 N회 반복 호출(루프).

## 트러블슈팅
- **여러 장을 while-read 루프로 돌릴 때 목록이 중간에 끊긴다** → `gen.sh`(codex)가 루프의
  stdin 을 같이 읽어버리기 때문이다. 호출에 `</dev/null` 을 붙이면 해결된다.
  100장을 돌렸을 때 매번 7~18장에서 조용히 멈췄던 원인이 이것이었다(2026-08-22).
  ```bash
  while IFS=$'\t' read -r slug n prompt; do
    gen.sh --prompt "$prompt" --out "$out" </dev/null    # ← 이 리다이렉션이 핵심
  done < jobs.tsv
  ```
- `codex not installed` → `npm i -g @openai/codex`
- `codex not authenticated` → 사용자에게 `codex login` 실행 요청(인터랙티브이므로 직접 해야 함;
  세션에서 `! codex login`으로 실행 가능).
- 승인/샌드박스로 멈춤 → 스크립트는 이미 `--dangerously-bypass-approvals-and-sandbox`를 사용한다.
