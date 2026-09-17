"""MUTATION BATTERY — `positions.py` and the guarantees it makes.

⚠️⚠️ ONE RED ARM IS NOT A BATTERY. Every arm runs and is reported, and the
POSITIVE CONTROL IN THE SAME CLASS is here for the reason CLAUDE.md records: a
battery made only of refusal arms can pass by refusing everything.

⚠️⚠️ IT REFUSES A DIRTY TREE AND IT LEAVES AN IN-FLIGHT SENTINEL, both paid-for
disciplines here: a battery killed mid-arm left its mutation on disk with the
snapshot dying in the dead process, and one run over an uncommitted change
restored from the index and the change under test vanished. The restore is
VERIFIED by hash, never assumed.

    python3 benchmarks/omr-family-positions-2026-09/mutate.py
    python3 benchmarks/omr-family-positions-2026-09/mutate.py --force   # dirty tree
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
POSITIONS = ROOT / "tools/omr/staged/positions.py"
SENTINEL = Path(__file__).resolve().parent / ".mutation-in-flight.json"

TESTS = ["tools/omr/tests/test_staged_positions.py"]

#: (name, file, anchor, replacement, the test that MUST go red)
#:
#: ⚠️ EVERY ARM NAMES THE GUARANTEE IT BREAKS, not the line it edits. An arm
#: that reads as a diff teaches the next reader nothing about what is at stake.
ARMS = [
    # ── the flag: default OFF, allow-list, and ABSENT rather than quiet ────
    ("the_flag_defaults_ON", POSITIONS,
     '    return os.environ.get(POSITIONS_ENV, "0").strip().lower() in _ON_WORDS',
     '    return os.environ.get(POSITIONS_ENV, "1").strip().lower() '
     'not in ("0", "", "false", "no", "off")',
     "test_absent_is_off"),

    ("the_flag_is_a_deny_list_so_a_typo_turns_it_ON", POSITIONS,
     '    return os.environ.get(POSITIONS_ENV, "0").strip().lower() in _ON_WORDS',
     '    return os.environ.get(POSITIONS_ENV, "0").strip().lower() '
     'not in ("0", "false", "no", "off")',
     "test_a_typo_leaves_it_off"),

    ("the_flag_is_not_consulted_at_all", POSITIONS,
     "    if not positions_enabled():\n        return",
     "    if False:\n        return",
     "test_flag_off_writes_nothing_at_all"),

    # ── the frame: staff-relative, or it composes with nothing ─────────────
    ("the_step_is_measured_from_the_cell_top_not_the_staff_line", POSITIONS,
     "    return (float(y) - top_y) / half_step",
     "    return float(y) / half_step",
     "test_a_whole_rest_hangs_below_the_second_line"),

    ("the_unit_is_a_constant_instead_of_the_cells_own_half_step", POSITIONS,
     "    return (float(y) - top_y) / half_step",
     "    return (float(y) - top_y) / 100.0",
     "test_a_whole_rest_hangs_below_the_second_line"),

    ("the_band_offset_is_restated_instead_of_imported", POSITIONS,
     "    top = G._band_offset_spaces(min(y0, y1), bottom_line, spacing)",
     "    top = (min(y0, y1) - bottom_line) / (spacing * 2.0)",
     "test_the_band_value_is_spaces_below_the_bottom_line"),

    # ── the rest: which SIDE of which LINE, and the ambiguity survives ─────
    ("the_rest_attaches_to_the_farther_edge", POSITIONS,
     "    if abs(t_res) < abs(b_res):",
     "    if abs(t_res) > abs(b_res):",
     "test_a_whole_rest_hangs_below_the_second_line"),

    ("a_tie_between_the_two_edges_is_RESOLVED_instead_of_recorded", POSITIONS,
     "        edge, line, resid, hangs = None, None, None, None",
     '        edge, line, resid, hangs = "top", t_line, t_res, "below"',
     "test_a_rest_centred_between_two_lines_attaches_to_neither"),

    ("the_decisiveness_of_the_pick_is_not_recorded", POSITIONS,
     '        "attach_margin": abs(abs(t_res) - abs(b_res)),',
     '        "attach_margin": 1.0,',
     "test_attach_margin_says_how_decisive_the_pick_was"),

    ("only_the_winning_edge_survives_the_pick", POSITIONS,
     '        "top_line": t_line, "top_residual": t_res,\n'
     '        "bottom_line": b_line, "bottom_residual": b_res,',
     "",
     "test_both_edges_are_recorded_whatever_the_pick"),

    # ── the meter: a measurement, never a veto ─────────────────────────────
    ("a_spanning_meter_glyph_is_REFUSED_instead_of_recorded", POSITIONS,
     "            _observe_step(log, staff_sub, Q.METER_GLYPH_POSITION,",
     "            if core['top'] < MIDDLE_LINE_STEP < core['bottom']:\n"
     "                continue\n"
     "            _observe_step(log, staff_sub, Q.METER_GLYPH_POSITION,",
     "test_a_meter_glyph_crossing_the_middle_line_is_still_recorded"),

    # ⚠️ THE TARGET IS THE NARROW TEST, NOT THE OBVIOUS ONE. This arm first
    # named `test_a_meter_digit_names_the_half_it_stands_in` and SURVIVED:
    # that fixture's two boxes touch the middle line from both sides, so they
    # stay correct for any cut in [4.0, 8.0]. The gap was real and closing it
    # took a new fixture whose boxes sit WHOLLY inside one half.
    ("the_half_is_decided_against_a_constant_not_the_middle_line", POSITIONS,
     "    elif bottom <= MIDDLE_LINE_STEP:",
     "    elif bottom <= 6.0:",
     "test_the_half_is_cut_at_the_MIDDLE_LINE_and_not_some_other_step"),

    ("the_fused_stroke_case_loses_its_own_measurement", POSITIONS,
     '        "centre_steps_from_middle": core["_centre"] - MIDDLE_LINE_STEP,',
     '        "centre_steps_from_middle": 0.0,',
     "test_a_meter_digit_names_the_half_it_stands_in"),

    # ── the mark families: a RULER, not the class name's own suffix ────────
    ("the_measured_side_is_taken_from_the_class_name", POSITIONS,
     '    o = _outside(top, bottom)\n'
     '    return "inside" if o == 0.0 else ("above" if o < 0.0 else "below")',
     '    return "above"',
     "test_a_mark_is_measured_not_read_off_its_class_name"),

    ("a_fermata_is_filed_as_an_articulation", POSITIONS,
     '    if name.lower().startswith(G._FERMATA_PREFIX):\n        return "fermata"',
     '    if name.lower().startswith(G._FERMATA_PREFIX):\n'
     '        return "articulation"',
     "test_a_fermata_is_not_an_articulation"),

    ("the_routing_is_restated_instead_of_imported_from_gather", POSITIONS,
     "    if name in G._ARC_CLASSES:",
     '    if name in ("tie", "slur"):',
     "test_the_predicates_come_from_gather"),

    ("a_tremolo_stops_being_an_ornament", POSITIONS,
     "    if G._ornament_kind(name) is not None:",
     '    if name.startswith("ornament"):',
     "test_a_tremolo_is_an_ornament_though_its_name_says_otherwise"),

    # ── the arc: its OWN ink, and no claim about curvature ─────────────────
    ("the_arc_claims_which_way_it_bends", POSITIONS,
     '        "opens": None,',
     '        "opens": "up",',
     "test_an_arc_does_not_claim_which_way_it_bends"),

    ("the_arcs_depth_is_not_measured", POSITIONS,
     '        "depth_steps": bottom - top,',
     '        "depth_steps": 1.0,',
     "test_an_arc_records_its_own_depth"),

    # ── the record's contract ──────────────────────────────────────────────
    ("a_position_row_carries_the_detectors_confidence", POSITIONS,
     '    return log.observe(subject, quantity, float(core["_centre"]),\n'
     "                       reader=READERS.GEOMETRY, frame=frame, **detail)",
     '    return log.observe(subject, quantity, float(core["_centre"]),\n'
     "                       reader=READERS.GEOMETRY, frame=frame, score=0.5,\n"
     "                       **detail)",
     "test_every_position_row_is_scoreless"),

    ("a_promoted_row_is_derived_from_its_source_and_so_is_ONE_signal",
     POSITIONS,
     "        _observe_band(log, row.subject, quantity, core,\n"
     "                      promoted_from=row.id, source_reader=row.reader)",
     "        log.observe(row.subject, quantity, float(core['_centre']),\n"
     "                    reader=READERS.GEOMETRY, frame=G.FRAME_PAGE,\n"
     "                    derived_from=(row.id,), promoted_from=row.id,\n"
     "                    source_reader=row.reader,\n"
     "                    **{k: v for k, v in core.items() if k != '_centre'})",
     "test_a_promoted_row_names_its_source_and_is_NOT_derived_from_it"),

    ("the_promotion_re_measures_every_earlier_page", POSITIONS,
     "        if page is not None and row.subject.page != page:\n            continue",
     "        if False:\n            continue",
     "test_an_earlier_pages_rows_are_not_re_measured"),

    # ── the missing ruler is a MEASUREMENT, filed once ─────────────────────
    ("the_refusal_is_filed_once_per_MARK_instead_of_once_per_cell", POSITIONS,
     "            if wanted:\n"
     "                log.abstain(sub, Q.CELL_POSITION_BASIS,",
     "            for _ in wanted:\n"
     "                log.abstain(sub, Q.CELL_POSITION_BASIS,",
     "test_no_grid_abstains_once_with_the_count"),

    ("a_gridless_cell_with_NO_marks_still_reports_a_fault", POSITIONS,
     "            if wanted:\n"
     "                log.abstain(sub, Q.CELL_POSITION_BASIS,",
     "            if True:\n"
     "                log.abstain(sub, Q.CELL_POSITION_BASIS,",
     "test_a_cell_with_no_marks_at_all_writes_nothing"),

    # ── the frames are NAMED, so a consumer cannot mix two units ───────────
    ("the_band_row_is_filed_in_the_cell_frame", POSITIONS,
     "                       reader=READERS.GEOMETRY, frame=G.FRAME_PAGE, "
     "**detail)",
     "                       reader=READERS.GEOMETRY, frame='cell/0', "
     "**detail)",
     "test_a_band_row_names_the_band_unit_and_is_in_page_pixels"),

    ("the_two_frames_share_one_unit_name", POSITIONS,
     'UNIT_BAND = "staff_spaces_below_bottom_line"',
     'UNIT_BAND = "staff_steps_from_top_line"',
     "test_a_band_row_names_the_band_unit_and_is_in_page_pixels"),

    # ── POSITIVE CONTROL, in the same class as the refusal arms ────────────
    #
    # ⚠️ Nearly every arm above makes the module say LESS or say it WRONGLY.
    # A battery of those can pass against a module that writes nothing at all,
    # so one arm has to break the ACCEPTING path while leaving the refusals
    # intact: this one emits no step row and keeps every abstention.
    ("it_never_writes_a_step_position_at_all", POSITIONS,
     "            _observe_step(log, g, quantity, frame, core, "
     "discriminate(core),\n"
     "                          detector_class=d.smufl_name)",
     "            continue",
     "test_the_two_differ_ONLY_in_position"),
]


def _hash(p: Path) -> str:
    return hashlib.md5(p.read_bytes()).hexdigest()


def run(target: str) -> bool:
    """True when the named test PASSES."""
    out = subprocess.run(
        [sys.executable, "-m", "pytest", *TESTS, "-k", target.split("::")[-1],
         "-q", "--no-header", "-p", "no:cacheprovider"],
        cwd=ROOT, capture_output=True, text=True)
    return out.returncode == 0 and " passed" in out.stdout


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true",
                    help="run over a dirty tools/ tree (see the docstring)")
    args = ap.parse_args()

    if SENTINEL.exists():
        print("⚠️⚠️ AN EARLIER BATTERY DID NOT FINISH. Its mutation may still "
              "be on disk and `git status` cannot tell it from a real edit.",
              file=sys.stderr)
        print(SENTINEL.read_text(), file=sys.stderr)
        return 2

    dirty = subprocess.run(["git", "status", "--porcelain", "--", "tools/"],
                           cwd=ROOT, capture_output=True, text=True).stdout
    if dirty.strip() and not args.force:
        print("⚠️ tools/ is dirty. A battery restores from its OWN snapshot, "
              "but an interrupted one leaves you unable to tell its mutation "
              "from your edit. Commit first, or pass --force.", file=sys.stderr)
        print(dirty, file=sys.stderr)
        return 2

    files = {POSITIONS}
    before = {f: _hash(f) for f in files}
    snap = Path(tempfile.mkdtemp(prefix="positions-mutate-"))
    for f in files:
        shutil.copy2(f, snap / f.name)
    SENTINEL.write_text(json.dumps(
        {str(f.relative_to(ROOT)): h for f, h in before.items()}, indent=2))

    print("── BASELINE ──────────────────────────────────────────────────")
    base = subprocess.run(
        [sys.executable, "-m", "pytest", *TESTS, "-q", "--no-header",
         "-p", "no:cacheprovider"], cwd=ROOT, capture_output=True, text=True)
    base_ok = base.returncode == 0
    print(f"  unmutated tree: {'GREEN' if base_ok else '⚠️ RED'}  "
          f"{base.stdout.strip().splitlines()[-1] if base.stdout else ''}")
    if not base_ok:
        for f in files:
            shutil.copy2(snap / f.name, f)
        SENTINEL.unlink(missing_ok=True)
        shutil.rmtree(snap, ignore_errors=True)
        print("⚠️ the baseline is red; every arm below would be unreadable.",
              file=sys.stderr)
        return 2

    results = []
    try:
        for name, path, anchor, repl, target in ARMS:
            src = path.read_text()
            n = src.count(anchor)
            if n != 1:
                results.append((name, target, f"⚠️ BAD ANCHOR ({n} matches)"))
                continue
            path.write_text(src.replace(anchor, repl))
            passed = run(target)
            path.write_text(src)
            results.append((name, target, "survived ⚠️" if passed else "red"))
    finally:
        for f in files:
            shutil.copy2(snap / f.name, f)
        shutil.rmtree(snap, ignore_errors=True)

    after = {f: _hash(f) for f in files}
    restored = after == before
    SENTINEL.unlink(missing_ok=True)

    print("\n── ARMS ──────────────────────────────────────────────────────")
    for name, target, verdict in results:
        print(f"  {verdict:<24} {name}")
        print(f"  {'':24} -> {target}")

    bad = [r for r in results if r[2] != "red"]
    print(f"\n{len(results) - len(bad)} of {len(results)} arms RED; "
          f"restore {'VERIFIED' if restored else '⚠️ FAILED'}")
    if bad:
        print("⚠️ arms that did not go red:", file=sys.stderr)
        for name, target, verdict in bad:
            print(f"   {verdict}  {name} -> {target}", file=sys.stderr)
    return 0 if (not bad and restored) else 1


if __name__ == "__main__":
    sys.exit(main())
