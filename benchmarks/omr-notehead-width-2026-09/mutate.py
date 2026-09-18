"""MUTATION BATTERY over this job's own probes.

There is no `tools/` change to mutate, so what is under test is the
INSTRUMENT: every control this job claims, mutated one at a time, with the
requirement that the control go RED. A control that cannot go red is not a
control, and this thread has shipped two of those already.

⚠️ THE RULE HAS THREE CLAUSES AND ALL THREE ARE OBEYED HERE:

  1. A battery must leave the tree as it FOUND it -- which is not the same as
     leaving it as GIT has it. A BYTE snapshot is taken before the first arm
     and the restore is VERIFIED by hash, never by `git checkout`.
  2. AN INTERRUPTED BATTERY OBEYS NEITHER. An in-flight SENTINEL is written
     before the first arm and deleted on a clean exit; a run that finds one
     refuses to start and names each file at risk with the hash it should
     have.
  3. ⚠️ `shutil.copy2` PRESERVES MTIME, so a `.pyc` written by one arm
     satisfies Python's `(mtime, size)` check in a later one, which then
     imports UNMUTATED code and reports NOT RED -- indistinguishable from a
     test gap. Every arm runs with `PYTHONDONTWRITEBYTECODE=1`, and the
     battery deletes `__pycache__` under the probe directory as well.

⚠️ A POSITIVE CONTROL IN THE SAME CLASS runs FIRST: the unmutated tree must
pass every control. A battery of "the control fails" arms can pass by having
a control that always fails.

⚠️ REFUSES A DIRTY TREE without `--force`: run over an uncommitted change,
a battery restores from its snapshot and the change under test survives, but
a battery that CRASHES mid-arm leaves a mutation looking exactly like the
legitimate edit. Commit a checkpoint first.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROBE = HERE / "probe"
OUT = HERE / "out"
SENTINEL = HERE / ".mutation-in-flight.json"
REPO = HERE.parents[1]
RECORDS = Path("/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records")

# Each arm: (name, file, old, new, the command that MUST now fail, why).
# ⚠️ Every `old` is asserted to occur EXACTLY ONCE in its file before the
# swap. A BAD ANCHOR is the commonest battery fault in this repo -- an anchor
# occurring twice mutates the wrong function and reports a survivor that is
# really a mis-aimed arm.
SCORE_L = ["score.py", "--pub", "litolff", "--json", "/dev/null"]
SCORE_B = ["score.py", "--pub", "breitkopf", "--json", "/dev/null"]
CONTAM = ["contamination.py", "--json", "/dev/null"]
# ⚠️ this one WRITES out/litolff-widths.json, so the battery snapshots and
# restores that file too -- an arm that leaves a mutated extraction behind
# would silently poison every later arm and every later table.
WIDTHS_L = ["widths.py",
            "--record", str(RECORDS / "beethoven5-p1-p4.record.json"),
            "--label", "Litolff Beethoven 5 pp.1-4",
            "--json", str(OUT / "litolff-widths.json")]
ISSUES = ["issues.py", "--json", "/dev/null"]

ARMS = [
    ("width-box read as a CORNER box", "widths.py",
     '"canon": [float(x) for x in v[1:]],',
     '"canon": [float(v[1]), float(v[2]), float(v[3]) - float(v[1]), float(v[4]) - float(v[2])],',
     [WIDTHS_L, SCORE_L],  # re-extract, THEN check the ruler agreement
     "the canonical box is (x,y,w,h); read as corners every width collapses "
     "and score.py's ruler-agreement control must fail"),
    ("the floor moved to 1.5 spaces", "floor.py",
     "\nFLOOR = 1.0\n", "\nFLOOR = 1.5\n", ISSUES,
     "issues.py must stop reproducing the stroke lane's 44 / 576"),
    ("the census join keyed on the CELL not the glyph", "score.py",
     'bucket = {r["subject"]: r["bucket"] for r in census["rows"]}',
     'bucket = {r["subject"].rsplit("/", 1)[0]: r["bucket"] for r in census["rows"]}',
     SCORE_L,
     "the census-covers-no_stem control must fail"),
    ("the notehead filter dropped", "score.py",
     'ctl["notehead_total"] = [len(rows), meta["n_heads"]]',
     'ctl["notehead_total"] = [len(rows) + 1, meta["n_heads"]]',
     SCORE_L,
     "a total control that cannot fail is not a control"),
    ("the partition control made vacuous", "score.py",
     'ctl["partition"] = [by_out["DECIDED"] + by_out["no_stem"]\n                        + by_out["stems_disagree"], len(rows)]',
     'ctl["partition"] = [len(rows), len(rows)]',
     None,  # vacuous-by-construction: checked by the EQUIVALENT-MUTANT note
     "EQUIVALENT MUTANT, held out -- see the note at the foot of this file"),
    ("the ruler-agreement control loosened to 10 spaces", "score.py",
     'if dif and max(dif) > 0.02:', 'if dif and max(dif) > 10.0:',
     None,  # also equivalent on a clean tree (the diff is 0.0); held out
     "EQUIVALENT MUTANT on a clean tree, held out"),
    ("the truth-mapping controls' GUARD disabled", "contamination.py",
     '    if tbad:', '    if tbad and False:',
     None,  # EQUIVALENT on a clean tree: `tbad` is empty, so the guard is
            # never reached. The arms BELOW are what prove it can fire.
     "EQUIVALENT MUTANT on a clean tree, held out -- `tbad` is empty there, "
     "so the guard is unreachable. The three mapping arms below reach it."),
    ("publisher pinned by PAGE NUMBER instead of the manifest",
     "contamination.py",
     '            pub, subj, kd = tile2.get(\n                r.get("id"), (None, r.get("subject"), None))',
     '            pub, subj, kd = (None, r.get("subject"), None)',
     CONTAM,
     "the tile ids resolve through the manifest; without it nothing joins"),
    ("`cannot_tell` collapsed back into IS-a-notehead", "contamination.py",
     '        return "cannot tell"\n    ps = r.get("print_shows")',
     '        return "IS a notehead"\n    ps = r.get("print_shows")',
     CONTAM,
     "the bug this session actually had: 0 cost becomes 5 false alarms"),
    ("an unknown vocabulary word defaulted to IS-a-notehead",
     "contamination.py",
     '    return "UNKNOWN VERDICT WORD: " + repr(ps)',
     '    return "IS a notehead"',
     None,  # DEAD BRANCH on this data: every one of the 255 rows maps, so
            # the line is unreachable and the mutant is equivalent. The arm
            # below makes it LIVE by removing a word from the vocabulary.
     "EQUIVALENT MUTANT on this data (the branch is unreachable) -- the "
     "`staff_line_gap` arm below makes it live and goes red"),
    ("a vocabulary word REMOVED, so the unknown branch goes live",
     "contamination.py",
     '    "time_signature_digit_8", "staff_line_gap", "hairpin_or_beam_wedge",',
     '    "time_signature_digit_8", "hairpin_or_beam_wedge",',
     CONTAM,
     "the five Litolff `staff_line_gap` rows become UNKNOWN; "
     "`no_unknown_verdict_word` and the Litolff sample counts must fail"),
    ("the whole-note vocabulary mapped to the wrong side",
     "contamination.py",
     'PRINT_SHOWS_IS_A_HEAD = {"dotted_half_note", "possibly_a_real_whole_note"}',
     'PRINT_SHOWS_IS_A_HEAD = set()',
     CONTAM,
     "a dotted half IS a notehead; calling it one of the non-heads inflates "
     "the floor's recall"),
    ("the stroke lane's figures taken on trust", "issues.py",
     '"agree": (thin == arm["thin_boxes"]\n                          and plaus == arm["plausible_heads"]),',
     '"agree": True,',
     None,  # equivalent on a clean tree; held out
     "EQUIVALENT MUTANT on a clean tree, held out"),
    ("the stroke reader's CIRCULAR variant used as the headline", "issues.py",
     'VARIANT = "side+end"', 'VARIANT = "side+end+legal"',
     None,  # not a control failure; a REPORTING change. Held out, named.
     "not a control -- a reporting choice. Held out and NAMED so the list "
     "does not train the reader to skim it."),
]


def files_under_test():
    return sorted({PROBE / f for _n, f, *_r in ARMS})


def digest(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def clear_pyc():
    for d in PROBE.rglob("__pycache__"):
        shutil.rmtree(d, ignore_errors=True)


def run(cmd, env):
    """A single command, or a CHAIN. A chain is red if ANY step fails."""
    if cmd is None:
        return None
    steps = cmd if isinstance(cmd[0], list) else [cmd]
    last = None
    for st in steps:
        last = subprocess.run([sys.executable, str(PROBE / st[0])] + st[1:],
                              cwd=REPO, env=env, capture_output=True,
                              text=True)
        if last.returncode != 0:
            return last
    return last


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()

    if SENTINEL.exists():
        s = json.loads(SENTINEL.read_text())
        print("REFUSING TO START: a previous battery was interrupted.",
              file=sys.stderr)
        for f, h in s["hashes"].items():
            cur = digest(Path(f)) if Path(f).exists() else "(missing)"
            mark = "ok" if cur == h else "⚠️ DIFFERS"
            print(f"   {mark}  {f}\n        should be {h[:16]}  is {cur[:16]}",
                  file=sys.stderr)
        print(f"   restore those files, then delete {SENTINEL}",
              file=sys.stderr)
        return 2

    dirty = subprocess.run(["git", "status", "--porcelain"], cwd=REPO,
                           capture_output=True, text=True).stdout.strip()
    if dirty and not a.force:
        print("REFUSING TO START: the tree is dirty. A battery that crashes "
              "mid-arm leaves a mutation looking exactly like your own edit. "
              "Commit a checkpoint, or pass --force.", file=sys.stderr)
        print(dirty, file=sys.stderr)
        return 2

    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    extra = [OUT / "litolff-widths.json"]
    snap = {str(p): p.read_bytes()
            for p in list(files_under_test()) + extra}
    hashes = {str(p): digest(p) for p in list(files_under_test()) + extra}
    SENTINEL.write_text(json.dumps({"hashes": hashes}, indent=1))
    clear_pyc()

    results = []
    try:
        # ---- POSITIVE CONTROL, in the same class, FIRST ----
        print("== POSITIVE CONTROL: the unmutated tree must pass every "
              "control")
        pc_ok = True
        for cmd in (SCORE_L, SCORE_B, CONTAM, ISSUES):
            r = run(cmd, env)
            ok = r.returncode == 0
            pc_ok &= ok
            print(f"   {'ok  ' if ok else 'FAIL'} {cmd[0]} "
                  f"{' '.join(cmd[1:3])} -> exit {r.returncode}")
            if not ok:
                print(r.stdout[-1500:], r.stderr[-1500:])
        results.append(("POSITIVE CONTROL", "green" if pc_ok else "RED"))
        if not pc_ok:
            print("DEAD: the positive control fails, so no arm below means "
                  "anything", file=sys.stderr)
            return 2

        # ---- the arms ----
        print("\n== ARMS")
        for name, fname, old, new, cmd, why in ARMS:
            p = PROBE / fname
            src = p.read_text()
            n = src.count(old)
            if n != 1:
                print(f"   BAD ANCHOR ({n} occurrences) {name}")
                results.append((name, f"BAD ANCHOR x{n}"))
                continue
            if cmd is None:
                print(f"   held out            {name}\n        -> {why}")
                results.append((name, "HELD OUT (equivalent/named)"))
                continue
            p.write_text(src.replace(old, new))
            clear_pyc()
            r = run(cmd, env)
            red = r.returncode != 0
            print(f"   {'RED ' if red else 'SURVIVED'}  {name} "
                  f"-> exit {r.returncode}")
            if not red:
                print(f"        expected: {why}")
            results.append((name, "RED" if red else "SURVIVED"))
            p.write_bytes(snap[str(p)])
            for e in extra:
                e.write_bytes(snap[str(e)])
            clear_pyc()
    finally:
        for p in list(files_under_test()) + extra:
            p.write_bytes(snap[str(p)])
        clear_pyc()
        # ⚠️ VERIFY the restore rather than trusting the write.
        bad = [str(p) for p in list(files_under_test()) + extra
               if digest(p) != hashes[str(p)]]
        if bad:
            print(f"⚠️⚠️ RESTORE FAILED for {bad} -- sentinel KEPT",
                  file=sys.stderr)
        else:
            SENTINEL.unlink(missing_ok=True)
            print("\nrestore VERIFIED by hash for every file under test")

    live = [r for r in results if r[1] in ("RED", "SURVIVED")]
    n_red = sum(1 for _n, s in live if s == "RED")
    print(f"\n{n_red} RED / {len(live)} live arms; "
          f"{sum(1 for _n, s in results if s.startswith('HELD'))} held out")
    (OUT / "mutation-battery.json").write_text(json.dumps(
        {"positive_control": "green" if pc_ok else "RED",
         "arms": [{"name": n, "result": s} for n, s in results],
         "red": n_red, "live": len(live)}, indent=1))
    return 0 if n_red == len(live) and live else 1


if __name__ == "__main__":
    raise SystemExit(main())

# ⚠️ EQUIVALENT MUTANTS, NAMED AND HELD OUT OF THE ARM LIST rather than left
# in it to go green:
#   * the partition control rewritten as `len(rows) == len(rows)` is vacuous
#     BY CONSTRUCTION -- the arm would be testing whether a tautology can
#     fail, which it cannot.
#   * loosening the ruler-agreement tolerance cannot fail on a clean tree,
#     because the two box conventions agree to 0.0 spaces there; the arm that
#     WOULD catch it is the corner/width swap, which is listed and needs a
#     re-extract to run (see `--force` note in FINDINGS §0).
#   * taking the stroke lane's figures on trust cannot fail while they agree;
#     it is the reproduction itself that is the control, and the floor-moved
#     arm is what proves that reproduction can fail.
# An arm that can never go red trains the next reader to ignore the list.
