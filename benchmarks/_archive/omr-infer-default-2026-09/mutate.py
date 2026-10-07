"""Mutation battery for the two 2026-09-21 evening changes.

    1. INFER's per-rule GATES -- `collapse_slot_index_to_family_block` on by
       default under its own flag, the two duration rules still behind
       `OMR_INFER`.
    2. The supplied clef admitted GAPS ONLY.

⚠️ EACH ARM NAMES ITS OWN SUBJECT FILE. The sibling battery in
`omr-factsheet-2026-09` dispatches its second subject by substring-matching
the arm's NAME (`"per-system seed collapses" in name`), which is a hand list
wearing a conditional: rename an arm and it silently mutates the wrong file,
which is how the fermata battery once mutated a different function entirely.

Discipline enforced rather than described, all of it paid for in this repo:
a BYTE snapshot before the first arm; `PYTHONDONTWRITEBYTECODE=1` in every
subprocess (a `.pyc` written under one arm survives `shutil.copy2`'s
mtime-preserving restore, and the NEXT arm then imports UNMUTATED code and
reports NOT RED); every mutation VERIFIED BY HASH to have changed its file;
an in-flight sentinel so an interrupted run refuses to start again; and every
subject's restore verified by hash at the end -- not just the first one.

⚠️ THE JUDGE MAY NOT CONTAIN pytest's OWN ELAPSED TIME. The summary line ends
" in 0.40s", which differs between two runs of an unmutated tree, so a judge
comparing it verbatim scores every arm RED for free. That shape voided two
published batteries here on 2026-09-20.
"""

import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SENTINEL = Path(__file__).resolve().parent / ".mutate-in-flight"

INFER = "tools/omr/staged/infer.py"
INFERENCES = "tools/omr/staged/inferences.py"
CLEF = "tools/omr/staged/adjudicators/clef.py"

TESTS = [
    "tools/omr/tests/test_infer_stage.py",
    "tools/omr/tests/test_infer_bypass.py",
    "tools/omr/tests/test_staged_clef.py",
    "tools/omr/tests/test_flag_default_direction.py",
]

# (subject, name, find, replace)
ARMS = [
    # ── 1. the switch mechanism ────────────────────────────────────────────
    (INFER, "run() ignores every rule's switch",
     "        if not r.switch():",
     "        if False:"),
    (INFER, "run() refuses every rule",
     "        if not r.switch():",
     "        if True:"),
    (INFER, "a switched-off rule is skipped SILENTLY",
     "            report.disabled.append((r.inference.value, r.switch.env))",
     "            pass"),
    (INFER, "the report names the wrong flag",
     "            report.disabled.append((r.inference.value, r.switch.env))",
     '            report.disabled.append((r.inference.value, "OMR_WRONG"))'),
    (INFER, "enabled_rules() ignores the switch",
     "    return [r for r in RULES if not r.stub and r.switch()]",
     "    return [r for r in RULES if not r.stub]"),
    (INFER, "enabled_rules() returns nothing",
     "    return [r for r in RULES if not r.stub and r.switch()]",
     "    return []"),
    (INFER, "stage_should_run() is always True",
     "    return bool(enabled_rules())\n\n\ndef _candidate_values",
     "    return True\n\n\ndef _candidate_values"),
    (INFER, "stage_should_run() is always False",
     "    return bool(enabled_rules())\n\n\ndef _candidate_values",
     "    return False\n\n\ndef _candidate_values"),

    # ── 2. the flag DIRECTIONS ───────────────────────────────────────────
    (INFER, "the family-block flag becomes default-OFF",
     'return (os.environ.get(FAMILY_BLOCK_ENV, "1").strip().lower()\n'
     "            not in _OFF_WORDS)",
     'return (os.environ.get(FAMILY_BLOCK_ENV, "0").strip().lower()\n'
     "            in _ON_WORDS)"),
    (INFER, "the family-block flag becomes an ALLOW-list (typo silences it)",
     'return (os.environ.get(FAMILY_BLOCK_ENV, "1").strip().lower()\n'
     "            not in _OFF_WORDS)",
     'return (os.environ.get(FAMILY_BLOCK_ENV, "1").strip().lower()\n'
     "            in _ON_WORDS)"),
    (INFER, "OMR_INFER becomes default-ON",
     'return os.environ.get(INFER_ENV, "0").strip().lower() in _ON_WORDS',
     'return os.environ.get(INFER_ENV, "1").strip().lower() not in _OFF_WORDS'),
    # ⚠️ AN EQUIVALENT MUTANT WAS TRIED HERE FIRST AND IS NAMED RATHER THAN
    # KEPT: giving `Switch.env` / `Switch.fn` DEFAULTS cannot fire, because every
    # Switch in the tree is constructed with both arguments POSITIONALLY, so the
    # defaults are unreachable. It survived, correctly. *An arm that can never
    # go red trains the next reader to skim the list*, so it was replaced by
    # one that mutates the value actually used.
    (INFER, "INFER_SWITCH carries the wrong flag name",
     'INFER_SWITCH = Switch(INFER_ENV, infer_enabled)',
     'INFER_SWITCH = Switch("OMR_NOT_A_FLAG", infer_enabled)'),

    # ── 3. the rule's own opt-in ─────────────────────────────────────────
    (INFERENCES, "the slot rule falls back to the stage-wide flag",
     "    switch=FAMILY_BLOCK_SWITCH,\n    target=Q.SLOT_INDEX,",
     "    target=Q.SLOT_INDEX,"),

    # ── 4. the supplied clef, GAPS ONLY ──────────────────────────────────
    (CLEF, "the supplied clef is admitted everywhere again",
     '        if row.detail.get("tier") == "dossier":\n'
     "            if page_spoke:",
     '        if row.detail.get("tier") == "dossier":\n'
     "            if False:"),
    (CLEF, "the supplied clef is NEVER admitted",
     '        if row.detail.get("tier") == "dossier":\n'
     "            if page_spoke:",
     '        if row.detail.get("tier") == "dossier":\n'
     "            if True:"),
    (CLEF, "the gap test counts the supplied terms too",
     "    read = (_detector_terms(ev), _locator_terms(ev))\n"
     "    page_spoke = any(bool(source) for source in read)",
     "    read = (_detector_terms(ev), _locator_terms(ev))\n"
     "    page_spoke = False"),
    (CLEF, "a withheld seed is not counted",
     "                withheld += 1\n                continue",
     "                continue"),
    (CLEF, "the withheld count never reaches the verdict",
     '        detail["supplied_clefs_withheld_because_the_page_spoke"] = seeds_withheld',
     "        pass"),
    (CLEF, "the CARRY tier is swallowed by the gap rule",
     '        out.setdefault(name, []).append(Term("carry", W_CARRY, (row.id,)))',
     "        pass"),
    (CLEF, "the supplied clef keeps the carry's weight",
     '                Term("supplied", W_DOSSIER, (row.id,)))',
     '                Term("supplied", W_CARRY, (row.id,)))'),
]


