"""The mutation battery for the margin-label record fix (scope §6, §8 step 1).

Every arm must go RED, and the POSITIVE CONTROL must be GREEN on the
unmutated tree -- a battery that only breaks things passes by breaking
everything, and one red arm is not a battery.

    python3 benchmarks/omr-surya-staged-cost-2026-09/mutate.py
    python3 benchmarks/omr-surya-staged-cost-2026-09/mutate.py --list

⚠️⚠️ IT `git checkout`s THE FILES IT MUTATES, WHICH DESTROYS UNCOMMITTED WORK
-- INCLUDING ITS OWN SESSION'S. CLAUDE.md records this twice: as a collision
with a SIBLING session, and (2026-09-15) as self-destruction. It refuses to
start on a dirty tree and there is no `--force`.

⚠️ An ANCHOR occurring more than once is an ERROR, never a silent mutation of
the first match. Two batteries in this repo have mutated a different function
than the one they named.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GATHER = ROOT / "tools/omr/staged/gather.py"
CONTEXTUAL = ROOT / "tools/omr/contextual.py"
PIPELINE = ROOT / "tools/omr/staged/pipeline.py"

TESTS = ["tools/omr/tests/test_staged_margin_label_rungs.py"]

#: (name, file, anchor, replacement, why)
ARMS = [
    # ── the four states ──────────────────────────────────────────────────
    ("absent-surya-reads-as-installed", GATHER,
     '        (available if ok else unavailable).append("surya")',
     '        available.append("surya")',
     "a rung that is not installed must not be reported as one that ran"),
    ("absent-tesseract-reads-as-installed", GATHER,
     '        (available if ok else unavailable).append("tesseract")',
     '        available.append("tesseract")',
     "the same, for the rung most likely to be present"),
    ("every-empty-staff-is-no-ink", GATHER,
     '    if rungs["unavailable"] or failures:\n'
     '        empty_reason = ABSTAIN.READER_UNAVAILABLE',
     '    if False:\n'
     '        empty_reason = ABSTAIN.READER_UNAVAILABLE',
     "THE ORIGINAL BUG. `cannot tell` collapsed into `this page prints "
     "no instrument name`"),
    ("a-rung-nobody-asked-is-a-decision", GATHER,
     '    elif not rungs["requested"]:\n'
     '        empty_reason = ABSTAIN.OUT_OF_SCOPE',
     '    elif False:\n'
     '        empty_reason = ABSTAIN.OUT_OF_SCOPE',
     "the staged DEFAULT: no OCR rung asked for is not evidence of "
     "silence"),
    ("a-failed-rung-does-not-poison-the-page", GATHER,
     '    if rungs["unavailable"] or failures:',
     '    if rungs["unavailable"]:',
     "a rung that was installed and threw is as blind as one that is "
     "absent"),
    ("a-crash-is-a-declared-stub", GATHER,
     '            log, cells, local, ABSTAIN.READER_UNAVAILABLE,',
     '            log, cells, local, ABSTAIN.NOT_IMPLEMENTED,',
     "`NOT_IMPLEMENTED` is the bucket `gather_coverage` reports as build "
     "progress; a defect filed there is invisible"),

    # ── the attribution ──────────────────────────────────────────────────
    ("every-label-is-the-text-layer", GATHER,
     '                    reader=_RUNG_READER.get(rung, READERS.TEXT_LAYER),',
     '                    reader=READERS.TEXT_LAYER,',
     "THE OTHER ORIGINAL BUG. Two rows from one reader are ONE signal, so "
     "a mis-named reader is a mis-counted witness"),
    ("tesseract-additions-uncredited", CONTEXTUAL,
     '                _credit_labels(sources, added, "tesseract")',
     '                pass',
     "the case a per-page COUNT structurally cannot express"),
    ("a-surya-win-does-not-erase-what-it-overruled", CONTEXTUAL,
     '                    _credit_labels(sources, read, "surya", replaces=True)',
     '                    _credit_labels(sources, read, "surya")',
     "Surya REPLACES the page; crediting without erasing names two "
     "producers for one staff"),

    # ── the swallowed exception ──────────────────────────────────────────
    ("surya-failure-leaves-no-trace", CONTEXTUAL,
     '                if failures is not None:\n'
     '                    failures.append({"rung": "surya",',
     '                if False:\n'
     '                    failures.append({"rung": "surya",',
     "the state the cascade swallows by design and the record must keep"),

    # ── the header, which is a control ───────────────────────────────────
    ("header-hides-the-direction-reader", PIPELINE,
     '''            f" | directions OMR_DIRECTION_TEXT={'1' if directions_on else '0'}"''',
     '''            f""''',
     "a header showing only the label flags licences `no --surya means no "
     "Surya`, which is false"),
    ("header-is-never-printed", PIPELINE,
     '        print(_rung_header(surya_fallback, ocr_fallback))',
     '        pass',
     "an arm cannot assert the rungs were up if the run never says"),
]


def run_tests() -> bool:
    p = subprocess.run([sys.executable, "-m", "pytest", *TESTS, "-x", "-q",
                        "-p", "no:randomly"],
                       cwd=ROOT, capture_output=True, text=True)
    return p.returncode == 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--only")
    args = ap.parse_args(argv)

    if args.list:
        for name, path, _a, _r, why in ARMS:
            print("%-44s %-16s %s" % (name, path.name, why))
        return 0

    dirty = subprocess.run(
        ["git", "status", "--porcelain", "--", *{str(p) for _n, p, *_ in ARMS}],
        cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    if dirty:
        print("REFUSING TO RUN -- a file this battery mutates is dirty, and "
              "`git checkout` would DISCARD it:")
        for ln in dirty.splitlines():
            print("   " + ln)
        print("Commit first. There is no --force.")
        return 2

    print("POSITIVE CONTROL (unmutated tree must be GREEN) ...", end=" ",
          flush=True)
    if not run_tests():
        print("RED  <-- the battery cannot say anything")
        return 2
    print("GREEN")

    bad = []
    for name, path, anchor, repl, why in ARMS:
        if args.only and args.only != name:
            continue
        text = path.read_text()
        n = text.count(anchor)
        if n != 1:
            print("%-44s ERROR anchor occurs %d times" % (name, n))
            bad.append(name)
            continue
        path.write_text(text.replace(anchor, repl))
        try:
            green = run_tests()
        finally:
            subprocess.run(["git", "checkout", "--", str(path)], cwd=ROOT,
                           check=True)
        print("%-44s %s   %s" % (name, "SURVIVED <--" if green else "red ",
                                 why))
        if green:
            bad.append(name)

    print()
    if bad:
        print("SURVIVORS / ERRORS: %s" % ", ".join(bad))
        return 1
    print("all %d arms red, positive control green."
          % len([a for a in ARMS if not args.only or a[0] == args.only]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
