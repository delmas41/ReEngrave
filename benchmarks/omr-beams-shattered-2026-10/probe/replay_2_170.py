"""ROADMAP 2.170 -- replay a WHOLE 20261018-night record (per-page slices cut by the 2.165 lane's `pages_2_165.py`, one streamed
pass of the same record; no gather, no detector) through ADJUDICATE..INFER (review.rerun.run_stages == pipeline.decide) AND THEN
EXPORT (`export.to_musicxml`), flag OFF vs ON. Adapted from lane-2.165's replay_2_165.py (same harness, so both lanes' numbers
are comparable). It measures the EXPORTED FILE.
  arms: off (both 0), tip (OMR_BEAM_REFUSED_OFF_THE_TIP=1), arc (OMR_BEAM_NOT_ON_SYSTEM_ARC=1), both   (else = main 7f668d66)
Per arm: OUTDIR/<doc>.<arm>.json {glyphs (live duration brief + origin), coverage digest, held bars, notes in xml} and
OUTDIR/<doc>.<arm>.record.json (mini record for `judged score`); OUTDIR/<doc>.control.json (OFF arm vs the stored verdicts).
usage: replay_2_170.py DOC SLICEDIR OUTDIR ARM[,ARM...] [--lock]"""
import collections
import glob
import json
import os
import sys
import time

sys.path.insert(0, ".")
sys.path.insert(0, "benchmarks/gather-zoom-layers-2026-10/probe")
import rec as RC  # noqa: E402
from tools.omr.staged import export as E  # noqa: E402
from tools.omr.staged.review import rerun as RR  # noqa: E402

DOC, SD, OUTDIR, ARMS = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4].split(",")
LOCK = "--lock" in sys.argv
D = os.path.join(SD, DOC)
TIP, ARCF = "OMR_BEAM_REFUSED_OFF_THE_TIP", "OMR_BEAM_NOT_ON_SYSTEM_ARC"
ENV = {"off": ("0", "0"), "on": ("1", "0"), "tip": ("1", "0"), "arc": ("0", "1"), "both": ("1", "1")}
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
                beam_levels=val.get("beam_levels"), rest=bool(val.get("is_rest")), decider=v.get("decider"), reason=v.get("reason"),
                cands=sorted({(c.get("value") or {}).get("beats") for c in (v.get("candidates") or [])
                              if isinstance(c.get("value"), dict)} - {None}) or None)


def main():
    t0 = time.time()
    rec = {"observations": rows("observations"), "abstentions": rows("abstentions"), "verdicts": []}
    stored = rows("verdicts")
    boxes, seen = [], set()
    for o in rec["observations"]:
        s = o.get("subject") or ""
        if s.startswith("glyph/") and s not in seen and isinstance((o.get("detail") or {}).get("bbox_page_px"), list):
            seen.add(s)
            boxes.append({k: o.get(k) for k in ("id", "subject", "quantity", "detail")})
    print(DOC, "rows", len(rec["observations"]), len(rec["abstentions"]), "%.0fs" % (time.time() - t0), flush=True)
    st_first = {}
    for v in stored:
        if v.get("decider") == "adjudicate_duration" and v["subject"] not in st_first:
            st_first[v["subject"]] = (v["outcome"], v.get("reason"))
    st_live = {g: brief(v) for g, v in live(stored, "duration", "glyph/").items()}
    del stored
    KEEP = ("bars_held_out_sum", "partial_bars", "guessed", "written", "notes_not_written", "notes_not_written_total")
    for arm in ARMS:
        os.environ[TIP], os.environ[ARCF] = ENV[arm]
        log, _ = RR.rebuild_gather(rec)
        RR.run_stages(log)
        result = {"record": log.to_json(), "summary": log.summary()}
        del log
        vs = result["record"]["verdicts"]
        glyph_live = live(vs, "duration", "glyph/")
        by_id = {x["id"]: x for x in vs if x["quantity"] == "duration"}

        def origin(v):
            seen_ids = set()
            while v.get("supersedes") and v["supersedes"] in by_id and v["id"] not in seen_ids:
                seen_ids.add(v["id"])
                v = by_id[v["supersedes"]]
            return v
        glyphs = {}
        for g, v in glyph_live.items():
            o = origin(v)
            d = o.get("detail") or {}
            glyphs[g] = dict(brief(v), origin_reason=o.get("reason"), origin_outcome=o.get("outcome"),
                             off_tip=bool(d.get("beam_refused_off_the_tip")),
                             on_arc=bool((d.get("beams_not_by_ink_why") or {}).get("on_system_arc")))
        if arm == "off":
            first = {}
            for v in vs:
                if v["quantity"] == "duration" and v.get("decider") == "adjudicate_duration" and v["subject"] not in first:
                    first[v["subject"]] = (v["outcome"], v.get("reason"))
            diff_first = sum(1 for g in st_first if g in first and st_first[g] != first[g])
            diff_live = sum(1 for g in st_live if g in glyphs and (st_live[g]["outcome"], st_live[g]["written"])
                            != (glyphs[g]["outcome"], glyphs[g]["written"]))
            json.dump(dict(stored_first=len(st_first), first_differ=diff_first, stored_live=len(st_live), live_differ=diff_live),
                      open(os.path.join(OUTDIR, "%s.control.json" % DOC), "w"))
            print(DOC, "CONTROL off vs stored: first adjudicate_duration differ", diff_first, "of", len(st_first),
                  "; live (outcome, written) differ", diff_live, "of", len(st_live), flush=True)
        t1 = time.time()
        xml, report = E.to_musicxml(result)
        print(DOC, arm, "export %.0fs" % (time.time() - t1), flush=True)
        cov = {k: report.get(k) for k in KEEP}
        cov["bars_held_out_sum"] = {k: v for k, v in (report.get("bars_held_out_sum") or {}).items() if k != "held"}
        cov["partial_bars"] = {k: v for k, v in (report.get("partial_bars") or {}).items()
                               if not isinstance(v, list) or k == "stay_held_by_reason"}
        held = [(h["page"], h["system"], h["staff"], h["cell"]) for h in (report.get("bars_held_out_sum") or {}).get("held", [])]
        out = dict(doc=DOC, arm=arm, glyphs=glyphs, coverage=cov, notes_in_xml=xml.count("<note"), held_bars=held)
        json.dump(out, open(os.path.join(OUTDIR, "%s.%s.json" % (DOC, arm)), "w"), default=str)
        json.dump({"observations": boxes, "abstentions": [], "verdicts": [v for v in vs if v["quantity"] in JUDGED_Q]},
                  open(os.path.join(OUTDIR, "%s.%s.record.json" % (DOC, arm)), "w"), default=str)
        with open(os.path.join(OUTDIR, "%s.%s.musicxml" % (DOC, arm)), "w") as fh:
            fh.write(xml)
        del vs, result, xml
        print(DOC, arm, "notes", (cov.get("written") or {}).get("notes"), "held", cov["bars_held_out_sum"].get("bars"),
              "off_tip", sum(1 for x in glyphs.values() if x["off_tip"]), "on_arc", sum(1 for x in glyphs.values() if x["on_arc"]), "%.0fs" % (time.time() - t0), flush=True)


if LOCK:
    with RC.lock():
        main()
else:
    main()
print("ALLDONE", DOC, flush=True)
