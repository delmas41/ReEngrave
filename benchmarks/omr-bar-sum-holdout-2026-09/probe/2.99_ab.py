"""2.99 base vs arm on ONE tree, from ONE saved gather record.

    python3 .../2.99_ab.py REC.json OUTDIR

REC.json is a small-re-gather record (`acceptance_quick`, `--through adjudicate`
is enough: only its GATHER rows are used) from a tree with `Q.UNBOXED_REST_SHAPE`.
Both arms re-run ADJUDICATE..INFER from the SAME gather rows. The ONLY
difference: the OFF arm makes `adjudicate_unboxed_ink_is_a_rest` abstain on
everything (the tree as it was before 2.99), the ON arm lets it decide.

Prints REACH first (clusters filed, decisions by outcome/reason, how many become
rests), then, per decided rest, what happened to ITS BAR across the arms using the
exporter's own `_bar_holds_out` (wrapped, not restated):

  released      held in OFF, adds up in ON      (the point)
  still_held    held in both                    (a rest found, the bar still wrong)
  newly_held    adds up in OFF, held in ON      (A FALSE POSITIVE: must be 0)
  unchanged_ok  adds up in both                 (rest added, bar still fine -- explain)
  was_empty     no events in OFF                (bar was unread; now holds one rest)
  no_verdict    no meter in force: neither arm can judge it
"""
import collections
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, ".")
from tools.omr.staged import adjudicate, export as EXPORT  # noqa: E402
from tools.omr.staged.record import Q  # noqa: E402
from tools.omr.staged.record_io import load_record  # noqa: E402
from tools.omr.staged.review import rerun  # noqa: E402

rec_path, out = sys.argv[1], Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
doc = load_record(rec_path)
rec = doc["record"] if "record" in doc else doc
adjudicate._ensure_decisions()
spec = [s for s in adjudicate.REGISTRY.values()
        if s.quantity == Q.UNBOXED_INK_IS_A_REST][0]
real_fn = spec.fn


def cell_of(sub):
    p = (sub or "").split("/")
    if len(p) >= 6 and p[0] == "glyph":
        return "/".join(p[1:5])
    return None


def run(arm):
    log, _ = rerun.rebuild_gather(rec)
    if arm == "off":
        object.__setattr__(spec, "fn", lambda ev: adjudicate.Ruling.abstain(
            "no_shape_reading"))
    bars = {}
    real_hold = EXPORT._bar_holds_out

    def wrapped(events, streams, divisions, meter):
        r = real_hold(events, streams, divisions, meter)
        c = None
        for ev in events:
            for h in (ev.get("noteheads") or [(ev.get("rest") or {})]):
                c = cell_of((h or {}).get("glyph"))
                if c:
                    break
            if c:
                break
        if c:
            bars[c] = {"held": r is not None,
                       "no_meter": EXPORT._bar_quarters(meter) is None,
                       "quarters": (r or {}).get("quarters"),
                       "want": (r or {}).get("want_quarters"),
                       "n_events": len(events),
                       "events": [[ev.get("kind"), ev.get("duration_beats"),
                                   [h.get("class") for h in (ev.get("noteheads") or [])]
                                   or (ev.get("rest") or {}).get("class"),
                                   round(float(ev.get("x_position") or 0), 1)]
                                  for ev in events]}
        return r

    EXPORT._bar_holds_out = wrapped
    try:
        rerun.run_stages(log)
        result = {"record": log.to_json(), "summary": log.summary()}
        xml, report = EXPORT.to_musicxml(result)
    finally:
        EXPORT._bar_holds_out = real_hold
        object.__setattr__(spec, "fn", real_fn)
    (out / f"{arm}.musicxml").write_text(xml)
    vs = result["record"]["verdicts"]
    last = {}
    for v in vs:
        if v["quantity"] == Q.UNBOXED_INK_IS_A_REST:
            last[v["subject"]] = v
    rows = {o["subject"]: o for o in result["record"]["observations"]
            if o["quantity"] == Q.UNBOXED_REST_SHAPE}
    return {"verdicts": last, "rows": rows, "bars": bars,
            "held": (report.get("bars_held_out_sum") or {}).get("bars"),
            "of": (report.get("bars_held_out_sum") or {}).get("of_bars_with_events"),
            "balanced": (report.get("balance") or {}).get("balanced"),
            "rests": report.get("rests"),
            "notes_not_written_total": report.get("notes_not_written_total")}


