#!/usr/bin/env python3
"""F형 10편 일괄 생성 — script.json / prompts.tsv / upload.md (2026-09-15)."""
import json, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = ("photorealistic DSLR photograph, 35mm lens, natural available light, shallow depth of field, "
     "Korean setting, no text no letters no signage no logos no brand marks no watermark")
W1 = "a Korean woman in her early 30s, shoulder-length dark brown hair, natural light makeup"
M1 = "a Korean man in his early 30s, short black hair, clean-shaven, slim build"
M2 = "a Korean man in his mid 30s, short wavy black hair, light stubble, sturdy build"
OUTRO = {"text": "구독!", "emotion": "toneup", "intensity": 2.0, "outro": True}

def L(text, img, sfx=None, em=None, yellow=False, dlg=None, emo=None):
    d = {"text": text, "img": img}
    if em: d["em"] = [em];
    if yellow: d["em_color"] = "yellow"
    if sfx: d["sfx"] = sfx
    if dlg: d["dialogue"] = True; d["voice"] = dlg; d["emotion"] = emo or "angry"; d["intensity"] = 2.0
    return d

EP = {}

EP["wedding70"] = dict(
 t1='"예식장 사정이라 어쩔 수 없어요"', t2='결혼 20일 전 취소당한 부부',
 hook='"예식장 사정이라 어쩔 수 없어요" 결혼 20일 전 취소당한 부부', bar='결혼 20일 앞두고 예식장이 취소 통보',
 src='https://www.korea.kr/news/policyNewsView.do?newsId=148956738', tag='#예식장취소',
 lines=[
  L("예식장 사정이라 어쩔 수 없다며 결혼 20일 전에 취소당한 부부가 있었음.",1),
  L("청첩장 300장 다 돌리고 신혼여행까지 끊어놨는데, 예식장에서 전화가 왔음.",2,"whoosh",em="300장"),
  L("그날 더 큰 행사가 잡혀서요. 계약금은 돌려드릴게요!",3,"eng",dlg="sub2"),
  L("저희 사정이라 어쩔 수 없어요. 다른 데 알아보세요?!",3,"dudung",dlg="sub2",emo="happy"),
  L("20일 남기고 새 예식장을 잡는 건 불가능에 가깝고, 하객들한테 다시 연락 돌릴 생각에 눈앞이 깜깜했음.",4,"tick"),
  L("근데 신랑이 화내는 대신 공정위 자료를 찾아봤음.",5,"ding"),
  L("2025년 12월 18일부터 예식장 위약금 기준이 바뀌었음.",6,"pop",em="12월 18일",yellow=True),
  L("소비자가 취소하면 29일 전은 40%, 9일 전은 50%, 당일은 70%인데,",7,"cash"),
  L("예식장 사정으로 취소하면 29일 전부터 총비용의 70%를 예식장이 물어야 함.",7,"siren",em="70%",yellow=True),
  L("총비용 2천만 원짜리 계약이면 1,400만 원임.",8,"cash",em="1,400만 원"),
  L("소비자원 접수하고 개정 기준을 첨부해서 내용증명을 보냈더니",9,"whoosh"),
  L("이틀 뒤 예식장에서 먼저 전화가 와서, 원래 날짜에 원래 홀로 식을 올리게 됐음.",10,"thud",em="원래 홀로"),
  L("아니, 더 큰 행사가 있다니까요!!?",11,"eng",dlg="sub2"),
  L("더 큰 행사보다 1,400만 원이 더 컸던 거임.",11,"boing"),
  L("결혼 준비하는 친구 있으면 이거 보내주셈. 12월 18일 기준임.",12),
  OUTRO],
 prompts=[
  f"A grand empty Korean wedding hall with white flower arch and rows of chairs, chandelier light, {T}",
  f"{W1} and {M1} as a couple at home holding a stack of wedding invitation cards, phone ringing on the table, worried faces, {T}",
  f"{M2} as a wedding hall manager in a suit at a front desk, shrugging with a dismissive smile, {T}",
  f"{W1} sitting at a kitchen table with her head in her hands next to a wedding planner notebook, {T}",
  f"{M1} in a shirt reading a document on a laptop at night with a determined expression, {T}",
  f"Close-up of a red circled date on a desk calendar page with a pen, warm light, {T}",
  f"Close-up of a printed contract with a highlighted clause and a calculator on a desk, {T}",
  f"Stacks of Korean banknotes on a desk next to a wedding ring box, {T}",
  f"Close-up of a hand dropping a white registered-mail envelope into a red Korean post box, {T}",
  f"{W1} in a white wedding dress and {M1} in a tuxedo walking down a wedding hall aisle, guests applauding, {T}",
  f"{M2} as a wedding hall manager in a suit, flustered on the phone, rubbing his forehead, {T}",
  f"Close-up of two hands exchanging wedding rings, soft light, {T}"])

