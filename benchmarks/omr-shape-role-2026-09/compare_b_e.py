#!/usr/bin/env python3
"""ROADMAP 2.12b / 2.12e — the base-vs-arm table, PRINTED FROM THE FILES.

    python3 benchmarks/omr-shape-role-2026-09/compare_b_e.py

⚠️ IT COMPUTES NOTHING ABOUT THE PIPELINE. It reads the `--off` and arm JSONs
`readjudicate_b_e.py` wrote and differences them, so that the table in
`FINDINGS.md` §2.12b/§2.12e is generated rather than typed and a reader can
reproduce it with one command instead of trusting a transcription.

⚠️ THE CONTROL IS PRINTED FIRST AND IS NOT THIS LANE'S. `--off` reproduces the
record's own `duration` verdicts on TODAY's tree, and where it falls short the
tree has moved since the record was gathered (CLAUDE.md §6b). A delta read
without that number beside it is a delta read against the wrong baseline.
"""
from __future__ import annotations

import json
import pathlib
import sys

_OUT = pathlib.Path(__file__).resolve().parent / "out"
_LABELS = ("beethoven5-litolff", "brahms1-breitkopf", "beethoven5-engraved")


#: ROADMAP 2.12b-cal writes its own pair of files rather than overwriting
#: 2.12b's, because 2.12b's are the evidence under a merged roadmap line and a
#: rerun that lands on top of them destroys the thing a later reader would
#: check the line against. `--prefix cal` reads `cal--<label>--base/arm.json`,
#: where BASE is 2.12b's nominal bands (`readjudicate_b_e.py --old-bands`) and
#: ARM is the calibrated ones, both rebuilt on ONE tree.
_PREFIX = "be"


def _load(label: str, arm: str):
    p = _OUT / ("%s--%s--%s.json" % (_PREFIX, label, arm))
    return json.loads(p.read_text()) if p.exists() else None


def main() -> int:
    global _PREFIX
    if len(sys.argv) > 2 and sys.argv[1] == "--prefix":
        _PREFIX = sys.argv[2]
    missing = []
    rows = []
    for label in _LABELS:
        b, a = _load(label, "base"), _load(label, "arm")
        if not b or not a:
            missing.append(label)
            continue
        rows.append((label, b, a))
    if missing:
        print("MISSING (run readjudicate_b_e.py first): %s" % missing)
    if not rows:
        return 1

    print("=== CONTROL — the `--off` rebuild against the record's own "
          "duration verdicts ===")
    for label, b, _a in rows:
        c = b.get("control")
        prov = "[record %s dirty=%s]" % (
            (b.get("provenance") or {}).get("commit", "?")[:8],
            (b.get("provenance") or {}).get("dirty"))
        if not c:
            # ⚠️ NOT PRINTED AS A ZERO. `--old-bands` (2.12b-cal's base) does
            # not carry the control, because the control compares a RULE-OFF
            # rebuild with the record's own verdicts and this base has the
            # rule on. Saying so beats printing -1 of -1, which reads like a
            # control that ran and found nothing.
            print("  %-20s base arm=%s — no control in this arm; run "
                  "`--control` separately   %s"
                  % (label, b.get("arm"), prov))
            continue
        print("  %-20s %d of %d reproduced, %d differ %s   %s"
              % (label, c.get("reproduced", -1), c.get("on_the_record", -1),
                 c.get("differ", -1), c.get("kinds") or "", prov))

    print()
    print("=== 2.12b — what the slot said about each rest ===")
    for label, b, a in rows:
        base = b["adjudicate"]["rest_slot_says"]
        arm = a["adjudicate"]["rest_slot_says"]
        print("  %-20s base %s" % (label, base))
        print("  %-20s arm  %s" % ("", arm))

    print()
    print("=== 2.12e — where a flag's direction came from ===")
    for label, b, a in rows:
        print("  %-20s base %s  disagreements %d  flags attached %d"
              % (label, b["adjudicate"]["flag_direction_source"] or "{}",
                 b["adjudicate"]["flag_disagreements"],
                 b["adjudicate"]["flags_attached_total"]))
        print("  %-20s arm  %s  disagreements %d  flags attached %d"
              % ("", a["adjudicate"]["flag_direction_source"] or "{}",
                 a["adjudicate"]["flag_disagreements"],
                 a["adjudicate"]["flags_attached_total"]))

    print()
    print("=== the file, base -> arm ===")
    keys = ("notes", "rests", "measure_rests", "notes_not_written_total")
    for label, b, a in rows:
        be, ae = b["export"], a["export"]
        bits = ["%s %d->%d" % (k, be[k], ae[k]) for k in keys]
        print("  %-20s %s" % (label, "  ".join(bits)))
        dr = {k: (be["notes_not_written"].get(k, 0),
                  ae["notes_not_written"].get(k, 0))
              for k in sorted(set(be["notes_not_written"])
                              | set(ae["notes_not_written"]))}
        moved = {k: v for k, v in dr.items() if v[0] != v[1]}
        print("  %-20s refusals that MOVED: %s" % ("", moved or "none"))
        bb, ab = be["bars_held_out_sum"], ae["bars_held_out_sum"]
        ins = set(ae["held_out_bar_keys"]) - set(be["held_out_bar_keys"])
        outs = set(be["held_out_bar_keys"]) - set(ae["held_out_bar_keys"])
        print("  %-20s bars held out %s -> %s of %s   moved IN %d, moved OUT "
              "%d" % ("", bb.get("bars"), ab.get("bars"),
                      ab.get("of_bars_with_events"), len(ins), len(outs)))
        print("  %-20s census unaccounted %s / %s   balanced %s / %s"
              % ("", be["census_unaccounted"], ae["census_unaccounted"],
                 be["balance"].get("balanced"), ae["balance"].get("balanced")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
