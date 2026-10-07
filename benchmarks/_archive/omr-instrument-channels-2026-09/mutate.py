"""Does this probe MEASURE anything? -- a mutation battery over its own code.

⚠️ THE JUDGE IS THE PROBE'S NUMBERS, NEVER ITS OUTPUT TEXT. Two batteries in
this repo were voided on 2026-09-20 by comparing a pytest summary line that
ends `" in 0.57s"` -- so every arm there scored RED for free. Here the judge is
the parsed `reach-*.json`: the forced/ambiguous/no-solution counts, the graft
count, and the named-staff control. A mutation is RED when one of those moves.

⚠️ THE TREE IS RESTORED FROM A BYTE SNAPSHOT TAKEN BEFORE THE FIRST ARM, NOT
FROM GIT, and the restore is VERIFIED BY HASH. An in-flight sentinel is written
first and removed on a clean exit; a run that finds one refuses to start and
names the files at risk. `PYTHONDONTWRITEBYTECODE=1` is set in every arm's
environment because a `.pyc` written under one mutation satisfies Python's
(mtime, size) check under the next when `shutil.copy2` has preserved mtime --
which took one battery here from 10 RED / 2 survived to 12 RED / 0.
"""
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
TARGETS = [HERE / "probe_reach.py", HERE / "channels.py"]
SENTINEL = HERE / ".mutate-in-flight"

#: ⚠️ FOUR ARMS ARE EXPECTED TO SURVIVE AND ARE MARKED SO, because the branch
#: they mutate is UNREACHABLE ON BOTH DOCUMENTS -- not because the guard is
#: wrong. An arm that can never go red trains the next reader to skim the list,
#: so each says which fact of the data makes it dormant and what would wake it.
#: This is `_forced_pairing`'s condition (b) arriving in an instrument: correct,
#: unit-tested, and not corroborated by any page in this corpus.
UNEXERCISED = {
    "bracket: map blocks by index without the equal-count check":
        "every system of both documents prints the SAME NUMBER of family "
        "blocks as its reference (Litolff 3, Breitkopf 2), so the guard never "
        "fires. A page dropping a whole section would wake it.",
    "clef: no instrument ALTERNATES between clefs":
        "Breitkopf is saturated by ORDER alone (38 of 40 forced with no clef "
        "at all) and Litolff's cello-slot staves stay ambiguous either way, so "
        "no arm here is sensitive to it. `ALTERNATING_CLEFS` is justified by "
        "probe_clef_stability.py, which measures the alternation directly, and "
        "NOT by this battery.",
    "reference: take the FIRST system rather than the widest":
        "on both documents the first system IS the widest, so the two rules "
        "coincide. A document opening with a short system would wake it.",
    "classify: a prefix counts as a condensation":
        "NO forced staff on either document is a condensed one -- every "
        "`Violoncello e Basso` staff comes out AMBIGUOUS -- so the "
        "condensation branch is never reached and `ok` fires first.",
}

#: `(name, file, find, replace, why it must go red)`
ARMS = [
    ("bracket: the channel goes silent",
     "probe_reach.py",
     '    if "bracket" in arm and bmap is not None and st.block is not None:',
     '    if False:',
     "Litolff's 5 forced-by-bracket staves must fall back to ambiguous"),
    ("clef: the slot admits every clef",
     "probe_reach.py",
     '        if "instrument_clefs" in arm and ref_admissible is not None:',
     "        if False:",
     "the instrument-clef arm must fall back to the reference's own reading"),
    ("order: a None reference slot EXCLUDES instead of widening",
     "probe_reach.py",
     "if nm is None or nm == st.instrument})",
     "if nm == st.instrument})",
     "Breitkopf's reference has 3 unreadable slots; systems go unsatisfiable"),
    ("bracket: map blocks by index without the equal-count check",
     "probe_reach.py",
     "    if not a or not b or len(a) != len(b):\n        return None",
     "    if not a or not b:\n        return None\n    b = b + b[-1:] * len(a)",
     "a system that lost a whole family block would be mapped anyway"),
    ("clef: apply it to NAMED staves too, ignoring `unnamed_only`",
     "probe_reach.py",
     'if not ("unnamed_only" in arm and st.named):',
     "if True:",
     "the false bassoon clef re-enters and costs Litolff its forced staves"),
    ("clef: drop the corroboration bar",
     "channels.py",
     "CLEF_CORROBORATED_MARGIN = 2.0",
     "CLEF_CORROBORATED_MARGIN = 0.0",
     "`sure` collapses onto `raw` and the margin-1.0 readings return"),
    ("clef: no instrument ALTERNATES between clefs",
     "channels.py",
     '    "Cello": ("bass", "tenor"),',
     "",
     "Breitkopf's cello slot admits only tenor and the channel is refused"),
    ("reference: take the FIRST system rather than the widest",
     "channels.py",
     "    cands = sorted(k for k, n in counts.items() if n == widest)",
     "    cands = sorted(counts)[:1]",
     "a short system as the reference cannot express the full lineup"),
    ("solve: never drop a channel, report no-solution instead",
     "probe_reach.py",
     "        if sols or len(use) <= 1:\n            return sols, dropped",
     "        return sols, dropped",
     "an unsatisfiable system stops abstaining and starts vanishing"),
    ("classify: a prefix counts as a condensation",
     "channels.py",
     "    if len(parts) > 1 and slot_name in parts:",
     "    if printed.startswith(slot_name):",
     "`Violino II` would read as a condensation of `Violino I`"),
    ("enumeration: allow a non-increasing map",
     "probe_reach.py",
     "            walk(ordinal + 1, slot + 1, acc)",
     "            walk(ordinal + 1, slot, acc)",
     "C62 -- a score may omit, never reorder -- stops being enforced"),
]


