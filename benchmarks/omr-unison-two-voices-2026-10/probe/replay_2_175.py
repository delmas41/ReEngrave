"""ROADMAP 2.175 (copy of 2.165's replay_2_165.py, flag swapped) -- replay a WHOLE 20261018-night record (per-page slices from `pages_2_165.py`; no gather, no detector) through
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
FLAG = "OMR_UNISON_TWO_NOTES"
ENV = {"off": "0", "on": "1"}
JUDGED_Q = {"duration", "notehead_is_not_a_notehead", "unboxed_ink_is_a_rest", "notehead_is_an_eighth_rest", "arc_kind"}
CORRECT_REASON = "bar_corrects_one_note"
UQ = "unison_voices"
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
    uni = collections.Counter()
    uni_rows = {}
    for x in vs:
        if x["quantity"] == UQ:
            uni[(x["outcome"], x.get("reason"))] += 1
            uni_rows[x["subject"]] = dict(outcome=x["outcome"], reason=x.get("reason"), value=x.get("value"),
                                          detail=x.get("detail"))
    hs = collections.Counter((x["outcome"], x.get("reason")) for x in vs if x["quantity"] == "head_stem"
                             and x.get("reason") in ("unison_two_voices", "two_stems"))
    ev_unison = sum((x.get("detail") or {}).get("unison_split", 0) for x in vs if x["quantity"] == "event")
    voices = collections.Counter()
    for x in vs:
        if x["quantity"] == "voices" and x["outcome"] == "decided":
            voices[(x.get("reason"), (x.get("value") or {}).get("n_voices"))] += 1
        elif x["quantity"] == "voices":
            voices[(x["outcome"], x.get("reason"))] += 1
    print(DOC, arm, "unison_voices", dict(uni), "head_stem", dict(hs), "event_unison_split", ev_unison, flush=True)
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
    glyphs = {g: dict(brief(v), margin=v.get("margin"), ev=evd(v), refusal=(v.get("detail") or {}).get("one_note_refusal"))
              for g, v in glyph_live.items()}
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
    try:
        xml, report = E.to_musicxml(result)
    except E.Unbalanced as exc:
        # keep going: the frame of `to_musicxml` still holds its counters; print what balances the equality
        import sys as _sys
        tb = _sys.exc_info()[2]
        while tb.tb_next:
            tb = tb.tb_next
        fl = tb.tb_frame.f_locals
        c = fl.get("counters", {})
        print(DOC, arm, "UNBALANCED", str(exc)[:2500], {k: c.get(k) for k in (
            "notes", "rests", "measure_rests_read", "notes_unison_second_voice", "rests_duplicated_across_voices",
            "notes_doubled_to_condensed_slot")}, flush=True)
        if fl.get("xml"):
            open(os.path.join(OUTDIR, "%s.%s.musicxml" % (DOC, arm)), "w").write(fl["xml"])
        import json as _j
        _j.dump({"held": fl.get("held_bars"), "partial": fl.get("partial_bars")}, open(os.path.join(OUTDIR, "%s.%s.heldbars.json" % (DOC, arm)), "w"), default=str)
        xml, report = fl["xml"], fl["report"]
        report["unbalanced"] = str(exc)[:200]
    open(os.path.join(OUTDIR, "%s.%s.musicxml" % (DOC, arm)), "w").write(xml)
    print(DOC, arm, "export %.0fs" % (time.time() - t1), flush=True)
    # which changed notes reached the file (blue, with the rule's name)? guess_of is the exporter's own test
    R = E.Record({"record": {"observations": [], "abstentions": [], "verdicts": vs}})
    by_rule = collections.Counter()
    for g in glyph_live:
        gs = E.guess_of(R, g)
        if gs:
            by_rule[gs["rule"]] += 1
    cov = {k: report.get(k) for k in KEEP}

    def flat(d, pre=""):
        out = {}
        if isinstance(d, dict):
            for k, v in d.items():
                if isinstance(v, (int, float)) and any(w in str(k) for w in ("two_voice", "unison", "divisi", "kept_as_two", "left_fused")):
                    out[pre + str(k)] = v
                elif isinstance(v, dict):
                    out.update(flat(v, pre + str(k) + "."))
        return out
    cov["voice_counters"] = flat(report)
    cov["balance"] = report.get("balance")
    cov["not_written"] = report.get("notes_not_written")
    cov["bars_held_out_sum"] = {k: v for k, v in (report.get("bars_held_out_sum") or {}).items() if k != "held"}
    cov["partial_bars"] = {k: v for k, v in (report.get("partial_bars") or {}).items() if not isinstance(v, list) or k == "stay_held_by_reason"}
    held_keys = {h["bar_key"] for h in (report.get("bars_held_out_sum") or {}).get("held", [])}
    held_bars = [h for h in (report.get("bars_held_out_sum") or {}).get("held", [])]
    # a glyph "g" = glyph/<page>/<system>/<staff>/<cell>/<i>; bar key page/system/staff... held "bar_key" is "page/system/cell"? kept raw
    out = dict(doc=DOC, arm=arm, unison={"verdicts": {"%s/%s" % k: n for k, n in uni.items()}, "rows": uni_rows,
                                          "head_stem": {"%s/%s" % k: n for k, n in hs.items()}, "event_unison_split": ev_unison,
                                          "voices": {"%s/%s" % k: n for k, n in voices.items()}}, glyphs=glyphs, meters=meters, changed=changed, marked=marked, bars=bars, refusals=dict(refusals), refusals_full=dict(refusals_full),
               guessed_by_rule_record=dict(by_rule), coverage=cov, notes_in_xml=xml.count("<note"),
               held_bars=[(h["page"], h["system"], h["staff"], h["cell"]) for h in held_bars])
    json.dump(out, open(os.path.join(OUTDIR, "%s.%s.json" % (DOC, arm)), "w"), default=str)
    json.dump({"observations": boxes, "abstentions": [], "verdicts": [v for v in vs if v["quantity"] in JUDGED_Q]},
              open(os.path.join(OUTDIR, "%s.%s.record.json" % (DOC, arm)), "w"), default=str)
    del vs, result, xml
    print(DOC, arm, "notes", cov["written"]["notes"] if cov.get("written") else None, "held", cov["bars_held_out_sum"].get("bars"),
          "guessed", (cov.get("guessed") or {}).get("by_rule"), "changed", len(changed), "marked", len(marked),
          "%.0fs" % (time.time() - t0), flush=True)
