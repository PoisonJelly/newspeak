#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""newspeak / lint.py: Korean and English AI-writing pattern detector.

Standard library only. Rule IDs match references/ko-patterns.md and
references/en-patterns.md.

Usage:
  python lint.py FILE [--lang auto|ko|en] [--json] [--skip-quotes] [--max-items N]
  python lint.py -                     # read stdin

Exit codes: 0 = no S1, 1 = at least one S1, 3 = runtime error.
"""
from __future__ import annotations

import argparse
import bisect
import json
import math
import re
import statistics
import sys
import unicodedata
from collections import Counter

SEV_RANK = {"S1": 1, "S2": 2, "S3": 3}
KO_UNIT = 1500   # Korean chars per scaling unit for density rules
EN_UNIT = 700    # English words per scaling unit

# ---------------------------------------------------------------------------
# Rule table: (id, lang, name, pattern, levels, scale, hint, opts)
#   lang   : ko | en | any
#   levels : minimum match counts per severity, e.g. {"S1": 3, "S2": 1}
#   scale  : True -> thresholds grow with text length (density rules)
#   opts   : {"flags": re.I, "raw": True (run on unmasked text),
#             "skip_prev": set of preceding words to ignore}
# ---------------------------------------------------------------------------
I = re.I
M = re.M

NOUN_GO = {  # nouns or conjunctions ending in 고/며/면 that are not connective endings
    "최고", "광고", "보고", "경고", "참고", "재고", "사고", "창고", "원고", "신고",
    "공고", "고고", "지고", "선고", "충고", "권고", "기고", "탈고", "투고", "마감고",
    "학고", "등고", "입고", "출고", "반품고", "매출고", "잔고", "통고", "예고", "회고",
    "측면", "이면", "전면", "화면", "장면", "방면", "표면", "국면", "정면", "반면",
    "지면", "단면", "대면", "내면", "외면", "일면", "양면", "수면", "체면", "라면",
    "냉면", "가면", "후면", "평면", "곡면", "도면", "서면", "사면", "다면", "이를테면",
}
# these spellings are also connective endings ('뜸해졌다면,', '친구라면,', '학생이면,'): exclude only the bare word
NOUN_GO_AMBIG = {"다면", "이면", "라면", "가면", "지면", "사면", "수면", "대면", "서면", "도면",
                 "보고", "입고", "지고", "사고", "신고", "재고", "고고", "그래도"}
NOUN_GO_T = tuple(NOUN_GO - NOUN_GO_AMBIG)

KO_RULES = [
    # --- A. translationese ---
    ("KO-A1b", "ko", "'~에 대해 설명/안내/소개합니다'", r"에 대해(?:서)? (?:설명|안내|소개|정리|기술|서술|다루|다룹|다뤄|다뤘)", {"S2": 2, "S3": 1}, True,
     "목적어를 바로 받는 동사라 '~을/를'로 바꾼다: '절차에 대해 설명합니다' -> '절차를 설명합니다'.", {}),
    ("KO-A1", "ko", "'~에 대해(서)' 밀집", r"에 대(?:해서?|하여|한)", {"S2": 3, "S3": 2}, True,
     "목적격 조사로 바로 잇는다: 'X에 대해 논의' -> 'X를 논의'. 한두 번은 사람도 쓴다.", {}),
    ("KO-A3", "ko", "'~에 있어(서)'", r"에 있어서?(?:는|도|의)?(?=[\s,]|$)", {"S1": 2, "S2": 1}, False,
     "'~에서', '~을 볼 때'로 바꾼다. 장소('집에 있어서')면 무시한다.", {}),
    ("KO-A5", "ko", "'~와 관련하여 / ~에 기반하여'", r"(?:와|과) 관련(?:하여|해서?|된|한)|에 기반(?:하여|해서?|한)|(?:을|를) (?:기반|바탕)으로", {"S2": 3, "S3": 1}, True,
     "'~에', '~로', '~를 보고'로 줄인다.", {}),
    ("KO-A7", "ko", "'가지고 있다'(have 직역)", r"(?:을|를) (?:가지고|갖고) (?:있|있었)", {"S1": 3, "S2": 1}, False,
     "형용사로 푼다: '경쟁력을 가지고 있다' -> '경쟁력이 있다'. 물건을 가진 뜻이면 둔다.", {}),
    ("KO-A8", "ko", "이중 피동", r"되어지|되어진|되어집|보여지|보여진|보여집|쓰여지|쓰여진|쓰여집|불려지|불려진|불려집|만들어지게 되|나뉘어지|나뉘어집|지게 된다|지게 됩니다"
     r"|(?:읽|잊|닫|갇|먹|잡|찍|묻|박)혀(?:지|진|집)|(?:놓|짜)여(?:지|진|집)|(?:담|안|감)겨(?:지|진|집)|열려(?:지|진|집)", {"S1": 1}, False,
     "단일 피동이나 능동으로: '판단되어진다' -> '판단된다'.", {}),
    ("KO-A9", "ko", "'~에 의해' 피동", r"에 의해서?|에 의하여", {"S2": 2, "S3": 1}, True,
     "행위자를 주어로: 'AI에 의해 생성된' -> 'AI가 만든'.", {}),
    ("KO-A10", "ko", "'~할 수 있다' 반복", r"[가-힣] ?수 있(?:다|습니다|어요|는|을|으며|고)", {"S2": 5, "S3": 3}, True,
     "단정으로 바꾸지 않는다. 일부만 다른 완곡으로 나눠 리듬만 깬다. 의학·법률 글은 둔다.", {}),
    ("KO-A15", "ko", "추상 주어 + 만능 동사", r"(?:를|을) (?:보여준다|보여줍니다|보여주고|제공한다|제공합니다|선사한다|선사합니다|가져온다|가져옵니다)", {"S2": 2, "S3": 1}, True,
     "구체 주어로 바꾸거나 '~에 따르면 ~이다'로 푼다.", {}),
    ("KO-A16", "ko", "문두 지시어 '이는/이러한/이처럼'", r"(?:^|(?<=[.!?…]) )(?:이는|이러한|이를 통해|이처럼|이에 따라|이로써|이로 인해)", {"S1": 4, "S2": 2}, True,
     "앞 문장과 잇거나 지시어를 지운다.", {"flags": M}),
    ("KO-A19", "ko", "이중 조사", r"(?:에서|으로부터|로부터|에게서|에로|으로)의(?=\s)|에의(?=\s)", {"S1": 3, "S2": 1}, False,
     "절로 풀어 쓴다: '긴장으로부터의 해방' -> '긴장에서 풀려나는 것'.", {}),
    ("KO-A20", "ko", "'~되고/지고 있다' 진행 피동", r"(?:되고|지고) 있(?:다|습니다|어요)", {"S2": 3, "S3": 2}, True,
     "일부만 단순 시제로: '심화되고 있다' -> '심해졌다'.", {}),
    ("KO-A21", "ko", "'단순한 X를 넘어'", r"단순(?:한|히)\s?[^.!?\n]{0,20}?(?:을|를)?\s?넘어", {"S1": 1}, False,
     "넘어-구를 지우고 Y를 바로 쓴다. 사람 글 실측 0건.", {}),
    ("KO-A22", "ko", "'~은 분명하다/명확하다' 평가 술어", r"(?:은|는|이|가|함은|것은) (?:분명|명확)(?:하다|합니다)", {"S2": 1}, False,
     "평가 술어를 걷고 명제를 단언한다.", {}),
    ("KO-A24", "ko", "'더 이상'", r"더 이상", {"S2": 2, "S3": 1}, True,
     "'이제'로 바꾸거나 변화 동사로 편다. '더 이상 A가 아니라 B'를 새로 만들지 않는다.", {}),
    ("KO-A25", "ko", "'~를 진행하다'", r"(?:을|를) 진행(?:하|했|합|할|해|한|하여|하고|해서)", {"S2": 3, "S3": 1}, True,
     "동사로 바로 쓴다: '논의를 진행했다' -> '논의했다'.", {}),
    # --- B. English in Korean ---
    ("KO-B1", "ko", "괄호 영어 병기 반복", r"[가-힣]+\s?\((?=[A-Za-z])[A-Za-z0-9 .\-/&]{2,40}\)", {"S2": 4, "S3": 2}, True,
     "첫 등장만 병기하고 이후는 한글만 쓴다.", {}),
    ("KO-B2", "ko", "광고성 영어 buzzword", r"\b(?:seamless|robust|leverage|synergy|holistic|game[- ]?changer|cutting[- ]?edge|next[- ]level|insightful)\b", {"S2": 1}, False,
     "한국어로 푼다. API·token 같은 표준 용어는 둔다.", {"flags": I}),
    # --- C. structure ---
    ("KO-C8", "ko", "대조 구문 'A가 아니라 B'", r"(?:이|가|은|는|게|것이|것은)?\s?(?<!뿐만 )(?<!뿐 )(?<!뿐만)(?<!뿐)아니라(?=[\s,]|$)|(?:인가|일까), [^.?!\n]{1,20}(?:인가|일까)", {"S1": 1}, False,
     "B를 그냥 단언한다. 앞에서 한 말을 바로잡는 자리만 예외다.", {}),
    ("KO-C8c", "ko", "두 문장 대조 'A가 아니다. B다.'", r"(?:이|가|은|는|게) 아니(?:다|에요|야|죠|었다)\.\s+[^.!?\n]{1,20}(?:다|입니다|예요|이에요)\.", {"S2": 1}, False,
     "뒤 문장이 앞을 고쳐 정의하는 구조면 B만 남긴다. 단순 부정 뒤 사실 서술이면 둔다.", {}),
    ("KO-C8b", "ko", "'~뿐만 아니라' 반복", r"뿐(?:만)? 아니라", {"S2": 3, "S3": 2}, True,
     "'~도', '~에 더해'로 일부를 바꾼다.", {}),
    ("KO-C9", "ko", "숫자 괄호 나열 '1) 2) 3)'", r"(?:^|\s)[1-9]\)\s", {"S3": 3}, False,
     "산문이면 본문에 녹인다. 목록 형식이 맞는 문서면 둔다.", {"flags": M}),
    ("KO-C10", "ko", "콜론 부제 제목 'X: Y'", r"^#{1,6}\s+[^:\n]{1,40}:\s+\S", {"S3": 2}, False,
     "제목을 명사구 하나로 줄인다.", {"flags": M}),
    ("KO-C11", "ko", "연결어미 뒤 쉼표", r"([가-힣]+?)(지만|면서|으며|이며|하며|하고|이고|으나|이나|는데|은데|인데|니까|으니|므로|아서|어서|여서|해서|라서|워서|와서|돼서|내서|봐서|줘서|으로써|도록|더니|다가|거나|으면|다면|려면|하여|아도|어도|해도|여도|고|며|면)\s?,", {"S1": 3, "S2": 1}, False,
     "쉼표를 지운다. 윤문이 새 쉼표를 만들면 실패다.", {"connective": True}),
    # --- D. signature phrases ---
    ("KO-D1a", "ko", "결산 표지 '결론적으로/요약하면'", r"결론적으로|결론부터 (?:말하자면|말하면|짧게)|요약하(?:면|자면)|정리하(?:면|자면)|종합하(?:면|자면)|한마디로 (?:말하면|정리하면)", {"S1": 1}, False,
     "지운다. 마지막 문단 자체가 결론이다.", {}),
    ("KO-D1b", "ko", "연결 결산어 '다시 말해/즉/이를 통해'", r"다시 말해|(?:^|(?<=[\s.]))즉,?(?=\s)|이를 통해|이를 바탕으로", {"S1": 5, "S2": 3}, True,
     "한두 개만 남기고 지운다.", {"flags": M}),
    ("KO-D2", "ko", "의의 과장", r"시사하는 바(?:가|는|도) (?:크|많)|주목할 만(?:하|한|합)|매우 중요(?:하|한|합)|(?:중요한|핵심적인|결정적인) 역할을|새로운 지평|패러다임|획기적|혁신적인|게임 ?체인저|판도를 바꾸|한 획을 긋|(?:중요한|새로운|큰) 전환점", {"S1": 3, "S2": 1}, True,
     "지우거나 구체 결과로 바꾼다.", {}),
    ("KO-D3", "ko", "열거 도입", r"크게 (?:두|세|네|다섯) 가지|(?:다음|아래)과 같(?:다|습니다|이|은)|다음과 같(?:다|습니다|이|은)", {"S2": 3, "S3": 1}, True,
     "도입구를 지우고 바로 쓴다.", {}),
    ("KO-D6", "ko", "결말 공식 '~할 때입니다'", r"(?:할|될|나설|돌아볼|고민할|생각할|움직일|나아갈) 때(?:다|이다|입니다|가 왔다)|(?:시점|순간)(?:이다|입니다)[.!]", {"S1": 2, "S2": 1}, False,
     "구체 동사로 단언한다. 문서당 1회 이하.", {}),
    ("KO-D7", "ko", "변환 공식 'X에서 Y로'", r"에서 [^.!?\n]{1,15}(?:으)?로[.!]?$|(?:을|를) 넘어 [^.!?\n]{1,15}(?:으)?로", {"S2": 2, "S3": 1}, False,
     "직접 단언으로 바꾼다. 문서당 1회 이하.", {"flags": M}),
    ("KO-D8", "ko", "분열문 '필요한 것은/핵심은'", r"(?:필요한|중요한|핵심적인) 것은|(?:^|(?<=[\s\"'(]))(?:핵심|관건|요점)은(?=\s)", {"S1": 3, "S2": 1}, True,
     "주어-서술로 잇는다: '필요한 것은 방향이다' -> '방향이 필요하다'.", {"flags": M}),
    ("KO-D9", "ko", "인과 결산 '결국/~로 이어진다'", r"결국|(?:으)?로 이어(?:진다|집니다|질 것)|에 직결(?:된다|됩니다)", {"S1": 4, "S2": 2}, True,
     "'결국'은 1회만 남긴다. 인과 경로를 구체로 쓴다.", {}),
    ("KO-D10", "ko", "도치 결산 '~하는 이유다'", r"[가-힣]+(?:는|은|던|ㄴ) 이유(?:다|이다|입니다)(?=[.!\s]|$)", {"S1": 2, "S2": 1}, False,
     "순방향으로: '그래서 ~다'. 새로 만들지 않는다.", {}),
    ("KO-D11", "ko", "출처 없는 '~다는 분석이다'", r"다는 (?:분석|평가|전망|지적|관측)(?:이다|입니다|다|이 나온다|이 많다)", {"S2": 1}, False,
     "출처가 있으면 둔다. 없으면 직접 서술로.", {}),
    ("KO-D12", "ko", "문패 문장 '과제도 남아 있다'", r"과제(?:도|가) (?:남아 ?있|산적)|한계도 (?:분명|있)|아쉬운 점도 (?:있|남)", {"S2": 1}, False,
     "문패를 지우고 실제 과제를 바로 쓴다.", {}),
    ("KO-D14", "ko", "사전 은유·감각 평가", r"잠식|청사진|적신호|경고등|신호탄|귀추가 주목|움켜쥐|뿌리내리|짓누르|토대를 마련|발판을 마련|지평을 열|첫발을 내딛|서늘하|(?:논리|주장|근거|설명)(?:이|가|은|는)? 선명", {"S1": 3, "S2": 1}, True,
     "명제로 바꾼다: '잠식한다' -> '점유율을 뺏는다'. 같은 은유 반복도 줄인다.", {}),
    # --- G. hedging & lecturing ---
    ("KO-G1", "ko", "같은 추측 종결 반복", r"(?:로|으로) (?:보인다|보입니다|판단된다|판단됩니다|여겨진다|여겨집니다|해석된다|해석됩니다)|(?:라고|다고) 할 수 있(?:다|습니다)", {"S2": 4, "S3": 2}, True,
     "단정으로 바꾸지 않는다. 유보 강도는 두고 형태만 바꾼다.", {}),
    ("KO-G5", "ko", "'~라고 할 수 있다' 얼버무림", r"(?:라고|다고|이라고) 할 수 있(?:다|습니다|어요|죠|겠다|겠습니다|겠어요)", {"S2": 3, "S3": 1}, True,
     "일반론에 붙은 얼버무림이면 문장째 지우거나 구체 사실로 바꾼다. 추측이 내용이면 표지 하나로 남긴다: '~라고 봐요', '~인 셈이에요'.", {}),
    ("KO-G2", "ko", "이중 완곡", r"수 있을 (?:것으로|것이라고) (?:보인|보입|예상|판단|생각)|가능성이 있을 수|보여질 수 있|(?:로|으로) 보일 수 있|(?:일|할) 수도 있을 것", {"S1": 2, "S2": 1}, False,
     "완곡 하나만 남긴다. 남긴 완곡의 확신도는 그대로.", {}),
    ("KO-G3", "ko", "훈계형 도입 '다만/짚고 가자'", r"(?:^|(?<=[.!?] ))다만[, ]|하나만 짚(?:고|어)|선을 긋고|짚고 넘어가", {"S2": 3, "S3": 2}, True,
     "꼭 필요한 단서만 문장 안에 녹인다. 문단 첫머리 '다만,'이 앞 문단과 대조되지 않으면(화제 전환, 코드 블록·표 바로 뒤) 지운다.", {"flags": M}),
    # --- I. formal nouns & ought-endings ---
    ("KO-I3", "ko", "'~다는 것이다' 결말", r"(?:다는|라는|는다는|한다는|ㄴ다는) (?:것|뜻|말)(?:이다|입니다)", {"S2": 2, "S3": 1}, True,
     "'~다'로 바로 끝낸다. 합산 2회 이하.", {}),
    ("KO-I4b", "ko", "당위·중요 종결 밀도", r"(?:[아어여해]야 (?:한다|합니다|해요|할 것이다)|필요가 있(?:다|습니다)|필요(?:하다|합니다)|중요(?:하다|합니다)|시급(?:하다|합니다))(?=[.!]|$)", {"S2": 8, "S3": 5}, True,
     "논평·공지에서 당위는 정상이다. 몰렸을 때만 일부를 사실 서술이 아닌 행위 주체 문장으로 바꾼다. 서법은 지킨다.", {"flags": M}),
    ("KO-I5", "ko", "'~하는 것이 중요합니다'", r"(?:는|하는|ㄴ|은) (?:것이|게) (?:중요|필요|바람직|좋)(?:합니다|하다|해요)", {"S1": 2, "S2": 1}, False,
     "누가 무엇을 하는지 동사로 쓴다.", {}),
    ("KO-D15", "ko", "결론·전망류 소제목", r"^#{1,6}[ \t]*(?:\S+[ \t]+)?(?:결론|결론적으로|마무리|마치며|정리|정리하며|요약|과제와 전망|향후 전망|시사점|의의)[ \t]*$", {"S3": 1}, False,
     "짧은 글이면 소제목을 지운다. 지운 뒤 그 문단이 앞 소제목 아래에 맞는지 본다. 안 맞으면 내용으로 소제목을 다시 단다.", {"flags": M}),
    ("KO-D16", "ko", "막연한 추세 도입문", r"(?:최근|요즘|요즈음|오늘날)[^.!?\n]{0,50}(?:늘고 있|늘어나고 있|높아지고 있|커지고 있|주목받고 있|화두가 되고 있|관심이 (?:높|커|많|쏠))|(?:분들|사람들|사람)이 (?:점점|날로|갈수록) 늘(?:고 있|어나고 있)", {"S2": 1}, False,
     "지우고 본론의 문제 문장으로 시작한다. 원문에 근거 수치가 있으면 그 수치로 쓴다.", {}),
    ("KO-H2", "ko", "문두 인과 접속사 '그래서/그러면' 반복", r"(?:^|(?<=[.!?] ))(?:그래서|그러면|그러니까|따라서|그러므로)(?=[\s,])", {"S2": 5, "S3": 3}, True,
     "빈자리를 접속사로 메우지 않는다. 문단 끝 '그래서 ~' 틀은 2회까지만 둔다.", {"flags": M}),
    ("KO-A31", "ko", "한 문장에 번역투 연결어 2개+", r"[^.!?\n]*(?:에 대해|에 대한|를 통해|을 통해|에 있어|와 관련해|과 관련해|에 기반해)[^.!?\n]*(?:에 대해|에 대한|를 통해|을 통해|에 있어|와 관련해|과 관련해|에 기반해)", {"S2": 1}, False,
     "적어도 하나를 푼다: 'X에 대해 다룬다' -> 'X를 다룬다'.", {}),
    ("KO-D1c", "ko", "'이를 통해 ~할 수 있다' 틀", r"(?:이를 통해|이것을 통해|이로써|이를 바탕으로|이 과정을 통해|이를 계기로|이를 토대로)[^.!?\n]{0,40}수 있(?:다|습니다|어요|었다|었습니다)", {"S2": 1}, False,
     "문장을 나누거나 결과를 바로 쓴다. 자소서·공지의 대표 AI 결말이다.", {}),
    ("KO-K8", "ko", "SNS·공지 상투 문구", r"댓글로 (?:남겨|알려|공유해) ?주세요|여러분의 (?:생각|의견)은 어떠신가요|(?:공유|소식을 전하)하게 되어 (?:기쁩|영광|감사)|좋아요와 구독|구독과 좋아요|알림 설정까지|댓글 하나하나가|큰 힘이 (?:돼요|됩니다)", {"S2": 2, "S3": 1}, False,
     "시청자에게 하는 요청(댓글로 알려 주세요, 구독, 링크 확인)은 기능 문장이라 하나씩 남긴다. 주변 상투구('댓글 하나하나가 큰 힘이 돼요')만 지운다. 질문으로 바꾸면 답할 곳도 남긴다.", {}),
    ("KO-D17", "ko", "홍보 문구 상투구", r"완벽한 (?:선택|동반자|솔루션|파트너)|언제 어디서나|걱정 없이|부담 없이|놓치지 마세요|차원이 다른|한층 더 (?:업그레이드|강화|편리)|특별한 경험을 (?:선사|드립)|만족을 (?:드립|선사)|품격을 (?:높여|더해)", {"S1": 3, "S2": 1}, False,
     "확인할 수 있는 사실(용량, 무게, 가격, 소재)로 바꾼다. 목록 항목도 본문과 같은 기준으로 고친다.", {}),
    ("KO-A29", "ko", "아는 주어 '저는/제가' 반복", r"(?:^|(?<=[\s.]))(?:저는|제가|저의|저희는)(?=\s)", {"S2": 6, "S3": 4}, True,
     "문맥상 아는 주어는 생략한다. 처음과 강조할 곳에만 남긴다.", {"flags": M}),
    ("KO-D18", "ko", "자문자답·안내 도입", r"(?:그럼|그렇다면|자,) ?(?:어떻게|무엇을|뭘) (?:하면|해야) (?:좋을까|할까|될까)\?|몇 가지 (?:방법|팁|포인트|이유)(?:을|를)? (?:정리해|알려|소개해|짚어) ?(?:볼게|줄게|드릴게요|드리겠습니다|볼게요)", {"S2": 1}, False,
     "지우고 바로 내용으로 들어간다. 반말·구어 글에서도 같다.", {}),
    ("KO-K9", "ko", "상담 상투구(가정형 공감·감정 재해석)", r"(?:다면|라면),? [^.!?\n]{0,25}(?:게|것이|건) (?:너무나? |정말 |충분히 )?당연(?:해|하다|해요|합니다|하지)|(?:은|는) [^.!?\n]{0,30}(?:다는|라는) 증거(?:야|예요|이다|입니다|이기도 해|이기도 하다)", {"S2": 1}, False,
     "짧은 구어 반응으로 낮춘다: '10년 친했는데 갑자기 그러면 당연히 서운하지', '그만큼 아끼니까 서운한 거지'. 낮출 수 없으면 지운다.", {}),
    ("KO-K10", "ko", "상담 상투구 '마음·감정을 챙기다'", r"(?:감정|마음|자신|스스로)(?:을|를|도)? (?:잘 )?(?:챙기|돌보|보듬|돌봐|챙겨)", {"S2": 2, "S3": 1}, False,
     "반말 글이면 일상어로 바꾸거나 뺀다: '너도 너 좀 챙기고'. 앞에서 행동을 이미 말했으면 꼬리를 지운다.", {}),
    ("KO-C8d", "ko", "비교 강조 'A보다 B가 중요하다'", r"[^.!?\n]{1,30}보다 [^.!?\n]{1,40}(?:게|것이|건|가|이) (?:더 )?(?:중요|낫|필요)(?:해|하다|합니다|해요|하지|다)(?=[.!\s]|$)", {"S2": 1}, False,
     "대조 틀을 바꿔 끼운 것이다. B를 행동이나 사실로 바로 쓴다: '따지지 말고 아직 신경 쓰고 있다는 것만 보여 줘'.", {"flags": M}),
    ("KO-M7", "ko", "자소서 귀사 기여 결말", r"(?:귀사|귀 기관|貴社)(?:의|에서|에)? ?[^.!?\n]{0,40}(?:강점|기여|도움|보탬|자산|밑거름|원동력)(?:이|을|를|가)? ?(?:될|할|드릴|되리라|하리라) ?(?:수 있(?:다고|을 것이라고)|것이라고|것으로)? ?(?:생각|확신|믿|기대)|귀사(?:의|에)? [^.!?\n]{0,30}(?:기여하겠|이바지하겠|보탬이 되겠|도움이 되겠)", {"S2": 1}, False,
     "결산 표지만 지우고 끝내지 않는다. 원문에 직무와 맞닿은 다짐이 있으면 행동 한 문장으로 끝낸다. 없으면 지우고 [필자 확인]을 단다. 앞 문단의 수치·사건을 결말에서 되풀이하지 않는다.", {}),
    ("KO-M6", "ko", "일반화 주어 '우리는 보통/사람들은 흔히'", r"(?:우리는|사람들은|누구나) (?:보통|흔히|대개|종종|대부분) ", {"S2": 2, "S3": 1}, True,
     "대화체면 상대에게 건네는 구어로: '이럴 때 보통 내가 뭘 잘못했나 싶잖아'. 글이면 구체 주어로.", {}),
    # --- K. chatbot residue (KO) ---
    ("KO-K1", "ko", "아첨·칭찬", r"좋은 질문|핵심을 (?:찔렀|짚었|찌르)|정곡을 찔|예리(?:하신|한|하게) (?:질문|지적|관찰|보셨)|날카로운 (?:질문|지적|통찰)|정말 (?:훌륭|대단|멋진)|완전 잘하고|상위 \d+ ?%|틀린 (?:거|것|말) 하나도 없|혼자가 아니(?:에요|야|다)|감정은 (?:정당|당연)|(?:느끼는|하는) (?:너는|네가|당신은|당신이) (?:전혀 |하나도 |절대 )?이상하지 않|(?:고민하는|물어보는|털어놓는|걱정하는) (?:것|거)만 봐도|(?:충분히|이미) (?:좋은|잘하고 있는|훌륭한) (?:친구|사람|엄마|아빠|부모|동료|리더)", {"S1": 1}, False,
     "지운다. 평가는 내용으로 대신한다.", {}),
    ("KO-K2", "ko", "후속 제안·맺음 인사", r"(?:같이 |내가 )?(?:써|정리해|만들어|짜|찾아) ?줄까\?|원하시면|원하면 [^.\n]{0,20}(?:줄게|드릴게)|해 ?드릴까요|도와드릴까요|더 궁금한 (?:점|것)|도움이 (?:되셨|되었|됐)(?:길|으면)|언제든(?:지)? (?:물어|말씀|편하게|연락)|필요하시면 (?:말씀|알려)|궁금하신 점이 있으시면", {"S1": 1}, False,
     "지운다. 문서는 내용에서 끝낸다.", {}),
    ("KO-K3", "ko", "AI 정체·지식 기준 잔재", r"저는 (?:AI|인공지능|언어 ?모델)|(?:AI|인공지능|언어 ?모델)(?:로서|이기 때문에|이라서)|학습 (?:데이터|시점) 기준|제 지식(?:의)? (?:기준|범위|한계)|실시간 정보(?:에|를) (?:접근|확인)할 수 없", {"S1": 1}, False,
     "지운다.", {}),
    ("KO-K4", "ko", "첫머리 감탄 응답", r"^[ \t]*(?:물론이죠|물론입니다|좋습니다!|네, 알겠습니다|알겠습니다!|훌륭한 질문|와[,!] ?(?:이런|정말|진짜|그런|그거|너))", {"S1": 1}, False,
     "지우고 내용으로 시작한다.", {"flags": M}),
    # --- L. model-specific vocabulary ---
    ("KO-L1", "ko", "'기능하다'", r"(?:으로|로|서) 기능(?:한다|합니다|하는|하고|하며|할|했)", {"S2": 1}, False,
     "'~ 역할을 한다', '~로 쓰인다'로 바꾸거나 '~이다'로 단언한다.", {}),
    ("KO-L2", "ko", "GPT·Claude 계열 어휘", r"통찰력|(?:논리|설득력|주장|근거)(?:이|가|은|는)? (?:강해|약해)(?:진다|집니다)|미친 듯이|실무적 지침|(?:로|으로) 보는 (?:게|것이) 맞(?:다|습니다)|함께 (?:봅니다|살펴봅시다|살펴보겠습니다)|살펴보겠습니다|알아보겠습니다|(?:알아|살펴|정리해 ?|짚어 ?)볼게요|(?:알아|살펴)봐요|에 대해 (?:알아|살펴)봤(?:어요|습니다)|함께 (?:볼까요|알아봐요)|반은 맞고 반은 틀|상당히 [^.\n]{1,15}에 가깝|방어 가능(?:한|합니다)|짚어 ?드리|삶의 단계|기대치를 조정|자기 자신에게서 찾", {"S1": 3, "S2": 1}, False,
     "평범한 말로 바꾼다: '논리가 약해집니다' -> '설득력이 떨어집니다'.", {}),
    # --- J. decoration (KO) ---
    ("KO-J3", "ko", "긴 대시(—)", r"—|―|(?<=\s)--(?=\s)", {"S1": 3, "S2": 1}, False,
     "쉼표·괄호·문장 분리로 바꾼다. 한국어 글에서 드물어 눈에 띈다.", {}),
    ("KO-J4", "ko", "공백 둔 가운뎃점 나열", r"\S · \S", {"S3": 2}, False,
     "쉼표나 '와/과'로 잇는다. '성능·품질' 같은 붙임은 둔다.", {}),
    ("KO-J6", "ko", "굵게 표시가 조사와 붙어 깨질 위험", r"\*\*[^*\n]*[\"'”’)\]]\*\*[가-힣]", {"S2": 1}, False,
     "굵게를 빼거나 따옴표를 굵게 밖으로 뺀다.", {}),
    ("KO-F1", "ko", "정도부사 밀집", r"(?:^|(?<=\s))(?:매우|정말|굉장히|대단히|진정으로|진정한|무척|상당히)(?=\s)", {"S2": 6, "S3": 4}, True,
     "대부분 지운다. 필요하면 수치·비교로 바꾼다.", {"flags": M}),
    ("KO-F5", "ko", "'~적 N' 추상 연쇄", r"[가-힣]{1,5}적(?:인)? (?:함의|토대|기반|가치|의미|접근|관점|전환|변화|역할|측면|차원|맥락)", {"S2": 3, "S3": 2}, True,
     "명사+명사로 줄이거나 풀어 쓴다: '전략적 함의' -> '전략에 주는 뜻'.", {}),
    ("KO-F7", "ko", "범용 정책 동사 밀집", r"(?:강화|확대|개선|확보|마련|구축|제고|활성화)(?:하|해|할|한|되|됩|됐|했)", {"S2": 6, "S3": 4}, True,
     "구체 행위 동사로 해체한다.", {}),
]

EN_RULES = [
    ("EN-A1", "en", "significance inflation", r"\b(?:stands?|serves?|stood|served) as (?:a |an |the )?(?:testament|reminder|symbol|beacon|cornerstone|catalyst)\b|\b(?:is|was|remains|stands as) a testament to\b|\bplay(?:s|ed|ing)? (?:a |an )?(?:crucial|pivotal|vital|key|significant|central|instrumental) role\b|\bmark(?:s|ed|ing)? (?:a |an )?(?:pivotal|significant|key|major|new) (?:moment|shift|turning point|milestone|chapter|era)\b|\bsetting the stage for\b|\b(?:is|was|marks) a (?:pivotal|defining|historic|watershed) moment\b|\bindelible mark\b|\b(?:ever-)?evolving landscape\b|\bdeeply rooted\b|\breflect(?:s|ed|ing)? (?:the |a )?broader\b|\bunderscor(?:es|ed|ing) (?:the |its |their )?(?:importance|significance|need)\b|\bhighlight(?:s|ed|ing)? the importance\b|\b(?:enduring|lasting) (?:legacy|impact|influence)\b|\bfocal point\b|\bturning point\b|\bfor (?:future )?generations to come\b|\bcontinues? to (?:thrive|flourish)\b|\bdeep(?:ly)? (?:commitment|connection|sense of)\b|\bcherished\b|\bvital (?:link|part|component)\b|\bhas evolved over the (?:years|decades|centuries)\b|\b(?:transformative|pivotal|crucial|vital|central) role (?:that )?[\w' ]{1,30}? play(?:s|ed)?\b|\btransformative (?:power|impact|potential|experience)\b", {"S1": 3, "S2": 1}, True,
     "Say what happened. Drop the legacy claim unless a source makes it.", {"flags": I}),
    ("EN-A2", "en", "'X matters because'", r"\b(?:this|that|it|which|the (?:distinction|difference|shift)) matters because\b|\bwhy (?:this|it|that) matters\b", {"S2": 1}, False,
     "Cut the announcement; give the consequence itself.", {"flags": I}),
    ("EN-A3", "en", "trailing -ing analysis", r",\s(?:thereby\s|further\s)?(?:highlighting|underscoring|emphasizing|reflecting|symbolizing|showcasing|ensuring|fostering|cementing|solidifying|reinforcing|illustrating|signaling|signalling|paving the way|contributing to|marking|making (?:it|them|this)|allowing|enabling)\b|\b(?:and|while) (?:fostering|highlighting|showcasing|underscoring|ensuring|cementing|reinforcing)\b", {"S1": 4, "S2": 2, "S3": 1}, True,
     "End the sentence at the fact. Move any real effect into its own sentence with a source.", {"flags": I}),
    ("EN-A4", "en", "promotional register", r"\bnestled\b|\bin the heart of\b|\bboasts?\b|\bbreathtaking\b|\brich (?:cultural |culinary )?(?:heritage|history|tapestry|tradition)\b|\bvibrant (?:communit(?:y|ies)|cultures?|cit(?:y|ies)|scenes?|hubs?|neighbou?rhoods?|spaces?|centers?|centres?)\b|\bmust-visit\b|\bhidden gem\b|\bworld-class\b|\bcutting-edge\b|\bstate-of-the-art\b|\bgame[- ]?chang(?:er|ing)\b|\brevolutioniz(?:e|es|ed|ing)\b|\bunlock(?:s|ing)? (?:the |your )?(?:full )?(?:potential|power)\b|\bseamless(?:ly)?\b|\belevate(?:s|d)? (?:your|the)\b|\btake (?:it|your \w+) to the next level\b", {"S1": 4, "S2": 2}, True,
     "Replace with a checkable detail (size, date, price, who uses it).", {"flags": I}),
    ("EN-A5", "en", "challenges-and-future formula", r"\bdespite (?:its|these|their|the|such) [^.\n]{0,40}?(?:challenges|setbacks|obstacles|limitations|hurdles)\b|\bfaces? (?:several|numerous|many|significant|a number of) (?:challenges|obstacles|hurdles)\b|\bfuture (?:prospects|outlook)\b|\bremains to be seen\b|\bonly time will tell\b|\btime will tell\b|\bdelivers? on (?:its|their) promise\b|\bwill become clearer\b", {"S1": 3, "S2": 1}, False,
     "Name the actual problem and stop. No vague optimism.", {"flags": I}),
    ("EN-A6", "en", "stock research/press phrases", r"\bsheds? (?:new )?light on\b|\bpaves? the way\b|\bpromising (?:tool|avenue|approach|step|option|strategy|solution)\b|\ba growing body of (?:evidence|research|literature)\b|\bopens? (?:up )?(?:new )?(?:avenues|doors|possibilities)\b|\bone (?:such|simple|key|small|surprising) [a-z]+(?: [a-z]+){0,3}: |\bgame plan\b|\bthe key takeaway\b", {"S1": 3, "S2": 1}, False,
     "Say what was done or found: 'sheds light on X' -> 'tested whether X'. Keep the hedge.", {"flags": I}),
    ("EN-D7", "en", "conclusion / evaluative section headings", r"^#{1,6}[ \t]*(?:conclusion|in conclusion|summary|final thoughts|key takeaways|wrapping up|challenges|legacy|future (?:prospects|outlook)|challenges and (?:opportunities|future|prospects)|impact and legacy|the perfect choice|why choose [\w ]+|why you\'ll love (?:it|this)|final verdict|the bottom line|our verdict)[ \t]*$", {"S3": 1}, False,
     "Delete the heading in short texts, or rename it after the actual subject (e.g. 'Demographics and transport'). Check the paragraph still fits the heading above.", {"flags": I | M}),
    ("EN-C1d", "en", "comparative maxim ('X matters more than Y')", r"\b(?:getting it right|showing up[\w ]{0,20}|consistency|progress|[\w-]+ing it \w+) matters? more than\b", {"S2": 2, "S3": 1}, False,
     "A maxim set against its opposite. Keep the claim as a plain statement tied to the text, or cut it if it repeats an earlier point.", {"flags": I}),
    ("EN-D4", "en", "rhetorical question answered at once", r"\bSo,? what(?:'s| is| does) (?:the (?:right |real )?answer|this mean|that mean)\?|\b(?:the truth|the reality|the answer) is,? it'?s complicated\b", {"S2": 1}, False,
     "Make the statement directly. Delete 'The truth is, it's complicated.'", {"flags": I}),
    ("EN-D9", "en", "moralising closer with abstract triplet ('X deserve a thoughtful, transparent, and … process')", r"\b(?:deserves?|need|needs|calls? for|requires?) (?:a |an |the )?[\w-]+, [\w-]+,? and [\w-]+ (?:process|approach|conversation|plan|debate|discussion|solution|future)\b", {"S2": 1}, False,
     "After cutting a closing label, check the new last sentence. End on the concrete recommendation or a fact from the text.", {"flags": I}),
    ("EN-F4", "en", "declared balance ('equally important concerns')", r"\bequally (?:important|valid|compelling|legitimate|serious) (?:concerns?|points?|arguments?|questions?)\b|\bjust as (?:compelling|valid|important)\b|\bboth sides (?:make|have|raise) (?:valid|good|compelling|strong) points\b", {"S2": 1}, False,
     "State what the concern is instead of declaring it equal. Keep the writer's balance only if no other sentence carries it.", {"flags": I}),
    ("EN-C1c", "en", "contrast rebuilt as a short pair ('X is new. Y is not.')", r"\b(?:is|are|was|were) [\w-]+\.\s+(?:The |Their |His |Her |My |Our |Its )?[\w' ]{1,40}? (?:is|are|was|were|did|do|does) not\.|\b(?:is|are|was|were) [\w-]+\.\s+(?:The |Their |His |Her |My |Our |Its )?[\w' ]{1,40}? (?:isn't|aren't|wasn't|weren't|didn't|don't|doesn't)\.", {"S2": 1}, False,
     "This is the same contrast in a new shape. Write the information once as a plain sentence, or cut the maxim.", {}),
    ("EN-C1b", "en", "two-sentence contrast ('X isn't A. It's B.')", r"\b(?:isn't|is not|wasn't|was not|aren't|are not|it's not|that's not) (?:just |only |merely |about )?[^.!?\n]{1,60}\.\s+(?:It|This|That|They|He|She)(?:'s| is| was| are)\b", {"S2": 1}, False,
     "Abstract reframe -> state B, and keep A as its own plain clause if A carries information. A concrete correction in a personal story is voice; keep it.", {"flags": I}),
    ("EN-H4", "en", "social-post formula (announcement / engagement bait)", r"\bI'?m (?:so )?(?:humbled|thrilled|excited|honored|honoured|proud|delighted) to (?:share|announce)\b|\b(?:share|post|tell me|let me know)(?: it| yours| them| your \w+)? in the comments\b|\bdrop (?:it|them|a comment|your thoughts|your answer)s? (?:in|below)\b|\blet me know in the comments\b|\btag someone who\b|\b(?:repost|share) (?:this )?if you\b|\bthis is your sign to\b|(?:^|(?<=[.!?] ))(?:Agree|Thoughts)\?[ \t]*$", {"S1": 1}, False,
     "State the fact plainly ('Today I became Head of Operations.'). Delete bait closers, or keep one plain question if the author wants replies.", {"flags": I | M}),
    ("EN-H5", "en", "hook opener", r"\bI (?:almost|nearly) didn'?t (?:post|share|write) this\b|\bI never thought I'?d (?:share|post|say)\b|\bthis one'?s personal\b|\bunpopular opinion:|\bhot take:|\bstory time:", {"S2": 1}, False,
     "Drop the hook unless the post later explains it.", {"flags": I}),
    ("EN-A7", "en", "product-copy stock phrases", r"\bwhether you'?re [^.,\n]{1,40}(?:,| or )|\bwithout compromising(?: on)?\b|\bdelivers? (?:all-day|unmatched|exceptional|superior|outstanding|reliable|effortless)\b|\bensures? (?:that )?(?:your|you)\b|\balways within reach\b|\bwhen the skies turn\b|\bdesigned with you in mind\b|\bthe perfect (?:choice|companion|solution|blend|balance)\b|\bstands? the test of time\b|\bpeace of mind\b|\bwhere [\w ]{1,20} meets [\w ]{1,20}\b", {"S1": 3, "S2": 1}, False,
     "Replace with the checkable fact ('It weighs 940 g.'). Apply the same standard to list items as to prose.", {"flags": I}),
    ("EN-C1", "en", "negative parallelism ('not X, but Y')", r"\bnot (?:just|only|merely|simply) (?:a |an |the )?[^.;:!?\n]{1,60}?,? but\b|\b(?:it|this|that)(?:'s| is| was) not (?:just |only |merely |about )?[^.;:!?\n]{1,50}?[,;—–-]+\s*(?:it|this|that)(?:'s| is| was)\b|\b(?:isn't|aren't|wasn't|weren't) (?:just |only |merely )?(?:a |an |the )?[^.;:!?\n]{1,80}?[,;—–]\s*(?:it|they|this)(?:'s| is| are| was)\b|\bgoes? (?:far )?beyond [^.;:!?\n]{1,40}?\s?[—–;,]\s*(?:it|this|that)(?:'s| is)\b|^#{1,6}[^\n]{3,80}?, [Nn]ot (?:a |an |the )?[\w ]{2,30}$|(?<![\s\S])[^\n.!?]{3,80}?, [Nn]ot (?:a |an |the )?[\w ]{2,30}$|\b(?:didn\'t|doesn\'t|don\'t|did not|does not|do not) just [^.!?\n]{1,50}?\s?[—–;,]\s*(?:she|he|they|it|we|I|you)\b|\b(?:is|are|was|were) not (?:just|only|merely|simply) [^.;:!?\n]{1,60}?[;,—–]\s*(?:it|they|this|these|he|she|we)(?:'s|'re| is| are| was| were)\b|\bmore than (?:just|merely|simply) (?:a|an)\b|\b(?:rather than|instead of) (?:merely|just|simply)\b|\bnot simply\b|\bless (?:like|about) (?:a |an )?[^.\n]{1,40}? and more (?:like|about)\b|(?:^|(?<=[.!?] ))Not (?:a |an |the )?[^.\n]{1,40}\.\s+Not (?:a |an |the )?[^.\n]{1,40}\.", {"S1": 1}, False,
     "State Y directly. For 'not only X but also Y', keep both facts and join them with 'and'. Keep the contrast only where you correct an earlier claim.", {"flags": I | M}),
    ("EN-C2", "en", "corrective framing ('should be treated as X rather than Y')", r"\bshould be (?:treated|seen|understood|read|viewed|considered) as [^.\n]{1,60}? rather than\b|\bdoes(?: not|n't) (?:by itself|on its own|alone) (?:establish|prove|mean|show|confirm)\b|\bshould not be confused with\b", {"S1": 2, "S2": 1}, False,
     "Say what the thing is. Drop the pre-emptive correction.", {"flags": I}),
    ("EN-C3", "en", "'rather than' density", r"\brather than\b", {"S2": 3, "S3": 2}, True,
     "Keep one. Rewrite the others as direct statements.", {"flags": I}),
    ("EN-D1", "en", "summary closer", r"(?:^|(?<=[.!?] ))(?:In conclusion|In summary|To sum up|To summarize|All in all|In short|Overall|Ultimately),", {"S1": 2, "S2": 1}, False,
     "Delete the label. The last paragraph is the conclusion.", {"flags": M}),
    ("EN-E1", "en", "copula avoidance ('serves as', 'boasts')", r"\b(?:serves|served|stands|stood|functions|functioned) as (?:a|an|the)\b|\bboasts\b|\brefers to\b", {"S2": 3, "S3": 2}, True,
     "Use is/has: 'serves as a hub' -> 'is a hub'.", {"flags": I}),
    ("EN-F1", "en", "vague attribution", r"\b(?:experts|scholars|critics|observers|analysts|historians|many people|some people) (?:say|argue|agree|believe|suggest|note|have noted|have argued|contend|point out|warn|caution|stress|maintain)\b|\bstudies (?:show|suggest|have shown)\b|\bit is (?:widely |generally |often )?(?:believed|thought|said|considered|recognized) that\b|\bindustry reports\b|\bobservers have (?:cited|noted)\b|\bwidely (?:regarded|considered|recognized) as\b", {"S1": 3, "S2": 1}, False,
     "Name the source or cut the claim.", {"flags": I}),
    ("EN-F2", "en", "false agency", r"\bthe (?:data|numbers|research|evidence|market|culture|story|history) (?:tells|shows|reveals|rewards|demands)\b|\b(?:decision|consensus|answer|picture|pattern) emerges\b|\bthe conversation (?:shifts|moves)\b", {"S2": 2, "S3": 1}, True,
     "Name the person who acts: 'the data tells us' -> 'we read the data and saw'.", {"flags": I}),
    ("EN-G1", "en", "throat-clearing / signposting", r"\bhere'?s the (?:thing|kicker|deal|catch|truth|problem|breakdown)\b|\bhere'?s (?:what|why|how) (?:you|it|this|that|I|we)\b|\blet'?s (?:dive|delve|break (?:it|this) down|unpack|explore|take a (?:closer )?look)\b|\blet me (?:be clear|be honest|walk you|break (?:it|this) down)\b|\bit turns out\b|\bthe (?:truth|reality|bottom line) is\b|\bmake no mistake\b|\blet that sink in\b|\bfull stop\b|\bin (?:this|today'?s) (?:article|post|guide|section|blog)\b|\bit'?s (?:worth|important to) (?:noting|note|mention|remember)\b|\bat its core\b|\bin today'?s (?:fast-paced|digital|ever-changing|modern|rapidly)\b|\bin today'?s [\w-]+ (?:world|age|era|society|environment|landscape|climate)\b|\bwhen it comes to\b|\bat the end of the day\b|\bin a world where\b|\band honestly\?|\bno fluff\b|\bshort answer:", {"S1": 3, "S2": 1}, False,
     "Delete and start with the point.", {"flags": I}),
    ("EN-H1", "en", "chatbot residue / sycophancy", r"^[ \t]*(?:certainly|absolutely|great question)[!.,]|(?<![\s\S])[ \t\n]*(?:of course|sure thing)[!.,]|\bgreat question\b|\byou'?re absolutely right\b|\bwhat a (?:great|fantastic|wonderful) (?:question|idea)\b|\bI hope this helps\b|\blet me know if\b|\bfeel free to\b|\bwould you like me to\b|\bhappy to help\b|\bas an AI\b|\bas a (?:large )?language model\b|\bas of my (?:last|latest) (?:knowledge|training) (?:update|cutoff)\b|\bI (?:don'?t|do not) have (?:personal|real-time)\b|\bhere is (?:a|an|the) (?:revised|updated|rewritten|polished|wikipedia-style)\b", {"S1": 1}, False,
     "Delete. Documents do not talk to the requester.", {"flags": I | M}),
    ("EN-H7", "en", "customer-service stock phrases", r"\brest assured\b|\b(?:your|customer) satisfaction is our (?:top |number one |highest |first )?priority\b|\bdon'?t hesitate to (?:reach out|contact)\b|\bwe (?:truly |really |greatly )?(?:value|appreciate) your (?:business|loyalty)\b|\bI (?:completely|totally|fully) understand how (?:frustrating|disappointing|upsetting|stressful)\b|\bwe take (?:this|these|your|such) [\w ]{0,25}?(?:very )?seriously\b|\bapologi[sz]e for (?:any|the) inconvenience\b|\bto make (?:things|it|this) right\b|\blook forward to serving you\b", {"S1": 4, "S2": 2, "S3": 1}, False,
     "Keep one apology and the real offer. Cut reassurance formulas that carry no fact. Keep real requests to the customer ('Please let me know which option works').", {"flags": I}),
    ("EN-H2", "en", "therapist mode", r"\byou'?re not (?:alone|broken|imagining (?:it|things)|crazy|weak)\b|\btake a (?:deep )?breath\b|\bit'?s (?:okay|ok|completely normal|perfectly normal) to\b|\byour feelings are (?:valid|completely valid)\b|\bsit with that\b|\byou'?re right to (?:push back|question)\b", {"S1": 1}, False,
     "Delete. Answer the actual problem.", {"flags": I}),
    ("EN-H3", "any", "tool residue / placeholders", r"\[(?:Your|Insert|Company|Name|Date|Title|Link|Author|Product)[^\]\n]{0,40}\]|\b20\d\d-XX-XX\b|utm_source=(?:chatgpt\.com|openai|copilot\.com)|turn\d+(?:search|news|image|file)\d+|oaicite|contentReference\[|\[cite: ?\d+\]|grok-card|【\d+†", {"S1": 1}, False,
     "Remove the artifact; fill or delete the placeholder.", {"raw": True}),
    ("EN-I1", "en", "source-availability disclaimer", r"\b(?:while|although) (?:specific )?(?:details|information) (?:are|is|remain) (?:limited|scarce|not widely (?:available|documented))\b|\bnot widely (?:documented|reported|available)\b|\bbased on (?:the )?(?:available|provided) (?:information|sources|search results)\b|\bmaintains a low profile\b", {"S1": 1}, False,
     "State what is known; cut speculation about what is unknown.", {"flags": I}),
    ("EN-I2", "en", "stacked hedges", r"\b(?:may|might|could) (?:potentially|possibly|perhaps)\b|\b(?:potentially|possibly) (?:could|might|may)\b|\bit (?:could|might|may) be argued that\b|\bit seems (?:likely|possible) that\b", {"S1": 2, "S2": 1}, False,
     "Keep one hedge at the original strength.", {"flags": I}),
    ("EN-K1", "en", "em dash", r"—|(?<=\s)–(?=\s)|(?<=\w) -- (?=\w)", {"S2": 2, "S3": 1}, True,
     "One dash per ~300 words is fine. Above that, use commas, parentheses, colons or a new sentence; vary them.", {}),
    ("EN-M1", "en", "AI-favoured adverbs", r"\b(?:quietly|deeply|fundamentally|truly|genuinely|incredibly|profoundly|inherently|seamlessly|undeniably|notably|crucially|importantly|essentially|remarkably)\b", {"S2": 5, "S3": 3}, True,
     "Cut these specific adverbs. Plain 'very', 'perhaps', 'tends to' are human signals; leave them.", {"flags": I}),
    ("EN-M3", "en", "cover-letter stock phrases", r"\bI am writing to express my (?:keen |strong |sincere |deep |great )?interest\b|\bpassionate advocate for\b|\b(?:skills|values|experience|background)(?: and (?:skills|values|experience|background))? align(?: \w+ly)? with (?:your|the (?:company|organization)'s) (?:mission|values|goals|vision)\b|\bpositions? me (?:well|perfectly|uniquely|ideally) to\b|\bfrom day one\b|\bdynamic team\b|\bcontinued success\b|\bbring a (?:genuine|unique|fresh) (?:enthusiasm|perspective|passion)\b|\bI look forward to the (?:possibility|opportunity) of\b|\bwould welcome the opportunity to discuss\b|\bwhat excites me most about [\w' ]{1,40}? is (?:your|its|the)\b", {"S1": 5, "S2": 3, "S3": 1}, False,
     "Keep one genre opener and one closing line. Replace stock self-description with a fact from the letter, or cut it. Keep the claims inside (confidence, fit, motive) in plain words. Keep the writer's stated degree ('had a central part in developing'; not 'developed', not 'helped').", {"flags": I}),
    ("EN-M4", "en", "stock self-deprecation", r"\bI have a (?:real |special |rare )?(?:talent|gift|knack) for\b|\bwhich I'?m (?:counting|calling|taking) as a win\b|\bask me how I know\b|\bspoiler(?: alert)?:|\bnarrator:|\breader, I\b", {"S2": 2, "S3": 1}, False,
     "One stock self-deprecating line per piece. Make the rest specific to what happened.", {"flags": I}),
    ("EN-M2", "en", "'quiet(ly)' as mood word", r"\bquiet(?:ly)? (?:confidence|rebellion|revolution|power|strength|resilience|dignity)\b", {"S2": 1}, False,
     "Describe the behaviour instead.", {"flags": I}),
]

ANY_RULES = [
    ("AN-J1", "any", "bold density", r"\*\*[^*\n]{1,80}\*\*", {"S2": 5, "S3": 3}, True,
     "Keep bold for headings or one key term per section.", {}),
    ("AN-J2", "any", "bold inline-header list items", r"^[ \t]*(?:[-*•]|\d+\.)[ \t]+\*\*[^*\n]{1,40}\*\*", {"S2": 4, "S3": 2}, True,
     "Turn into prose, or keep plain list items without bold labels.", {"flags": M}),
    ("AN-J6", "any", "stock hype emoji", "[\U0001F680\U0001F525\u2728\U0001F4AF\U0001F64C\U0001F447\U0001F4A1\u2705\U0001F449\U0001F389\U0001F4AA\U0001F64F\U0001F4CC\U0001F539\U0001F538\u27A1\U0001F31F\u2B50]", {"S2": 1}, False,
     "Remove in every genre, social posts included. Keep at most one emoji that carries meaning.", {}),
    ("AN-J5", "any", "emoji (other than stock hype emoji)", "(?![\U0001F680\U0001F525\u2728\U0001F4AF\U0001F64C\U0001F447\U0001F4A1\u2705\U0001F449\U0001F389\U0001F4AA\U0001F64F\U0001F4CC\U0001F539\U0001F538\u27A1\U0001F31F\u2B50'])[\U0001F300-\U0001FAFF⌚⌛⌨⏏⏩-⏳⏸-⏺☀-⛿✀-➿⭐⭕✅❌✔✨]", {"S1": 3, "S2": 1}, False,
     "Delete in reports, essays, articles, mail, wiki and product pages. Social posts and YouTube descriptions may keep one per section header (--genre sns); messenger texts may keep one or two (--genre chat).", {}),
]

AI_VOCAB_EN = [
    "delve", "delves", "delving", "tapestry", "testament", "pivotal", "underscore", "underscores",
    "underscoring", "showcase", "showcases", "showcasing", "intricate", "intricacies", "meticulous",
    "meticulously", "vibrant", "bolster", "bolstered", "garner", "garnered", "interplay", "enduring",
    "foster", "fosters", "fostering", "enhance", "enhances", "enhancing", "crucial", "realm",
    "robust", "seamless", "leverage", "leveraging", "multifaceted", "dependable", "commendable",
    "camaraderie", "embark", "navigate", "navigating", "landscape", "paramount", "nuanced",
    "holistic", "synergy", "streamline", "unwavering", "resonate", "resonates", "elevate",
    "fostered", "seamlessly", "resonated", "resonating", "showcased", "navigated", "elevates", "elevated",
    "elevating", "leveraged", "leverages", "streamlined", "streamlines", "enhanced", "embarked", "embarking",
    "underscored", "garnering", "bolstering", "bolsters", "delved", "tapestries",
]
_EN_LEMMA_GROUPS = [
    ("delve", "delves", "delving", "delved"), ("underscore", "underscores", "underscoring", "underscored"),
    ("showcase", "showcases", "showcasing", "showcased"), ("intricate", "intricacies"),
    ("meticulous", "meticulously"), ("bolster", "bolstered", "bolstering", "bolsters"),
    ("garner", "garnered", "garnering"), ("foster", "fosters", "fostering", "fostered"),
    ("enhance", "enhances", "enhancing", "enhanced"), ("seamless", "seamlessly"),
    ("leverage", "leveraging", "leveraged", "leverages"), ("embark", "embarked", "embarking"),
    ("navigate", "navigating", "navigated"), ("streamline", "streamlined", "streamlines"),
    ("resonate", "resonates", "resonated", "resonating"), ("elevate", "elevates", "elevated", "elevating"),
    ("tapestry", "tapestries"),
]
EN_LEMMA = {w: g[0] for g in _EN_LEMMA_GROUPS for w in g}

KO_CONNECTIVES = ["그러나", "또한", "따라서", "게다가", "더욱이", "나아가", "한편", "그리고", "하지만", "이와 함께", "아울러", "특히"]
EN_SMALL = {"a", "an", "the", "and", "or", "of", "in", "on", "for", "to", "with", "at", "by", "from", "as"}

HANGUL = re.compile(r"[가-힣]")
LATIN = re.compile(r"[A-Za-z]")
EN_WORD = re.compile(r"[A-Za-z][A-Za-z'\-]*")


def read_text(path: str) -> str:
    if path == "-":
        data = sys.stdin.buffer.read()
    else:
        with open(path, "rb") as f:
            data = f.read()
    text = data.decode("utf-8-sig", errors="replace")
    return normalize(text)


def normalize(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return unicodedata.normalize("NFC", text)


def mask(text: str, skip_quotes: bool = False) -> str:
    """Blank out code, URLs and HTML comments (and optionally quotes), keeping offsets."""
    pats = [r"```.*?```", r"~~~.*?~~~", r"`[^`\n]+`", r"https?://\S+", r"\bwww\.\S+", r"<!--.*?-->",
            r"\[(?:필자 확인|출처 필요|writer to confirm|writer check|source needed)[^\]\n]{0,160}\]"]
    if skip_quotes:
        dq = [r"\u201c[^\u201d\n]*\u201d", r'"[^"\n]*"']
        if skip_quotes == "double":
            pats += dq
            skip_quotes = False
    if skip_quotes:
        pats += [r"“[^”\n]*”", r'"[^"\n]*"', r"「[^」\n]*」", r"『[^』\n]*』",
                 r"‘[^’\n]*’", r"'(?=[^'\n]*[가-힣])[^'\n]{1,80}'"]
    out = list(text)
    # news dateline ("PORT CALDER — The council...") is a format convention, not a dash habit
    for m in re.finditer(r"^[A-Z][A-Z .,'\-]{1,40} \u2014", text, re.M):
        out[m.end() - 1] = " "
    for p in pats:
        for m in re.finditer(p, text, re.S):
            for i in range(m.start(), m.end()):
                if out[i] != "\n":
                    out[i] = " "
    return "".join(out)


class Doc:
    def __init__(self, text: str, lang: str = "auto", skip_quotes: bool = False):
        self.raw = normalize(text)
        self.text = mask(self.raw, skip_quotes)
        self.line_starts = [0] + [m.end() for m in re.finditer("\n", self.text)]
        self.lines = self.raw.split("\n")
        self._assign_lang(lang)

    def _assign_lang(self, lang: str):
        n = len(self.lines)
        self.line_lang = ["none"] * n
        i = 0
        masked_lines = self.text.split("\n")
        while i < n:
            if not masked_lines[i].strip():
                i += 1
                continue
            j = i
            while j < n and masked_lines[j].strip():
                j += 1
            para = "\n".join(masked_lines[i:j])
            if lang in ("ko", "en"):
                pl = lang
            else:
                h = len(HANGUL.findall(para))
                l = len(LATIN.findall(para))
                if h >= 2 and h * 2 >= l:
                    pl = "ko"
                elif l >= 3:
                    pl = "en"
                else:
                    pl = "none"
            for k in range(i, j):
                self.line_lang[k] = pl
            i = j
        # keep one entry per original line (blank for other languages) so paragraph breaks survive
        ko_lines = [masked_lines[k] if self.line_lang[k] == "ko" else "" for k in range(n)]
        en_lines = [masked_lines[k] if self.line_lang[k] == "en" else "" for k in range(n)]
        self.ko_text = "\n".join(ko_lines)
        self.en_text = "\n".join(en_lines)
        self.ko_chars = len(HANGUL.findall(self.ko_text))
        self.en_words = len(EN_WORD.findall(self.en_text))
        self.total_chars = len(re.sub(r"\s", "", self.text))

    def line_of(self, pos: int) -> int:
        return bisect.bisect_right(self.line_starts, pos) - 1

    def lang_at(self, pos: int) -> str:
        ln = self.line_of(pos)
        return self.line_lang[ln] if 0 <= ln < len(self.line_lang) else "none"

    def units(self, lang: str) -> float:
        if lang == "ko":
            return max(1.0, self.ko_chars / KO_UNIT)
        if lang == "en":
            return max(1.0, self.en_words / EN_UNIT)
        return max(1.0, self.total_chars / KO_UNIT)


def snippet(line: str, col: int = 0, width: int = 70) -> str:
    """Return up to `width` chars of `line` around column `col`."""
    if len(line) <= width:
        return line.strip()
    lo = max(0, min(col - width // 3, len(line) - width))
    part = line[lo:lo + width].strip()
    return ("…" if lo > 0 else "") + part + ("…" if lo + width < len(line) else "")


def _severity(count: int, levels: dict, mult: float) -> str | None:
    best = None
    for sev in ("S3", "S2", "S1"):
        need = levels.get(sev)
        if need is None:
            continue
        if count >= math.ceil(need * mult):
            best = sev
    return best


def run_regex_rules(doc: Doc, rules, results: dict, counts: dict, max_items: int):
    for rid, lang, name, pat, levels, scale, hint, opts in rules:
        flags = opts.get("flags", 0)
        src = doc.raw if opts.get("raw") else doc.text
        items = []
        count = 0
        for m in re.finditer(pat, src, flags):
            pos = m.start()
            plang = doc.lang_at(pos)
            if lang != "any" and plang != lang:
                continue
            if rid == "EN-F1" and re.search(r"\[(?:source needed|출처 필요)", doc.lines[doc.line_of(pos)], re.I):
                continue  # already handed to the writer
            if opts.get("connective"):
                word = m.group(1) + m.group(2)
                if word in NOUN_GO_AMBIG or word.endswith(NOUN_GO_T):
                    continue
            count += 1
            if len(items) < max_items:
                ln = doc.line_of(pos)
                col = pos - doc.line_starts[ln]
                items.append({"line": ln + 1, "match": m.group(0).strip()[:40], "text": snippet(doc.lines[ln], col)})
        counts[rid] = count
        if count == 0:
            continue
        mult = doc.units(lang if lang != "any" else "any") if scale else 1.0
        sev = _severity(count, levels, mult)
        if sev:
            results[rid] = {"id": rid, "sev": sev, "name": name, "count": count, "hint": hint, "items": items,
                            "esc": _escalated(sev, levels)}


def _escalated(sev: str, levels: dict) -> bool:
    """True when the rule reached this severity only because of the match count."""
    first = min(levels, key=lambda k: levels[k]) if levels else sev
    return SEV_RANK[sev] < SEV_RANK[first]


def split_sentences(text: str, lang: str):
    sents = []
    for line in text.split("\n"):
        s = line.strip()
        if not s or s.startswith("#") or s.startswith("|"):
            continue
        s = re.sub(r"^(?:[-*•>]|\d+[.)])\s+", "", s)
        parts = re.split(r"(?<=[.!?…])\s+", s) if lang == "ko" else re.split(r"(?<=[.!?])\s+(?=[A-Z\"“(])", s)
        for p in parts:
            p = p.strip()
            if len(p) >= 5:
                sents.append(p)
    return sents


def ko_ending(sent: str) -> str | None:
    body = re.sub(r"[^가-힣]+$", "", sent)
    if not body or not re.search(r"[.!?]$", sent.strip()):
        return None
    tail = HANGUL.findall(body[-4:])
    if len(tail) < 2:
        return None
    key = "".join(tail[-2:])
    # 합쇼체 '-니다' and 해요체 '-요' close almost every sentence; compare one more syllable
    if key in ("니다", "니까") and len(tail) >= 4:
        key = "".join(tail[-4:])
    elif (key in ("니다", "니까") or key.endswith("요")) and len(tail) >= 3:
        key = "".join(tail[-3:])
    return key


def run_function_rules(doc: Doc, results: dict, counts: dict, max_items: int):
    # KO-E2: same ending in 5+ consecutive sentences
    ko_s = split_sentences(doc.ko_text, "ko")
    runs, run, prev, run_examples = 0, 1, None, []
    for s in ko_s:
        e = ko_ending(s)
        if e and e == prev:
            run += 1
            if run == 5:
                runs += 1
                if len(run_examples) < max_items:
                    run_examples.append({"line": 0, "match": e, "text": snippet(s)})
        else:
            run = 1
        prev = e
    counts["KO-E2"] = runs
    if runs:
        results["KO-E2"] = {"id": "KO-E2", "sev": "S2" if runs >= 2 else "S3", "name": "같은 종결어미 5문장+ 연속",
                            "count": runs, "hint": "종결 형태를 섞는다. 격식(합쇼·해요·해라)은 바꾸지 않는다.", "items": run_examples}
    # KO-E1 / EN-L1: uniform rhythm
    for rid, lang, sents, long_thr in (("KO-E1", "ko", ko_s, 100), ("EN-L1", "en", split_sentences(doc.en_text, "en"), 30)):
        if len(sents) < 8:
            counts[rid] = 0
            continue
        lens = [len(s) if lang == "ko" else len(EN_WORD.findall(s)) for s in sents]
        mean = statistics.mean(lens)
        cv = statistics.pstdev(lens) / mean if mean else 0
        longs = sum(1 for x in lens if x >= long_thr)
        flag = cv < 0.3 and longs == 0
        counts[rid] = 1 if flag else 0
        if flag:
            results[rid] = {"id": rid, "sev": "S3", "name": "uniform sentence rhythm" if lang == "en" else "문장 길이 균일·장문 없음",
                            "count": 1, "hint": "Merge two short sentences or split one long one. Add no content." if lang == "en"
                            else "문장 길이가 고르고(cv<0.3) 100자 넘는 문장이 없다. 인접 문장을 이어 긴 문장 하나를 만들거나 짧은 문장 하나를 섞는다. 내용은 더하지 않는다.",
                            "items": [{"line": 0, "match": f"cv={cv:.2f}", "text": f"{len(sents)} sentences, mean {mean:.0f}"}]}
    paras = [p for p in re.split(r"\n\s*\n", doc.ko_text) if p.strip()]
    # KO-E3: a paragraph with 3+ same endings in a row that is wrapped up with '결국/결과적으로',
    #        or the same '~ㄹ 것이다' predicate 3+ times in one paragraph
    blocks, ex = 0, []
    for p in paras:
        sents = split_sentences(p, "ko")
        keys = [ko_ending(x) for x in sents]
        best, run = 1, 1
        for i in range(1, len(keys)):
            run = run + 1 if keys[i] and keys[i] == keys[i - 1] else 1
            best = max(best, run)
        preds = Counter(re.findall(r"([가-힣]+) 것(?:이다|이고|이며|입니다|이라)", p))
        rep_pred = [w for w, c in preds.items() if c >= 3]
        if (best >= 3 and re.search(r"결국|결과적으로", p)) or rep_pred:
            blocks += 1
            if len(ex) < max_items:
                what = f"'{rep_pred[0]} 것' x{preds[rep_pred[0]]}" if rep_pred else f"같은 종결 {best}연속 + 결국"
                ex.append({"line": 0, "match": what, "text": snippet(p.replace(chr(10), " "))})
    counts["KO-E3"] = blocks
    if blocks:
        results["KO-E3"] = {"id": "KO-E3", "sev": "S2", "name": "같은 서술 반복 + 결산 덩어리", "count": blocks,
                            "hint": "첫 문장과 결산 문장이 같은 말인지 본다. 같으면 원인과 결과를 한 문장으로 합친다. 쉼표만 고치고 넘어가지 않는다.",
                            "items": ex}
    # KO-I4: paragraphs that END on an ought/importance sentence (first one is free)
    ought_end = re.compile(r"(?:(?:(?!이)[가-힣])야 ?(?:한다|합니다|해요|할 것이다)|필요가 있(?:다|습니다)|필요(?:하다|합니다|해요)|중요(?:하다|합니다|해요)|시급(?:하다|합니다)|(?:서는|면) 안 (?:된다|됩니다))[.!]?$")
    ends, ex = 0, []
    ko_lines = doc.ko_text.split("\n")
    spans, k = [], 0
    while k < len(ko_lines):
        if not ko_lines[k].strip():
            k += 1
            continue
        j = k
        while j < len(ko_lines) and ko_lines[j].strip():
            j += 1
        spans.append((k, j))
        k = j
    for a, b in spans:
        p = "\n".join(ko_lines[a:b])
        nxt = b
        while nxt < len(doc.lines) and not doc.lines[nxt].strip():
            nxt += 1
        if nxt < len(doc.lines) and doc.lines[nxt].lstrip().startswith(("```", "~~~", "|")):
            continue  # the sentence introduces the code/table below it
        sents = split_sentences(p, "ko")
        if sents and ought_end.search(sents[-1]):
            ends += 1
            if len(ex) < max_items:
                ex.append({"line": 0, "match": "", "text": snippet(sents[-1])})
    counts["KO-I4"] = ends
    if ends >= 2:
        results["KO-I4"] = {"id": "KO-I4", "sev": "S1" if ends >= 4 else "S2", "name": "당위로 끝나는 문단 2개+",
                            "count": ends, "hint": "문단 하나까지는 둔다(어느 문단이든). 나머지 문단의 당위 문장은 문단 앞이나 중간으로 옮기거나 행위 주체 문장으로 쓴다. 지우거나 단정으로 바꾸지 않는다. 코드 블록·표를 바로 이끄는 지시문은 세지 않는다.",
                            "items": ex, "esc": ends >= 4}
    # KO-H1: 3+ sentence-initial connectives in one paragraph
    dense, ex = 0, []
    for p in paras:
        sents = split_sentences(p, "ko")
        n = sum(1 for s in sents if any(s.startswith(c) for c in KO_CONNECTIVES))
        if n >= 3:
            dense += 1
            if len(ex) < max_items:
                ex.append({"line": 0, "match": f"{n}회", "text": snippet(p.replace("\n", " "))})
    counts["KO-H1"] = dense
    if dense:
        results["KO-H1"] = {"id": "KO-H1", "sev": "S2", "name": "문두 접속사 밀집(문단당 3회+)", "count": dense,
                            "hint": "그 문단에서 절반쯤 덜어낸다. 문서 전체 일괄 삭제 금지.", "items": ex}
    # EN-B1: AI vocabulary (distinct words)
    words = [w.lower() for w in EN_WORD.findall(doc.en_text)]
    found = {}
    vocab = set(AI_VOCAB_EN)
    fig_nav = len(re.findall(r"\bnavigat\w* (?:the |these |this |its |their |our |your )?(?:complexit|challeng|landscape|intricac|nuance|uncertaint|world of|maze|ever-)", doc.en_text, re.I))
    for w in words:
        if w in vocab:
            w = EN_LEMMA.get(w, w)
            if w == "navigate":
                continue
            found[w] = found.get(w, 0) + 1
    if fig_nav:
        found["navigate"] = fig_nav
    distinct = len(found)
    counts["EN-B1"] = sum(found.values())
    if distinct:
        mult = doc.units("en")
        sev = _severity(distinct, {"S1": 4, "S2": 2, "S3": 1}, mult)
        if sev:
            listing = ", ".join(f"{w} x{c}" for w, c in sorted(found.items(), key=lambda x: (-x[1], x[0])))
            results["EN-B1"] = {"id": "EN-B1", "sev": sev, "name": "AI vocabulary cluster (distinct words)", "count": distinct,
                                "hint": "Replace with plain words (use, show, important, many). One or two alone are fine.",
                                "items": [{"line": 0, "match": "", "text": listing}], "esc": sev != "S3"}
    # EN-D2: rule of three density ("a, b, and c" / "a, b, or c")
    trip = [t for t in re.findall(r"\b\w+(?: \w+)?, \w+(?: \w+)?,? (?:and|or) \w+\b", doc.en_text)
            if not all(x.split()[-1][:1].isupper() for x in re.split(r",\s*|,?\s+(?:and|or)\s+", t) if x.split())]
    counts["EN-D2"] = len(trip)
    if trip:
        sev = _severity(len(trip), {"S2": 3, "S3": 2}, doc.units("en"))
        if sev:
            results["EN-D2"] = {"id": "EN-D2", "sev": sev, "name": "rule-of-three lists", "count": len(trip),
                                "hint": "Use two items, or the one that matters. A single triplet is fine.",
                                "items": [{"line": 0, "match": t[:40], "text": t[:70]} for t in trip[:max_items]],
                                "esc": sev != "S3"}
    # EN-L4: 4+ sentences in a row that start with "I"
    en_s = split_sentences(doc.en_text, "en")
    run_i, best_i, ex_i = 0, 0, ""
    for s_ in en_s:
        if re.match(r"I(?:'m|'ve|'d|'ll)?\b", s_):
            run_i += 1
            if run_i > best_i:
                best_i, ex_i = run_i, s_
        else:
            run_i = 0
    counts["EN-L4"] = best_i if best_i >= 4 else 0
    if best_i >= 4:
        results["EN-L4"] = {"id": "EN-L4", "sev": "S2" if best_i >= 6 else "S3", "name": "sentences in a row starting with 'I'",
                            "count": best_i, "hint": "Start one or two with the fact, the place or the other person.",
                            "items": [{"line": 0, "match": f"{best_i} in a row", "text": snippet(ex_i)}], "esc": best_i >= 6}
    # EN-L3: 3+ paragraphs that open with a very short sentence (bullet-to-paragraph rhythm)
    en_paras = [q for q in re.split(r"\n\s*\n", doc.en_text) if q.strip() and not q.lstrip().startswith(("#", "-", "*", "|"))]
    short_open = []
    for q in en_paras:
        first = re.split(r"(?<=[.!?])\s+", q.strip(), maxsplit=1)[0]
        if len(EN_WORD.findall(first)) <= 5 and len(EN_WORD.findall(q)) > len(EN_WORD.findall(first)):
            short_open.append(first)
    counts["EN-L3"] = len(short_open)
    if len(en_paras) >= 3 and len(short_open) >= 3 and len(short_open) * 2 >= len(en_paras):
        results["EN-L3"] = {"id": "EN-L3", "sev": "S2" if len(short_open) >= 4 else "S3",
                            "name": "paragraphs open with the same short sentence", "count": len(short_open),
                            "hint": "Vary paragraph openings. Merge a short opener into the next sentence, or start with the fact.",
                            "items": [{"line": 0, "match": "", "text": snippet(x)} for x in short_open[:max_items]],
                            "esc": len(short_open) >= 4}
    # EN-J3: title case headings
    body_en = "\n".join(l for l, lg in zip(doc.lines, doc.line_lang) if lg == "en" and not l.lstrip().startswith("#"))
    tc, ex = 0, []
    for ln, (line, lg) in enumerate(zip(doc.lines, doc.line_lang)):
        if lg != "en":
            continue
        m = re.match(r"^#{1,6}\s+(.+)$", line.strip())
        if not m:
            continue
        head = m.group(1).strip()
        if re.search(r"\d", head) or (len(head) > 3 and body_en.count(head) > 0):
            continue  # product or place name, not a title-cased phrase
        ws = EN_WORD.findall(head)
        big = [w for w in ws[1:] if w.lower() not in EN_SMALL]
        small_caps = any(w.lower() in EN_SMALL and w[0].isupper() for w in ws[1:])
        if len(ws) >= 2 and big and all(w[0].isupper() for w in big) and (small_caps or len(big) >= 1):
            tc += 1
            if len(ex) < max_items:
                ex.append({"line": ln + 1, "match": "", "text": snippet(line)})
    counts["EN-J3"] = tc
    if tc:
        results["EN-J3"] = {"id": "EN-J3", "sev": "S3", "name": "Title Case headings", "count": tc,
                            "hint": "Use sentence case in headings.", "items": ex}
    # EN-K2: mixed curly and straight quotes
    mixed = ("“" in doc.en_text or "”" in doc.en_text) and '"' in doc.en_text
    counts["EN-K2"] = 1 if mixed else 0
    if mixed:
        results["EN-K2"] = {"id": "EN-K2", "sev": "S3", "name": "curly and straight quotes mixed", "count": 1,
                            "hint": "Pick one quote style.", "items": []}


GENRE_LEVELS = {
    # social posts and YouTube descriptions: a few section emoji and one CTA line are normal
    "sns": {"AN-J5": {"S2": 6, "S3": 1}, "KO-K8": {"S2": 3, "S3": 1}, "AN-J1": {"S2": 1}},
    # messenger: one or two emoji are normal
    "chat": {"AN-J5": {"S2": 3, "S3": 1}, "AN-J1": {"S2": 1}},
}


def _with_genre(rules, genre):
    over = GENRE_LEVELS.get(genre or "", {})
    if not over:
        return rules
    return [(r[0], r[1], r[2], r[3], over.get(r[0], r[4]), r[5], r[6], r[7]) for r in rules]


def analyze(text: str, lang: str = "auto", skip_quotes: bool = False, max_items: int = 5, genre: str | None = None) -> dict:
    doc = Doc(text, lang, skip_quotes)
    results, counts = {}, {}
    run_regex_rules(doc, _with_genre(KO_RULES, genre), results, counts, max_items)
    run_regex_rules(doc, _with_genre(EN_RULES, genre), results, counts, max_items)
    run_regex_rules(doc, _with_genre(ANY_RULES, genre), results, counts, max_items)
    run_function_rules(doc, results, counts, max_items)
    findings = sorted(results.values(), key=lambda r: (SEV_RANK[r["sev"]], r["id"]))
    tally = {s: sum(1 for f in findings if f["sev"] == s) for s in ("S1", "S2", "S3")}
    return {
        "stats": {"ko_chars": doc.ko_chars, "en_words": doc.en_words, "chars": doc.total_chars},
        "tally": tally,
        "findings": findings,
        "counts": counts,
    }


def format_report(res: dict) -> str:
    st, t = res["stats"], res["tally"]
    out = [f"newspeak lint | ko {st['ko_chars']} hangul syllables, en {st['en_words']} words | S1 {t['S1']} / S2 {t['S2']} / S3 {t['S3']}"]
    if not res["findings"]:
        out.append("no findings")
    for f in res["findings"]:
        up = "↑" if f.get("esc") else ""  # raised by match count
        out.append(f"[{f['sev']}{up}] {f['id']} {f['name']} x{f['count']}: {f['hint']}")
        for it in f["items"]:
            loc = f"L{it['line']}: " if it["line"] else ""
            m = f" <{it['match']}>" if it["match"] else ""
            out.append(f"    {loc}{it['text']}{m}")
        hidden = f["count"] - len(f["items"])
        if f["items"] and hidden > 0 and f["id"] != "EN-B1":
            out.append(f"    (+{hidden} more; run with --max-items {f['count']})")
    return "\n".join(out)


def _configure_stdout():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def main(argv=None) -> int:
    _configure_stdout()
    ap = argparse.ArgumentParser(description="Detect Korean/English AI-writing patterns.")
    ap.add_argument("file", help="text file path, or - for stdin")
    ap.add_argument("--lang", default="auto", choices=["auto", "ko", "en"])
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--skip-quotes", action="store_true", help="ignore text inside double quotes")
    ap.add_argument("--max-items", type=int, default=8)
    ap.add_argument("--genre", choices=sorted(GENRE_LEVELS), default=None,
                    help="sns = social posts and YouTube descriptions, chat = messenger; relaxes emoji/CTA counts")
    try:
        a = ap.parse_args(argv)
        res = analyze(read_text(a.file), a.lang, a.skip_quotes, max(0, a.max_items), a.genre)
    except SystemExit as e:
        return 3 if e.code not in (0, None) else 0
    except Exception as e:  # report, never crash with a traceback
        print(f"lint error: {type(e).__name__}: {e}", file=sys.stderr)
        return 3
    print(json.dumps(res, ensure_ascii=False, indent=1) if a.json else format_report(res))
    return 1 if res["tally"]["S1"] else 0


if __name__ == "__main__":
    sys.exit(main())
