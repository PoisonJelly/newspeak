#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""newspeak / selftest.py: unit tests for lint.py and gate.py.

  python selftest.py        # exit 0 when every case passes
"""
from __future__ import annotations

import contextlib
import io
import os
import subprocess
import sys
import tempfile
import time
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gate  # noqa: E402
import lint  # noqa: E402

KO_AI = """좋은 질문이에요! 요즘 많은 기업이 AI를 도입하고 있습니다.

결론적으로, AI는 단순한 도구를 넘어 비즈니스의 핵심 동반자로 기능합니다. 이는 생산성뿐만 아니라 조직 문화에도 중요한 역할을 합니다. 기술은 발전하지만, 기업은 따라가지 못하고 있습니다.

중요한 것은 속도가 아니라 방향입니다. 이제는 우리 모두가 함께 고민할 때입니다. 더 궁금한 점이 있으시면 언제든지 물어보세요!"""

KO_HUMAN = """어제 회의는 두 시간 걸렸다. 결론은 없었고 다음 주에 다시 모이기로 했다.

김 팀장이 예산표를 들고 왔는데 숫자가 지난달과 달랐다. 왜 바뀌었냐고 물으니 본사에서 3% 깎았단다. 그 말에 다들 한숨부터 쉬었다. 광고, 마케팅, 홍보 예산이 같이 줄었다."""

EN_AI = """Great question! Nestled in the heart of the valley, the town boasts a vibrant tapestry of cultures.

The festival is not just a celebration, but a testament to the community's enduring spirit, highlighting its deep commitment to tradition. It's not a party, it's a movement. Additionally, the event plays a pivotal role in the local economy, underscoring the importance of tourism.

In conclusion, despite these challenges, the town continues to thrive. I hope this helps!"""

EN_HUMAN = """The bakery opened in 1998 on Elm Street. It sells about 400 loaves a day, mostly sourdough.

