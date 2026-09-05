# 유튜브 업로드 워크플로우

bystander 편(2026-08-17)을 올릴 때 실제로 통한 순서를 그대로 적어 둔 것.
브라우저 조작은 **ScaleMaker Chrome MCP**(`chrome-mcp-stdio`, `CHROME_PORT=12320`,
설정은 `.mcp.json`)로 한다.

> **왜 YouTube Data API 를 안 쓰나** (2026-08-17 검토 후 브라우저 유지로 결정)
> 2020-07-28 이후 만들어진 API 프로젝트가 `videos.insert` 로 올린 영상은 **전부
> 비공개로 잠긴다.** 풀려면 구글 감사(audit) 승인이 필요하다. 그 밖에 앱이 "테스트"
> 상태면 리프레시 토큰이 7일마다 만료되고, **고정 댓글은 API 로 아예 안 된다**
> (댓글 등록만 가능). 결국 브라우저가 필요하므로 처음부터 브라우저로 끝낸다.
> 발행량이 하루 여러 편으로 늘면 그때 감사를 신청한다.

---

## 0. 채널·계정 (매번 먼저 확인)

| 항목 | 값 |
|---|---|
| 채널 | 썰푸는휴지 `@ssulltissue` |
| 채널 ID | `UCAZ1Hlnb5SvubqROkMDFFlw` |
| 구글 계정 | `.env`의 `YT_ACCOUNT` |

브라우저에 기본 로그인돼 있는 계정이 **란빵🐣 `@eggbread0`(쇼핑쇼츠,
`UCxQK4IBAJ1t-dPImmMinCng`)** 인 경우가 많다. **다른 구글 계정**이라 채널
전환으로는 안 넘어가고 재로그인이 필요하다.

확인은 여기서만 한다:

```
https://www.youtube.com/account
```

> ⚠️ `youtube.com/logout` 은 절대 열지 않는다. 계정 목록을 보려다 열면
> 구글에서 로그아웃되고 Chrome 동기화까지 끊긴다. (실제로 한 번 났던 사고)

---

## 1. 업로드 다이얼로그 열기

```
https://studio.youtube.com/channel/UCAZ1Hlnb5SvubqROkMDFFlw/videos/upload?d=ud
```

파일은 파일 선택 버튼을 누르지 말고 input 에 바로 넣는다.

```
chrome_upload_file
  selector: input[type="file"]
  filePath: /Users/kimyiseul/Desktop/kim/ssul/work/<slug>/<slug>.mp4
```

업로드가 끝나면 세부정보 화면이 뜨고, 세로 영상이면 자동으로
`youtube.com/shorts/...` 링크가 잡힌다. 이때 링크에 붙은 **영상 ID를 기록**해
둔다 — 뒤에 댓글 달 때 쓴다.

---

## 2. 제목·설명 입력 — `execCommand` 로만

YouTube Studio 의 제목/설명은 Polymer `contenteditable` 이라
**키보드 시뮬레이션이 통하지 않는다.** `cmd+a`·`Backspace` 가 전부 무시되고,
`type` 은 들어가긴 하는데 포커스가 옮겨가지 않아 **설명이 제목 칸에 통째로
붙는 사고**가 난다(실제로 났다. 제목이 145자가 됐다).

`chrome_javascript` 로 이렇게 넣는다:

```js
const box = document.querySelector('ytcp-video-title').querySelector('#textbox');
box.focus();
const r = document.createRange();
r.selectNodeContents(box);
const s = getSelection(); s.removeAllRanges(); s.addRange(r);
document.execCommand('insertText', false, '제목');
```

설명은 같은 방식으로 `ytcp-video-description #textbox` 에 넣는다.
`selectNodeContents` + `insertText` 라서 **기존 내용 교체와 input 이벤트 발생이
한 번에** 된다.

내용은 `work/<slug>/upload.md` 의 제목·설명 블록을 그대로 쓴다.

---

## 3. 나머지 설정

라디오 버튼은 좌표 클릭 대신 `el.click()` 을 쓴다. 좌표로 누르면 영상 플레이어
오버레이나 다이얼로그 backdrop 이 클릭을 가로챈다.

