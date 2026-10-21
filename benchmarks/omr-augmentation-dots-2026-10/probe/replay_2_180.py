"""ROADMAP 2.180 -- replay a WHOLE 20261018-night record (per-page slices from benchmarks/omr-bar-sum-holdout-2026-09/probe/
pages_2_165.py; no gather, no detector) through ADJUDICATE..INFER..second EVALUATE (review.rerun.run_stages == pipeline.decide)
and then EXPORT (export.to_musicxml), OMR_DOT_POSITION_OVER_WEDGE off vs on (everything else = this tree's defaults).
Measures the EXPORTED FILE. Per arm writes OUTDIR/<doc>.<arm>.json {glyph live duration + dot_role, report digest, xml counts},
OUTDIR/<doc>.<arm>.musicxml, and OUTDIR/<doc>.<arm>.record.json (mini record for `judged score`).
usage: replay_2_180.py DOC SLICEDIR OUTDIR ARM[,ARM...]     ARM = off | on"""
import collections
import glob
import json
import os
import re
import sys
import time

sys.path.insert(0, ".")
from tools.omr import acceptance as A  # noqa: E402
from tools.omr.staged import export as E  # noqa: E402
from tools.omr.staged.review import rerun as RR  # noqa: E402

DOC, SD, OUTDIR, ARMS = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4].split(",")
D = os.path.join(SD, DOC)
FLAG = "OMR_DOT_POSITION_OVER_WEDGE"
ENV = {"off": "0", "on": "1"}
JUDGED_Q = {"duration", "notehead_is_not_a_notehead", "unboxed_ink_is_a_rest", "notehead_is_an_eighth_rest", "arc_kind"}
os.makedirs(OUTDIR, exist_ok=True)


def rows(kind):
    out = []
    for p in sorted(glob.glob(os.path.join(D, "*.%s.jsonl" % kind))):
        out += [json.loads(l) for l in open(p)]
    return out


def live(verdicts, quantity):
    chains = collections.defaultdict(list)
    for v in verdicts:
        if v["quantity"] == quantity and v["subject"].startswith("glyph/"):
            chains[v["subject"]].append(v)
    out = {}
    for g, ch in chains.items():
        sup = {x.get("supersedes") for x in ch if x.get("supersedes")}
        out[g] = ([x for x in ch if x["id"] not in sup] or ch)[-1]
    return out


def brief(v):
    val = v["value"] if isinstance(v["value"], dict) else {}
    return [v["outcome"][:4], val.get("written"), val.get("dots"), v.get("decider"), v.get("reason"),
            sorted({((c.get("value") or {}).get("written"), (c.get("value") or {}).get("dots")) for c in (v.get("candidates") or [])
                    if isinstance(c.get("value"), dict)}, key=str) or None]


t0 = time.time()
rec = {"observations": rows("observations"), "abstentions": rows("abstentions"), "verdicts": []}
boxes, seen = [], set()
for o in rec["observations"]:
    s = o.get("subject") or ""
    if s.startswith("glyph/") and s not in seen and isinstance((o.get("detail") or {}).get("bbox_page_px"), list):
        seen.add(s)
        boxes.append({k: o.get(k) for k in ("id", "subject", "quantity", "detail")})
print(DOC, "rows", len(rec["observations"]), "%.0fs" % (time.time() - t0), flush=True)
for arm in ARMS:
    os.environ[FLAG] = ENV[arm]
    log, _ = RR.rebuild_gather(rec)
    RR.run_stages(log)
    result = {"record": log.to_json(), "summary": log.summary()}
    del log
    vs = result["record"]["verdicts"]
    dur = {g: brief(v) for g, v in live(vs, "duration").items()}
    role = {g: [v["outcome"][:4], v.get("value") if isinstance(v.get("value"), str) else None, v.get("reason"),
                (v.get("detail") or {}).get("head")] for g, v in live(vs, "dot_role").items()}
    t1 = time.time()
    xml, report = E.to_musicxml(result)
    notes = re.findall(r"<note\b.*?</note>", xml, flags=re.S)
    dotted = sum(1 for n in notes if "<dot/>" in n and "<rest" not in n)
    R = E.Record({"record": {"observations": [], "abstentions": [], "verdicts": vs}})
    guessed = collections.Counter()
    for g in dur:
        gs = E.guess_of(R, g)
        if gs:
            guessed[gs["rule"]] += 1
    red = report.get("bars_written_red") or {}
    try:
        bau = A.bars_add_up(xml)
        bau = {k: v for k, v in bau.items() if not isinstance(v, (list, dict))}
    except Exception as e:  # a control; never let it sink the run
        bau = {"error": str(e)[:200]}
    out = dict(doc=DOC, arm=arm, dur=dur, role=role,
               xml=dict(notes=len(notes), pitched=sum(1 for n in notes if "<rest" not in n), dotted_notes=dotted,
                        dots=xml.count("<dot/>")),
               written=report.get("written"), bars_written_red=red.get("bars"), red_rows=red.get("noteheads_and_rests"),
               notes_not_written_total=report.get("notes_not_written_total"), notes_not_written=report.get("notes_not_written"),
               guessed_by_rule=dict(guessed), bars_add_up=bau,
               dot_role_balance=report.get("dot_role_balance"))
    json.dump(out, open(os.path.join(OUTDIR, "%s.%s.json" % (DOC, arm)), "w"), default=str)
    open(os.path.join(OUTDIR, "%s.%s.musicxml" % (DOC, arm)), "w").write(xml)
    json.dump({"observations": boxes, "abstentions": [], "verdicts": [v for v in vs if v["quantity"] in JUDGED_Q]},
              open(os.path.join(OUTDIR, "%s.%s.record.json" % (DOC, arm)), "w"), default=str)
    print(DOC, arm, "notes", len(notes), "dotted", dotted, "red", red.get("bars"), "export %.0fs" % (time.time() - t1),
          "total %.0fs" % (time.time() - t0), flush=True)
    del vs, result, xml