off, on = run("off"), run("on")
rows = on["rows"]
cov = lambda r: (r["detail"].get("coverage") or 0)
print("REACH clusters filed:", len(rows),
      " unboxed (cover<0.1):", sum(1 for r in rows.values() if cov(r) < 0.1))
dec = collections.Counter()
for s, v in on["verdicts"].items():
    dec[(v["outcome"], str(v.get("value")), v.get("reason"))] += 1
for k, n in sorted(dec.items(), key=lambda kv: -kv[1]):
    print("  ", n, k)
decided = [s for s, v in on["verdicts"].items()
           if v["outcome"] == "decided" and v["value"] in ("eighth", "quarter")]
print("DECIDED rests:", len(decided),
      collections.Counter(on["verdicts"][s]["value"] for s in decided))

cls = collections.defaultdict(list)
for s in decided:
    c = cell_of(s)
    b0, b1 = off["bars"].get(c), on["bars"].get(c)
    if b0 is None and b1 is not None:
        k = "was_empty"
    elif b0 is None or b1 is None:
        k = "bar_missing"
    elif b0["no_meter"] or b1["no_meter"]:
        k = "no_verdict"
    elif b0["held"] and not b1["held"]:
        k = "released"
    elif b0["held"] and b1["held"]:
        k = "still_held"
    elif not b0["held"] and b1["held"]:
        k = "newly_held"
    else:
        k = "unchanged_ok"
    cls[k].append({"subject": s, "cell": c, "off": b0, "on": b1,
                   "value": on["verdicts"][s]["value"],
                   "shape": {k2: rows[s]["detail"].get(k2) for k2 in (
                       "width_spaces", "height_spaces", "staff_step",
                       "max_column_share", "mass_y", "bbox_page_px")}})
print("BARS of the decided rests:",
      {k: len(v) for k, v in cls.items()})
print("held OFF/ON:", off["held"], on["held"], "of", off["of"], on["of"],
      "balanced", off["balanced"], on["balanced"])


def bars(xml):
    d = {}
    for pm in re.finditer(r'<part id="([^"]+)">(.*?)</part>', xml, re.S):
        for mm in re.finditer(r'<measure number="([^"]+)"[^>]*>(.*?)</measure>',
                              pm.group(2), re.S):
            d[(pm.group(1), mm.group(1))] = mm.group(2)
    return d


b0 = bars((out / "off.musicxml").read_text())
b1 = bars((out / "on.musicxml").read_text())
changed = sorted(k for k in set(b0) | set(b1) if b0.get(k) != b1.get(k))
print("MusicXML bars changed:", len(changed))
(out / "ab2_99.json").write_text(json.dumps({
    "decisions": {str(k): n for k, n in dec.items()},
    "classes": cls, "changed_bars": [list(k) for k in changed],
    "held": [off["held"], on["held"]], "of": [off["of"], on["of"]],
    "balanced": [off["balanced"], on["balanced"]],
    "off_bars": off["bars"], "on_bars": on["bars"],
    "clusters": {s: {"detail": r["detail"], "value": on["verdicts"].get(s, {}).get("value"),
                     "reason": on["verdicts"].get(s, {}).get("reason"),
                     "outcome": on["verdicts"].get(s, {}).get("outcome")}
                 for s, r in rows.items()},
}, indent=1, default=str))
