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
    # ⚠️ SCORING THE *CLEF* WITNESS AS ALWAYS-RIGHT IS AN EQUIVALENT MUTANT ON
    # THIS DOCUMENT and is deliberately NOT an arm: the 25 staves' clef is 20
    # decided and 20 correct, so `s.clef in want` and `True` agree on every
    # row. An arm that can never go red trains the next reader to skim the
    # list. The KEY witness is mutated instead -- it disagrees with the print
    # 5 times, so that arm CAN fire.
    ("probe_witnesses.py",
     '        elif s.key == want:\n            kok += 1',
     '        elif True:\n            kok += 1',
     "the key witness is scored as always right", "red"),
    # ── Sean's suffix rule
    # ⚠️ NARROWING the window, not removing it. REMOVING it is an EQUIVALENT
    # MUTANT on this document -- every unnamed block here is size 4 or 5, so
    # `contiguous and in_range` and `contiguous` agree on all six systems and
    # the arm could never go red. Narrowing to 5-only stops the five 4-blocks
    # from firing, which tests that the window is consulted at all. ⚠️ What
    # stays UNTESTED either way is the window's real job: refusing a block of
    # 1-2 staves, which this document never prints.
    ("probe_suffix_rule.py",
     'MIN_BLOCK, MAX_BLOCK = 4, 5',
     'MIN_BLOCK, MAX_BLOCK = 5, 5',
     "the block-size window is narrowed to 5 only", "red"),
    ("probe_suffix_rule.py",
     '            elif len(block) == n_slot - 1 and i < len(block) - 1:',
     '            elif len(block) == n_slot - 1:',
     "a SHORT block's last member is placed instead of abstained", "red"),
    ("probe_suffix_rule.py",
     'GLYPH_CLEF = {"clefG": "treble", "clefF": "bass", "clefC": "alto"}',
     'GLYPH_CLEF = {"gClef": "treble", "fClef": "bass", "cClef": "alto"}',
     "the clef map reverts to the SMuFL spellings that matched nothing", "red"),
    # ── POSITIVE CONTROL: a cosmetic change must leave every number alone
    ("probe_forced_by_clef.py",
     'MAX_ENUM = 200000  # a system this ambiguous is a "cannot tell", not a slow one',
     'MAX_ENUM = 199999  # a system this ambiguous is a "cannot tell", not a slow one',
     "POSITIVE CONTROL: an irrelevant constant", "green"),
]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


#   ⚠️⚠️ `probe_sensitivity.py` IS IN THIS LIST BECAUSE THE BATTERY'S FIRST RUN
#   REPORTED THREE SURVIVORS AND TWO OF THEM WERE THE BATTERY'S OWN SCOPE.
#   On this document the baseline forces 16 placements with ZERO grafts and
#   ZERO condensations, so an arm breaking `classify`'s graft branch or its
#   condensation branch changed nothing -- the branches are unreachable from
#   those two probes. The probe that DOES reach them is the sensitivity arm,
#   which produces 19 grafting perturbations. *A battery whose tests do not
#   reach the file it mutates measures its own scope*, which this repo has
#   recorded twice before and which happened here on the first run.
PROBES = ("probe_forced_by_clef.py", "probe_witnesses.py",
          "probe_sensitivity.py", "probe_suffix_rule.py")


def baseline() -> dict:
    """The numbers every red arm must disturb and every green arm must not."""
    out = {}
    for name in PROBES:
        r = subprocess.run([sys.executable, name], cwd=HERE,
                           capture_output=True, text=True)
        if r.returncode != 0:
            raise SystemExit("%s failed at baseline:\n%s" % (name, r.stderr[-800:]))
        out[name] = r.stdout
    return out


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
                changed = any(out[k] != base[k] for k in PROBES)
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
