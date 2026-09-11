"""The mutation battery for the two repairs. One red arm is not a battery.

⚠️ AND A BATTERY OF REFUSAL TESTS CAN PASS BY REFUSING EVERYTHING, so the
arms come in pairs: one that makes the refusal never fire, and one that makes
it always fire. A test suite that only pins the first is satisfied by a rule
that fragments every document ever exported.

⚠️ AN ARM WHOSE ANCHOR TEXT IS GONE IS REPORTED AS AN ERROR, NOT A PASS. The
fermata battery silently mutated a DIFFERENT function because its anchor
occurred twice, and the wedge battery reported a survivor that was a moved
line. A battery that cannot find its anchor has measured nothing.

Run from the repo root. Restores every file unconditionally.
"""

from __future__ import annotations

import pathlib
import subprocess
import sys

IDENTITY = pathlib.Path("tools/omr/staged/adjudicators/identity.py")
PIPELINE = pathlib.Path("tools/omr/staged/pipeline.py")

TESTS = ["tools/omr/tests/test_staged_part_join.py",
         "tools/omr/tests/test_staged_identity_chain.py",
         "tools/omr/tests/test_staged_export.py"]

#: (file, anchor, replacement). Each must turn the suite RED.
MUTATIONS = {
    # ── the refusal ─────────────────────────────────────────────────────────
    "refusal never fires": (
        IDENTITY,
        "    if usable and _slots_are_ordinals(usable):",
        "    if False and _slots_are_ordinals(usable):"),
    "refusal always fires": (
        IDENTITY,
        "    if usable and _slots_are_ordinals(usable):",
        "    if usable:"),
    "contiguity relaxed to distinctness": (
        IDENTITY,
        "    return all(sorted(vals) == list(range(len(vals)))",
        "    return all(len(set(vals)) == len(vals)"),
    "slots pooled instead of grouped by system": (
        IDENTITY,
        '        key = (getattr(sub, "page", None), getattr(sub, "system", None))',
        "        key = 0  # every system in one bucket"),
    "an empty table reads as the ordinal": (
        IDENTITY,
        "    if not by_system:\n        return False",
        "    if not by_system:\n        return True"),
    # ⚠️ The refusal must not fire where the counts AGREE -- that branch
    # returns first, and this arm proves the ordering is load-bearing rather
    # than incidental.
    "the ordinal branch loses its early return": (
        IDENTITY,
        '        return Ruling(value={"join": "ordinal", "staves_per_system": sizes.pop()},\n'
        '                      reason="ordinal", used=tuple(v.id for v in counts))',
        '        pass'),

    # ── the forward ─────────────────────────────────────────────────────────
    # ⚠️ THE TWO FORWARDS DIFFER BY ONE SPACE OF INDENTATION AND THE FIRST
    # DRAFT OF THIS BATTERY MUTATED THE WRONG ONE. `run_staged` hands the path
    # to `run_staged_on`, which hands it to `gather` -- two hops, two places it
    # can be dropped, and only the pair of arms proves BOTH are load-bearing.
    # Anchored on the callee's name, which is the only text that tells them
    # apart.
    "run_staged_on does not forward pdf_path to gather": (
        PIPELINE,
        "    log = gather.gather(prepared, detector=detector,\n"
        "                        conf_threshold=conf_threshold, imgsz=imgsz,\n"
        "                        dossier=dossier, roster=roster, pdf_path=pdf_path,",
        "    log = gather.gather(prepared, detector=detector,\n"
        "                        conf_threshold=conf_threshold, imgsz=imgsz,\n"
        "                        dossier=dossier, roster=roster,"),
    "run_staged drops pdf_path on the way to run_staged_on": (
        PIPELINE,
        "    return run_staged_on(prepared, detector=detector,\n"
        "                         conf_threshold=conf_threshold, imgsz=imgsz,\n"
        "                         dossier=dossier, roster=roster, pdf_path=pdf_path,",
        "    return run_staged_on(prepared, detector=detector,\n"
        "                         conf_threshold=conf_threshold, imgsz=imgsz,\n"
        "                         dossier=dossier, roster=roster,"),
    "the surya rung is not forwarded": (
        PIPELINE,
        "                        surya_fallback=surya_fallback,\n"
        "                        ocr_fallback=ocr_fallback, progress=progress)",
        "                        progress=progress)"),
}

#: ⚠️ THE POSITIVE CONTROL, in the same class as the arms. A battery whose
#: runner is broken reports every arm red and reads as a pass.
CONTROL = (IDENTITY, "def _slots_are_ordinals(slots) -> bool:",
           "def _slots_are_ordinals(slots) -> bool:  # noqa")


def run() -> str:
    r = subprocess.run(["python3", "-m", "pytest", *TESTS, "-q"],
                       capture_output=True, text=True)
    lines = [l for l in r.stdout.strip().splitlines() if l.strip()]
    return lines[-1] if lines else "(no output)"


def main() -> int:
    originals = {p: p.read_text() for p in {IDENTITY, PIPELINE}}
    bad = []
    try:
        for name, (path, a, b) in MUTATIONS.items():
            orig = originals[path]
            if orig.count(a) != 1:
                bad.append("%s: anchor occurs %d times, cannot mutate safely"
                           % (name, orig.count(a)))
                print("%-46s -> BAD ANCHOR (%d matches)" % (name, orig.count(a)))
                continue
            path.write_text(orig.replace(a, b))
            line = run()
            print("%-46s -> %s" % (name, line))
            if "failed" not in line and "error" not in line:
                bad.append("%s: the suite stayed GREEN" % name)
            path.write_text(orig)

        path, a, b = CONTROL
        orig = originals[path]
        path.write_text(orig.replace(a, b))
        line = run()
        print("%-46s -> %s" % ("POSITIVE CONTROL (a no-op edit)", line))
        if "failed" in line or "error" in line:
            bad.append("POSITIVE CONTROL: a no-op edit turned the suite RED, "
                       "so the arms above prove nothing")
        path.write_text(orig)
    finally:
        for p, text in originals.items():
            p.write_text(text)

    print("%-46s -> %s" % ("restored", run()))
    for b in bad:
        print("SURVIVED / VACUOUS: " + b)
    print("\n%d arms, %d problems" % (len(MUTATIONS), len(bad)))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
