"""Mutation battery for `tools/omr/factsheet.py`.

Discipline this repo paid for, all of it enforced here rather than described:
a BYTE snapshot taken before the first arm; `PYTHONDONTWRITEBYTECODE=1` in
every subprocess (a `.pyc` written under one arm survives `shutil.copy2`'s
mtime-preserving restore and the NEXT arm then imports UNMUTATED code and
reports NOT RED); every mutation VERIFIED by hash to have changed the file;
an in-flight sentinel so an interrupted run refuses to start again; and the
restore verified by hash at the end.

⚠️ THE JUDGE MAY NOT CONTAIN pytest's OWN ELAPSED TIME. The summary line ends
" in 0.40s", which differs between two runs of an unmutated tree -- a judge
comparing it verbatim scores every arm RED for free. That shape voided two
published batteries in this repo on 2026-09-20.
"""

import hashlib
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SUBJECT = ROOT / "tools/omr/factsheet.py"
SUBJECT2 = ROOT / "tools/omr/staged/gather.py"
TESTS = "tools/omr/tests/test_factsheet.py"
SENTINEL = Path(__file__).resolve().parent / ".mutate-in-flight"

# (name, find, replace) -- each must change the file, and be caught by a test.
ARMS = [
    ("is_leaf always True (containers become facts)",
     "    return not isinstance(f, (dict, list))\n\n\ndef value_of",
     "    return True\n\n\ndef value_of"),
    ("is_leaf always False (nothing is a fact)",
     "    return not isinstance(f, (dict, list))\n\n\ndef value_of",
     "    return False\n\n\ndef value_of"),
    ("is_leaf ignores the declared list-valued paths",
     "    if isinstance(f, list) and path and is_list_valued(path):\n        return True",
     "    if False:\n        return True"),
    ("merge truncates a hand list to the reader's length",
     "            if len(o) != len(n):\n                # \u26a0\ufe0f A HUMAN'S LENGTH WINS.",
     "            if False:\n                # \u26a0\ufe0f A HUMAN'S LENGTH WINS."),
    ("a bare leaf reads as a reader fact, not a hand one",
     '    return "hand"', '    return "reader"'),
    ("None reads as a hand fact",
     '    if f is None:\n        return "unread"',
     '    if f is None:\n        return "hand"'),
    ("merge drops the reader's answer",
     '''                return {"value": o, "source": "hand", "reader_said": nv,
                        "note": "you corrected the machine here"}''',
     '                return o'),
    ("merge lets the machine overwrite a hand fact",
     "        if is_leaf(o, path) and source_of(o) == \"hand\":",
     "        if False:"),
    ("merge calls agreement a disagreement",
     "            if is_machine_fact(n) and source_of(n) != \"unread\" and nv != o:",
     "            if is_machine_fact(n) and source_of(n) != \"unread\":"),
    ("_missing loses multiset awareness",
     "        if pool.get(n):\n            pool[n] -= 1",
     "        if n in pool:\n            pass"),
    ("_missing hides an unmatched staff",
     "    return missing, sorted(k for k, v in pool.items() if v > 0)",
     "    return missing, []"),
    ("a raw label counts as a lexicon name",
     '        return str(s["label"]), "label_only"',
     '        return str(s["label"]), "instrument"'),
    ("suppression is derived even from refused names",
     "        elif not (reliable and here_ok):",
     "        elif False:"),
    ("the canonical lineup ignores how well named a system is",
     "        return sum(1 for s in v if _name_of(s)[1] == \"instrument\")",
     "        return 0"),
    ("the dossier id is guessed when several match",
     "        if len(cands) == 1:", "        if cands:"),
    ("an unknown PDF gets an invented work id",
     '    if e is None:', '    if e is None and False:'),
    ("the gate admits an UNCONFIRMED dossier",
     '            return value_of(v) if source_of(v) == "hand" else None',
     '            return value_of(v)'),
    ("the per-system seed collapses to one index-keyed dict (the graft)",
     '        per_system = clefs.get(f"p{c.page_index}/s{key[0]}") or {}\n        value = per_system.get(key[1]) or per_system.get(str(key[1]))',
     '        value = clefs.get(key[1]) or clefs.get(str(key[1]))'),
    ("a system whose suppression list is unconfirmed is seeded anyway",
     "        if sup is None:\n            skipped += 1\n            continue",
     "        if sup is None:\n            sup = []"),
    ("the two independent staff counts need not reconcile",
     "        if n_read is not None and len(present) != n_read:",
     "        if False:"),
    ("a staff whose parts disagree takes one of them anyway",
     "        return cl.pop() if len(cl) == 1 else None",
     "        return cl.pop() if cl else None"),
    ("the join is drafted by NAME on a condensed page",
     "    if n_parts and n_parts == widest:",
     "    if n_parts:"),
    ("_present_indices ignores a name that is in no slot",
     "    return None if any(v > 0 for v in want.values()) else out",
     "    return out"),
    ("walk counts metadata as facts",
     '            if k.startswith("_") or k in META:',
     '            if k.startswith("_") and False:'),
]