EP["noshow40"] = dict(
 t1='"돈 낸 것도 없는데 뭘 물어요"', t2='30인분 노쇼한 단체 손님',
 hook='"돈 낸 것도 없는데 뭘 물어요" 30인분 노쇼한 단체 손님', bar='30인분 준비했는데 아무도 안 온 날',
 src='https://www.korea.kr/news/policyNewsView.do?newsId=148956738', tag='#노쇼',
 lines=[
  L("돈 낸 것도 없는데 뭘 무냐며 30인분 노쇼한 단체 손님이 있었음.",1),
  L("회식 30명 예약이라 새벽부터 한우 30인분 재워놓고 홀을 통째로 비웠는데, 저녁 7시에 아무도 안 왔음.",2,"whoosh",em="30인분",yellow=True),
  L("전화했더니 아, 취소됐어요. 말씀 못 드렸네요!",3,"eng",dlg="sub2"),
  L("예약금 낸 것도 없는데 뭘 물어요. 알아서 하세요?!",3,"dudung",dlg="sub2",emo="happy"),
  L("그날 재료값이랑 비운 홀 매출 합치면 150만 원이 날아갔음.",4,"tick",em="150만 원"),
  L("근데 이 사장은 예약받을 때 문자 한 통을 보내놨었음.",5,"ding"),
  L("예약보증금이랑 위약금 기준을 문자로 미리 고지한 거임.",6,"pop",em="미리 고지"),
  L("2025년 12월 18일부터 단체 예약은 이렇게 사전 고지만 하면, 노쇼 위약금을 총 이용금액의 40%까지 청구할 수 있음.",7,"siren",em="40%",yellow=True),
  L("30인분 120만 원어치면 48만 원임.",8,"cash",em="48만 원"),
  L("문자 캡처랑 재료 영수증 붙여서 소비자원에 접수했더니",9,"whoosh"),
  L("일주일 만에 48만 원이 입금됐음.",10,"thud",em="48만 원 입금"),
  L("아니, 그냥 예약만 한 건데요!!?",11,"eng",dlg="sub2"),
  L("예약도 계약이라서, 문자 한 통이 48만 원짜리 증거가 된 거임.",11,"boing"),
  L("식당 하는 친구 있으면 이거 보내주셈. 예약 문자부터.",12),
  OUTRO],
 prompts=[
  f"An empty Korean restaurant hall with tables set for a large group, 30 place settings, warm evening light, no people, {T}",
  f"{M2} as a restaurant owner in an apron at dawn marinating a large tray of beef in a kitchen, {T}",
  f"{M1} in a suit at an office desk on the phone with a careless shrug, {T}",
  f"Close-up of a restaurant owner's hand holding a stack of receipts next to a calculator, {T}",
  f"{M2} in an apron looking calmly at his smartphone in the restaurant kitchen, {T}",
  f"Close-up of a smartphone on a wooden counter showing a chat app bubble icon, restaurant background, {T}",
  f"Close-up of a printed official document with a yellow highlighted line on a desk, {T}",
  f"Korean banknotes fanned out on a restaurant counter next to a receipt, {T}",
  f"Close-up of a hand dropping a white envelope into a red Korean post box on a street, {T}",
  f"Close-up of a smartphone in a man's hand showing a big green checkmark icon, bright background, {T}",
  f"{M1} in a suit looking shocked at his phone in an office hallway, {T}",
  f"{M2} in an apron smiling while serving a full table of customers in a busy restaurant, {T}"])

