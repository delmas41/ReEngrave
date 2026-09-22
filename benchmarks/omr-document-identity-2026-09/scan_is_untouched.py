"""THE SCAN FILE DOES NOT MOVE — and a control proving the comparison has teeth.

The one-sided tier must be a NO-OP on a document measured `scanned`. That is
easy to assert and easy to assert VACUOUSLY: two exports of a record the rule
never touches are identical whether or not the rule exists.

So this runs THREE arms over one scan gather:

    OFF        the shipped precedence
    ON         the flag on, and the document measures `scanned`
    CONTROL    the flag on, with the record's own `input_domain` row
               REWRITTEN to `engraved` -- a page the tier WOULD act on

**OFF and ON must be byte-identical. CONTROL must differ.** Without the third
arm the first two prove nothing about the rule, only about the export.

    python3 benchmarks/omr-document-identity-2026-09/scan_is_untouched.py \
        --record .../litolff-p1-identity.record.json
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import os
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools.omr.staged import adjudicate, evaluate            # noqa: E402
from tools.omr.staged import adjudicators, consequences      # noqa: E402,F401
from tools.omr.staged.adjudicators import header as H        # noqa: E402
from tools.omr.staged.record import Q                        # noqa: E402

_RJ = REPO / "benchmarks/omr-staged-duration-beams-2026-09/readjudicate.py"
_spec = importlib.util.spec_from_file_location("_canonical_rj", _RJ)
_canon = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_canon)


def _keys(log):
    """Every LIVE key-signature verdict, as a comparable dict."""
    out = {}
    for v in log.all_verdicts():
        if v.quantity != Q.KEY_SIGNATURE:
            continue
        live = log.verdict(Q.KEY_SIGNATURE, v.subject)
        out[v.subject.to_key()] = (live.outcome.value, live.value, live.reason)
    return out


def run(rec: dict, flag: str) -> dict:
    os.environ[H.ENGRAVED_KEYSIG_ENV] = flag
    log = _canon.rebuild(rec)
    adjudicate.run(log)
    evaluate.run(log)
    return _keys(log)


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--record", type=Path, required=True)
    ap.add_argument("--json-out", type=Path)
    #: ⚠️ A POSITIVE CONTROL ON THE VACUITY GUARD, not a mode anyone runs for
    #: a result. `return 0 if (same and moved) else 1` only DOES anything when
    #: `moved` is False, which on a healthy tree never happens -- so a battery
    #: arm dropping `and moved` changed neither the exit code nor a printed
    #: line and reported SURVIVED. This forces the state the guard exists for.
    ap.add_argument("--no-forge", action="store_true",
                    help="skip the forging, so the control CANNOT differ; the "
                         "instrument must then REFUSE (exit 1)")
    args = ap.parse_args()

    rec = json.loads(args.record.read_text())["record"]
    dom = [o for o in rec["observations"] if o.get("quantity") == Q.INPUT_DOMAIN]
    print(f"── REACH: Q.INPUT_DOMAIN {[o.get('value') for o in dom]}")
    if not dom:
        print("⚠️ DEAD: this record carries no domain row at all.")
        return 2
    if dom[0].get("value") != "scanned":
        print(f"⚠️ DEAD: this record is not a SCAN, so it cannot show the "
              f"scan fall-through.")
        return 2

    off, on = run(rec, "0"), run(rec, "1")

    forged = copy.deepcopy(rec)
    if not args.no_forge:
        for o in forged["observations"]:
            if o.get("quantity") == Q.INPUT_DOMAIN:
                o["value"] = "engraved"
    ctrl = run(forged, "1")

    same = off == on
    moved = ctrl != off
    print(f"   verdicts: {len(off)}   reasons "
          f"{dict(Counter(t[2] for t in off.values()))}")
    print(f"\n   OFF == ON                      {same}   "
          f"{'✅ the scan is untouched' if same else '⚠️ THE SCAN MOVED'}")
    print(f"   CONTROL (forced `engraved`)    "
          f"{'DIFFERS' if moved else 'IDENTICAL'}   "
          f"{'✅ the comparison has teeth' if moved else '⚠️ VACUOUS — the two arms above prove NOTHING'}")
    if moved:
        ch = [k for k in off if off[k] != ctrl[k]]
        print(f"   control changed {len(ch)} of {len(off)} verdicts, "
              f"reasons {dict(Counter(ctrl[k][2] for k in ch))}")

    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(
            {"n_verdicts": len(off), "off_equals_on": same,
             "control_differs": moved,
             "off_reasons": dict(Counter(t[2] for t in off.values())),
             "control_reasons": dict(Counter(t[2] for t in ctrl.values()))},
            indent=1))
        print(f"\nwrote {args.json_out}")
    # ⚠️ BOTH conditions. A run where the scan is untouched AND the control is
    # vacuous is a PASS-shaped nothing.
    return 0 if (same and moved) else 1


if __name__ == "__main__":
    raise SystemExit(main())
