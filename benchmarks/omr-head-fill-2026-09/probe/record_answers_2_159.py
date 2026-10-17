"""ROADMAP 2.159 -- record Sean's answers (2026-10-17) in the judged-index format: answers.json tiles {n, doc, glyph, sean,
off, on, verdict}; manifest.json gets the (now answered) tile -> glyph list so `judged build` joins them.
usage: record_answers_2_159.py"""
import json

KEY = json.load(open("out/2.159/tiles-key.json"))
VERBATIM = "1. Ff 2. 2 3.2 4.trem slashes 5.4 6.2 7-8.2"
SEAN = {1: "ff", 2: "2", 3: "2", 4: "trem slashes", 5: "4", 6: "2", 7: "2", 8: "2"}
R = {d: json.load(open("out/2.159/replay_%s.json" % d))["changed"] for d in ("litolff", "brahms")}


def w(b):
    if not b:
        return None
    return str(b["written"]) if b["written"] is not None else "|".join(str(c) for c in b["cands"] or [])


tiles, man = [], []
for k in KEY:
    n = k["tile"]
    c = R[k["doc"]].get(k["subject"]) or {}
    s = SEAN[n]
    on = w(c.get("adj_on"))
    if k["why"].startswith("control"):
        verdict = "control right" if (s == "2") == (k["why"] == "control_half") else "control WRONG"
    elif s in ("2",):
        verdict = "right" if on == "2.0" else "WRONG"
    else:
        verdict = "NOT A NOTE"
    tiles.append(dict(n=n, doc=k["doc"], glyph=k["subject"], sean=s, off=w(c.get("adj_off")), on=on,
                      control=k["why"].startswith("control"), verdict=verdict))
    man.append(dict(n=n, doc=k["doc"], glyph=k["subject"], control=k["why"].startswith("control")))
json.dump(dict(answered="2026-10-17", verbatim=VERBATIM,
               question="What is the written value of the note in the blue box (1, 2, 4, 8 ..., dot, or not a note)?",
               tiles=tiles), open("out/print/2.159-review/answers.json", "w"), indent=1)
m = json.load(open("out/print/2.159-review/manifest.json"))
m["tiles"] = man
json.dump(m, open("out/print/2.159-review/manifest.json", "w"), indent=1)
for t in tiles:
    print(t)
