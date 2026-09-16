"""ONE GATHER, ADJUDICATED TWICE, EXPORTED TWICE — the phantom-note A/B.

⚠️ WHY NOT A PLAIN RE-EXPORT. `notehead_is_a_whole_rest` is an ADJUDICATE
decision, and re-exporting a SAVED record replays saved verdicts, so it would be
BLIND to the rule and both arms would come back identical whatever the rule did.
This rebuilds a `Log` from the record's GATHER rows (`readjudicate.rebuild`),
re-runs ADJUDICATE and EVALUATE, and only then exports — so the two arms differ
in the decision under test and in nothing else. The OFF arm is the full `ORDER`
with that one quantity REMOVED, which is exactly what `main` does.

⚠️⚠️ WHAT IT IS BLIND TO, stated because a green number here would otherwise be
reported as evidence for something it cannot test: it CANNOT see a GATHER
change. New rows, new fields, a changed frame never enter the rebuild. Only two
full re-gathers answer that. Nothing in this repair is in GATHER.

⚠️ REACH AND A CONTROL BEFORE ANY DELTA. The control is that the OFF arm
reproduces the SHARED RECORD'S OWN duration verdicts — if the rebuild does not
reproduce the pipeline, the delta is measuring the rebuild. The reach is how
many noteheads the rule even fires on; a rule that fires on nothing produces two
identical files and looks clean.

    python3 arm.py <record.json> --out-dir D
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "benchmarks" / "omr-staged-duration-beams-2026-09"))

from tools.omr.staged import adjudicate, evaluate                  # noqa: E402
from tools.omr.staged import adjudicators, consequences            # noqa: E402,F401
from tools.omr.staged import export as EXPORT                      # noqa: E402
from tools.omr.staged.record import Outcome, Q                     # noqa: E402
from readjudicate import rebuild                                   # noqa: E402


def _bars(xml_text):
    """[(part, measure, [events])] — one row per bar, straight out of the file."""
    out = []
    for part in ET.fromstring(xml_text).findall("part"):
        pid = part.get("id")
        div = beats = btype = None
        for m in part.findall("measure"):
            at = m.find("attributes")
            if at is not None:
                if at.find("divisions") is not None:
                    div = int(at.find("divisions").text)
                t = at.find("time")
                if t is not None:
                    beats = int(t.find("beats").text)
                    btype = int(t.find("beat-type").text)
            ev = []
            for n in m.findall("note"):
                p = n.find("pitch")
                ev.append((None if p is None else
                           p.find("step").text + p.find("octave").text,
                           n.find("rest") is not None,
                           int(n.find("duration").text)
                           if n.find("duration") is not None else 0))
            out.append((pid, int(m.get("number")), ev,
                        None if not (div and beats and btype)
                        else div * 4 * beats / btype))
    return out


def _lone_quarters(rows):
    return {(p, m) for p, m, ev, bar in rows
            if len(ev) == 1 and ev[0][0] and bar and ev[0][2] * 2 == bar}


def _run(result, *, on):
    order = tuple(q for q in adjudicate.ORDER
                  if on or q != Q.NOTEHEAD_IS_A_WHOLE_REST)
    log = rebuild(result["record"])
    adjudicate.run(log, order=order)
    evaluate.run(log)
    xml, report = EXPORT.to_musicxml({"record": log.to_json(),
                                      "source": result.get("source", {})})
    return log, xml, report


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args(argv)
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    result = json.loads(Path(args.record).read_text())
    saved = {v["subject"]: v for v in result["record"]["verdicts"]
             if v["quantity"] == Q.DURATION}

    off_log, off_xml, off_rep = _run(result, on=False)
    on_log, on_xml, on_rep = _run(result, on=True)

    # ── the CONTROL, before any delta ───────────────────────────────────────
    rebuilt = {v["subject"]: v for v in off_log.to_json()["verdicts"]
               if v["quantity"] == Q.DURATION}
    same = sum(1 for s, v in rebuilt.items()
               if s in saved and saved[s]["value"] == v["value"]
               and saved[s]["outcome"] == v["outcome"])
    print(f"CONTROL: the OFF arm reproduces {same} of {len(saved)} of the "
          f"record's own duration verdicts")
    if not saved or same < len(saved):
        print("  ⚠️ THE REBUILD DOES NOT REPRODUCE THE PIPELINE — a delta "
              "measured against it is measuring the rebuild.")

    # ── REACH ───────────────────────────────────────────────────────────────
    vs = [v for v in on_log.to_json()["verdicts"]
          if v["quantity"] == Q.NOTEHEAD_IS_A_WHOLE_REST]
    n_true = sum(1 for v in vs if v["value"] is True)
    by_reason = collections.Counter(v["reason"] for v in vs)
    by_witness = collections.Counter((v.get("detail") or {}).get("witness")
                                     for v in vs if v["value"] is True)
    print(f"\nREACH: {len(vs)} noteheads asked, {n_true} answered "
          f"'this is a whole rest'")
    for k, n in by_reason.most_common():
        print(f"   {k:<34} {n}")
    print(f"   witness: {dict(by_witness)}")
    if not vs:
        print("INSTRUMENT DEAD: the decision produced no verdict at all.")
        return 2
    if n_true == 0:
        print("THE RULE FIRES ON NOTHING HERE — the two arms are identical "
              "for a reason that is not the rule working.")
        return 2

    # ── the delta ───────────────────────────────────────────────────────────
    (out / "off.musicxml").write_text(off_xml)
    (out / "on.musicxml").write_text(on_xml)
    print("\nWHAT REACHED THE FILE")
    for k in ("notes", "rests", "measure_rests_read", "empty_bars_padded",
              "empty_bars_padded_without_meter", "slurs", "ties",
              "dynamics", "articulations", "fermatas", "parts", "measures"):
        a, b = off_rep["written"].get(k), on_rep["written"].get(k)
        mark = "   <-- MOVED" if a != b else ""
        print(f"   {k:<34} {a}  ->  {b}{mark}")
    print(f"   {'notes_not_written_total':<34} "
          f"{off_rep['notes_not_written_total']}  ->  "
          f"{on_rep['notes_not_written_total']}")
    print("   notes_not_written buckets:")
    keys = set(off_rep["notes_not_written"]) | set(on_rep["notes_not_written"])
    for k in sorted(keys):
        a = off_rep["notes_not_written"].get(k, 0)
        b = on_rep["notes_not_written"].get(k, 0)
        print(f"     {k:<32} {a}  ->  {b}")

    off_rows, on_rows = _bars(off_xml), _bars(on_xml)
    lq_off, lq_on = _lone_quarters(off_rows), _lone_quarters(on_rows)
    print(f"\nBARS whose whole content is one lone QUARTER in 2/4: "
          f"{len(lq_off)}  ->  {len(lq_on)}")
    print(f"   cleared: {sorted(lq_off - lq_on)}")
    print(f"   created: {sorted(lq_on - lq_off)}")

    off_notes = [(p, m, e) for p, m, ev, _ in off_rows for e in ev if e[0]]
    on_notes = [(p, m, e) for p, m, ev, _ in on_rows for e in ev if e[0]]
    print(f"\nPITCHED <note> elements: {len(off_notes)}  ->  {len(on_notes)}")
    gone = collections.Counter(x for x in off_notes) - collections.Counter(on_notes)
    added = collections.Counter(on_notes) - collections.Counter(off_notes)
    print(f"   removed {sum(gone.values())}, added {sum(added.values())}")
    if added:
        print("   ⚠️ THE RULE ONLY EVER REFUSES; anything ADDED is a "
              "downstream re-planning and must be explained:")
        for k, n in added.most_common(20):
            print(f"     +{n}  {k}")

    json.dump({"reach": {"asked": len(vs), "true": n_true,
                         "reasons": dict(by_reason),
                         "witness": {str(k): v for k, v in by_witness.items()}},
               "control_duration_verdicts": [same, len(saved)],
               "off": off_rep, "on": on_rep,
               "lone_quarters": [len(lq_off), len(lq_on)],
               "notes": [len(off_notes), len(on_notes)]},
              open(out / "arm.json", "w"), indent=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