EP["refund7"] = dict(
 t1='"세일 상품은 교환만 돼요"', t2='환불 거부한 쇼핑몰의 결말',
 hook='"세일 상품은 교환만 돼요" 환불 거부한 쇼핑몰의 결말', bar='택배 받고 바로 환불 요청했는데 거부당함',
 src='https://www.easylaw.go.kr/CSP/CnpClsMain.laf?csmSeq=835&ccfNo=4&cciNo=1&cnpClsNo=2', tag='#온라인쇼핑환불',
 lines=[
  L("세일 상품은 교환만 된다며 환불 거부한 쇼핑몰이 있었음.",1),
  L("18만 원짜리 코트를 세일가로 샀는데 받아보니 색이 사진이랑 완전 달라서, 받은 날 바로 환불 요청했음.",2,"whoosh",em="18만 원"),
  L("세일 상품은 환불 불가예요! 상품 페이지에 써 있잖아요?!",3,"eng",dlg="sub1"),
  L("교환은 해드릴게요. 환불은 안 돼요!",3,"dudung",dlg="sub1"),
  L("게시판 보니까 같은 답변을 받은 사람이 수십 명이었음.",4,"tick"),
  L("근데 이건 쇼핑몰이 정할 수 있는 게 아님.",5,"ding"),
  L("전자상거래법 17조. 온라인으로 산 물건은 받은 날부터 7일 안에 이유 없이 청약철회가 됨.",6,"pop",em="7일",yellow=True),
  L("세일이든 아니든 상관없고, 환불 불가라고 써놔도 소용없음.",6,"pop"),
  L("환불 요청 받으면 3영업일 안에 돈을 돌려줘야 하고, 늦으면 연 15% 지연배상금까지 붙음.",7,"cash",em="3영업일"),
  L("법 조문 캡처해서 보내고, 안 되면 공정위 신고하겠다고 했더니",8,"whoosh"),
  L("다음 날 18만 원 전액 환불에 반품 택배비까지 쇼핑몰 부담으로 처리됐음.",9,"thud",em="전액 환불",yellow=True),
  L("아니, 저희 규정이 그런데요!!?",10,"eng",dlg="sub1"),
  L("쇼핑몰 규정 위에 법이 있는 거임.",10,"boing"),
  L("온라인 쇼핑 자주 하는 친구 있으면 이거 보내주셈. 7일임.",11),
  OUTRO],
 prompts=[
  f"Close-up of a woman's hands opening a cardboard delivery box on a bed, a coat inside, {T}",
  f"{W1} holding up a dark coat next to her laptop screen comparing colors, frowning, {T}",
  f"A young Korean woman customer service agent with a headset in a small office, dismissive expression, {T}",
  f"Close-up of a laptop screen showing a long list of comment bubbles, blurred, {T}",
  f"{W1} at a cafe table reading on her laptop with a determined face, {T}",
  f"Close-up of an open law book on a desk with a finger pointing at a line, warm lamp light, {T}",
  f"Close-up of a calculator and Korean banknotes on a desk next to a smartphone, {T}",
  f"Close-up of a woman's hand typing a message on a smartphone, screen glowing, {T}",
  f"Close-up of a smartphone in a woman's hand showing a big green checkmark icon, bright background, {T}",
  f"A young Korean woman customer service agent with a headset looking flustered at her monitor, {T}",
  f"{W1} smiling while carrying a shopping bag on a sunny street, {T}",
  f"Close-up of a cardboard box sealed with tape on a doorstep, {T}"])

EP["hagwon"] = dict(
 t1='"환불은 원래 안 돼요"', t2='학원비 120만 원 떼먹으려던 원장',
 hook='"환불은 원래 안 돼요" 학원비 120만 원 떼먹으려던 원장', bar='3개월치 끊고 일주일 다닌 학원',
 src='https://easylaw.go.kr/CSP/CnpClsMain.laf?popMenu=ov&csmSeq=1140&ccfNo=2&cciNo=3&cnpClsNo=2', tag='#학원비환불',
 lines=[
  L("환불은 원래 안 된다며 학원비 120만 원을 떼먹으려던 원장이 있었음.",1),
  L("3개월치 120만 원을 한 번에 결제하고 일주일 다녔는데, 갑자기 지방 발령이 나서 환불하러 갔음.",2,"whoosh",em="120만 원"),
  L("등록할 때 환불 불가 동의하셨잖아요! 서명 여기 있잖아요?!",3,"eng",dlg="sub2"),
  L("원래 학원은 환불 안 돼요. 남은 건 친구한테 양도하세요!",3,"dudung",dlg="sub2",emo="happy"),
  L("서명한 건 맞아서 그냥 포기하려다가, 학원법을 한번 찾아봤음.",4,"tick"),
  L("학원법 시행령에 환불 비율이 법으로 딱 정해져 있었음.",5,"ding",em="법으로 딱"),
  L("한 달짜리 기준으로, 수업 3분의 1 지나기 전이면 3분의 2를 돌려주고, 절반 전이면 절반을 돌려줌.",6,"pop",em="3분의 2",yellow=True),
  L("그리고 여러 달 끊었으면 아직 시작 안 한 달은 전액 환불임.",6,"cash",em="전액"),
  L("120만 원 중에 첫 달 40만 원은 3분의 2인 26만 원, 나머지 두 달 80만 원은 전액. 합쳐서 106만 원임.",7,"cash",em="106만 원",yellow=True),
  L("환불 불가 서명은 법보다 학생한테 불리해서 효력이 없고, 환불은 5일 안에 해줘야 함.",8,"pop"),
  L("교육청 민원 넣겠다고 했더니 그날 오후에 원장한테 전화가 왔음.",9,"whoosh"),
  L("106만 원 입금 완료.",10,"thud",em="106만 원 입금"),
  L("아니, 서명하셨잖아요!!?",11,"eng",dlg="sub2"),
  L("서명보다 법이 위라는 걸 원장도 알고 있었던 거임.",11,"boing"),
  L("학원 끊고 후회하는 친구 있으면 이거 보내주셈.",12),
  OUTRO],
 prompts=[
  f"Exterior of a Korean private academy building at night with lit classroom windows, {T}",
  f"{M1} in a shirt standing at an academy front desk holding a receipt, polite but troubled face, {T}",
  f"{M2} as an academy director in a cardigan behind a desk pointing at a contract with a smug face, {T}",
  f"{M1} sitting on a bus reading on his smartphone with a thoughtful expression, {T}",
  f"Close-up of an open law book with a finger pointing at a highlighted line, warm light, {T}",
  f"Close-up of a hand writing fractions on a whiteboard with a marker, classroom, {T}",
  f"Korean banknotes stacked on a desk next to a calculator, bright light, {T}",
  f"Close-up of a signed contract on a desk with a red pen crossing out a line, {T}",
  f"{M2} as an academy director looking anxious on the phone in an empty classroom, {T}",
  f"Close-up of a smartphone in a man's hand showing a big green checkmark icon, {T}",
  f"{M2} in a cardigan slumped at his desk rubbing his forehead, classroom behind, {T}",
  f"{M1} smiling while walking with a backpack on a sunny street, {T}"])

