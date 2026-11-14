#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""newspeak / gate.py: before/after check for a rewrite (or brief/after for write mode).

rewrite mode (default) checks:
  1. edit rates     rewrite = replaced+inserted tokens / original tokens (30% warn, 50% reject)
                    delete  = deleted tokens / original tokens (35% warn, 60% reject)
  2. invariants     numbers, URLs and code must survive; no new numbers; quoted spans kept
  3. mood           sentence-aligned: a rewritten sentence must keep its ought
                    ("~해야 한다", must/should) and hedge ("~일 수 있다", may/might) markers.
                    Markers inside deleted sentences are reported separately.
  4. injection      no lint rule may fire more often after than before
  5. residue        S1 findings left after the rewrite

write mode (--mode write BRIEF AFTER):
  numbers/URLs in AFTER must come from BRIEF; brief numbers missing in AFTER are listed;
  lint S1/S2 in AFTER must be zero.

Usage:
  python gate.py BEFORE AFTER [--lang auto|ko|en] [--json]
                 [--allow KEY=reason ...]                  # accept an explained warning (repeatable)
                 [--allow KEY[,KEY] --reason "why"]        # same reason for several keys
  python gate.py BRIEF AFTER --mode write
  python gate.py ... --style ste       # reports/documents: ASD-STE100 limits (STE-1, STE-2) count as findings
  python gate.py ... --no-linebreak    # skip the one-sentence-per-line check (on by default on the command line)
  allow keys: rewrite, delete, numbers, quotes, mood, deleted-ought, attribution, contribution, certainty, inject, s1, linebreak