```js
// 아동용 아님
[...document.querySelectorAll('tp-yt-paper-radio-button')]
  .find(x => x.getAttribute('name') === 'VIDEO_MADE_FOR_KIDS_NOT_MFK').click();
```

그다음 `#next-button` 을 세 번 눌러 세부정보 → 동영상 요소 → 검토 → 공개 상태로
넘어간다. 공개 범위는 같은 방식으로 `PUBLIC` 을 고르고 `#done-button` 으로 게시.

게시가 됐는지는 다이얼로그 텍스트에 **"게시된 동영상"** 이 뜨는지로 확인한다.
`#done-button` 을 눌러도 화면이 그대로인 것처럼 보이는데, 실제로는 뒤에
공유 다이얼로그가 떠 있는 경우가 있다.

---

## 3-2. 예약 업로드

**반드시 업로드 흐름 안에서 끝낸다.** 업로드가 끝난 뒤 편집 화면에서 예약 시각을
고치려 하면 공개 상태 다이얼로그가 아예 안 열린다(영상 편집 사이드바, 새로고침 후
재시도, 콘텐츠 목록의 "예약됨" 셀 — 셋 다 안 됨). 그래서 처음 올릴 때 제대로
잡아야 한다.

### ① 예약 섹션 펼치기 — 좌표 클릭

공개 상태 단계에는 `#visibility-title` 이 **두 개**다. 첫째가 "저장 또는 게시",
둘째가 "예약". 둘째를 좌표로 클릭한다(`.click()` 은 안 먹는다).

```js
[...document.querySelectorAll('#visibility-title')].map(h => {
  const r = (h.closest('.early-access-header') || h.parentElement).getBoundingClientRect();
  return {text: h.textContent.trim(), cx: Math.round(r.x+r.width/2), cy: Math.round(r.y+r.height/2)};
});
// → [{'저장 또는 게시', 592, 311}, {'예약', 592, 577}]  ← 둘째를 chrome_click_element
```

### ② 시간 — 드롭다운에서 고른다 ⚠️

시간 칸에 **값을 써넣는 방식은 전부 실패한다.** JS 로 `.value` 를 넣거나
`insertText` 로 타이핑하면 화면에는 `오후 7:00` 으로 보이는데 컴포넌트 값은
`오전 12:00` 그대로다. 그 상태로 저장하면 **0시로 예약된다**(실제로 한 번 났다).

시간 칸을 **좌표로 클릭**하면 15분 단위 96개짜리 드롭다운이 열린다. 여기서 골라야
값이 실제로 들어간다. 항목 선택은 좌표 대신 `.click()` — 좌표로 누르면
`TP-YT-IRON-OVERLAY-BACKDROP` 이 클릭을 가로챈다.

```js
// 시간 칸 좌표 클릭(586, 498) 후:
[...document.querySelectorAll('tp-yt-paper-item')]
  .filter(i => i.offsetParent !== null)
  .find(i => i.innerText.trim() === '오후 7:00')
  .click();
```

### ③ 날짜 — 달력에서 고른다

날짜 기본값은 **내일**이다. 바꾸려면 날짜 트리거를 좌표 클릭(410, 491)해서 달력을
연 뒤, `.today` 클래스가 붙은 칸을 기준으로 오프셋을 세어 `.click()` 한다.
`17` 같은 숫자로 찾으면 8월·9월·10월의 17이 모두 걸리므로 반드시 `today` 기준으로 센다.

> ⚠️ **`today + N` 로 세면 안 된다.** 달력은 월별 그리드라 그 달 마지막 주 뒤에
> **빈 칸(padding)** 이 붙고, 다음 달은 새 헤더 아래에서 다시 시작한다. 오프셋으로
> 세면 빈 칸을 찍어 **날짜가 안 바뀐 채 기본값(내일)으로 예약된다.**
> 실제로 pms 편이 9/1 대신 8/26 으로 잡혀 다른 예약과 겹쳤다.
>
> 달력 구조는 이렇게 생겼다:
> `[2026년 8월] _ _ _ _ _ _ 1 2 … 30 31 _ _ _ _ _ [2026년 9월] _ _ 1 2 3 …`

**월 헤더를 기준으로 "몇 월 며칠"을 직접 찾는다.** 날짜 칸과 헤더는 shadow DOM
안에 있어 `document.querySelectorAll` 로는 안 잡히므로 `shadowRoot` 까지 훑는다.

