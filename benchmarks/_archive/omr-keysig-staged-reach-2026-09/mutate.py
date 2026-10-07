"""Mutation battery over the key signature's marker-ink split.

⚠️ ONE RED ARM IS NOT A BATTERY, and a SURVIVOR is a real gap rather than a
pass. The baseline must be GREEN before any arm is read or every arm is red
for free.

⚠️ A MUTATION BATTERY MUST LEAVE THE TREE AS IT FOUND IT — WHICH IS NOT THE
SAME AS LEAVING IT AS GIT HAS IT, AND AN INTERRUPTED BATTERY OBEYS NEITHER.
A BYTE snapshot on disk, an in-flight SENTINEL written before the first arm,
a restore VERIFIED by md5, and a refusal to start on a dirty target.

⚠️ THE ARMS DO NOT RUN `check_arm.py`. A full re-adjudication of a shared
record costs many minutes; every arm here is a claim about the RULE, and the
arm's own control (the join is UNMOVED, and the detail is PRESENT) is what
guards the measurement.
"""
from __future__ import annotations

import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / "out"
SENTINEL = OUT / ".mutate-in-flight"

HEADER = ROOT / "tools/omr/staged/adjudicators/header.py"
ARM = HERE / "check_arm.py"
PROBE = HERE / "probe_records.py"
TARGETS = {"header": HEADER, "arm": ARM, "probe": PROBE}

SUITES = [
    "tools/omr/tests/test_keysig_marker_ink.py",
    "tools/omr/tests/test_keysig_second_reader.py",
    "tools/omr/tests/test_staged_wiring.py",
    "tools/omr/tests/test_staged_inventory.py",
    "tools/omr/tests/test_staged_reach.py",
]

