"""ROADMAP 2.168 -- replay a WHOLE 20261016-night record (per-page slices from `pages_2_162.py`; no gather, no detector) through
ADJUDICATE..INFER with review.rerun, flag OFF vs ON (everything else = main: 2.162 block ON, 2.153 off).
  off -- OMR_BAR_DISAGREES_BLUE=0          on -- OMR_BAR_DISAGREES_BLUE=1
Per arm writes OUTDIR/<doc>.<arm>.json {glyphs: {glyph: brief}, meters, marked: [...], guessed_by_rule}, and
OUTDIR/<doc>.<arm>.record.json (mini record for `judged score`).
`marked` = live duration verdicts with reason bar_disagrees_with_decided; `guessed_by_rule` = `export.guess_of` over every glyph
(the EXPORT's own GUESSED test), so the blue count is the exporter's, not ours.
usage: replay_2_168.py DOC SLICEDIR OUTDIR ARM[,ARM...]"""
import collections
import glob
import json
import os
import sys
import time

sys.path.insert(0, ".")
from tools.omr.staged import export as E  # noqa: E402
from tools.omr.staged.review import rerun as RR  # noqa: E402

DOC, SD, OUTDIR, ARMS = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4].split(",")
D = os.path.join(SD, DOC)
FLAG = "OMR_BAR_DISAGREES_BLUE"
ENV = {"off": "0", "on": "1"}
JUDGED_Q = {"duration", "notehead_is_not_a_notehead", "unboxed_ink_is_a_rest", "notehead_is_an_eighth_rest", "arc_kind"}
os.makedirs(OUTDIR, exist_ok=True)


def rows(kind):
    out = []
    for p in sorted(glob.glob(os.path.join(D, "*.%s.jsonl" % kind))):
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


def brief(v):
    if v is None:
        return None
    val = v["value"] if isinstance(v["value"], dict) else {}
    return dict(outcome=v["outcome"], written=val.get("written"), dots=val.get("dots"), beats=val.get("beats"),
                beam_levels=val.get("beam_levels"), rest=bool(val.get("is_rest")), measure_rest=bool(val.get("measure_rest")),
                decider=v.get("decider"), reason=v.get("reason"),
                cands=sorted({(c.get("value") or {}).get("beats") for c in (v.get("candidates") or [])
                              if isinstance(c.get("value"), dict)} - {None}) or None)


def meter_brief(v):
    val = v["value"] if isinstance(v["value"], dict) else {}
    return dict(outcome=v["outcome"], num=val.get("numerator"), den=val.get("denominator"),
                segments=[(s.get("from_cell"), s.get("numerator"), s.get("denominator")) for s in (val.get("segments") or [])])


t0 = time.time()
rec = {"observations": rows("observations"), "abstentions": rows("abstentions"), "verdicts": []}
boxes, seen = [], set()
for o in rec["observations"]:
    s = o.get("subject") or ""
    if s.startswith("glyph/") and s not in seen and isinstance((o.get("detail") or {}).get("bbox_page_px"), list):
        seen.add(s)
        boxes.append({k: o.get(k) for k in ("id", "subject", "quantity", "detail")})
print(DOC, "rows", len(rec["observations"]), len(rec["abstentions"]), flush=True)
for arm in ARMS:
    os.environ[FLAG] = ENV[arm]
    log, _ = RR.rebuild_gather(rec)
    RR.run_stages(log)
    vs = log.to_json()["verdicts"]
    del log
    glyph_live = live(vs, "duration", "glyph/")
    glyphs = {g: brief(v) for g, v in glyph_live.items()}
    meters = {s: meter_brief(v) for s, v in live(vs, "meter", "system/").items()}
    marked = []
    for g, v in glyph_live.items():
        if v.get("reason") == "bar_disagrees_with_decided":
            marked.append(dict(glyph=g, kept=brief(v),
                               alternative=[c["value"] for c in v["candidates"]][1], detail=v.get("detail")))
    R = E.Record({"record": {"observations": [], "abstentions": [], "verdicts": vs}})
    by_rule = collections.Counter()
    for g in glyph_live:
        gs = E.guess_of(R, g)
        if gs:
            by_rule[gs["rule"]] += 1
    out = dict(doc=DOC, arm=arm, glyphs=glyphs, meters=meters, marked=marked, guessed_by_rule=dict(by_rule))
    json.dump(out, open(os.path.join(OUTDIR, "%s.%s.json" % (DOC, arm)), "w"), default=str)
    json.dump({"observations": boxes, "abstentions": [], "verdicts": [v for v in vs if v["quantity"] in JUDGED_Q]},
              open(os.path.join(OUTDIR, "%s.%s.record.json" % (DOC, arm)), "w"), default=str)
    del vs
    print(DOC, arm, "glyphs", len(glyphs), "marked", len(marked), "guessed", dict(by_rule), "%.0fs" % (time.time() - t0), flush=True)
