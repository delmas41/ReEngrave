"""2.119 step 0: one record -> one small JSON of per-glyph facts for ONE page + the EXPORT outcome of each glyph.
usage (cwd = a checkout of the tree to export with):  python3 extract.py RECORD PAGE OUT.json
Export = main (ffb66049) default flags (OMR_PARTIAL_BARS on, re-centring on). Hooks only OBSERVE: _bar_holds_out,
_partial_bar_plan, _measure_events_xml are wrapped and call through unchanged."""
import sys, json, collections, time
sys.path.insert(0, ".")
from tools.omr.staged import record_io, readout as RO, export as SX
rec_path, page, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
t0 = time.time()
result = record_io.load_record(rec_path)
print("loaded", round(time.time() - t0), flush=True)
run = RO.run_from_result(result, path=rec_path)
print("indexed", round(time.time() - t0), flush=True)

def subs_of(ev):
    s = []
    for h in ev.get("noteheads") or ():
        if h.get("glyph"): s.append(h["glyph"])
    r = (ev.get("rest") or {}).get("glyph")
    if r: s.append(r)
    return s

rendered = {}     # sub -> guess dict or None at render time
bar_fate = {}     # sub -> reason string
bar_info = {}
FATES = {}
STATE = {"held_events": None}
_ob, _op, _om, _mc = SX._bar_holds_out, SX._partial_bar_plan, SX._measure_events_xml, SX.marks_census
def hb(events, *a, **k):
    r = _ob(events, *a, **k)
    STATE["held_events"] = events if r is not None else None
    STATE["held_info"] = r
    return r
def pp(events, *a, **k):
    plan = _op(events, *a, **k)
    ev0 = STATE["held_events"]; STATE["held_events"] = None
    hi = STATE.get("held_info") or {}
    unplaced = a[3] if len(a) > 3 else k.get("unplaced", ())
    info = {"want_quarters": hi.get("want_quarters"), "voice_quarters": hi.get("quarters"), "plan_ok": bool(plan.get("ok")),
            "plan_why": plan.get("why"), "n_events": len(events),
            "unplaced": [{"sub": u.get("sub"), "reason": u.get("reason"), "x": u.get("x")} for u in (unplaced or ())],
            "bar_subs": [s for e in events for s in subs_of(e)]}
    if plan.get("ok"):
        for e in plan["unwritten"]:
            for s in subs_of(e): bar_fate[s] = "unread_gap_in_partial_bar"; bar_info[s] = info
        for e in plan["written"]:
            for s in subs_of(e): bar_info.setdefault(s, info)
    else:
        for e in events:
            for s in subs_of(e): bar_fate[s] = "held_bar:" + str(plan.get("why")); bar_info[s] = info
    return plan
HC = collections.Counter()
def me(events, *a, **k):
    for ev in events:
        if ev.get("kind") != "rest":
            for h in ev.get("noteheads") or ():
                HC["heads"] += 1
                if not h.get("glyph"): HC["no_glyph"] += 1
                elif h["glyph"] in rendered: HC["dup_sub"] += 1
        else: HC["rest_events"] += 1
    for ev in events:
        if ev.get("kind") == "rest":
            g = (ev.get("rest") or {}).get("guess")
            for s in subs_of(ev): rendered[s] = {"guess": g, "rest": True}
        else:
            for h in ev.get("noteheads") or ():
                if h.get("glyph"): rendered[h["glyph"]] = {"guess": h.get("guess"), "rest": False}
    return _om(events, *a, **k)
def mc(rec, fates):
    FATES.update(fates); return _mc(rec, fates)
SX._bar_holds_out, SX._partial_bar_plan, SX._measure_events_xml, SX.marks_census = hb, pp, me, mc
xml, rep = SX.to_musicxml(result)
print("exported", round(time.time() - t0), len(xml), flush=True)
open(out.replace(".json", ".musicxml"), "w").write(xml)
json.dump({"written": rep.get("written"), "guessed": rep.get("guessed"), "bars_held_out_sum": {k: v for k, v in (rep.get("bars_held_out_sum") or {}).items() if k != "bars_list"},
           "partial_bars": {k: v for k, v in (rep.get("partial_bars") or {}).items() if k != "bars"}, "balance": rep.get("balance")},
          open(out.replace(".json", ".report.json"), "w"), default=str)
print("head counter", dict(HC), flush=True)
n_note_rendered = sum(1 for v in rendered.values() if not v["rest"])
print("rendered note subs", n_note_rendered, "report written.notes", (rep.get("written") or {}).get("notes"), flush=True)

def comp(v, n=240):
    s = json.dumps(v, default=str, separators=(",", ":"))
    return s if len(s) <= n else s[:n] + "~"
glyphs = {}
for k, g in run.glyphs.items():
    if g.page != page: continue
    st, why = RO.adjudicate_status(run, g)
    rows = []
    for stage, kind, r in run.rows_at(k):
        rows.append({"stage": stage, "kind": kind, "q": r.get("quantity"), "outcome": r.get("outcome"),
                     "reason": r.get("reason"), "value": comp(r.get("value"), 500), "score": r.get("score"),
                     "decider": r.get("decider") or r.get("source"), "detail": comp(r.get("detail"), 900) if r.get("detail") else None})
    fate = FATES.get(k)
    glyphs[k] = {"cls": g.cls, "family": g.family, "score": g.score, "system": g.system, "staff": g.staff, "cell": g.cell,
                 "box_canon": g.box_canon, "box_page": g.box_page, "adj": st, "adj_why": why,
                 "place": fate, "rendered": rendered.get(k), "bar_fate": bar_fate.get(k), "bar_info": bar_info.get(k), "rows": rows}
json.dump({"record": rec_path, "page": page, "dpi": run.dpi, "pdf": run.pdf, "provenance_tree": run.provenance.get("commit"),
           "n_fates": len(FATES), "n_rendered": len(rendered), "glyphs": glyphs}, open(out, "w"), default=str)
print("wrote", out, len(glyphs), flush=True)
