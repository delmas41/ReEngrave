"""ONE GATHER, ADJUDICATED AND EXPORTED TWICE -- the arms differ only in the rule.

⚠️ WHAT IT CAN AND CANNOT SEE, because a green number here has already been
about to be reported as evidence for something it could not test. The change
under test spans ADJUDICATE (a new decision) and EXPORT (the refusal that
consumes it), so NEITHER `readjudicate.py` nor `reexport_arm.py` can measure it
alone -- the first is blind to the export half, the second to the adjudicate
half. This rebuilds one `Log` from the saved record's own observations and
abstentions, runs ADJUDICATE + EVALUATE, and exports; the `--off` arm disables
only the rule's verdict, so the two arms share every detection.

⚠️ IT IS BLIND TO ANY GATHER CHANGE by exactly the same construction, and this
change makes none: the decision reads `Q.GLYPH_BOX`, `Q.STAFF_LINES` and
`Q.STAFF_SPACING`, all of which the record already holds.

⚠️ POSITIVE CONTROL FIRST: `--control` re-adjudicates with nothing disabled and
diffs every DURATION verdict against the pipeline's own, exactly as
`readjudicate.py --control` does. A rebuild that does not reproduce the record
is not a control, and every number below would be a measurement of the harness.

    python3 .../arm.py <record.json> --control
    python3 .../arm.py <record.json> --out-dir DIR
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from tools.omr.staged import adjudicate, evaluate          # noqa: E402
from tools.omr.staged import adjudicators                  # noqa: E402,F401
from tools.omr.staged import export as SX                  # noqa: E402
from tools.omr.staged.record import Log, Q, Subject        # noqa: E402


def rebuild(rec: dict) -> Log:
    log = Log()
    rows = [(r, "obs") for r in rec["observations"]]
    rows += [(r, "abs") for r in rec.get("abstentions", [])]
    rows.sort(key=lambda t: t[0]["id"])
    for r, kind in rows:
        sub = Subject.from_key(r["subject"])
        detail = dict(r.get("detail") or {})
        if kind == "obs":
            log.observe(sub, r["quantity"], r["value"], reader=r["reader"],
                        frame=r["frame"], score=r.get("score"), **detail)
        else:
            log.abstain(sub, r["quantity"], reader=r["reader"],
                        frame=r["frame"], reason=r["reason"], **detail)
    return log


def run(rec: dict, *, off: bool):
    log = rebuild(rec)
    adjudicate.run(log)
    evaluate.run(log)
    out = log.to_json()
    if off:
        # ⚠️ NOT "delete the quantity": the OLD behaviour is an exporter that
        # never asked, and dropping the verdicts reproduces exactly that,
        # leaving every other verdict on this arm byte-identical.
        out["verdicts"] = [v for v in out["verdicts"]
                           if v["quantity"] != Q.NOTEHEAD_IS_A_WHOLE_REST]
    return out


def measures_with_a_note(xml):
    """{(part, measure)} that carry at least one PITCHED note."""
    got = set()
    for part in ET.fromstring(xml).findall("part"):
        for m in part.findall("measure"):
            if any(n.find("pitch") is not None for n in m.findall("note")):
                got.add((part.get("id"), m.get("number")))
    return got


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--control", action="store_true")
    ap.add_argument("--out-dir")
    a = ap.parse_args()

    result = json.load(open(a.record))
    rec = result["record"]

    if a.control:
        log = rebuild(rec)
        adjudicate.run(log)
        evaluate.run(log)
        got = {v["subject"]: v for v in log.to_json()["verdicts"]
               if v["quantity"] == Q.DURATION}
        want = {v["subject"]: v for v in rec["verdicts"]
                if v["quantity"] == Q.DURATION}
        same = sum(1 for k, w in want.items()
                   if got.get(k) and got[k]["outcome"] == w["outcome"]
                   and got[k]["value"] == w["value"])
        print(f"CONTROL: {same} of {len(want)} duration verdicts reproduced")
        if same != len(want):
            print("  ⚠️ the rebuild does not reproduce the record -- "
                  "every figure below would be the harness's")
            return 1
        return 0

    arms = {}
    for name, off in (("off", True), ("on", False)):
        res = dict(result)
        res["record"] = run(rec, off=off)
        xml, report = SX.to_musicxml(res)
        arms[name] = (xml, report, res["record"])
        if a.out_dir:
            d = Path(a.out_dir)
            d.mkdir(parents=True, exist_ok=True)
            (d / f"{name}.musicxml").write_text(xml)
            json.dump(report, open(d / f"{name}.coverage.json", "w"), indent=1)

    on_rec = arms["on"][2]
    v = [x for x in on_rec["verdicts"]
         if x["quantity"] == Q.NOTEHEAD_IS_A_WHOLE_REST]
    print(f"verdicts written            {len(v)}")
    print(f"  {dict(collections.Counter(x['reason'] for x in v))}")
    flagged = [x for x in v if x["value"] is True]
    print(f"  DECIDED True              {len(flagged)}")
    if not flagged:
        print("  ⚠️ nothing flagged -- do not read the rest as a clean result")
    print()

    for name in ("off", "on"):
        xml, report, _ = arms[name]
        root = ET.fromstring(xml)
        print(f"--- arm {name}")
        print(f"    <note> with a pitch   "
              f"{sum(1 for n in root.iter('note') if n.find('pitch') is not None)}")
        print(f"    <rest>                {sum(1 for _ in root.iter('rest'))}")
        print(f"    notes_not_written     "
              f"{report['notes_not_written_total']} "
              f"{dict(report['notes_not_written'])}")
        print(f"    balanced              {report['balance']['balanced']}")

    off_m, on_m = (measures_with_a_note(arms["off"][0]),
                   measures_with_a_note(arms["on"][0]))
    gone = off_m - on_m
    print(f"\nbars that held a pitched note and now hold NONE: {len(gone)}")
    for k in sorted(gone, key=lambda t: (t[0], int(t[1])))[:40]:
        print(f"    {k[0]} m{k[1]}")
    print(f"bars that GAINED a pitched note: {len(on_m - off_m)}  "
          f"(must be 0 -- this rule only ever refuses)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
