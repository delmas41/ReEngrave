"""Mutation battery for the wedge wiring — every arm, not one.

⚠️⚠️ ONE RED ARM IS NOT A BATTERY. Running a single mutation, seeing red and
stopping is the reassurance that hides the rest: the fermata session measured
FIVE of six surviving behind one that did not. So every arm below is run and
the survivors are named.

⚠️ A BATTERY OF REFUSAL TESTS CAN PASS BY REFUSING EVERYTHING, so the last arm
is a POSITIVE CONTROL in the same class: it mutates the decision to refuse
every input, and the arms asserting acceptance must go red. If that arm
SURVIVES, the accept-side tests are not reaching the code.

⚠️ ANCHOR ON THE WHOLE EXPRESSION, NOT A FRAGMENT. The fermata battery had an
arm mutate a DIFFERENT function because `for h in heads` occurs three times in
`rhythm.py`; every anchor here is asserted UNIQUE in its file before the
substitution is made, and a non-unique anchor is a battery FAILURE rather than
a skipped arm.

    python3 benchmarks/omr-staged-wedge-2026-09/probe/battery.py
"""
from __future__ import annotations

import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
OWN = ROOT / "tools/omr/staged/adjudicators/ownership.py"
EXP = ROOT / "tools/omr/staged/export.py"
LEG = ROOT / "tools/omr/export.py"

TESTS = [
    "tools/omr/tests/test_staged_wedge_anchor.py",
    "tools/omr/tests/test_staged_export.py",
    # ⚠️ THE LEGACY SUITE IS IN THE LIST because the refactor moved the RULE.
    # The fermata battery's two survivors were both "the test list did not
    # include the tests that reach the file it mutates" — a battery whose
    # tests cannot see the mutation measures its own scope, not the code.
    "tools/omr/tests/test_export.py",
]

#: `(name, file, find, replace)`. Each `find` must occur EXACTLY ONCE.
ARMS = [
    # ── the adjudicator ──────────────────────────────────────────────────
    # ⚠️ ANCHORED ON THE `if`, NOT ON THE `Ruling.abstain(` CALL: that call
    # occurs TWICE in this function (the frame refusal and `no_anchor`'s
    # second branch), and a two-match anchor is how the fermata battery
    # silently mutated something else.
    ("the page-frame refusal never fires (cell frame used instead)", OWN,
     '    if not box or len(box) != 4:\n        return Ruling.abstain("no_page_frame",',
     '    if False:\n        return Ruling.abstain("no_page_frame",'),
    ("the wedge box is read as WIDTH not corners", OWN,
     "left, right = float(box[0]), float(box[2])",
     "left, right = float(box[0]), float(box[0]) + float(box[2])"),
    ("the window reaches two bars instead of one", OWN,
     "if abs(int(head_cell.cell) - int(here)) > _WEDGE_WINDOW_CELLS:",
     "if abs(int(head_cell.cell) - int(here)) > _WEDGE_WINDOW_CELLS + 1:"),
    ("ownership is ignored — the cell's own heads anchor it", OWN,
     'if str(staff_key) != str(own):',
     'if False and str(staff_key) != str(own):'),
    # ⚠️ The same two-match hazard: `arc_owner` filters on the identical
    # expression 400 lines up. Anchored on the following line, which is
    # unique to this function.
    ("rests anchor a hairpin as well as noteheads", OWN,
     'if row.detail.get("category") != "notehead":\n            continue\n        hbox = row.detail.get("bbox_page_px")',
     'if row.detail.get("category") not in ("notehead", "rest"):\n            continue\n        hbox = row.detail.get("bbox_page_px")'),
    ("the anchor names the stop twice", OWN,
     'value=[str(start_key), str(stop_key)],',
     'value=[str(stop_key), str(stop_key)],'),
    ("a head with no page box is used anyway", OWN,
     'if not hbox or len(hbox) != 4:\n            continue',
     'if not hbox or len(hbox) != 4:\n            hbox = [0.0, 0.0, 1.0, 1.0]'),

    # ── the emission ─────────────────────────────────────────────────────
    ("the STOP is written before the note, not after", EXP,
     'if _kind == "stop":\n                out.append(_legacy._mxl_wedge(_number, _kind, "      "))',
     'if _kind == "stop":\n                pass'),
    ("the OPENING mark is not written at all", EXP,
     'if _kind != "stop":\n                out.append(_legacy._mxl_wedge(_number, _kind, "      "))',
     'if False:\n                out.append(_legacy._mxl_wedge(_number, _kind, "      "))'),
    ("every hairpin takes number 1", EXP,
     "numbered = _legacy._number_spans(spans, _legacy._MAX_WEDGE_NUMBER)",
     "numbered = [(1, s) for s in spans]"),
    ("the kind check is dropped — any verdict is a hairpin", EXP,
     'if kind not in ("crescendo", "diminuendo"):',
     'if False:'),
    ("a missing anchor note is silently swallowed", EXP,
     'dropped["wedge_anchor_note_not_written"] += 1',
     "pass"),
    # ⚠️ THE TEN, as an arm. This is the bug the first cut shipped: a per-part
    # head index made "not in this part" and "never written" the same
    # condition, and a hairpin with both ends unwritten was counted by nobody.
    ("a hairpin with NEITHER anchor written is swallowed", EXP,
     'dropped["wedge_neither_anchor_written"] += 1',
     "pass"),
    ("the head index sees only the FIRST part", EXP,
     "for pi, part in enumerate(parts):\n        for n, (run, i) in enumerate(_part_cells_in_order(part)):",
     "for pi, part in enumerate(parts[:1]):\n        for n, (run, i) in enumerate(_part_cells_in_order(part)):"),
    ("the counter fires at the ATTACH, not at the render", EXP,
     'counters["wedges"] += 1',
     "pass"),
    # ⚠️ THE PART ORDINAL, MUTATED WHERE IT IS CONSUMED. The first version of
    # this arm mutated `out.append((run, i))` into
    # `out.append((run, i)) if True else None`, which is the SAME PROGRAM — an
    # EQUIVALENT MUTANT, not a coverage gap, and it "survived" for that reason
    # alone. The hazard is the ordinal restarting per system, so the mutation
    # is to key the bar on its cell index instead.
    # ⚠️ THIS ANCHOR WENT STALE WHEN THE HEAD INDEX MOVED and the battery
    # reported `BAD ANCHOR (matches 0)` rather than a green pass — which is
    # the whole reason a zero-match anchor is an error here and not a skip.
    ("the part ordinal is the CELL index (restarts per system)", EXP,
     "heads[str(det['glyph'])] = (det, n, pi)".replace("'", '"'),
     "heads[str(det['glyph'])] = (det, i, pi)".replace("'", '"')),

    # ── the coverage reporting gap ───────────────────────────────────────
    ("CV-read ink is invisible to the headline again", EXP,
     '"ink_rows": n_detected + n_cv,',
     '"ink_rows": n_detected,'),
    ("the non-detector count includes the detector's own rows", EXP,
     'if str(o.get("reader")) not in _DETECTOR_READERS)',
     "if True)"),

    # ── the legacy refactor ──────────────────────────────────────────────
    ("the legacy caller stops passing its voice map", LEG,
     "lambda det: voice_of.get(id(det), 0))",
     "lambda det: 0)"),
    ("the pure core ignores the voice filter", LEG,
     "same_voice = [c for c in candidates if voice_of(c[2]) == voice]",
     "same_voice = list(candidates)"),
]

