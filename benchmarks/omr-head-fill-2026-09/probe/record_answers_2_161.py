"""ROADMAP 2.161 -- record Sean's answers (2026-10-17) in the judged-index format: answers.json tiles {n, doc, glyph, sean,
off, on, control, verdict}; manifest.json gets the (now answered) tile -> glyph list so `judged build` joins them.
usage: record_answers_2_161.py W161DIR   (replay2161_<doc>.json from replay_pages_2_161.py)"""
import json
import os
import sys

W = sys.argv[1]
KEY = json.load(open("out/2.161/tiles-key.json"))
VERBATIM = "Set G 1.2 2.2 3.1 4.2 5.2"
SEAN = {1: "2", 2: "2", 3: "1", 4: "2", 5: "2"}
R = {d: json.load(open(os.path.join(W, "replay2161_%s.json" % d)))["changed"] for d in ("litolff", "brahms")}
# Unchanged by the flag: both arms are the stored verdict (the replay control matched it on every Brahms glyph).
STORED = {"glyph/4/0/3/3/8": None, "glyph/5/0/2/3/2": "1.0"}


def w(b):
    if not b:
        return None
    return str(b["written"]) if b["written"] is not None else "|".join(str(c) for c in b["cands"] or [])


tiles, man = [], []
for k in KEY:
    n = k["tile"]
    c = R[k["doc"]].get(k["subject"])
    s = SEAN[n]
    off = w(c.get("adj_off")) if c else "unchanged"
    on = w(c.get("adj_on")) if c else "unchanged"
    ctl = k["why"].startswith("control")
    if ctl:
        want = "2" if k["why"] == "control_half" else "4"
        verdict = "control right" if s == want else "control WRONG"
        if k["subject"] == "glyph/5/0/2/3/2":
            verdict = ("control CONFLICT: we write a quarter (decided, stem_tip_reads_no_beam, both arms); Sean said 4 on "
                       "the same head at 2.154-review tile 4 and 1 here")
    else:
        verdict = "right" if s == "2" and on == "2.0" else "WRONG"
    tiles.append(dict(n=n, doc=k["doc"], glyph=k["subject"], sean=s, off=off, on=on, control=ctl, verdict=verdict))
    man.append(dict(n=n, doc=k["doc"], glyph=k["subject"], control=ctl))
json.dump(dict(answered="2026-10-17", verbatim=VERBATIM,
               question="What is the written value of the note in the blue box (1, 2, 4, 8 ..., dot, or not a note)?",
               tiles=tiles), open("out/print/2.161-review/answers.json", "w"), indent=1)
m = json.load(open("out/print/2.161-review/manifest.json"))
m["tiles"] = man
json.dump(m, open("out/print/2.161-review/manifest.json", "w"), indent=1)
for t in tiles:
    print(t)
