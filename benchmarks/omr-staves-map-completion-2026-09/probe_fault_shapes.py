"""WHICH bar trips each `page_normalise` fault, and what is special about it?

An exception type is not a diagnosis. Both faults are reported here with the
staff, the measure and the property of that bar that no already-mapped row has,
so the claim "this is a transform gap, not a bad map" is checkable.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
MAIN = Path("/Users/seanjohnson/Desktop/ReEngrave")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "benchmarks" / "omr-scan-e2e-2026-09"))
sys.path.insert(0, str(HERE))

import page_normalise as pn                      # noqa: E402
import candidate_maps                            # noqa: E402
from music21 import chord, converter, note, stream   # noqa: E402

REC = (MAIN / ".claude/worktrees/reconciliation/benchmarks"
       "/omr-scan-e2e-2026-09/fixtures")


def bar_facts(m):
    voices = list(m.getElementsByClass(stream.Voice))
    unpitched = [el for el in m.recurse().notesAndRests
                 if not isinstance(el, (note.Note, note.Rest, chord.Chord))]
    return {
        "n_voices": len(voices),
        "n_unpitched": len(unpitched),
        "n_events": len(list(m.recurse().notesAndRests)),
    }


def main() -> int:
    out = []
    for rid in ("mahler-sym5-mvt1-local-p3", "mahler-sym5-mvt1-local-p4",
                "mahler-sym5-mvt1-local-p5", "mahler-sym5-mvt1-local-p2"):
        truth = REC / f"{rid}.truth.musicxml"
        sc = converter.parse(str(truth))
        parts = list(sc.parts)
        for spec in candidate_maps.flat(rid):
            idx = spec["parts"]
            if len(idx) < 2:
                continue
            keep = parts[idx[0]]
            others = [parts[i] for i in idx[1:]]
            for m in keep.getElementsByClass(stream.Measure):
                bars = [m] + [p.measure(m.number) for p in others]
                bars = [b for b in bars if b is not None]
                try:
                    kind = pn.classify(bars)
                except Exception as exc:                 # noqa: BLE001
                    out.append({"row": rid, "staff": spec["name"],
                                "measure": m.number, "stage": "classify",
                                "error": f"{type(exc).__name__}: {exc}",
                                "bars": [bar_facts(b) for b in bars]})
                    continue
                if kind != "divisi":
                    continue
                if pn._aligned(bars):
                    continue
                try:
                    pn._voice_merge(bars)
                except Exception as exc:                 # noqa: BLE001
                    out.append({"row": rid, "staff": spec["name"],
                                "measure": m.number, "stage": "_voice_merge",
                                "error": f"{type(exc).__name__}: {exc}",
                                "bars": [bar_facts(b) for b in bars]})
                else:
                    out.append({"row": rid, "staff": spec["name"],
                                "measure": m.number, "stage": "_voice_merge",
                                "error": None,
                                "bars": [bar_facts(b) for b in bars]})
    for rec in out:
        print(json.dumps(rec, ensure_ascii=False))
    (HERE / "fault-shapes.json").write_text(
        json.dumps({"faults": out}, indent=1, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
