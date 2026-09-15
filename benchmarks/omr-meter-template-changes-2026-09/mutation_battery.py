#!/usr/bin/env python3
"""Mutation battery for the bar-head template reader.

⚠️⚠️ IT RESTORES FROM A BYTE SNAPSHOT IT TAKES ITSELF, NOT FROM GIT. CLAUDE.md
records a battery that certified a change and then DESTROYED it: ten arms went
red, the battery `git checkout`ed the files it had mutated, and HEAD did not
have the new function — `git diff --stat` afterwards listed only the benchmark
script and the tests that had just passed were testing code no longer on disk.

    > **A mutation battery must leave the tree as it FOUND it — which is not
    > the same as leaving it as GIT has it.**

So: a byte snapshot before the first arm, restore from the snapshot, and the
restore is VERIFIED against that snapshot before the run is allowed to report
anything. The cheap prophylactic is still worth taking as well — commit a
checkpoint before running this.

⚠️ ONE RED ARM IS NOT A BATTERY, and a battery of REFUSAL tests can pass by
refusing everything — so `everything_refuses` is here as a POSITIVE CONTROL in
the same class: with the consensus quorum set beyond any reachable number the
ACCEPT tests must go red, and if they do not, every refusal test below them is
passing for free.

    python3 benchmarks/omr-meter-template-changes-2026-09/mutation_battery.py
"""
from __future__ import annotations

import hashlib
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
TESTS = "tools/omr/tests/test_meter_template_at_bar.py"
GATHER = ROOT / "tools/omr/staged/gather.py"
RHYTHM = ROOT / "tools/omr/staged/adjudicators/rhythm.py"

#: (name, file, old, new, note). Each `old` must occur EXACTLY ONCE — a
#: two-occurrence anchor is how a previous battery silently mutated a
#: different function and reported a survivor that was never tested.
ARMS = [
    ("window_is_the_whole_cell", GATHER,
     "    width = int(round(spaces * spacing))",
     "    width = 10 ** 6  # MUTANT",
     "the bar-head window becomes the whole bar — the false-positive rate "
     "at 8 spaces is already 2.5x the rate at 4"),
    ("window_ignores_the_spacing", GATHER,
     "    width = min(int(image.shape[1]), width)",
     "    width = min(int(image.shape[1]), 64)  # MUTANT",
     "a fixed pixel width, so the slice stops tracking the staff's scale"),
    ("no_geometry_is_not_an_abstention", GATHER,
     "    metrics = staff_metrics(cell)\n    if metrics is None:\n        return None",
     "    metrics = staff_metrics(cell) or (25.0, 0.0, 100.0)  # MUTANT",
     "a cell with no five-line geometry gets an invented spacing"),
    ("cell_zero_is_a_candidate", GATHER,
     "            if cell_index == 0:\n                continue",
     "            if False:  # MUTANT\n                continue",
     "the OPENING bar becomes a change candidate"),
    ("candidates_ignore_the_class", GATHER,
     '            if not any(d.smufl_name.startswith("timeSig") for d in cell_dets):',
     "            if not cell_dets:  # MUTANT",
     "every bar with any ink at all is asked"),
    ("the_flag_does_nothing", GATHER,
     "    if not _meter_template_at_bar_enabled():\n        return",
     "    if False:  # MUTANT\n        return",
     "flag-off stops being byte-identical"),
    ("the_flag_is_a_deny_list", GATHER,
     '    return os.environ.get(METER_TEMPLATE_AT_BAR_ENV, "0").strip().lower() in (\n        "1", "true", "yes", "on")',
     '    return os.environ.get(METER_TEMPLATE_AT_BAR_ENV, "0").strip().lower() not in (\n        "0", "", "false", "no", "off")  # MUTANT',
     "a default-OFF flag written as a deny-list — a typo switches it ON"),
    ("the_bar_is_not_recorded", GATHER,
     "                        cell=cell_index, score=float(found.score),",
     "                        score=float(found.score),  # MUTANT",
     "the reading loses the bar it was taken at, so the consumer cannot "
     "group it — the `Q.METER_GLYPH` fixture-mismatch shape"),
    ("a_lone_reading_is_admitted", RHYTHM,
     "        if len(staves) < METER_TEMPLATE_AT_BAR_MIN_STAVES:\n            continue",
     "        if False:  # MUTANT\n            continue",
     "⚠️ THE ONE THAT MATTERS: the consensus is where all the safety is. "
     "Measured, admitting a lone reading produces 16 spurious columns on "
     "ten real pages that print no change."),
    ("the_quorum_is_two", RHYTHM,
     "METER_TEMPLATE_AT_BAR_MIN_STAVES = 3",
     "METER_TEMPLATE_AT_BAR_MIN_STAVES = 2  # MUTANT",
     "two agreeing staves — measured at 2 spurious columns, not zero"),
    ("the_printed_form_leaves_the_key", RHYTHM,
     '        raw = detail.get("raw") or f"{num}/{den}"\n        out.setdefault(cell, {}).setdefault((num, den, raw), set()).add(',
     '        raw = "X"  # MUTANT\n        out.setdefault(cell, {}).setdefault((num, den, raw), set()).add(',
     "`C` and `4/4` get averaged into one reading"),
    ("cell_zero_reaches_the_consumer", RHYTHM,
     "        cell = int(cell)\n        if cell == 0:\n            continue                      # cell 0 states the staff's OPENING",
     "        cell = int(cell)\n        if False:  # MUTANT\n            continue",
     "an opening reading is offered as a change"),
    ("the_admitted_staves_are_not_recorded", RHYTHM,
     '            if template_admitted.get((num, den, raw)):\n                cand["staves_from_bar_head_template"] = (',
     '            if False:  # MUTANT\n                cand["staves_from_bar_head_template"] = (',
     "the flag's effect becomes invisible in the verdict"),
    ("the_segment_projection_drops_it", RHYTHM,
     '        if c.get("staves_from_bar_head_template"):\n            segments[-1]["staves_from_bar_head_template"] = (',
     '        if False:  # MUTANT\n            segments[-1]["staves_from_bar_head_template"] = (',
     "⚠️ THE REAL BUG THIS BATTERY'S SUBJECT ALREADY HAD ONCE: the field was "
     "set on the candidate and the whitelist projection dropped it"),
    # ⚠️ POSITIVE CONTROL, in the same class as the refusal arms.
    ("POSITIVE_everything_refuses", RHYTHM,
     "METER_TEMPLATE_AT_BAR_MIN_STAVES = 3",
     "METER_TEMPLATE_AT_BAR_MIN_STAVES = 10 ** 6  # MUTANT",
     "nothing is ever admitted — the ACCEPT tests must go red, and if they "
     "do not then every refusal test above is passing for free"),
]


