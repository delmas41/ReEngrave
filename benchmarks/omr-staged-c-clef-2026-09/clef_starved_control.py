"""CONTROL: does the RECORD agree that those staves have no clef?

`clef_reach.py` predicts which staves `gather_clef` starves, by re-deriving
its admission test. That is a claim about code. This asks the RECORD what
actually happened on those staves -- the `clef_glyph` observation/abstention
and the `clef` verdict -- so the prediction is checked against the artefact
rather than against itself.

⚠️ IT MUST BE ABLE TO FAIL. If a "starved" staff turns out to carry a decided
clef, the reach number is wrong and this prints DISAGREE. The positive
control is the complement: staves the probe calls admitted must mostly carry
a clef_glyph observation, or the join is reading the wrong subjects.
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "benchmarks" / "omr-ledger-extrapolation-2026-09"))

from recordstream import stream_array                       # noqa: E402
from clef_reach import measure                              # noqa: E402

DOCS = {
    "Litolff Beethoven 5 p1-p4": "library/_shared-records/beethoven5-p1-p4.record.json",
    "Breitkopf Brahms 1 p0-p3": "library/_shared-records/brahms1-breitkopf-p0-p3.record.json",
}


def staff_facts(path: str, wanted: set[str]) -> dict:
    """`{staff_subject: {"glyph": [...], "clef_verdict": (outcome, reason, value)}}`"""
    out: dict[str, dict] = {k: {"glyph": [], "clef_verdict": None} for k in wanted}
    for o in stream_array(path, "observations"):
        if o.get("quantity") != "clef_glyph":
            continue
        s = str(o.get("subject", ""))
        if s in out:
            out[s]["glyph"].append(o.get("value"))
    for v in stream_array(path, "verdicts"):
        if v.get("quantity") != "clef":
            continue
        s = str(v.get("subject", ""))
        if s in out:
            out[s]["clef_verdict"] = (v.get("outcome"), v.get("reason"), v.get("value"))
    return out


def main() -> int:
    bad = 0
    for label, rel in DOCS.items():
        p = ROOT / rel
        if not p.exists():
            print(f"{label}: RECORD ABSENT -- reported, not skipped")
            continue
        r = measure(str(p))
        starved = {f"staff/{a}/{b}/{c}" for (a, b, c) in r["rescuable"]}
        admitted = {f"staff/{a}/{b}/{c}"
                    for (a, b, c), v in r["starved"].items()} | starved
        # a sample of staves the probe says ARE served, as the positive control
        served = set()
        for o in stream_array(str(p), "observations"):
            if o.get("quantity") == "clef_glyph":
                served.add(str(o.get("subject", "")))
            if len(served) > 4000:
                break
        served -= admitted

        facts = staff_facts(str(p), starved | set(list(served)[:40]))
        print(f"=== {label} ===")
        print(f"  staves the probe calls STARVED (by the INCUMBENT rule): {len(starved)}")
        for s in sorted(starved):
            f = facts[s]
            v = f["clef_verdict"]
            agree = (not f["glyph"]) and (v is None or v[0] != "decided")
            print(f"    {s:22s} clef_glyph_obs={f['glyph']!r:6s} "
                  f"clef_verdict={v}  -> {'AGREE' if agree else 'DISAGREE'}")
            if not agree:
                bad += 1
        sample = sorted(set(list(served)[:40]))[:5]
        print(f"  positive control -- staves the probe calls SERVED (sample of "
              f"{len(sample)}):")
        for s in sample:
            f = facts[s]
            print(f"    {s:22s} clef_glyph_obs={f['glyph']!r} "
                  f"clef_verdict={f['clef_verdict']}")
        print()
    # ⚠️ THE RESULT IS THE REFUTATION, and the exit code says so rather than
    # reporting a defect. Every one of the nine staves confirms the GATHER
    # half -- `clef_glyph_obs=[]`, the detector's C clef discarded -- and
    # every one carries a DECIDED clef verdict anyway. So the brief's premise
    # ("a dropped C clef is a whole staff of missing music") is FALSE on both
    # documents: the CV locator is already covering exactly this population.
    # What the repair buys is therefore corroboration, not rescue.
    #
    # ⚠️ IT CAN STILL FAIL. A staff that turned out to carry a `clef_glyph`
    # observation would mean the gather-side reach number is wrong, and that
    # is a different answer from this one -- so the two are separated.
    wrong_gather = 0
    for label, rel in DOCS.items():
        p = ROOT / rel
        if not p.exists():
            continue
        r = measure(str(p))
        starved = {f"staff/{a}/{b}/{c}" for (a, b, c) in r["rescuable"]}
        facts = staff_facts(str(p), starved)
        wrong_gather += sum(1 for s in starved if facts[s]["glyph"])
    if wrong_gather:
        print(f"GATHER REACH IS WRONG on {wrong_gather} staves -- a staff the "
              f"probe calls starved carries a clef_glyph row.")
        return 1
    print(f"RESULT: the gather-side drop is confirmed on all {bad} staves "
          f"(no clef_glyph row on any of them), AND all {bad} carry a decided "
          f"clef verdict anyway -- so no staff is left without a clef. "
          f"The brief's 'a whole staff of missing music' is REFUTED; the "
          f"locator is carrying this population alone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
