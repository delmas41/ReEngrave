#!/usr/bin/env python3
"""Mutation battery for carry_domain.py.

⚠️⚠️ THIS BATTERY MUTATES PRODUCTION CODE, WHICH THE SIBLING BATTERY DOES NOT.
`carry_domain.py`'s whole claim is a claim about `rhythm.py`, so the arms that
matter perturb THE TREE and ask whether the probe notices -- mutating only the
probe would test its plumbing and not its subject. That makes the snapshot
discipline load-bearing rather than ceremonial: CLAUDE.md records a battery
restoring `export.py` from HEAD and DELETING the change it had just certified,
and another dying mid-arm and leaving the mutation on disk looking like an
ordinary edit. So: a BYTE snapshot per target written to DISK before the first
arm, an in-flight SENTINEL that refuses the next run, and a VERIFIED restore.

⚠️ AND IT MUST NOT RUN AGAINST A DIRTY TREE for those files -- an interrupted
restore would be indistinguishable from a legitimate edit. It checks.
"""
import hashlib
import json
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PROBE = HERE / "carry_domain.py"
RHYTHM = ROOT / "tools" / "omr" / "staged" / "adjudicators" / "rhythm.py"
SNAPDIR = HERE / ".mutate-carry-domain-snapshot"
SENTINEL = HERE / ".mutate-carry-domain-inflight"

#: (name, target, old, new, why)
ARMS = [
    ("carry_no_longer_first", RHYTHM,
     "    carried = _carry_meter(ev, why)",
     "    carried = None",
     "the rung-order refusal must fire"),
    ("carry_gate_removed", RHYTHM,
     "    if not meter_carry_enabled():\n        return None",
     "    if False:\n        return None",
     "the flag-gate refusal must fire"),
    ("default_flipped_to_match_the_record", RHYTHM,
     'os.environ.get(METER_CARRY_ENV, "1")',
     'os.environ.get(METER_CARRY_ENV, "0")',
     "the positive control must fail: both trees would read '0'"),
    ("change_only_callable_outside_the_chain", RHYTHM,
     "def _bar_lengths_for(ev: Evidence) -> dict:",
     "def _bar_lengths_for(ev: Evidence) -> dict:\n"
     "    if False:\n        _change_only(ev, 'x')",
     "reachability must go NO and refuse"),
    # ⚠️ The one PROBE-side arm, and it is here because the census is the only
    # figure that comes from OUTSIDE the tree. A neutered regex must ABSTAIN
    # and never report `CARRY DOMAIN: 0`, which would read as a reach zero --
    # the exact conclusion this probe exists to refute.
    ("census_regex_neutered", PROBE,
     r'r"\|\s*p\d\s*s\d\s*\|[^|]*\|\s*`([a-z_]+)`\s*\|"',
     r'r"^NOTHING MATCHES THIS$"',
     "must abstain, never report domain 0"),
]


def run():
    r = subprocess.run([sys.executable, str(PROBE)],
                       capture_output=True, text=True, cwd=ROOT)
    return r.returncode, r.stdout + r.stderr


def verdict_line(out):
    """The two lines the whole finding rests on, plus any refusal."""
    keep = [l.strip() for l in out.splitlines()
            if l.startswith("CARRY DOMAIN") or l.startswith("REFUSED")
            or "POSITIVE CONTROL FAILED" in l or l.startswith("ABSTAINED")]
    return " || ".join(keep) or "<nothing conclusive>"


def main():
    if SENTINEL.is_file():
        print("REFUSING TO START: a previous battery was interrupted.")
        print(SENTINEL.read_text())
        return 2

    targets = sorted({t for _, t, _, _, _ in ARMS})
    dirty = subprocess.run(["git", "status", "--porcelain", "--"]
                           + [str(t) for t in targets],
                           cwd=ROOT, capture_output=True, text=True).stdout
    # the probe itself is new and untracked on a first run; only a TRACKED
    # modification is the hazard here
    bad = [l for l in dirty.splitlines() if not l.startswith("??")]
    if bad:
        print("REFUSING TO START: a target is modified in the working tree, so "
              "a failed restore could not be told from a real edit:")
        print("\n".join(bad))
        return 2

    SNAPDIR.mkdir(exist_ok=True)
    originals = {}
    for t in targets:
        originals[t] = t.read_bytes()
        (SNAPDIR / t.name).write_bytes(originals[t])
    SENTINEL.write_text(json.dumps(
        {str(t): hashlib.sha256(b).hexdigest() for t, b in originals.items()},
        indent=1))

    rc = 0
    try:
        print("=" * 72)
        print("POSITIVE CONTROL FIRST -- an unmutated run must pass")
        print("=" * 72)
        code, out = run()
        base = verdict_line(out)
        print("  exit=%d  %s" % (code, base))
        if code != 0:
            print("  DEAD: the subject does not pass unmutated.")
            return 1
        print()

        survived = []
        for name, target, old, new, why in ARMS:
            src = originals[target].decode()
            if old not in src:
                print("%-42s BAD ANCHOR -- arm did not run" % name)
                survived.append(name + " (BAD ANCHOR)")
                continue
            target.write_text(src.replace(old, new, 1))
            code, out = run()
            v = verdict_line(out)
            red = (code != 0) or (v != base)
            print("%-42s %-9s exit=%d  %s" %
                  (name, "RED" if red else "SURVIVED", code, v))
            if not red:
                survived.append(name)
            target.write_bytes(originals[target])

        print()
        if survived:
            print("SURVIVORS: %s" % ", ".join(survived))
            rc = 1
        else:
            print("ALL %d ARMS RED, positive control green." % len(ARMS))
    finally:
        for t in targets:
            t.write_bytes((SNAPDIR / t.name).read_bytes())
            ok = hashlib.sha256(t.read_bytes()).hexdigest() == \
                hashlib.sha256(originals[t]).hexdigest()
            print("restore %-18s %s" % (t.name, "VERIFIED" if ok else "FAILED"))
            if not ok:
                rc = 2
        SENTINEL.unlink(missing_ok=True)
    return rc


if __name__ == "__main__":
    sys.exit(main())
