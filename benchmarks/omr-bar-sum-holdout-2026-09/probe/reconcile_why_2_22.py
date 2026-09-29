"""ROADMAP 2.22 -- why did `reconcile_duration` (EVALUATE) not repair a held
bar that one note read one beam level off would release?

PATH: STAGED. Loads ONE record once, re-decides it on this tree
(`review.rerun`), exports it with `_bar_holds_out` wrapped (the exporter's own
rule), then asks the RECORD, for every held bar, what `reconcile_duration`
saw there -- through the rule's own helpers (`consequences._standing`,
`_event_totals`, `_admitted`, `_is_rest`, `_left_the_bar`), never a copy of
its arithmetic except the ten-line landing loop, which is the thing being
diagnosed and is restated below with its bound (tuplets and rests skipped,
exact landing).

Buckets, first that applies:
  meter_not_decided    the system's `Q.METER` is not DECIDED: the rule's
                       cause never arrives, whatever the bar holds
  no_event_grouping    `Q.EVENT` not DECIDED for the cell: the rule refuses
  record_total_fits    the rule's own total already equals the meter, so it
                       does nothing, while EXPORT's bar does not add up
  unique / none / many landings over the rule's own notes
and, beside each, the same count with the notes a DECIDED verdict already
took OUT of the bar set aside (`_left_the_bar`, 2.19's helper) -- the
connection this probe exists to price.

    python3 .../reconcile_why_2_22.py <record.json> --label L --out <json>
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
T0 = time.time()


def say(m):
    print(f"[{time.time() - T0:7.1f}s] {m}", flush=True)


def _cell_of(sub):
    p = (sub or "").split("/")
    if len(p) >= 6 and p[0] == "glyph":
        return tuple(int(x) for x in p[1:5])
    return None


def landings(C, notes, current, total, expected):
    out = []
    for note in notes:
        if C._is_rest(note):
            continue
        now = current[note.id]
        if float(now.get("beats") or 0.0) != float(now.get("written") or -1.0):
            continue
        for option in C._admitted(note):
            if option.get("beam_levels") == now.get("beam_levels"):
                continue
            moved = total - float(now.get("beats") or 0.0) \
                + float(option.get("beats") or 0.0)
            if abs(moved - expected) < 1e-6:
                out.append(note.subject.to_key())
    return out


def write_geometry(rec, held, out):
    """Geometry for the crops, so the crop script never loads the record."""
    from tools.omr.staged.record import Q
    held_staves = {f"staff/{p}/{s}/{st}" for (p, s, st, _c) in held}
    geom = {"staff_lines": {}, "staff_spacing": {}, "cell_box": {},
            "glyph_page_px": {}}
    for o in rec["observations"]:
        q, sub = o["quantity"], o["subject"]
        if q == Q.STAFF_LINES and o["frame"] == "page" and sub in held_staves:
            geom["staff_lines"][sub] = list(o["value"])
        elif q == Q.STAFF_SPACING and o["frame"] == "page" and sub in held_staves:
            geom["staff_spacing"][sub] = float(o["value"])
        elif q == Q.CELL_BOX:
            parts = sub.split("/")
            if len(parts) == 5 and tuple(int(x) for x in parts[1:]) in held:
                geom["cell_box"][sub] = list(o["value"])
        elif q == Q.GLYPH_BOX and _cell_of(sub) in held:
            bp = (o.get("detail") or {}).get("bbox_page_px")
            if bp:
                geom["glyph_page_px"][sub] = [o["value"][0], bp]
    Path(out).with_suffix(".geometry.json").write_text(json.dumps(geom))
    say(f"geometry written: {({k: len(v) for k, v in geom.items()})}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--label", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--geometry-only", metavar="HELD_DUMP",
                    help="no re-decision: write crop geometry for the cells "
                         "of this held dump and stop")
    a = ap.parse_args()

    from tools.omr.staged import consequences as C
    from tools.omr.staged import export as EX
    from tools.omr.staged.record import Kind, Outcome, Q, Subject
    from tools.omr.staged.record_io import load_record
    from tools.omr.staged.review import rerun as RR

    doc = load_record(a.record)
    say("loaded")
    if a.geometry_only:
        cells = {tuple(b["cell"]) for b in
                 json.load(open(a.geometry_only))["bars"] if b.get("cell")}
        write_geometry(doc["record"] if "record" in doc else doc, cells, a.out)
        return 0
    log, _ = RR.rebuild_gather(doc["record"] if "record" in doc else doc)
    prov = doc.get("provenance")
    del doc
    RR.run_stages(log)
    say("decided")
    result = RR._to_result(log, {"provenance": prov}, None)

    held = {}
    orig = EX._bar_holds_out

    def wrapped(events, streams, divisions, meter):
        out = orig(events, streams, divisions, meter)
        if out is not None:
            cells = {_cell_of(g) for ev in events for g in
                     ([h.get("glyph") for h in ev.get("noteheads") or []]
                      or [(ev.get("rest") or {}).get("glyph")]) if _cell_of(g)}
            if len(cells) == 1:
                held[next(iter(cells))] = {
                    "n_streams": len(streams) if streams else 1,
                    "want": out["want_quarters"]}
        return out

    EX._bar_holds_out = wrapped
    try:
        EX.to_musicxml(result)
    finally:
        EX._bar_holds_out = orig
    say(f"exported, {len(held)} held")

    write_geometry(result["record"], held, a.out)

    fired = {v.subject.to_key() for v in log.all_verdicts()
             if v.quantity == Q.DURATION and v.decider == "reconcile_duration"}
    buckets = collections.Counter()
    kept_buckets = collections.Counter()
    rows = []
    for (p, s, st, c), info in sorted(held.items()):
        cell = Subject(Kind.CELL, page=p, system=s, staff=st, cell=c)
        meter = log.verdict(Q.METER, Subject(Kind.SYSTEM, page=p, system=s))
        row = {"cell": [p, s, st, c], "n_streams": info["n_streams"]}
        if meter is None or meter.outcome is not Outcome.DECIDED \
                or not (meter.value or {}).get("numerator"):
            row["bucket"] = "meter_not_decided"
            row["meter"] = None if meter is None else [meter.outcome.value,
                                                       meter.reason]
            buckets[row["bucket"]] += 1
            rows.append(row)
            continue
        # the meter in force AT THIS CELL is the file's; the rule reads the
        # system verdict's top-level value -- recorded, not corrected here
        num, den = meter.value["numerator"], meter.value["denominator"]
        expected = float(num) * 4.0 / float(den)
        notes = [v for v in C._standing(log, cell, Q.DURATION)
                 if v.outcome in (Outcome.DECIDED, Outcome.NARROWED)]

        def cur(v):
            if v.outcome is Outcome.DECIDED:
                return v.value
            return v.candidates[0].value if v.candidates else None
        current = {v.id: cur(v) for v in notes}
        if not notes or any(x is None for x in current.values()):
            row["bucket"] = "no_notes_or_unvalued"
            buckets[row["bucket"]] += 1
            rows.append(row)
            continue
        total = C._event_totals(log, cell, notes, current)
        if total is None:
            row["bucket"] = "no_event_grouping"
            buckets[row["bucket"]] += 1
            rows.append(row)
            continue
        kept = [v for v in notes if C._left_the_bar(log, v.subject) is None]
        kept_total = C._event_totals(log, cell, kept, current) if kept else 0.0
        row.update({"expected": expected, "export_want": info["want"],
                    "total": total, "kept_total": kept_total,
                    "n_notes": len(notes), "n_set_aside": len(notes) - len(kept)})
        if abs(total - expected) < 1e-6:
            b = "record_total_fits"
        else:
            L = landings(C, notes, current, total, expected)
            b = ("unique_landing" if len(L) == 1 else
                 "no_landing" if not L else "many_landings")
            row["landings"] = L
        if kept and abs(kept_total - expected) >= 1e-6:
            LK = landings(C, kept, current, kept_total, expected)
            kb = ("unique_landing" if len(LK) == 1 else
                  "no_landing" if not LK else "many_landings")
            row["kept_landings"] = LK
        else:
            kb = "kept_total_fits" if kept else "nothing_kept"
        if info["n_streams"] > 1:
            b, kb = b + "+two_voices", kb + "+two_voices"
        row["bucket"], row["kept_bucket"] = b, kb
        row["reconciled_here"] = any(k.startswith(f"glyph/{p}/{s}/{st}/{c}/")
                                     for k in fired)
        buckets[b] += 1
        kept_buckets[kb] += 1
        rows.append(row)
    print(a.label, "held", len(held))
    print(" rule's own view:", dict(buckets.most_common()))
    print(" with left-the-bar set aside:", dict(kept_buckets.most_common()))
    Path(a.out).write_text(json.dumps({
        "label": a.label, "held": len(held),
        "buckets": buckets, "kept_buckets": kept_buckets,
        "reconcile_fired_anywhere": len(fired), "rows": rows},
        indent=1, default=str))
    say("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
