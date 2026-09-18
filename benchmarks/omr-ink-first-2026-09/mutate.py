"""Mutation battery for the ink-first probe.

Nothing under `tools/` is touched by this lane, so the only thing worth
mutating is the INSTRUMENT -- and an instrument that reports the same numbers
after its controls are broken is not an instrument.

Every arm must go RED: either the probe REFUSES (exit 2), or a headline number
moves. An arm that leaves both unchanged is a survivor and a real test gap.

⚠️ A MUTATION BATTERY MUST LEAVE THE TREE AS IT FOUND IT -- WHICH IS NOT THE
SAME AS LEAVING IT AS GIT HAS IT, AND AN INTERRUPTED BATTERY OBEYS NEITHER.
So: a BYTE snapshot on disk (not in memory, which dies with the process), an
in-flight SENTINEL written before the first arm and deleted on a clean exit,
a VERIFIED restore by md5, and a refusal to start on a dirty tree without
--force.

⚠️ PYTHONDONTWRITEBYTECODE=1 in every arm. A stale .pyc made two arms in a
sibling lane import UNMUTATED code and report NOT RED.
"""
from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TARGET = HERE / "probe_ink_first.py"
SNAP = HERE / "out" / ".mutate-snapshot.py"
SENTINEL = HERE / "out" / ".mutate-in-flight"

#: (name, find, replace, what it should break)
ARMS = [
    ("POSITIVE CONTROL: baseline is green",
     None, None, "must PASS -- if this is red the battery measures nothing"),

    ("ink box read as [x,y,w,h] instead of corners",
     'ink[cell].append({\n                "subject": sub, "box": bb,',
     'bb = [bb[0], bb[1], bb[0] + bb[2], bb[1] + bb[3]]\n'
     '            ink[cell].append({\n                "subject": sub, "box": bb,',
     "control B (ink corners vs its own width_spaces) must refuse"),

    ("glyph box read as corners instead of [x,y,w,h]",
     "glyph_box[sub] = (v[0], (x, y, x + w, y + h))",
     "glyph_box[sub] = (v[0], (x, y, w, h))",
     "control B2 (a notehead is ~1 space tall) must refuse"),

    ("manifest staff index used RAW (no per-system offset)",
     "st = s_page_wide - offset.get(sysi, 0)",
     "st = s_page_wide",
     "controls C and E must refuse -- the cells joined are the wrong cells"),

    ("hand boxes scaled by the RECORD's frame, not the manifest's",
     'W = float(e["cell_canonical_w"])',
     'W = float(e["cell_canonical_w"]) * 1.15',
     "control E must refuse -- a 15% frame error is exactly what the join "
     "is for"),

    ("top_y inverted with the WRONG sign",
     "tmp[cell].append(yc - pos * hs)",
     "tmp[cell].append(yc + pos * hs)",
     "control C's grid-top column must stop agreeing"),

    # ⚠️ THIS ARM REPLACES "remove the class-match check", WHICH SURVIVED AND
    # WAS AN EQUIVALENT MUTANT RATHER THAN A TEST GAP: all 22 print verdicts on
    # this page DO class-match, so admitting the un-matched ones admits nothing
    # and no number moves. The reachable version is the actual hazard -- join
    # ANOTHER PAGE's tiles, whose subjects collide by positional index.
    ("crop tiles taken from page 3 instead of this page",
     't or t["where"]["page"] != PAGE',
     't or t["where"]["page"] != 3',
     "control F must REFUSE most of them on the class match -- if it does "
     "not, the collision guard is not guarding"),

    ("a vertical run is anything taller than it is wide",
     "RUN_MIN_ASPECT = 2.0",
     "RUN_MIN_ASPECT = 1.0",
     "the run population must change"),

    ("the structural split is removed -- beam/stem ink counts as a SYMBOL",
     "STRUCTURAL = (\"stem\", \"beam\", \"staff\", \"ledgerLine\", \"brace\", "
     "\"barline\")",
     "STRUCTURAL = ()",
     "the partition must move -- this is the split that makes it mean "
     "anything, and without it structural ink reads as invention and as "
     "missed music"),
]

#: Arms that pass a FLAG rather than mutating a line. The cost counter reads
#: ZERO on this page, so a mutation that sets it to zero is an equivalent
#: mutant, not a test -- the only way to show the counter works is to make the
#: world it measures and watch it fire.
FLAG_ARMS = [
    ("POSITIVE CONTROL for the cost counter: drop every detector notehead",
     ["--drop-det-heads"],
     "the VETO COST must RISE above zero -- otherwise the measured zero is "
     "the instrument and not the page"),
]


def md5(p: Path) -> str:
    return hashlib.md5(p.read_bytes()).hexdigest()