Exit codes: 0 pass | 1 warn (fix, or --allow with a reason) | 2 reject (roll back) | 3 error
"""
from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lint  # noqa: E402

REWRITE_WARN, REWRITE_ABORT = 0.30, 0.50
DELETE_WARN, DELETE_ABORT = 0.40, 0.60

KO_OUGHT = re.compile(
    r"(?:(?!이)[가-힣])야(?:만)? ?(?:한다|합니다|해요|해(?=[\s.!?,]|$)|하며|하고|할(?!지|까)|하는|했|된다|됩니다)(?! ?(?:방향|길|과제|숙제|모습|가치))"
    r"|필요(?:가 있|하|합|해)|시급(?:하|합)|마땅(?:하|합)|중요(?:하다|합니다|해요|하죠)"
    r"|(?:세요|십시오|하자|합시다|해 ?주세요)(?=[.!\s]|$)|주시기 바랍니다|주시길 바랍니다|부탁드립니다|당부드립니다"
    r"|(?:서는|면) 안 (?:된다|됩니다|돼|되는|될)")
KO_HEDGE = re.compile(
    r"수(?:도)? 있|여지가? 있|(?:로|으로) 보(?:인|입|여|일)|판단(?:된|됩)|여겨(?:진|집)|듯(?:하|합|이|싶)"
    r"|가능성|(?:것|거) 같|추정|아닐까|지도 모른|읽힌다|읽힙니다|단정하기(?:는)? 이르"
    r"|(?:라고|다고|것이라고|거라고) (?:생각|봅|본다|봐요|여깁|여긴다)"
    r"|겠지|겠죠|거겠|듯(?=[.!?\s]|$)|(?:것으로|것이라고) (?:기대|예상|전망)(?:된|됩|한|합)")
EN_OUGHT = re.compile(r"\b(?:must|should|need to|needs to|have to|has to|ought to|must not|mustn't|should not|shouldn't)\b", re.I)
EN_EPISTEMIC = re.compile(
    r"\bmust(?:'ve| have (?:been|had|felt|thought|seen|known|gone|missed|forgotten|taken))\b"
    r"|\bmust be (?:so |very |really |incredibly |quite |pretty )?(?:frustrating|hard|difficult|annoying|disappointing|stressful"
    r"|exhausting|upsetting|confusing|tough|awful|scary|painful|nice|fun|exciting|tiring|lonely|worrying)\b|\bmust feel\b"
    r"|\bhow \w+(?: \w+)? (?:it|this|that|you) must (?:be|feel|have been)\b", re.I)
EN_HEDGE = re.compile(r"\b(?:may|might|could|likely|unlikely|perhaps|possibly|probably|appears? to|seems? to|suggests?)\b", re.I)

CERTAIN = re.compile(r"\bI(?:'m| am) (?:confident|certain|sure)\b|\bI have no doubt\b|확신(?:합니다|한다|해요|하고 있)|자신(?:합니다|있습니다|있어요|이 있습니다)", re.I)
KO_ATTR = re.compile(r"(?:에 따르면|라고 (?:말했|밝혔|전했|주장했|설명했)|다고 (?:말했|밝혔|전했|주장했|설명했|본다|봤다)|(?:전문가|연구진|관계자|학자)(?:들)?(?:은|는|이|가))")
EN_ATTR = re.compile(r"\b(?:says?|said|according to|argues?|argued|claims?|claimed|reports?|reported|suggests?|told)\b|\b(?:experts|researchers|officials|scientists|critics|analysts)\b", re.I)
LIST_MARK = re.compile(r"^[ \t]*(?:#+[ \t]*)?\d+[.)][ \t]", re.M)
NUM = re.compile(r"\d+(?:[.,]\d+)*")
URL = re.compile(r"https?://[^\s)>\]\"']+")
CODE = re.compile(r"```.*?```|`[^`\n]+`", re.S)
QUOTE = re.compile(r"“[^”\n]{2,}”|\"[^\"\n]{2,}\"|「[^」\n]{2,}」|‘[^’\n]{2,}’|'(?=[^'\n]*[가-힣])[^'\n]{2,}'")
SENT_SPLIT = re.compile(r"(?<=[.!?…])\s+|\n+")


def tokens(text: str):
    return re.findall(r"\S+", text)


def edit_rates(before: str, after: str) -> dict:
    a, b = tokens(before), tokens(after)
    if not a and not b:
        return {"rewrite": 0.0, "delete": 0.0, "overall": 0.0}
    if not a:
        return {"rewrite": 1.0, "delete": 0.0, "overall": 1.0}
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    rep = ins = dele = 0
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "replace":
            # substituted tokens count as rewrite; a shrink counts as deletion, a growth as insertion
            n_b, n_a = i2 - i1, j2 - j1
            rep += min(n_b, n_a)
            dele += max(0, n_b - n_a)
            ins += max(0, n_a - n_b)
        elif op == "insert":
            ins += j2 - j1
        elif op == "delete":
            dele += i2 - i1
    n = len(a)
    return {"rewrite": round(min(1.0, (rep + ins) / n), 4),
            "delete": round(min(1.0, dele / n), 4),
            "overall": round(1.0 - sm.ratio(), 4)}


def invariants(text: str) -> dict:
    t = LIST_MARK.sub(" ", re.sub(r"^([ \t]*)\*\*", r"\1", text, flags=re.M))
    code = Counter(CODE.findall(t))
    t_nocode = CODE.sub(" ", t)
    return {
        "numbers": Counter(n.replace(",", "") for n in NUM.findall(URL.sub(" ", t_nocode))),
        "urls": Counter(u.rstrip(".,;:") for u in URL.findall(t_nocode)),
        "code": code,
        "quotes": Counter(QUOTE.findall(t_nocode)),
    }


def lost(before: Counter, after: Counter):
    return sorted((before - after).elements())


def marks(text: str) -> tuple[int, int]:
    ought = len(KO_OUGHT.findall(text)) + len(EN_OUGHT.findall(text)) - len(EN_EPISTEMIC.findall(text))
    return (max(0, ought), len(KO_HEDGE.findall(text)) + len(EN_HEDGE.findall(text)))


# chatbot wrapper around the real text: a preface line, a closing offer, separators (R19)
WRAP_HEAD = re.compile(
    r"^[ \t]*(?:(?:certainly|sure|of course|absolutely|okay|ok)[!.,]?[ \t]+)?(?:here(?:'s| is| are)|below is)[^\n]{0,80}"
    r"(?:response|reply|version|draft|email|message|rewrite|text|translation|post|caption|summary|letter)[^\n]{0,60}:[ \t]*$"
    r"|^[ \t]*(?:물론이?죠|네,? (?:알겠습니다|좋아요)|알겠습니다)[!.,]?[^\n]{0,100}(?:답장|답변|초안|버전|메일|메시지|글|문안)[^\n]{0,40}[:.!]?[ \t]*$", re.I)
WRAP_TAIL = re.compile(
    r"^[ \t]*(?:let me know if you'?d like|would you like me to|I can also (?:make|adjust|shorten|rewrite|change)|feel free to ask)[^\n]*$"
    r"|^[ \t]*(?:더 )?(?:필요하시면|원하시면|수정이 필요하면|다른 버전이 필요하면)[^\n]{0,80}(?:말씀해 ?주세요|알려 ?주세요)[.!]?[ \t]*$", re.I)
HR_LINE = re.compile(r"^[ \t]*(?:-{3,}|\*{3,}|_{3,})[ \t]*$")


def strip_wrapper(before: str, after: str):
    """Drop chatbot wrapper lines the rewrite removed, so they do not count as deleted text."""
    lines = before.split("\n")
    nonblank = [i for i, l in enumerate(lines) if l.strip()]
    head, tail = set(nonblank[:3]), set(nonblank[-3:])
    kept = {l.strip() for l in after.split("\n")}
    drop = {i for i in head if WRAP_HEAD.match(lines[i]) and lines[i].strip() not in kept}
    drop |= {i for i in tail if WRAP_TAIL.match(lines[i]) and lines[i].strip() not in kept}
    if not drop:
        return before, 0
    drop |= {i for i, l in enumerate(lines) if HR_LINE.match(l) and l.strip() not in kept}
    return "\n".join(l for i, l in enumerate(lines) if i not in drop), len(drop)


MARKER = re.compile(r"\s?\[(?:필자 확인|출처 필요|writer to confirm|writer check|source needed)[^\]\n]{0,160}\]", re.I)


def strip_markers(text: str):
    found = MARKER.findall(text)
    return MARKER.sub("", text), len(found)


# 'played a key role in developing X' -> 'I developed X' turns a shared role into a solo one (R17)
ROLE_IN = re.compile(r"\b(?:I|we|he|she|they)(?:'ve| have| had| has)?\s+(?:also\s+)?(?:play(?:s|ed|ing)?|ha[sd] had|have had|had) "
                     r"(?:a |an |the )?(?:[\w-]+ )?(?:role|part|hand) in ([a-z]{3,}?)ing\b", re.I)


def contribution_check(before: str, after: str):
    """Return (phrase, 'up'|'down') for each 'role in X-ing' whose share changed in the rewrite."""
    out = []
    for m in ROLE_IN.finditer(before):
        stem = m.group(1)
        solo = re.compile(rf"\b(?:I|we)\s+(?:have\s+|had\s+)?{stem}e?d\b", re.I)
        down = re.compile(rf"\b(?:help(?:ed|s)?|assist(?:ed|s)?|support(?:ed|s)?)(?: to| with| in)? {stem}", re.I)
        if solo.search(after) and not solo.search(before):
            out.append((m.group(0), "up"))
        elif down.search(after) and not down.search(before):
            out.append((m.group(0), "down"))
    return out


def sentences(text: str):
    t = CODE.sub(" ", text)
    return [s.strip() for s in SENT_SPLIT.split(t) if s and len(s.strip()) >= 2]


def _norm(s: str) -> str:
    return re.sub(r"[\s*_#>`\-]+", "", s)


LEAD = re.compile(r"^(?:다만|그러나|하지만|또한|물론|However|But|Also|Still),?\s*", re.I)


def _key(s: str) -> str:
    return _norm(LEAD.sub("", s.strip()))


def moved_sentences(before: str, after: str):
    """Sentences of the original that reappear elsewhere in the rewrite (moved, not deleted)."""
    keys_a = {_key(x) for x in sentences(after)}
    sb = sentences(before)
    sm = difflib.SequenceMatcher(None, [_norm(x) for x in sb], [_norm(x) for x in sentences(after)], autojunk=False)
    gone = [sb[i] for op, i1, i2, _, _ in sm.get_opcodes() if op in ("delete", "replace") for i in range(i1, i2)]
    return [x for x in gone if len(_key(x)) >= 8 and _key(x) in keys_a]


def mood_check(before: str, after: str) -> dict:
    """Align sentences; compare markers inside rewritten blocks, report deleted ones apart."""
    sb, sa = sentences(before), sentences(after)
    moved = {_key(x) for x in moved_sentences(before, after)}
    sm = difflib.SequenceMatcher(None, [_norm(x) for x in sb], [_norm(x) for x in sa], autojunk=False)
    res = {"ought": [0, 0], "hedge": [0, 0], "drops": [], "deleted_ought": [], "deleted_hedge": 0, "unattributed": []}
    tb = marks(before)
    ta = marks(after)
    res["ought"] = [tb[0], ta[0]]
    res["hedge"] = [tb[1], ta[1]]
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "delete":
            for s in sb[i1:i2]:
                if _key(s) in moved:
                    continue
                o, h = marks(s)
                if o:
                    res["deleted_ought"].append(s[:80])
                res["deleted_hedge"] += h
        elif op == "replace":
            _replace_block([x for x in sb[i1:i2] if _key(x) not in moved], sa[j1:j2], res)
    return res


def _replace_block(bs, as_, res):
    """Pair each original sentence with its closest rewrite; unpaired originals count as deleted.

    A rewrite fails the mood check when it loses an ought marker, or when sentences that carried
    a hedge end up with none (collapsing a double hedge to a single one is allowed).
    """
    groups = {}
    block_ok = sum(marks(x)[0] for x in as_) >= sum(marks(x)[0] for x in bs)
    for s in bs:
        best, score = None, 0.0
        for j, t in enumerate(as_):
            r = difflib.SequenceMatcher(None, _norm(s), _norm(t), autojunk=False).ratio()
            if r > score:
                best, score = j, r
        if best is None or score < 0.35:
            o, h = marks(s)
            if o and not block_ok:
                res["deleted_ought"].append(s[:80])
            res["deleted_hedge"] += h
            continue
        groups.setdefault(best, []).append(s)
    for j, srcs in groups.items():
        ob = sum(marks(x)[0] for x in srcs)
        hb = sum(marks(x)[1] for x in srcs)
        oa, ha = marks(as_[j])
        if oa > ob and hb == 0 and sum(marks(x)[0] for x in as_) > sum(marks(x)[0] for x in bs):
            res["drops"].append({"before": " ".join(srcs)[:160], "after": as_[j][:160],
                                 "ought": f"{ob}->{oa} (strengthened)", "hedge": f"{hb}->{ha}"})
            continue
        if (oa < ob and not block_ok) or (hb > 0 and ha == 0):
            res["drops"].append({"before": " ".join(srcs)[:160], "after": as_[j][:160],
                                 "ought": f"{ob}->{oa}", "hedge": f"{hb}->{ha}"})
        had = any(KO_ATTR.search(x) or EN_ATTR.search(x) for x in srcs)
        if had and not (KO_ATTR.search(as_[j]) or EN_ATTR.search(as_[j])):
            res["unattributed"].append({"before": " ".join(srcs)[:160], "after": as_[j][:160]})


def grade(rates: dict, after_tally: dict, verdict: int) -> str:
    if verdict == 2:
        return "D"
    s1, s2 = after_tally["S1"], after_tally["S2"]
    if s1 == 0 and s2 <= 2 and verdict == 0:
        return "A"
    if s1 == 0 and s2 <= 4 and rates["rewrite"] < REWRITE_WARN:
        return "B"
    return "C"


def linebreak_warn(after: str):
    hits = lint.inline_sentence_ends(after)
    if not hits:
        return None
    lines = sorted({li for li, _ in hits})
    first = after.splitlines()[lines[0]].strip()[:60]
    return ("linebreak", f"{len(lines)} line(s) hold more than one sentence (first: \"{first}\"). Break the line after each "
                         "sentence-ending period (python scripts/linebreak.py IN OUT). Keep a line whole only where the format "
                         "forbids a break (subtitle line, table cell, title, one-line field) and say so: --allow linebreak=reason")


def compare(before: str, after: str, lang: str = "auto", allow=None, reason: str = "", quotes: str = "double",
            genre: str | None = None, linebreak: bool = False, style: str | None = None) -> dict:
    before, after = lint.normalize(before), lint.normalize(after)
    after_marked = after
    after, n_marks = strip_markers(after)
    core, wrapped = strip_wrapper(before, after)
    rates = edit_rates(core, after)
    mv = moved_sentences(before, after)
    if mv:
        n_tok = max(1, len(tokens(core)))
        shift = sum(len(tokens(x)) for x in mv) / n_tok
        rates["delete"] = round(max(0.0, rates["delete"] - shift), 4)
        rates["rewrite"] = round(max(0.0, rates["rewrite"] - shift), 4)
    lb = lint.analyze(before, lang, quotes or False, 5, genre, style)
    la = lint.analyze(after_marked, lang, quotes or False, 5, genre, style)
    ib, ia = invariants(before), invariants(after)
    md = mood_check(before, after)

    fails, warns, notes = [], [], []
    if before.strip() == after.strip():
        notes.append("unchanged: no edits were made")
    if wrapped:
        notes.append(f"{wrapped} chatbot wrapper line(s) (preface, closing offer, separators) left out of the edit rates")
    if n_marks:
        notes.append(f"{n_marks} writer-check marker(s) ([필자 확인]/[출처 필요]/[writer to confirm]/[source needed]) left out of the check; resolve them before sending")
    if mv:
        notes.append(f"{len(mv)} sentence(s) moved, not deleted (left out of the delete rate)")
    cb, ca = len(CERTAIN.findall(before)), len(CERTAIN.findall(after))
    if ca < cb:
        warns.append(("certainty", f"certainty statements fell {cb}->{ca} ('I am confident', '확신합니다'). "
                                   "Keep the writer's confidence and the claim it carries, in plain words"))
    for c, way in contribution_check(before, after)[:3]:
        what = "a shared role became a solo action ('I ...ed')" if way == "up" else "a key role became a supporting one ('helped ...')"
        warns.append(("contribution", f"{what}: '{c}'. Keep the stated degree in plain words ('had a central part in developing'), "
                                      "or mark [writer to confirm: led, co-led, or supported?]"))
    if rates["rewrite"] >= REWRITE_ABORT:
        fails.append(f"rewrite rate {rates['rewrite']:.1%} >= 50%: over-rewritten, roll back")
    elif rates["rewrite"] >= REWRITE_WARN:
        warns.append(("rewrite", f"rewrite rate {rates['rewrite']:.1%} >= 30%: check for over-polishing"))
    if rates["delete"] >= DELETE_ABORT:
        fails.append(f"delete rate {rates['delete']:.1%} >= 60%: too much removed, roll back")
    elif rates["delete"] >= DELETE_WARN:
        warns.append(("delete", f"delete rate {rates['delete']:.1%} >= 40%: confirm every deleted sentence was empty filler"))

    for key, label in (("numbers", "numbers"), ("urls", "URLs")):
        gone = sorted(set(ib[key]) - set(ia[key]))
        if gone:
            fails.append(f"lost {label}: {', '.join(gone[:8])}")
        fewer = sorted(k for k in ib[key] if k in ia[key] and ia[key][k] < ib[key][k])
        if fewer:
            warns.append(("numbers", f"{label} appear fewer times (fine if a duplicate sentence was cut): {', '.join(fewer[:8])}"))
    miss_code = lost(ib["code"], ia["code"])
    if miss_code:
        fails.append(f"lost or changed code: {', '.join(c[:40] for c in miss_code[:5])}")
    added_nums = sorted(set(ia["numbers"]) - set(ib["numbers"]))
    if added_nums:
        fails.append(f"new numbers not in the original: {', '.join(added_nums[:8])}")
    miss_q = lost(ib["quotes"], ia["quotes"])
    if miss_q:
        warns.append(("quotes", "quoted spans changed or removed (restore if they are direct quotes): " + " | ".join(miss_q[:5])))

    for d in md["drops"][:5]:
        warns.append(("mood", f"mood changed in a rewritten sentence (ought {d['ought']}, hedge {d['hedge']}): "
                              f"\"{d['before']}\" -> \"{d['after']}\""))
    for u in md["unattributed"][:5]:
        warns.append(("attribution", "a claim lost its attribution and now reads as the writer's own statement "
                                     f"(keep the source, mark [source needed], or cut the claim): \"{u['before']}\" -> \"{u['after']}\""))
    if md["deleted_ought"]:
        warns.append(("deleted-ought", "deleted sentences carried must/should markers; confirm they were filler: "
                      + " | ".join(md["deleted_ought"][:3])))
    if md["deleted_hedge"]:
        notes.append(f"{md['deleted_hedge']} hedge marker(s) were inside deleted sentences (list the deletions in the report)")

    rhythm = {"KO-E1", "EN-L1", "EN-L3"}
    sev_after = {f["id"]: f["sev"] for f in la["findings"]}
    rose = [(rid, n) for rid, n in la["counts"].items() if n > lb["counts"].get(rid, 0)]
    soft = [f"{rid} {lb['counts'].get(rid, 0)}->{n}" for rid, n in rose if rid in rhythm and sev_after.get(rid) == "S3"]
    if soft:
        notes.append("sentence-rhythm signal rose (often from deleting short filler); vary one or two sentences if easy: " + ", ".join(soft))
    injected = [f"{rid} {lb['counts'].get(rid, 0)}->{n}" for rid, n in rose if not (rid in rhythm and sev_after.get(rid, "S3") == "S3")]
    if injected:
        warns.append(("inject", "patterns added by the rewrite: " + ", ".join(injected)))

    s1_left = [f["id"] for f in la["findings"] if f["sev"] == "S1"]
    if s1_left:
        warns.append(("s1", "S1 left: " + ", ".join(s1_left)))
    if rates["rewrite"] + rates["delete"] < 0.05 and s1_left:
        warns.append(("s1", "under-rewritten: under 5% edited while S1 remains"))
    lw = linebreak_warn(after) if linebreak else None
    if lw:
        warns.append(lw)

    return apply_allow(_finish(fails, warns, notes, rates, lb, la, md), allow if isinstance(allow, dict) else set(allow or ()), reason)


def compare_write(brief: str, after: str, lang: str = "auto", allow=None, reason: str = "", quotes: str = "double",
                  genre: str | None = None, linebreak: bool = False, style: str | None = None) -> dict:
    brief, after = lint.normalize(brief), lint.normalize(after)
    after_marked = after
    after, n_marks = strip_markers(after)
    la = lint.analyze(after_marked, lang, quotes or False, 5, genre, style)
    ib, ia = invariants(brief), invariants(after)
    fails, warns, notes = [], [], []
    new_nums = sorted(set(ia["numbers"]) - set(ib["numbers"]))
    if new_nums:
        fails.append(f"numbers not in the brief (invented?): {', '.join(new_nums[:8])}")
    new_urls = sorted(set(ia["urls"]) - set(ib["urls"]))
    if new_urls:
        fails.append(f"URLs not in the brief: {', '.join(new_urls[:5])}")
    if n_marks:
        notes.append(f"{n_marks} writer-check marker(s) left out of the check; remove them before sending")
    missing = sorted(set(ib["numbers"]) - set(ia["numbers"]))
    if missing:
        notes.append(f"brief numbers not used (labels and word limits are fine; check facts): {', '.join(missing[:10])}")
    left = [f["id"] for f in la["findings"] if f["sev"] in ("S1", "S2")]
    if left:
        warns.append(("s1", "S1/S2 in the draft: " + ", ".join(left)))
    lw = linebreak_warn(after) if linebreak else None
    if lw:
        warns.append(lw)
    zero = {"rewrite": 0.0, "delete": 0.0, "overall": 0.0}
    return apply_allow(_finish(fails, warns, notes, zero, {"tally": {"S1": 0, "S2": 0, "S3": 0}}, la, None, mode="write"),
                       allow if isinstance(allow, dict) else set(allow or ()), reason)


def _finish(fails, warns, notes, rates, lb, la, md, mode="rewrite"):
    return {
        "mode": mode,
        "fails": fails,
        "warns": warns,
        "notes": notes,
        "rates": rates,
        "before": lb["tally"],
        "after": la["tally"],
        "mood": None if md is None else {"ought": md["ought"], "hedge": md["hedge"]},
        "after_findings": [{"id": f["id"], "sev": f["sev"], "name": f["name"], "count": f["count"]} for f in la["findings"]],
    }


def parse_allow(items, default_reason: str = "") -> dict:
    """['mood=G2 collapse', 'delete'] -> {'mood': 'G2 collapse', 'delete': default_reason}"""
    out = {}
    for it in items or ():
        it = str(it).strip()
        if "=" in it:  # one key with a free-text reason (commas allowed)
            k, _, why = it.partition("=")
            out[k.strip()] = why.strip() or default_reason
            continue
        for k in it.split(","):
            if k.strip():
                out[k.strip()] = default_reason
    return out


def apply_allow(r: dict, allow, reason: str) -> dict:
    allow = allow if isinstance(allow, dict) else {k: reason for k in (allow or ())}
    kept, allowed = [], []
    for key, msg in r["warns"]:
        (allowed if key in allow else kept).append((key, msg))
    r["allowed"] = [{"key": k, "warn": m, "reason": allow[k]} for k, m in allowed]
    r["warns"] = kept
    verdict = 2 if r["fails"] else (1 if kept else 0)
    r["verdict"] = verdict
    r["grade"] = grade(r["rates"], r["after"], verdict) if r["mode"] == "rewrite" else (
        "D" if verdict == 2 else ("A" if verdict == 0 else "C"))
    return r


def format_report(r: dict) -> str:
    names = {0: "PASS", 1: "WARN", 2: "REJECT"}
    b, a, rt = r["before"], r["after"], r["rates"]
    head = f"newspeak gate [{r['mode']}] | {names[r['verdict']]} | grade {r['grade']}"
    if r["mode"] == "rewrite":
        head += f" | rewrite {rt['rewrite']:.1%} delete {rt['delete']:.1%}"
    out = [head, f"  S1 {b['S1']}->{a['S1']}  S2 {b['S2']}->{a['S2']}  S3 {b['S3']}->{a['S3']}"]
    if r.get("mood"):
        m = r["mood"]
        out.append(f"  ought {m['ought'][0]}->{m['ought'][1]}  hedge {m['hedge'][0]}->{m['hedge'][1]} (whole text)")
    for f in r["fails"]:
        out.append(f"  FAIL  {f}")
    for _, w in r["warns"]:
        out.append(f"  WARN  {w}")
    for al in r.get("allowed", []):
        out.append(f"  ALLOWED [{al['key']}] {al['warn']}  -- reason: {al['reason']}")
    for n in r["notes"]:
        out.append(f"  NOTE  {n}")
    return "\n".join(out)


def main(argv=None) -> int:
    lint._configure_stdout()
    ap = argparse.ArgumentParser(description="Compare a rewrite against its original, or a draft against its brief.")
    ap.add_argument("before", help="original text (rewrite) or brief (write)")
    ap.add_argument("after")
    ap.add_argument("--mode", default="rewrite", choices=["rewrite", "write"])
    ap.add_argument("--lang", default="auto", choices=["auto", "ko", "en"])
    ap.add_argument("--allow", action="append", default=[],
                    help="accept a warning: KEY=reason (repeatable), or KEY[,KEY] with --reason")
    ap.add_argument("--reason", default="", help="default reason for --allow keys given without one")
    ap.add_argument("--include-quotes", action="store_true",
                    help="also lint text inside double quotes (default: direct quotes are skipped)")
    ap.add_argument("--genre", choices=sorted(lint.GENRE_LEVELS), default=None,
                    help="sns = social posts and YouTube descriptions, chat = messenger (passed to lint)")
    ap.add_argument("--style", choices=["ste"], default=None,
                    help="ste = reports and documents: ASD-STE100 sentence and paragraph limits (passed to lint)")
    ap.add_argument("--no-linebreak", action="store_true",
                    help="skip the one-sentence-per-line check (default: on)")
    ap.add_argument("--json", action="store_true")
    try:
        a = ap.parse_args(argv)
        allow = parse_allow(a.allow, a.reason.strip())
        if any(not why for why in allow.values()):
            missing = ", ".join(k for k, why in allow.items() if not why)
            print(f"gate error: no reason for --allow {missing}. Use --allow KEY=reason (one key each) or --reason", file=sys.stderr)
            return 3
        fn = compare_write if a.mode == "write" else compare
        r = fn(lint.read_text(a.before), lint.read_text(a.after), a.lang, allow, a.reason.strip(),
               quotes=None if a.include_quotes else "double", genre=a.genre,
               linebreak=not a.no_linebreak, style=a.style)
    except SystemExit as e:
        return 3 if e.code not in (0, None) else 0
    except Exception as e:
        print(f"gate error: {type(e).__name__}: {e}", file=sys.stderr)
        return 3
    if a.json:
        out = dict(r)
        out["warns"] = [m for _, m in r["warns"]]
        print(json.dumps(out, ensure_ascii=False, indent=1))
    else:
        print(format_report(r))
    return r["verdict"]


if __name__ == "__main__":
    sys.exit(main())