The owner, Ana Ruiz, still starts the ovens at 4 a.m. She says the rent doubled in 2019, so she cut the menu to six items. Most customers are regulars; some have come every Saturday for twenty years."""

CASES = []


def case(fn):
    CASES.append(fn)
    return fn


def ids(res, sev=None):
    return {f["id"] for f in res["findings"] if sev is None or f["sev"] == sev}


@case
def empty_inputs():
    for t in ("", "   ", "\n\n\n", "﻿"):
        r = lint.analyze(t)
        assert r["findings"] == [], r["findings"]
        g = gate.compare(t, t)
        assert g["verdict"] == 0, g


@case
def korean_ai_sample_detected():
    r = lint.analyze(KO_AI)
    need = {"KO-K1", "KO-K2", "KO-D1a", "KO-A21", "KO-C8", "KO-C11", "KO-D6", "KO-L1", "KO-D8"}
    missing = need - ids(r)
    assert not missing, f"missing {missing}; got {ids(r)}"
    assert "KO-C8b" not in ids(r, "S1"), "'뿐만 아니라' must not count as contrast"


@case
def korean_human_sample_clean():
    r = lint.analyze(KO_HUMAN)
    assert not ids(r, "S1"), ids(r, "S1")
    assert "KO-C11" not in ids(r), "noun list '광고, 마케팅' is not a connective comma"


@case
def english_ai_sample_detected():
    r = lint.analyze(EN_AI)
    need = {"EN-H1", "EN-A1", "EN-A3", "EN-A4", "EN-C1", "EN-D1", "EN-A5", "EN-B1"}
    missing = need - ids(r)
    assert not missing, f"missing {missing}; got {ids(r)}"


@case
def english_human_sample_clean():
    r = lint.analyze(EN_HUMAN)
    assert not ids(r, "S1"), ids(r, "S1")
    assert not ids(r, "S2"), ids(r, "S2")


@case
def code_and_urls_are_masked():
    t = "설명은 아래 코드에 있다.\n```\n결론적으로, 이는 단순한 도구를 넘어 기능합니다.\n```\n`It's not X, it's Y` 는 예시다. https://example.com/결론적으로"
    r = lint.analyze(t)
    assert not ids(r, "S1"), ids(r)


@case
def tool_residue_inside_url_detected():
    t = "Source: https://news.example.com/a?utm_source=chatgpt.com and citeturn0search3"
    r = lint.analyze(t)
    assert "EN-H3" in ids(r, "S1"), ids(r)


@case
def mixed_bilingual_document():
    t = KO_AI + "\n\n" + EN_AI + "\n\n| a | b |\n|---|---|\n| 1 | 2 |\n\n## 제목: 부제\n- **항목:** 설명"
    r = lint.analyze(t)
    assert any(i.startswith("KO-") for i in ids(r)) and any(i.startswith("EN-") for i in ids(r))
    assert r["stats"]["ko_chars"] > 0 and r["stats"]["en_words"] > 0


@case
def nfd_bom_crlf_file():
    t = "﻿" + unicodedata.normalize("NFD", KO_AI).replace("\n", "\r\n")
    with tempfile.NamedTemporaryFile("wb", suffix=".txt", delete=False) as f:
        f.write(t.encode("utf-8"))
        p = f.name
    try:
        r = lint.analyze(lint.read_text(p))
        assert "KO-K1" in ids(r), ids(r)
    finally:
        os.unlink(p)


@case
def ppunman_not_contrast():
    r = lint.analyze("이 제도는 학생뿐만 아니라 교사에게도 도움이 된다. 비용뿐 아니라 시간도 줄었다.")
    assert "KO-C8" not in ids(r), ids(r)


@case
def contrast_variants():
    for t in ("이건 버그가 아니라 설계 문제다.", "기술인가, 사람인가의 문제다.", "중요한 건 속도가 아니라, 방향이다."):
        assert "KO-C8" in ids(lint.analyze(t)), t
    assert "KO-C8c" in ids(lint.analyze("그건 실수가 아니다. 구조의 문제다."))


@case
def skip_quotes_option():
    t = '그는 "결론적으로, 이건 단순한 문제를 넘어선다"라고 말했다.'
    assert "KO-D1a" in ids(lint.analyze(t))
    assert "KO-D1a" not in ids(lint.analyze(t, skip_quotes=True))


@case
def gate_rejects_lost_number_and_url():
    b = "매출은 2.1% 늘었다. 자세한 내용은 https://example.com/r 에 있다."
    a = "매출이 늘었다. 자세한 내용은 보고서에 있다."
    g = gate.compare(b, a)
    assert g["verdict"] == 2 and any("numbers" in f for f in g["fails"]) and any("URLs" in f for f in g["fails"]), g
    assert g["grade"] == "D"


@case
def gate_rejects_new_number():
    g = gate.compare("방문자가 크게 늘었다.", "방문자가 30% 늘었다.")
    assert g["verdict"] == 2, g


@case
def gate_rejects_over_rewrite():
    g = gate.compare("오늘은 비가 와서 집에 있었다. 책을 두 권 읽었다.", "날씨 탓에 외출을 포기하고 독서로 하루를 보냈다. 소설 두 편을 마쳤다.")
    assert g["verdict"] == 2 and g["rates"]["rewrite"] >= 0.5, g


def wkeys(g):
    return {k for k, _ in g["warns"]}


def wtext(g):
    return " ".join(m for _, m in g["warns"])


@case
def gate_warns_on_injected_comma():
    b = "기술은 발전한다. 기업은 따라가지 못한다. 그래서 격차가 커진다."
    a = "기술은 발전하지만, 기업은 따라가지 못한다. 그래서 격차가 커진다."
    g = gate.compare(b, a)
    assert g["verdict"] >= 1 and "KO-C11" in wtext(g), g


@case
def gate_warns_on_mood_change():
    b = "보고서는 길다. 정부는 제도를 고쳐야 한다. 표는 세 개다. 비용이 늘어날 수 있다. 끝."
    a = "보고서는 길다. 정부는 제도를 고친다. 표는 세 개다. 비용이 늘어난다. 끝."
    g = gate.compare(b, a)
    assert "mood" in wkeys(g), g


@case
def gate_deleted_hedge_is_a_note_not_a_warning():
    b = "산책은 혈당 관리에 도움이 된다. 전문가들은 시점이 중요할 수 있다고 말한다. 식후 10분이면 된다."
    a = "산책은 혈당 관리에 도움이 된다. 식후 10분이면 된다."
    g = gate.compare(b, a)
    assert "mood" not in wkeys(g), g
    assert any("hedge" in n for n in g["notes"]), g


@case
def gate_allow_with_reason():
    b = "정부는 제도를 고쳐야 한다. 비용이 늘어날 수 있다. 표는 세 개다. 끝이다."
    a = "정부는 제도를 고친다. 비용이 늘어난다. 표는 세 개다. 끝이다."
    g = gate.compare(b, a, allow={"mood", "rewrite"}, reason="test")
    assert "mood" not in wkeys(g) and g["allowed"], g
    rc = gate.main(["x.txt", "y.txt", "--allow", "mood"])  # no --reason
    assert rc == 3, rc


@case
def gate_write_mode():
    brief = "첫 캠핑 브이로그 설명란. 2026년 10월 24~25일, 12번 사이트, 밤 기온 3도."
    good = "첫 캠핑 브이로그예요. 2026년 10월 24~25일에 12번 사이트에서 지냈어요. 밤에는 3도까지 내려갔어요."
    bad = "첫 캠핑 브이로그예요. 2026년 10월 24~25일, 12번 사이트, 텐트 치는 데 40분 걸렸어요."
    assert gate.compare_write(brief, good)["verdict"] == 0
    g = gate.compare_write(brief, bad)
    assert g["verdict"] == 2 and "40" in " ".join(g["fails"]), g


@case
def gate_unchanged_note():
    g = gate.compare(KO_HUMAN, KO_HUMAN)
    assert g["verdict"] == 0 and any("unchanged" in n for n in g["notes"]), g


@case
def gate_deletion_counted_apart_from_rewrite():
    b = EN_AI
    a = "The town has many cultures.\n\nThe festival is a celebration. The event helps the local economy."
    r = gate.edit_rates(b, a)
    assert r["delete"] > 0.3 and r["rewrite"] < r["delete"], r
    b2 = "One. Two is here. Three is long and full of filler words that say nothing at all. Four."
    a2 = "One. Two is here. Four."
    r2 = gate.edit_rates(b2, a2)
    assert r2["rewrite"] == 0 and r2["delete"] > 0.5, r2


@case
def new_rules_fire():
    assert "KO-D16" in ids(lint.analyze("요즘 홈카페를 즐기는 분들이 점점 늘고 있어요. 원두 얘기를 해 볼게요."))
    assert "KO-L2" in ids(lint.analyze("오늘은 원두 보관법에 대해 알아볼게요."))
    assert "EN-A6" in ids(lint.analyze("A new trial sheds light on one simple habit: walking after meals."))
    assert "EN-D7" in ids(lint.analyze("## Challenges\nThe town is small.\n\n## Conclusion\nIt is quiet."))
    assert "KO-D15" in ids(lint.analyze("## 결론\n짧다.\n\n## ✨ 마무리\n끝이다."))
    t = "그래서 샀다. 그래서 먹었다. 그러면 좋다. 그래서 잤다. 그러면 된다. 그래서 끝났다. 그러니까 됐다."
    assert "KO-H2" in ids(lint.analyze(t))


@case
def connective_comma_myeon_and_exclusions():
    assert "KO-C11" in ids(lint.analyze("산화가 진행되면, 향이 줄어요."))
    r = lint.analyze("반면, 비용은 줄었다. 화면, 장면, 표면을 모두 봤다. 라면, 김밥을 샀다.")
    assert "KO-C11" not in ids(r), r["findings"]


@case
def emoji_misc_technical_and_line_numbers():
    r = lint.analyze("⏰ 알람을 맞추세요.")
    assert "AN-J5" in ids(r), ids(r)
    t = "제목\n\n- **하나:** 설명\n- **둘:** 설명\n- **셋:** 설명\n- **넷:** 설명\n"
    r = lint.analyze(t)
    f = [x for x in r["findings"] if x["id"] == "AN-J2"][0]
    assert f["items"][0]["line"] == 3, f["items"]


@case
def haeyo_endings_not_all_same():
    t = "어제 캠핑을 갔어요. 텐트를 쳤어요. 저녁은 라면이었어요. 밤에는 추웠어요. 아침엔 안개가 꼈어요. 집에 왔어요."
    assert "KO-E2" not in ids(lint.analyze(t)), ids(lint.analyze(t))
    t2 = "정말 좋아요. 정말 좋아요. 정말 좋아요. 정말 좋아요. 정말 좋아요. 정말 좋아요."
    assert "KO-E2" in ids(lint.analyze(t2))


@case
def batch2_rules_fire():
    t = "앞으로 이 격차는 더 벌어질 것이다. 무인 매장은 더 늘어날 것이고 고령 인구도 더 늘어날 것이다. 결국 소외되는 사람의 수 역시 늘어날 것이다."
    assert "KO-E3" in ids(lint.analyze(t)), ids(lint.analyze(t))
    assert "KO-A8" in ids(lint.analyze("교육은 세 가지 주제로 구성되어집니다."))
    assert "KO-G2" in ids(lint.analyze("익히실 수 있을 것으로 보입니다."))
    assert "KO-D2" in ids(lint.analyze("이 수치가 시사하는 바는 크다."))
    assert "KO-A31" in ids(lint.analyze("사례 3건에 대해 다룰 예정이며 이를 통해 대처 방법을 익힙니다."))
    assert "KO-D1c" in ids(lint.analyze("이를 통해 실제 상황에서 대처 방법을 익히실 수 있습니다."))
    assert "EN-H4" in ids(lint.analyze("Today, I'm humbled to share that I got promoted. Drop it in the comments below."))
    assert "EN-H5" in ids(lint.analyze("I almost didn't post this. Here is my news."))
    assert "EN-C1b" in ids(lint.analyze("This isn't a story about success. It's a story about resilience."))
    assert "EN-C1" in ids(lint.analyze("Dana didn't just give me advice — she gave me a seat at the table."))
    assert "AN-J6" in ids(lint.analyze("Big news today \U0001F680"))
    t2 = "첫 문단이다. 정부는 고쳐야 한다.\n\n둘째 문단이다. 기업도 바뀌어야 한다.\n\n셋째 문단이다. 시민은 참여해야 한다."
    assert "KO-I4" in ids(lint.analyze(t2)), ids(lint.analyze(t2))


@case
def gate_batch2_semantics():
    # double hedge collapsed to one: no mood warning
    b = "교육은 길다. 방법을 익히실 수 있을 것으로 보입니다. 끝이다."
    a = "교육은 길다. 방법을 익히실 수 있습니다. 끝이다."
    g = gate.compare(b, a)
    assert "mood" not in wkeys(g), g
    # deleted sentence inside a rewritten block is a deletion, not a mood drop
    b = "산책이 좋다. 전문가들은 시점이 중요할 수 있다고 본다. 식후 10분이면 된다고 한다."
    a = "산책이 좋다. 식후 10분이면 된다."
    g = gate.compare(b, a)
    assert "mood" not in wkeys(g), g
    # prohibition counts as ought
    b = "개인에게 떠넘겨서는 안 된다. 표는 셋이다. 끝."
    a = "개인에게 떠넘긴다. 표는 셋이다. 끝."
    assert "mood" in wkeys(gate.compare(b, a))
    # same number twice in write mode is fine
    assert gate.compare_write("Billwick 4.2 ships on November 12.", "Billwick 4.2 ships November 12. Version 4.2 adds CSV.")["verdict"] == 0
    # per-key reasons
    g = gate.compare("정부는 고쳐야 한다. 비용이 늘 수 있다. 표는 셋이다. 끝이다.", "정부는 고친다. 비용이 는다. 표는 셋이다. 끝이다.",
                     allow=gate.parse_allow(["mood=test reason"]))
    assert "mood" not in wkeys(g) and g["allowed"][0]["reason"] == "test reason", g
    # Korean single-quoted saying is protected
    b = "그들은 '어르신들이 배우면 된다'고 말한다. 끝이다."
    a = "그들은 배우면 된다고 말한다. 끝이다."
    assert "quotes" in wkeys(gate.compare(b, a))


@case
def batch3_rules_and_gate():
    assert "KO-C11" in ids(lint.analyze("데이터를 분석하여, 결과를 정리했습니다."))
    assert "EN-A7" in ids(lint.analyze("Whether you're hiking or commuting, it delivers all-day comfort without compromising on strength."))
    assert "KO-D17" in ids(lint.analyze("언제 어디서나 걱정 없이 쓰는 완벽한 선택이에요."))
    assert "EN-D7" in ids(lint.analyze("## The Perfect Choice\nIt costs $129."))
    assert "EN-J3" in ids(lint.analyze("### Key Features\nIt is light."))
    # dateline dash is not counted; quote-internal tells are ignored by gate
    r = lint.analyze("PORT CALDER — The council voted 7–2 on Tuesday. The plan passed.")
    assert "EN-K1" not in ids(r), ids(r)
    b = 'The mayor said, "This is not just about bikes, it\'s about safety." The vote was 7-2.'
    g = gate.compare(b, b)
    assert g["after"]["S1"] == 0, g
    # attribution removed -> warning
    b = "Experts say protected lanes can reduce injuries. The plan costs $18.4 million."
    a = "Protected lanes can reduce injuries. The plan costs $18.4 million."
    assert "attribution" in wkeys(gate.compare(b, a))
    # --allow reason with commas
    al = gate.parse_allow(["delete=cut slogans, CTA, and fluff", "mood"], "default")
    assert al == {"delete": "cut slogans, CTA, and fluff", "mood": "default"}, al
    rc = gate.main([__file__, __file__, "--allow", "delete=a, b, c"])
    assert rc in (0, 1), rc
    # '진행한' -> '진행했습니다' is not an injection
    g = gate.compare("이 프로젝트를 진행한 경험이 있다. 끝이다.", "이 프로젝트를 진행했습니다. 끝이다.")
    assert "KO-A25" not in wtext(g), g
    # '~라고 생각합니다' counts as a hedge
    assert gate.marks("좋아질 것이라고 생각합니다")[1] >= 1


@case
def batch4_rules_and_gate():
    # new lint rules
    assert "EN-C1" in ids(lint.analyze("Libraries are not just places to borrow books; they are hubs of learning."))
    assert "EN-A4" in ids(lint.analyze("They are vibrant hubs of discovery in vibrant communities."))
    assert "EN-A1" in ids(lint.analyze("I admire the transformative role that libraries play in towns."))
    r = lint.analyze("Rest assured, your satisfaction is our top priority. Please don't hesitate to reach out.")
    assert "EN-H7" in ids(r, "S2"), ids(r)
    r = lint.analyze("I am writing to express my keen interest in the role. My skills align with your mission. "
                     "I look forward to the possibility of joining your dynamic team.")
    assert "EN-M3" in ids(r, "S2"), ids(r)
    assert "EN-M3" in ids(lint.analyze("I am writing to express my interest in the role. I worked there."), "S3")
    assert "EN-M4" in ids(lint.analyze("I have a real talent for this. I can read menus, which I'm counting as a win."), "S2")
    r = lint.analyze("I started in May with a free app and a lot of hope.\n\nAnd there are plenty. I mixed up every ending.\n\n"
                     "There is some progress. I read menus now.\n\nI'm nowhere near fluent. Tips are below.")
    assert "EN-L3" in ids(r), ids(r)
    # B1 counts inflections as one word
    r = lint.analyze("We foster trust. We fostered trust. It fosters trust.")
    assert r["counts"]["EN-B1"] == 3 and not [f for f in r["findings"] if f["id"] == "EN-B1" and f["count"] > 1]
    assert "KO-A8" in ids(lint.analyze("기존 파일은 더 이상 읽혀지지 않습니다."))
    assert "KO-A8" not in ids(lint.analyze("원인이 밝혀지지 않았고 이름도 알려지지 않았다."))
    assert "KO-G5" in ids(lint.analyze("김치볶음밥은 자취생의 소울푸드라고 할 수 있어요."))
    assert "KO-A1b" in ids(lint.analyze("본 문서에서는 업그레이드 절차에 대해 설명합니다."))
    assert "KO-L2" in ids(lint.analyze("오늘은 김치볶음밥 레시피에 대해 알아봤어요."))
    # KO-I4: an instruction that leads into a code block is not counted
    t = ("설정을 바꿨습니다. 이 경우 반드시 변환해야 합니다.\n\n```bash\nlogferry migrate\n```\n\n"
         "버퍼는 크게 잡지 마세요. 메모리를 아껴야 합니다.\n\n나머지는 그대로입니다.")
    assert lint.analyze(t)["counts"]["KO-I4"] == 1, lint.analyze(t)["counts"]["KO-I4"]
    # genre sns: header emoji and one CTA are conventions; KO-K8 once is S3 by default
    sns = "⏱ 타임라인\n00:00 오프닝\n\n🛒 재료\n밥 1공기\n\n구독과 좋아요, 알림 설정도 잊지 마세요."
    assert "AN-J5" in ids(lint.analyze(sns), "S2")
    r = lint.analyze(sns, genre="sns")
    assert "AN-J5" in ids(r, "S3") and "KO-K8" in ids(r, "S3"), ids(r)
    assert lint.main(["-", "--genre", "nope"]) == 3
    # gate: epistemic 'must' is not an obligation
    assert gate.marks("I understand how frustrating it must be to wait.")[0] == 0
    assert gate.marks("It must have been hard.")[0] == 0
    assert gate.marks("Refunds must be requested within 30 days.")[0] == 1
    # gate: chatbot wrapper lines do not count as deletions
    b = ("Certainly! Here's a friendly response to the customer:\n\n---\n\nHi Sam,\n\nYour lamp ships on May 2.\n\n"
         "Best,\nAlex\n\n---\n\nLet me know if you'd like me to adjust the tone!")
    a = "Hi Sam,\n\nYour lamp ships on May 2.\n\nBest,\nAlex"
    g = gate.compare(b, a)
    assert g["rates"]["delete"] == 0.0 and any("wrapper" in n for n in g["notes"]), g
    # an in-letter line ending with a colon is not a wrapper
    core, n = gate.strip_wrapper("Hi Sam,\n\nHere's what we can do to make things right:\n\n- Refund", "Hi Sam,\n\n- Refund")
    assert n == 0, core
    # gate: shared role turned solo
    b = "I have played a pivotal role in developing more than 40 workshops."
    assert "contribution" in wkeys(gate.compare(b, "I have developed more than 40 workshops."))
    assert "contribution" in wkeys(gate.compare(b, "I have helped develop more than 40 workshops."))  # downgrade
    assert "contribution" not in wkeys(gate.compare(b, "I have had a central part in developing more than 40 workshops."))
    # gate passes --genre through
    assert gate.main([__file__, __file__, "--genre", "sns"]) in (0, 1)


@case
def batch5_rules_and_gate():
    # KO-C11: '-다면,' '-라면,' '-어도,' are connective commas; bare nouns are not
    for t in ("연락이 뜸해졌다면, 서운할 수 있어.", "친구라면, 먼저 연락해.", "매일 연락하지 않아도, 괜찮아."):
        assert "KO-C11" in ids(lint.analyze(t)), t
    for t in ("이 화면, 저 화면을 비교했다.", "반면, 비용은 줄었다.", "그래도, 나는 간다."):
        assert "KO-C11" not in ids(lint.analyze(t)), t
    assert "KO-K9" in ids(lint.analyze("연락이 뜸해졌다면, 서운하고 불안한 게 너무나 당연해."))
    assert "KO-K1" in ids(lint.analyze("그런 감정을 느끼는 너는 전혀 이상하지 않아."))
    assert "KO-K4" in ids(lint.analyze("와, 이런 고민을 털어놓다니 대단해."))
    assert "KO-D1c" not in ids(lint.analyze("데이터를 기준으로 두면 합의에 이를 수 있다는 것을 배웠습니다."))
    assert "KO-D1c" in ids(lint.analyze("이를 통해 팀은 합의에 도달할 수 있었습니다."))
    # EN-J3 skips product names used in the body; EN-D2 skips lists of names; literal 'navigate' is not B1
    r = lint.analyze("## Ridgeway 28 Daypack\nThe Ridgeway 28 Daypack comes in Slate, Moss, and Ember.\n\n## Key Features\nIt is light.")
    assert r["counts"]["EN-J3"] == 1 and r["counts"]["EN-D2"] == 0, r["counts"]
    assert lint.analyze("It makes navigating your daily commute easy.")["counts"]["EN-B1"] == 0
    assert lint.analyze("We help you navigate the complexities of tax.")["counts"]["EN-B1"] == 1
    # gate: writer-check markers are ignored in rates and lint, and reported
    b = "I ran 40 workshops a year with the team."
    g = gate.compare(b, "I ran 40 workshops a year with the team [writer to confirm: led or co-led?].")
    assert g["rates"]["rewrite"] == 0.0 and any("marker" in n for n in g["notes"]), g
    g = gate.compare("공감이 협업의 핵심이었습니다.", "공감[필자 확인]도 협업의 핵심이었습니다.")
    assert any("marker" in n for n in g["notes"]), g
    # cover-letter ending, messenger trailing offer, praising the act of worrying
    assert "KO-M7" in ids(lint.analyze("이 경험은 귀사의 데이터 분석 업무에서 큰 강점이 될 수 있다고 생각합니다."))
    assert "KO-M7" not in ids(lint.analyze("입사 후 데이터 분석에서도 근거를 먼저 모으겠습니다."))
    assert "KO-K2" in ids(lint.analyze("친구에게 보낼 첫 메시지를 같이 써 줄까?"))
    assert "KO-K2" not in ids(lint.analyze("내일 같이 가 줄까? 시간 되면 말해."))
    assert "KO-K1" in ids(lint.analyze("이렇게 고민하는 것만 봐도 알 수 있어."))
    # gate: a rhythm signal raised by deleting filler is a note, not an injection
    b = "짧다. 또 짧다. 그래서 길게 이어지는 문장 하나가 여기 있는데 이 문장은 꽤 길게 늘어진다. 끝."
    g = gate.compare(b, "짧다. 또 짧다. 끝.")
    assert not [m for k, m in g["warns"] if k == "inject" and "KO-E1" in m], g


@case
def batch6_rules_and_gate():
    assert "EN-C1c" in ids(lint.analyze("The title is new. The people who lifted me up are not."))
    assert "EN-H4" in ids(lint.analyze("What helped you most? Share it in the comments."))
    t = "I led the team. I wrote the plan. I ran the budget. I hired two people. Then we shipped."
    assert "EN-L4" in ids(lint.analyze(t)), ids(lint.analyze(t))
    assert "KO-K10" in ids(lint.analyze("다른 사람도 만나면서 네 감정도 챙겨 봐."))
    # markers are masked in lint; a marked vague attribution is not graded
    r = lint.analyze("Experts say the timing could matter [source needed: name the study].")
    assert "EN-F1" not in ids(r) and r["stats"]["en_words"] == 6, (ids(r), r["stats"])
    # stock emoji are counted once (AN-J6), not again as AN-J5; raw ** in social posts
    r = lint.analyze("Big news 🚀 today.")
    assert "AN-J6" in ids(r) and "AN-J5" not in ids(r), ids(r)
    assert "AN-J1" in ids(lint.analyze("This is **big** news.", genre="sns"), "S2")
    # gate: a habit's role is not a person's contribution
    b = "Post-meal walking may play a crucial role in managing blood sugar."
    assert "contribution" not in wkeys(gate.compare(b, "Post-meal walking may help manage blood sugar."))
    # gate: a moved sentence is not a deletion
    b = ("키오스크는 이제 어디에나 있다. 비용을 약한 사람이 치르는 구조는 바뀌어야 한다. "
         "물론 키오스크를 모두 없애자는 주장은 현실적이지 않다. 다만 방법은 있다.")
    a = ("키오스크는 이제 어디에나 있다. 물론 키오스크를 모두 없애자는 주장은 현실적이지 않다. "
         "비용을 약한 사람이 치르는 구조는 바뀌어야 한다. 다만 방법은 있다.")
    g = gate.compare(b, a)
    assert "deleted-ought" not in wkeys(g) and any("moved" in n for n in g["notes"]), g
    # gate: certainty dropped
    b = "I am confident that my skills fit your mission. I ran 40 workshops."
    assert "certainty" in wkeys(gate.compare(b, "My skills fit your mission. I ran 40 workshops."))
    # gate: an ought that survives in the same rewritten block is not 'deleted'
    b = "However, it should be treated as a complement to, rather than a replacement for, medical care. Ask a doctor."
    a = "A short walk should go alongside medical care, not replace it. Ask a doctor."
    assert "deleted-ought" not in wkeys(gate.compare(b, a))


@case
def batch7_rules_and_gate():
    assert "EN-C1" in ids(lint.analyze("This isn't a choice between supporting teachers and supporting families — it's about finding a path."))
    assert "EN-C1" in ids(lint.analyze("It's a decision that goes beyond the calendar — it's a question about community."))
    assert "EN-C1" in ids(lint.analyze("# Four-Day Week Deserves a Careful Look, Not a Quick Vote\nThe board meets."))
    assert "EN-C1b" in ids(lint.analyze("It's not a verdict on who you are. It's feedback on what to try next."))
    assert "EN-F1" in ids(lint.analyze("Experts point out that younger students can fall behind."))
    assert "EN-A1" in ids(lint.analyze("This is a pivotal moment for the firm. We move in May."))
    assert "KO-C11" in ids(lint.analyze("한쪽이 4.6g이라서, 오래 껴도 편해요."))
    assert "EN-M3" not in ids(lint.analyze("I am confident that my skills fit your mission."))
    assert "EN-C1d" in ids(lint.analyze("Getting it right matters more than getting it done fast."))
    assert "EN-D4" in ids(lint.analyze("So what's the right answer? The truth is, it's complicated."))
    assert "EN-D9" in ids(lint.analyze("Our children deserve a thoughtful, transparent, and data-driven process."))
    assert "EN-F4" in ids(lint.analyze("Critics, however, raise equally important concerns."))
    # gate markers: requests, indirect questions, casual and press-release hedges
    assert gate.marks("셔틀버스를 이용해 주시기 바랍니다.")[0] == 1
    assert gate.marks("뭘 골라야 할지 고민되시죠?")[0] == 0
    assert gate.marks("눅눅해지지 말라고 그런 거겠지. 또 갈 듯.")[1] == 2
    assert gate.marks("지역 경제에도 효과가 있을 것으로 기대됩니다.")[1] >= 1
    # list numbers behind ** are not values
    g = gate.compare("**1. 디자인**\n가볍다.\n\n**2. 배터리**\n7시간이다.", "1. 디자인\n가볍다.\n\n2. 배터리\n7시간이다.")
    assert "numbers" not in wkeys(g), g
    # gate lint sees the marker, so a marked vague attribution is not graded there either
    b = "Experts say the timing could matter. The trial ran 12 weeks."
    a = "Experts say the timing could matter [source needed]. The trial ran 12 weeks."
    assert not [f for f in gate.compare(b, a)["after_findings"] if f["id"] == "EN-F1"]
    # a statement turned into an obligation is a mood change
    g = gate.compare("This isn't a choice between teachers and families. The board votes in March.",
                     "This doesn't have to be a choice: the board should weigh both. The board votes in March.")
    assert "mood" in wkeys(g), g


@case
def linebreak_one_sentence_per_line():
    import linebreak
    t = ("첫 영상을 올리고 18일 만에 71명이 됐다. 다음 주에는 9명만 늘었다.\n"
         "1. 쇼츠는 웃긴 장면을 앞에 둔다. 지금은 늦다.\n"
         "버전 2.0은 8.5개월 걸렸다... 그래서 끝.\n"
         "The U.S. team met Dr. Kim at 4 p.m. Then they left. Values were 7.3% and 3.9x.\n"
         "그는 \"좋다. 정말 좋다.\"라고 했다. 끝났다.\n"
         "# 제목. 이건 제목\n| 표. 칸 |\n```\na = 1. b = 2.\n```")
    out = linebreak.break_lines(t).split("\n")
    assert "첫 영상을 올리고 18일 만에 71명이 됐다." in out and "다음 주에는 9명만 늘었다." in out, out
    assert "1. 쇼츠는 웃긴 장면을 앞에 둔다." in out and "   지금은 늦다." in out, out  # list indent kept
    assert "버전 2.0은 8.5개월 걸렸다... 그래서 끝." in out, out                  # decimal and ellipsis
    assert "The U.S. team met Dr. Kim at 4 p.m. Then they left." in out, out      # abbreviations
    assert "그는 \"좋다. 정말 좋다.\"라고 했다." in out and "끝났다." in out, out    # quote kept whole
    assert "# 제목. 이건 제목" in out and "| 표. 칸 |" in out and "a = 1. b = 2." in out, out
    assert lint.analyze(linebreak.break_lines(t))["format"]["count"] == 0
    assert lint.analyze(t)["format"]["count"] == 4
    assert linebreak.break_lines("가다. 나다.", "markdown") == "가다.  \n나다."
    assert linebreak.break_lines("가다. 나다.", "html") == "가다.<br>\n나다."


@case
def gate_linebreak_check():
    multi = "18일 만에 구독자가 71명이 됐다. 다음 주에는 속도를 다시 본다."
    g = gate.compare_write("18 71", multi, linebreak=True)
    assert "linebreak" in wkeys(g), g
    g = gate.compare_write("18 71", multi, linebreak=True, allow={"linebreak": "한 줄 입력칸"})
    assert g["verdict"] == 0, g
    assert gate.compare_write("18 71", multi)["verdict"] == 0  # API default stays off
    with tempfile.TemporaryDirectory() as d:
        b, a = os.path.join(d, "b.txt"), os.path.join(d, "a.txt")
        open(b, "w", encoding="utf-8").write("18 71")
        open(a, "w", encoding="utf-8").write(multi)
        assert gate.main([b, a, "--mode", "write"]) == 1                    # CLI default on
        assert gate.main([b, a, "--mode", "write", "--no-linebreak"]) == 0
        open(a, "w", encoding="utf-8").write(multi.replace(". ", ".\n"))
        assert gate.main([b, a, "--mode", "write"]) == 0


@case
def structural_ai_tells():
    r = lambda s: {f["id"]: f["sev"] for f in lint.analyze(s)["findings"]}
    assert r("출발은 빠르다. 이번 주는 구독이 덜 늘었다\n\n본문이다.").get("KO-S1") == "S2"
    assert "KO-S1" not in r("18일이 됐다. 다음은 없다.")                      # one-line text is not a title
    assert r("Fast start. Slower week.\n\nWe grew this week.").get("EN-S1") == "S2"
    assert "EN-S1" not in r("I almost didn't post this. 🙏\n\nBody text goes here.")
    assert "EN-S1" not in r("Billwick 4.2 ships November 12. Version 4.2 adds CSV.\n\nMore below.")
    triplet = "주간 보고서\n성장: 18일 만에 구독자 71명이 됐다.\n비교: 빠른 채널과 같은 자리다.\n개선: 웃긴 장면을 앞으로 당긴다."
    assert r(triplet).get("KO-S2") == "S2"
    stacked = "보고서\n성장\n18일 만에 구독자 71명이 됐다.\n비교\n빠른 채널과 같은 자리다.\n개선\n웃긴 장면을 앞으로 당긴다."
    assert r(stacked).get("KO-S2") == "S2"
    assert "KO-S2" not in r("용량: 28L\n무게: 940g\n소재: 나일론")                  # spec values
    assert "KO-S2" not in r("- 일시: 2026년 11월 18일(수) 오후 2시\n- 장소: 3층 회의실\n- 대상: 신입 사원\n- 강사: 김 팀장")
    opts = ("Pick one:\n- Full refund: We refund $64.90 to your card.\n- Replacement: We ship a new bag today.\n"
            "- Store credit: We add $70 to your account.")
    assert r(opts).get("EN-S2") == "S3"                                             # bulleted options stay advisory
    assert r("조회가 늘었다. 구독은 줄었다. 쇼츠는 빠르다. 롱폼은 느리다. 이유는 많다.").get("KO-E4") == "S3"
    assert "KO-E4" not in r("00:00 오프닝\n01:10 첫 장소\n02:30 점심\n04:00 바다\n05:20 마무리")  # chapter lines


@case
def ste_style_limits():
    long = ("이 문장은 일부러 길게 쓴 문장으로 스무 개가 넘는 어절을 넣어서 STE 규칙의 설명문 길이 상한을 넘기는지 "
            "확인하려고 만든 시험 문장인데 실제 보고서에서는 이렇게 길게 쓰지 않고 나눠서 쓴다.")
    assert "STE-1" in ids(lint.analyze(long, style="ste")) and "STE-1" not in ids(lint.analyze(long))
    para = "\n".join(f"{i}번째 문장은 보통 길이로 쓴 설명 문장이다." for i in range(1, 8))
    assert "STE-2" in ids(lint.analyze(para, style="ste"))
    items = "\n".join(f"- {i}번 항목은 짧다." for i in range(1, 9))
    assert "STE-2" not in ids(lint.analyze(items, style="ste"))                      # a list is not a paragraph
    todo = "이번 주 할 일\n" + "\n".join(f"{i}. {i}번 일을 한다.\n   이유는 {i}번에 적었다." for i in range(1, 5))
    assert "STE-2" not in ids(lint.analyze(todo, style="ste"))                       # items with continuation lines
    en = " ".join(["word"] * 27) + "."
    assert "STE-1" in ids(lint.analyze("This sentence has " + en, lang="en", style="ste"))


@case
def docs_match_lint_levels():
    import re as _re
    root = os.path.dirname(HERE)
    doc = ""
    for name in ("ko-patterns.md", "en-patterns.md"):
        with open(os.path.join(root, "references", name), encoding="utf-8") as f:
            doc += f.read() + "\n"
    tags = dict(_re.findall(r"^- \*\*((?:KO|EN|AN)-[A-Z]\d+[a-z]?)\*\* \[([^\]]*)\]", doc, _re.M))
    ids_doc = _re.findall(r"^- \*\*((?:KO|EN|AN)-[A-Z]\d+[a-z]?)\*\*", doc, _re.M)
    dup = sorted({i for i in ids_doc if ids_doc.count(i) > 1})
    assert not dup, f"duplicate IDs in pattern docs: {dup}"
    bad = []
    for r in lint.KO_RULES + lint.EN_RULES:
        rid, levels = r[0], r[4]
        tag = tags.get(rid)
        assert tag is not None, f"{rid} is missing from the pattern docs"
        first = min(levels, key=lambda k: levels[k])
        if not tag.startswith(first) or "eye" in tag or "눈" in tag:
            bad.append((rid, tag, levels))
    assert not bad, f"doc severity differs from lint: {bad}"


@case
def escalation_marker():
    t = "결론적으로 좋다. " + "기술은 발전하지만, 기업은 느리다. " * 4
    out = lint.format_report(lint.analyze(t))
    assert "[S1↑] KO-C11" in out, out


@case
def gate_passes_good_rewrite():
    b = KO_AI
    a = """요즘 AI를 도입하는 기업이 많다.

