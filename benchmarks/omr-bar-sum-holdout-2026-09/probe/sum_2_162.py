"""ROADMAP 2.162 -- fold `replay_2_162.py` arms: per pair (A -> B), glyphs changed (whole rests vs notes, by kind), whole-rest
lengths against the dossier meter, meter verdicts that change, and the 2.153b Set F tiles 5/8/11/15.
Dossier bar length (catalog witness): Litolff Beethoven 5/i 2/4 = 2.0; Brahms 1/i 6/8 = 3.0 (one 9/8 bar, measure 8).
usage: sum_2_162.py OUTDIR OUT.json"""
import collections
import json
import os
import sys

OUTDIR, OUT = sys.argv[1:3]
DOSSIER = {"litolff": 2.0, "brahms": 3.0}
SET_F = {"litolff": {"glyph/12/1/3/9/1": ("tile 8", 0.5), "glyph/13/0/2/2/2": ("tile 15", 0.5)},
         "brahms": {"glyph/3/1/4/2/2": ("tile 5", 0.75), "glyph/17/1/9/0/4": ("tile 11", 0.25)}}
PAIRS = (("base", "mine"), ("b153", "both"), ("base", "b153"), ("base", "both"))


def load(doc, arm):
    p = os.path.join(OUTDIR, "%s.%s.json" % (doc, arm))
    return json.load(open(p)) if os.path.exists(p) else None


def k(b):
    return None if b is None else (b["outcome"], b["written"], b["dots"], b["beats"], tuple(b["cands"] or ()))


def whole_rest(b):
    return b is not None and b["rest"] and b.get("rest_glyph") == "restWhole"


def kind(a, b):
    if a is None or b is None:
        return "appears/vanishes"
    if a["outcome"] == b["outcome"] == "decided":
        return "decided -> another value" if (a["beats"], a["written"]) != (b["beats"], b["written"]) else "same value, another decider"
    return "%s -> %s" % (a["outcome"], b["outcome"])


res = {}
for doc in ("litolff", "brahms"):
    arms = {a: load(doc, a) for a in ("base", "mine", "b153", "both")}
    res[doc] = {"control": (arms["base"] or {}).get("control"),
                "unknown_moves": {a: (v or {}).get("unknown_moves") for a, v in arms.items()}}
    # whole-rest lengths per arm vs the dossier
    wr = {}
    for a, v in arms.items():
        if v is None:
            continue
        c = collections.Counter()
        for g, b in v["glyphs"].items():
            if whole_rest(b) and b["outcome"] == "decided":
                c["= dossier" if abs((b["beats"] or 0) - DOSSIER[doc]) < 1e-6 else "%s beats" % b["beats"]] += 1
        wr[a] = dict(c)
    res[doc]["whole_rests"] = wr
    res[doc]["set_f"] = {lab: {a: (v["glyphs"].get(g) or {}).get("beats") if v else None for a, v in arms.items()}
                         | {"sean": want, "decider": {a: (v["glyphs"].get(g) or {}).get("decider") for a, v in arms.items() if v}}
                         for g, (lab, want) in SET_F[doc].items()}
    for A, B in PAIRS:
        if arms[A] is None or arms[B] is None:
            continue
        ga, gb = arms[A]["glyphs"], arms[B]["glyphs"]
        ch = [g for g in sorted(set(ga) | set(gb)) if k(ga.get(g)) != k(gb.get(g))]
        rests = [g for g in ch if whole_rest(ga.get(g)) or whole_rest(gb.get(g))]
        notes = [g for g in ch if g not in rests]
        rest_dir = collections.Counter("%s -> %s" % ((ga.get(g) or {}).get("beats"), (gb.get(g) or {}).get("beats")) for g in rests)
        rest_pages = collections.Counter(g.split("/")[1] for g in rests)
        note_kinds = collections.Counter(kind(ga.get(g), gb.get(g)) for g in notes)
        via = collections.Counter("%s/%s" % ((gb.get(g) or {}).get("decider"), (gb.get(g) or {}).get("reason")) for g in notes)
        ma, mb = arms[A]["meters"], arms[B]["meters"]
        mch = {s: {"A": ma.get(s), "B": mb.get(s)} for s in sorted(set(ma) | set(mb))
               if (ma.get(s) or {}).get("outcome") != (mb.get(s) or {}).get("outcome")
               or (ma.get(s) or {}).get("segments") != (mb.get(s) or {}).get("segments")}
        res[doc]["%s->%s" % (A, B)] = dict(
            glyphs_changed=len(ch), whole_rests_changed=len(rests), whole_rest_beats=dict(rest_dir),
            whole_rest_pages=dict(sorted(rest_pages.items(), key=lambda x: int(x[0]))), notes_changed=len(notes),
            note_kinds=dict(note_kinds), note_now_by=dict(via.most_common(12)), meters_changed=len(mch),
            meters=dict(list(mch.items())[:40]),
            notes=[{"glyph": g, "A": ga.get(g), "B": gb.get(g)} for g in notes])
json.dump(res, open(OUT, "w"), indent=1, default=str)
for doc, r in res.items():
    print("==", doc, "control", r["control"], "unknown_moves", r["unknown_moves"])
    print("   whole rests:", r["whole_rests"])
    print("   set F:", {lab: {a: v[a] for a in ("base", "mine", "b153", "both", "sean")} for lab, v in r["set_f"].items()})
    for pk in ("%s->%s" % p for p in PAIRS):
        if pk in r:
            x = r[pk]
            print("  ", pk, "glyphs", x["glyphs_changed"], "rests", x["whole_rests_changed"], x["whole_rest_beats"],
                  "pages", x["whole_rest_pages"], "notes", x["notes_changed"], x["note_kinds"], "meters", x["meters_changed"])