```js
function pick(month, day){            // pick('2026년 9월', 1)
  let seq = [];
  (function w(root, d){
    if (d > 24 || !root) return;
    for (const el of (root.children || [])) {
      const c = typeof el.className === 'string' ? el.className : '';
      if (c.includes('calendar-day'))
        seq.push({k:'d', t: el.textContent.trim(), dis: c.includes('disabled'), el});
      else if (c.includes('month') && el.children.length === 0)
        seq.push({k:'m', t: el.textContent.trim()});
      w(el, d+1);
      if (el.shadowRoot) w(el.shadowRoot, d+1);
    }
  })(document.body, 0);

  let cur = null;
  for (const s of seq) {
    if (s.k === 'm') { cur = s.t; continue; }
    if (cur === month && s.t === String(day) && !s.dis) { s.el.click(); return true; }
  }
  return false;
}
```

시간 항목(`TP-YT-PAPER-ITEM`)도 같은 이유로 shadow DOM 을 훑어야 찾힌다.

> **달력을 연 직후엔 날짜 칸이 비어 있다.** 탭이 화면에 그려져야 렌더되므로,
> 트리거를 누른 뒤 `chrome_screenshot` 을 한 번 찍어 리페인트를 강제하고 나서
> 칸을 찾는다. 기다리기만 해서는 계속 0개로 나온다.

### 제목·설명은 클릭으로 포커스를 준 뒤에 넣는다

`box.focus()` 만으로는 `execCommand` 가 **조용히 무시된다**(반환값은 true인데
값이 안 바뀜). 반드시 `chrome_click_element` 로 **좌표를 클릭**해 실제 포커스를
준 다음 `execCommand` 를 호출한다. 1440×813 창 기준 제목 `(556, 296)`,
설명은 `scrollIntoView` 후 `(340, 400)`.

### 예약 시각은 업로드 후에도 고칠 수 있다

이전 기록과 달리, **영상 편집 화면(`/video/<ID>/edit`)에서 공개 상태 카드를
클릭하면 예약 다이얼로그가 열린다.** 날짜를 고치고 `완료` → `저장` 하면 반영된다.
잘못 잡힌 예약 때문에 영상을 지우고 다시 올릴 필요는 없다.
(영상 **파일** 교체는 여전히 불가.)

### ④ 저장 전 확인 → 저장

`#done-button` 라벨이 **"예약"** 으로 바뀌고, 공개 상태 영역에 **"공개로 예약"**
과 목표 날짜가 뜨는지 본다. 누른 뒤 다이얼로그가

> 동영상 예약됨 — 2026년 8월 17일 **19:00** 에 동영상이 공개 상태로 설정됩니다.

처럼 **시각까지** 찍어주므로, 여기서 시간이 맞는지 반드시 눈으로 확인한다.

### 올린 영상의 파일은 교체할 수 없다

유튜브는 **업로드된 영상의 파일 교체를 지원하지 않는다.** 영상 자체를 고쳐야 하면
예약본을 `옵션(⋮) → 영구 삭제` 로 지우고 다시 올리는 수밖에 없다. 링크(영상 ID)가
바뀌므로 아래 기록표도 같이 고친다. 삭제를 **먼저** 하고 업로드한다 — 순서를 바꿨다가
업로드가 끊기면 같은 영상 두 개가 공개된다.

옵션 버튼은 **행에 마우스를 올려야** 나타난다(`aria-label="옵션"`). 확인창에서
"이해합니다" 체크박스를 켜야 `영구 삭제` 가 활성화된다.

### 예약 영상의 고정 댓글

**공개되기 전에는 댓글을 달 수 없다.** 예약 건은 공개된 뒤에 §4 를 따로 돌린다.

---

## 3-3. Zernio API 경로 — 브라우저 없이 (2026-08-28 확인)

썰푸는휴지 유튜브가 **Zernio 에 연결됐다.** Chrome MCP 가 죽어도 이 경로로 올라간다.
제목·설명·첫 댓글·공개범위·예약을 한 번에 넘기므로 §3-2 의 달력·드롭다운 함정이 없다.

