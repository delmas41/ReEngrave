"""RED-FIRST, mechanically: break the wiring and check the tests notice.

⚠️ THE DEFECT THIS IS ADDRESSED TO IS A TEST THAT CANNOT FAIL.
`hairpin_detection` shipped with nineteen green tests and no call site — every
one of them passed while the module was unreachable, because none of them asked
about `transcribe`. A wiring test written after that fact is worth nothing until
somebody has watched it go red for the right reason.

Each mutation below is a plausible way the wiring breaks. It is applied to a
COPY of the tree, the suite is run, and the mutation is REQUIRED to redden the
tests named for it — and only a run where every mutation reddens exits 0.

    python3 benchmarks/omr-hairpin-cv-2026-09/probe/mutate_wiring.py
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
TRANSCRIBE = "tools/omr/transcribe.py"
MODULE = "tools/omr/hairpin_detection.py"
TESTS = "tools/omr/tests/test_hairpin_detection.py"

CALL_SITE = """        if _cv_hairpins_enabled():
            n_cv_hairpins = read_hairpins_for_page(page_dict, page.binary)
            if n_cv_hairpins:
                page_dict["n_cv_hairpins_added"] = n_cv_hairpins
                out["n_cv_hairpins_added"] = (
                    out.get("n_cv_hairpins_added", 0) + n_cv_hairpins)
                out["n_detections_total"] += n_cv_hairpins
"""

#: (name, file, edits, tests that MUST go red). `edits` is one (find,
#: replace) pair or a list of them — a mutation that MOVES code needs two.
MUTATIONS = [
    ("call site deleted — the module is unreachable again",
     TRANSCRIBE, (CALL_SITE, ""),
     ["TestWiring::test_transcribe_calls_the_reader",
      "TestWiring::test_the_call_is_gated_on_the_flag",
      "TestWiring::test_the_reader_runs_before_the_cross_staff_arbitration",
      "TestWiring::test_the_call_site_hands_over_the_binary_not_a_mask"]),

    ("gate removed — the flag stops meaning anything",
     TRANSCRIBE, ("        if _cv_hairpins_enabled():\n            n_cv_hairpins",
                  "        if True:\n            n_cv_hairpins"),
     ["TestWiring::test_the_call_is_gated_on_the_flag"]),

    ("call MOVED after the cross-staff arbitration — still called, wrong order",
     TRANSCRIBE, [(CALL_SITE, ""),
                  ('        out["n_detections_total"] -= n_deduped\n',
                   '        out["n_detections_total"] -= n_deduped\n' + CALL_SITE)],
     ["TestWiring::test_the_reader_runs_before_the_cross_staff_arbitration"]),

    ("call site inverts the page itself — the polarity convention drifts",
     TRANSCRIBE, ("read_hairpins_for_page(page_dict, page.binary)",
                  "read_hairpins_for_page(page_dict, 255 - page.binary)"),
     ["TestWiring::test_the_call_site_hands_over_the_binary_not_a_mask"]),

    ("flag defaults ON",
     TRANSCRIBE, ('"OMR_CV_HAIRPINS", "0"', '"OMR_CV_HAIRPINS", "1"'),
     ["TestWiring::test_the_flag_is_off_by_default"]),

    ("polarity guard removed — the wrong image reports a clean zero",
     MODULE, ("    if ink_fraction > _INK_FRACTION_CEILING:",
              "    if False:"),
     ["test_the_wrong_polarity_raises_instead_of_reporting_zero"]),

    ("blanking removed — a detection standing on the hairpin hides it",
     MODULE,
     ("    blanked = blank_point_detections(page_ink, _detection_boxes(page), sp_med)\n"
      "    return attach_to_page(page, page_ink, blanked)",
      "    return attach_to_page(page, page_ink, None)"),
     ["test_the_rung_blanks_the_point_detections_before_searching"]),
]


def _failed(root: Path) -> set[str]:
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", TESTS, "-q", "--no-header", "-p",
         "no:cacheprovider"],
        cwd=root, capture_output=True, text=True)
    out = proc.stdout + proc.stderr
    return {line.split("::", 1)[1].strip()
            for line in out.splitlines() if line.startswith("FAILED ")}


def main() -> int:
    bad = 0
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "tree"
        shutil.copytree(REPO / "tools", root / "tools")
        (root / "benchmarks").mkdir()

        base = _failed(root)
        if base:
            sys.stderr.write(f"FATAL: unmutated tree already RED: {base}\n")
            return 2
        print(f"baseline: {TESTS} is green\n")

        for name, rel, edits, expect in MUTATIONS:
            path = root / rel
            original = path.read_text()
            text = original
            for find, repl in ([edits] if isinstance(edits, tuple) else edits):
                if text.count(find) != 1:
                    sys.stderr.write(
                        f"FATAL: mutation {name!r} matched {text.count(find)} "
                        f"sites in {rel} (expected exactly 1) — the mutation "
                        "is stale and proves nothing.\n")
                    return 2
                text = text.replace(find, repl, 1)
            path.write_text(text)
            red = _failed(root)
            path.write_text(original)

            missed = [t for t in expect if t not in red]
            print(f"{'OK ' if not missed else 'BAD'}  {name}")
            print(f"      red: {sorted(red) or 'NOTHING — the mutation is invisible'}")
            if missed:
                bad += 1
                print(f"      MISSED: {missed}")
        print()
    if bad:
        sys.stderr.write(f"{bad} mutation(s) went unnoticed.\n")
        return 1
    print("every mutation reddens the tests named for it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
