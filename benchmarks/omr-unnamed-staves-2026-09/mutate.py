"""Mutation battery for this benchmark's OWN probes.

⚠️ THE SUBJECT IS THE INSTRUMENT, because nothing under `tools/` is changed by
this work -- the deliverable is a measured refusal. So what must be shown to
have teeth is the measurement: that the graft detector can fire, that the
constraint actually constrains, and that the robustness arm can distinguish a
stable placement from a movable one.

THE RECORDED HAZARDS, each paid for elsewhere in this repo and obeyed here:
  * a battery must leave the tree as it FOUND it, which is NOT the same as
    leaving it as GIT has it -- so the restore is from a BYTE SNAPSHOT taken
    before the first arm, never from `git checkout`;
  * the restore is VERIFIED, byte for byte, and a mismatch is fatal;
  * an interrupted battery obeys neither, so an IN-FLIGHT SENTINEL is written
    before the first arm and removed on a clean exit; a run that finds one
    refuses to start and names each file at risk with the hash it should have;
  * a dirty tree is refused without --force, because a battery run over an
    uncommitted change has destroyed that change before now;
  * every anchor is asserted UNIQUE before it is applied -- two batteries in
    this repo silently mutated a different function than the one they named.

⚠️ A BATTERY OF REFUSAL ARMS PASSES BY REFUSING EVERYTHING, so there is a
POSITIVE CONTROL in the same class: an arm that must stay GREEN.
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
SENTINEL = HERE / "out" / ".mutate-in-flight.json"

# (file, unique anchor, replacement, arm name, expectation)
#   "red"   -- the checks must NOTICE this change
#   "green" -- the positive control: this must NOT disturb the result
ARMS = [
    ("probe_forced_by_clef.py",
     '    if len(parts) > 1 and slot_name in parts:',
     '    if False:',
     "classify can no longer see a condensation", "red"),
    ("probe_forced_by_clef.py",
     '    return "graft"',
     '    return "ok"',
     "classify can never report a graft", "red"),
    ("probe_forced_by_clef.py",
     '            if ok is not None and slot not in ok:',
     '            if False:',
     "the clef constraint is removed entirely", "red"),
    ("probe_forced_by_clef.py",
     '            walk(ordinal + 1, slot + 1, acc)',
     '            walk(ordinal + 1, slot, acc)',
     "the assignment stops being strictly increasing", "red"),
    ("probe_forced_by_clef.py",
     '            if len(got) == 1:',
     '            if len(got) >= 1:',
     "an ambiguous staff is placed anyway (the guess)", "red"),
    ("probe_witnesses.py",
     '        elif s.clef in want:',
     '        elif True:',
     "the clef witness is scored as always right", "red"),
    # ── POSITIVE CONTROL: a cosmetic change must leave every number alone
    ("probe_forced_by_clef.py",
     'MAX_ENUM = 200000  # a system this ambiguous is a "cannot tell", not a slow one',
     'MAX_ENUM = 199999  # a system this ambiguous is a "cannot tell", not a slow one',
     "POSITIVE CONTROL: an irrelevant constant", "green"),
]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def baseline() -> dict:
    """The numbers every red arm must disturb and every green arm must not."""
    r = subprocess.run([sys.executable, "probe_forced_by_clef.py"], cwd=HERE,
                       capture_output=True, text=True)
    w = subprocess.run([sys.executable, "probe_witnesses.py"], cwd=HERE,
                       capture_output=True, text=True)
    if r.returncode != 0 or w.returncode != 0:
        raise SystemExit("a probe failed at baseline:\n%s\n%s"
                         % (r.stderr[-800:], w.stderr[-800:]))
    return {"forced": r.stdout, "witness": w.stdout}


def main() -> int:
    force = "--force" in sys.argv
    files = sorted({a[0] for a in ARMS})
    paths = {f: HERE / f for f in files}

    if SENTINEL.is_file():
        print("REFUSING: a previous battery did not finish. Files at risk:",
              file=sys.stderr)
        for f, h in json.loads(SENTINEL.read_text())["hashes"].items():
            cur = sha(HERE / f) if (HERE / f).is_file() else "MISSING"
            print("   %-28s should be %s  is %s"
                  % (f, h[:16], cur[:16]), file=sys.stderr)
        print("Restore them, delete %s, and re-run." % SENTINEL, file=sys.stderr)
        return 2

    dirty = subprocess.run(["git", "status", "--porcelain", "--", str(HERE)],
                           cwd=HERE, capture_output=True, text=True).stdout.strip()
    if dirty and not force:
        print("REFUSING: the tree is dirty and a battery has destroyed an\n"
              "uncommitted change before now. Commit, or pass --force.\n%s"
              % dirty, file=sys.stderr)
        return 2

    # ── every anchor unique, BEFORE anything is written
    for f, anchor, _, name, _ in ARMS:
        n = paths[f].read_text().count(anchor)
        if n != 1:
            print("BAD ANCHOR (%d matches, need 1) in %s for arm: %s"
                  % (n, f, name), file=sys.stderr)
            return 2
    print("all %d anchors unique" % len(ARMS))

    snapshot = {f: paths[f].read_bytes() for f in files}
    SENTINEL.parent.mkdir(parents=True, exist_ok=True)
    SENTINEL.write_text(json.dumps(
        {"hashes": {f: hashlib.sha256(b).hexdigest()
                    for f, b in snapshot.items()}}, indent=1))

    base = baseline()
    print("baseline captured")
    print()

    results = []
    try:
        for f, anchor, repl, name, expect in ARMS:
            paths[f].write_text(paths[f].read_text().replace(anchor, repl, 1))
            try:
                out = baseline()
                changed = (out["forced"] != base["forced"]
                           or out["witness"] != base["witness"])
                verdict = "changed" if changed else "UNCHANGED"
            except SystemExit:
                changed, verdict = True, "crashed (counts as noticed)"
            finally:
                paths[f].write_bytes(snapshot[f])
            good = changed if expect == "red" else not changed
            results.append((name, expect, verdict, good))
            print("   [%s] %-52s %s" % ("OK " if good else "!! ", name, verdict))
    finally:
        for f in files:
            paths[f].write_bytes(snapshot[f])
        bad = [f for f in files if sha(paths[f])
               != hashlib.sha256(snapshot[f]).hexdigest()]
        if bad:
            print("RESTORE FAILED for %s" % bad, file=sys.stderr)
            return 2
        print()
        print("restore verified byte-for-byte on %d file(s)" % len(files))
        SENTINEL.unlink(missing_ok=True)

    red = [r for r in results if r[1] == "red"]
    green = [r for r in results if r[1] == "green"]
    survivors = [r for r in results if not r[3]]
    print("arms %d (%d red-expected, %d positive control), survivors %d"
          % (len(results), len(red), len(green), len(survivors)))
    for s in survivors:
        print("   SURVIVOR: %s" % s[0])
    return 1 if survivors else 0


if __name__ == "__main__":
    raise SystemExit(main())