def _run() -> str:
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    env.pop("OMR_INFER", None)
    env.pop("OMR_SLOT_FAMILY_BLOCK", None)
    out = subprocess.run([sys.executable, "-m", "pytest", *TESTS, "-q"],
                         cwd=ROOT, capture_output=True, text=True, env=env)
    line = ""
    for ln in (out.stdout + out.stderr).splitlines():
        if re.search(r"\d+ (passed|failed|error)", ln):
            line = ln
    # ⚠️ pytest's elapsed time is stripped HERE and nowhere else.
    return re.sub(r" in [\d.]+s.*$", "", line).strip() or "NO SUMMARY LINE"


def main() -> int:
    if SENTINEL.exists():
        print("REFUSING: an earlier battery did not finish.\n"
              + SENTINEL.read_text())
        return 2

    subjects = sorted({a[0] for a in ARMS})
    originals = {s: (ROOT / s).read_bytes() for s in subjects}
    digests = {s: hashlib.sha256(b).hexdigest() for s, b in originals.items()}
    SENTINEL.write_text("\n".join(f"{s} {d}" for s, d in digests.items()) + "\n")

    try:
        base = _run()
        print(f"BASE (unmutated): {base}")
        if "failed" in base or "error" in base or base == "NO SUMMARY LINE":
            print("REFUSING: the base is not green.")
            return 2

        red = 0
        for subject, name, find, repl in ARMS:
            path = ROOT / subject
            text = originals[subject].decode()
            if find not in text:
                print(f"  BAD ANCHOR  [{Path(subject).name}] {name}")
                continue
            path.write_text(text.replace(find, repl, 1))
            if hashlib.sha256(path.read_bytes()).hexdigest() == digests[subject]:
                print(f"  NO-OP ARM   [{Path(subject).name}] {name}")
                path.write_bytes(originals[subject])
                continue
            out = _run()
            ok = out != base
            red += ok
            print(f"  {'RED     ' if ok else 'SURVIVED'} "
                  f"[{Path(subject).name}] {name}\n              {out}")
            path.write_bytes(originals[subject])

        print(f"\n{red} RED / {len(ARMS)} arms, {len(ARMS) - red} survived")
        return 0 if red == len(ARMS) else 1
    finally:
        # ⚠️ EVERY subject restored and EVERY restore verified. The sibling
        # battery verifies only its first file's hash, so a failed restore of
        # the second would leave a mutation on disk looking like a real edit.
        bad = []
        for s in subjects:
            (ROOT / s).write_bytes(originals[s])
            if hashlib.sha256((ROOT / s).read_bytes()).hexdigest() != digests[s]:
                bad.append(s)
        if bad:
            print("RESTORE FAILED:", bad)
            raise SystemExit(3)
        SENTINEL.unlink(missing_ok=True)
        print("restore verified by hash for every subject")


if __name__ == "__main__":
    raise SystemExit(main())