EP["carrepair"] = dict(
 t1='"이왕 뜯은 김에 다 갈았어요"', t2='수리비 80만 원 청구한 정비소',
 hook='"이왕 뜯은 김에 다 갈았어요" 수리비 80만 원 청구한 정비소', bar='브레이크 패드만 맡겼는데 80만 원 나옴',
 src='https://easylaw.go.kr/CSP/CnpClsMain.laf?popMenu=ov&csmSeq=675&ccfNo=2&cciNo=3&cnpClsNo=1', tag='#자동차정비',
 lines=[
  L("이왕 뜯은 김에 다 갈았다며 수리비 80만 원을 청구한 정비소가 있었음.",1),
  L("브레이크 패드 교체 12만 원 견적 듣고 차를 맡겼는데, 찾으러 갔더니 청구서가 80만 원이었음.",2,"whoosh",em="80만 원",yellow=True),
  L("디스크도 갈고 오일도 갈고 부싱도 갈았어요! 이왕 뜯은 김에요?!",3,"eng",dlg="sub2",emo="happy"),
  L("차 찾으려면 결제하셔야죠. 안 하면 차 못 드려요!",3,"dudung",dlg="sub2"),
  L("전화 한 통 없었고, 동의한 적도 없는 항목이 68만 원어치였음.",4,"tick",em="68만 원"),
  L("근데 여기서 차주가 카드를 꺼내는 대신 자동차관리법을 꺼냈음.",5,"ding"),
  L("자동차관리법 58조. 정비업자는 정비 전에 견적서를 주고, 의뢰인 동의 없이 임의로 정비하면 안 됨.",6,"pop",em="동의 없이",yellow=True),
  L("어기면 100만 원 이하 과태료에 영업정지까지 갈 수 있음.",6,"siren",em="영업정지"),
  L("견적서 없이 한 정비는 지불할 의무가 없고, 차를 안 주면 그건 별개 문제가 됨.",7,"pop"),
  L("구청 교통과에 신고하겠다고 하고 처음 견적 12만 원만 결제했더니",8,"whoosh"),
  L("사장이 5분 만에 청구서를 다시 뽑아 왔음. 12만 원.",9,"thud",em="12만 원"),
  L("아니, 이미 다 갈았는데요!!?",10,"eng",dlg="sub2"),
  L("동의 없이 간 부품은 정비소가 공부한 값이 된 거임.",10,"boing"),
  L("차 정비 맡길 일 있는 친구한테 이거 보내주셈. 견적서 먼저.",11),
  OUTRO],
 prompts=[
  f"A car lifted on a hoist in a Korean auto repair garage, mechanic's legs visible underneath, {T}",
  f"{M1} in casual clothes at a repair shop counter staring at a long receipt with a shocked face, {T}",
  f"{M2} as a mechanic in grey coveralls with grease on his hands, arms crossed, smug expression, {T}",
  f"Close-up of a long paper invoice with many line items on a counter, blurred, {T}",
  f"{M1} calmly holding up his smartphone at the repair shop counter, {T}",
  f"Close-up of an open law book with a finger on a highlighted line, warm light, {T}",
  f"Close-up of a blank estimate form clipped to a clipboard on a garage counter, {T}",
  f"Close-up of a hand tapping a credit card on a payment terminal at a counter, {T}",
  f"Close-up of a short receipt printing out of a receipt printer, {T}",
  f"{M2} as a mechanic in coveralls looking flustered and scratching his head in the garage, {T}",
  f"{M1} driving his car out of the garage with a small smile, sunny street, {T}",
  f"Close-up of new brake pads and a disc on a workbench, {T}"])

