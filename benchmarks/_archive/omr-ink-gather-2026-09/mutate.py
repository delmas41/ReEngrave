"""MUTATION BATTERY — `gather_ink` and the guarantees it makes.

⚠️⚠️ ONE RED ARM IS NOT A BATTERY. Every arm runs and is reported, and the
POSITIVE CONTROL IN THE SAME CLASS is here for the reason CLAUDE.md records: a
battery made only of refusal arms can pass by refusing everything.

⚠️⚠️ IT REFUSES A DIRTY TREE AND IT LEAVES AN IN-FLIGHT SENTINEL, both paid-for
disciplines here: a battery killed mid-arm left its mutation on disk with the
snapshot dying in the dead process, and one run over an uncommitted change
restored from the index and the change under test vanished. The restore is
VERIFIED by hash, never assumed.

    python3 benchmarks/omr-ink-gather-2026-09/mutate.py
    python3 benchmarks/omr-ink-gather-2026-09/mutate.py --force   # dirty tree
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
GATHER = ROOT / "tools/omr/staged/gather.py"
SENTINEL = Path(__file__).resolve().parent / ".mutation-in-flight.json"

TESTS = ["tools/omr/tests/test_staged_ink.py"]

#: (name, file, anchor, replacement, the test that MUST go red)
ARMS = [
    # ── the flag: a GATHER change that must default to nothing ─────────────
    ("the_flag_defaults_ON", GATHER,
     '    return os.environ.get(INK_ENV, "0").strip().lower() \\\n'
     '        in ("1", "true", "yes", "on")',
     '    return os.environ.get(INK_ENV, "1").strip().lower() \\\n'
     '        not in ("0", "", "false", "no", "off")',
     "test_the_default_writes_no_row_at_all"),

    ("the_flag_is_a_deny_list_so_a_typo_turns_it_ON", GATHER,
     '    return os.environ.get(INK_ENV, "0").strip().lower() \\\n'
     '        in ("1", "true", "yes", "on")',
     '    return os.environ.get(INK_ENV, "0").strip().lower() \\\n'
     '        not in ("0", "false", "no", "off")',
     "test_an_allow_list_leaves_a_typo_off"),

    ("the_flag_is_not_consulted_at_all", GATHER,
     "    if not _ink_enabled():\n        return",
     "    if False:\n        return",
     "test_the_default_writes_no_row_at_all"),

    # ── the image: the erased variant, not the raw cell ────────────────────
    ("it_reads_the_cell_with_its_staff_lines_still_in", GATHER,
     '    img = getattr(cell, "image_no_staff", None)\n'
     '    if img is None or getattr(img, "ndim", 0) != 2:\n'
     '        return None',
     '    img = getattr(cell, "image_no_staff", None)\n'
     '    if img is None:\n'
     '        img = getattr(cell, "image", None)\n'
     '    if img is None or getattr(img, "ndim", 0) != 2:\n'
     '        return None',
     "test_a_cell_with_no_erased_image_refuses_by_name"),

    # ── nothing is filtered ────────────────────────────────────────────────
    ("a_size_gate_is_applied_at_the_gather_site", GATHER,
     "    return [tuple(int(stats[i, k]) for k in range(5)) for i in range(1, n)]",
     "    out = [tuple(int(stats[i, k]) for k in range(5)) for i in range(1, n)]\n"
     "    return [c for c in out if c[4] >= 4]",
     "test_a_single_pixel_gets_a_row"),

    ("a_shape_gate_drops_the_long_flat_residue", GATHER,
     "    return [tuple(int(stats[i, k]) for k in range(5)) for i in range(1, n)]",
     "    out = [tuple(int(stats[i, k]) for k in range(5)) for i in range(1, n)]\n"
     "    return [c for c in out if c[3] * 8 >= c[2]]",
     "test_a_staff_line_remnant_gets_a_row_and_is_not_marked_bad"),

    # ── the span rule: without it the layer is vacuous ─────────────────────
    ("a_span_detection_explains_the_ink_it_encloses", GATHER,
     "        if d.width_canonical > cut:\n            continue",
     "        if False:\n            continue",
     "test_a_SPAN_detection_explains_nothing"),

    ("the_span_cut_is_restated_instead_of_imported", GATHER,
     "    cut = DEFAULT_BAND_CONFIG.max_blank_width_spaces * spacing",
     "    cut = 4.0 * spacing",
     "test_the_span_cut_is_the_direction_readers_own_constant"),

    # ── coverage is a UNION, and it is only coverage ────────────────────────
    ("overlapping_detections_are_summed_not_unioned", GATHER,
     "        mask[int(iy0) - y:int(iy1) - y, int(ix0) - x:int(ix1) - x] = True\n"
     "        who.append(name)\n"
     "    return float(mask.sum()) / float(w * h), tuple(sorted(set(who)))",
     "        mask[int(iy0) - y:int(iy1) - y, int(ix0) - x:int(ix1) - x] = True\n"
     "        who.append(name)\n"
     "        total = locals().get('total', 0) + (ix1-ix0)*(iy1-iy0)\n"
     "    return float(locals().get('total', 0)) / float(w * h), "
     "tuple(sorted(set(who)))",
     "test_two_overlapping_detections_do_not_over_count"),

    # ── the frames ─────────────────────────────────────────────────────────
    ("the_page_box_is_DEFAULTED_to_the_cell_frame", GATHER,
     '                optional["frame_note"] = (\n'
     '                    "no page box: cell has no bbox_page_px/upscale_factor")',
     '                optional.update(bbox_page_px=[x, y, x + w, y + h],\n'
     '                                x_center_page=x + w / 2.0,\n'
     '                                y_center_page=y + h / 2.0)',
     "test_a_cell_with_no_page_frame_DECLINES_it"),

    ("the_unit_is_the_nominal_staff_space_not_the_cells_own", GATHER,
     "        spacing = grid[1] * 2.0 if grid else None",
     "        spacing = 100.0",
     "test_the_unit_is_the_CELLS_own_staff_space"),

    ("the_canonical_box_is_dropped", GATHER,
     "                ink_bbox_canonical=[x, y, x + w, y + h],",
     "                ink_bbox_canonical=[0, 0, 0, 0],",
     "test_the_box_is_reported_in_BOTH_frames"),

    # ── the abstentions are measurements ────────────────────────────────────
    ("an_empty_cell_says_nothing_at_all", GATHER,
     "            log.abstain(sub, Q.INK, reader=READERS.CV_INK, frame=frame,\n"
     "                        reason=ABSTAIN.NO_INK)\n"
     "            continue",
     "            continue",
     "test_a_blank_cell_abstains_rather_than_saying_nothing"),

    ("a_missing_erased_image_falls_through_silently", GATHER,
     "            log.abstain(sub, Q.INK, reader=READERS.CV_INK, frame=frame,\n"
     "                        reason=ABSTAIN.NO_MASK,\n"
     '                        note="cell carries no image_no_staff")\n'
     "            continue",
     "            continue",
     "test_a_cell_with_no_erased_image_refuses_by_name"),

    # ── the key space ───────────────────────────────────────────────────────
    ("ink_indices_collide_with_the_detectors_own", GATHER,
     "_INK_GLYPH_BASE = 200_000",
     "_INK_GLYPH_BASE = 0",
     "test_ink_indices_sit_past_the_detector_and_the_cv_rung"),

    # ── the merge is REPORTED ───────────────────────────────────────────────
    ("the_merge_warning_is_not_written", GATHER,
     "                ink_n_components=len(comps),",
     "                ink_n_components=1,",
     "test_a_bridge_makes_two_marks_one_row_and_the_row_admits_it"),

    ("share_of_cell_is_computed_against_this_component", GATHER,
     "                ink_share_of_cell=round(area / total_ink, 4),",
     "                ink_share_of_cell=1.0,",
     "test_share_of_cell_ink_is_per_row_and_sums_to_one"),

    # ── the ordering edge ───────────────────────────────────────────────────
    ("it_runs_before_the_detections_exist", GATHER,
     "        gather_ink(log, cells, local, detections, progress=progress)",
     "",
     "test_gather_calls_it_after_detection"),

    # ── POSITIVE CONTROL, in the same class as the refusal arms ────────────
    #
    # ⚠️ Every arm above makes the reader do LESS or say LESS. A battery of
    # those passes by writing nothing at all, so one arm has to break the
    # ACCEPTING path: here, by emitting no observation while leaving every
    # refusal intact.
    ("it_never_writes_an_observation", GATHER,
     "            log.observe(\n"
     "                g, Q.INK, \"ink\", reader=READERS.CV_INK, frame=frame,",
     "            continue\n"
     "            log.observe(\n"
     "                g, Q.INK, \"ink\", reader=READERS.CV_INK, frame=frame,",
     "test_the_positive_control_writes_rows"),
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

    files = {GATHER}
    before = {f: _hash(f) for f in files}
    snap = Path(tempfile.mkdtemp(prefix="ink-mutate-"))
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