```bash
python3 pipeline/upload_zernio.py <slug>                               # DRY RUN
python3 pipeline/upload_zernio.py <slug> --schedule 2026-08-28T07:00:00
python3 pipeline/upload_zernio.py <slug> --publish                     # 즉시 공개
```

- 내용은 `work/<slug>/upload.md` 의 `## 제목` `## 설명` `## 고정 댓글` 에서 읽는다
- 키는 `.env` 의 `ZERNIO_API_KEY`. 계정 확인은 `GET /v1/accounts`
- **3분 미만이면 자동으로 쇼츠.** `madeForKids:false` 를 명시하지 않으면 조회가 막힐 수 있다
- **`containsSyntheticMedia:true`** — 이미지가 전부 생성물이고 실사풍 인물이 나오므로
  합성 콘텐츠 고지 대상이다. 스크립트 기본값
- 예약 확인은 `GET /v1/posts`. `scheduledFor` 가 **UTC** 라 KST 07:00 이 전날 22:00Z 로 보인다
- 첫 댓글은 자동 등록되지만 **고정(pin)은 안 된다** — 전화번호 인증 후 Studio 에서

**Studio 가 여전히 필요한 것** — 댓글 고정, 예약 시각 수정, 유튜브 쇼핑 태그.

---

## 4. 고정 댓글 (README 의 핵심 원칙)

> 100일 실험의 결론이 "댓글이 조회수를 만든다"였다. 질문형으로 달아 답글을 유도한다.

```
https://www.youtube.com/watch?v=<영상ID>
```

댓글창(`#contenteditable-root`)도 **contenteditable 이라 2번과 같은
`execCommand` 방식**을 쓴다. 등록은 `#submit-button` 을 좌표가 아니라
`.click()` 으로 누른다.

문안은 `work/<slug>/upload.md` 의 "업로드 후" 블록.

### ⚠️ 고정은 전화번호 인증이 먼저

댓글 `⋮` → 고정을 누르면 이 안내가 뜬다:

> 고급 기능 이용하기 — 댓글을 고정하려면 YouTube 스튜디오에서 간단한 일회성
> 인증을 완료하세요.

**사람이 직접** `https://www.youtube.com/verify` 에서 전화번호 인증을 해야 한다.
일회성이라 한 번 해두면 이후 편부터는 바로 고정된다.

---

## 5. 체크리스트

- [ ] `https://www.youtube.com/account` 에서 **`.env`의 `YT_ACCOUNT` 계정 / 썰푸는휴지** 확인
- [ ] `work/<slug>/upload.md` 작성돼 있음
- [ ] 제목이 **100자 이내** (입력 후 카운터 확인 — 사고가 여기서 났다)
- [ ] 설명에 해시태그 포함
- [ ] 아동용 **아니요**
- [ ] 공개 범위 지정
- [ ] 저작권 검사 "문제 없음"
- [ ] 게시 확인 (다이얼로그에 "게시된 동영상")
- [ ] 고정 댓글 등록
- [ ] 댓글 **고정** 처리 (전화번호 인증 완료 후)

---

## 기록

