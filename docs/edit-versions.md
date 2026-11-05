# 쇼츠 편집 버전 — 단일 출처

2026-10-10 사용자 지시: **기존 편집 규칙 = 버전1, 10/10 에 만든 것 = 버전3** 로 저장.
(버전2 = 템플릿2 몰랐썰형, `docs/template2.md`)

사용자가 "버전1로 / 버전3로" 라고 하면 아래 해당 규칙대로 만든다. 말이 없으면 **버전1** (2026-10-15 사용자 지시 "앞으로 만드는거 버전1로" — 10/10~14 기본이던 버전3에서 되돌림). 목소리는 버전1도 이슈쿠키(tts.py 자동)·1.2배속 그대로 — 기준편 `work/ic_payslip`.

| | 버전1 (기존) | 버전2 (몰랐썰형) | 버전3 (10/10~) |
|---|---|---|---|
| 엔진 | Python·PIL·ffmpeg `pipeline/render.py`→`build.py` | Remotion `templates/2` 자체 파이프라인 | 대본·음성은 버전1 파이프라인, 영상은 Remotion — `pipeline/to_remotion.py` |
| 단일 출처 | `prd.md`, `docs/script-guide.md`, 스킬 ssul-shorts | `docs/template2.md` | **이 문서 §버전3** |

---

## 버전1 — 기존 편집 (기준편 `work/ramencafe`, `work/ic_payslip`)

- 화면: 1080×1920, 제목 영역 0~528px(잘난체 고딕·흰+형광·외곽선·자간 -1·좌우 80), 이미지 528~1363px, 하단 검은 띠
- 자막: 이미지 안쪽 하단 검은 박스(`style.sub_box`), 10자 내외 덩어리, 강조 을지로체(연두/노랑), 대사 하늘색
- 이미지: 문장당 1장(`img`), 한 편 10장 이상, 고정 컷(모션 기본 끔)
- 소리: BGM `assets/bgm.mp3` 0.30 · 시작 "띵~" · 효과음은 지정한 문장에만(편당 4~6개) · 흔들림(dudung·eng·thud)
- **2026-10-16 사용자 지시**: 화면 넘어갈 때 문장마다 나던 '툭툭'(whoosh) 전부 제외 — render.py `line_sfx` 기본 "" · 목소리는 타입캐스트(`"tts_engine": "typecast"`, 나레이션 태섭) — 기준편 `work/airgun`
- 흰 바(`style.bar`) + 댓글 수 — 첫 문장 동안
- 명령: `tts.py → render.py → build.py`

## 버전3 — 10/10 편집 (기준편 `work/teslaplate`, `work/jebak30`)

레퍼런스: 한입썰 https://www.youtube.com/shorts/AoAK3YS2I8c (컷 빈도·확대·영상감)

**대본** — 썰푸는휴지 규칙 그대로(`script-guide.md`): 법푸는휴지 법 소재 F형 + 개드립형, 음슴체·연결어구, 첫 문장=제목, 찬반 질문 → 공유 유도 → 구독!
- 금액은 붙여 쓰고 붙여 읽는다: `20만원`
- 실존 인물은 기사처럼 이름 빼고 얼굴 없이

**목소리** — 이슈쿠키(GPT-SoVITS, `pipeline/tts_issuecookie.py`, tts.py 가 자동 호출) · **1.2배속**(layout SPEED)
- 문장 안 쉼 살림(KEEP_PAUSES) · 읽기용 `say` 에 인위적 띄어쓰기 금지 · 짧은 문장은 늘려서 · "구독!"은 "구독해 주세요!"로 읽힘

**화면** — 버전1 레이아웃·타이틀 픽셀 그대로(`zones` 528/835 + `titleImage`) 위에 Remotion 연출
- 컷: 문장당 1~3컷(`img` + `cuts[{img,chunk,...}]`), 한 편 20컷 안팎
- 이미지: **캡처(얼굴·방송 아닌 실제 사진) + 실사 AI(iPhone 캔디드)** 섞기. 방송·언론 캡처는 금지라 그런 소재는 AI 만
- 카메라 이동: 컷마다 자동 순환 — 확대·왼→오·좌하→우상·축소·오→왼·좌상→우하… (`move` 로 지정, `focus` 는 전체→지점 확대)
- 연출: `punch`(줌 펀치) · `shake` · `sticker`(sweat·shock·lines·question) · `dim`
- **물음표 핑**: "?"로 끝나는 나레이션 → 화면 가운데 크게 노란 "?" 탄성 등장·흔들림·파동 → 1초 뒤 우상단으로 작아지며 이동 + "띵-딩"(qping)
- 하단 댓글 카드: 줄에 `comment` — 원글/기사 **실제 댓글** 4~5개(닉네임 가림, 공감 수 실제값), 다음 댓글까지 유지
- 자막: tissue 스타일(버전1 박스 자막), 대본 text 기준

**소리**
- BGM 기본 깔림
- **나레이션 문장 시작마다 효과음** (`pipeline/sfx_pack.py` 합성): 해결=뾰로롱(sparkle) · 화남·어이없는 문제 제기=두둥(dudung) · 숫자 강조=팡(pang) · 질문·정보=띠링(dingring) · 물음표=핑(qping) · 그 외=클릭(click). **칼 가는 소리는 쓰지 않음**. 대사·아웃트로 제외
- **2026-10-11 이슈쿠키 효과음 샘플러 141개 사용** — `assets/sfx/ic/<이름>.wav`, 번호·용도표 `assets/sfx/ic/_목록.txt`. 감정 기본값은 샘플러 소리로 나간다(`to_remotion.py` `SFX_ALIAS`): 클릭=click_ui · 두둥=hit_dun_dun · 팡=pop_long · 띠링=correct_notif · 뾰로롱=notify_fairy (물음표 qping 만 합성음 유지). 줄 `"sfx"` 에 샘플러 이름(crowd_laugh·scratch_vinyl·wrong_trombone·cash_chaching 등)을 바로 써도 됨. **cash_register(90)·heart_heavy(130)는 출처 표기 필요** 표시가 있어 기본값으로 안 씀
- 효과음 음량 = **나레이션의 0.56배**(소리마다 실측 RMS 로 맞춤). 슬라이드 넘어갈 때 전환음 없음

**명령**
```
python3 pipeline/tts.py <slug>            # 이슈쿠키 음성(자동)
python3 pipeline/to_remotion.py <slug>    # Remotion 렌더 → work/<slug>/<slug>.mp4, 재생 창
```
업로드: `docs/upload-workflow.md` (설명칸 클릭 후 activeElement 확인 · Escape 금지)