def _run() -> str:
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    p = subprocess.run([sys.executable, "-m", "pytest", TESTS, "-q"],
                       cwd=ROOT, env=env, capture_output=True, text=True)
    tail = (p.stdout or "") + (p.stderr or "")
    # ⚠️ strip the elapsed time; see the module docstring.
    m = re.search(r"^(\d+ (?:passed|failed).*?)(?: in [\d.]+s)?$",
                  tail.strip().splitlines()[-1] if tail.strip() else "", re.M)
    for line in reversed(tail.strip().splitlines()):
        if "passed" in line or "failed" in line or "error" in line:
            return re.sub(r"\s+in\s+[\d.]+s.*$", "", line).strip()
    return "NO SUMMARY"


def main() -> int:
    if SENTINEL.exists():
        print("REFUSING: an earlier battery did not finish. %s should hash %s"
              % (SUBJECT, SENTINEL.read_text().strip()))
        return 2
    original = SUBJECT.read_bytes()
    digest = hashlib.sha256(original).hexdigest()
    SENTINEL.write_text(digest + "\n")
    try:
        base = _run()
        print(f"BASE (unmutated): {base}")
        if "failed" in base or "error" in base:
            print("REFUSING: the base is not green.")
            return 2
        red = 0
        original2 = SUBJECT2.read_bytes()
        digest2 = hashlib.sha256(original2).hexdigest()
        for name, find, repl in ARMS:
            which = SUBJECT2 if "per-system seed collapses" in name else SUBJECT
            base_bytes = original2 if which is SUBJECT2 else original
            text = base_bytes.decode()
            if find not in text:
                print(f"  BAD ANCHOR  {name}")
                continue
            mutated = text.replace(find, repl, 1)
            assert mutated != text
            which.write_text(mutated)
            assert hashlib.sha256(which.read_bytes()).hexdigest() != (
                digest2 if which is SUBJECT2 else digest), \
                "mutation did not change the file"
            out = _run()
            ok = out != base
            red += ok
            print(f"  {'RED ' if ok else 'SURVIVED'}  {name}\n            {out}")
            which.write_bytes(base_bytes)
        print(f"\n{red} RED / {len(ARMS)} arms, {len(ARMS) - red} survived")
        return 0 if red == len(ARMS) else 1
    finally:
        SUBJECT.write_bytes(original)
        SUBJECT2.write_bytes(SUBJECT2.read_bytes() if 'original2' not in dir()
                             else original2)
        assert hashlib.sha256(SUBJECT.read_bytes()).hexdigest() == digest, \
            "RESTORE FAILED"
        SENTINEL.unlink(missing_ok=True)
        print("restore verified by hash")


if __name__ == "__main__":
    raise SystemExit(main())
