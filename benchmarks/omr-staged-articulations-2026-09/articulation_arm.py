"""Do articulations reach the file — ONE gather, ADJUDICATED TWICE.

⚠️ THIS IS THE ADJUDICATE-ONLY CASE, and knowing that is what picks the
instrument. `adjudicate_articulation_owner` reads `Q.ARTICULATION_MARK` and
`Q.GLYPH_BOX`, both of which GATHER already emitted, so a saved record already
contains everything the new rule needs and re-adjudicating it is a real A/B.
The arc export was NOT this case — it added `Q.CELL_BOX`, a GATHER change, and
`readjudicate` is structurally blind to those. Check which case you are in
before reaching for either instrument.

⚠️ IT VERIFIES THE REBUILD FIRST, by delegating to the instrument that owns
that check: `readjudicate.py --control` re-adjudicates with nothing disabled
and compares every duration verdict against the pipeline's own. On the record
this shipped with it reads 1863 of 1863. A rebuild that does not reproduce the
record is not a control.

⚠️ REACH BEFORE ACCURACY. This prints how many articulation marks the document
HOLDS before it prints what moved, because a change that moves nothing because
it is inert and one that moves nothing because the page holds nothing to move
are the same number.

    python3 articulation_arm.py <staged.json>
"""
from __future__ import annotations

import collections
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]
                       / "omr-staged-duration-beams-2026-09"))

from readjudicate import rebuild                              # noqa: E402
from tools.omr.staged import adjudicate, evaluate             # noqa: E402
from tools.omr.staged import adjudicators, consequences       # noqa: E402,F401
from tools.omr.staged import export as SX                     # noqa: E402
from tools.omr.staged.adjudicate import Ruling                # noqa: E402
from tools.omr.staged.adjudicators import ownership as OWN    # noqa: E402
from tools.omr.staged.record import ABSTAIN, Q                # noqa: E402


def _arm(record: dict, *, stubbed: bool) -> dict:
    """Re-adjudicate the saved gather, optionally with the rule STUBBED OUT.

    ⚠️ BOTH ARMS ARE RE-ADJUDICATED. Using the record's SAVED verdicts as the
    off arm would compare a rebuild against a pipeline run, so any difference
    between those two would be billed to this rule.
    """
    # ⚠️ The registry entry is a FROZEN dataclass, so the arm swaps the
    # module-level function the spec was built from and rebuilds the entry,
    # rather than mutating it in place.
    import dataclasses
    spec = adjudicate.REGISTRY[Q.ARTICULATION_OWNER]
    if stubbed:
        adjudicate.REGISTRY[Q.ARTICULATION_OWNER] = dataclasses.replace(
            spec, fn=lambda ev: Ruling.abstain(ABSTAIN.NOT_IMPLEMENTED))
    try:
        log = rebuild(record)
        adjudicate.run(log)
        evaluate.run(log)
        xml, rep = SX.to_musicxml({"record": log.to_json()})
        return xml, rep, log.to_json()
    finally:
        adjudicate.REGISTRY[Q.ARTICULATION_OWNER] = spec


def main(argv) -> int:
    doc = json.load(open(argv[1]))
    rec = doc["record"] if "record" in doc else doc

    marks = [o for o in rec["observations"]
             if o["quantity"] == Q.ARTICULATION_MARK]
    print(f"REACH: {len(marks)} articulation marks in the record")
    print("       classes: " + ", ".join(
        f"{k} x{v}" for k, v in
        collections.Counter(str(m["value"]) for m in marks).most_common()))
    sides = collections.Counter(str((m.get("detail") or {}).get("side"))
                                for m in marks)
    print(f"       declared sides: {dict(sides)}")
    if not marks:
        print("       ⚠️ this document prints none -- nothing below can move, "
              "and a zero here is NOT a result about the rule")
        return 0

    on_xml, on_rep, on_json = _arm(rec, stubbed=False)
    off_xml, off_rep, _off_json = _arm(rec, stubbed=True)

    print(f"\nON : <articulations> {on_xml.count('<articulations>')}  "
          f"written {on_rep['written'].get('articulations', 0)}")
    print(f"     not written: {on_rep['articulations_not_written']}")
    print(f"     balance: {on_rep['articulation_balance']}")
    print(f"OFF: <articulations> {off_xml.count('<articulations>')}  "
          f"written {off_rep['written'].get('articulations', 0)}")

    # ⚠️ THE CONTROL THE ARC EXPORT USED: outside the elements under test the
    # two files must be IDENTICAL. A rule that quietly moved a note would
    # otherwise be invisible behind a plausible articulation count.
    def _strip(xml: str) -> str:
        out, skip = [], False
        for line in xml.splitlines():
            t = line.strip()
            if t.startswith("<articulations>"):
                skip = True
            if not skip:
                out.append(line)
            if t.startswith("</articulations>"):
                skip = False
        return "\n".join(out)

    same = _strip(on_xml) == _strip(off_xml)
    print(f"\noutside the <articulations> blocks, the two files are "
          f"{'IDENTICAL' if same else '⚠️ DIFFERENT'}")
    for fam in ("notes", "rests", "slurs", "ties", "dynamics"):
        a, b = on_rep["written"].get(fam, 0), off_rep["written"].get(fam, 0)
        flag = "" if a == b else "   ⚠️ MOVED"
        print(f"  {fam:<10} ON {a:>5} vs OFF {b:>5}{flag}")

    # ⚠️⚠️ IS THE ENGRAVED CONSTANT VALID ON A SCAN? The same question the arc
    # split had to ask of `_SLUR_ARC_PAD_NOTEHEADS`, and there the answer was
    # NO: its plateau was read off an engraved page and does not exist on a
    # scan. `_ARTIC_MAX_DX_NOTEHEAD_WIDTHS` was swept over eight ENGRAVED works
    # too (0.50-2.50 identical, cliff at 0.30). This prints the distance of
    # every ATTACHED mark from its notehead, in the constant's own unit, so a
    # reader can see whether the population clusters well inside the limit --
    # which is what a plateau looks like from the inside -- or crowds its edge.
    dxs = sorted(
        round(float(d), 3) for d in (
            (v.get("detail") or {}).get("dx_notehead_widths")
            for v in on_json["verdicts"]
            if v["quantity"] == Q.ARTICULATION_OWNER
            and v["outcome"] == "decided")
        if d is not None)
    if dxs:
        print(f"\ndx from the owning notehead, in NOTEHEAD WIDTHS "
              f"(limit {OWN._legacy_articulation._ARTIC_MAX_DX_NOTEHEAD_WIDTHS}):")
        print(f"  n={len(dxs)}  min {dxs[0]}  median {dxs[len(dxs)//2]}  "
              f"max {dxs[-1]}")
        print(f"  all: {dxs}")

    kinds = collections.Counter()
    for line in on_xml.splitlines():
        t = line.strip()
        if t.startswith("<") and t.endswith("/>") and t[1:-2] in (
                "staccato", "staccatissimo", "accent", "strong-accent",
                "tenuto"):
            kinds[t[1:-2]] += 1
    print(f"\nkinds written: {dict(kinds)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