def run(extra=()) -> tuple[int, str]:
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    r = subprocess.run([sys.executable, "-u", str(TARGET), *extra],
                       cwd=str(HERE.parent.parent), env=env,
                       capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def headline(out: str) -> str:
    """The lines an arm must move if it is doing anything.

    ⚠️ THE FIRST VERSION OF THIS FUNCTION MADE THE STRUCTURAL-SPLIT ARM
    SURVIVE, AND THAT WAS THE BATTERY'S FAULT AND NOT A TEST GAP. It kept
    lines matching CONTROL/REACH/TOTAL and the partition's own bucket rows
    match none of those, while `TOTAL` is 776 whichever way the ink is
    bucketed -- so the one arm aimed at the split that makes the partition
    mean anything could not move the thing being compared. *A battery whose
    headline does not reach what it mutates measures its own scope.*
    """
    keep = []
    for ln in out.splitlines():
        s = ln.strip()
        if any(t in s for t in ("CONTROL", "ALL CONTROLS", "REFUSED",
                                "VETO REACH", "VETO COST", "REACH:",
                                "TOTAL", "class-matched", "top agrees",
                                "spacing agrees", "landing on")):
            keep.append(s)
        # the partition and shape rows: "1 REAL MARK...", "2s STRUCTURAL...",
        # "a SPECK...", "MARK-SIZED..."
        elif s[:1].isdigit() and "%" in s:
            keep.append(s)
        elif s.startswith(("a SPECK", "a VERTICAL", "a HORIZONTAL",
                           "MARK-SIZED", "OTHER /")):
            keep.append(s)
    return "\n".join(keep)


def main() -> int:
    force = "--force" in sys.argv
    if SENTINEL.exists():
        print("REFUSED: an in-flight sentinel exists -- a previous battery was "
              "interrupted and the tree may still carry a mutation.")
        print(SENTINEL.read_text())
        print("Compare the target's md5 against the snapshot before rerunning.")
        return 3
    dirty = subprocess.run(["git", "status", "--porcelain", "--", str(TARGET)],
                           cwd=str(HERE), capture_output=True,
                           text=True).stdout.strip()
    if dirty and not force:
        print(f"REFUSED: {TARGET.name} is dirty ({dirty!r}). Commit it, or "
              "pass --force.")
        return 3

    SNAP.parent.mkdir(parents=True, exist_ok=True)
    SNAP.write_bytes(TARGET.read_bytes())
    want = md5(SNAP)
    SENTINEL.write_text(f"target={TARGET}\nsnapshot={SNAP}\nmd5={want}\n")

    base_rc, base_out = run()
    base_h = headline(base_out)
    print("=" * 78)
    print("BASELINE (positive control)")
    print("=" * 78)
    print(base_h or base_out[-2000:])
    print(f"exit {base_rc}")
    if base_rc != 0:
        print("\n⚠️ BASELINE IS NOT GREEN -- every arm below would be red for "
              "free. The battery measures nothing until this passes.")
        SENTINEL.unlink(missing_ok=True)
        return 4

    red, survived, bad = [], [], []
    for name, find, repl, why in ARMS:
        if find is None:
            continue
        src = SNAP.read_text()
        if src.count(find) != 1:
            bad.append((name, f"BAD ANCHOR: {src.count(find)} occurrences"))
            continue
        TARGET.write_text(src.replace(find, repl))
        rc, out = run()
        h = headline(out)
        moved = (rc != base_rc) or (h != base_h)
        (red if moved else survived).append((name, rc, why))
        print()
        print("-" * 78)
        print(f"ARM: {name}")
        print(f"  expected: {why}")
        print(f"  exit {rc} (baseline {base_rc})  headline moved: {h != base_h}"
              f"  -> {'RED' if moved else 'SURVIVED'}")
        if not moved:
            print("  ⚠️ SURVIVOR -- a real test gap, not a pass.")

    TARGET.write_bytes(SNAP.read_bytes())

    # FLAG arms run on the RESTORED file -- they change the world, not the code
    for name, flags, why in FLAG_ARMS:
        rc, out = run(flags)
        h = headline(out)
        moved = h != base_h
        (red if moved else survived).append((name, rc, why))
        print()
        print("-" * 78)
        print(f"FLAG ARM: {name}")
        print(f"  expected: {why}")
        print(f"  exit {rc}  headline moved: {moved} -> "
              f"{'RED' if moved else 'SURVIVED'}")
        for ln in h.splitlines():
            if "VETO COST" in ln:
                print(f"    {ln}")

    got = md5(TARGET)
    ok = got == want
    SENTINEL.unlink(missing_ok=True)

    print()
    print("=" * 78)
    print(f"RESULT: {len(red)} red, {len(survived)} survived, "
          f"{len(bad)} bad anchors, of {len(ARMS) - 1 + len(FLAG_ARMS)} arms")
    print(f"RESTORE VERIFIED: {ok}  (md5 {got[:12]} vs snapshot {want[:12]})")
    for n, why in bad:
        print(f"  BAD ANCHOR  {n}: {why}")
    for n, rc, why in survived:
        print(f"  SURVIVOR    {n}  (expected: {why})")
    if not ok:
        print("⚠️⚠️ RESTORE FAILED -- the tree does NOT match the snapshot.")
        return 5
    return 0 if not survived and not bad else 1


if __name__ == "__main__":
    sys.exit(main())
