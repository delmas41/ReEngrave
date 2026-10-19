"""ROADMAP 2.165 -- replay a WHOLE 20261018-night record (per-page slices from `pages_2_165.py`; no gather, no detector) through
ADJUDICATE..INFER..second EVALUATE (review.rerun.run_stages == pipeline.decide) AND THEN EXPORT (`export.to_musicxml`), flag OFF vs ON.
It measures the EXPORTED FILE (2.168 measured the record and missed that most blue notes never reached the file):
  notes reaching file (`written.notes`), `bars_held_out_sum`, partial bars, `guessed.by_rule`, the writing of every note
  the rule changed (is it in the file, blue, in a held-out bar?).
  off -- OMR_BAR_CORRECTS_ONE_NOTE=0          on -- OMR_BAR_CORRECTS_ONE_NOTE=1     (everything else = main)
Per arm writes OUTDIR/<doc>.<arm>.json {glyphs, meters, changed[], marked[], coverage digest} and
OUTDIR/<doc>.<arm>.record.json (mini record for `judged score`).
usage: replay_2_165.py DOC SLICEDIR OUTDIR ARM[,ARM...]"""
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
FLAG = "OMR_BAR_CORRECTS_ONE_NOTE"
ENV = {"off": "0", "on": "strict", "relaxed": "relaxed", "loose": "loose"}
JUDGED_Q = {"duration", "notehead_is_not_a_notehead", "unboxed_ink_is_a_rest", "notehead_is_an_eighth_rest", "arc_kind"}
CORRECT_REASON = "bar_corrects_one_note"
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
    EV0 = ("beam_evidence", "flag_levels", "flags_attached", "beams_by_stem", "levels_certain", "levels_possible",
           "beams_not_by_ink", "beams_not_by_ink_why", "cv_beams", "yolo_beams", "head_is_open", "stem_tip_hook",
           "hooks_counted", "second_hollow", "tip_unread", "hollow_readings")
    by_id = {x["id"]: x for x in vs if x["quantity"] == "duration"}

    def origin(v):
        """the earliest verdict in v's supersession chain (the reader's own reading)"""
        seen = set()
        while v.get("supersedes") and v["supersedes"] in by_id and v["id"] not in seen:
            seen.add(v["id"])
            v = by_id[v["supersedes"]]
        return v

    def evd(v):
        o = origin(v)
        d = o.get("detail") or {}
        return dict(origin_decider=o.get("decider"), origin_reason=o.get("reason"), origin_outcome=o.get("outcome"),
                    **{k: d[k] for k in EV0 if k in d})
    glyphs = {g: dict(brief(v), margin=v.get("margin"), ev=evd(v)) for g, v in glyph_live.items()}
    meters = {s: meter_brief(v) for s, v in live(vs, "meter", "system/").items()}
    changed = []
    for g, v in glyph_live.items():
        if v.get("reason") == CORRECT_REASON:
            changed.append(dict(glyph=g, now=brief(v), cands=[c["value"] for c in v["candidates"]], detail=v.get("detail")))
    marked = [g for g, v in glyph_live.items() if v.get("reason") == "bar_disagrees_with_decided"]
    # the evidence landscape of every disputed bar: each standing duration verdict in the cell with its evidence keys
    EV = ("beam_evidence", "flag_levels", "flags_attached", "beams_by_stem", "levels_certain", "levels_possible",
          "beams_not_by_ink", "beams_not_by_ink_why", "cv_beams", "yolo_beams", "head_is_open", "margin", "margin_axis",
          "stem_tip_hook", "hooks_counted", "bar_expected_beats", "bar_total_beats", "kept_beats", "bar_alternative_beats")
    by_cell = collections.defaultdict(list)
    for g in glyph_live:
        by_cell["/".join(g.split("/")[:5])].append(g)
    refusals = collections.Counter(((v.get("detail") or {}).get("one_note_refusal") or "").split(":")[0]
                                   for g, v in glyph_live.items() if v.get("reason") == "bar_disagrees_with_decided")
    refusals_full = collections.Counter((v.get("detail") or {}).get("one_note_refusal") for g, v in glyph_live.items()
                                        if v.get("reason") == "bar_disagrees_with_decided")
    bars = {}
    for g in set(marked) | {c["glyph"] for c in changed}:
        ck = "/".join(g.split("/")[:5])
        members = []
        for m in by_cell[ck]:
            v = glyph_live[m]
            d = v.get("detail") or {}
            members.append(dict(glyph=m, **brief(v), margin=v.get("margin"), ev=evd(v), live_detail={k: d[k] for k in EV if k in d}))
        bars[ck] = members
    t1 = time.time()
    xml, report = E.to_musicxml(result)
    print(DOC, arm, "export %.0fs" % (time.time() - t1), flush=True)
    # which changed notes reached the file (blue, with the rule's name)? guess_of is the exporter's own test
    R = E.Record({"record": {"observations": [], "abstentions": [], "verdicts": vs}})
    by_rule = collections.Counter()
    for g in glyph_live:
        gs = E.guess_of(R, g)
        if gs:
            by_rule[gs["rule"]] += 1
    cov = {k: report.get(k) for k in KEEP}
    cov["bars_held_out_sum"] = {k: v for k, v in (report.get("bars_held_out_sum") or {}).items() if k != "held"}
    cov["partial_bars"] = {k: v for k, v in (report.get("partial_bars") or {}).items() if not isinstance(v, list) or k == "stay_held_by_reason"}
    held_keys = {h["bar_key"] for h in (report.get("bars_held_out_sum") or {}).get("held", [])}
    held_bars = [h for h in (report.get("bars_held_out_sum") or {}).get("held", [])]
    # a glyph "g" = glyph/<page>/<system>/<staff>/<cell>/<i>; bar key page/system/staff... held "bar_key" is "page/system/cell"? kept raw
    out = dict(doc=DOC, arm=arm, glyphs=glyphs, meters=meters, changed=changed, marked=marked, bars=bars, refusals=dict(refusals), refusals_full=dict(refusals_full),
               guessed_by_rule_record=dict(by_rule), coverage=cov, notes_in_xml=xml.count("<note"),
               held_bars=[(h["page"], h["system"], h["staff"], h["cell"]) for h in held_bars])
    json.dump(out, open(os.path.join(OUTDIR, "%s.%s.json" % (DOC, arm)), "w"), default=str)
    json.dump({"observations": boxes, "abstentions": [], "verdicts": [v for v in vs if v["quantity"] in JUDGED_Q]},
              open(os.path.join(OUTDIR, "%s.%s.record.json" % (DOC, arm)), "w"), default=str)
    del vs, result, xml
    print(DOC, arm, "notes", cov["written"]["notes"] if cov.get("written") else None, "held", cov["bars_held_out_sum"].get("bars"),
          "guessed", (cov.get("guessed") or {}).get("by_rule"), "changed", len(changed), "marked", len(marked),
          "%.0fs" % (time.time() - t0), flush=True)
