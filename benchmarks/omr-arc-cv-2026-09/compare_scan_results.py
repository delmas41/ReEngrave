"""Compare a scan-e2e arm's result JSON to the recorded widened-graft
baseline: per-row deltas, 11-row and 10-row (excl. bach) pools, and element
counts (tie/slur/rest/note/beam) from the arm's prediction fixtures vs truth.
Element counting replicates ROUND5_METHOD section 3 (<tie> start+stop counted
individually, <rest> any, <slur> start+stop... slur counted as elements)."""
import json
import re
import sys
from pathlib import Path

BENCH = Path("benchmarks/omr-scan-e2e-2026-09")
BASE = BENCH / "results-widened-graft.json"


def count_elements(xml_path: Path) -> dict:
    if not xml_path.is_file():
        return {}
    t = xml_path.read_text()
    return {
        "tie": len(re.findall(r"<tie ", t)) + len(re.findall(r"<tie/>", t)),
        "slur": len(re.findall(r"<slur[ />]", t)),
        "rest": len(re.findall(r"<rest[ />]", t)),
        "note": len(re.findall(r"<note[ >]", t)),
        "beam": len(re.findall(r"<beam[ >]", t)),
    }


def pools(rows, skip=("bach-brandenburg3-mvt1-468678-p1",)):
    e = sum(r["omr_ned"]["omr_ed"] for r in rows)
    d = sum(r["omr_ned"]["truth_symbols"] + r["omr_ned"]["pred_symbols"] for r in rows)
    sub = [r for r in rows if r["row_id"] not in skip]
    e10 = sum(r["omr_ned"]["omr_ed"] for r in sub)
    d10 = sum(r["omr_ned"]["truth_symbols"] + r["omr_ned"]["pred_symbols"] for r in sub)
    return (e / d, e), (e10 / d10, e10)


def main():
    arm_path = Path(sys.argv[1])
    tag = sys.argv[2] if len(sys.argv) > 2 else ""
    arm = json.load(open(arm_path))
    base = json.load(open(BASE))
    b_rows = {r["row_id"]: r for r in base["rows"]}
    print(f"{'row':38s} {'base':>8s} {'arm':>8s} {'d_edits':>8s}")
    for r in arm["rows"]:
        rid = r["row_id"]
        b = b_rows.get(rid)
        if not b or not r.get("omr_ned"):
            continue
        print(f"{rid:38s} {b['omr_ned']['omr_ned']:.4f}/{b['omr_ned']['omr_ed']:>5d} "
              f"{r['omr_ned']['omr_ned']:.4f}/{r['omr_ned']['omr_ed']:>5d} "
              f"{r['omr_ned']['omr_ed'] - b['omr_ned']['omr_ed']:+6d}")
    (p11, e11), (p10, e10) = pools([r for r in arm["rows"] if r.get("omr_ned")])
    (b11, be11), (b10, be10) = pools([r for r in base["rows"] if r.get("omr_ned")])
    print(f"\n11-row pool: base {b11:.4f}/{be11}  arm {p11:.4f}/{e11}  ({p11-b11:+.4f}, {e11-be11:+d} edits)")
    print(f"10-row pool: base {b10:.4f}/{be10}  arm {p10:.4f}/{e10}  ({p10-b10:+.4f}, {e10-be10:+d} edits)")
    # element counts, arm predictions vs truth (10-row = excl bach, and 11-row)
    tot_t, tot_p, tot_t10, tot_p10 = {}, {}, {}, {}
    for r in arm["rows"]:
        rid = r["row_id"]
        t = count_elements(BENCH / "fixtures" / f"{rid}.truth.musicxml")
        p = count_elements(Path(r["pred_xml"]))
        for k in ("tie", "slur", "rest", "note", "beam"):
            tot_t[k] = tot_t.get(k, 0) + t.get(k, 0)
            tot_p[k] = tot_p.get(k, 0) + p.get(k, 0)
            if rid != "bach-brandenburg3-mvt1-468678-p1":
                tot_t10[k] = tot_t10.get(k, 0) + t.get(k, 0)
                tot_p10[k] = tot_p10.get(k, 0) + p.get(k, 0)
    print("\nelements (11-row): truth", tot_t, "\n                   arm  ", tot_p)
    print("elements (10-row): truth", tot_t10, "\n                   arm  ", tot_p10)


if __name__ == "__main__":
    main()
