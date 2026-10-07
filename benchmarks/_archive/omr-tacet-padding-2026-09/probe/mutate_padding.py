"""Mutation battery for the tacet padding. RUN IT ALONE.

    python3 benchmarks/omr-tacet-padding-2026-09/probe/mutate_padding.py

⚠️⚠️ **IT MUST LEAVE THE TREE AS IT FOUND IT — WHICH IS NOT THE SAME AS
LEAVING IT AS VERSION CONTROL HAS IT.** The battery next door destroyed the
change it had just certified by restoring its subject from `HEAD`, which did
not carry the new function: ten arms went red, the file was reverted, and the
tests that had just passed were testing code no longer on disk. So this takes a
BYTE snapshot before the first arm, restores from that snapshot, and VERIFIES
the restore — exiting 3 if it does not match. Commit a checkpoint first anyway,
so the snapshot and version control agree.

⚠️ **AND IT MUST NOT RUN BESIDE THE A/B ARM.** `padding_arm.py` imports the
module this rewrites; a mutated `export.py` on disk while that arm is reading
it is the collision CLAUDE.md already records costing a session its first
three-arm run.

⚠️ **ONE RED ARM IS NOT A BATTERY**, and a battery of REFUSAL tests passes by
refusing everything — `everything_refuses` is the positive control in the same
class: an arm that makes the rule never fire must fail the tests asserting a
document IS padded.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TARGET = ROOT / "tools/omr/staged/export.py"
TESTS = ["tools/omr/tests/test_staged_tacet_padding.py",
         "tools/omr/tests/test_staged_measure_numbering.py"]

#: `(name, anchor, replacement)`. The anchor must occur EXACTLY ONCE — an
#: anchor that occurs twice is how the fermata battery silently mutated a
#: different function, and a BAD ANCHOR is reported as an error rather than
#: passing quietly.
ARMS = [
    ("pads_without_a_meter",
     '            counters["tacet_bars_not_padded_without_meter"] += 1\n'
     "            continue",
     '            counters["tacet_bars_not_padded_without_meter"] += 1\n'
     "            meter = {}"),

    ("meter_per_system_not_per_bar",
     "        meter = _meter_dict(meter_at(sys_meter, i) if segments_on\n"
     "                            else sys_meter)",
     "        meter = _meter_dict(meter_at(sys_meter, 0) if segments_on\n"
     "                            else sys_meter)"),

    ("off_by_one_number",
     "        lines.append(f'    <measure number=\"{base + i + 1}\">')",
     "        lines.append(f'    <measure number=\"{base + i}\">')"),

    ("walk_ignores_spans",
     "    if offsets is None or spans is None:\n"
     "        return [((r.page, r.system), r, r.n_measures) for r in part]",
     "    if True:\n"
     "        return [((r.page, r.system), r, r.n_measures) for r in part]"),

    ("report_not_written",
     '    report["tacet_padding"] = _tacet_report(parts, offsets, spans, counters)',
     '    report["tacet_padding"] = {}'),

    ("counters_not_preinitialised",
     '    counters["tacet_bars_padded"] += 0\n'
     '    counters["tacet_bars_not_padded_without_meter"] += 0',
     "    pass"),

    ("empty_bars_absorbs_it",
     '        counters["tacet_bars_padded"] += 1',
     '        counters["empty_bars_padded"] += 1'),

    ("rest_not_sized_to_the_bar",
     "        lines.extend(_legacy._mxl_empty_measure(\n"
     '            meter, divisions, None, "      "))',
     "        lines.extend(_legacy._mxl_empty_measure(\n"
     '            None, divisions, None, "      "))'),

    ("pad_states_a_clef",
     "        if first:\n"
     "            lines.append(_legacy._mxl_attributes_block(\n"
     '                None, None, meter, divisions, "      ",\n'
     "                include_divisions=True))\n"
     "            first = False",
     "        lines.append(_legacy._mxl_attributes_block(\n"
     '            "treble", None, meter, divisions, "      ",\n'
     "            include_divisions=first))\n"
     "        first = False"),

    ("refusal_reports_a_zero",
     '        out["refused"] = "the_document_bar_sequence_was_refused"\n'
     '        out["tacet_bar_total"] = None\n'
     '        out["balanced"] = None',
     "        pass"),

    ("system_key_swapped",
     '        [((r["page"], r["system_index"]), int(r["bars"]))',
     '        [((r["system_index"], r["page"]), int(r["bars"]))'),

    # ── THE POSITIVE CONTROL, in the same class as the refusals ────────────
    ("everything_refuses",
     "    base = offsets.get(sys_key)\n"
     "    sys_meter = meters.get(sys_key)",
     "    return first\n"
     "    base = offsets.get(sys_key)\n"
     "    sys_meter = meters.get(sys_key)"),
]


def run_tests() -> bool:
    r = subprocess.run([sys.executable, "-m", "pytest", *TESTS, "-q",
                        "-p", "no:randomly"],
                       cwd=ROOT, capture_output=True, text=True)
    return r.returncode == 0


def main() -> int:
    snapshot = TARGET.read_bytes()
    print("snapshot: %d bytes of %s" % (len(snapshot), TARGET.name))

    print("\nunmutated tree ... ", end="", flush=True)
    if not run_tests():
        print("RED — fix the tree before running a battery")
        return 2
    print("GREEN")

    survivors, bad_anchors = [], []
    try:
        for name, anchor, repl in ARMS:
            text = snapshot.decode()
            n = text.count(anchor)
            if n != 1:
                bad_anchors.append((name, n))
                print("  %-32s BAD ANCHOR (%d occurrences)" % (name, n))
                continue
            TARGET.write_text(text.replace(anchor, repl, 1))
            green = run_tests()
            print("  %-32s %s" % (name, "SURVIVED" if green else "red"))
            if green:
                survivors.append(name)
            TARGET.write_bytes(snapshot)
    finally:
        TARGET.write_bytes(snapshot)

    if TARGET.read_bytes() != snapshot:
        print("\nRESTORE FAILED — the tree is NOT as this battery found it")
        return 3
    print("\nrestore verified: byte-identical to the snapshot")
    print("arms %d, survivors %d, bad anchors %d"
          % (len(ARMS), len(survivors), len(bad_anchors)))
    if survivors:
        print("SURVIVORS:", ", ".join(survivors))
    return 1 if (survivors or bad_anchors) else 0


if __name__ == "__main__":
    sys.exit(main())
