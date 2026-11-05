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
| 채널 | 법푸는휴지 `@beopdaerohaedeurim` (구 법푸는휴지) |
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
  filePath: <저장소 경로>/work/<slug>/<slug>.mp4
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

법푸는휴지 유튜브가 **Zernio 에 연결됐다.** Chrome MCP 가 죽어도 이 경로로 올라간다.
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

### ⚠️ 2026-10-26 함정: youtube.com 활성 채널이 란빵이면 댓글이 @eggbread0 으로 달린다

같은 구글 계정에 법푸는휴지(소유)와 란빵 등 관리 채널이 여러 개라, 스튜디오는 채널 URL 로 맞춰도
**youtube.com 시청 페이지의 활성 채널은 마지막으로 전환한 채널**이다. 이날 두 편 고정 댓글을
@eggbread0 으로 달아 버려 삭제 후 재등록했다.

- 댓글 달기 전에 `ytd-comment-simplebox-renderer img` 의 alt 가 "법푸는휴지"인지 확인
- 아니면 `https://www.youtube.com/account` 의 "모든 채널"에서 법푸는휴지를 클릭해 전환
- 댓글 ⋮ 메뉴는 `ytd-menu-navigation-item-renderer` 로 뜬다(고정/수정/삭제). JS `.click()` 으로는
  안 열리고 chrome_click_element 좌표 클릭으로 연다. 고정은 확인 창 "고정" 버튼 → "님이 고정함" 배지
- 전화번호 인증은 이미 돼 있어 고정이 바로 됐다

---

## 5. 체크리스트

- [ ] `https://www.youtube.com/account` 에서 **`.env`의 `YT_ACCOUNT` 계정 / 법푸는휴지** 확인
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
| 2026-09-05 18:54 | `rent` | 서울 아파트 평균 월세 152만원 | https://youtube.com/shorts/mL2kN5_ez0E | Zernio 즉시 공개 |

| 2026-09-14 20:00 | `jejuvisa` | https://youtube.com/shorts/6rpGo4aaNJ0 | 예약(Studio). 개드립 724475314. 태섭 나레이션·motion·로컬 SDXL 10장. 고정 댓글은 공개 후 |
| 2026-09-14 20:30 | `wage450` | https://youtube.com/shorts/cWgG6zzwlhc | 예약(Studio). 개드립 724361932. 태섭 나레이션·motion·로컬 SDXL 10장. 고정 댓글은 공개 후 |
| 2026-09-14 21:00 | `gumi` | https://youtube.com/shorts/Ocm9ngsFnWM | 예약(Studio). 개드립 724450584. 태섭 나레이션·motion·로컬 SDXL 10장. 고정 댓글은 공개 후 |
| 2026-09-14 21:30 | `mousewheel` | https://youtube.com/shorts/T90vDsvKg7c | 예약(Studio). 개드립 724485263. 태섭 나레이션·motion·로컬 SDXL 10장. 고정 댓글은 공개 후 |
| 2026-09-14 22:00 | `height180` | https://youtube.com/shorts/W7sgG1yNaGI | 예약(Studio). 개드립 724359382. 태섭 나레이션·motion·로컬 SDXL 10장. 고정 댓글은 공개 후 |

> **2026-09-14 배치에서 배운 것** — ① 시간 드롭다운은 **날짜보다 먼저** 고른다. 달력을 먼저 열면
> 백드롭이 남아 시간 칸 클릭이 백드롭에 먹힌다. 시간→스크린샷(리페인트)→`tp-yt-paper-item` 을
> `getBoundingClientRect().height>0` 로 찾아 `.click()`(`offsetParent` 는 shadow DOM 이라 null).
> ② 열린 `TP-YT-PAPER-DIALOG` 에 `.close()` 를 부르면 **업로드 다이얼로그 자체가 닫힌다**(초안 저장됨).
> 복구는 `/video/<ID>/edit` 상단 **「초안 수정」** 버튼 — 제목·설명 유지된 채 다이얼로그가 다시 열린다.
> ③ JS 안에서 `for … await sleep` 폴링 루프는 CDP 타임아웃이 난다. 상태는 짧은 JS 로 따로 확인한다.

| 2026-09-14 22:30 | `interlock` | https://youtube.com/shorts/BI_JdkSEolg | 예약(Studio). 레퍼런스 채널 발굴(자나스·짧은주녑·뇌전구) → 원 보도 확인. **여성 대사·구독 = 소예 첫 배치**. 고정 댓글은 공개 후 |
| 2026-09-14 23:00 | `otcdrug` | https://youtube.com/shorts/aR7D3t4wAZM | 예약(Studio). 레퍼런스 채널 발굴(자나스·짧은주녑·뇌전구) → 원 보도 확인. **여성 대사·구독 = 소예 첫 배치**. 고정 댓글은 공개 후 |
| 2026-09-14 23:30 | `dropout` | https://youtube.com/shorts/zh0GboNjFW0 | 예약(Studio). 레퍼런스 채널 발굴(자나스·짧은주녑·뇌전구) → 원 보도 확인. **여성 대사·구독 = 소예 첫 배치**. 고정 댓글은 공개 후 |
| 2026-09-15 00:00 | `tjchart` | https://youtube.com/shorts/UOinIaAFjVM | 예약(Studio). 레퍼런스 채널 발굴(자나스·짧은주녑·뇌전구) → 원 보도 확인. **여성 대사·구독 = 소예 첫 배치**. 고정 댓글은 공개 후 |
| 2026-09-15 00:30 | `nurseroom` | https://youtube.com/shorts/eBPKVqV3PwU | 예약(Studio). 레퍼런스 채널 발굴(자나스·짧은주녑·뇌전구) → 원 보도 확인. **여성 대사·구독 = 소예 첫 배치**. 고정 댓글은 공개 후 |
| 2026-09-15 20:00 | `parking` | https://youtube.com/shorts/E2rJbBcW35k | 예약(Studio). **F형 법조항 사이다 첫 편**(주차장법 8/28 시행). **효과음+화면흔들림 첫 적용**(`sfx`/`shake`, pipeline/sfx.py). 이미지 12장 gpt + 13번 로컬 SDXL(codex 한도). 고정 댓글은 공개 후 |
| 2026-09-15 20:30 | `review305` | https://youtube.com/shorts/AhbpmcD0-sY | 예약(Studio). F형 2편(실제 판결). **자체 개구리 캐릭터 2컷** — 사용자 "별로", 추가 생성 금지. 대사 angry 첫 적용. 고정 댓글은 공개 후 |
| 2026-09-15 21:00 | `floornoise` | https://youtube.com/shorts/_JJQRuGy2HQ | 예약(Studio, 초안 수정 경로). F형 3편(실제 판결). 구 자막 청킹본(사용자 "지금껀 그냥 올려") |
| 2026-09-15 21:30 | `gymrefund` | https://youtube.com/shorts/k5rF4XR5wFI | 예약(Studio). F형 4편(각색). gpt 12장 |
| 2026-09-15 22:00 | `deposit` | https://youtube.com/shorts/bVtOMYsyR5I | 예약(Studio). F형 5편(각색). 로컬 SDXL 12장 — 문서컷 글씨 뭉개짐 감수 |
| 2026-09-15 12:00 | `wagedelay` | https://youtube.com/shorts/opHPaeWCCBY | 예약(Studio). F형 각색. **새 슬롯 규칙 첫 적용(12:00~14:00)** |
| 2026-09-15 12:30 | `wedding70` | https://youtube.com/shorts/5Khw6cSNP80 | 예약(Studio). F형 각색 |
| 2026-09-15 13:00 | `noshow40` | https://youtube.com/shorts/LiYVOymdYNw | 예약(Studio). F형 각색 |
| 2026-09-15 13:30 | `rent5` | https://youtube.com/shorts/vfoO3erwKGo | 예약(Studio). F형 각색 |
| 2026-09-15 14:00 | `parcel` | https://youtube.com/shorts/RQQy1CTkc-8 | 예약(Studio). F형 각색 |
| 2026-09-16 12:00 | `refund7` | https://youtube.com/shorts/dlePZbTzFbk | 예약(Studio). F형 각색 |
| 2026-09-16 12:30 | `hagwon` | https://youtube.com/shorts/nnRKcEiRxQ4 | 예약(Studio). F형 각색 |
| 2026-09-16 13:00 | `carrepair` | https://youtube.com/shorts/k9UGrgc-AY4 | 예약(Studio). F형 각색 |
| 2026-09-16 13:30 | `evcharge` | https://youtube.com/shorts/G3DfvCpz3Wo | 예약(Studio). F형 각색 |
| 2026-09-16 14:00 | `dogleash` | https://youtube.com/shorts/n2RFJw42GHo | 예약(Studio). F형 각색. 고정 댓글은 공개 후 |
| 2026-09-15 22:30 | `gyeongbok` | https://youtube.com/shorts/x_xiLmL_te0 | 예약(Studio). **사이다·현장 1순위 첫 편**(경복궁 댕댕런·고궁박물관 공지). gpt 10장. 초안으로 빠졌다가 "초안 수정"으로 복구해 예약 |
| 2026-09-15 23:00 | `drone` | https://youtube.com/shorts/yu7nJp5ZHjs | 예약(Studio). 추석 고속도로 AI 드론 단속(시의성 9/24~27). gpt 10장 |
| 2026-09-15 23:30 | `ktxfee` | https://youtube.com/shorts/TFYHSYSpgvI | 예약(Studio). 명절 KTX 위약금 F형. gpt 10장 |

> **2026-09-14 재업로드** — 위 5편(interlock·otcdrug·dropout·tjchart·nurseroom)은 사용자 지적(댓글 중계 문장 제거, 이미지 10장 이상)으로 초판 예약본을 Studio 에서 **완전삭제**하고 같은 슬롯에 다시 올렸다. 링크는 재업로드본 ID 로 교체함. 삭제는 콘텐츠 목록 체크박스 5개 선택 → 「추가 작업」 → 「완전삭제」 → 확인 체크박스 → 완전삭제 (일괄 삭제가 행별 ⋮ 보다 빠르다).

> **2026-09-14 tjchart 3판** — 사용자 요청 "실제 사진 활용"으로 img 01~04 를 TJ미디어 공식 차트 페이지 캡처(앨범아트·메뉴 제거, 순위·곡명·가수 열만, 연도 태그 우리가 얹음)로 교체. 초판 "10위 안 6곡" 은 오기 → 5곡(1·3·4·6·8위, 바다의 왕자 2000년)으로 수정. 2판(3Y-Ec7myV1o) 완전삭제 후 재업로드.

> **2026-09-15 규칙 변경** — ① 자막은 문장 끝·쉼표에서 끊는다(`subs.py`, 이후 제작분부터) ② 대사 기본 감정 angry(§12) ③ 개구리 캐릭터 추가 생성 금지 ④ Studio 시간 드롭다운은 달력을 **Escape 로 닫은 뒤** `input[data-claude=time]` 셀렉터 클릭이 안정적 — 좌표 클릭은 달력 백드롭에 먹힌다.

> **2026-09-15 슬롯 변경** — 매일 12:00·12:30·13:00·13:30·14:00 + 20:00·20:30·21:00·21:30·22:00 (하루 10편). 내일 날짜 예약은 달력 기본값이라 시간만 고르면 되고, 오늘 날짜는 달력에서 골라야 하며 **달력은 Escape 를 두 번(각각 따로) 눌러야 닫힌다.**

