"""Mutation battery for S4 and S6 in `adjudicate_arc_kind`.

⚠️ ONE RED ARM IS NOT A BATTERY — this repo measured five of six arms
surviving behind one that did not. Every arm is applied to a SNAPSHOT of the
tree, never to the working copy: *a battery that `git checkout`s the files it
mutates is not isolated from anything else running beside it*, which cost a
sibling session its first three-arm run, and a later one its first A/B.

⚠️⚠️ THE BATTERY'S OWN HAZARD IS THE POINT OF ARM 0. Almost every test here
asserts that a witness is RECORDED AND CHANGES NOTHING, and a suite of those
can pass by recording nothing and changing nothing. Arm 0 is the positive
control in the same class: it PROMOTES S4 to a gate, which is precisely the
thing this job declined to do, and `test_it_changes_NO_verdict` must go red.
Arm 1 is its mirror for S6.

⚠️ A MISSING OR AMBIGUOUS ANCHOR IS AN ERROR, NEVER A PASS. `Ruling.abstain(`
occurs TWICE in `ownership.py` and the fermata battery silently mutated a
different function for exactly that reason, so every arm asserts its anchor
occurs EXACTLY ONCE and says so when it does not.
"""
from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
TESTS = "tools/omr/tests/test_staged_arc_kind.py"
OWN = "tools/omr/staged/adjudicators/ownership.py"

ARMS = [
    # ── positive controls: make the witnesses ACT, which they must not ──────
    ("0 POSITIVE CONTROL: S4 promoted to a GATE (the refused thing)",
     'grammar["s4_stem_position"] = s4',
     'grammar["s4_stem_position"] = s4\n        if s4["any_endpoint_on_a_stem"] and s4["t_median"] > 0.5:\n            kind = "slur"'),
    ("1 POSITIVE CONTROL: S6 promoted to a GATE",
     'grammar["s6_stacked_with"] = s6',
     'grammar["s6_stacked_with"] = s6\n        if any(r["y_gap"] > 0 for r in s6):\n            kind = "slur" if s6[0]["this_is_upper"] else "tie"'),

    # ── S4 ──────────────────────────────────────────────────────────────────
    ("2 S4: the arc's FAR edge stands in for its near edge",
     "near_edge = ay1 if above else ay0",
     "near_edge = ay0 if above else ay1"),
    ("3 S4: the stem's head end and far end are swapped",
     "((sy, sy1) if abs(sy - h_yc) < abs(sy1 - h_yc)\n                                 else (sy1, sy))",
     "((sy1, sy) if abs(sy - h_yc) < abs(sy1 - h_yc)\n                                 else (sy, sy1))"),
    ("4 S4: `same_side` is always true (an arc off the stem counts)",
     "same_side=bool(above == (far_end < head_end)),",
     "same_side=True,"),
    ("5 S4: every stem in the cell attaches to every head",
     "for sx, sy, sw, sh in [s for s in stems\n                               if _boxes_overlap(s, head_box)]:",
     "for sx, sy, sw, sh in list(stems):"),
    ("6 S4: `t` is a PIXEL offset, not a fraction of the stem",
     "t=round((near_edge - head_end) / span, 4),",
     "t=round(near_edge - head_end, 4),"),
    ("7 S4: it reads only the FIRST flanked head, never the last",
     "for (_xc, head_box, h_yc, _step), ex in ((heads[0], ax0), (heads[-1], ax1)):",
     "for (_xc, head_box, h_yc, _step), ex in ((heads[0], ax0),):"),

    # ── S6 ──────────────────────────────────────────────────────────────────
    ("8 S6: upper and lower are swapped",
     "this_is_upper=bool((ay0 + ay1) < (by0 + by1))",
     "this_is_upper=bool((ay0 + ay1) > (by0 + by1))"),
    ("9 S6: the y-gap's sign is flipped",
     "y_gap=round(-oy, 2),",
     "y_gap=round(oy, 2),"),
    ("10 S6: duplicates are silently dropped instead of recorded",
     "        out.append(dict(\n            other=sid,",
     "        if oy > 0:\n            continue\n        out.append(dict(\n            other=sid,"),
    ("11 S6: an arc with NO x-overlap is still called a sibling",
     "        if ox <= 0:\n            continue",
     "        ox = max(ox, 1.0)"),
    ("12 S6: the x-overlap fraction is taken over the WIDER arc",
     "x_overlap_frac=round(ox / max(1.0, min(ax1 - ax0, bx1 - bx0)), 4),",
     "x_overlap_frac=round(ox / max(1.0, max(ax1 - ax0, bx1 - bx0)), 4),"),
    ("13 S6: an arc is recorded as its own sibling",
     "        if sid == arc_id:\n            continue",
     "        pass"),

    # ── S4's WIDENED quantity (2026-09-15) ──────────────────────────────────
    ("15 t_axis measured from the stem's head END, not the head CENTRE",
     "axis_span = far_end - h_yc",
     "axis_span = far_end - head_end"),
    ("16 t_axis is an alias of t (the widening silently undone)",
     "t_axis=(round((near_edge - h_yc) / axis_span, 4)",
     "t_axis=(round((near_edge - head_end) / span, 4)"),
    ("17 t_axis runs to the stem's HEAD end instead of its TIP",
     "            axis_span = far_end - h_yc",
     "            axis_span = head_end - h_yc"),

    # ── the seam: the declaration that makes the read legal at all ──────────
    ("14 Q.STEM is not declared, so `Evidence` must refuse the read",
     "    wants=(Q.ARC_BOX, Q.NOTEHEAD_STAFF_POSITION, Q.GLYPH_BOX, Q.STEM),",
     "    wants=(Q.ARC_BOX, Q.NOTEHEAD_STAFF_POSITION, Q.GLYPH_BOX),"),
]


def run_arm(name: str, a: str, b: str) -> str:
    tmp = pathlib.Path(tempfile.mkdtemp())
    try:
        shutil.copytree(ROOT / "tools", tmp / "tools",
                        ignore=shutil.ignore_patterns("training", "annotate",
                                                      "symbol_library", "*.pt"),
                        dirs_exist_ok=True)
        p = tmp / OWN
        s = p.read_text()
        if s.count(a) != 1:
            return f"BAD ANCHOR ({s.count(a)} matches)  {name}"
        p.write_text(s.replace(a, b))
        out = subprocess.run(
            [sys.executable, "-m", "pytest", TESTS, "-q"],
            cwd=tmp, capture_output=True, text=True,
            env={"PYTHONPATH": ".", "PATH": "/usr/bin:/bin:/usr/local/bin",
                 "HOME": str(pathlib.Path.home())})
        tail = (out.stdout or "") + (out.stderr or "")
        return ("RED       " if "failed" in tail or "error" in tail.lower()
                else "SURVIVED  <-- A GAP  ") + name
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    for arm in ARMS:
        print(run_arm(*arm), flush=True)
