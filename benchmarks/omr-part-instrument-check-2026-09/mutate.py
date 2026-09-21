"""Mutation battery over `part_partition`'s instrument check.

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

IDENTITY = ROOT / "tools/omr/staged/adjudicators/identity.py"
ARM = HERE / "check_arm.py"
TARGETS = {"identity": IDENTITY, "arm": ARM}

SUITES = [
    "tools/omr/tests/test_part_instrument_check.py",
    "tools/omr/tests/test_staged_part_join.py",
    "tools/omr/tests/test_staged_slot_by_name.py",
    "tools/omr/tests/test_staged_wiring.py",
    "tools/omr/tests/test_staged_inventory.py",
]

#: (target, name, find, replace, what it must break)
ARMS = [
    # ── THE FRAME: the trap `wiring.py` named before the check existed ─────
    ("identity", "the instrument read loses its SCOPE (the bare read)",
     "    seen = ev.verdicts(Q.INSTRUMENT, scope=Scope.SELF_AND_DESCENDANTS)",
     "    seen = ev.verdicts(Q.INSTRUMENT)",
     "a DOCUMENT-scoped read finds no staff row: every page reports "
     "`checked: False` and reads as a document that prints no labels"),

    # ── ABSENT IS NOT CLEAN ────────────────────────────────────────────────
    ("identity", "an unread page reports a clean zero instead of abstaining",
     '        return {"checked": False,\n'
     '                "why_not": "no_instrument_was_read",',
     '        return {"checked": True, "parts_contested": 0,\n'
     '                "why_not": "no_instrument_was_read",',
     "silence read as agreement — the failure that would have reported the "
     "part join sound on the 75-of-75 pages where it was worst"),

    # ── THE CHECK MAY NOT ACT ──────────────────────────────────────────────
    ("identity", "a contested join is downgraded to an abstention (it ACTS)",
     '    return Ruling(value={"join": _JOIN_SLOT,',
     '    if _instrument_consistency(ev, _JOIN_SLOT).get("parts_contested"):\n'
     '        return Ruling.abstain("no_evidence")\n'
     '    return Ruling(value={"join": _JOIN_SLOT,',
     "the wiring plan's one condition: a wiring pass may CONNECT a decision, "
     "it may not let one GUESS"),

    # ── THE JOIN'S OWN TERMS ───────────────────────────────────────────────
    ("identity", "the slot join is checked in ORDINAL terms",
     '                  detail={"instrument_consistency":\n'
     '                          _instrument_consistency(ev, _JOIN_SLOT)})',
     '                  detail={"instrument_consistency":\n'
     '                          _instrument_consistency(ev, _JOIN_ORDINAL)})',
     "a check asked in the wrong join's terms measures a partition that does "
     "not ship, and reports the shipping one broken"),

    ("identity", "the slots_are_ordinals branch is checked as a SLOT join",
     '                              "instrument_consistency":\n'
     '                                  _instrument_consistency(ev, _JOIN_ORDINAL),',
     '                              "instrument_consistency":\n'
     '                                  _instrument_consistency(ev, _JOIN_SLOT),',
     "that branch has just decided the slot table IS the ordinal; checking it "
     "as a slot join checks a partition it refused"),

    # ── THE ANSWER ─────────────────────────────────────────────────────────
    ("identity", "contested counts every part, not the disagreeing ones",
     "    contested = {k: sorted(set(v)) for k, v in named.items()\n"
     "                 if len(set(v)) > 1}",
     "    contested = {k: sorted(set(v)) for k, v in named.items()}",
     "every part reports as contested, including the ones that agree"),

    ("identity", "a part named on ONE system is counted as agreeing",
     '            "parts_with_two_or_more_named_staves":\n'
     "                sum(1 for v in named.values() if len(v) > 1),",
     '            "parts_with_two_or_more_named_staves":\n'
     "                len(named),",
     "reach the check does not have: a part named once cannot disagree with "
     "itself"),

    ("identity", "an unkeyed staff is silently dropped rather than counted",
     "        if key is None:\n"
     "            unkeyed += 1\n"
     "            continue",
     "        if key is None:\n"
     "            continue",
     "a hole in the check's reach reported as full coverage"),

    ("identity", "the slot join keys by the staff's ORDINAL anyway",
     "            slot = ev.verdict(Q.SLOT_INDEX, subject=v.subject)\n"
     "            key = slot.value if slot is not None else None",
     "            key = v.subject.staff",
     "the gap a slot table exists to express is thrown away, and two "
     "instruments collide on one key"),

    # ── THE ORDINAL BRANCH IS CHECKED TOO ──────────────────────────────────
    ("identity", "the equal-count branch skips the check entirely",
     '                      reason="ordinal", used=tuple(v.id for v in counts),\n'
     '                      detail={"instrument_consistency":\n'
     '                              _instrument_consistency(ev, _JOIN_ORDINAL)})',
     '                      reason="ordinal", used=tuple(v.id for v in counts))',
     "the branch where an equal-count constraint is satisfiable BY ACCIDENT — "
     "two 11-staff systems with different lineups — goes unchecked"),

    # ── THE ARM'S OWN CONTROLS ─────────────────────────────────────────────
    ("arm", "the arm stops asserting the join is UNMOVED",
     "        if got.get(\"value\") != want.get(\"value\"):",
     "        if False:",
     "a check that silently re-decided the partition would report a clean "
     "control"),

    ("arm", "the arm drops its POSITIVE control (detail present)",
     '        if "instrument_consistency" not in (got.get("detail") or {}):',
     "        if False:",
     "'nothing moved' is also what a check that never ran looks like"),

    ("arm", "the arm reports a clean result at ZERO reach",
     '    if not check.get("checked"):',
     "    if False:",
     "REACH BEFORE ACCURACY: an arm that cannot speak must declare itself "
     "DEAD, not print a table"),
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