EP["rent5"] = dict(
 t1='"월세 30% 올릴게요, 싫으면 나가세요"', t2='건물주가 조용해진 이유',
 hook='"월세 30% 올릴게요, 싫으면 나가세요" 건물주가 조용해진 이유', bar='장사 잘되니까 월세 200에서 260으로',
 src='https://realestate.ehyun.co.kr/rental-increase-limit-response', tag='#상가임대료',
 lines=[
  L("월세 30% 올릴 테니 싫으면 나가라던 건물주가 조용해진 이유가 있음.",1),
  L("보증금 5천에 월세 200으로 2년 장사해서 자리 잡았는데, 재계약 앞두고 건물주가 찾아왔음.",2,"whoosh",em="월세 200"),
  L("장사 잘되던데, 다음 달부터 260 받을게요!",3,"eng",dlg="sub2",emo="happy"),
  L("싫으면 나가세요. 들어올 사람 많아요?!",3,"dudung",dlg="sub2"),
  L("인테리어에 4천 들였는데 2년 만에 나가면 그게 다 날아가는 거였음.",4,"tick",em="4천"),
  L("근데 이 사장은 계약서 대신 상가임대차보호법을 펼쳤음.",5,"ding"),
  L("11조. 임대료 인상은 한 번에 5%까지만 가능함. 200이면 210이 끝임.",6,"pop",em="5%",yellow=True),
  L("그리고 10조. 세입자가 갱신을 요구하면 건물주는 10년까지 거절할 수 없음.",6,"pop",em="10년",yellow=True),
  L("보증금 5천에 월세 200이면 환산보증금 2억 5천이라 서울 기준 9억 이하, 그대로 적용됨.",7,"cash"),
  L("만기 한 달 전에 갱신 요구를 내용증명으로 보냈더니",8,"whoosh"),
  L("건물주가 210으로 재계약서를 들고 왔음. 나가라던 말은 없었던 일이 됐음.",9,"thud",em="210"),
  L("아니, 내 건물인데요!!?",10,"eng",dlg="sub2"),
  L("건물은 건물주 건데, 인상률은 법이 정하는 거임.",10,"boing"),
  L("상가 세 얻어서 장사하는 친구한테 이거 보내주셈. 5%랑 10년임.",11),
  OUTRO],
 prompts=[
  f"Exterior of a small Korean cafe storefront on a commercial street at dusk, warm light inside, {T}",
  f"{W1} as a cafe owner in an apron wiping a counter in her cozy cafe, {T}",
  f"{M2} as a building owner in a golf shirt standing in the cafe doorway with a smug expression, {T}",
  f"Close-up of a cafe interior with wooden furniture and pendant lights, empty, {T}",
  f"{W1} in an apron sitting at a cafe table reading a law book with a determined face, {T}",
  f"Close-up of a calculator on a counter next to a lease contract, {T}",
  f"Close-up of a hand writing a number on a notepad next to a coffee cup, {T}",
  f"Close-up of a hand dropping a white envelope into a red Korean post box, {T}",
  f"Close-up of two hands signing a contract on a cafe table, coffee cups beside, {T}",
  f"{M2} in a golf shirt looking flustered while holding papers outside the cafe, {T}",
  f"{W1} smiling while handing a coffee to a customer across the counter, {T}",
  f"Wide shot of a busy small cafe with customers at every table, {T}"])

