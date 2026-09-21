#!/usr/bin/env python3
"""Mutation battery over this lane's one instrument.

⚠️ THE PROBE IS THE ONLY THING THIS LANE SHIPS. Nothing under `tools/` changes
— the lane's result is a NEGATIVE — so there is no unit suite to be the judge.
The judge is the probe's own HEADLINE, which must MOVE. An arm that leaves it
unchanged is a SURVIVOR and a real gap.

⚠️ ONE RED ARM IS NOT A BATTERY, and the baseline must be GREEN before any arm
is read, or every arm is red for free.

⚠️ A MUTATION BATTERY MUST LEAVE THE TREE AS IT FOUND IT — WHICH IS NOT THE
SAME AS LEAVING IT AS GIT HAS IT, AND AN INTERRUPTED BATTERY OBEYS NEITHER. A
BYTE snapshot on disk, an in-flight SENTINEL, a VERIFIED restore by md5, and a
refusal to start on a dirty tree without `--force`. Convention inherited from
`benchmarks/omr-stem-attribution-2026-09/mutate.py` rather than re-argued.

⚠️ THE SMALLER RECORD ONLY. Litolff is 132 MB; Breitkopf is 443 MB and every
arm would pay it. Every arm here is a claim about the RULE, not about a plate —
and the publisher SPLIT is a finding of the FINDINGS, not of the battery.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / "out"
SENTINEL = OUT / ".mutate-in-flight"

PROBE = HERE / "probe_two_stems_as_one.py"
TARGETS = {"probe": PROBE}

LIB = Path("/Users/seanjohnson/Desktop/ReEngrave/library")
RECORD = LIB / "_shared-records" / "beethoven5-p1-p4.record.json"

#: (target, name, find, replace, what it must break)
ARMS = [
    # ── THE UNIT. The whole reason this lane could correct §0(d). ──────────
    ("probe", "the unit becomes a flat 100 px again (the §0(d) fault)",
     '        elif q == "cell_staff_space":',
     '        elif q == "__never_matches_anything__":',
     "every staff-space median, and the count of cells carrying a space"),
    ("probe", "the staff space is read but never applied",
     '            "len_spaces": (sb[3] / sp) if sp else None,',
     '            "len_spaces": (sb[3] / 100.0) if sp else None,',
     "the flagged/unflagged length medians on any non-100 cell"),

    # ── THE OVERSHOOT: measured past the head's EDGE, not its CENTRE. ──────
    ("probe", "overshoot is measured from the head's CENTRE (§0(d)'s spelling)",
     '        over_bot = ((sb[1] + sb[3]) - (bot[1] + bot[3])) / hh',
     '        over_bot = ((sb[1] + sb[3]) - (bot[1] + bot[3] / 2.0)) / hh',
     "every both-ends count, by about half a notehead of free overshoot"),
    ("probe", "the OUTERMOST claimant is no longer the outermost",
     '        top, bot = cl[0]["box"], cl[-1]["box"]',
     '        top, bot = cl[0]["box"], cl[0]["box"]',
     "over_bot on every run carrying more than one head"),
    ("probe", "the claimants are not sorted, so first/last are arbitrary",
     '                    for h in sorted(claimants, key=lambda h: h[2][1])],',
     '                    for h in claimants],',
     "which head counts as outermost on a multi-head run"),

    # ── THE BOTH-ENDS PREDICATE ITSELF. ────────────────────────────────────
    ("probe", "both-ends becomes either-end (the asymmetry is the whole test)",
     '            "both_ends": over_top > 0.5 and over_bot > 0.5,',
     '            "both_ends": over_top > 0.5 or over_bot > 0.5,',
     "the both-ends counts and the reach"),
    ("probe", "the both-ends cut goes to zero, so box jitter qualifies",
     '        over_top = (top[1] - sb[1]) / hh',
     '        over_top = (top[1] - sb[1]) / hh + 0.5',
     "the both-ends counts (the 0..0.25 jitter band floods in)"),

    # ── THE §0(b) CLASSIFICATION the flagged set is built from. ────────────
    ("probe", "the end band widens, so a mid-stroke head reads as at-an-end",
     '            if gap <= 1.0:',
     '            if gap <= 3.0:',
     "at_an_end, and therefore the whole flagged population"),
    ("probe", "the companion offset is measured in PIXELS, not notehead widths",
     "            offs = [abs(o[\"box\"][0] - hb[0]) / max(1.0, hb[2])",
     "            offs = [abs(o[\"box\"][0] - hb[0]) / 1.0",
     "the same-x/chord band, and the flagged residue under it"),
    ("probe", "a head is compared against itself, so every head has a companion",
     '                    for o in s["claimants"] if o["subject"] != c["subject"]]',
     '                    for o in s["claimants"]]',
     "no_companion, which falls to zero"),

    # ── THE FRAME. The fault this repo records four instances of. ──────────
    ("probe", "the overlap test loses its y half (a frame error)",
     '    return not (a[0] + a[2] <= b[0] or b[0] + b[2] <= a[0]\n'
     '                or a[1] + a[3] <= b[1] or b[1] + b[3] <= a[1])',
     '    return not (a[0] + a[2] <= b[0] or b[0] + b[2] <= a[0])',
     "the pair count, by claiming every head at that x on the page"),
    ("probe", "a corner box is read as a width box",
     '            stems[o["subject"]].append((o["id"], [float(x) for x in v]))',
     '            stems[o["subject"]].append((o["id"], [float(v[0]), float(v[1]),'
     ' float(v[2]) - float(v[0]), float(v[3]) - float(v[1])]))',
     "every stroke height, and so every overshoot"),

    # ── REACH FIRST. The rule that stops a dead probe reading as a result. ─
    ("probe", "the reach-first refusal is removed (a dead probe reads clean)",
     '    if not n_heads or not n_stems:',
     '    if False:',
     "nothing on a healthy record -- an EQUIVALENT MUTANT, held out below"),
]

#: ⚠️ NAMED AND HELD OUT rather than left in the list to go green for free.
#: On a record that HAS heads and stems the reach-first branch cannot be
#: reached, so mutating it is an equivalent mutant — exactly the shape
#: CLAUDE.md records being deleted rather than tested around. It is kept in
#: `ARMS` only so the next reader sees it was considered, and is excluded from
#: the verdict here. Its real test is `--dead-probe`, below, which runs the
#: probe against a record carrying no stem at all.
EQUIVALENT = {"the reach-first refusal is removed (a dead probe reads clean)"}


def md5b(b: bytes) -> str:
    return hashlib.md5(b).hexdigest()[:12]


def _run(args: list, cwd=ROOT) -> tuple[int, str]:
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    r = subprocess.run([sys.executable, "-u", *args], cwd=str(cwd), env=env,
                       capture_output=True, text=True)
    return r.returncode, (r.stdout + r.stderr)


def headline() -> tuple[int, str]:
    """The probe, and every number it prints."""
    tmp = OUT / ".mutate"
    tmp.mkdir(parents=True, exist_ok=True)
    rc, o = _run([str(PROBE), "--record", str(RECORD), "--label", "M",
                  "--json", str(tmp / "probe.json")])
    keep = [s for s in (line.strip() for line in o.splitlines())
            if any(t in s for t in (
                "notehead boxes", "overlapping pairs", "at_an_end",
                "companion", "no_companion", "FLAGGED", "flagged strokes",
                "BOTH ends", "UNFLAGGED", "median", "strokes", "both_ends",
                "DEAD"))]
    return rc, "\n".join(keep)


def dead_probe() -> tuple[int, str]:
    """⚠️ THE REACH-FIRST BRANCH, EXERCISED FOR REAL.

    A record with no stem row at all must make the probe exit NON-ZERO and say
    DEAD. Written as its own control because the mutation arm for it is an
    equivalent mutant on a healthy record — *a branch that cannot be reached
    cannot be wrong, and cannot be right either.*
    """
    tmp = OUT / ".mutate"
    tmp.mkdir(parents=True, exist_ok=True)
    empty = tmp / "empty.record.json"
    empty.write_text(json.dumps({"record": {"observations": []}}))
    return _run([str(PROBE), "--record", str(empty), "--label", "DEAD",
                 "--json", str(tmp / "dead.json")])


def main() -> int:
    force = "--force" in sys.argv
    if SENTINEL.exists():
        print("REFUSED: an in-flight sentinel exists -- a previous battery "
              "was interrupted and the tree may still carry a mutation.")
        print(SENTINEL.read_text())
        return 3
    rel = [str(p.relative_to(ROOT)) for p in TARGETS.values()]
    dirty = subprocess.run(["git", "status", "--porcelain", "--", *rel],
                           cwd=str(ROOT), capture_output=True,
                           text=True).stdout.strip()
    if dirty and not force:
        print(f"REFUSED: a target is dirty:\n{dirty}\nCommit, or --force.")
        return 3

    OUT.mkdir(parents=True, exist_ok=True)
    snap = {k: v.read_bytes() for k, v in TARGETS.items()}
    SENTINEL.write_text("\n".join(
        f"{k}={TARGETS[k]} md5={md5b(v)}" for k, v in snap.items()) + "\n")

    print("=" * 78)
    print("BASELINE (the positive control -- every arm is free if this is not "
          "green)")
    print("=" * 78)
    b_rc, b_out = headline()
    print(f"  exit {b_rc}")
    print("  " + b_out.replace("\n", "\n  "))
    if b_rc != 0:
        print("\n⚠️ BASELINE IS NOT GREEN. The battery measures nothing.")
        for k, v in snap.items():
            TARGETS[k].write_bytes(v)
        SENTINEL.unlink(missing_ok=True)
        return 4

    d_rc, d_out = dead_probe()
    d_ok = d_rc != 0 and "DEAD" in d_out
    print(f"\nREACH-FIRST CONTROL: a record with no stem -> exit {d_rc}, "
          f"says DEAD: {'DEAD' in d_out}  -> {'OK' if d_ok else '⚠️ FAILED'}")

    red, survived, bad, held = [], [], [], []
    for target, name, find, repl, why in ARMS:
        if name in EQUIVALENT:
            held.append((target, name, why))
            print(f"\n{'-' * 78}\nARM [{target}]: {name}\n"
                  f"  HELD OUT -- equivalent mutant on a healthy record; its "
                  f"real test is the REACH-FIRST CONTROL above.")
            continue
        src = snap[target].decode("utf-8")
        if src.count(find) != 1:
            bad.append((name, f"{src.count(find)} occurrences in {target}"))
            print(f"\n{'-' * 78}\nARM [{target}]: {name}\n  ⚠️ BAD ANCHOR "
                  f"({src.count(find)} occurrences) -- REPORTED AS AN ERROR")
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
            print("  ⚠️ SURVIVOR -- a real gap, not a pass.")

    ok = True
    for k, v in snap.items():
        TARGETS[k].write_bytes(v)
        if md5b(TARGETS[k].read_bytes()) != md5b(v):
            print(f"\n⚠️⚠️ RESTORE FAILED for {k}")
            ok = False
    if ok:
        SENTINEL.unlink(missing_ok=True)

    print("\n" + "=" * 78)
    print(f"RED {len(red)}   SURVIVED {len(survived)}   BAD ANCHORS {len(bad)}"
          f"   HELD OUT (equivalent) {len(held)}")
    print(f"reach-first control: {'OK' if d_ok else 'FAILED'}")
    print(f"restore VERIFIED by md5: {ok}")
    for t, n, _ in survived:
        print(f"  SURVIVOR [{t}] {n}")
    for n, m in bad:
        print(f"  BAD ANCHOR {n}: {m}")
    return 0 if (ok and d_ok and not survived and not bad) else 1


if __name__ == "__main__":
    raise SystemExit(main())
