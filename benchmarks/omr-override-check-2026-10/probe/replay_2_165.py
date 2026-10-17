"""ROADMAP 2.165 -- replay a WHOLE 20261016-night record's GATHER rows (the per-page slices `pages_2_162.py` cut; no
gather, no detector) through INFER with review.rerun (2.157-fixed), one arm at a time. STAGED ADJUDICATE..INFER.

Arms (everything else at shipped defaults):
  base -- OMR_ONE_OVERRIDE_CHECK off (= main + 2.162 merged, its flag off)
  on   -- OMR_ONE_OVERRIDE_CHECK on (which also turns 2.162's bar-length helper on: the guard's hook)

Writes per arm OUTDIR/<doc>.<arm>.json:
  glyphs     {glyph: brief of the standing duration, with its class READ / GUESSED / UNREAD}
  stems      {glyph: (outcome, reason) of Q.STEM_VALUE}
  meters     {system: brief}
  near_misses (on arm) [{row, why, subject, quantity, attempted brief, prior brief}]
and OUTDIR/<doc>.<arm>.record.json, a mini record for `python3 -m tools.omr.staged.judged score`.
usage: replay_2_165.py DOC SLICEDIR OUTDIR ARM[,ARM...] [PAGE]   (PAGE e.g. p05: that page + common only)"""
import collections
import glob
import json
import os
import sys
import time

sys.path.insert(0, ".")
from tools.omr.staged.review import rerun as RR  # noqa: E402

DOC, SD, OUTDIR, ARMS = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4].split(",")
PAGE = sys.argv[5] if len(sys.argv) > 5 else None
D = os.path.join(SD, DOC)
FLAG = "OMR_ONE_OVERRIDE_CHECK"
ENV = {"base": "0", "on": "1"}
JUDGED_Q = {"duration", "notehead_is_not_a_notehead", "unboxed_ink_is_a_rest", "notehead_is_an_eighth_rest", "arc_kind",
            "stem_value"}
GUESSERS = ("reconcile_duration",)
os.makedirs(OUTDIR, exist_ok=True)


def rows(kind):
    out = []
    for p in sorted(glob.glob(os.path.join(D, "*.%s.jsonl" % kind))):
        name = os.path.basename(p).split(".")[0]
        if PAGE and name not in (PAGE, "common"):
            continue
        out += [json.loads(l) for l in open(p)]
    return out


def live(verdicts, quantity, prefix):
    chains = collections.defaultdict(list)
    for v in verdicts:
        if v["quantity"] == quantity and v["subject"].startswith(prefix):
            chains[v["subject"]].append(v)
    out = {}
    for g, ch in chains.items():
        sup = {x.get("supersedes") for x in ch if x.get("supersedes")}
        out[g] = ([x for x in ch if x["id"] not in sup] or ch)[-1]
    return out


def is_guess_chain(v, by_id):
    seen = set()
    while v is not None and v["id"] not in seen:
        seen.add(v["id"])
        d = v.get("decider") or ""
        if d.startswith("infer:") or d in GUESSERS or (d == "share_stem_value" and (v.get("detail") or {}).get("guessed")):
            return True
        v = by_id.get(v.get("supersedes")) if v.get("supersedes") else None
    return False


def brief(v, by_id=None, stem=None):
    if v is None:
        return None
    val = v["value"] if isinstance(v["value"], dict) else {}
    d = v.get("detail") or {}
    if v["outcome"] != "decided" or (stem and stem[0] == "narrowed" and stem[1] == "stem_heads_disagree"
                                     and os.environ.get(FLAG) == "1" and not val.get("is_rest")):
        cls = "UNREAD"
    elif by_id is not None and is_guess_chain(v, by_id):
        cls = "GUESSED"
    else:
        cls = "READ"
    return dict(outcome=v["outcome"], written=val.get("written"), dots=val.get("dots"), beats=val.get("beats"),
                levels=val.get("beam_levels"), decider=v.get("decider"), reason=v.get("reason"),
                rest=bool(val.get("is_rest")), cls=cls, likely_misreading=bool(d.get("likely_misreading")),
                cands=sorted({(c.get("value") or {}).get("beats") for c in (v.get("candidates") or [])
                              if isinstance(c.get("value"), dict)} - {None}) or None)


def meter_brief(v):
    val = v["value"] if isinstance(v["value"], dict) else {}
    return dict(outcome=v["outcome"], reason=v.get("reason"), num=val.get("numerator"), den=val.get("denominator"))


t0 = time.time()
rec = {"observations": rows("observations"), "abstentions": rows("abstentions"), "verdicts": []}
boxes, seen = [], set()
for o in rec["observations"]:
    s = o.get("subject") or ""
    if s.startswith("glyph/") and s not in seen and isinstance((o.get("detail") or {}).get("bbox_page_px"), list):
        seen.add(s)
        boxes.append({k: o.get(k) for k in ("id", "subject", "quantity", "detail")})
print(DOC, PAGE or "whole", "rows", len(rec["observations"]), len(rec["abstentions"]), flush=True)
for arm in ARMS:
    os.environ[FLAG] = ENV[arm]
    log, _ = RR.rebuild_gather(rec)
    RR.run_stages(log)
    js = log.to_json()
    vs = js["verdicts"]
    nm = js.get("near_misses", [])
    del log, js
    by_id = {v["id"]: v for v in vs}
    stems = {g: (v["outcome"], v.get("reason")) for g, v in live(vs, "stem_value", "glyph/").items()}
    glyphs = {g: brief(v, by_id, stems.get(g)) for g, v in live(vs, "duration", "glyph/").items()}
    meters = {s: meter_brief(v) for s, v in live(vs, "meter", "system/").items()}
    misses = []
    for m in nm:
        att = m.get("attempted") or {}
        pr = by_id.get(m.get("prior")) if m.get("prior") else None
        misses.append(dict(row=m["row"], why=m["why"], subject=m["subject"], quantity=m["quantity"],
                           attempted=brief(att) if att else None, prior=brief(pr) if pr else None,
                           attempted_decider=att.get("decider"), attempted_reason=att.get("reason")))
    out = dict(doc=DOC, arm=arm, page=PAGE, glyphs=glyphs, stems=stems, meters=meters, near_misses=misses,
               rows=dict(collections.Counter(m["row"] for m in misses)))
    json.dump(out, open(os.path.join(OUTDIR, "%s.%s.json" % (DOC, arm)), "w"))
    json.dump({"observations": boxes, "abstentions": [], "verdicts": [v for v in vs if v["quantity"] in JUDGED_Q]},
              open(os.path.join(OUTDIR, "%s.%s.record.json" % (DOC, arm)), "w"), default=str)
    del vs, by_id
    print(DOC, arm, "glyphs", len(glyphs), "meters", len(meters), "near_misses", len(misses),
          dict(collections.Counter(m["row"] for m in misses)), "%.0fs" % (time.time() - t0), flush=True)
