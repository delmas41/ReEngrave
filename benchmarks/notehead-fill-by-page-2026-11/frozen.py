"""ROADMAP 2.326 small test (read-only, scratch), measure 5: on the frozen sample (lane-report slices), the code's count of
notehead boxes whose value is left blue / narrowed / abstained BECAUSE OF A FILL READING, and what the head's own trimmed
ink (in_dark, the trimmed slit) would say of each -- a count of CHANGES, not of fixes.

    python3 benchmarks/notehead-fill-by-page-2026-11/frozen.py
"""
import json
import pathlib
from collections import Counter

SL = pathlib.Path("/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/lane-report-slices-20261117-night")
W = pathlib.Path(__file__).parent / "work"
FROZEN = {"litolff": {2, 4, 6, 8, 9, 10, 11, 16}, "brahms": {0, 4, 5, 8, 12, 14, 19, 25}}
FILL_REASONS = {"head_fill_from_ink", "whole_class_filled_or_stemmed", "whole_class_filled_on_a_stem", "open_head_flag_contradiction",
                "second_hollow_unclear", "second_only_unclear", "second_hollow_filled"}


def own_reading(m, hi):
    """What the trimmed head's own ink says (scratch rule, not product): solid where the inside is as black as the page's solid
    heads (in_dark >= 0.98; every page's solid median is 1.0) and the trimmed slit holds no paper; hollow where the inside is
    clearly lighter (in_dark <= 0.90) and the slit holds paper (>= 0.18); else between."""
    if not m or m.get("box_from") != "trimmed" or m.get("in_dark") is None:
        return "unread"
    s = (hi or {}).get("slit")
    if m["in_dark"] >= 0.98 and (s is None or s <= 0.06):
        return "solid"
    if m["in_dark"] <= 0.90 and s is not None and s >= 0.18:
        return "hollow"
    return "between"


def main():
    for doc in ("litolff", "brahms"):
        pages = {h["subject"]: h for h in json.load(open(W / ("pages-%s.json" % doc)))["heads"]
                 if int(h["subject"].split("/")[1]) in FROZEN[doc]}
        meas = json.load(open(W / ("measures-%s.json" % doc)))
        chain = {}
        with open(SL / doc / "verdicts.jsonl") as f:
            for line in f:
                if '"quantity": "duration"' not in line or '"glyph/' not in line[:60]:
                    continue
                v = json.loads(line)
                if v["subject"] in pages:
                    chain.setdefault(v["subject"], []).append((v.get("decider") or "", v.get("reason"), v.get("outcome"),
                                                                bool(((v.get("detail") or {}).get("head_ink_guess") or {}).get("marks_blue"))))
        c = Counter()
        ex = {}
        for s, h in pages.items():
            n = h.get("notehead_is_not_a_notehead") or {}
            if n.get("outcome") == "decided" and n.get("value") is True:
                continue
            ch = chain.get(s) or []
            if not ch:
                continue
            adj = [x for x in ch if not x[0].startswith(("infer", "evaluate"))] or ch
            first = adj[-1]
            stand = ch[-1]
            cause = None
            if first[3]:
                cause = "blue: head_ink_hollow_over_black (box not head-sized; 2.220 guess)"
            elif first[1] in FILL_REASONS:
                cause = "%s %s" % (first[2], first[1])
            if cause is None:
                continue
            if stand is not first and stand[0].startswith("infer"):
                cause += " -> INFER %s (blue)" % stand[1]
            hi = ((h.get("obs") or {}).get("head_ink") or {}).get("detail")
            r = own_reading(meas.get(s), hi)
            c[(cause, r)] += 1
            ex.setdefault((cause, r), []).append(s)
        print("\n== %s frozen sample: notehead boxes whose value a FILL reading left blue / narrowed / abstained (code's count)" % doc)
        tot = Counter()
        for (cause, r), n in sorted(c.items()):
            tot[cause] += n
            print("   %-95s own ink says %-8s %4d   e.g. %s" % (cause, r, n, ", ".join(ex[(cause, r)][:2])))
        print("   totals:", dict(tot))
        json.dump({"%s|%s" % k: v for k, v in ex.items()}, open(W / ("frozen-%s.json" % doc), "w"))


if __name__ == "__main__":
    main()