> **2026-09-15 함정 추가** — 업로드 다이얼로그에서 달력이 이미 닫힌 상태로 Escape 를 한 번 더 누르면 **다이얼로그 자체가 닫혀 초안으로 빠진다.** Escape 는 `ytcp-date-picker` 가 보일 때 한 번만, 닫혔는지 스크린샷으로 확인 후 시간 선택. 초안으로 빠지면 Shorts 목록 행의 "초안 수정"으로 이어서 예약 가능.
| 2026-09-19 12:00 | `sangjo` | https://youtube.com/shorts/oSHfs8aemYc | 예약(Studio). F형 각색. 할부거래법 25조 상조 해약환급금. 이미지 gpt 14장 |
| 2026-09-19 12:30 | `doorsale` | https://youtube.com/shorts/H4zeniN-518 | 예약(Studio). F형 각색. 방문판매법 8조 14일 청약철회. 로컬 SDXL 14장 |
| 2026-09-19 13:00 | `rental` | https://youtube.com/shorts/kOh6EJi6af4 | 예약(Studio). F형 각색. 소비자분쟁해결기준 대여업 위약금 10%. gpt 6장 + 로컬 8장 |
| 2026-09-19 13:30 | `guard` | https://youtube.com/shorts/5wVwujVOrFI | 예약(Studio). F형 각색. 공동주택관리법 65조 경비원 갑질. 로컬 SDXL 14장 |
| 2026-09-19 14:00 | `interior` | https://youtube.com/shorts/x3AT9Hkdl2g | 예약(Studio). F형 각색. 민법 667조 + 지급명령. 로컬 SDXL 14장 |

| 2026-09-25 13:30 | `sunflowercam` | https://youtube.com/shorts/Thw8IrR6nwE | 예약(Studio). 개드립 726380308 사이다·현장. 로컬 SDXL 768×480 --fast |
| 2026-09-25 14:00 | `frogcall` | https://youtube.com/shorts/WMqvwOOY5jY | 예약(Studio). 개드립 726392009 반전 유머. 로컬 SDXL 768×480 --fast |
| 2026-09-25 20:30 | `knitkeyring` | https://youtube.com/shorts/EK8dMJv3aWo | 예약(Studio). 개드립 726376707 여운형(아이 이름·원본 사진 미사용). 로컬 SDXL 768×480 --fast |
| 2026-09-25 21:00 | `daisomouse` | https://youtube.com/shorts/ZU3iwvUalO8 | 예약(Studio). 개드립 726364557 반전. 로컬 SDXL 768×480 --fast |
| 2026-09-25 21:30 | `genius15` | https://youtube.com/shorts/1q6hl0DzJbE | 예약(Studio). 개드립 726360975 반전. 로컬 SDXL 768×480 --fast |
| 2026-09-25 22:00 | `openreturn` | https://youtube.com/shorts/RMBz4vGN4sg | 예약(Studio). F형 각색. 전자상거래법 17조. 로컬 SDXL 768×480 --fast |
| 2026-09-26 12:00 | `laundrypad` | https://youtube.com/shorts/oftd619oQ68 | 예약(Studio). F형 각색. 소비자분쟁해결기준 세탁업. 로컬 SDXL 768×480 --fast |
| 2026-09-26 12:30 | `taxicard` | https://youtube.com/shorts/MQoYaNiS8po | 예약(Studio). F형 각색. 택시발전법 16조(1차 과태료 20만). 첫 시도는 Escape로 창이 닫혀 초안 OizhqStW95w 남음. 로컬 SDXL 768×480 --fast |
| 2026-09-26 13:00 | `fakeid` | https://youtube.com/shorts/9B2jQh9fAAo | 예약(Studio). F형 각색. 식품위생법 75조(2024.3.29 시행령). 로컬 SDXL 768×480 --fast |
| 2026-09-26 13:30 | `probation90` | https://youtube.com/shorts/J2vbyMbSPuM | 예약(Studio). F형 각색. 최저임금법 5조2항(1년 이상 계약만 감액). 로컬 SDXL 768×480 --fast |
| 2026-09-26 14:00 | `albaleave` | https://youtube.com/shorts/B4L8MqjQSiU | 예약(Studio). F형 각색. 근로기준법 60조. 로컬 SDXL 768×480 --fast |
| 2026-09-26 20:00 | `dogpoop` | https://youtube.com/shorts/OItYLt3AeqE | 예약(Studio). F형 각색. 동물보호법 16·101조(최대 50만). 로컬 SDXL 768×480 --fast |
| 2026-09-26 20:30 | `trashdump` | https://youtube.com/shorts/rrfkGXcT9J8 | 예약(Studio). F형 각색. 폐기물관리법 8·68조(최대 100만). 로컬 SDXL 768×480 --fast |
| 2026-09-26 21:00 | `hairbleach` | https://youtube.com/shorts/-zMWb6wjTjk | 예약(Studio). F형 각색. 소비자분쟁해결기준 이·미용업. 로컬 SDXL 768×480 --fast |
| 2026-09-26 21:30 | `renonoise` | https://youtube.com/shorts/sWemfT7N4Xc | 예약(Studio). F형 각색. 소음·진동관리법 21조+관리규약. 로컬 SDXL 768×480 --fast |

> **2026-09-24 배치 메모** — MCP 작업 창이 가려지면(visibilityState hidden) Studio 타이머가 멈춰 저장이 안 끝난다 → `chrome_switch_tab` 으로 앞으로 가져오면 즉시 진행. 날짜 선택 후 달력은 자동으로 닫히므로 **Escape 를 누르지 않는다**(업로드 창이 닫혀 업로드가 취소됨). vidIQ 확장 패널이 설명란 좌표를 가려 클릭이 새는 경우가 있어 `[class*=vidiq]{display:none}` 스타일을 주입했다.
| 2026-09-26 | bukangi | https://youtube.com/shorts/zeG_lwflKYk | **즉시 공개**. E형 찬반(부캉이 북항 상어). 이미지 mflux Z-Image-Turbo 첫 편. 합성 콘텐츠 "예". 고정 댓글 등록 + 고정 확인창 "고정" 클릭(반영 미확인) |