EP["wagedelay"] = dict(
 t1='"월급은 다음 달에 줄게, 고소하든가"', t2='사장이 3배를 물게 된 이유',
 hook='"월급은 다음 달에 줄게, 고소하든가" 사장이 3배를 물게 된 이유', bar='석 달째 월급 안 주는 사장',
 src='https://kbthink.com/business/tips/wage-arrears-prevention-law.html', tag='#임금체불',
 lines=[
  L("월급은 다음 달에 줄 테니 고소하라던 사장이 3배를 물게 된 이유가 있음.",1),
  L("월급 250만 원짜리 직장에서 석 달째 월급이 안 나왔음. 750만 원임.",2,"whoosh",em="750만 원",yellow=True),
  L("요즘 회사 어려운 거 알잖아. 다음 달에 한꺼번에 줄게!",3,"eng",dlg="sub2"),
  L("싫으면 고소하든가. 어차피 벌금 조금 내고 끝이야?!",3,"dudung",dlg="sub2",emo="happy"),
  L("실제로 예전엔 그 말이 반쯤 맞았음. 합의하면 처벌도 안 받았거든.",4,"tick"),
  L("근데 이 직원은 달력을 봤음. 2025년 10월 23일.",5,"ding",em="10월 23일",yellow=True),
  L("그날부터 상습 임금체불 근절법이 시행됐음.",6,"pop"),
  L("고의로 체불하면 법원에 체불액의 최대 3배까지 손해배상을 청구할 수 있고, 재직 중이어도 연 20% 지연이자가 붙음.",6,"siren",em="3배",yellow=True),
  L("750만 원이면 최대 2,250만 원임.",7,"cash",em="2,250만 원"),
  L("노동청에 진정 넣고 3배 배상 청구하겠다고 문자를 보냈더니",8,"whoosh"),
  L("다음 날 아침 750만 원이 전액 입금됐음.",9,"thud",em="전액 입금"),
  L("아니, 다음 달에 준다고 했잖아!!?",10,"eng",dlg="sub2"),
  L("다음 달이 2,250만 원짜리라는 걸 사장도 계산한 거임.",10,"boing"),
  L("월급 밀리는 친구 있으면 이거 보내주셈. 10월 23일부터임.",11),
  OUTRO],
 prompts=[
  f"{M1} in a shirt staring at an empty bank balance on his smartphone at an office desk, {T}",
  f"Close-up of a desk calendar with three months crossed out in red marker, {T}",
  f"{M2} as a company boss in a suit leaning back in an office chair with a dismissive wave, {T}",
  f"{M1} in a shirt sitting on a park bench at night looking exhausted, {T}",
  f"{M1} at his desk looking calmly at a wall calendar, {T}",
  f"Close-up of an open law book with a finger pointing at a highlighted line, {T}",
  f"Korean banknotes stacked high on a desk next to a calculator, {T}",
  f"Close-up of a man's hand typing a message on a smartphone, screen glowing, {T}",
  f"Close-up of a smartphone showing a big green checkmark icon in a man's hand, {T}",
  f"{M2} as a boss in a suit pacing anxiously on the phone in a glass office, {T}",
  f"{M1} in a shirt walking out of an office building with a relieved smile, {T}",
  f"Exterior of a Korean government labor office building entrance, daytime, {T}"])

EP["evcharge"] = dict(
 t1='"5분만 대는 건데 왜요"', t2='충전구역 알박기 차주의 결말',
 hook='"5분만 대는 건데 왜요" 충전구역 알박기 차주의 결말', bar='전기차 충전구역에 매일 세워두는 옆집 차',
 src='https://www.seosan.go.kr/www/contents.do?key=9213', tag='#전기차충전구역',
 lines=[
  L("5분만 대는 건데 왜 그러냐던 충전구역 알박기 차주가 있었음.",1),
  L("아파트 충전기가 두 대뿐인데 한 자리를 휘발유 차가 매일 밤 차지하고 있었음.",2,"whoosh",em="휘발유 차"),
  L("잠깐 대는 건데 왜요? 자리 없어서 그래요!",3,"eng",dlg="sub1"),
  L("전기차라고 유세 떠세요? 신고하든가요?!",3,"dudung",dlg="sub1",emo="happy"),
  L("충전을 못 해서 새벽에 회사 근처 충전소까지 돌아다닌 게 2주였음.",4,"tick",em="2주"),
  L("여기서 전기차 차주가 말싸움 대신 안전신문고 앱을 켰음.",5,"ding",em="안전신문고"),
  L("친환경자동차법. 충전구역에 일반 차를 세우면 과태료 10만 원임.",6,"pop",em="10만 원",yellow=True),
  L("전기차라도 충전 끝나고 완속은 14시간, 급속은 1시간 넘게 세워두면 똑같이 10만 원임.",6,"pop"),
  L("앱에서 사진 두 장 찍어 올리면 촬영 시각이 자동으로 박혀서, 구청이 그걸로 과태료를 매김.",7,"siren"),
  L("매일 밤 두 장씩 일주일 찍어 올렸더니",8,"whoosh"),
  L("옆집 우편함에 과태료 고지서가 일곱 장 꽂혔음. 70만 원임.",9,"thud",em="70만 원",yellow=True),
  L("아니, 5분이라니까요!!?",10,"eng",dlg="sub1"),
  L("5분이 아니라 사진 시각이 증거였던 거임.",10,"boing"),
  L("충전구역 막히는 아파트 사는 친구한테 이거 보내주셈.",11),
  OUTRO],
 prompts=[
  f"A gasoline sedan parked in a green-painted electric vehicle charging bay in an underground apartment garage at night, charger beside it, {T}",
  f"Close-up of an electric vehicle charging station with two ports in an underground garage, one blocked by a sedan, {T}",
  f"{W1} standing next to her sedan in a garage with arms crossed and an annoyed smug expression, {T}",
  f"{M1} in a jacket driving at night looking tired, dashboard glow, {T}",
  f"{M1} calmly holding up a smartphone to photograph a parked car in a garage, {T}",
  f"Close-up of a green electric vehicle charging bay floor marking with a charging cable, {T}",
  f"Close-up of a smartphone screen showing a camera viewfinder aimed at a parked car, garage, {T}",
  f"Close-up of a hand holding a smartphone taking a photo, timestamp style overlay avoided, garage at night, {T}",
  f"Close-up of several white official envelopes stuffed in an apartment mailbox, {T}",
  f"{W1} holding a stack of envelopes with a shocked face at a mailbox, {T}",
  f"{M1} plugging a charging cable into his electric car in the garage, small smile, {T}",
  f"Close-up of an electric car charging port with cable connected, green light, {T}"])