#: (target, name, find, replace, what it must break)
ARMS = [
    # ── THE SPLIT ─────────────────────────────────────────────────────────
    ("header", "an unread page reports no_evidence again (the split is gone)",
     '        marks = ev.rows(Q.KEYSIG_MARKER)\n'
     '        if marks:\n'
     '            return Ruling.abstain("markers_without_a_run", **_marker_ink(ev))',
     '        marks = ()',
     "the ABSENT/DECLINED collapse restored: 7 of 17 and 9 of 20 staves "
     "carrying key-accidental ink go back to reading as 'no evidence'"),

    ("header", "EVERY abstention becomes markers_without_a_run",
     '        marks = ev.rows(Q.KEYSIG_MARKER)\n'
     '        if marks:',
     '        marks = ev.rows(Q.KEYSIG_MARKER)\n'
     '        if True:',
     "a rule that renames every abstention says nothing; the positive control "
     "is that a staff with NO ink still reads no_evidence"),

    # ── IT MAY NEVER BECOME A VALUE ───────────────────────────────────────
    ("header", "the markers DECIDE a key (the legacy count-the-markers rule)",
     '        marks = ev.rows(Q.KEYSIG_MARKER)\n'
     '        if marks:\n'
     '            return Ruling.abstain("markers_without_a_run", **_marker_ink(ev))',
     '        marks = ev.rows(Q.KEYSIG_MARKER)\n'
     '        if marks:\n'
     '            return Ruling(value=-len(marks), reason="fitted",\n'
     '                          used=(clef.id,), detail=_marker_ink(ev))',
     "THE rule this repair exists not to be: counting markers cost seven "
     "spurious key flips on the legacy path"),

    ("header", "the markers overturn a fitted reading",
     "    fits = ev.rows(Q.KEYSIG_CLEF_FIT)\n",
     "    if ev.rows(Q.KEYSIG_MARKER):\n"
     "        return Ruling(value=-len(ev.rows(Q.KEYSIG_MARKER)),\n"
     "                      reason='fitted', used=(clef.id,))\n"
     "    fits = ev.rows(Q.KEYSIG_CLEF_FIT)\n",
     "a settled fit must outrank marker ink; the locator cannot invent a "
     "glyph and the marker count agrees with it only ~half the time"),

    # ── ABSENT IS NOT DECLINED, ONE LEVEL DOWN ────────────────────────────
    ("header", "the no-ink branch stops recording WHICH silence it is",
     '        return {"keysig_marker_ink": 0,\n'
     '                "keysig_marker_state": str(ev.state(Q.KEYSIG_MARKER))}',
     '        return {"keysig_marker_ink": 0}',
     "'the detector produced no row' and 'it produced a row saying nothing' "
     "collapse into one, which is the fault this detail repairs"),

    ("header", "the detail drops its own not-a-reading warning",
     '            "keysig_marker_count_is_not_a_reading": True}',
     '            "_unused": True}',
     "a consumer meeting `keysig_marker_ink: 3` and reading it as three flats "
     "is the measured seven-flip rule"),

    ("header", "the marker classes are no longer recorded",
     '            "keysig_marker_classes": sorted({str(m.value) for m in marks}),',
     "",
     "sharps and flats are different evidence; a bare count cannot say which"),

    # ── THE DECLARATION ───────────────────────────────────────────────────
    ("header", "the new reason is not declared",
     '             "run_fits_no_slot_table", "no_run", "markers_without_a_run",\n'
     '             "no_evidence"),',
     '             "run_fits_no_slot_table", "no_run", "no_evidence"),',
     "a branch returning an UNDECLARED reason is the mirror of a declared "
     "reason with no branch"),

    # ── THE ARM'S OWN CONTROLS ────────────────────────────────────────────
    ("arm", "the arm stops asserting no DECIDED key moved",
     "        if g[\"outcome\"] != \"decided\" or g.get(\"value\") != w.get(\"value\") \\\n"
     "                or g[\"reason\"] != w[\"reason\"]:",
     "        if False:",
     "the one thing that must not move is a decided key; an arm that cannot "
     "see it move would pass a change that started counting markers"),

    ("arm", "the arm permits ANY abstention movement",
     "        if w[\"reason\"] in PERMITTED and g[\"reason\"] in PERMITTED:",
     "        if True:",
     "only no_evidence -> markers_without_a_run is legal; anything else is a "
     "different change wearing this one's name"),

    ("arm", "the arm drops its POSITIVE control (the split must happen)",
     "    if n_split == 0:",
     "    if False:",
     "'no decided key moved' is also exactly what a change that never ran "
     "looks like"),

    ("arm", "the arm stops checking the probe's restated constant",
     "    if tuple(probe.KEYSIG_CLASSES) != tuple(_KEYSIG_CLASSES):",
     "    if False:",
     "the probe deliberately does not import the tree, so a drift would make "
     "the two instruments measure different populations in silence"),

    # ── THE PROBE'S OWN CONTROLS ──────────────────────────────────────────
    ("probe", "the probe reports a clean result with no key verdicts",
     "    if not keys:",
     "    if False:",
     "REACH BEFORE ACCURACY: a probe that cannot speak must declare itself "
     "DEAD, not print a table of zeros"),

    ("probe", "the probe counts cell-0 detections as out of reach",
     "    later = sum(n for c, n in cells.items() if c != 0)",
     "    later = sum(cells.values())",
     "the whole Q2 finding is that the out-of-reach population is SMALL (21 "
     "and 2); counting cell 0 into it inflates it to 126 and 148"),
]


def md5b(b: bytes) -> str:
    return hashlib.md5(b).hexdigest()[:12]