#: ⚠️ ONE KNOWN EQUIVALENT MUTANT, NAMED RATHER THAN CHASED. Turning the wedge
#: balance's `==` back into `<=` survives, and it is not a coverage gap: once
#: the head index is global, `written + not_written` is ALWAYS exactly
#: `decided`, so the two spellings agree on every input the code can produce.
#: The `==` is kept because it is the guard against a FUTURE regression
#: reintroducing a residue — which is exactly what the `<=` hid for one
#: afternoon — and because an equivalent mutant is a fact about the current
#: code, not a licence to loosen the check. It is deliberately NOT in `ARMS`:
#: an arm that can never go red would be reported as a survivor every run and
#: would train the next reader to ignore the list.
_EQUIVALENT_BY_DESIGN = ("the balance goes back to a tolerant <=", EXP,
                         '+ report["wedges_not_written_total"]) == w_decided,',
                         '+ report["wedges_not_written_total"]) <= w_decided,')

#: ⚠️ THE POSITIVE CONTROL, IN THE SAME CLASS AS THE REFUSAL ARMS. If the
#: accept-side tests do not reach the code, refusing everything survives.
CONTROL = ("POSITIVE CONTROL: the decision refuses every input", OWN,
           "    wedges = ev.rows(Q.WEDGE_BOX)",
           '    return Ruling.abstain("no_evidence")\n'
           "    wedges = ev.rows(Q.WEDGE_BOX)")


def _run() -> bool:
    r = subprocess.run([sys.executable, "-m", "pytest", *TESTS, "-q",
                        "-x", "--no-header", "-p", "no:warnings"],
                       cwd=ROOT, capture_output=True, text=True)
    return r.returncode == 0


def _arm(name, path, find, replace) -> str:
    orig = path.read_text()
    n = orig.count(find)
    if n != 1:
        # ⚠️ NOT A SKIP. An anchor matching zero or many places is a battery
        # DEFECT and is reported as loudly as a survivor, because that is how
        # the fermata battery silently mutated a different function.
        return f"BAD ANCHOR (matches {n})"
    path.write_text(orig.replace(find, replace))
    try:
        green = _run()
    finally:
        path.write_text(orig)
    return "SURVIVED" if green else "red"


def main() -> int:
    print(f"baseline: {'green' if _run() else 'RED — fix the tree first'}\n")
    bad = []
    for name, path, find, replace in ARMS:
        got = _arm(name, path, find, replace)
        print(f"  [{got:12}] {name}")
        if got != "red":
            bad.append(name)
    got = _arm(*CONTROL)
    print(f"\n  [{got:12}] {CONTROL[0]}")
    if got != "red":
        bad.append(CONTROL[0])
    print(f"\n{len(ARMS) + 1} arms, {len(bad)} not red")
    for name in bad:
        print(f"  ⚠️ {name}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
