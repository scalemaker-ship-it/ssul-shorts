# -*- coding: utf-8 -*-
"""사이다 현장 3편 (2026-09-15): gyeongbok / drone / ktxfee"""
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
    if em: d["em"] = [em]
    if yellow: d["em_color"] = "yellow"
    if sfx: d["sfx"] = sfx
    if dlg: d["dialogue"] = True; d["voice"] = dlg; d["emotion"] = emo or "angry"; d["intensity"] = 2.0
    return d
EP = {}
EP["gyeongbok"] = dict(t1='"짐 좀 맡길게요"', t2='경복궁 댕댕런의 결말',
 hook='"짐 좀 맡길게요" 경복궁 댕댕런의 결말', bar='박물관 무료 보관소를 러닝 짐 창고로 쓴 크루들',
 src='https://www.fnnews.com/news/202609041444332074', tag='#댕댕런',
 lines=[
  L("짐 좀 맡기겠다던 경복궁 댕댕런 러너들이 박물관 공지 한 장에 막혔음.",1),
  L("댕댕런은 광화문에서 출발해 경복궁, 청와대, 삼청동, 청계천을 도는 8km 코스임. GPS 궤적이 강아지 모양이라 붙은 이름임.",2,"whoosh",em="8km"),
  L("전현무가 예능에서 소개하고 나서 러닝크루가 몰렸음.",3,"pop"),
  L("근데 문제는 뛰기 전에 짐을 어디 두느냐였음.",4,"tick"),
  L("국립고궁박물관에 무료 물품보관소가 있거든. 러너들이 거기에 가방을 맡기고 두세 시간 뛰고 오는 거임.",5,"dudung",em="무료 물품보관소",yellow=True),
  L("무료라면서요? 잠깐 맡기는 건데 뭐 어때요?!",6,"eng",dlg="sub1",emo="happy"),
  L("정작 전시 보러 온 관람객은 보관소가 꽉 차서 가방을 들고 다녔음.",7,"tick"),
  L("그래서 9월 3일, 박물관이 공식 인스타에 공지를 올렸음.",8,"ding",em="9월 3일",yellow=True),
  L("무료 물품보관소는 전시 관람객을 위한 시설이니, 관람 목적 외 보관은 자제해 달라.",8,"siren"),
  L("한마디로 러닝 짐 창고로 쓰지 말라는 거임.",9,"pop",em="짐 창고"),
  L("아니, 그럼 짐은 어디에 두라고요!!?",6,"eng",dlg="sub1"),
  L("경복궁역에 유료 물품보관함이 있음. 몇천 원이면 됨.",10,"cash",em="유료"),
  L("공짜 창고 쓰다가 몇천 원짜리 보관함 쓰게 된 거임.",10,"boing"),
  L("러닝크루 하는 친구 있으면 이거 보내주셈. 박물관은 짐 창고가 아님.",1),
  OUTRO],
 prompts=[
  f"A large group of runners in athletic wear jogging past the stone walls of Gyeongbokgung palace in Seoul at dawn, traditional Korean palace gate in background, {T}",
  f"Aerial view of a running route through old Seoul streets around a palace, drawn as a glowing line on a dark map, no text, {T}",
  f"A crowd of Korean runners in matching crew shirts stretching in front of a palace plaza in the early morning, {T}",
  f"{W1} in running gear standing with a heavy backpack at her feet looking around a palace plaza, {T}",
  f"Rows of free coin lockers in a museum lobby, several doors open with backpacks and running shoes stuffed inside, {T}",
  f"{W1} in running gear with a smug shrug next to museum lockers, {T}",
  f"An elderly Korean couple in a museum lobby holding their bags awkwardly in front of fully occupied lockers, {T}",
  f"Close-up of a smartphone screen showing a social media post card with a museum photo, no readable text, held in a hand, {T}",
  f"Close-up of a museum locker door being closed with a small paper notice taped on it, no readable text, {T}",
  f"A row of paid coin lockers in a Seoul subway station corridor, a hand inserting coins, {T}"])
EP["drone"] = dict(t1='"갓길로 잠깐 빠질게요"', t2='추석 고속도로의 결말',
 hook='"갓길로 잠깐 빠질게요" 추석 고속도로 얌체 운전자의 결말', bar='통행료 무료 나흘, 갓길 얌체차를 하늘에서 잡음',
 src='https://www.gokorea.kr/news/articleView.html?idxno=877330', tag='#추석고속도로',
 lines=[
  L("갓길로 잠깐 빠지겠다던 얌체 운전자들이 이번 추석엔 하늘에서 잡힘.",1),
  L("9월 24일부터 27일까지 나흘간 고속도로 통행료가 무료임.",2,"whoosh",em="무료",yellow=True),
  L("그만큼 차가 몰리고, 매년 나오는 게 갓길 주행이랑 버스전용차로 얌체차임.",3,"tick"),
  L("어차피 카메라 없잖아요, 잠깐인데 뭐?!",4,"eng",dlg="sub2",emo="happy"),
  L("근데 올해는 한국도로공사랑 경찰이 순찰 드론을 수십 대 띄움.",5,"ding",em="순찰 드론",yellow=True),
  L("30배 광학줌 4K 카메라에 AI가 달려서, 갓길 주행이랑 버스전용차로 위반, 비상등 없는 급정거를 자동으로 골라냄.",6,"siren"),
  L("상공 30에서 50m에서 번호판까지 찍히고, 사고 현장엔 3분 안에 도착함.",7,"pop",em="3분"),
  L("갓길 주행이랑 고속도로 버스전용차로 위반은 승용차 기준 범칙금 6만 원에 벌점 30점임.",8,"cash",em="벌점 30점",yellow=True),
  L("벌점은 40점부터 면허정지라, 두 번 걸리면 면허가 날아감.",8,"dudung",em="면허정지"),
  L("아니, 경찰차도 없었는데요!!?",9,"eng",dlg="sub2"),
  L("경찰차는 없었고, 드론이 위에 있었던 거임.",9,"boing"),
  L("추석에 운전대 잡을 친구한테 이거 보내주셈. 하늘 조심.",10),
  OUTRO],
 prompts=[
  f"A silver sedan driving on the highway shoulder past a long line of stopped cars in a traffic jam, aerial view, daytime, {T}",
  f"A crowded Korean expressway toll gate with barrier arms raised, heavy holiday traffic, {T}",
  f"Aerial view of a jammed multi-lane expressway, one car cutting along the shoulder, {T}",
  f"{M2} behind the wheel of a sedan grinning and glancing at the side mirror, {T}",
  f"A quadcopter surveillance drone hovering above a highway with a camera gimbal, blue sky, {T}",
  f"Close-up of a drone camera gimbal lens, expressway blurred far below, {T}",
  f"A patrol drone flying low over a highway with police cars stopped on the shoulder below, {T}",
  f"Close-up of a traffic penalty notice envelope and car keys on a kitchen table, {T}",
  f"{M2} standing beside his sedan on the highway shoulder looking up at the sky with a shocked face, {T}",
  f"A quiet Korean expressway at dawn with a drone silhouette against the sunrise, {T}"])
