#!/usr/bin/env python3
"""Mutation battery over this lane's probes.

⚠️⚠️ FOUR PROPHYLACTICS, EVERY ONE PAID FOR ELSEWHERE IN THIS REPO:

1. **`PYTHONDONTWRITEBYTECODE=1` in every arm's subprocess environment.**
   `shutil.copy2` preserves mtime, so a `.pyc` written during one arm still
   satisfies Python's `(mtime, size)` validity check during a later one and
   that arm imports the UNMUTATED code and reports NOT RED. Two published
   batteries were voided by this.
2. **pytest's own elapsed time is stripped from the judge.** The summary line
   ends `" in 0.57s"`, which differs between two runs of an unmutated tree --
   so a verbatim comparison scores every arm RED for free. Two more published
   batteries were voided by that, and one of them is the file this one is
   written against.
3. **A byte snapshot and an in-flight SENTINEL.** A battery killed mid-arm
   leaves the mutation on disk and `git status` shows one modified file,
   indistinguishable from a legitimate edit. A run that finds a sentinel
   refuses to start and names each file at risk with the hash it should have.
4. **Each mutation is VERIFIED BY HASH to have changed the file.** An anchor
   that matches and a write that succeeds are not evidence that anything
   moved.

⚠️ AND A POSITIVE CONTROL IN THE SAME CLASS: `everything_refuses` must be RED
too, because a battery of refusal tests passes by refusing everything.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

BENCH = Path(__file__).resolve().parent
PROBE = BENCH / "probe"
TESTS = BENCH / "test_probes.py"
SENTINEL = BENCH / ".mutation-in-flight.json"

#: (name, file, anchor, replacement)
ARMS = [
    # ── common.py: the predicates ────────────────────────────────────────────
    ("x_overlap_becomes_strict", "common.py",
     'return _boxes_overlap((a[0], 0.0, a[2], 1.0), (b[0], 0.0, b[2], 1.0))',
     'return a[0] < b[0] + b[2] and a[0] + a[2] > b[0]'),
    ("x_overlap_ignores_width", "common.py",
     'return _boxes_overlap((a[0], 0.0, a[2], 1.0), (b[0], 0.0, b[2], 1.0))',
     'return abs(a[0] - b[0]) < 1e-9'),
    ("y_overlap_becomes_strict", "common.py",
     'return _boxes_overlap((0.0, a[1], 1.0, a[3]), (0.0, b[1], 1.0, b[3]))',
     'return a[1] < b[1] + b[3] and a[1] + a[3] > b[1]'),
    ("y_overlap_always_true", "common.py",
     'return _boxes_overlap((0.0, a[1], 1.0, a[3]), (0.0, b[1], 1.0, b[3]))',
     'return True'),
    ("cell_of_keeps_the_glyph_ordinal", "common.py",
     'return "cell/" + "/".join(parts[1:5])',
     'return "cell/" + "/".join(parts[1:6])'),
    ("cell_of_never_abstains", "common.py",
     '    return ""',
     '    return subject'),
    # ── reach.py: the rule under test ────────────────────────────────────────
    ("reach_drops_the_own_stroke_guard", "reach.py",
     '        if _stems_on(hb, stems_c):\n            continue',
     '        if False:\n            continue'),
    ("reach_drops_the_y_span_condition", "reach.py",
     '            if not y_overlap(hb, sb):\n                continue',
     '            if False:\n                continue'),
    ("reach_drops_the_x_alignment_condition", "reach.py",
     '                     and x_overlap(hb, o.value)]',
     '                     ]'),
    ("reach_drops_the_joined_mate_requirement", "reach.py",
     '            mates = [o for o in heads_c\n'
     '                     if o is not h and _boxes_overlap(o.value, sb)\n'
     '                     and x_overlap(hb, o.value)]',
     '            mates = [o for o in heads_c\n'
     '                     if o is not h and x_overlap(hb, o.value)]'),
    # ⚠️ `reach_lets_a_head_be_its_own_mate` (deleting `o is not h`) is an
    # EQUIVALENT MUTANT and is NAMED here rather than run: the loop is only
    # reached when `_stems_on(hb, stems_c)` is empty, so `h` cannot overlap
    # `sb` and can never be selected as its own mate. An arm that can never go
    # red trains the next reader to skim the list.
    # ── decompose.py: the sibling's restated windows ─────────────────────────
    ("decompose_forgets_the_stemless_column", "decompose.py",
     '                    "shadow_is_stemless": not _stems_on(b2, stems_c),',
     '                    "shadow_is_stemless": True,'),
    ("decompose_admits_a_multi_head_stroke", "decompose.py",
     '        if len(members) != 1:\n            continue',
     '        if len(members) < 1:\n            continue'),
    ("decompose_widens_the_x_window", "decompose.py",
     '            if (abs(cx2 - hcx) <= max(hb[2], b2[2])',
     '            if (abs(cx2 - hcx) <= 4 * max(hb[2], b2[2])'),
    ("decompose_drops_the_y_window", "decompose.py",
     '                    and sb[1] - hh <= cy2 <= sb[1] + sb[3] + hh):',
     '                    and True):'),
    # ── flip.py ──────────────────────────────────────────────────────────────
    ("flip_direction_ignores_the_group", "flip.py",
     '    return _legacy._stem_direction(_Shim(*stroke), [_Shim(*b) for b in boxes])',
     '    return "up"'),
    ("flip_extra_members_ignores_its_own_stroke", "flip.py",
     '        if _stems_on(h.value, stems_c):\n            continue',
     '        if False:\n            continue'),
    ("flip_extra_members_needs_no_joined_head", "flip.py",
     '    if not joined:\n        return []',
     '    if False:\n        return []'),
    # ── score.py: the instrument that reports the result ─────────────────────
    ("score_takes_the_stratum_from_the_adjudication", "score.py",
     '        if tid in stratum:\n            out[stratum[tid]][rec["verdict"]] += 1',
     '        out["CANDIDATE"][rec["verdict"]] += 1'),
    ("score_stops_reporting_unadjudicated_tiles", "score.py",
     '    missing = sorted(set(stratum) - set(v))',
     '    missing = []'),
    ("score_stops_reporting_unknown_tiles", "score.py",
     '    extra = sorted(set(v) - set(stratum))',
     '    extra = []'),
    ("score_counts_cannot_tell_as_settled", "score.py",
     '    settled = sum(v for k, v in cand.items() if k != "cannot_tell")',
     '    settled = sum(cand.values())'),
    ("score_counts_a_non_notehead_as_a_chord", "score.py",
     '    not_head = sum(cand[k] for k in NOT_A_HEAD if k in cand)',
     '    not_head = 0'),
    ("score_check_ignores_a_wrong_control", "score.py",
     '        if report["POOLED"]["controls_WRONG"]:',
     '        if False:'),
    ("score_check_ignores_a_dead_control_set", "score.py",
     '        if report["POOLED"]["controls_correct"] == 0:',
     '        if False:'),
    # ── the positive control, in the same class ──────────────────────────────
    ("POSITIVE_CONTROL_everything_refuses", "score.py",
     '    report, problems = {}, []',
     '    report, problems = {}, ["forced"]'),
]


def _hash(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _targets():
    return sorted({PROBE / f for _n, f, _a, _r in ARMS} | {TESTS})


def _snapshot(d: Path):
    shot = {}
    for p in _targets():
        dst = d / p.name
        shutil.copy2(p, dst)          # mtime preserved -- see the docstring
        shot[str(p)] = _hash(p)
    return shot


def _restore(d: Path, shot):
    bad = []
    for p in _targets():
        shutil.copy2(d / p.name, p)
        if _hash(p) != shot[str(p)]:
            bad.append(str(p))
    return bad


def _run_tests():
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"      # prophylactic 1
    r = subprocess.run(
        [sys.executable, "-B", "-m", "pytest", str(TESTS), "-q",
         "-p", "no:cacheprovider"],
        capture_output=True, text=True, cwd=str(BENCH.parents[1]), env=env)
    out = r.stdout + r.stderr
    # prophylactic 2: strip pytest's own elapsed time before judging
    out = re.sub(r"\bin \d+\.\d+s\b", "in <T>", out)
    tail = [ln for ln in out.splitlines()
            if "passed" in ln or "failed" in ln or "error" in ln]
    return r.returncode, (tail[-1] if tail else out.strip()[-200:])


def main() -> int:
    if SENTINEL.exists():
        print("⚠️ AN EARLIER BATTERY DID NOT FINISH. The tree may still carry "
              "a mutation. Each file and the hash it should have:")
        print(SENTINEL.read_text())
        return 2

    base_rc, base_line = _run_tests()
    if base_rc != 0:
        print(f"⚠️ the suite is not green before any arm: {base_line}")
        return 2
    print(f"BASE  {base_line}")

    with tempfile.TemporaryDirectory() as d:
        snap = Path(d)
        shot = _snapshot(snap)
        SENTINEL.write_text(json.dumps(shot, indent=1))
        try:
            red, survived, broken = 0, [], []
            for name, fname, anchor, repl in ARMS:
                p = PROBE / fname
                src = p.read_text()
                if src.count(anchor) != 1:
                    broken.append(
                        f"{name}: anchor occurs {src.count(anchor)}x in {fname}")
                    continue
                before = _hash(p)
                p.write_text(src.replace(anchor, repl, 1))
                if _hash(p) == before:          # prophylactic 4
                    broken.append(f"{name}: the write changed nothing")
                    _restore(snap, shot)
                    continue
                rc, line = _run_tests()
                _restore(snap, shot)
                if rc != 0:
                    red += 1
                    print(f"RED   {name}  ({line})")
                else:
                    survived.append(name)
                    print(f"⚠️ SURVIVED {name}  ({line})")
            bad = _restore(snap, shot)          # prophylactic 3
        finally:
            SENTINEL.unlink(missing_ok=True)

    print(f"\n{red} RED / {len(ARMS)} arms, {len(survived)} survived, "
          f"{len(broken)} could not be applied")
    for b in broken:
        print(f"  BAD ANCHOR {b}")
    for s in survived:
        print(f"  SURVIVOR {s}")
    if bad:
        print(f"⚠️⚠️ RESTORE FAILED for {bad}")
        return 2
    print("restore verified by hash")
    return 0 if (not survived and not broken) else 1


if __name__ == "__main__":
    raise SystemExit(main())
