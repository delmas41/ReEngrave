"""ROADMAP 2.176 -- replay a 20261018-night record (per-page slices; no gather, no detector) through ADJUDICATE..INFER..second EVALUATE
(review.rerun.run_stages) AND THEN EXPORT (`export.to_musicxml`), flag OFF vs ON. Measures the EXPORTED FILE.
  off -- OMR_HEAD_ON_ANOTHER_MARK=0     on -- OMR_HEAD_ON_ANOTHER_MARK=1     (everything else = main defaults)
Writes OUTDIR/<doc>.<arm>.json {glyphs{g: brief}, refusals{g: [value, reason]}, coverage, notes_in_xml, held_bars} per arm.
usage: replay_2_176.py DOC SLICEDIR OUTDIR ARM[,ARM...]"""
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
FLAG = "OMR_HEAD_ON_ANOTHER_MARK"
ENV = {"off": "0", "on": "1"}
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
    val = v["value"] if isinstance(v["value"], dict) else {}
    return dict(outcome=v["outcome"], written=val.get("written"), dots=val.get("dots"), beats=val.get("beats"),
                rest=bool(val.get("is_rest")), measure_rest=bool(val.get("measure_rest")), decider=v.get("decider"), reason=v.get("reason"))


t0 = time.time()
rec = {"observations": rows("observations"), "abstentions": rows("abstentions"), "verdicts": []}
print(DOC, "rows", len(rec["observations"]), len(rec["abstentions"]), "%.0fs" % (time.time() - t0), flush=True)
KEEP = ("bars_held_out_sum", "partial_bars", "guessed", "written", "notes_not_written_total", "balance")
for arm in ARMS:
    os.environ[FLAG] = ENV[arm]
    log, _ = RR.rebuild_gather(rec)
    RR.run_stages(log)
    result = {"record": log.to_json(), "summary": log.summary()}
    del log
    vs = result["record"]["verdicts"]
    glyph_live = live(vs, "duration", "glyph/")
    glyphs = {g: brief(v) for g, v in glyph_live.items()}
    refusals = {g: [v["value"], v.get("reason"), v.get("margin")] for g, v in live(vs, "notehead_is_not_a_notehead", "glyph/").items()
                if v["value"] is True}
    t1 = time.time()
    xml, report = E.to_musicxml(result)
    print(DOC, arm, "export %.0fs" % (time.time() - t1), flush=True)
    cov = {k: report.get(k) for k in KEEP}
    cov["bars_held_out_sum"] = {k: v for k, v in (report.get("bars_held_out_sum") or {}).items() if k != "held"}
    cov["partial_bars"] = {k: v for k, v in (report.get("partial_bars") or {}).items() if not isinstance(v, list) or k == "stay_held_by_reason"}
    held_bars = (report.get("bars_held_out_sum") or {}).get("held", [])
    nfile = {k: v for k, v in (report.get("written") or {}).items()}
    out = dict(doc=DOC, arm=arm, glyphs=glyphs, refusals=refusals, coverage=cov, notes_in_xml=xml.count("<note"),
               held_bars=[(h["page"], h["system"], h["staff"], h["cell"]) for h in held_bars],
               not_a_notehead={k: v for k, v in report.items() if "not_a_notehead" in str(k)})
    json.dump(out, open(os.path.join(OUTDIR, "%s.%s.json" % (DOC, arm)), "w"), default=str)
    del vs, result, xml
    print(DOC, arm, "notes", nfile.get("notes"), "held", cov["bars_held_out_sum"].get("bars"), "partial", (cov.get("partial_bars") or {}).get("bars"),
          "refused", len(refusals), "%.0fs" % (time.time() - t0), flush=True)
