"""ONE GATHER, ADJUDICATED TWICE, EXPORTED TWICE — the rest-sizing A/B.

⚠️ WHY NOT A PLAIN RE-EXPORT. `size_measure_rest` is an EVALUATE consequence
and the meter is an ADJUDICATE decision, so re-exporting a SAVED record replays
saved verdicts and is BLIND to both. This rebuilds a `Log` from the record's
GATHER rows (`readjudicate.rebuild`), re-runs ADJUDICATE and EVALUATE under a
named environment, and only then exports — so the two arms differ in the rule
under test and in nothing else.

⚠️⚠️ WHAT IT IS BLIND TO, stated because a green number here has been reported
as evidence for something it could not test: it CANNOT see a GATHER change.
New rows, new fields, a changed frame never enter the rebuild, and the arms
would come back identical whatever the change did. The only instrument for
that is two full re-gathers.

⚠️ REACH IS PRINTED BEFORE ANYTHING ELSE. A page whose systems all read their
own meter would make every arm here identical and the run would look clean; the
header says how many systems ABSTAINED so a dead instrument cannot read as a
result.

    python3 rest_sizing_arm.py <record.json> --env OMR_METER_CARRY=1
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.omr.staged import adjudicate, evaluate                  # noqa: E402
from tools.omr.staged import adjudicators, consequences            # noqa: E402,F401
from tools.omr.staged import export as EXPORT                      # noqa: E402
from tools.omr.staged.record import Outcome                        # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]
                       / "omr-staged-duration-beams-2026-09"))
from readjudicate import rebuild                                   # noqa: E402


def rest_table(xml_text: str) -> collections.Counter:
    """Rest `<duration>` in QUARTER NOTES, over the whole file."""
    root = ET.fromstring(xml_text)
    out: collections.Counter = collections.Counter()
    for part in root.findall("part"):
        div = None
        for meas in part.findall("measure"):
            d = meas.find("./attributes/divisions")
            if d is not None:
                div = float(d.text)
            for note in meas.findall("note"):
                if note.find("rest") is None or div is None:
                    continue
                out[float(note.find("duration").text) / div] += 1
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--env", action="append", default=[],
                    help="NAME=VALUE applied before ADJUDICATE")
    ap.add_argument("--bar-beats", type=float, default=2.0)
    ap.add_argument("--out-xml")
    ap.add_argument("--json-out")
    args = ap.parse_args(argv)

    for pair in args.env:
        name, _, value = pair.partition("=")
        os.environ[name] = value

    result = json.loads(Path(args.record).read_text())
    log = rebuild(result["record"])
    adjudicate.run(log)
    evaluate.run(log)

    # ---- REACH, printed first ------------------------------------------
    meters = [v for v in log.to_json()["verdicts"] if v["quantity"] == "meter"]
    decided = [v for v in meters if v["outcome"] == "decided"]
    print("REACH: %d systems carry a meter verdict, %d DECIDED, %d abstained"
          % (len(meters), len(decided), len(meters) - len(decided)))
    for v in sorted(meters, key=lambda r: r["subject"]):
        val = v.get("value") or {}
        print("   %-14s %-9s %-30s %s/%s  support=%s"
              % (v["subject"], v["outcome"], v["reason"],
                 val.get("numerator"), val.get("denominator"),
                 (v.get("detail") or {}).get("support")))
    if not meters:
        print("INSTRUMENT DEAD: the record holds no meter verdict at all.")
        return 2

    xml, report = EXPORT.to_musicxml({"record": log.to_json(),
                                      "source": result.get("source", {})})
    if args.out_xml:
        Path(args.out_xml).write_text(xml)

    tab = rest_table(xml)
    total = sum(tab.values())
    wrong = sum(n for b, n in tab.items()
                if abs(b - args.bar_beats) > 1e-6)
    print("\nRESTS IN THE FILE: %d, %d not the printed bar length (%s)"
          % (total, wrong, args.bar_beats))
    for b in sorted(tab):
        print("   %-8s x%-6d %s" % (b, tab[b],
                                    "OK" if abs(b - args.bar_beats) < 1e-6
                                    else "!!"))
    w = report["written"]
    for k in ("rests", "measure_rests_read", "empty_bars_padded",
              "empty_bars_padded_without_meter", "notes"):
        print("   %-34s %s" % (k, w.get(k)))
    print("   %-34s %s" % ("notes_not_written_total",
                           report.get("notes_not_written_total")))
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(
            {"env": args.env, "rests": {str(k): v for k, v in tab.items()},
             "written": w,
             "meters": [{"subject": v["subject"], "outcome": v["outcome"],
                         "reason": v["reason"], "value": v.get("value")}
                        for v in meters]}, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
