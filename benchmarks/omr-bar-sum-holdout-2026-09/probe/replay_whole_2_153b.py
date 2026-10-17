"""ROADMAP 2.153b -- replay a WHOLE night record's GATHER rows (re-assembled from the per-page slices; no gather, no detector)
through INFER with review.rerun (2.157-fixed), flag `OMR_BEAM_LEVEL_NEEDS_A_JOINED_STEM` OFF vs ON. Every other flag shipped.
Why whole, not per page: a page slice's EVALUATE lacks the meter carried from earlier pages (Litolff p11 with one context page:
160 whole rests + 10 bar picks differ from the stored record; with all eleven preceding pages: 0), so the per-page replay is
faithful for ADJUDICATE only.
CONTROL: the OFF arm's live duration verdict vs the stored live one, every glyph (must be ~0 differ).
usage: replay_whole_2_153b.py DOC SLICEDIR OUT.json   -> OUT.json {doc, glyphs, control, changed{glyph:{off,on}}}"""
import collections
import glob
import json
import os
import sys
import time

sys.path.insert(0, ".")
sys.path.insert(0, "benchmarks/omr-bar-sum-holdout-2026-09/probe")
from tools.omr.staged.review import rerun as RR  # noqa: E402

DOC, SD, OUT = sys.argv[1:4]
D = os.path.join(SD, DOC)
FLAG = "OMR_BEAM_LEVEL_NEEDS_A_JOINED_STEM"


def rows(kind):
    out = []
    for p in sorted(glob.glob(os.path.join(D, "*.%s.jsonl" % kind))):
        out += [json.loads(l) for l in open(p)]
    return out


def live(verdicts):
    chains = collections.defaultdict(list)
    for v in verdicts:
        if v["quantity"] == "duration" and v["subject"].startswith("glyph/"):
            chains[v["subject"]].append(v)
    out = {}
    for g, ch in chains.items():
        sup = {x.get("supersedes") for x in ch if x.get("supersedes")}
        out[g] = ([x for x in ch if x["id"] not in sup] or ch)[-1]
    return out


def brief(v):
    if v is None:
        return None
    val = v["value"] if isinstance(v["value"], dict) else {}
    return dict(outcome=v["outcome"], written=val.get("written"), dots=val.get("dots"), beats=val.get("beats"),
                decider=v.get("decider"), reason=v.get("reason"),
                cands=sorted({(c.get("value") or {}).get("beats") for c in (v.get("candidates") or [])
                              if isinstance(c.get("value"), dict)} - {None}) or None)


def key(b):
    return None if b is None else (b["outcome"], b["written"], b["dots"], b["beats"], tuple(b["cands"] or ()))


t0 = time.time()
rec = {"observations": rows("observations"), "abstentions": rows("abstentions"), "verdicts": []}
stored = {g: brief(v) for g, v in live(rows("verdicts")).items()}
print(DOC, "rows", len(rec["observations"]), len(rec["abstentions"]), "stored glyphs", len(stored), flush=True)
arms = {}
for arm, val in (("off", None), ("on", "1")):
    if val is None:
        os.environ.pop(FLAG, None)
    else:
        os.environ[FLAG] = val
    log, _ = RR.rebuild_gather(rec)
    RR.run_stages(log)
    arms[arm] = {g: brief(v) for g, v in live(log.to_json()["verdicts"]).items()}
    del log
    print(DOC, arm, len(arms[arm]), "%.0fs" % (time.time() - t0), flush=True)
os.environ.pop(FLAG, None)
ctl = collections.Counter("agree" if key(arms["off"].get(g)) == key(b) else "differ" for g, b in stored.items())
ctl_rows = [dict(glyph=g, stored=b, off=arms["off"].get(g)) for g, b in stored.items() if key(arms["off"].get(g)) != key(b)]
changed = {g: dict(off=arms["off"].get(g), on=arms["on"].get(g))
           for g in sorted(set(arms["off"]) | set(arms["on"])) if key(arms["off"].get(g)) != key(arms["on"].get(g))}
json.dump(dict(doc=DOC, glyphs=len(arms["off"]), control=dict(ctl), control_rows=ctl_rows[:200], changed=changed,
               seconds=round(time.time() - t0)), open(OUT, "w"), indent=0)
print(DOC, "glyphs", len(arms["off"]), "control", dict(ctl), "changed", len(changed), "%.0fs" % (time.time() - t0),
      flush=True)