| 날짜(공개) | slug | 링크 | 비고 |
|---|---|---|---|
| 2026-08-17 | bystander | https://youtube.com/shorts/g0mFk-5xX-4 | 채널 첫 영상. 공개. 댓글 등록됨, 고정은 전화번호 인증 대기 |
| 2026-08-17 | chinil | https://youtube.com/shorts/yx7J99gDT8I | 8/18 예약으로 올렸으나 시각이 0시로 잘못 잡힘 → 사람이 직접 공개 + 댓글 |
| 2026-08-17 19:00 | brainrot | https://youtube.com/shorts/uM-qkKOGroA | 예약. 고정 댓글 미등록 |
| 2026-08-18 19:00 | meta | https://youtube.com/shorts/7hclfiT39sg | 예약. 고정 댓글 미등록 |
| 2026-08-19 19:00 | munsa | https://youtube.com/shorts/WNAHzlEqXyI | 예약. 오디오 재작업 후 재업로드(구 DkG5nxLCroY 삭제). 고정 댓글 미등록 |
| 2026-08-20 19:00 | monster | https://youtube.com/shorts/oDzsjadx53w | 예약. 오디오 재작업 후 재업로드(구 RQINq0PB7p8 삭제). 고정 댓글 미등록 |
| 2026-08-21 19:00 | taishoku | https://youtube.com/shorts/VAccAf-iYDM | 예약. 오디오 재작업 후 재업로드(구 8LqbmKJmNgo 삭제). 고정 댓글 미등록 |
| 2026-08-22 | marshmallow | https://youtube.com/shorts/7vZbra0oU_Y | **즉시 공개**. 나레이션 민욱, 대사 예슬. 고정 댓글 **등록됨**, 고정은 전화번호 인증 대기 |
| 2026-08-23 17:00 | halo | https://youtube.com/shorts/Fc04ujeyQ60 | 예약. 자극형 10편 배치. 고정 댓글은 공개 후 등록 필요 |
| 2026-08-23 20:00 | apt | https://youtube.com/shorts/rbtsUp2pdmU | 예약. 자극형 10편 배치. 고정 댓글은 공개 후 등록 필요 |
| 2026-08-24 17:00 | nice | https://youtube.com/shorts/63CDTtnJz2k | 예약. 자극형 10편 배치. 고정 댓글은 공개 후 등록 필요 |
| 2026-08-24 20:00 | dating | https://youtube.com/shorts/SwEvvFNY_zA | 예약. 자극형 10편 배치. 고정 댓글은 공개 후 등록 필요 |
| 2026-08-25 17:00 | poortax | https://youtube.com/shorts/cx3aS-QztXM | 예약. 자극형 10편 배치. 고정 댓글은 공개 후 등록 필요 |
| 2026-08-25 20:00 | hardwork | https://youtube.com/shorts/XRZPfBmomow | 예약. 자극형 10편 배치. 고정 댓글은 공개 후 등록 필요 |
| 2026-08-26 (즉시공개) | anger | (예약 목록에서 확인) | 예약. 자극형 10편 배치. 고정 댓글은 공개 후 등록 필요 |
| 2026-08-26 20:00 | sorry | (예약 목록에서 확인) | 예약. 자극형 10편 배치. 고정 댓글은 공개 후 등록 필요 |
| 2026-08-27 17:00 | babble | (예약 목록에서 확인) | 예약. 자극형 10편 배치. 고정 댓글은 공개 후 등록 필요 |
| 2026-08-27 20:00 | gift | https://youtube.com/shorts/IHlDVebfncg | 예약. **수정본 재업로드**(1.3배속·검은 자막박스·실사 이미지·시작음). 구 예약본 삭제함. 고정 댓글은 공개 후 |
| 2026-08-23 | law77 | https://youtube.com/shorts/CFRGqXldpPk | 즉시 공개. 7·7 정보통신망법 팩트체크 |
| 2026-08-23 | nsacard | https://youtube.com/shorts/NkFUpTOTZgg | **즉시 공개**. 개드립 「여군은 나라사랑카드도 안줌」 팩트체크. 나레이션 edge-tts(타입캐스트 크레딧 소진) |
| 2026-08-28 17:00 | overparent | (예약 목록) | 예약. 개드립 배치 1편 |
| 2026-08-28 20:00 | bkvip | (예약 목록) | 예약. **본문 미반영 버전** — bkvip2 로 교체 검토 |
| 2026-08-29 17:00 | catmom | (예약 목록) | 예약 |
| 2026-08-23 | mackerel | https://youtube.com/shorts/pTXM9AqUNa4 | **즉시 공개**. D형 첫 편 — 연합뉴스 '고등어 특사단' 오해유도 반전. 나레이션 edge-tts(타입캐스트 크레딧 소진). 고정 댓글 **등록됨**, 고정은 전화번호 인증 대기 |
| 2026-08-23 | michelin | https://youtube.com/shorts/T2XqnnpK7HI | 즉시 공개. 개드립 「한국에서 미슐랭 식당들이 살아남기 어려운 이유」 본문 충실. 제목에 ㄷㄷ 미사용 |
| 2026-08-24 | assembly | https://youtube.com/shorts/IgHXz-vrDig | 즉시 공개. 개드립 「국회 의사당 자리에 아파트」 본문 충실. **1.3배속 고정 첫 편** · 끝맺음 질문 + "구독" 1.5배속 첫 적용. 고정 댓글 등록됨 |
| 2026-08-29 20:00 | allowance | https://youtube.com/shorts/FYCkBiuGZnE | 예약. 개드립 배치. 구 규격. 고정 댓글은 공개 후 |
| 2026-08-30 17:00 | carexport | https://youtube.com/shorts/-r1rJkqm02A | 예약. 개드립 배치. 구 규격. 고정 댓글은 공개 후 |
| 2026-08-30 20:00 | cooking | https://youtube.com/shorts/csEz_UmVmSw | 예약. 개드립 배치. 구 규격. 고정 댓글은 공개 후 |
| 2026-08-31 17:00 | menuchange | https://youtube.com/shorts/xpkxEIG2okM | 예약. 개드립 배치. 구 규격. 고정 댓글은 공개 후 |
| 2026-08-31 20:00 | modernwarfare | https://youtube.com/shorts/cvdDIpnUUgI | 예약. 개드립 배치. 구 규격. 고정 댓글은 공개 후 |
| 2026-09-01 17:00 | pms | https://youtube.com/shorts/Llb6ClH6eNg | 예약. 개드립 배치. 구 규격. **최초 8/26 로 잘못 잡혀 편집 화면에서 9/1 로 수정**. 고정 댓글은 공개 후 |
| 2026-09-01 20:00 | regular | https://youtube.com/shorts/kuK-nVtjnAk | 예약. 개드립 배치. 구 규격. 고정 댓글은 공개 후 |
| 2026-09-02 17:00 | bkvip2 | https://youtube.com/shorts/tVpGUGlqqUQ | 예약. 버거킹 **본문 충실판**. bkvip(8/28 20:00)과 별개 편으로 유지. 고정 댓글은 공개 후 |
| 2026-08-26 13:00 | interior | https://youtube.com/shorts/ovRfNtPPfnM | 예약. 개드립 신규 10편 배치(2026-08-26 제작). **현행 규격**(1.3배속·직접 설명 화법·구독 아웃트로). 고정 댓글은 공개 후 |
| 2026-08-27 00:30 | banmal | https://youtube.com/shorts/7uJyB1bva4A | 예약. 개드립 신규 10편 배치(2026-08-26 제작). **현행 규격**(1.3배속·직접 설명 화법·구독 아웃트로). 고정 댓글은 공개 후 |
| 2026-08-27 13:00 | camper | https://youtube.com/shorts/vfd8bXUdnK4 | 예약. 개드립 신규 10편 배치(2026-08-26 제작). **현행 규격**(1.3배속·직접 설명 화법·구독 아웃트로). 고정 댓글은 공개 후 |
| 2026-08-28 00:30 | drink | https://youtube.com/shorts/3loixJ8oYzQ | 예약. 개드립 신규 10편 배치(2026-08-26 제작). **현행 규격**(1.3배속·직접 설명 화법·구독 아웃트로). 고정 댓글은 공개 후 |
| 2026-08-28 13:00 | jokbal | https://youtube.com/shorts/mCDdUxKAf3M | 예약. 개드립 신규 10편 배치(2026-08-26 제작). **현행 규격**(1.3배속·직접 설명 화법·구독 아웃트로). 고정 댓글은 공개 후 |
| 2026-08-29 00:30 | medi | https://youtube.com/shorts/3EJIYXTBXPA | 예약. 개드립 신규 10편 배치(2026-08-26 제작). **현행 규격**(1.3배속·직접 설명 화법·구독 아웃트로). 고정 댓글은 공개 후 |
| 2026-08-29 13:00 | washer | https://youtube.com/shorts/FDqk6hpC268 | 예약. 개드립 신규 10편 배치(2026-08-26 제작). **현행 규격**(1.3배속·직접 설명 화법·구독 아웃트로). 고정 댓글은 공개 후 |
| 2026-08-30 00:30 | ricecake | https://youtube.com/shorts/ZWUuHT5a75E | 예약. 개드립 신규 10편 배치(2026-08-26 제작). **현행 규격**(1.3배속·직접 설명 화법·구독 아웃트로). 고정 댓글은 공개 후 |
| 2026-08-30 13:00 | illusion | https://youtube.com/shorts/ky8tCzOWCv8 | 예약. 개드립 신규 10편 배치(2026-08-26 제작). **현행 규격**(1.3배속·직접 설명 화법·구독 아웃트로). 고정 댓글은 공개 후 |
| 2026-08-31 00:30 | quit | https://youtube.com/shorts/UpuLNiLMH7M | 예약. 개드립 신규 10편 배치(2026-08-26 제작). **현행 규격**(1.3배속·직접 설명 화법·구독 아웃트로). 고정 댓글은 공개 후 |