def headline() -> tuple[int, str]:
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", *SUITES],
                       cwd=str(ROOT), env=env, capture_output=True, text=True)
    tail = [ln for ln in (r.stdout + r.stderr).splitlines()
            if "passed" in ln or "failed" in ln or "error" in ln.lower()]
    # ⚠️⚠️ THE DURATION IS STRIPPED, AND THE BATTERY WAS MEASURING NOTHING
    # WITHOUT THIS. pytest ends its summary with " in 0.57s", which differs
    # between two runs of an UNMUTATED tree -- so `out != b_out` was true for
    # every arm and all of them scored RED for free. Measured: two baseline
    # runs back to back gave "13 passed, 5 warnings in 0.57s" and
    # "... in 0.61s". A battery whose judge cannot say two identical trees are
    # identical is the "control that computes the wrong thing" family, and it
    # fails in the direction that looks like success.
    tail = [re.sub(r" in \d+\.\d+s$", "", ln) for ln in tail]
    return r.returncode, "\n".join(tail[-2:]) or "(no summary)"


def main() -> int:
    force = "--force" in sys.argv
    OUT.mkdir(parents=True, exist_ok=True)
    if SENTINEL.exists():
        print("REFUSED: an in-flight sentinel exists — a previous battery was "
              "interrupted and the tree may still carry a mutation.")
        print(SENTINEL.read_text())
        return 3
    rel = [str(p.relative_to(ROOT)) for p in TARGETS.values()]
    dirty = subprocess.run(["git", "status", "--porcelain", "--", *rel],
                           cwd=str(ROOT), capture_output=True,
                           text=True).stdout.strip()
    if dirty and not force:
        print(f"REFUSED: a target is dirty:\n{dirty}\nCommit, or --force.")
        return 3

    snap = {k: v.read_bytes() for k, v in TARGETS.items()}
    SENTINEL.write_text("\n".join(
        f"{k}={TARGETS[k]} md5={md5b(v)}" for k, v in snap.items()) + "\n")

    print("=" * 78)
    print("BASELINE (the positive control — every arm is free if this is not "
          "green)")
    print("=" * 78)
    b_rc, b_out = headline()
    print(f"  exit {b_rc}\n  " + b_out.replace("\n", "\n  "))
    if b_rc != 0:
        print("\n⚠️ BASELINE IS NOT GREEN. The battery measures nothing.")
        for k, v in snap.items():
            TARGETS[k].write_bytes(v)
        SENTINEL.unlink(missing_ok=True)
        return 4

    red, survived, bad = [], [], []
    for target, name, find, repl, why in ARMS:
        src = snap[target].decode("utf-8")
        if src.count(find) != 1:
            bad.append((target, name, f"{src.count(find)} occurrences"))
            print(f"\n{'-' * 78}\nARM [{target}]: {name}\n"
                  f"  ⚠️ BAD ANCHOR ({src.count(find)} occurrences) — "
                  f"REPORTED AS AN ERROR, not a pass")
            continue
        TARGETS[target].write_text(src.replace(find, repl), encoding="utf-8")
        rc, out = headline()
        TARGETS[target].write_bytes(snap[target])
        moved = (rc != b_rc) or (out != b_out)
        (red if moved else survived).append((target, name, why))
        print(f"\n{'-' * 78}\nARM [{target}]: {name}")
        print(f"  expected: {why}")
        print(f"  exit {rc}  -> {'RED' if moved else 'SURVIVED'}")
        if not moved:
            print("  ⚠️ SURVIVOR — a real gap, not a pass.")

    ok = True
    for k, v in snap.items():
        TARGETS[k].write_bytes(v)
        if md5b(TARGETS[k].read_bytes()) != md5b(v):
            print(f"\n⚠️⚠️ RESTORE FAILED for {k}")
            ok = False
    if ok:
        SENTINEL.unlink(missing_ok=True)

    print("\n" + "=" * 78)
    print(f"RED {len(red)}   SURVIVED {len(survived)}   BAD ANCHORS {len(bad)}")
    print(f"restore VERIFIED by md5: {ok}")
    for t, n, _ in survived:
        print(f"  SURVIVOR [{t}] {n}")
    for t, n, m in bad:
        print(f"  BAD ANCHOR [{t}] {n}: {m}")
    return 0 if (ok and not survived and not bad) else 1


if __name__ == "__main__":
    raise SystemExit(main())
