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

    ("cross-record class match removed",
     'if got[0] == t.get("cls"):',
     "if True:",
     "control F must stop refusing collided subjects -- the count must move"),

    ("the veto counts runs with NO hand reading as safe",
     "if not d and t:\n                cost_rows.append(r)",
     "if False:\n                cost_rows.append(r)",
     "the VETO COST must fall to zero -- the number that decides the rule"),

    ("a vertical run is anything taller than it is wide",
     "RUN_MIN_ASPECT = 2.0",
     "RUN_MIN_ASPECT = 1.0",
     "the run population must change"),

    ("the unexplained bucket absorbs detector-only ink",
     'elif by_det and not by_hand:\n                k = "2 DETECTOR INVENTION (det only)"',
     'elif by_det and not by_hand:\n                k = "4 UNEXPLAINED (neither)"',
     "the partition must move -- the four buckets must stay four facts"),
]


def md5(p: Path) -> str:
    return hashlib.md5(p.read_bytes()).hexdigest()


def run() -> tuple[int, str]:
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    r = subprocess.run([sys.executable, "-u", str(TARGET)],
                       cwd=str(HERE.parent.parent), env=env,
                       capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def headline(out: str) -> str:
    """The lines an arm must move if it is doing anything."""
    keep = []
    for ln in out.splitlines():
        if any(t in ln for t in ("CONTROL", "ALL CONTROLS", "REFUSED",
                                 "VETO REACH", "VETO COST", "REACH:",
                                 "TOTAL", "class-matched", "top agrees",
                                 "spacing agrees", "landing on")):
            keep.append(ln.strip())
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
    got = md5(TARGET)
    ok = got == want
    SENTINEL.unlink(missing_ok=True)

    print()
    print("=" * 78)
    print(f"RESULT: {len(red)} red, {len(survived)} survived, "
          f"{len(bad)} bad anchors, of {len(ARMS) - 1} arms")
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