EP["dogleash"] = dict(
 t1='"우리 개는 안 물어요"', t2='목줄 풀고 다니던 견주의 결말',
 hook='"우리 개는 안 물어요" 목줄 풀고 다니던 견주의 결말', bar='공원에서 매일 목줄 풀어놓는 대형견',
 src='https://www.easylaw.go.kr/CSP/OnhunqueansInfoRetrieve.laf?onhunqnaAstSeq=87&onhunqueSeq=6152', tag='#목줄',
 lines=[
  L("우리 개는 안 문다며 목줄 풀고 다니던 견주가 있었음.",1),
  L("아파트 공원에서 30kg짜리 대형견을 매일 저녁 목줄 없이 풀어놨음.",2,"whoosh",em="30kg"),
  L("우리 애는 순해서 안 물어요! 왜 호들갑이세요?!",3,"eng",dlg="sub1"),
  L("무서우면 그쪽이 돌아가세요!",3,"dudung",dlg="sub1",emo="happy"),
  L("유모차 끌고 나온 엄마들이 개가 달려올 때마다 얼어붙었고, 놀이터가 비기 시작했음.",4,"tick"),
  L("근데 한 아빠가 화내는 대신 영상을 찍어서 구청에 보냈음.",5,"ding"),
  L("동물보호법. 외출할 때 반려견은 2m 이내 목줄이나 가슴줄이 필수임.",6,"pop",em="2m",yellow=True),
  L("안 하면 과태료 1차 20만 원, 2차 30만 원, 3차부터 50만 원임.",6,"cash",em="50만 원",yellow=True),
  L("그리고 목줄 안 한 개가 사람을 다치게 하면 견주는 2년 이하 징역이나 2천만 원 이하 벌금임.",7,"siren",em="2년 이하 징역"),
  L("영상 세 개가 사흘 간격으로 접수됐더니",8,"whoosh"),
  L("한 달 사이에 20만, 30만, 50만. 과태료 100만 원이 날아왔음.",9,"thud",em="100만 원"),
  L("아니, 진짜 안 문다니까요!!?",10,"eng",dlg="sub1"),
  L("무는지 안 무는지가 아니라 줄이 있냐 없냐가 기준인 거임.",10,"boing"),
  L("공원에 목줄 푼 개 때문에 못 나가는 친구한테 이거 보내주셈.",11),
  OUTRO],
 prompts=[
  f"A large dog running free without a leash across a Korean apartment complex park lawn in the evening, {T}",
  f"{W1} in athleisure standing in a park with a leash coiled in her hand, large dog running in the background, smug expression, {T}",
  f"{W1} in athleisure with arms crossed and a dismissive expression in a park, {T}",
  f"A young Korean mother with a stroller frozen on a park path, large dog approaching in the distance, {T}",
  f"{M1} in a jacket calmly holding up a smartphone recording video in a park, {T}",
  f"Close-up of a red dog leash and harness hanging on a hook by a front door, {T}",
  f"Close-up of several white official envelopes on a table with a calculator, {T}",
  f"Close-up of an open law book with a finger on a highlighted line, {T}",
  f"Close-up of a hand tapping send on a smartphone, park background, {T}",
  f"{W1} holding a stack of envelopes at an apartment mailbox with a shocked face, {T}",
  f"A large dog walking calmly on a short leash beside its owner in a park, {T}",
  f"Children playing on a Korean apartment playground in the evening, parents watching, {T}"])

