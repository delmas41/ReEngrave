"""Does the SHIPPED branch do what it claims? -- a battery over `tools/`.

⚠️ THE JUDGE IS THE UNIT TESTS PLUS THE ARM'S OWN NUMBERS, and it contains no
elapsed time: two batteries in this repo were voided on 2026-09-20 by comparing
a pytest summary line ending `" in 0.57s"`, so every arm scored RED for free.
Here the judge is `(returncode, the failing test ids)`.

⚠️ THE TREE IS RESTORED FROM A BYTE SNAPSHOT TAKEN BEFORE THE FIRST ARM, NOT
FROM GIT, the restore is VERIFIED BY HASH, an in-flight sentinel refuses a
second run after a kill, and `PYTHONDONTWRITEBYTECODE=1` is set in every arm --
a `.pyc` written under one mutation satisfies Python's (mtime, size) check
under the next when the restore preserved mtime, which took one battery here
from 10 RED / 2 survived to 12 RED / 0.
"""
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parents[1]
IDENTITY = ROOT / "tools/omr/staged/adjudicators/identity.py"
INFERENCES = ROOT / "tools/omr/staged/inferences.py"
TARGETS = [IDENTITY, INFERENCES]
SENTINEL = HERE / ".mutate-rule-in-flight"
TESTS = ["tools/omr/tests/test_staged_slot_constraints.py",
         "tools/omr/tests/test_staged_unnamed_block.py",
         "tools/omr/tests/test_staged_slot_by_name.py"]

#: ⚠️ ARMS THAT CANNOT GO RED, NAMED RATHER THAN QUIETLY TOLERATED. An arm
#: that can never fail trains the next reader to skim the list, so each says
#: which fact makes it dormant and what would wake it.
UNEXERCISED = {
    "the narrowing is renamed, so INFER stops recognising it":
        "the SHRINK branch is unreachable at `FAMILY_BLOCK_MAX_DEFICIT = 1`: "
        "a block one slot short narrows every member to exactly two "
        "candidates, so the filter can only FORCE (one survives) or stand "
        "aside (both do). Raising the cap wakes it, and "
        "test_the_SHRINK_branch_is_unreachable_at_the_current_deficit_cap is "
        "what will say so.",
    "the run is read off members[0] again":
        "every member decided by the filter was NARROWED first, so it still "
        "carries the block's `run`. A member decided on the `placed is None` "
        "path would not -- and that path cannot co-occur with a block, since "
        "it is the branch for a staff the block did not reach.",
}

ARMS = [
    ("the clef is COLLECTED for named staves too (the population site)",
     IDENTITY,
     "        if names[sub.staff] is None:\n            clefs[sub.staff] = _clef_read_at(ev, sub)",
     "        clefs[sub.staff] = _clef_read_at(ev, sub)"),
    ("a channel EMPTIES the solution set instead of being dropped",
     IDENTITY,
     "        if use_clef:\n            use_clef = False\n            dropped.append(\"clef\")\n            continue",
     "        if False:\n            pass"),
    ("the drop is silent -- it stops NAMING the channel it discarded",
     IDENTITY, '            dropped.append("clef")', '            pass'),
    ("the map need not be strictly increasing",
     IDENTITY, "            walk(ordinal + 1, slot + 1, acc)",
     "            walk(ordinal + 1, slot, acc)"),
    ("an unreadable reference slot EXCLUDES instead of widening",
     IDENTITY, "                     if nm is None or nm == mine})",
     "                     if nm == mine})"),
    ("no instrument alternates between clefs",
     IDENTITY, '    "Cello": ("bass", "tenor"),', ""),
    ("the family block is mapped without the equal-count guard",
     IDENTITY, "    if not a or not b or len(a) != len(b):",
     "    if not a or not b:"),
    ("the filter may INVENT a candidate the block never admitted",
     IDENTITY, "    kept = [c for c in placed.candidates if int(c.value) in surviving]",
     "    kept = [c for c in placed.candidates]"),
    ("disagreeing clef glyphs are a VOTE rather than no opinion",
     IDENTITY, "    return named.pop() if len(named) == 1 else None",
     "    return sorted(named)[0] if named else None"),
    ("the narrowing is renamed, so INFER stops recognising it",
     IDENTITY, "    return Ruling.narrow(kept, placed.reason, used=placed.used,",
     "    return Ruling.narrow(kept, 'constraints_not_forced', used=placed.used,"),
    ("a FORCED member is a hole in the block again",
     INFERENCES,
     "        if v.outcome is Outcome.DECIDED:\n            if v.reason != \"forced_by_constraints\":\n                continue",
     "        if v.outcome is Outcome.DECIDED:\n            continue"),
    ("the run is read off members[0] again",
     INFERENCES,
     "        detail = next((m.detail for m in members\n                       if (m.detail or {}).get(\"run\")), None) or {}",
     "        detail = members[0].detail or {}"),
]


def digest(p):
    return hashlib.md5(p.read_bytes()).hexdigest()


def judge():
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    r = subprocess.run([sys.executable, "-m", "pytest", *TESTS, "-q",
                        "--no-header", "-p", "no:cacheprovider"],
                       cwd=ROOT, env=env, capture_output=True, text=True)
    failed = sorted(set(re.findall(r"^FAILED (\S+)", r.stdout, re.M)))
    errors = sorted(set(re.findall(r"^ERROR (\S+)", r.stdout, re.M)))
    return {"rc": r.returncode, "failed": failed, "errors": errors}


def main() -> int:
    if SENTINEL.is_file():
        print("REFUSING: a previous battery did not finish.")
        print(SENTINEL.read_text())
        return 2
    snap = {p: p.read_bytes() for p in TARGETS}
    SENTINEL.write_text(json.dumps({str(p): digest(p) for p in TARGETS}, indent=1))
    try:
        base = judge()
        print("POSITIVE CONTROL — the unmutated tree:", base)
        if base["rc"] != 0:
            print("FAILED: the tree is not green. Nothing below means anything.")
            return 2
        again = judge()
        if again != base:
            print("FAILED: two runs of the same tree disagree.")
            return 2
        print("  green, and stable across two runs.\n")
        red = survived = bad = 0
        for name, target, find, repl in ARMS:
            src = snap[target].decode()
            if src.count(find) != 1:
                print("BAD ANCHOR  %s  (%d matches in %s)\n"
                      % (name, src.count(find), target.name))
                bad += 1
                continue
            target.write_text(src.replace(find, repl))
            got = judge()
            for p, b in snap.items():
                p.write_bytes(b)
            if got["rc"] != 0:
                red += 1
                print("RED       %s\n          -> %s\n"
                      % (name, ", ".join(got["failed"] + got["errors"])[:150]))
            elif name in UNEXERCISED:
                print("UNEXERCISED  %s\n          -> dormant, and that is the "
                      "CODE: %s\n" % (name, UNEXERCISED[name]))
            else:
                survived += 1
                print("SURVIVED  %s\n          -> the suite is blind to it\n" % name)
        for p, b in snap.items():
            p.write_bytes(b)
        ok = all(digest(p) == hashlib.md5(snap[p]).hexdigest() for p in TARGETS)
        print("=" * 70)
        print("%d RED, %d survived, %d dormant-by-design, %d bad anchors.  "
              "restore verified: %s" % (red, survived, len(UNEXERCISED), bad, ok))
        return 0 if (survived == 0 and bad == 0 and ok) else 1
    finally:
        for p, b in snap.items():
            p.write_bytes(b)
        SENTINEL.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