def _run_tests() -> bool:
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", TESTS, "-q", "--no-header", "-x"],
        cwd=ROOT, capture_output=True, text=True)
    return proc.returncode == 0


def main() -> int:
    snapshot = {p: p.read_bytes() for p in (GATHER, RHYTHM)}
    digests = {p: hashlib.sha256(b).hexdigest() for p, b in snapshot.items()}

    print("baseline (unmutated) ...", flush=True)
    if not _run_tests():
        print("BASELINE IS RED. Nothing below this line means anything.",
              file=sys.stderr)
        return 2
    print("  green\n")

    results = []
    try:
        for name, path, old, new, note in ARMS:
            text = snapshot[path].decode()
            count = text.count(old)
            if count != 1:
                results.append((name, "BAD ANCHOR", count, note))
                print(f"  {name:<38} BAD ANCHOR (occurs {count}x)")
                continue
            path.write_text(text.replace(old, new))
            red = not _run_tests()
            path.write_bytes(snapshot[path])
            results.append((name, "red" if red else "SURVIVED", 1, note))
            print(f"  {name:<38} {'red' if red else 'SURVIVED'}")
    finally:
        # ⚠️ FROM THE SNAPSHOT, and then VERIFIED. A restore that silently
        # failed is how a battery destroys the change it just certified.
        for path, blob in snapshot.items():
            path.write_bytes(blob)
        for path, want in digests.items():
            got = hashlib.sha256(path.read_bytes()).hexdigest()
            if got != want:
                print(f"\n⚠️⚠️ RESTORE FAILED for {path} "
                      f"({got[:12]} != {want[:12]})", file=sys.stderr)
                return 3
        print("\nrestore VERIFIED byte-for-byte against the snapshot")

    survived = [r for r in results if r[1] != "red"]
    print(f"\n{len(results)} arms, {len(results) - len(survived)} red, "
          f"{len(survived)} not red")
    for name, state, count, note in survived:
        print(f"  ⚠️ {name}: {state} — {note}")
    return 0 if not survived else 1


if __name__ == "__main__":
    raise SystemExit(main())
