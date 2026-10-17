"""ROADMAP 2.153b -- replay each page of a night record through INFER (review.rerun, fixed 2.157), flag OFF vs ON.

Slice = the `common` rows + page p-1 (context: the meter carried in) + page p; only page p's glyphs are reported. One page at a
time, in this process, serially. The flag `OMR_BEAM_LEVEL_NEEDS_A_JOINED_STEM` is read at call time, so both arms run here;
every other flag is the shipped default (main e75bc907 = records' 1d42c4aa + ledger rows).
CONTROL: the OFF arm's live duration verdict vs the record's stored live one, per glyph (counts agree / differ).
usage: replay_pages_2_153b.py DOC SLICEDIR OUT.json [PAGE ...]
"""
import collections
import glob
import json
import os
import sys
import time

sys.path.insert(0, ".")
from tools.omr.staged.review import rerun as RR  # noqa: E402

DOC, SD, OUT = sys.argv[1:4]
D = os.path.join(SD, DOC)
FLAG = "OMR_BEAM_LEVEL_NEEDS_A_JOINED_STEM"
pages = sorted(int(os.path.basename(p)[1:3]) for p in glob.glob(os.path.join(D, "p*.observations.jsonl")))
if sys.argv[4:]:
    pages = [int(x) for x in sys.argv[4:]]


def rows(tag, kind):
    p = os.path.join(D, "%s.%s.jsonl" % (tag, kind))
    if not os.path.exists(p):
        return []
    return [json.loads(l) for l in open(p)]


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


common = {k: rows("common", k) for k in ("observations", "abstentions")}
report = json.load(open(OUT)) if os.path.exists(OUT) else {"doc": DOC, "pages": {}}
for p in pages:
    if str(p) in report["pages"]:
        continue
    t0 = time.time()
    tags = ["p%02d" % (p - 1), "p%02d" % p] if p > 0 else ["p%02d" % p]
    rec = {k: list(common[k]) + [r for t in tags for r in rows(t, k)] for k in ("observations", "abstentions")}
    rec["verdicts"] = []
    stored = {g: brief(v) for g, v in live(rows("p%02d" % p, "verdicts")).items()}
    arms = {}
    for arm, val in (("off", None), ("on", "1")):
        if val is None:
            os.environ.pop(FLAG, None)
        else:
            os.environ[FLAG] = val
        log, _ = RR.rebuild_gather(rec)
        RR.run_stages(log)
        arms[arm] = {g: brief(v) for g, v in live(log.to_json()["verdicts"]).items() if int(g.split("/")[1]) == p}
    os.environ.pop(FLAG, None)
    ctl = collections.Counter("agree" if key(arms["off"].get(g)) == key(b) else "differ" for g, b in stored.items())
    changed = {g: dict(off=arms["off"].get(g), on=arms["on"].get(g))
               for g in sorted(set(arms["off"]) | set(arms["on"])) if key(arms["off"].get(g)) != key(arms["on"].get(g))}
    report["pages"][str(p)] = dict(glyphs=len(arms["off"]), control=dict(ctl), changed=changed,
                                   seconds=round(time.time() - t0, 1))
    json.dump(report, open(OUT, "w"), indent=0)
    print(DOC, "p", p, "glyphs", len(arms["off"]), "control", dict(ctl), "changed", len(changed),
          "%.0fs" % (time.time() - t0), flush=True)
