"""ROADMAP 2.153b -- fold the whole-record replays (replay_whole_2_153b.py) into: changes per plate by kind, and Sean's judged tiles
before (flag OFF) / after (flag ON) on the changed notes. Sean's values: sean_2_153b.load() (judged index glyph rows + every
answers.json tile that names a glyph) -- his answer is the truth.
usage: sum_2_153b.py OUT.json"""
import collections
import glob
import json
import os
import sys

sys.path.insert(0, ".")
sys.path.insert(0, "benchmarks/omr-bar-sum-holdout-2026-09/probe")
import sean_2_153b  # noqa: E402

OUT = sys.argv[1]
SEAN, NAMED = sean_2_153b.load()


def vs(b, want):
    if b is None:
        return "not_found"
    if b["outcome"] == "decided" and b["beats"] is not None:
        return "right" if abs(b["beats"] - want) < 1e-6 else "wrong"
    if b["outcome"] == "narrowed":
        return "narrowed-holding" if any(abs(c - want) < 1e-6 for c in b["cands"] or ()) else "narrowed-not"
    return "abstained"


def show(b):
    if b is None:
        return "none"
    if b["outcome"] == "decided":
        return "%g" % b["beats"] if b["beats"] is not None else "decided?"
    return "%s%s" % (b["outcome"][:3], b["cands"] or "")


rep = {}
for doc in ("litolff", "brahms"):
    try:
        w = json.load(open("out/2.153b/whole_%s.json" % doc))
    except FileNotFoundError:
        continue
    pp = {}
    for g, d in w["changed"].items():
        pp.setdefault(g.split("/")[1], {})[g] = d
    r = {"pages": {p: dict(glyphs=0, control={}, changed=c) for p, c in pp.items()}}
    r["pages"].setdefault("-1", dict(glyphs=w["glyphs"], control=w["control"], changed={}))
    kinds, judged, ctl, rows = collections.Counter(), collections.Counter(), collections.Counter(), []
    glyphs = 0
    for p, pg in sorted(r["pages"].items(), key=lambda t: int(t[0])):
        glyphs += pg["glyphs"]
        ctl.update(pg["control"])
        for g, d in pg["changed"].items():
            o, n = d["off"], d["on"]
            kind = "%s -> %s" % ("decided" if o and o["outcome"] == "decided" else (o or {}).get("outcome"),
                                 (n or {}).get("outcome"))
            kinds[kind] += 1
            row = dict(glyph=g, page=int(p), off=o, on=n, off_s=show(o), on_s=show(n), judged=g in NAMED)
            if g in SEAN.get(doc, {}):
                src, want = SEAN[doc][g]
                row.update(sean=want, src=src, off_vs=vs(o, want), on_vs=vs(n, want))
                judged["%s -> %s" % (row["off_vs"], row["on_vs"])] += 1
            rows.append(row)
    trans = collections.Counter("%s -> %s" % (x["off_s"], x["on_s"]) for x in rows)
    rep[doc] = dict(pages=len(r["pages"]), glyphs=glyphs, control=dict(ctl), changed=len(rows), kinds=dict(kinds),
                    transitions=dict(trans.most_common()), judged=dict(judged),
                    unjudged=sum(1 for x in rows if not x["judged"]), rows=rows)
    per_page = collections.Counter(x["page"] for x in rows)
    rep[doc]["per_page"] = dict(sorted(per_page.items()))
    print("== %s: %d pages, %d glyphs, control OFF vs stored %s; changed %d (unjudged %d)"
          % (doc, len(per_page), glyphs, dict(ctl), len(rows), rep[doc]["unjudged"]))
    print("   kinds", dict(kinds))
    print("   transitions", dict(trans.most_common(12)))
    print("   judged", dict(judged))
    for x in rows:
        if "sean" in x:
            print("     %-26s %-22s sean %g  off %s (%s) -> on %s (%s)" % (x["glyph"], x["src"], x["sean"], x["off_s"],
                  (x["off"] or {}).get("reason"), x["on_s"], (x["on"] or {}).get("reason")))
# every glyph Sean judged on this doc: OFF (= stored; the whole-replay control is 100% agree) vs ON
SD = ("/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-start-here-go-cbd2bc/"
      "97504ff3-7ad5-4ac2-8be1-95887e8a9382/scratchpad/slices")


def _live(ch):
    sup = {x.get("supersedes") for x in ch if x.get("supersedes")}
    return ([x for x in ch if x["id"] not in sup] or ch)[-1]


def _brief(v):
    val = v["value"] if isinstance(v["value"], dict) else {}
    return dict(outcome=v["outcome"], beats=val.get("beats"), reason=v.get("reason"),
                cands=sorted({(c.get("value") or {}).get("beats") for c in (v.get("candidates") or [])
                              if isinstance(c.get("value"), dict)} - {None}) or None)


for doc in rep:
    want = SEAN.get(doc, {})
    chains = collections.defaultdict(list)
    for p in glob.glob(os.path.join(SD, doc, "p*.verdicts.jsonl")):
        for line in open(p):
            v = json.loads(line)
            if v["subject"] in want:
                chains[v["subject"]].append(v)
    changed = {x["glyph"]: x["on"] for x in rep[doc]["rows"]}
    tot = {"off": collections.Counter(), "on": collections.Counter()}
    for g, (src, val) in want.items():
        st = _brief(_live(chains[g])) if chains.get(g) else None
        tot["off"][vs(st, val)] += 1
        tot["on"][vs(changed[g] if g in changed else st, val)] += 1
    rep[doc]["judged_all"] = {k: dict(v) for k, v in tot.items()}
    print(doc, "all judged glyphs", len(want), "OFF", dict(tot["off"]), "ON", dict(tot["on"]))
json.dump(rep, open(OUT, "w"), indent=1)
