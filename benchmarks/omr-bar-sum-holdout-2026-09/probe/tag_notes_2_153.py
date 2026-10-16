"""ROADMAP 2.153 -- score ALL of Sean's judged NOTE tiles of a document against the CURRENT code (STAGED; the slice's own
GATHER rows re-decided through INFER) in one or more ARMS, and tag each tile with the mechanism features of the first
`adjudicate_duration` verdict. Truth = Sean's written value only.
usage: tag_notes_2_153.py SLICE.json DOC OUT.json ARM [ARM ...]      ARM = name  or  name:ENV=val,ENV2=val
  e.g.  base   arm:OMR_BEAM_NEEDS_A_JOINED_STEM=1
OUT[arm][glyph] = {item, n, sean, ours, outcome, right, cands, reason, decider, chain, feats}"""
import json
import os
import sys

sys.path.insert(0, ".")
SL, DOC, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
ARMS = sys.argv[4:] or ["base"]
tiles = json.load(open("out/2.153/notes.json"))[DOC]
rec = json.load(open(SL))
from tools.omr.staged.record import Q  # noqa: E402
from tools.omr.staged.review import rerun as RR  # noqa: E402
sys.path.insert(0, "benchmarks/omr-bar-sum-holdout-2026-09/probe")
import replay_util_2_153 as RU  # noqa: E402

FEATS = ("head_is_open", "beam_evidence", "stems_attached", "beams_by_stem", "levels_certain", "levels_possible",
         "beams_neighbour_staff", "beams_decided_arc", "beams_beyond_stem", "yolo_beams", "cv_beams", "flag_levels",
         "dots_attached", "beam_side", "head", "beam_stem_levels")
EPS = 1e-6


def live(chain):
    sup = {v.get("supersedes") for v in chain if v.get("supersedes")}
    l = [v for v in chain if v["id"] not in sup]
    return (l or chain)[-1]


present = {x["subject"] for x in rec["observations"]}
res = {}
for arm in ARMS:
    name, _, env = arm.partition(":")
    saved = {}
    for kv in [e for e in env.split(",") if e]:
        k, v = kv.split("=")
        saved[k] = os.environ.get(k)
        os.environ[k] = v
    log, _ = RU.rebuild(rec)
    RR.run_stages(log)
    d = log.to_json()
    by = {}
    for v in d["verdicts"]:
        if v["quantity"] == Q.DURATION:
            by.setdefault(v["subject"], []).append(v)
    out = {}
    for t in tiles:
        g = t["glyph"]
        ch = by.get(g)
        if not ch:
            out[g] = dict(item=t["item"], n=t["n"], sean=t["sean"], missing=True, in_slice=g in present)
            continue
        L = live(ch)
        first = next((v for v in ch if v.get("decider") == "adjudicate_duration"), None)
        f = {k: (first.get("detail") or {}).get(k) for k in FEATS} if first else {}
        val = L["value"] if isinstance(L["value"], dict) else {}
        cands = [c.get("value", {}).get("written") for c in (L.get("candidates") or [])]
        w = val.get("written")
        if L["outcome"] == "decided" and w is not None and not val.get("is_rest"):
            right = abs(w - t["beats"]) < EPS
        elif L["outcome"] == "narrowed":
            right = any(c is not None and abs(c - t["beats"]) < EPS for c in cands)
        else:
            right = None
        out[g] = dict(item=t["item"], n=t["n"], sean=t["sean"], beats=t["beats"], outcome=L["outcome"], ours=w,
                      cands=cands or None, right=right, reason=L["reason"], decider=L.get("decider"),
                      first_reason=first["reason"] if first else None, first_outcome=first["outcome"] if first else None,
                      chain=[(v["decider"], v["reason"], v["outcome"]) for v in ch], feats=f, is_rest=val.get("is_rest"))
    res[name] = out
    for k, v in saved.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
    n = [x for x in out.values() if not x.get("missing")]
    print(name, "tiles found", len(n), "of", len(out), "| decided right %d wrong %d | narrowed holding %d not %d" % (
        sum(1 for x in n if x["outcome"] == "decided" and x["right"]), sum(1 for x in n if x["outcome"] == "decided" and x["right"] is False),
        sum(1 for x in n if x["outcome"] == "narrowed" and x["right"]), sum(1 for x in n if x["outcome"] == "narrowed" and x["right"] is False)),
        flush=True)
json.dump(res, open(OUT, "w"), indent=1, default=str)