> **2026-09-26 배치 메모** — 설명 칸 좌표(396,437) 클릭 시 제목 해시태그 추천 버튼(#suggestion-0)이 그 자리에 떠 있으면 눌려 **제목 끝에 '#과태료' 같은 태그가 붙는다**(costcomistake 실제 발생, 게시 전 수정). 설명 칸은 오른쪽 아래(right-40, bottom-15)를 누르고 next 전에 제목 innerText 를 확인한다. '예약' 헤더 y 는 577/609 로 달라져 매번 JS 로 읽는다. 시간 드롭다운은 스크린샷 없이도 shadowRoot 훑어 `.click()` 이 먹었다. 두 lane 이 같은 창을 쓰면 가려진 탭은 hidden 이라 JS 타이머가 멈춘다 → 저장 직전 `chrome_switch_tab`.
| 2026-09-27 12:00 | `mounjaro` | https://youtube.com/shorts/lJk7qmGRtJ8 | 예약(Studio). #마운자로 할인의 진실. codex gen.sh 이미지, 잇슈머형 효과음 |
| 2026-09-27 12:30 | `megaclose` | https://youtube.com/shorts/qIhCSOCK1IM | 예약(Studio). #추석알바 손님 폭탄. codex gen.sh 이미지, 잇슈머형 효과음 |
| 2026-09-27 13:00 | `charger` | https://youtube.com/shorts/Wz5WwIerBfE | 예약(Studio). #충전기 변상 논란. codex gen.sh 이미지, 잇슈머형 효과음 |
| 2026-09-27 13:30 | `jesa11` | https://youtube.com/shorts/SlgN5D4hQ0k | 예약(Studio). #제사 반으로 줄인 집. codex gen.sh 이미지, 잇슈머형 효과음 |
| 2026-09-27 14:00 | `parentfurn` | https://youtube.com/shorts/dwIPPC3vJnU | 예약(Studio). #효도 용달기사 아들. codex gen.sh 이미지, 잇슈머형 효과음 |
| 2026-09-27 20:00 | `chickensale` | https://youtube.com/shorts/FaHzzb0RsJo | 예약(Studio). #치킨값 쿠폰의 비밀. codex gen.sh 이미지, 잇슈머형 효과음 |
| 2026-09-27 20:30 | `ttukgalbi` | https://youtube.com/shorts/Xa--lnTFxSQ | 예약(Studio). #떡갈비집 일요일 휴무. codex gen.sh 이미지, 잇슈머형 효과음 |
| 2026-09-27 21:00 | `tithe` | https://youtube.com/shorts/nJR3cpeSc0A | 예약(Studio). #십일조 아내 월급만. codex gen.sh 이미지, 잇슈머형 효과음 |
| 2026-09-27 21:30 | `usentry` | https://youtube.com/shorts/Sym9EKJYAX0 | 예약(Studio). #입국심사 1시간 털림. codex gen.sh 이미지, 잇슈머형 효과음 |
| 2026-09-27 22:00 | `formula` | https://youtube.com/shorts/JGWJ4g0-eXk | 예약(Studio). #친자확인 분유의 반전. codex gen.sh 이미지, 잇슈머형 효과음 |
| 2026-09-28 12:00 | `coffee5` | https://youtube.com/shorts/-0JtSHX2GLk | 예약(Studio). #배달앱 커피값 4배. codex gen.sh 이미지, 잇슈머형 효과음 |
| 2026-09-28 12:30 | `airpods` | https://youtube.com/shorts/tAK9MfkWYJk | 예약(Studio). #신입사원 에어팟 반전. codex gen.sh 이미지, 잇슈머형 효과음 |
| 2026-09-28 13:00 | `jigekkun` | https://youtube.com/shorts/H2Ll2lJusoU | 예약(Studio). #지게꾼 22살 청년. codex gen.sh 이미지, 잇슈머형 효과음 |
| 2026-09-28 13:30 | `firepreg` | https://youtube.com/shorts/_eEu-Ts-egM | 예약(Studio). #소방관 수당 논란. codex gen.sh 이미지, 잇슈머형 효과음 |
| 2026-09-28 14:00 | `shelfcollapse` | https://youtube.com/shorts/wAABDEwxjIM | 예약(Studio). #책장사고 360만 원. codex gen.sh 이미지, 잇슈머형 효과음 |
| 2026-09-28 20:00 | `lostdog` | https://youtube.com/shorts/37ma60_ctr4 | 예약(Studio). #강아지 찾은 곳 닭집. codex gen.sh 이미지, 잇슈머형 효과음 |
| 2026-09-28 20:30 | `plant300` | https://youtube.com/shorts/SJhG8rybJXQ | 예약(Studio). #꿀직업 화분 월300. codex gen.sh 이미지, 잇슈머형 효과음 |
| 2026-09-28 21:00 | `save30` | https://youtube.com/shorts/ByBVzRC407s | 예약(Studio). #30대 저축 논란. codex gen.sh 이미지, 잇슈머형 효과음 |
| 2026-09-28 21:30 | `ushouse` | https://youtube.com/shorts/jiMNSmg9bNY | 예약(Studio). #맥맨션 썩은 대저택. codex gen.sh 이미지, 잇슈머형 효과음 |
| 2026-09-28 22:00 | `vncustoms` | https://youtube.com/shorts/-xY3XFzmUjY | 예약(Studio). #베트남세관 100달러. codex gen.sh 이미지, 잇슈머형 효과음 |
| 2026-09-26 | `costcomistake` | https://youtube.com/shorts/gQ6nSxjoDxM | **즉시 공개**. #코스트코 핫도그 비밀. codex gen.sh 이미지, 잇슈머형 효과음 |
| 2026-09-26 | `maclipstick` | https://youtube.com/shorts/lgC-VhWQ2Uo | **즉시 공개**. #맥칠리 품절대란 비밀. codex gen.sh 이미지, 잇슈머형 효과음 |

| 2026-09-29 12:00 | `severance` | https://youtube.com/shorts/B1M5Eh-HkpE | 예약(Studio). F형 각색. #퇴직금 수습도 포함. codex 10장, 8비트 BGM 이전 빌드 |
| 2026-09-29 12:30 | `firenotice` | https://youtube.com/shorts/OykoPRPDHhM | 예약(Studio). F형 각색. #해고예고수당 30일. codex 10장, 8비트 BGM 이전 빌드 |
| 2026-09-29 13:00 | `jeonsequit` | https://youtube.com/shorts/0rlX6Sys4Xw | 예약(Studio). F형 각색. #전세 묵시적갱신 해지. codex 10장, 8비트 BGM 이전 빌드 |
| 2026-09-29 13:30 | `silgeoju` | https://youtube.com/shorts/A9QcyQz38Xw | 예약(Studio). F형 각색. #실거주 갱신거절 배상. codex 10장, 8비트 BGM 이전 빌드 |
| 2026-09-29 14:00 | `boiler` | https://youtube.com/shorts/x0FbpRex6Is | 예약(Studio). F형 각색. #보일러 수리 집주인. codex 10장, 8비트 BGM 이전 빌드 |
| 2026-09-29 20:00 | `usedflaw` | https://youtube.com/shorts/hzyrMP6aswA | 예약(Studio). F형 각색. #중고거래 숨긴 하자. codex 10장, 8비트 BGM 이전 빌드 |
| 2026-09-29 20:30 | `dogbite` | https://youtube.com/shorts/1stS9Hy2buU | 예약(Studio). F형 각색. #개물림 견주 책임. codex 10장, 8비트 BGM 이전 빌드 |
| 2026-09-29 21:00 | `smoke` | https://youtube.com/shorts/dPTw1dYYvSg | 예약(Studio). F형 각색. #층간흡연 해결법. codex 10장, 8비트 BGM 이전 빌드 |
| 2026-09-29 21:30 | `cctvview` | https://youtube.com/shorts/nMqqqboCSJc | 예약(Studio). F형 각색. #CCTV 열람 방법. codex 10장, 8비트 BGM 이전 빌드 |
| 2026-09-29 22:00 | `groupchat` | https://youtube.com/shorts/APhMMbLLdV0 | 예약(Studio). F형 각색. #단톡방 명예훼손. codex 10장, 8비트 BGM 이전 빌드 |
| 2026-09-30 12:00 | `iou` | https://youtube.com/shorts/VpnIfxYsn-I | 예약(Studio). F형 각색. #차용증 없는 돈. codex 10장, 8비트 BGM 이전 빌드 |
| 2026-09-30 12:30 | `criminalsettle` | https://youtube.com/shorts/Exjbw6GoUSc | 예약(Studio). F형 각색. #형사합의금 직접지급. codex 10장, 8비트 BGM 이전 빌드 |
| 2026-09-30 13:00 | `matchmaker` | https://youtube.com/shorts/vOGLjdG7md8 | 예약(Studio). F형 각색. #결정사 가입비 환불. codex 10장, 8비트 BGM 이전 빌드 |
| 2026-09-30 13:30 | `luggage` | https://youtube.com/shorts/4Mc98btKlyY | 예약(Studio). F형 각색. #수하물파손 7일. codex 10장, 8비트 BGM 이전 빌드 |
| 2026-09-30 14:00 | `brokerfee` | https://youtube.com/shorts/cKM3cCcYc2s | 예약(Studio). F형 각색. #복비 상한 초과. codex 10장, 8비트 BGM 이전 빌드 |
| 2026-09-30 20:00 | `inherit` | https://youtube.com/shorts/GG8jvQMMr2Y | 예약(Studio). F형 각색. #상속포기 3개월. codex 10장, 8비트 BGM 이전 빌드 |
| 2026-09-30 20:30 | `yuryubun` | https://youtube.com/shorts/dRFvWWsT2Js | 예약(Studio). F형 각색. #유류분 상속권 상실. codex 10장, 8비트 BGM 이전 빌드 |
| 2026-09-30 21:00 | `vetfee` | https://youtube.com/shorts/TnMNZ20TYp4 | 예약(Studio). F형 각색. #동물병원 진료비. codex 10장, 8비트 BGM 이전 빌드 |
| 2026-09-30 21:30 | `bankbook` | https://youtube.com/shorts/19-oZ2VP8PU | 예약(Studio). F형 각색. #통장대여 5년 징역. codex 10장, 8비트 BGM 이전 빌드 |
| 2026-09-30 22:00 | `neighborcctv` | https://youtube.com/shorts/w7KpguEo1i0 | 예약(Studio). F형 각색. #옆집CCTV 사생활. codex 10장, 8비트 BGM 이전 빌드 |
| 2026-10-01 12:00 | `house50` | https://youtube.com/shorts/z-jgiioJr3g | 예약(Studio). 개드립 726894694. #종부세 50억집 논란. 8비트 BGM |
| 2026-10-01 12:30 | `bankhours` | https://youtube.com/shorts/3EZY1K4Lz8o | 예약(Studio). 개드립 726991113. #은행 영업시간 단축. 8비트 BGM |
| 2026-10-01 13:00 | `seoulgift` | https://youtube.com/shorts/BVq2euhf-d0 | 예약(Studio). 개드립 726866449. #서울 월세 지방 이사. 8비트 BGM |
| 2026-10-01 13:30 | `vaccine` | https://youtube.com/shorts/_1oyOhorEbs | 예약(Studio). 개드립 726969742. #예방접종 거부 처벌. 8비트 BGM |
| 2026-10-01 14:00 | `inheritgap` | https://youtube.com/shorts/0lHHQXHPapY | 예약(Studio). 개드립 726881855. #상속 손주는 따질까. 8비트 BGM |
| 2026-10-01 20:00 | `leaveday` | https://youtube.com/shorts/dhRNUAwDLGs | 예약(Studio). 개드립 726755892. #연차 시기변경권. 8비트 BGM |
| 2026-10-01 20:30 | `taeum` | https://youtube.com/shorts/xvmt4DGFi1g | 예약(Studio). 개드립 726763429. #태움 직장내괴롭힘. 8비트 BGM |
| 2026-10-01 21:00 | `badtenant` | https://youtube.com/shorts/2-VWu1k7Mqw | 예약(Studio). 개드립 726935017. #원상회복 보증금 공제. 8비트 BGM |
| 2026-10-01 21:30 | `quitcall` | https://youtube.com/shorts/tLoiUoJOqxI | 예약(Studio). 개드립 726854456. #퇴사날 피드백 50개. 8비트 BGM |
| 2026-10-02 12:00 | `ranksoldier` | https://youtube.com/shorts/_nXXbP7WcgI | 예약(Studio). 개드립 726880011. #군대 군장돌리기 논란. 8비트 BGM |
| 2026-10-02 13:00 | `smartson` | https://youtube.com/shorts/ltFSKsWo_aA | 예약(Studio). 개드립 726969455. #아들 선택 밸런스게임. 8비트 BGM |
| 2026-10-02 14:00 | `diet5` | https://youtube.com/shorts/jVc3-XOFqz4 | 예약(Studio). 개드립 726726973. #다이어트 5가지 루틴. 8비트 BGM |
| 2026-10-02 19:00 | `schooltrip` | https://youtube.com/shorts/anSXPuGXaZA | 예약(Studio). 개드립 726962664. #수학여행 해외 지원금. 8비트 BGM |
| 2026-10-02 20:00 | `regularjerk` | https://youtube.com/shorts/sUYEQgIUQO0 | 예약(Studio). 개드립 726748681. #곱빼기 진상 논란. 8비트 BGM |
| 2026-10-02 21:00 | `dolgift` | https://youtube.com/shorts/GcYB-BLU0xA | 예약(Studio). 개드립 726863062. #돌잔치 답례품 논란. 8비트 BGM |
| 2026-10-03 12:00 | `keyring` | https://youtube.com/shorts/fHcSrhEZBu0 | 예약(Studio). 개드립 726863348. #조카 키링 논란. 8비트 BGM |
| 2026-10-03 13:00 | `newbieoffice` | https://youtube.com/shorts/NtjQq9CzRh0 | 예약(Studio). 개드립 726868008. #첫월급 신입 간식. 8비트 BGM |
| 2026-10-03 14:00 | `illegalpark` | https://youtube.com/shorts/jym7CVu_KOY | 예약(Studio). 개드립 726864713. #불법주차 신고 보복. 8비트 BGM |
| 2026-10-03 19:00 | `gangnampark` | https://youtube.com/shorts/EZZ2C4WhC4c | 예약(Studio). 개드립 726895653. #강남주차장 회차요금. 8비트 BGM |
| 2026-10-03 20:00 | `rent85` | https://youtube.com/shorts/ab3fi-VqKmk | 예약(Studio). 개드립 726957920. #금천구 월세 85만. 8비트 BGM |
| 2026-10-03 21:00 | `cashshort` | https://youtube.com/shorts/vIUnRwDQR38 | 예약(Studio). F형 각색. codex 3장+Commons CC 7장. #알바 월급 공제 불법. 8비트 BGM |
| 2026-10-04 12:00 | `commute` | https://youtube.com/shorts/FIhDrRXwuNk | 예약(Studio). F형 P배치. #출퇴근사고 산재. 8비트 BGM |
| 2026-10-04 13:00 | `silson` | https://youtube.com/shorts/eph3Wzghj5A | 예약(Studio). F형 P배치. #실손보험 청구 3년. 8비트 BGM |
| 2026-10-04 14:00 | `phishing` | https://youtube.com/shorts/-tS7ka_kHk8 | 예약(Studio). F형 P배치. #보이스피싱 지급정지. 8비트 BGM |
| 2026-10-04 19:00 | `jobless` | https://youtube.com/shorts/SmSvT-wDsC0 | 예약(Studio). F형 P배치. #실업급여 자진퇴사. 8비트 BGM |
| 2026-10-04 20:00 | `childsupport` | https://youtube.com/shorts/a9_5-jVA2Cw | 예약(Studio). F형 P배치. #양육비 미지급 처벌. 8비트 BGM |
| 2026-10-04 21:00 | `pension` | https://youtube.com/shorts/aaPnXH7nNPg | 예약(Studio). F형 P배치. #펜션 예약취소 환불. 8비트 BGM |
| 2026-10-05 12:00 | `airfare` | https://youtube.com/shorts/pO7V9C8xIWY | 예약(Studio). F형 P배치. #항공권 취소수수료. 8비트 BGM |
| 2026-10-05 13:00 | `foreignbody` | https://youtube.com/shorts/i6yaJ0qXERw | 예약(Studio). F형 P배치. #음식 이물질 보상. 8비트 BGM |
| 2026-10-05 14:00 | `nocontract` | https://youtube.com/shorts/GPK7OszXmYY | 예약(Studio). F형 P배치. #근로계약서 벌금. 8비트 BGM |
| 2026-10-05 19:00 | `medbill` | https://youtube.com/shorts/7X8Ih1qght4 | 예약(Studio). F형 P배치. #병원비 진료비확인. 8비트 BGM |
| 2026-10-05 20:00 | `movein` | https://youtube.com/shorts/kfJBMAR9CT0 | 예약(Studio). F형 P배치. #전입신고 확정일자. 8비트 BGM |
| 2026-10-05 21:00 | `parental` | https://youtube.com/shorts/en3NBP-NZaM | 예약(Studio). F형 P배치. #육아휴직 복직 거부. 8비트 BGM |
| 2026-10-06 12:00 | `divorce2y` | https://youtube.com/shorts/iBPeu9XTKrE | 예약(Studio). F형 P배치. #이혼 재산분할 2년. 8비트 BGM |
| 2026-10-06 13:00 | `will` | https://youtube.com/shorts/BTNVF6f9qa4 | 예약(Studio). F형 P배치. #자필 유언장 효력. 8비트 BGM |
| 2026-10-06 14:00 | `aptdefect` | https://youtube.com/shorts/E07LYy6XdKY | 예약(Studio). F형 P배치. #아파트 하자보수 기간. 8비트 BGM |
| 2026-10-06 19:00 | `repairfund` | https://youtube.com/shorts/fgmbf186gOg | 예약(Studio). F형 P배치. #장기수선충당금 반환. 8비트 BGM |
| 2026-10-03 17:00 | `usedcar30` | https://youtube.com/shorts/-ei6WBcd7Hs | 예약(Studio). F형 각색·훅v2. #중고차 30일 보증. 시작음 없음 |
| 2026-10-03 17:30 | `deposit12` | https://youtube.com/shorts/eJ_RKClREBk | 예약(Studio). F형 각색·훅v2. #보증금 이자 12%. 시작음 없음 |
| 2026-10-03 18:00 | `hallway100` | https://youtube.com/shorts/njOTLmJw7tM | 예약(Studio). F형 각색·훅v2. #복도 적치 과태료. 시작음 없음 |
| 2026-10-04 12:30 | `trashcash` | https://youtube.com/shorts/y6iL-02i4_U | 예약(Studio). 훅v2 개드립. #습득물 2500만원. 시작음 없음 |
| 2026-10-04 13:30 | `saucetable` | https://youtube.com/shorts/fRcHhwy3MEc | 예약(Studio). 훅v2 개드립. #식당 소스통 불법?. 시작음 없음 |
| 2026-10-04 19:30 | `sev11` | https://youtube.com/shorts/OJZzFQP1tB0 | 예약(Studio). 훅v2 각색. #알바 11개월 퇴직금. 시작음 없음 |
| 2026-10-04 20:30 | `dogbone` | https://youtube.com/shorts/99X08FbuFMU | 예약(Studio). 훅v2 개드립. #족발뼈 강아지 논란. 시작음 없음 |
| 2026-10-05 12:30 | `pcfraud` | https://youtube.com/shorts/w-u-x_8cOuQ | 예약(Studio). 훅v2 개드립. #사기방조 무죄 취지. 시작음 없음 |
| 2026-10-05 13:30 | `spamgift` | https://youtube.com/shorts/Nzi6Su-mAB0 | 예약(Studio). 훅v2 개드립. #스팸선물 버린 알바. 시작음 없음 |
| 2026-10-05 19:30 | `dentrun` | https://youtube.com/shorts/Y4H0caVS2Gs | 예약(Studio). 훅v2 각색. #문콕 도주 범칙금. 시작음 없음 |
| 2026-10-05 20:30 | `cutin800` | https://youtube.com/shorts/oR-czT0x3YA | 예약(Studio). 훅v2 개드립. #끼어들기 800건. 시작음 없음 |
| 2026-10-06 12:30 | `firsthome` | https://youtube.com/shorts/ZJlHibx7QUQ | 예약(Studio). 훅v2 개드립. #상속지분 청약 예외. 시작음 없음 |
| 2026-10-06 13:30 | `hairturkey` | https://youtube.com/shorts/pBxF9CXDps4 | 예약(Studio). 훅v2 개드립. #터키 모발이식 반전. 시작음 없음 |
| 2026-10-06 19:30 | `debt10` | https://youtube.com/shorts/VvBw4Xn9HRc | 예약(Studio). 훅v2 각색. #빌려준돈 10년 시효. 시작음 없음 |
| 2026-10-06 20:00 | `phonealbum` | https://youtube.com/shorts/rVeoB-k9-lM | 예약(Studio). 훅v2 개드립. #몰카 오해 대처법. 시작음 없음 |
| 2026-10-06 20:30 | `kidzone12` | https://youtube.com/shorts/Ib-JhGKIlxs | 예약(Studio). 훅v2 각색. #스쿨존 주차 과태료. 시작음 없음 |
| 2026-10-06 21:00 | `chokbeop` | https://youtube.com/shorts/Mqp75lIbxpw | 예약(Studio). 훅v2 개드립. #촉법소년 고소. 시작음 없음 |
| 2026-10-04 22:40 | `stablehusband2` | https://youtube.com/shorts/7Rgyev9tLkA | 즉시 공개(Studio, Zernio 유튜브 연결 끊김). 개드립. #안정형. **경모 목소리 TTS 첫 편**(tts_myvoice.py). 합성 콘텐츠 고지 예 |

> **2026-10-07 30편 배치**(개드립 13 + F형 각색 17, 10/8~10/10 하루 10편). 함정: 백그라운드 빌드가 mp4 를 쓰는 중에 업로드하면 Studio 가 「처리 중단됨」을 띄운다(leavecash 1회, 임시본 삭제 후 재업로드) — 업로드는 run.log 의 `DONE <slug>` 확인 뒤에. 설명 칸 좌표는 제목 입력 직후 레이아웃이 흔들리므로 1.5초 대기 후 rect 를 다시 읽는다.

| 2026-10-08 12:00 | `juhyu` | https://youtube.com/shorts/E7C0zUZ55yA | 예약(Studio). F형 각색. #주휴수당 조건. 훅v2·8비트 BGM |
| 2026-10-08 12:30 | `housebuyer` | https://youtube.com/shorts/jxpE-oZrWXo | 예약(Studio). 개드립 728185782. #집 깎아준 매도인. 훅v2·8비트 BGM |
| 2026-10-08 13:00 | `recordcall` | https://youtube.com/shorts/lUJtrnXczJE | 예약(Studio). F형 각색. #몰래 녹음 합법?. 훅v2·8비트 BGM |
| 2026-10-08 13:30 | `youtubework` | https://youtube.com/shorts/p0RgQt2ReCY | 예약(Studio). 개드립 728395804. #근무중 유튜브 면직. 훅v2·8비트 BGM |
| 2026-10-08 14:00 | `taxking` | https://youtube.com/shorts/DS9p2lDssuo | 예약(Studio). 개드립 728416846. #체납 1위 4천억. 훅v2·8비트 BGM |
| 2026-10-08 19:00 | `smokeplay` | https://youtube.com/shorts/lGtZsi57tRA | 예약(Studio). 개드립 728209394. #놀이터 흡연 폭행. 훅v2·8비트 BGM |
| 2026-10-08 19:30 | `milexempt` | https://youtube.com/shorts/FZxwzxV0bfM | 예약(Studio). 개드립 728277563. #병역특례 폐지?. 훅v2·8비트 BGM |
| 2026-10-08 20:00 | `medalapt` | https://youtube.com/shorts/g_-bgqRWzCQ | 예약(Studio). 개드립 728230332. #메달리스트 특공. 훅v2·8비트 BGM |
| 2026-10-08 20:30 | `scalper` | https://youtube.com/shorts/k6xr496A1EM | 예약(Studio). 개드립 728277633. #암표 신고 포상금. 훅v2·8비트 BGM |
| 2026-10-08 21:00 | `landlordin` | https://youtube.com/shorts/QnBaP0tOLe4 | 예약(Studio). F형 각색. #집주인 무단출입. 훅v2·8비트 BGM |
| 2026-10-09 12:00 | `fivejob` | https://youtube.com/shorts/nFICqUfR1jg | 예약(Studio). F형 각색. #5인미만 야근수당. 훅v2·8비트 BGM |
| 2026-10-09 12:30 | `dog11h` | https://youtube.com/shorts/TzE_flh8VCU | 예약(Studio). 개드립 728371558. #1인가구 반려견. 훅v2·8비트 BGM |
| 2026-10-09 13:00 | `breaktime` | https://youtube.com/shorts/5YGC1CPzAmk | 예약(Studio). F형 각색. #휴게시간 1시간. 훅v2·8비트 BGM |
| 2026-10-09 13:30 | `cheongyak` | https://youtube.com/shorts/PLC_STM9erE | 예약(Studio). 개드립 728437654. #청약통장 해지. 훅v2·8비트 BGM |
| 2026-10-09 14:00 | `giftcon` | https://youtube.com/shorts/xe8sFYHsttc | 예약(Studio). F형 각색. #기프티콘 환불. 훅v2·8비트 BGM |
| 2026-10-09 19:00 | `jjambbong` | https://youtube.com/shorts/9mAiSFmJyaM | 예약(Studio). 개드립 728305507. #짬뽕 강아지 장례비. 훅v2·8비트 BGM |
| 2026-10-09 19:30 | `sixho` | https://youtube.com/shorts/mgVQvLF2uOs | 예약(Studio). 개드립 728215430. #6호처분 탈출 모의. 훅v2·8비트 BGM |
| 2026-10-09 20:00 | `hakpok4` | https://youtube.com/shorts/nuk_7UL-1N0 | 예약(Studio). F형 각색. #학폭 기록 4년. 훅v2·8비트 BGM |
| 2026-10-09 20:30 | `wrongsend` | https://youtube.com/shorts/7MNnrN7KaVY | 예약(Studio). F형 각색. #착오송금 반환. 훅v2·8비트 BGM |
| 2026-10-09 21:00 | `directbuy` | https://youtube.com/shorts/GbuuV94aCfk | 예약(Studio). F형 각색. #직구 되팔기 처벌. 훅v2·8비트 BGM |
| 2026-10-10 12:00 | `minwage` | https://youtube.com/shorts/s1JHSYKcfWU | 예약(Studio). F형 각색. #최저시급 미달. 훅v2·8비트 BGM |
| 2026-10-10 12:30 | `bride12` | https://youtube.com/shorts/p09za5VVCck | 예약(Studio). 개드립 728389188. #신혼 12억 논란. 훅v2·8비트 BGM |
| 2026-10-10 13:00 | `paternity20` | https://youtube.com/shorts/n4WVYEFNJi4 | 예약(Studio). F형 각색. #배우자 출산휴가. 훅v2·8비트 BGM |
| 2026-10-10 13:30 | `prizetax` | https://youtube.com/shorts/8vb4GLL4l3A | 예약(Studio). F형 각색. #경품 당첨 세금. 훅v2·8비트 BGM |
| 2026-10-10 14:00 | `leavecash` | https://youtube.com/shorts/5yy0u7kZ7MU | 예약(Studio). F형 각색. #연차수당 미지급. 훅v2·8비트 BGM |
| 2026-10-10 19:00 | `gamerinsult` | https://youtube.com/shorts/coit1AzP3Ts | 예약(Studio). 개드립 728218706. #모욕죄 고소 취하. 훅v2·8비트 BGM |
| 2026-10-10 19:30 | `taxirefuse` | https://youtube.com/shorts/4-Qy2uCvAz0 | 예약(Studio). F형 각색. #택시 승차거부. 훅v2·8비트 BGM |
| 2026-10-10 20:00 | `breakupgift` | https://youtube.com/shorts/jqeBUVPAS14 | 예약(Studio). F형 각색. #이별 선물 반환. 훅v2·8비트 BGM |
| 2026-10-10 20:30 | `wrongparcel` | https://youtube.com/shorts/eaybIMtVyXw | 예약(Studio). F형 각색. #오배송 택배 횡령. 훅v2·8비트 BGM |
| 2026-10-10 21:00 | `bikedui` | https://youtube.com/shorts/nTEMTnlNopk | 예약(Studio). F형 각색. #자전거 음주운전. 훅v2·8비트 BGM |

> **2026-10-09 20편 배치**(한글날 4 + 개드립 4 + 법 6 + 부동산법 6). 한글날 4편은 당일 21:30~23:00, 나머지 10/11~10/12. MCP 작업 창이 hidden 상태여도 `chrome_screenshot` 을 몇 번 찍어 레이아웃을 강제하고 setTimeout 없이 단계별로 호출하면 예약된다. 시간 항목은 높이 0이라 textContent 로만 찾는다. 예약 완료 다이얼로그는 반드시 「닫기」를 눌러야 다음 업로드 입력칸이 뜬다.

| 2026-10-09 21:30 | `hangulday` | https://youtube.com/shorts/7ikobNoG1FE | 예약(Studio). 각색. #한글날 공휴일 23년. 훅v2·8비트 BGM |
| 2026-10-09 22:00 | `kfoodhangul` | https://youtube.com/shorts/P7H5H40OOqc | 예약(Studio). 개드립 728715969. #해외 한글 포장. 훅v2·8비트 BGM |
| 2026-10-09 22:30 | `signhangul` | https://youtube.com/shorts/hv9-idDyFVo | 예약(Studio). 각색. #영어간판 한글병기. 훅v2·8비트 BGM |
| 2026-10-09 23:00 | `gongmun` | https://youtube.com/shorts/IZ-GhBUdkPw | 예약(Studio). 각색. #공문서 외국어 남용. 훅v2·8비트 BGM |
| 2026-10-11 12:00 | `payslip` | https://youtube.com/shorts/e8DWYttM-jM | 예약(Studio). 각색. #임금명세서 의무. 훅v2·8비트 BGM |
| 2026-10-11 12:30 | `roomfee` | https://youtube.com/shorts/eVnqRgr_IdM | 예약(Studio). 각색. #원룸 관리비 내역. 훅v2·8비트 BGM |
| 2026-10-11 13:00 | `msafer` | https://youtube.com/shorts/LDgPoqgJHXI | 예약(Studio). 각색. #명의도용 엠세이퍼. 훅v2·8비트 BGM |
| 2026-10-11 13:30 | `dealreport` | https://youtube.com/shorts/vHtLH9bk3jM | 예약(Studio). 각색. #부동산 실거래 신고. 훅v2·8비트 BGM |
| 2026-10-11 14:00 | `lostcard60` | https://youtube.com/shorts/f-Li-R3WSpA | 예약(Studio). 각색. #카드 분실 보상. 훅v2·8비트 BGM |
| 2026-10-11 19:00 | `gajeonsub` | https://youtube.com/shorts/ZYW29yiFVFg | 예약(Studio). 개드립 728619236. #가전구독 위약금. 훅v2·8비트 BGM |
| 2026-10-11 19:30 | `thiefface` | https://youtube.com/shorts/Jmub1RXd5AI | 예약(Studio). 각색. #도둑 얼굴 공개. 훅v2·8비트 BGM |
| 2026-10-11 20:00 | `leasereg` | https://youtube.com/shorts/pGbBycrPd-Y | 예약(Studio). 각색. #임차권등기명령. 훅v2·8비트 BGM |
| 2026-10-11 20:30 | `armorpass` | https://youtube.com/shorts/uFsQgLSO2hY | 예약(Studio). 개드립 728758859. #장갑차 하이패스. 훅v2·8비트 BGM |
| 2026-10-11 21:00 | `nomovein` | https://youtube.com/shorts/978hXLmKkRw | 예약(Studio). 각색. #전입신고 금지 특약. 훅v2·8비트 BGM |
| 2026-10-12 12:00 | `cardfee` | https://youtube.com/shorts/22sxaokJsBY | 예약(Studio). 각색. #카드 수수료 전가. 훅v2·8비트 BGM |
| 2026-10-12 13:00 | `week52` | https://youtube.com/shorts/XjFVy8KFy8k | 예약(Studio). 각색. #주52시간 초과. 훅v2·8비트 BGM |
| 2026-10-12 14:00 | `gongmu39` | https://youtube.com/shorts/5ncajM-XGqc | 예약(Studio). 개드립 728606543. #첫발령 편도 39km. 훅v2·8비트 BGM |
| 2026-10-12 19:00 | `newowner` | https://youtube.com/shorts/nW0-TKceb5Q | 예약(Studio). 각색. #집주인 바뀌면 전세. 훅v2·8비트 BGM |
| 2026-10-12 20:00 | `rent2late` | https://youtube.com/shorts/jkZEFOO14Ks | 예약(Studio). 각색. #월세 연체 계약해지. 훅v2·8비트 BGM |
| 2026-10-12 21:00 | `wifesalary` | https://youtube.com/shorts/O1P98EF8e04 | 예약(Studio). 개드립 728628225. #와이프 연봉 역전. 훅v2·8비트 BGM |
| 2026-10-13 12:00 | `sancheong` | https://youtube.com/shorts/y6sOXAcF8eU | 예약(Studio). **사용자 직접 촬영 맛집 후기**(산청 흑돼지, 영상 15컷+AI 3장). #흑돼지 1근 7만원. 현장음 깔기·지글 효과음 1회. 합성 콘텐츠 예·유료 프로모션 아니요 |

- 2026-10-10 롱폼 long_hospital5060 "5060이 모르고 놓치는 병원비 3가지, 이렇게 돌려받으세요" 법푸는휴지 즉시 공개 https://youtu.be/9qQAtnzic0I — 첫 5060 정보 롱폼(이슬+타입캐스트, 홈페이지 캡처·색연필)

- 2026-10-10 쇼츠 jebak30 "#장애인주차 박제 역풍" 법푸는휴지 즉시 공개 https://youtube.com/shorts/uXNAVYhowyo — 첫 Remotion·이슈쿠키 쇼츠
- ⚠️ 2026-10-10 함정: 설명칸 좌표 클릭이 해시태그 추천 버튼에 걸리면 insertText 가 제목에 들어감 → 클릭 후 activeElement 가 설명 textbox 인지 확인하고 넣는다. **Escape 를 누르면 업로드 대화상자 자체가 닫힌다**(초안으로 남음 → 콘텐츠>Shorts 에서 "초안 수정"으로 재개)

- 2026-10-11 23:00 예약 쇼츠 teslaplate "#임시번호판 인수거부" 법푸는휴지 https://youtube.com/shorts/9anjlYA4L6Y
| 2026-10-13 19:00 | `pensionkill` | https://youtube.com/shorts/DdMiEsW0jlY | 예약(Studio). **뉴스+법조항 첫 편**(머니투데이 008/0005424740). #이은해 연금환수 불가. 버전3 Remotion·いらすとや 캐릭터·물음표 핑 끔·모자이크 가상인물. 합성 콘텐츠 예 |
| ~~2026-10-13 20:00~~ | `daeri13` | ~~rf52REJOVHU~~ | **10/13 19:30 사용자 지시로 공개 전 완전삭제(살인 소재)**. 예약(Studio). 뉴스+법조항. #대리기사 살인 13년. 버전3·いらすとや·물음표 끔 |
| ~~2026-10-13 21:00~~ | `hanger8` | ~~RTeWyYd4yWQ~~ | **10/13 19:40 사용자 지시로 공개 전 완전삭제(폭행 소재)**. 예약(Studio). 뉴스+법조항. #아내 폭행 집행유예. 버전3·いらすとや·물음표 끔 |
| 2026-10-14 12:00 | `wage4day` | https://youtube.com/shorts/SJODyEZyT-s | 예약(Studio). 뉴스+법조항. #나흘 퇴사 임금 고소. 버전3·いらすとや·물음표 끔 |
| 2026-10-14 13:00 | `meoktwi16` | https://youtube.com/shorts/yHLfVoM1Qtk | 예약(Studio). 뉴스+법조항. #고깃집 먹튀 처벌. 버전3·いらすとや·물음표 끔 |
| 2026-10-14 14:00 | `icecream` | https://youtube.com/shorts/c5iKMfbiVbE | 예약(Studio). 뉴스+법조항. #무인매장 전기 절도. 버전3·いらすとや·물음표 끔 |
| ~~2026-10-14 19:00~~ | `diary9` | ~~eD8uoYPk77g~~ | **10/13 19:30 사용자 지시로 공개 전 완전삭제(아동학대 소재)**. 예약(Studio). 뉴스+법조항. #일기장 아동학대 유죄. 버전3·いらすとや·물음표 끔 |
| 2026-10-14 20:00 | `katalkleak` | https://youtube.com/shorts/5QB1X97_yyk | 예약(Studio). 뉴스+법조항. #카톡 몰래보기 유죄. 버전3·いらすとや·물음표 끔 |
| 2026-10-14 21:00 | `rose10` | https://youtube.com/shorts/PBa4YQvnjiE | 예약(Studio). 뉴스+법조항. #남의집 장미 절도. 버전3·いらすとや·물음표 끔 |
| 2026-10-15 12:00 | `sache40k` | https://youtube.com/shorts/bST5SBxiyTU | 예약(Studio). 뉴스+법조항. #연이자 4만% 사채. 버전3·いらすとや·물음표 끔 |
| 2026-10-15 13:00 | `healthrefund` | https://youtube.com/shorts/8yJ2oNUybPs | 예약(Studio). 뉴스+법조항. #건보료 환급 455억. 버전3·いらすとや·물음표 끔 |

> **2026-10-13 뉴스+법조항 11편 배치 함정 (MCP 작업 창이 hidden 일 때)**
> - 업로드 직후 제목칸이 rect 0 이면 **`chrome_click_element` 셀렉터 클릭을 한 번 더** — 첫 실패가 붙이는 failure screenshot 이 리페인트를 강제해 두 번째엔 잡힌다. 좌표 클릭·setTimeout 대기는 hidden 탭에서 스로틀돼 쓸모없다
> - 달력 칸이 0개면 **없는 셀렉터(`input[type="file"]`)를 일부러 클릭해 실패 스크린샷을 찍히게** 한 뒤 pick() — 바로 잡힌다. 날짜 고른 직후 시간칸 클릭은 한 번 "covered" 로 실패하니 재시도
> - `ytcp-date-picker` 의 dateText 를 JS 로 바꾸면 날짜가 "선택"으로 날아간다 — 쓰지 말 것
> - 예약 클릭 후 공유 다이얼로그가 hidden 탭에서 안 뜰 수 있다 → **다른 탭에서 콘텐츠>Shorts 목록의 "예약됨"으로 확인**
> - 이슈쿠키 TTS 는 영문 약자(CCTV) 문장을 통째로 실패시킨다 → `say` 에 "씨씨티비". 조문 번호("제346조")·큰 숫자(455억·4조2477억)는 자주 틀리게 읽혀 받아쓰기 ⚠ 를 보고 반올림·생략으로 고친다
| 2026-10-14 19:00 | `tint63` | https://youtube.com/shorts/pbbsRfKPaY4 | 예약(Studio). 개드립+법조항. #선팅 덧방 6.3%. 버전3·いらすとや·물음표 끔 |
| 2026-10-15 14:00 | `truckcamp` | https://youtube.com/shorts/xgLpy0huTUY | 예약(Studio). 개드립+법조항. #탑차 캠핑카 튜닝. 버전3·いらすとや·물음표 끔 |
| 2026-10-15 19:00 | `toolwife` | https://youtube.com/shorts/F3WC3Qe7Ofc | 예약(Studio). 개드립+법조항. #남편 공구 버리면. 버전3·いらすとや·물음표 끔 |
| 2026-10-15 20:00 | `beatbox` | https://youtube.com/shorts/PAQSv7ionlA | 예약(Studio). 개드립+법조항. #고속도로 비트박스. 버전3·いらすとや·물음표 끔 |
| 2026-10-15 21:00 | `rebar3` | https://youtube.com/shorts/zIP5ZI9Jkf8 | 예약(Studio). 개드립+법조항. #철근 누락 벌점3점. 버전3·いらすとや·물음표 끔 |
| 2026-10-13 23:39 (즉시공개) | `fridgehack` | https://youtube.com/shorts/7asZvjCBPdg | 공개(Studio). 뉴스+법조항. #마트 냉장고 해킹. 버전3·いらすとや·물음표 끔 |
| 2026-10-13 23:54 (즉시공개) | `ainews14` | https://youtube.com/shorts/hWMLdPZzWx8 | 공개(Studio). 뉴스+법조항. #AI 뉴스 저작권. 버전3·いらすとや·물음표 끔 |
| 2026-10-15 20:30 | `airforcex` | https://youtube.com/shorts/2KKqVwC6a2g | 예약(Studio). 개드립 729707711. #공군 유격 행군. 버전3·いらすとや·물음표 끔 |
| 2026-10-15 21:30 | `dinkmarry` | https://youtube.com/shorts/UC8N8IOlX6g | 예약(Studio). 개드립+법조항 729700202. #딩크 혼인신고. 버전3 |
| 2026-10-15 22:00 | `samik5dong` | https://youtube.com/shorts/Q31nh5Ojhzc | 예약(Studio). 개드립+법조항 729705122. #5동만 빼고 재건축. 버전3 |
| 2026-10-15 22:30 | `goryeohanbok` | https://youtube.com/shorts/KaUMYbmi5E4 | 예약(Studio). 개드립 729545163. #한복 입구컷. 버전3 |
| 2026-10-15 23:00 | `tendongwater` | https://youtube.com/shorts/SK5NnwMwtv8 | 예약(Studio). 개드립 729622105. #텐동집 정수기. 버전3 |

> **2026-10-15 함정**: ① 이슈쿠키 TTS 한 줄만 다시 뽑을 땐 `tts/line_NNN.wav` 와 함께 **`ic_tmp/` 도 지운다** — 안 지우면 이전 테이크(옛 문장)를 그대로 다시 골라 온다. ② 시간 칸은 좌표 클릭이 backdrop 에 먹히는 일이 잦다 → `chrome_click_element` 셀렉터 `ytcp-datetime-picker #time-of-day-container input` 로 열면 바로 됨. 날짜는 `#datepicker-trigger` 셀렉터 클릭 후 pick()
| 2026-10-16 12:00 | `lambmeat` | https://youtube.com/shorts/1V3um-XATiI | 예약(Studio). 개드립 729651139. #양고기 입문. 버전3 |
| 2026-10-16 13:00 | `modelywall` | https://youtube.com/shorts/TOpbx7rqPjI | 예약(Studio). 개드립 729534790. #모델Y 국산차 가격. 버전3 |
| 2026-10-16 14:00 | `marathonbus` | https://youtube.com/shorts/xZGP9xsKVHs | 예약(Studio). 개드립+법조항 729500377. #마라톤 버스 우회. 버전3 |
| 2026-10-16 19:00 | `accdeath` | https://youtube.com/shorts/leBJWuXaqIQ | 예약(Studio). 개드립+뉴스 729691283. #고속도로 사망 52%. 버전3 |
| 2026-10-16 20:00 | `weddingmeal` | https://youtube.com/shorts/sV5YikvGX5I | 예약(Studio). 개드립 729530519. #축의금 식대 논란. 버전3 |
| 2026-10-18 12:00 | `phish010` | https://youtube.com/shorts/rl8wjNBPydU | 예약(Studio). 개드립 729549371. #010피싱 징역10년 |
| 2026-10-18 13:00 | `goraebap` | https://youtube.com/shorts/wLeXg_skPpE | 예약(Studio). 개드립 729579756. #고래밥 절도 입건 |
| 2026-10-18 14:00 | `elevdog` | https://youtube.com/shorts/yd3g06Ol590 | 예약(Studio). 개드립 729629644. #개물림 견주 처벌 |
| 2026-10-18 19:00 | `leaseword` | https://youtube.com/shorts/gCD9GVcvV_k | 예약(Studio). 동아일보 2026-10-16 [집과법]. #실거주 구두약속 패소. 버전1, 대화 15% 기준편, 미자 목소리 |
| 2026-10-18 20:00 | `ambuyield` | https://youtube.com/shorts/gPsKy5b4c4w | 예약(Studio). 개드립 729552642. #구급차 양보 의무 |
| 2026-10-18 21:00 | `rentcredit` | https://youtube.com/shorts/MQaP6RIIXdI | 예약(Studio). 각색(조특법 95조의2). #월세공제 집주인동의 |
| 2026-10-19 12:00 | `lastpay14` | https://youtube.com/shorts/joQV6NacPL0 | 예약(Studio). 각색(근기법 36조). #퇴사월급 14일 지급 |
| 2026-10-19 13:00 | `hiddenins` | https://youtube.com/shorts/SMuVV4sADv0 | 예약(Studio). 각색(금융위 2026-07-08). #숨은보험금 10조 |
| 2026-10-19 14:00 | `taxback5` | https://youtube.com/shorts/hDa1YccczPU | 예약(Studio). 각색(소득세법 50조). #부양가족공제 5년환급 |
| 2026-10-19 19:00 | `realrent` | https://youtube.com/shorts/3uI6LmZVHrY | 예약(Studio). 개드립 729631420. #실거주 거절 후 전세 |
| 2026-10-19 20:00 | `carrent35` | https://youtube.com/shorts/quAR_xJJ9C8 | 예약(Studio). 각색(자보 표준약관 대차료). #렌트비 35% 현금 |

> **2026-10-18 함정**: 새벽에 Chrome 창이 가려져 있으면(visibilityState hidden) 예약 달력이 안 그려져 날짜 칸이 0개로 잡힌다. `chrome_screenshot` 을 한 번 호출하면(120초 타임아웃이 나도) 그 사이 렌더돼 pick() 이 된다. 기본값(내일)인 날짜는 달력을 열 필요가 없다. `#done-button` 뒤 확인 문구가 안 뜨고 버튼이 aria-disabled 로 멈출 때가 있는데, 콘텐츠 목록에서 "예약됨"이면 저장된 것이다(taxback5, carrent35).
| 2026-10-19 21:00 | `brandflip` | https://youtube.com/shorts/aZdkWluRhbs | 예약(Studio). 룩스 카드뉴스 → 브랜드 원본(맥도날드 체코/이케아 대만/하이네켄) 좋아요 TOP3. 실제 이미지(출처 표기)+Tesla 프레임, 1.1배속, sneaky-123 BGM, 하단 label. #테슬라 패러디 TOP3 |
| 2026-10-20 12:00 | `lottowife` | https://youtube.com/shorts/syoUFuxt-cs | 예약(Studio). 파이낸셜뉴스 2009-01-19 서울고법. #로또 18억 횡령. 이미지 いらすとや 카드(ir_card.py) |
| 2026-10-20 13:00 | `lottotax` | https://youtube.com/shorts/fWjz2HMkQQ4 | 예약(Studio). 소득세법 22%/33%, 200만원 비과세. #로또 1등 실수령액 |
| 2026-10-20 14:00 | `lottoscam` | https://youtube.com/shorts/g_5A04fb_SM | 예약(Studio). 한국경제 2025-10-30 인천지법 징역 12년. #로또 번호 사기 |
| 2026-10-20 19:00 | `lottoex` | https://youtube.com/shorts/sebMFA-raWQ | 예약(Studio). 경향신문 2004-07-02 서울가정법원. #로또 51억 이혼소송 |
| 2026-10-20 20:00 | `lottoexpire` | https://youtube.com/shorts/kPzPf_vkB18 | 예약(Studio). 더팩트 2025-02-08 61억 귀속. #로또 61억 증발 |
| 2026-10-21 12:00 | `aaa` | https://youtube.com/shorts/6S5PEukyf-I | 예약(Studio). 개드립 찬반 10편 배치(10/21). #AAA 건전지 발음. 버전1, 타입캐스트, codex 실사, 변경된 콘텐츠 예 |
| 2026-10-21 13:00 | `custard` | https://youtube.com/shorts/5iMDrdK2N6o | 예약(Studio). 개드립 찬반 10편 배치(10/21). #커스타드 잼 실종. 버전1, 타입캐스트, codex 실사, 변경된 콘텐츠 예 |
| 2026-10-21 14:00 | `carworst` | https://youtube.com/shorts/gy7FQ_SqCPQ | 예약(Studio). 개드립 찬반 10편 배치(10/21). #최악 자동차 옵션. 버전1, 타입캐스트, codex 실사, 변경된 콘텐츠 예 |
| 2026-10-21 19:00 | `inlaws` | https://youtube.com/shorts/VkvijwhpN_Q | 예약(Studio). 개드립 찬반 10편 배치(10/21). #장인장모 부부싸움. 버전1, 타입캐스트, codex 실사, 변경된 콘텐츠 예 |
| 2026-10-21 20:00 | `dadcar` | https://youtube.com/shorts/jZqkYqC-v20 | 예약(Studio). 개드립 찬반 10편 배치(10/21). #아빠차 드라이버 선물. 버전1, 타입캐스트, codex 실사, 변경된 콘텐츠 예 |
| 2026-10-21 21:00 | `bancart` | https://youtube.com/shorts/_3DsErEI0zQ | 예약(Studio). 개드립 찬반 10편 배치(10/21). #마트카트 반출 절도?. 버전1, 타입캐스트, codex 실사, 변경된 콘텐츠 예 |
| 2026-10-22 12:00 | `ktxpizza` | https://youtube.com/shorts/8y8pRQxjR5Q | 예약(Studio). 개드립 찬반 10편 배치(10/21). #KTX 피자 민폐. 버전1, 타입캐스트, codex 실사, 변경된 콘텐츠 예 |
| 2026-10-22 13:00 | `sciencehs` | https://youtube.com/shorts/pNMMPxvOl9s | 예약(Studio). 개드립 찬반 10편 배치(10/21). #과학고 의대 환수. 버전1, 타입캐스트, codex 실사, 변경된 콘텐츠 예 |
| 2026-10-22 19:00 | `doyoung` | https://youtube.com/shorts/PGwXxlUmeM8 | 예약(Studio). 개드립 찬반 10편 배치(10/21). #김도영 모르면 광주. 버전1, 타입캐스트, codex 실사, 변경된 콘텐츠 예 |
| 2026-10-22 20:00 | `momtrip` | https://youtube.com/shorts/8uJOwYoWnws | 예약(Studio). 개드립 찬반 10편 배치(10/21). #엄마 유언 동생여행. 버전1, 타입캐스트, codex 실사, 변경된 콘텐츠 예 |
| 2026-10-24 00:15 | `kiosk` | https://youtube.com/shorts/lt0E--fM6MY | 예약(Studio). 개드립 긴급 10편 배치(10/23 밤, 15분 간격). #키오스크 먹튀 수법. 버전1, 타입캐스트, codex 실사 |
| 2026-10-24 00:30 (00:24 수동 공개) | `mcseoul` | https://youtube.com/shorts/Mx50d-dnn6Q | 예약(Studio). 개드립 긴급 10편 배치(10/23 밤, 15분 간격). #서울역 맥도날드 에이스. 버전1, 타입캐스트, codex 실사 |
| 2026-10-24 00:45 (00:35 수동 공개) | `fire11` | https://youtube.com/shorts/R4rRd3tk6Rg | 예약(Studio). 개드립 긴급 10편 배치(10/23 밤, 15분 간격). #파이어족 11억 근황. 버전1, 타입캐스트, codex 실사 |
| 2026-10-24 01:00 (00:45 수동 공개) | `agmil` | https://youtube.com/shorts/of6G5Tg6zSw | 예약(Studio). 개드립 긴급 10편 배치(10/23 밤, 15분 간격). #아시안게임 군면제 폐지. 버전1, 타입캐스트, codex 실사 |
| 2026-10-24 01:15 (00:55 수동 공개) | `ktxrock` | https://youtube.com/shorts/ibNgC7oicdA | 예약(Studio). 개드립 긴급 10편 배치(10/23 밤, 15분 간격). #KTX 선로 돌덩이 처벌. 버전1, 타입캐스트, codex 실사 |
| 2026-10-24 01:30 (01:05 수동 공개) | `cuoven` | https://youtube.com/shorts/5_oskmpWLsE | 예약(Studio). 개드립 긴급 10편 배치(10/23 밤, 15분 간격). #CU 바코드 오븐 도입. 버전1, 타입캐스트, codex 실사 |
| 2026-10-24 01:45 (01:15 수동 공개) | `jeonse` | https://youtube.com/shorts/DS7Zo_IOy5w | 예약(Studio). 개드립 긴급 10편 배치(10/23 밤, 15분 간격). #전세 외국인 반응. 버전1, 타입캐스트, codex 실사 |
| 2026-10-24 02:00 (01:44 수동 공개, 01:25 틱 놓침) | `aitrap` | https://youtube.com/shorts/HTcPzTjktLU | 예약(Studio). 개드립 긴급 10편 배치(10/23 밤, 15분 간격). #AI 함정 과제 교사. 버전1, 타입캐스트, codex 실사 |
| 2026-10-24 02:15 (02:06 수동 공개, 01:35 틱 놓침) | `sejong` | https://youtube.com/shorts/hy8NrM1WjgU | 예약(Studio). 개드립 긴급 10편 배치(10/23 밤, 15분 간격). #공무원 세종 7천명. 버전1, 타입캐스트, codex 실사 |
| 2026-10-24 02:30 (02:16 수동 공개) | `colason` | https://youtube.com/shorts/yEdvXuUqBlk | 예약(Studio). 개드립 긴급 10편 배치(10/23 밤, 15분 간격). #응급실 검은물 아들. 버전1, 타입캐스트, codex 실사. img02 아이 구토 프롬프트가 OpenAI 모더레이션에 막혀 욕실 공간컷으로 교체 |

> **2026-10-23 밤 함정**: ① 시간 드롭다운은 셀렉터 클릭 1회로 안 열린다. `input[type="file"]` 같은 없는 셀렉터를 일부러 클릭(실패 스크린샷→리페인트)한 뒤 다시 시간칸을 클릭하면 'covered' 로 실패하는데 그게 열린 상태라 바로 pick 하면 된다. ② 자정을 넘기면 날짜 기본값이 모레로 밀리니 `#datepicker-trigger` 열고 pick('2026년 10월', N) 으로 고친다. ③ 스튜디오 예약은 15분 단위라 10분 간격 요청은 15분 간격으로 잡았다.
> **2026-10-24 00:12 검증**: 편집 화면 공개 상태 다이얼로그의 시간 칸에 `오전 12:25` 를 키보드/네이티브 setter 로 넣으면 화면값은 바뀌지만 페이지 저장 버튼이 활성화되지 않고(변경 미인식) 새로고침하면 12:30 으로 돌아온다. **15분 단위 외 시각은 예약으로 못 잡는다.** 10분 간격이 필요하면 세션 크론(CronCreate 일회성)으로 10분마다 편집 화면 → 공개 상태 카드 → 첫 `#visibility-title` 헤더 `.click()`(JS) → `PUBLIC` 라디오 `.click()` → 다이얼로그 `#save-button` → 페이지 `#save` 순으로 수동 공개한다. 원래 15분 예약은 폴백으로 남겨둔다.
| 2026-10-26 11:10 | `motelblackmail` | https://youtube.com/shorts/Il11-t-EmL8 | 12:00 예약 → 사용자 지시로 11:10 즉시 공개. 고정 댓글 등록+고정 완료. 개드립 731229921+731251656 + 형법 350조 공갈. #불륜폭로 돈 요구하면 공갈죄. 버전1, 타입캐스트, codex 실사, 38.2초 | ※ 10:5x 실사 캡처(기사 사진/입장문/댓글) 버전 Il11-t-EmL8 로 재예약, 초판 DoInkCOcIV8 비공개 전환
| 2026-10-26 11:15 | `tilefloat` | https://youtube.com/shorts/tkozI-ZvnwQ | 12:30 예약 → 사용자 지시로 11:15 즉시 공개. 고정 댓글 등록+고정 완료. 유튜브 레퍼런스(평양냉면 EjFmXOYBIo0) + 하자판정기준 18조 80%. #떠붙임 타일 80% 안 차면 하자. 버전1, 타입캐스트, codex 실사, 39.3초 |
| 2026-10-26 13:05 | `cardtrace` | https://youtube.com/shorts/XyfSjIsMwsM | Studio 즉시 공개(Zernio 유튜브 미연결). 고정 댓글 등록+고정 완료. JTBC 사건반장 쇼츠 ZbXhvWjmVOs + 머니투데이, 여신전문금융업법 70조, 방송 캡처 6장 |
| 2026-10-28 12:00 | leavebank | https://youtube.com/shorts/WRQ_HqrpxHQ | 예약. 10/28 하루 10편 첫 배치(daily/). 고정 댓글은 공개 후 |
| 2026-10-28 12:30 | cvspee | https://youtube.com/shorts/lgxvY8Hcx4Q | 예약. 고정 댓글은 공개 후 |
| 2026-10-28 13:00 | dental23 | https://youtube.com/shorts/El25LF8yWgo | 예약. 고정 댓글은 공개 후 |
| 2026-10-28 13:30 | singerfee | https://youtube.com/shorts/CCCMLORa7ow | 예약. 고정 댓글은 공개 후 |
| 2026-10-28 14:00 | roadblock | https://youtube.com/shorts/V4oAjOkMMS4 | 예약. 고정 댓글은 공개 후 |
| 2026-10-28 18:00 | pension40 | https://youtube.com/shorts/uWfQ6R6IGls | 예약. 2021년 사건 재탕(대본·설명에 명시). 고정 댓글은 공개 후 |
| 2026-10-28 18:30 | loan20 | https://youtube.com/shorts/oAsJB4FnkLA | 예약. 40초 초과로 4문장 삭제 후 재빌드. 고정 댓글은 공개 후 |
| 2026-10-28 19:00 | bikegap | https://youtube.com/shorts/g3ywORGGrCg | 예약. 고정 댓글은 공개 후 |
| 2026-10-28 19:30 | pocket60 | https://youtube.com/shorts/XiU_kz2hAo4 | 예약. 대사 "..." 줄이 타입캐스트 422 → "음..."으로 수정. 고정 댓글은 공개 후 |
| 2026-10-28 20:00 | aegibong | https://youtube.com/shorts/WcM38hpGFOw | 예약. 고정 댓글은 공개 후 |
| 2026-10-29 12:00 | judge8 | https://youtube.com/shorts/crhJJhjahds | 예약. 10/29 daily10 자동 제작. 형사소송법 368조. 고정 댓글은 공개 후 |
| 2026-10-29 12:30 | newbiemom | https://youtube.com/shorts/AUG-TVhLzA0 | 예약. 10/29 daily10 자동 제작. 개드립형. 고정 댓글은 공개 후 |
| 2026-10-29 13:00 | suseup | https://youtube.com/shorts/we_OWgxaGGQ | 예약. 10/29 daily10 자동 제작. F형 각색, 최저임금법 5조 2항. 고정 댓글은 공개 후 |
| 2026-10-29 13:30 | monshell | https://youtube.com/shorts/v4zO5zDE2Hk | 예약. 10/29 daily10 자동 제작. 개드립형. 고정 댓글은 공개 후 |
| 2026-10-29 14:00 | car20 | https://youtube.com/shorts/OXhQb0cY2CU | 예약. 10/29 daily10 자동 제작. 상증법 53조. 고정 댓글은 공개 후 |
| 2026-10-29 18:00 | clubbreak | https://youtube.com/shorts/KFzosffd4jo | 예약. 10/29 daily10 자동 제작. 민법 803, 804, 806조. 고정 댓글은 공개 후 |
| 2026-10-29 18:30 | samsung90 | https://youtube.com/shorts/DJi9ZHYXpNo | 예약. 10/29 daily10 자동 제작. 개드립형. 고정 댓글은 공개 후 |
| 2026-10-29 19:00 | daeri | https://youtube.com/shorts/Jdn81u_ihF4 | 예약. 10/29 daily10 자동 제작. 근로기준법 23조. 고정 댓글은 공개 후 |
| 2026-10-29 19:30 | funeral | https://youtube.com/shorts/jPlcWpxeOl4 | 예약. 10/29 daily10 자동 제작. 개드립형. 고정 댓글은 공개 후 |
| 2026-10-29 20:00 | dealgyo | https://youtube.com/shorts/U031mtT3oH0 | 예약. 10/29 daily10 자동 제작. 개드립형. 고정 댓글은 공개 후 |
| 2026-10-30 12:00 | allergy | https://youtube.com/shorts/Qrz_Zzsj5PI | 예약. 10/30 daily10 자동 제작(누구 책임 판결형). 수원지법 2014가합62810, 어린이식생활법 11조의2. 고정 댓글은 공개 후 |
| 2026-10-30 12:30 | gymfall | https://youtube.com/shorts/GO8LQ-2Swug | 예약. 10/30 daily10 자동 제작(누구 책임 판결형). 민법 758조, 인천지법. 고정 댓글은 공개 후 |
| 2026-10-30 13:00 | hairburn | https://youtube.com/shorts/bQnw5hGORCA | 예약. 10/30 daily10 자동 제작(누구 책임 판결형). 소비자분쟁해결기준 미용업, 소비자원 결정. 고정 댓글은 공개 후 |
| 2026-10-30 13:30 | cprsue | https://youtube.com/shorts/rKmy2Yfd448 | 예약. 10/30 daily10 자동 제작(누구 책임 판결형). 응급의료법 5조의2. 고정 댓글은 공개 후 |
| 2026-10-30 14:00 | selfpay | https://youtube.com/shorts/bnj-JVkNzzY | 예약. 10/30 daily10 자동 제작(누구 책임 판결형). 형법 329조, 수원지법 무죄. 고정 댓글은 공개 후 |
| 2026-10-30 18:00 | meatsmell | https://youtube.com/shorts/fJwd-QQD96o | 예약. 10/30 daily10 자동 제작(누구 책임 판결형). 민법 217조. 고정 댓글은 공개 후 |
| 2026-10-30 18:30 | tenantdie | https://youtube.com/shorts/5R0u3-GXh9Q | 예약. 10/30 daily10 자동 제작(누구 책임 판결형). 주택임대차보호법 9조, 민법 1005조. 고정 댓글은 공개 후 |
| 2026-10-30 19:00 | lottoshare | https://youtube.com/shorts/HeAJWeabYa8 | 예약. 10/30 daily10 자동 제작(누구 책임 판결형). 수원지법 성남지원 분배약정. 고정 댓글은 공개 후 |
| 2026-10-30 19:30 | textfire | https://youtube.com/shorts/kTqNIM7CvQk | 예약. 10/30 daily10 자동 제작(누구 책임 판결형). 근로기준법 27조, 서울행정법원. 고정 댓글은 공개 후 |
| 2026-10-30 20:00 | surgerymed | https://youtube.com/shorts/MoOnS6KOtYY | 예약. 10/30 daily10 자동 제작(누구 책임 판결형). 의료분쟁조정법 27조, 서울중앙지법 설명의무. 고정 댓글은 공개 후 |
| 2026-10-31 12:00 | sunroof | https://youtube.com/shorts/4UdywHvHvqI | 예약. 10/31 daily10 자동 제작. 도로교통법 39조 3항, 50조 1항, 156조. 고정 댓글은 공개 후 |
| 2026-10-31 13:00 | schoolred | https://youtube.com/shorts/Afol1UkLh64 | 예약. 10/31 daily10 자동 제작. 도로교통법 12조, 특가법 5조의13. 고정 댓글은 공개 후 |
| 2026-10-31 14:00 | kibosu | https://youtube.com/shorts/9gk_vQ3wk7Y | 예약. 10/31 daily10 자동 제작. 국민기초생활보장법 생계급여(복지로 2026 선정기준). 고정 댓글은 공개 후 |
| 2026-10-31 12:30 | buffetegg | https://youtube.com/shorts/5lEgDP5tv9M | 예약. 10/31 daily10 자동 제작. 찬반, 법령 없음. 고정 댓글은 공개 후 |
| 2026-10-31 13:30 | grandcall | https://youtube.com/shorts/Yxteo_QeBh0 | 예약. 10/31 daily10 자동 제작. 썰, 법령 없음. 고정 댓글은 공개 후 |
| 2026-10-31 18:00 | copcos | https://youtube.com/shorts/GGsHgTL0z94 | 예약. 10/31 daily10 자동 제작. 경찰제복장비법 9조, 12조. 고정 댓글은 공개 후 |
| 2026-10-31 18:30 | noweding | https://youtube.com/shorts/SiNGC2yPyXk | 예약. 10/31 daily10 자동 제작. 찬반, 법령 없음. 고정 댓글은 공개 후 |
| 2026-10-31 19:00 | parkdrink | https://youtube.com/shorts/ZOmWRtSXaxc | 예약. 10/31 daily10 자동 제작. 자연공원법 27조, 86조. 고정 댓글은 공개 후 |
| 2026-10-31 19:30 | hero14 | https://youtube.com/shorts/jqdsVMWWT4Y | 예약. 10/31 daily10 자동 제작. 훈훈, 법령 없음. 고정 댓글은 공개 후 |
| 2026-10-31 20:00 | vapewife | https://youtube.com/shorts/eeJJA-DTpyE | 예약. 10/31 daily10 자동 제작. 찬반, 법령 없음. 고정 댓글은 공개 후 |
| 2026-11-01 12:00 | bedframe | https://youtube.com/shorts/uJO_PU6XTzo | 예약. 11/1 daily10 자동 제작. 제조물책임법 3조, 3조의2. 고정 댓글은 공개 후 |
| 2026-11-01 18:00 | barefoot | https://youtube.com/shorts/NZVC0Jyv8-I | 예약. 11/1 daily10 자동 제작. 도로교통법 148조, 특가법 5조의11. 고정 댓글은 공개 후 |
| 2026-11-01 12:30 | kittenname | https://youtube.com/shorts/1kdDQi9IaPc | 예약. 11/1 daily10 자동 제작. 개드립 참여형, 법령 없음. 고정 댓글은 공개 후 |
| 2026-11-01 13:00 | tljcream | https://youtube.com/shorts/D3OPbQulzss | 예약. 11/1 daily10 자동 제작. 소비자분쟁해결기준 식료품 함량, 용량부족. 고정 댓글은 공개 후 |
| 2026-11-01 13:30 | burgertier | https://youtube.com/shorts/gi9W9-g8uEQ | 예약. 11/1 daily10 자동 제작. 개드립 찬반, 법령 없음. 고정 댓글은 공개 후 |
| 2026-11-01 14:00 | nicu | https://youtube.com/shorts/bG0FZFYMTAA | 예약. 11/1 daily10 자동 제작. 국민건강보험법 44조 2항. 고정 댓글은 공개 후 |
| 2026-11-01 18:30 | ewhaglass | https://youtube.com/shorts/xbXlNbiwH5c | 예약. 11/1 daily10 자동 제작. 개드립 찬반, 법령 없음. 고정 댓글은 공개 후 |
| 2026-11-01 19:00 | leafburn | https://youtube.com/shorts/lW6YKSzNCzY | 예약. 11/1 daily10 자동 제작. 폐기물관리법 8조 2항, 68조 3항 1호. 고정 댓글은 공개 후 |
| 2026-11-01 19:30 | acorn | https://youtube.com/shorts/pKlFBnnM5nU | 예약. 11/1 daily10 자동 제작. 자연공원법 23조 1항 7호, 82조 2호. 고정 댓글은 공개 후 |
| 2026-11-01 20:00 | yearparty | https://youtube.com/shorts/cJu0u6oD0tc | 예약. 11/1 daily10 자동 제작. 근로기준법 76조의2, 76조의3, 116조. 고정 댓글은 공개 후 |
| 2026-11-02 12:00 | lostwallet | https://youtube.com/shorts/1n2iPhl8QDU | 예약. 11/2 daily10 자동 제작. 유실물법 4조, 형법 360조. 고정 댓글은 공개 후 |
| 2026-11-02 12:30 | cutline | https://youtube.com/shorts/Bsf_1uOF8K4 | 예약. 11/2 daily10 자동 제작. 경범죄처벌법 3조 1항 36호. 고정 댓글은 공개 후 |
| 2026-11-02 13:00 | fluwife | https://youtube.com/shorts/l2q1CswDhhc | 예약. 11/2 daily10 자동 제작. 민법 840조. 고정 댓글은 공개 후 |
| 2026-11-02 13:30 | snowfront | https://youtube.com/shorts/S9Yrzle37f8 | 예약. 11/2 daily10 자동 제작. 자연재해대책법 27조. 고정 댓글은 공개 후 |
| 2026-11-02 18:00 | butts | https://youtube.com/shorts/XPnuBc2e9-A | 예약. 11/2 daily10 자동 제작. 경범죄처벌법 3조 1항 11호. 고정 댓글은 공개 후 |
| 2026-11-02 14:00 | chef01 | https://youtube.com/shorts/7espzm5IjI0 | 예약. 11/2 daily10 자동 제작. 법령 없음(개드립 찬반). 고정 댓글은 공개 후 |
| 2026-11-02 18:30 | kidbeef | https://youtube.com/shorts/vZO-OprAXRU | 예약. 11/2 daily10 자동 제작. 법령 없음(개드립 찬반). 고정 댓글은 공개 후 |
| 2026-11-02 19:00 | bankquit | https://youtube.com/shorts/fOAI0RNN2KA | 예약. 11/2 daily10 자동 제작. 법령 없음(개드립 찬반). 고정 댓글은 공개 후 |
| 2026-11-02 19:30 | gukbap | https://youtube.com/shorts/wc4ExYpHX7Y | 예약. 11/2 daily10 자동 제작. 법령 없음(개드립 찬반). 고정 댓글은 공개 후 |
| 2026-11-02 20:00 | star5 | https://youtube.com/shorts/XNUw8SOOVVw | 예약. 11/2 daily10 자동 제작. 법령 없음(개드립 훈훈). 고정 댓글은 공개 후 |
| 2026-11-03 12:00 | latefine | https://youtube.com/shorts/kN5x2mdwPOY | 예약. 11/3 daily10 자동 제작. 근로기준법 43조, 20조. 고정 댓글은 공개 후 |
| 2026-11-03 18:00 | nightpay | https://youtube.com/shorts/zu3vKstKyVE | 예약. 11/3 daily10 자동 제작. 근로기준법 56조 3항. 고정 댓글은 공개 후 |
| 2026-11-03 12:30 | pigeon | https://youtube.com/shorts/XcBl1XxqE6w | 예약. 11/3 daily10 자동 제작. 야생생물법 23조의3, 73조. 고정 댓글은 공개 후 |
| 2026-11-03 13:00 | periodleave | https://youtube.com/shorts/86jALBKEmXc | 예약. 11/3 daily10 자동 제작. 근로기준법 73조. 고정 댓글은 공개 후 |
| 2026-11-03 13:30 | cashreceipt | https://youtube.com/shorts/l63TGszncDg | 예약. 11/3 daily10 자동 제작. 소득세법 162조의3, 81조의9. 고정 댓글은 공개 후 |
| 2026-11-03 14:00 | drunkloud | https://youtube.com/shorts/OXQxfnKvTIA | 예약. 11/3 daily10 자동 제작. 경범죄처벌법 3조 1항 20호. 고정 댓글은 공개 후 |
| 2026-11-03 18:30 | duocandy | https://youtube.com/shorts/Y9JA2J0j-Ak | 예약. 11/3 daily10 자동 제작. 경범죄처벌법 3조 3항 2호, 정보통신망법 70조 2항. 고정 댓글은 공개 후 |
| 2026-11-03 19:00 | chinanoodle | https://youtube.com/shorts/CeOxIvnwoAk | 예약. 11/3 daily10 자동 제작. 법령 없음(개드립 찬반). 고정 댓글은 공개 후 |
| 2026-11-03 19:30 | tonkatsu | https://youtube.com/shorts/T23JxPTLwOs | 예약. 11/3 daily10 자동 제작. 개드립 반응형, 법령 없음. 고정 댓글은 공개 후 |
| 2026-11-03 20:00 | nursenum | https://youtube.com/shorts/VDm5I3J8EuU | 예약. 11/3 daily10 자동 제작. 개드립 반응형, 법령 없음. 고정 댓글은 공개 후 |
| 2026-11-04 09:00 | mobileid | https://youtube.com/shorts/MO_l9naLTh0 | 예약. 11/3 밤 수동 지시 6편(30분 간격) 제작. 전자정부법 76조 3항, 식품위생법 75조. 고정 댓글은 공개 후 |
| 2026-11-04 09:30 | drive13 | https://youtube.com/shorts/E_GXCM0hlkY | 예약. 11/3 밤 수동 지시 6편(30분 간격) 제작. 도로교통법 13조 3항, 19조 3항. 고정 댓글은 공개 후 |
| 2026-11-04 10:00 | carstop | https://youtube.com/shorts/rqHk0NHSavU | 예약. 11/3 밤 수동 지시 6편(30분 간격) 제작. 도로교통법 32조. 고정 댓글은 공개 후 |
| 2026-11-04 10:30 | coupangrev | https://youtube.com/shorts/vZg10zhV9zY | 예약. 11/3 밤 수동 지시 6편(30분 간격) 제작. 표시광고법 3조, 17조, 추천보증 심사지침. 고정 댓글은 공개 후 |
| 2026-11-04 11:00 | interview | https://youtube.com/shorts/GqkVxu4z_Uo | 예약. 11/3 밤 수동 지시 6편(30분 간격) 제작. 법령 없음(찬반). 고정 댓글은 공개 후 |
| 2026-11-04 11:30 | boss43 | https://youtube.com/shorts/cvPPAxrZ4BQ | 예약. 11/3 밤 수동 지시 6편(30분 간격) 제작. 법령 없음(찬반). 고정 댓글은 공개 후 |
| 2026-11-04 12:00 | daiso63 | https://youtube.com/shorts/-0Umy0RLCAc | 예약. 11/4 daily10 자동 제작. 형법 13조, 329조. 고정 댓글은 공개 후 |
| 2026-11-04 12:30 | pregwork | https://youtube.com/shorts/TzMFR-prdYg | 예약. 11/4 daily10 자동 제작. 법령 없음(찬반). 고정 댓글은 공개 후 |
| 2026-11-04 13:00 | eatdebt | https://youtube.com/shorts/K3EHGJEK9Tw | 예약. 11/4 daily10 자동 제작. 민법 164조, 168조, 178조. 고정 댓글은 공개 후 |
| 2026-11-04 13:30 | ocean400 | https://youtube.com/shorts/ySXJcl3BdIg | 예약. 11/4 daily10 자동 제작. 법령 없음(반응형). 고정 댓글은 공개 후 |
| 2026-11-04 14:00 | laptopkeep | https://youtube.com/shorts/6a-C8sPA0h0 | 예약. 11/4 daily10 자동 제작. 형법 355조 1항, 356조. 고정 댓글은 공개 후 |
| 2026-11-04 18:00 | wageadvance | https://youtube.com/shorts/H_dJuzNx4i0 | 예약. 11/4 daily10 자동 제작. 근로기준법 45조, 113조, 시행령 25조. 고정 댓글은 공개 후 |
| 2026-11-04 18:30 | carbuy | https://youtube.com/shorts/bmNLwIXq1Es | 예약. 11/4 daily10 자동 제작. 법령 없음(찬반). 고정 댓글은 공개 후 |
| 2026-11-04 19:00 | forcesave | https://youtube.com/shorts/cG8lEv5KX3o | 예약. 11/4 daily10 자동 제작. 근로기준법 22조 1항, 110조. 고정 댓글은 공개 후 |
| 2026-11-04 19:30 | beans | https://youtube.com/shorts/A2arFikSJ8w | 예약. 11/4 daily10 자동 제작. 수입식품안전관리 특별법 25조(적용 여부 확인 안 됨). 고정 댓글은 공개 후 |
| 2026-11-04 20:00 | tossdel | https://youtube.com/shorts/sGfJ9lYoCYg | 예약. 11/4 daily10 자동 제작. 법령 없음(반응형). 고정 댓글은 공개 후 |
| 2026-11-05 12:00 | taxpeek | https://youtube.com/shorts/h8F27LRP41g | 예약. daily10 자동 제작. 국세기본법 81조의13, 90조. 고정 댓글은 공개 후 |
| 2026-11-05 12:30 | hometown | https://youtube.com/shorts/8QnVtoUZOKQ | 예약. daily10 자동 제작. 법령 없음(찬반). 고정 댓글은 공개 후 |
| 2026-11-05 13:00 | parcelthief | https://youtube.com/shorts/IvlWA3rBV8Q | 예약. daily10 자동 제작. 형법 329조, 366조. 고정 댓글은 공개 후 |
| 2026-11-05 13:30 | kozel | https://youtube.com/shorts/4NMMcX7MF18 | 예약. daily10 자동 제작. 법령 없음(뉴스1 보도). 고정 댓글은 공개 후 |
| 2026-11-05 14:00 | wall50 | https://youtube.com/shorts/gH1EMjGoLmA | 예약. daily10 자동 제작. 민법 242조, 243조. 고정 댓글은 공개 후 |
| 2026-11-05 18:00 | undercity | https://youtube.com/shorts/xttnlPLo5gk | 예약. daily10 자동 제작. 매장유산법 17조, 21조, 31조 6항, 38조. 고정 댓글은 공개 후 |
| 2026-11-05 18:30 | kangaroo | https://youtube.com/shorts/c8155Jh-8Tc | 예약. daily10 자동 제작. 법령 없음(찬반). 고정 댓글은 공개 후 |
| 2026-11-05 19:00 | flyer | https://youtube.com/shorts/EfLLttVjm_0 | 예약. daily10 자동 제작. 경범죄 처벌법 3조 1항 9호. 고정 댓글은 공개 후 |
| 2026-11-05 19:30 | koreaproof | https://youtube.com/shorts/21aHD0KT8G4 | 예약. daily10 자동 제작. 법령 없음(공감). 고정 댓글은 공개 후 |
| 2026-11-05 20:00 | runvr | https://youtube.com/shorts/jcx7iGM5n-A | 예약. daily10 자동 제작. 법령 없음(찬반). 고정 댓글은 공개 후 |