AI는 업무를 돕는 동반자가 됐다. 생산성과 조직 문화가 함께 바뀐다. 기술은 발전하는데 기업은 따라가지 못하고 있다.

방향이 속도보다 중요하다. 우리 모두가 함께 고민하자."""
    g = gate.compare(b, a)
    assert g["after"]["S1"] == 0, g
    assert g["verdict"] in (0, 1, 2)


@case
def gate_missing_file_exit3():
    rc = gate.main(["no_such_file_123.txt", "no_such_file_456.txt"])
    assert rc == 3, rc


@case
def lint_cli_stdin_and_exit_codes():
    py = sys.executable
    p = subprocess.run([py, os.path.join(HERE, "lint.py"), "-"], input=KO_AI.encode("utf-8"), capture_output=True)
    assert p.returncode == 1, (p.returncode, p.stderr.decode("utf-8", "replace"))
    p = subprocess.run([py, os.path.join(HERE, "lint.py"), "-", "--json"], input=EN_HUMAN.encode("utf-8"), capture_output=True)
    assert p.returncode == 0, (p.returncode, p.stderr.decode("utf-8", "replace"))
    p = subprocess.run([py, os.path.join(HERE, "lint.py"), "--lang", "xx", "-"], input=b"x", capture_output=True)
    assert p.returncode == 3, p.returncode


@case
def large_input_is_fast():
    t = (KO_AI + "\n\n" + EN_AI + "\n\n") * 300
    t0 = time.time()
    lint.analyze(t)
    gate.compare(t[: len(t) // 2], t[: len(t) // 2])
    assert time.time() - t0 < 30, time.time() - t0


@case
def weird_characters_do_not_crash():
    t = "\x00\x07 이모지 \U0001F600\U0001F680 표 | | ** ** ` ``` 끝나지 않은 코드\n​  — – -- 〜 ～ 「인용」『책』"
    lint.analyze(t)
    lint.analyze(t, lang="ko")
    lint.analyze(t, lang="en", skip_quotes=True)
    gate.compare(t, t[::-1])


def main() -> int:
    lint._configure_stdout()
    ok = 0
    for fn in CASES:
        try:
            # cases call the CLIs on purpose with bad input; keep their messages out of the report
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                fn()
            ok += 1
            print(f"PASS {fn.__name__}")
        except Exception as e:  # noqa: BLE001
            print(f"FAIL {fn.__name__}: {type(e).__name__}: {e}")
    print(f"{ok}/{len(CASES)} passed")
    return 0 if ok == len(CASES) else 1


if __name__ == "__main__":
    sys.exit(main())
