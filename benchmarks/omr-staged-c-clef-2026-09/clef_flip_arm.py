"""WOULD ANY REAL STAFF FLIP if the class name were allowed to name the clef?

§4 refuses to put `clefCAlto`/`clefCTenor` into `_GLYPH_TO_CLEF`. The first
statement of WHY was wrong (it claimed a flip on `p3/s1/st11`, and two locator
crops outweigh it), so this asks the question properly instead of reasoning
about weights: rebuild each affected staff's evidence FROM THE RECORD, run the
real adjudicator twice -- shipped, and with the naming mutation applied in
memory -- and report every staff whose value or margin moves.

⚠️ WEIGHTS DO NOT DECIDE A CONTEST; ROW COUNTS DO. `W_DETECTOR_HIGH` (3.0)
beating `W_LOCATOR` (2.0) is true and was the source of the wrong claim: two
locator crops are two independent signals and sum, so the comparison that
matters is per-staff and can only be taken per staff.

⚠️ IT REBUILDS THE POST-REPAIR SHAPE. The committed records were gathered
BEFORE this lane, so they hold no `clef_glyph` row for the dropped C clefs.
The rows are reconstructed from the `glyph_box` rows the record does hold --
which is exactly what `gather_clef` would now emit -- and the reconstruction
is stated rather than hidden, because it is the one step between this arm and
a real re-gather.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "benchmarks" / "omr-ledger-extrapolation-2026-09"))

from recordstream import stream_array                        # noqa: E402
from clef_reach import measure                               # noqa: E402
from tools.omr.staged import adjudicate, adjudicators        # noqa: E402,F401
from tools.omr.staged import record as R                     # noqa: E402
from tools.omr.staged.record import Log, Q, READERS          # noqa: E402
from tools.omr.staged.adjudicators import clef as clef_mod   # noqa: E402

DOCS = {
    "Litolff Beethoven 5 p1-p4": "library/_shared-records/beethoven5-p1-p4.record.json",
    "Breitkopf Brahms 1 p0-p3": "library/_shared-records/brahms1-breitkopf-p0-p3.record.json",
}
SUB = R.staff(0, 0, 0)


def evidence_for(path: str, staves: set[str]) -> dict:
    """`{staff: {"glyphs": [(name, score, y)], "located": [(value, frame, score)]}}`"""
    out = {s: {"glyphs": [], "located": []} for s in staves}
    for o in stream_array(path, "observations"):
        s = str(o.get("subject", ""))
        q = o.get("quantity")
        if q == "clef_located" and s in out:
            out[s]["located"].append((o.get("value"), o.get("frame"), o.get("score")))
        elif q == "glyph_box":
            parts = s.split("/")
            if len(parts) != 6 or parts[0] != "glyph" or parts[4] != "0":
                continue
            key = f"staff/{parts[1]}/{parts[2]}/{parts[3]}"
            if key not in out:
                continue
            if (o.get("detail") or {}).get("category") != "clef":
                continue
            val = o.get("value") or []
            if val:
                out[key]["glyphs"].append(
                    (str(val[0]), o.get("score"),
                     (o.get("detail") or {}).get("y_center_page")))
    return out


def run_one(ev: dict):
    log = Log()
    for name, score, _y in ev["glyphs"]:
        log.observe(SUB, Q.CLEF_GLYPH, name, reader=READERS.DETECTOR,
                    frame="cell:0", score=float(score or 0.0),
                    y_center=180.0, x_center=50.0)
        # the grid row `gather_clef` emits beside every admitted glyph; 4.0
        # steps == ON this staff, the case most favourable to the mutation
        log.observe(SUB, Q.CLEF_POSITION, 4.0, reader=READERS.GEOMETRY,
                    frame="cell:0", glyph=name, y_center=180.0)
    for val, frame, score in ev["located"]:
        log.observe(SUB, Q.CLEF_LOCATED, str(val), reader=READERS.CV_LOCATOR,
                    frame=str(frame), score=float(score or 0.0))
    adjudicate.run(log)
    v = log.verdict(Q.CLEF, SUB)
    if v is None:
        return None, None, None
    return v.value, v.outcome.value, (round(v.margin, 2) if v.margin is not None else None)


def main() -> int:
    flips = eroded = 0
    checked = 0
    for label, rel in DOCS.items():
        p = ROOT / rel
        if not p.exists():
            print(f"{label}: RECORD ABSENT -- reported, not skipped")
            continue
        r = measure(str(p))
        staves = {f"staff/{a}/{b}/{c}" for (a, b, c) in r["rescuable"]}
        ev = evidence_for(str(p), staves)
        print(f"=== {label} ===")
        for s in sorted(staves):
            checked += 1
            saved = dict(clef_mod._GLYPH_TO_CLEF)
            shipped = run_one(ev[s])
            clef_mod._GLYPH_TO_CLEF["clefCAlto"] = "alto"
            clef_mod._GLYPH_TO_CLEF["clefCTenor"] = "tenor"
            try:
                mutated = run_one(ev[s])
            finally:
                clef_mod._GLYPH_TO_CLEF.clear()
                clef_mod._GLYPH_TO_CLEF.update(saved)
            flip = shipped[0] != mutated[0]
            erode = (not flip and shipped[2] is not None
                     and mutated[2] is not None and mutated[2] < shipped[2])
            flips += bool(flip)
            eroded += bool(erode)
            tag = "FLIP" if flip else ("margin eroded" if erode else "unchanged")
            names = [g[0] for g in ev[s]["glyphs"]]
            print(f"  {s:22s} glyphs={names} locator={[l[0] for l in ev[s]['located']]}")
            print(f"      shipped={shipped}  mutated={mutated}   -> {tag}")
        print()

    # ⚠️ POSITIVE CONTROL: if the mutation moved NOTHING anywhere, the arm is
    # not applying it and every "unchanged" below is void.
    if not flips and not eroded:
        print("ARM DEAD: the naming mutation moved neither a value nor a "
              "margin on any staff -- it is not being applied.")
        return 2
    print(f"{checked} staves checked: {flips} FLIP, {eroded} margin eroded.")
    print("⚠️ A FLIP IS THE HAZARD; AN ERODED MARGIN IS THE COST. On this "
          "corpus the hazard is what the layout happens to prevent, not what "
          "the rule prevents -- which is why the refusal rests on the "
          "erosion and on DeepScoresV2 having no soprano/mezzo/baritone "
          "class, not on an observed flip.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
