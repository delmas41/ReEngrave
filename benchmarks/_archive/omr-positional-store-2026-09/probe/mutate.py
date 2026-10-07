#!/usr/bin/env python3
"""Mutation battery for the positional store.

⚠️⚠️ **A MUTATION BATTERY MUST LEAVE THE TREE AS IT FOUND IT — WHICH IS NOT
THE SAME AS LEAVING IT AS GIT HAS IT, AND AN INTERRUPTED BATTERY OBEYS
NEITHER.**  This repo has paid for both halves: one battery restored from HEAD
and annihilated the change it had just certified, and another was killed
mid-arm with its snapshot in memory, leaving a mutation on disk that looked
exactly like the legitimate edit beside it.  So:

* a BYTE snapshot is taken before the first arm and the restore is VERIFIED;
* an IN-FLIGHT SENTINEL is written before the first arm and deleted on a clean
  exit -- a run that finds one refuses to start and names each file at risk
  with the hash it should have;
* a dirty tree is refused without ``--force``.

⚠️ **ONE RED ARM IS NOT A BATTERY**, and a battery of REFUSAL tests can pass by
refusing everything -- so a POSITIVE CONTROL in the same class runs first:
a mutation that makes everything refuse must fail a test that asserts
something is ACCEPTED.
"""
from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
STORE = ROOT / "tools" / "omr" / "positional_store.py"
GATHER = ROOT / "tools" / "omr" / "staged" / "gather.py"
TESTS = "tools/omr/tests/test_positional_store.py"
SENTINEL = Path(__file__).resolve().parent / ".mutation-in-flight"

# (name, file, find, replace, why this must be caught)
ARMS = [
    ("membership flattened to the first name", STORE,
     "for name in (names or {UNKNOWN}):",
     "for name in (sorted(names)[:1] or [UNKNOWN]):",
     "a dot may belong to MANY things; keeping one is the whole objection"),
    ("an entry with no membership is dropped", STORE,
     "for name in (names or {UNKNOWN}):",
     "for name in names:",
     "unclassified ink is the population this layer exists for"),
    ("the tier guard is removed", STORE,
     "if tier is None and require_tier:",
     "if False:",
     "pooling provenance silently is how a store launders its own output"),
    ("an unknown tier is accepted", STORE,
     "if e.tier not in TIERS:",
     "if False:",
     "the tier is not optional"),
    ("position falls back to page pixels", STORE,
     "                pos = (float(yc) - ls[0]) / (space / 2.0)",
     "                pos = float(yc)",
     "a page-pixel key composes with nothing across documents"),
    ("a spanless staff gets a fabricated position", STORE,
     "if ls and len(ls) >= 2 and (ls[-1] - ls[0]) > 0:",
     "if ls and len(ls) >= 1:",
     "a fabricated number in the key field is worse than no entry"),
    ("unpositioned entries are dropped instead of counted", STORE,
     "            if e.staff_position is None:\n                self.unpositioned += 1\n                continue",
     "            if e.staff_position is None:\n                continue",
     "a store that silently drops what it cannot key overstates its reach"),
    ("the query stops merging the unconstrained axis", STORE,
     "                if hb is not None and h is not None and h != hb:",
     "                if hb is not None and h != hb:",
     "one name came back as nine rows with every share nine times too small"),
    ("shape stops being measured in staff spaces", STORE,
     "                w = round((bb[2] - bb[0]) / space, 3)",
     "                w = round(bb[2] - bb[0], 3)",
     "a pixel shape pools with nothing, same fault as a pixel position"),
    ("the round-trip drops an absent position", STORE,
     '        kw.setdefault("staff_position", None)',
     "        pass",
     "an UNPOSITIONED entry must survive a write/read cycle"),
    ("the identity flag becomes a deny-list", GATHER,
     '    return os.environ.get(DOCUMENT_IDENTITY_ENV, "0").strip().lower() \\\n        in ("1", "true", "yes", "on")',
     '    return os.environ.get(DOCUMENT_IDENTITY_ENV, "0").strip().lower() \\\n        not in ("0", "", "false", "no", "off")',
     "a default-OFF flag as a deny-list is switched ON by a typo"),
    ("flag-off writes an abstention anyway", GATHER,
     "    if not _document_identity_enabled():\n        # ⚠️ SILENT",
     "    if False:\n        # ⚠️ SILENT",
     "flag-off must be byte-identical to a tree without the rung"),
    ("an unknown pdf defaults instead of abstaining", GATHER,
     "    if not facts:",
     "    if False:",
     "a fallback must never convert 'cannot tell' into a definite answer"),
    ("the two abstentions fold into one", GATHER,
     "reason=ABSTAIN.NOT_IN_CATALOG,",
     "reason=ABSTAIN.OUT_OF_SCOPE,",
     "'we declined to look' and 'not held' have different repairs"),
]

