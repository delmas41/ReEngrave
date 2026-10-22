"""WHO is naming the C clefs the gatherer drops -- and does it ever DISAGREE
with the dropped class name?

The starved-staff control refuted the brief's premise: the nine staves whose
C clef `_CLEF_CLASSES` drops all carry a DECIDED clef verdict anyway. So the
question stops being "does a staff lose its clef" and becomes the two that
actually decide whether to wire this:

  1. WHICH reader is carrying those staves alone today?
  2. Where the dropped class name and the standing verdict DISAGREE, wiring
     the detector in at W_DETECTOR_HIGH (3.0) would OVERTURN the reader that
     is right today -- that is the COST, and it must be counted before the
     benefit.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "benchmarks" / "omr-ledger-extrapolation-2026-09"))

from recordstream import stream_array                       # noqa: E402
from clef_reach import measure                              # noqa: E402
from tools.omr.clef_geometry import clef_name_from_class    # noqa: E402

DOCS = {
    "Litolff Beethoven 5 p1-p4": "library/_shared-records/beethoven5-p1-p4.record.json",
    "Breitkopf Brahms 1 p0-p3": "library/_shared-records/brahms1-breitkopf-p0-p3.record.json",
}

CLEF_QS = ("clef_glyph", "clef_position", "clef_located", "clef_seed")


def main() -> int:
    agree = disagree = 0
    for label, rel in DOCS.items():
        p = ROOT / rel
        if not p.exists():
            print(f"{label}: RECORD ABSENT -- reported, not skipped")
            continue
        r = measure(str(p))
        want = {f"staff/{a}/{b}/{c}": dict(v["dropped"])
                for (a, b, c), v in r["rescuable"].items()}
        obs: dict[str, list] = {k: [] for k in want}
        verd: dict[str, list] = {k: [] for k in want}
        for o in stream_array(str(p), "observations"):
            s = str(o.get("subject", ""))
            if s in obs and o.get("quantity") in CLEF_QS:
                obs[s].append((o.get("quantity"), o.get("value"),
                               o.get("reader"), o.get("score")))
        for v in stream_array(str(p), "verdicts"):
            s = str(v.get("subject", ""))
            if s in verd and v.get("quantity") in ("clef",) + CLEF_QS:
                verd[s].append((v.get("quantity"), v.get("outcome"),
                                v.get("reason"), v.get("value")))
        print(f"=== {label} ===")
        for s in sorted(want):
            dropped = want[s]
            # what the DROPPED class names would have said, by the legacy rule
            named = {clef_name_from_class(n) for n in dropped}
            standing = [x for x in verd[s] if x[0] == "clef"]
            stand_val = standing[0][3] if standing else None
            mark = "AGREE" if stand_val in named else "DISAGREE"
            if mark == "AGREE":
                agree += 1
            else:
                disagree += 1
            print(f"  {s}")
            print(f"    dropped class(es) : {dropped}  -> legacy name(s) {sorted(named)}")
            print(f"    standing verdict  : {stand_val}   [{mark}]")
            for q, val, rd, sc in obs[s]:
                print(f"    obs {q:14s} = {val!r:22s} reader={rd} score={sc}")
            for q, out, why, val in verd[s]:
                if q != "clef":
                    print(f"    vrd {q:14s} = {out}/{why}/{val!r}")
            print()
    print(f"SUMMARY: dropped class name AGREES with the standing verdict on "
          f"{agree} staves, DISAGREES on {disagree}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