| 2026-08-28 (즉시공개) | parcel | https://youtube.com/shorts/IwCRXTJhnZ0 | **즉시 공개**. D형 뉴스 반전 — 조선일보 「'전두환 손자' 전우원, 택배 알바로 생계」. 사용자 요청으로 제목에 "전두환 손자" 키워드 노출. 자막 "518"·음성 "오일팔". 고정 댓글 **등록됨**, 고정은 전화번호 인증 대기 |
| 2026-08-28 07:00 | fourth | (Zernio 예약 · 게시 후 링크 기입) | 예약. **Zernio API 경로 첫 편.** 개드립 「넷째 낳자고 보채는」. 강조 자막(을지로체)·3화자 첫 적용. 첫 댓글 자동 등록 |
| 2026-08-29 07:00 | probation | (Zernio 예약 · 게시 후 링크 기입) | 예약. 집행유예 취소 실형 — 지역세계 보도 확인. 대사는 시청자 딴지로 처리 |
| 2026-08-30 07:00 | wedding | (Zernio 예약 · 게시 후 링크 기입) | 예약. 축의금 200만원 오송금. **끝 "구독" 여성(sub1) 첫 편** |
| 2026-08-30 (즉시공개) | willpower | https://youtube.com/shorts/8-svWoTLbkY | **즉시 공개(Zernio)**. 개드립 「과학이랑 기싸움하는 분야」(다이어트·의지력). **신규격 첫 편** — 나레이션 용식·대사 세희·흰 바+파란 댓글수(300)·캐릭터 없음·자막 숫자단위 규칙. 첫 댓글 자동 등록. ⚠️ publish 이중 실행으로 중복본(vWAgvFO4tbg)이 올라갔었고 조회 0회 상태에서 Studio 에서 완전 삭제함 — **Zernio publish 는 한 번만 실행하고 반드시 `GET /v1/posts` 로 확인할 것** |
| 2026-08-31 10:00 | reward | (Zernio 예약 · 게시 후 링크 기입) | 예약(Zernio post `6a9440bf31b7e74c9cc56f46`). 이데일리 「혈세 2800억 지켜낸 공무원 포상금」. 신규격(용식·세희·흰 바 123·bar_count) |
| 2026-08-31 20:00 | ramencafe | (Zernio 예약 · 게시 후 링크 기입) | 예약(Zernio post `6a945927898fbfe51b2d1913` — 초판 `6a944abc…` 는 아웃트로 수정으로 삭제 후 재예약). 개드립 「무인 라면카페 남중생 출입금지 경고문」. **원글 실물 사진 크롭 3컷 사용**(사용자 명시 지시 예외 — 식별정보 없음 확인). 마감 "중학생들 이정도임?" + **"구독!" toneup 아웃트로 첫 편** |
| 2026-08-31 (즉시공개) | `tunnelwed` | https://youtube.com/shorts/59jTtfPlGaU | **즉시 공개**(사용자 요청). 개드립 722201396 남산 3호터널 웨딩촬영 — 원글 블랙박스 사진 1컷 사용(**차량번호 블러**, SNS 계정 영역 제외), 나머지 생성. 첫 댓글 자동 등록, 고정은 전화번호 인증 대기 |
| 2026-09-01 07:00 | `pizza` | (Zernio 예약 · 게시 후 링크 기입) | 예약. 개드립 피자 현타 — 원글 사진 2컷(주문내역·카톡) 사용. **제목 신규격**(#검색키워드+궁금증/위험성), 설명 #shorts+관련태그 |
| 2026-09-01 13:00 | `taxidoor` | (Zernio 예약 · 게시 후 링크 기입) | 예약. 2014 신라호텔 회전문 사건 — 언론사 사진 미사용, 전 컷 생성. **제목 신규격**(#검색키워드+궁금증/위험성), 설명 #shorts+관련태그 |
| 2026-09-01 20:00 | `comeback` | (Zernio 예약 · 게시 후 링크 기입) | 예약. 유튜브 캡처 금지 규칙 적용 — 전 컷 생성. **제목 신규격**(#검색키워드+궁금증/위험성), 설명 #shorts+관련태그 |
| 2026-09-02 07:00 | `maserati` | (Zernio 예약 · 게시 후 링크 기입) | 예약. KBC 2026-08-30 보도 + 윤창호법 형량. **제목 신규격**(#검색키워드+궁금증/위험성), 설명 #shorts+관련태그 |
| 2026-09-02 13:00 | `nepal` | (Zernio 예약 · 게시 후 링크 기입) | 예약. 한겨레 현장 르포 1275369. **제목 신규격**(#검색키워드+궁금증/위험성), 설명 #shorts+관련태그 |
| 2026-09-02 20:00 | `glacier` | (Zernio 예약 · 게시 후 링크 기입) | 예약. 한겨레 1275336 빙하호 급증. **제목 신규격**(#검색키워드+궁금증/위험성), 설명 #shorts+관련태그 |
| 2026-09-03 07:00 | `kimbusik` | (Zernio 예약 · 게시 후 링크 기입) | 예약. 개드립 721982065 — 비속어 순화, 유튜브 캡처 미사용. **제목 신규격**(#검색키워드+궁금증/위험성), 설명 #shorts+관련태그 |
| 2026-09-03 13:00 | `hanlaser` | (Zernio 예약 · 게시 후 링크 기입) | 예약. 개드립 722094881 — 방송 캡처 금지 적용, 전 컷 생성. **제목 신규격**(#검색키워드+궁금증/위험성), 설명 #shorts+관련태그 |
| 2026-09-03 20:00 | `lhtrash` | (Zernio 예약 · 게시 후 링크 기입) | 예약. 개드립 722086547 — 원글 사진 2컷(복도·쓰레기) 사용. **제목 신규격**(#검색키워드+궁금증/위험성), 설명 #shorts+관련태그 |
| 2026-09-04 07:00 | `tattoo` | (Zernio 예약 · 게시 후 링크 기입) | 예약. 개드립 722035334 — 인스타 캡처 미사용. **제목 신규격**(#검색키워드+궁금증/위험성), 설명 #shorts+관련태그 |
| 2026-09-04 13:00 | `ajumma` | (Zernio 예약 · 게시 후 링크 기입) | 예약. 개드립 722035112 — 찬반형. **제목 신규격**(#검색키워드+궁금증/위험성), 설명 #shorts+관련태그 |
| 2026-09-04 20:00 | `porter` | (Zernio 예약 · 게시 후 링크 기입) | 예약. 개드립 722003183 — 원글 사진 1컷(차량번호 블러). **제목 신규격**(#검색키워드+궁금증/위험성), 설명 #shorts+관련태그 |
| 2026-09-05 07:00 | `litcar` | (Zernio 예약 · 게시 후 링크 기입) | 예약. 개드립 722041341 — 문자 캡처 2컷. **제목 신규격**(#검색키워드+궁금증/위험성), 설명 #shorts+관련태그 |
| 2026-09-05 13:00 | `nightpast` | (Zernio 예약 · 게시 후 링크 기입) | 예약. 뱅크 A10 자이가르닉. **제목 신규격**(#검색키워드+궁금증/위험성), 설명 #shorts+관련태그 |
| 2026-09-05 20:00 | `pickfail` | (Zernio 예약 · 게시 후 링크 기입) | 예약. 뱅크 B12 선택 마비. **제목 신규격**(#검색키워드+궁금증/위험성), 설명 #shorts+관련태그 |
> **2026-08-26 일정 변경** — 오늘 만든 신규 10편만 **00:30 / 13:00** 으로 앞당겨
> 8/26~8/31 에 배치했다. 기존 15편은 **17:00 / 20:00 그대로** 둔다.
> 두 시간대가 나란히 돌아가므로 **발행 시간대 A/B 비교**가 가능하다.
> `anger`(화 잘 내는 사람)는 이 과정에서 **즉시 공개**로 나갔다(8/26 17:00 예정이었음).

| 2026-09-04 22:50 | `yeouido` | 여의도 돗자리 알박기 | https://youtube.com/shorts/RG7H37xq3u4 | Zernio 즉시 공개 |