EP["ktxfee"] = dict(t1='"표 안 쓰면 그만이죠"', t2='명절 KTX 노쇼의 결말',
 hook='"표 안 쓰면 그만이죠" 명절 KTX 노쇼족의 결말', bar='추석 기차표 여러 장 잡고 버리는 사람들',
 src='https://info.korail.com/info/selectBbsNttView.do?bbsNo=199&key=911&nttNo=23993', tag='#추석기차표',
 lines=[
  L("표 안 쓰면 그만이라던 명절 KTX 노쇼족이 있었음.",1),
  L("추석 기차표는 9월 23일부터 27일까지가 명절 특별수송 기간임.",2,"whoosh"),
  L("예매 전쟁이라 일단 여러 장 잡아놓고, 안 타는 표는 그냥 버리는 사람들이 있음.",3,"tick",em="여러 장"),
  L("취소하면 수수료 나오잖아요. 그냥 안 타면 되지?!",4,"eng",dlg="sub1",emo="happy"),
  L("근데 명절 기간은 위약금이 평소랑 다름.",5,"ding"),
  L("출발 2일 전까지는 200원, 하루 전은 5%, 당일 출발 3시간 전까지는 10%.",6,"cash",em="200원",yellow=True),
  L("출발 3시간 전부터 출발까지는 20%, 출발하고 나면 최대 70%까지 뗌.",6,"dudung",em="70%",yellow=True),
  L("그러니까 안 타고 버리는 표는 환불이 거의 안 되고, 미리 취소한 사람은 200원에 끝남.",7,"pop"),
  L("서울 부산 6만 원짜리 표면, 이틀 전 취소는 200원, 출발 뒤 반환은 4만 2천 원 가까이 날아감.",8,"cash",em="4만 2천 원"),
  L("그 취소표는 새벽에 줍는 사람한테 가서 고향 가는 자리가 됨.",9,"whoosh"),
  L("아니, 내 돈 주고 산 표인데요!!?",4,"eng",dlg="sub1"),
  L("내 돈 주고 산 표라서 70%가 내 돈에서 나가는 거임.",9,"boing"),
  L("추석 기차표 여러 장 잡아둔 친구한테 이거 보내주셈. 이틀 전까지 200원임.",10),
  OUTRO],
 prompts=[
  f"A high-speed train at a busy Seoul station platform with holiday travelers carrying gift boxes, {T}",
  f"Close-up of a paper wall calendar with a five-day span circled in red, no readable text, {T}",
  f"{W1} at a cafe table holding several train tickets fanned out in her hand, smug expression, {T}",
  f"{W1} shrugging with a dismissive smile, train station concourse behind her, {T}",
  f"Close-up of a smartphone showing a train booking app with a red cancel button, no readable text, {T}",
  f"Close-up of a calculator and Korean coins and banknotes on a desk beside a train ticket, {T}",
  f"An empty reserved seat on a moving high-speed train with a ticket left on the tray table, {T}",
  f"Korean banknotes fanned out next to a train ticket on a wooden table, {T}",
  f"{M1} smiling while boarding a high-speed train with a small suitcase at dawn, {T}",
  f"A high-speed train speeding through Korean countryside with rice fields in autumn, {T}"])
for slug, e in EP.items():
    d = os.path.join(ROOT, "work", slug); os.makedirs(os.path.join(d,"img"), exist_ok=True)
    sc = {"slug": slug, "type": "사이다·현장 (2026-09-15 분석 1순위)", "source": e["src"],
          "title_line1": e["t1"], "title_line2": e["t2"], "hook": e["hook"], "channel": "썰푸는휴지",
          "voice": "taesub", "style": {"sub_box": True, "motion": True, "bar": e["bar"]}, "lines": e["lines"]}
    json.dump(sc, open(os.path.join(d, "script.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    with open(os.path.join(d, "prompts.tsv"), "w", encoding="utf-8") as f:
        for i, p in enumerate(e["prompts"], 1): f.write(f"{i:02d}\t{p}\n")
    with open(os.path.join(d, "upload.md"), "w", encoding="utf-8") as f:
        f.write(f"# {slug}\n\n## 제목\n\n{e['tag']} {e['hook']}\n\n## 근거\n{e['src']}\n")
    print(slug, len(e["lines"]), "lines", len(e["prompts"]), "imgs")