EP["parcel"] = dict(
 t1='"문 앞에 뒀는데 없어졌으면 저희 책임 아니죠"', t2='택배사가 배상한 이유',
 hook='"문 앞에 뒀는데 없어졌으면 저희 책임 아니죠" 택배사가 배상한 이유', bar='문 앞 배송 완료 사진은 있는데 물건이 없음',
 src='https://easylaw.go.kr/CSP/CnpClsMain.laf?popMenu=ov&csmSeq=663&ccfNo=3&cciNo=1&cnpClsNo=2', tag='#택배분실',
 lines=[
  L("문 앞에 뒀는데 없어진 건 자기 책임 아니라던 택배사가 배상한 이유가 있음.",1),
  L("38만 원짜리 무선 이어폰을 시켰는데, 배송 완료 문자만 오고 문 앞엔 아무것도 없었음.",2,"whoosh",em="38만 원",yellow=True),
  L("문 앞 사진 있잖아요! 저희는 배송 완료예요?!",3,"eng",dlg="sub2"),
  L("없어진 건 경찰에 신고하세요. 저희 책임 아니에요!",3,"dudung",dlg="sub2",emo="happy"),
  L("CCTV는 복도에 없고, 경찰은 절도 신고 접수만 해주고 끝이었음.",4,"tick"),
  L("근데 여기서 택배 표준약관을 찾아봤음.",5,"ding"),
  L("택배는 받는 사람한테 직접 전달하는 게 원칙이고, 문 앞에 두려면 받는 사람 동의가 있어야 함.",6,"pop",em="동의",yellow=True),
  L("주문할 때 문 앞 배송을 고른 적도 없고 연락도 없었으면, 두고 가서 잃어버린 책임은 택배사 거임.",6,"siren",em="택배사 거"),
  L("분실은 14일 안에 통지하면 되고, 표준약관 배상 한도는 50만 원임.",7,"cash",em="14일"),
  L("약관 조항 캡처해서 내용증명으로 보냈더니",8,"whoosh"),
  L("일주일 뒤 택배사에서 38만 원 전액을 배상했음.",9,"thud",em="38만 원 전액"),
  L("아니, 사진 찍어놨는데요!!?",10,"eng",dlg="sub2"),
  L("사진은 두고 갔다는 증거지, 동의받았다는 증거가 아닌 거임.",10,"boing"),
  L("택배 잃어버린 적 있는 친구한테 이거 보내주셈. 14일임.",11),
  OUTRO],
 prompts=[
  f"An empty apartment hallway doormat in front of a door, no package, fluorescent light, {T}",
  f"{W1} standing at her apartment door looking at her phone with a confused face, empty doormat, {T}",
  f"A Korean delivery man in a cap and vest at a van, shrugging with a dismissive expression, {T}",
  f"Close-up of a police station counter with a blank form and a pen, {T}",
  f"{W1} at a kitchen table reading a document on her laptop with a determined face, {T}",
  f"Close-up of an open printed document with a yellow highlighted line, {T}",
  f"Close-up of a hand knocking on an apartment door, package under the other arm, {T}",
  f"Close-up of a desk calendar with a date circled in red and a pen, {T}",
  f"Close-up of a hand dropping a white envelope into a red Korean post box, {T}",
  f"Close-up of a smartphone in a woman's hand showing a big green checkmark icon, {T}",
  f"A Korean delivery man in a vest looking flustered at his handheld scanner beside a van, {T}",
  f"{W1} smiling while receiving a package directly from a delivery man at her door, {T}"])

for slug, e in EP.items():
    d = os.path.join(ROOT, "work", slug); os.makedirs(d, exist_ok=True)
    sc = {"slug": slug, "type": "F형 (법조항 사이다) — 각색", "source": e["src"],
          "title_line1": e["t1"], "title_line2": e["t2"], "hook": e["hook"],
          "channel": "썰푸는휴지", "voice": "taesub",
          "style": {"sub_box": True, "motion": True, "bar": e["bar"]}, "lines": e["lines"]}
    json.dump(sc, open(os.path.join(d, "script.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    with open(os.path.join(d, "prompts.tsv"), "w", encoding="utf-8") as f:
        for i, p in enumerate(e["prompts"], 1):
            f.write(f"{i:02d}\t{p}\n")
    with open(os.path.join(d, "upload.md"), "w", encoding="utf-8") as f:
        f.write(f"# {slug} — 업로드 메타\n\n## 제목\n\n{e['tag']} {e['hook']}\n\n## 설명\n\n"
                f"{e['bar']}. 상황은 규정을 설명하기 위해 각색한 사례이며 특정 인물·업체와 무관합니다.\n"
                f"※ 근거: {e['src']}\n※ 영상 속 이미지는 AI 연출 자료입니다.\n\n#shorts {e['tag']} #사이다 #법 #썰\n\n"
                f"## 고정 댓글\n\n님들도 이런 일 당해본 적 있음?\n\n---\n- 각색. 나레이션 태섭, 대사 angry/happy, 구독 소예. 이미지: gpt 우선, 로컬 SDXL 폴백.\n")
    n = len(e["lines"]); print(slug, n, "lines", len(e["prompts"]), "imgs", "maximg", max(l.get("img",0) for l in e["lines"] if isinstance(l, dict)))
