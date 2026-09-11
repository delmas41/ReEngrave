"""A mutation battery for the contest repair. ONE RED ARM IS NOT A BATTERY.

    python3 benchmarks/omr-staged-dedupe-2026-09/mutants.py

Each arm edits the tree, runs the named tests, and restores with
`git checkout -- <file>`. An arm that does NOT go red is a test gap, an
equivalent mutant, or a BAD ANCHOR — and the three are reported apart, because
a bad anchor reads exactly like a passing mutant and has silently mutated a
different function in this repo before.

⚠️ A BATTERY OF REFUSAL TESTS CAN PASS BY REFUSING EVERYTHING, so there is a
POSITIVE CONTROL in the same class: an arm that makes every glyph a relocated
copy must fail the "an uncontested note is still written" test specifically.

⚠️ DO NOT RUN THIS BESIDE AN A/B ARM THAT READS THE WORKING TREE. This
`git checkout`s the files it mutates; CLAUDE.md records exactly that collision
costing a session its first three-arm run.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

ADJ = "tools/omr/staged/adjudicate.py"
EXP = "tools/omr/staged/export.py"
TXT = "tools/omr/staged/adjudicators/text.py"
OWN = "tools/omr/staged/adjudicators/ownership.py"

DEDUPE = "tools/omr/tests/test_staged_dedupe.py"
EXPORT = "tools/omr/tests/test_staged_export.py"
DYN = "tools/omr/tests/test_staged_dynamics.py"
ALL = f"{DEDUPE} {EXPORT} {DYN}"

# (name, file, find, replace, tests, note)
ARMS = [
    ("the rule never fires (relocate again)", ADJ,
     "    return own is not None and own.to_key() != owner_value",
     "    return False", ALL,
     "the whole repair, off"),

    ("the rule ALWAYS fires", ADJ,
     "    return own is not None and own.to_key() != owner_value",
     "    return True", ALL,
     "POSITIVE CONTROL: must fail the UNCONTESTED tests, not only the "
     "contested ones"),

    ("the comparison is inverted", ADJ,
     "    return own is not None and own.to_key() != owner_value",
     "    return own is not None and own.to_key() == owner_value", ALL,
     "keeps the neighbour's copy and drops the owner's own"),

    ("a MISSING owner verdict counts as a relocation", ADJ,
     '    if not isinstance(owner_value, str) or not owner_value:\n'
     '        return False',
     '    if not isinstance(owner_value, str) or not owner_value:\n'
     '        return True', ALL,
     "absence read as a decision -- drops every uncontested glyph"),

    ("_place_notes relocates instead of refusing", EXP,
     '        if A.is_relocated_copy(sub, owner):',
     '        if False:', f"{EXPORT} {DEDUPE}",
     "the note half of the repair, off"),

    ("_place_notes drops but does NOT count it", EXP,
     '            dropped["owned_by_another_staff"] += 1',
     '            pass', EXPORT,
     "the accounting control must raise Unbalanced"),

    ("the dynamics keep the relocated letter", TXT,
     '        if is_relocated_copy(row.subject, owned_by):',
     '        if False:', DYN,
     "the letter half of the repair, off"),

    ("glyph_owner's domain is widened to every glyph", OWN,
     "    subjects_from=Q.GLYPH_BAND_DISTANCE,\n)\ndef adjudicate_glyph_owner",
     "    subjects_from=Q.GLYPH_BOX,\n)\ndef adjudicate_glyph_owner", DEDUPE,
     "the premise that makes dropping safe -- must go red"),

    ("the contest needs only ONE detection", "tools/omr/staged/gather.py",
     "                if gi.staff == gj.staff:\n                    continue",
     "                if False:\n                    continue", DEDUPE,
     "⚠️ EQUIVALENT-ISH: a same-staff pair would now contest. The premise "
     "test must still see one lone glyph produce no contest."),
]


def run(cmd, **kw):
    return subprocess.run(cmd, shell=True, cwd=ROOT, capture_output=True,
                          text=True, **kw)


def main():
    dirty = run("git status --porcelain -- tools/").stdout.strip()
    if dirty:
        print("⚠️ tools/ is dirty; this battery checks files out. Commit "
              "first.\n" + dirty)
        return 2

    base = run(f"python3 -m pytest {ALL} -q")
    if base.returncode != 0:
        print("⚠️ the suite is RED before any mutation. Nothing below means "
              "anything.")
        print(base.stdout[-3000:])
        return 2
    print(f"baseline GREEN: {base.stdout.strip().splitlines()[-1]}\n")

    red, survived, bad_anchor = [], [], []
    for name, path, find, repl, tests, note in ARMS:
        src = (ROOT / path).read_text()
        if src.count(find) != 1:
            bad_anchor.append((name, path, src.count(find)))
            print(f"BAD ANCHOR  {name}  ({src.count(find)} matches in {path})")
            continue
        (ROOT / path).write_text(src.replace(find, repl))
        try:
            r = run(f"python3 -m pytest {tests} -q")
        finally:
            run(f"git checkout -- {path}")
        tail = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else "?"
        if r.returncode != 0:
            red.append(name)
            print(f"RED         {name}\n            {tail}")
        else:
            survived.append((name, note))
            print(f"⚠️ SURVIVED  {name}\n            {tail}\n"
                  f"            note: {note}")

    print(f"\n{len(red)} red / {len(survived)} survived / "
          f"{len(bad_anchor)} bad anchors, of {len(ARMS)} arms")
    for name, note in survived:
        print(f"  SURVIVED: {name} -- {note}")
    for name, path, n in bad_anchor:
        print(f"  BAD ANCHOR: {name} -- {n} matches in {path}")
    # ⚠️ A BAD ANCHOR IS AN ERROR, NOT A PASS. It reads exactly like a mutant
    # that could not be applied, and this repo has silently mutated a different
    # function that way.
    return 0 if not bad_anchor and not survived else 1


if __name__ == "__main__":
    sys.exit(main())