#: ⚠️ THE POSITIVE CONTROL, in the same class as the arms: a mutation that
#: makes the query refuse EVERYTHING.  Without it, a battery of refusal tests
#: passes by refusing everything and reports itself green.
POSITIVE_CONTROL = (
    "everything_refuses", STORE,
    "            if merged is None:\n                continue",
    "            if True:\n                continue",
    "a store that answers nothing must fail a test that asserts an answer")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def run_tests() -> bool:
    r = subprocess.run([sys.executable, "-m", "pytest", TESTS, "-q"],
                       cwd=ROOT, capture_output=True, text=True)
    return r.returncode == 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true",
                    help="run despite a dirty tree")
    args = ap.parse_args()

    if SENTINEL.exists():
        print("REFUSING: a previous battery did not finish. Files at risk:")
        print(SENTINEL.read_text())
        print("Restore them from git or from the hashes above, then delete\n"
              "  %s" % SENTINEL)
        return 2

    dirty = subprocess.run(["git", "status", "--porcelain", "--",
                            str(STORE), str(GATHER)],
                           cwd=ROOT, capture_output=True, text=True).stdout
    if dirty.strip() and not args.force:
        print("REFUSING: the files this battery mutates are dirty.\n%s"
              "Commit a checkpoint first, or pass --force." % dirty)
        return 2

    files = {STORE, GATHER}
    snapshot = {p: p.read_bytes() for p in files}
    hashes = {p: sha(p) for p in files}
    SENTINEL.write_text("".join("%s  %s\n" % (h, p) for p, h in hashes.items()))

    def restore() -> None:
        for p, b in snapshot.items():
            p.write_bytes(b)
        for p, h in hashes.items():
            assert sha(p) == h, "RESTORE FAILED for %s" % p

    rc = 0
    try:
        print("BASELINE: the suite must be GREEN before any arm means anything")
        if not run_tests():
            print("  BASELINE IS RED. The battery says nothing. Stopping.")
            return 2
        print("  green\n")

        name, path, find, repl, why = POSITIVE_CONTROL
        print("POSITIVE CONTROL (must go RED): %s" % name)
        src = path.read_text()
        if find not in src:
            print("  BAD ANCHOR -- the control does not apply cleanly.")
            rc = 2
        else:
            path.write_text(src.replace(find, repl, 1))
            ok = run_tests()
            restore()
            print("  %s   (%s)" % ("RED (good)" if not ok
                                   else "GREEN -- THE BATTERY IS BLIND", why))
            if ok:
                rc = 1
        print()

        red = 0
        for i, (name, path, find, repl, why) in enumerate(ARMS, 1):
            src = path.read_text()
            n = src.count(find)
            if n == 0:
                print("%2d. BAD ANCHOR: %s" % (i, name))
                rc = 2
                continue
            if n > 1:
                # ⚠️ An anchor occurring twice has bitten this repo three
                # times -- the arm mutates a DIFFERENT function and its
                # survival is reported as a test gap.
                print("%2d. AMBIGUOUS ANCHOR (%d matches): %s" % (i, n, name))
                rc = 2
                continue
            path.write_text(src.replace(find, repl, 1))
            ok = run_tests()
            restore()
            if ok:
                print("%2d. SURVIVED: %s\n      -> %s" % (i, name, why))
                rc = max(rc, 1)
            else:
                red += 1
                print("%2d. red      %s" % (i, name))
        print("\n%d of %d arms red" % (red, len(ARMS)))
    finally:
        restore()
        SENTINEL.unlink(missing_ok=True)
        print("tree restored and verified; sentinel cleared")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