def digest(p: Path) -> str:
    return hashlib.md5(p.read_bytes()).hexdigest()


def run(record: str):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    r = subprocess.run([sys.executable, "probe_reach.py", record],
                       cwd=HERE, env=env, capture_output=True, text=True)
    out = HERE / "out" / ("reach-%s.json" % record)
    if r.returncode not in (0, 3) or not out.is_file():
        return {"crashed": r.returncode, "stderr": r.stderr[-400:]}
    d = json.loads(out.read_text())
    return {arm: {k: v[k] for k in ("forced", "ambiguous", "no_solution",
                                    "systems_channel_dropped",
                                    "control_agree", "control_differ")}
                 | {"graft": (v["scored"] or {}).get("graft")}
            for arm, v in d["arms"].items()} or {"empty": True}


def main() -> int:
    if SENTINEL.is_file():
        print("REFUSING: a previous battery did not finish. Restore these from "
              "the hashes in %s before running again." % SENTINEL.name)
        print(SENTINEL.read_text())
        return 2
    snapshot = {p: p.read_bytes() for p in TARGETS}
    SENTINEL.write_text(json.dumps({str(p): digest(p) for p in TARGETS}, indent=1))
    records = ["litolff", "breitkopf"]
    try:
        base = {r: run(r) for r in records}
        print("=" * 78)
        print("POSITIVE CONTROL -- the unmutated tree, run twice")
        print("=" * 78)
        again = {r: run(r) for r in records}
        if again != base:
            print("FAILED: two runs of the same tree disagree. Nothing below means "
                  "anything.")
            return 2
        print("  identical on both records. The judge is stable.")
        red = survived = bad_anchor = 0
        for name, fname, find, repl, why in ARMS:
            target = HERE / fname
            src = snapshot[target].decode()
            if src.count(find) != 1:
                print("\nBAD ANCHOR  %s  (%d matches in %s)"
                      % (name, src.count(find), fname))
                bad_anchor += 1
                continue
            target.write_text(src.replace(find, repl))
            got = {r: run(r) for r in records}
            for p, b in snapshot.items():
                p.write_bytes(b)
            moved = [r for r in records if got[r] != base[r]]
            if moved:
                red += 1
                print("\nRED       %s\n          -> moved on %s  (%s)"
                      % (name, ", ".join(moved), why))
            elif name in UNEXERCISED:
                print("\nUNEXERCISED  %s\n          -> dormant, and that is the "
                      "DATA: %s" % (name, UNEXERCISED[name]))
            else:
                survived += 1
                print("\nSURVIVED  %s\n          -> nothing moved. %s" % (name, why))
        for p, b in snapshot.items():
            p.write_bytes(b)
        ok = all(digest(p) == hashlib.md5(snapshot[p]).hexdigest() for p in TARGETS)
        print()
        print("=" * 78)
        print("%d RED, %d survived, %d dormant-by-design, %d bad anchors.  "
              "restore verified: %s"
              % (red, survived, len(UNEXERCISED), bad_anchor, ok))
        run("litolff")
        run("breitkopf")
        return 0 if (survived == 0 and bad_anchor == 0 and ok) else 1
    finally:
        for p, b in snapshot.items():
            p.write_bytes(b)
        SENTINEL.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
