"""2.152 -- Sean's judged tiles, normalised to {doc, glyph, kind, beats|what, ...}. Sean's words only (answers.json / the
committed judged index); nothing of ours decides what is right.

    python3 tiles.py OUT.json [A150.json M150.json]    (A150/M150 = out/print/2.150-review from lane-2.150-rests-global)

kind: note (beats = written value in quarters, dotted included) | rest | nonnote (what = named by Sean) | stem_for_rest.
"""
import json
import os
import sys

sys.path.insert(0, "tools/.." if False else ".")
from tools.omr.staged import judged  # noqa: E402

PRINT = "out/print/"
BEATS = {"1": 4.0, "2": 2.0, "4": 1.0, "8": 0.5, "16": 0.25, "32": 0.125, "dot 2": 3.0, "dot 4": 1.5, "dot 8": 0.75,
         "dot 16": 0.375, "dot 1": 6.0, "dotted 4": 1.5, "dot2": 3.0, "dot4": 1.5, "dot8": 0.75}
NONNOTE = ("beam", "barline", "clef", "natural", "key flat", "part of", "meter", "trem", "f dyn", "sf", "C clef")


def kind_of(s):
    """(kind, beats|what) from a short answer of the 2.14x/2.15x galleries."""
    t = s.strip().lower()
    if t in BEATS:
        return "note", BEATS[t]
    if t.endswith("rest"):
        return "rest", t
    if "stem" == t:
        return "stem_for_rest", "stem"
    return "nonnote", t


def recent():
    out = []
    # 2.145 -- rests read as heads (declined / stem-touched); two meter digits
    a = json.load(open(PRINT + "2.145-review/answers.json"))
    for t in a["tiles"]:
        k, w = kind_of(t["sean"]) if "rest" in t["sean"] else ("nonnote", t["sean"])
        out.append(dict(item="2.145", n=t["n"], doc=t["document"], glyph=t["glyph"], kind=k, what=w, sean=t["sean"],
                        role=t["role"]))
    # 2.146 -- note values, dotted/plain, both docs
    a = json.load(open(PRINT + "2.146-review/answers.json"))
    fix = {15: "2", 13: "4"}   # Sean's follow-up line: 15 is a half note, 13 definitely a quarter
    for t in a["tiles"]:
        s = fix.get(t["n"], t["sean"])
        k, w = kind_of(s)
        out.append(dict(item="2.146", n=t["n"], doc=t["doc"], glyph=t["glyph"], kind=k, what=w, sean=s,
                        role=t.get("rule")))
    # 2.148 -- Litolff (FINDINGS 2.148: "Sean's 30 Litolff tiles")
    a = json.load(open(PRINT + "2.148-review/answers.json"))
    for t in a["tiles"]:
        s = t["sean"]
        k, w = kind_of(s)
        if s == "whole rest":
            k, w = "rest", "whole rest"
        out.append(dict(item="2.148", n=t["n"], doc="litolff", glyph=t["glyph"], kind=k, what=w, sean=s, role=None))
    # 2.151 -- Brahms p0-p3 (the p0-p3 ink record); Sean's verbatim line, parsed by hand from answers.json 'sean'
    a = json.load(open(PRINT + "2.151-review/answers.json"))
    nn = {11: "part of an 8 rest", 12: "part of an sf dynamic", 14: "trem slash", 15: "f dynamic", 19: "trem slash",
          30: "clef"}
    for t in a["tiles"]:
        s = t["sean"]
        if t["n"] in nn:
            k, w = "nonnote", nn[t["n"]]
        else:
            k, w = kind_of(s)
        out.append(dict(item="2.151", n=t["n"], doc="brahms_p0p3", glyph=t["glyph"], kind=k, what=w, sean=s,
                        role=t["role"]))
    return out


def r150(a_path, m_path):
    a = json.load(open(a_path))
    m = {t["n"]: t for t in json.load(open(m_path))["tiles"]}
    out = []
    for t in a["tiles"]:
        s = t["sean"]
        k, w = ("rest", "quarter rest") if s == "quarter rest" else ("stem_for_rest", s)
        if s == "barline":
            k, w = "nonnote", "barline"
        out.append(dict(item="2.150", n=t["n"], doc=m[t["n"]]["document"], glyph=t["glyph"], kind=k, what=w, sean=s,
                        role=t["role"], page_box=m[t["n"]]["page_box_600dpi"], width_spaces_then=t["width_spaces"]))
    return out


def indexed(skip_items):
    d = json.load(open(judged.INDEX_PATH))["tiles"]
    out = []
    for x in d:
        if x["item"] in skip_items or x["subject_kind"] != "glyph" or x["doc"] not in ("litolff", "brahms"):
            continue
        if x["answer_kind"] == "not_a_note":
            k, w = "nonnote", x["value"]
        elif x["answer_kind"] == "rest":
            k, w = "rest", x["value"]
        elif x["answer_kind"] == "duration":
            k, w = "note", x["value"]
        else:
            continue
        out.append(dict(item=x["item"], n=x["tile"], doc=x["doc"], glyph=x["subject"], kind=k, what=w,
                        sean=x["answer"], role="control" if x["control"] else None, page_box=x["page_box"],
                        src="index"))
    return out


if __name__ == "__main__":
    res = recent()
    if len(sys.argv) > 3:
        res += r150(sys.argv[2], sys.argv[3])
    res += indexed({"2.145-review", "2.146-review", "2.148-review", "2.151-review", "2.150-review"})
    json.dump(res, open(sys.argv[1], "w"), indent=0)
    from collections import Counter
    print(len(res), Counter((r["item"], r["doc"]) for r in res).most_common(12))
    print(Counter(r["kind"] for r in res))
