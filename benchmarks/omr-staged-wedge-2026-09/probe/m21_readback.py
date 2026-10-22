"""Does a staged `<wedge>` survive a round trip through music21?

⚠️ THE COUNT IS NOT THE POINT; THE PAIRING IS. music21 attaches a `crescendo`
to the next note it PARSES and a `stop` to the last note it parsed, so a file
whose element ORDER is wrong still contains the right number of `<wedge>`
elements and spans the WRONG NOTES. A count-only check cannot see that, which
is the same shape as the arc export's corner-vs-width mutation surviving every
assertion — only NAMING THE NOTES catches it.

So this writes a file whose two hairpins deliberately OVERLAP and span known,
different note pairs, and asserts which notes music21 says each one binds.

    python3 benchmarks/omr-staged-wedge-2026-09/probe/m21_readback.py
    .venv-omrned/bin/python benchmarks/omr-staged-wedge-2026-09/probe/m21_readback.py --read /tmp/wedge/m21probe.musicxml
"""
from __future__ import annotations

import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve()


def _obs(i, sub, q, val, **d):
    return {"id": f"obs:{i:06d}", "subject": sub, "quantity": q, "value": val,
            "reader": "detector", "frame": "cell:0", "score": 0.9,
            "detail": d, "basis": []}


def _vrd(i, sub, q, val, outcome="decided", reason="x", detail=None):
    return {"id": f"vrd:{i:06d}", "subject": sub, "quantity": q,
            "outcome": outcome, "value": val, "decider": "t", "reason": reason,
            "considered": [], "used": [], "missing": [], "declined": [],
            "excluded": [], "correlated": [], "candidates": [], "basis": [],
            "margin": None, "supersedes": None, "detail": detail or {}}


def build_page(Q):
    obs, vrd, n = [], [], 0
    for gi in range(4):
        sub = f"glyph/0/0/0/0/{gi}"
        obs.append(_obs(n, sub, Q.GLYPH_BOX,
                        ["noteheadBlackOnLine", 100 * gi, 50, 40, 40],
                        category="notehead"))
        n += 1
        obs.append(_obs(n, sub, Q.NOTEHEAD_CLASS, "noteheadBlackOnLine"))
        n += 1
        vrd.append(_vrd(n, sub, Q.PITCH, "CDEF"[gi] + "4"))
        n += 1
        vrd.append(_vrd(n, sub, Q.DURATION,
                        {"beats": 1.0, "written": 1.0, "dots": 0}))
        n += 1
    vrd.append(_vrd(900, "staff/0/0/0", Q.MEASURE_PARTITION, 1))
    vrd.append(_vrd(901, "staff/0/0/0", Q.CLEF, "treble"))
    vrd.append(_vrd(902, "system/0/0", Q.SYSTEM_STAFF_COUNT, 1))
    vrd.append(_vrd(903, "document", Q.PART_PARTITION,
                    {"join": "ordinal", "staves_per_system": 1},
                    reason="ordinal"))
    # ⚠️ OVERLAPPING ON PURPOSE: C->E crescendo and D->F diminuendo. They need
    # two `number=` levels, and each must bind the pair NAMED here.
    plan = [(0, 2, "crescendo", 5.0, 205.0),
            (1, 3, "diminuendo", 105.0, 305.0)]
    for k, (a, b, kind, x0, x1) in enumerate(plan):
        sub = f"glyph/0/0/0/0/{90 + k}"
        obs.append(_obs(500 + k, sub, Q.WEDGE_BOX, kind,
                        bbox_page_px=[x0, 160.0, x1, 168.0]))
        vrd.append(_vrd(950 + k, sub, Q.WEDGE_ANCHOR,
                        [f"glyph/0/0/0/0/{a}", f"glyph/0/0/0/0/{b}"],
                        reason="nearest_either_side",
                        detail={"kind": kind, "start_cell": 0, "stop_cell": 0,
                                "start_x_page": x0, "stop_x_page": x1}))
    return {"record": {"observations": obs, "verdicts": vrd,
                       "abstentions": [], "counts": {}}, "summary": {}}


def write(out: str) -> int:
    sys.path.insert(0, str(HERE.parents[3]))
    from tools.omr.staged import export as SX
    from tools.omr.staged.record import Q

    xml, report = SX.to_musicxml(build_page(Q))
    pathlib.Path(out).write_text(xml)
    print(f"wedges written : {report['written']['wedges']}")
    print(f"balance        : {json.dumps(report['wedge_balance'])}")
    print(f"wrote {out}")
    return 0


def read(path: str) -> int:
    """⚠️ RUN THIS UNDER `.venv-omrned/bin/python`, never the host 3.9."""
    from music21 import converter, dynamics

    score = converter.parse(path)
    wedges = list(score.recurse().getElementsByClass(dynamics.DynamicWedge))
    print(f"music21 read back: {len(wedges)} DynamicWedge")
    ok = True
    want = {"Crescendo": ("C", "E"), "Diminuendo": ("D", "F")}
    for w in wedges:
        notes = [n for n in w.getSpannedElements()]
        names = tuple(getattr(n.pitch, "name", "?") for n in notes)
        kind = type(w).__name__
        print(f"  {kind:12} binds {names}")
        if kind in want and names != want[kind]:
            print(f"    ⚠️ EXPECTED {want[kind]} — the element ORDER is wrong, "
                  "and the COUNT above would not have said so")
            ok = False
    return 0 if ok and len(wedges) == 2 else 1


if __name__ == "__main__":
    if "--read" in sys.argv:
        raise SystemExit(read(sys.argv[sys.argv.index("--read") + 1]))
    raise SystemExit(write(sys.argv[1] if len(sys.argv) > 1
                           else "/tmp/wedge/m21probe.musicxml"))
