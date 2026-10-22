"""THE POSITIVE CONTROL POPULATION — heads whose stem we DID read.

⚠️⚠️ WHY THIS EXISTS AND WHY IT IS NOT OPTIONAL. This pass answers "does the
print hold a stem here?" by eye. A negative verdict from an eye that cannot
read this plate is worthless, and indistinguishable from a true absence -- the
repo's own rule that *a control reporting "the print holds nothing there" must
first be able to say "I could not look there"*. So before a single stemless
head is adjudicated, the same crops are made for heads the record decided
`up`/`down`, and read BLIND to that decision. If the eye cannot recover the
direction the pipeline already read, no figure in this pass survives.

⚠️ These heads are drawn from a DISJOINT population (outcome == decided) and
are excluded from every stemless stratum, so calibrating on them cannot
contaminate the pre-registered sample.

No page re-cut is needed: the page box is on the record.

    python3 probe/decided_rows.py --record R --label litolff \
        --json out/litolff-decided.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "benchmarks" / "omr-ledger-extrapolation-2026-09"))
from recordstream import stream_array  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--json", required=True)
    a = ap.parse_args()

    heads, pboxes, klass, lines_of, spacing_of = {}, {}, {}, {}, {}
    for o in stream_array(a.record, "observations"):
        q, s = o.get("quantity"), o.get("subject")
        if q == "staff_lines" and isinstance(o.get("value"), list):
            lines_of[s] = sorted(float(x) for x in o["value"])
        elif q == "staff_spacing":
            spacing_of[s] = float(o["value"])
        elif q == "notehead_class":
            klass[s] = str(o.get("value"))
        elif q == "glyph_box":
            v = o.get("value")
            if isinstance(v, list) and len(v) == 5 and str(v[0]).startswith("notehead"):
                heads[s] = [float(x) for x in v[1:]]
                bp = (o.get("detail") or {}).get("bbox_page_px")
                if bp:
                    pboxes[s] = [float(x) for x in bp]

    out = []
    for v in stream_array(a.record, "verdicts"):
        if v.get("quantity") != "stem_direction" or v.get("outcome") != "decided":
            continue
        s = v["subject"]
        if s not in heads or s not in pboxes:
            continue
        p = s.split("/")
        sk = f"staff/{p[1]}/{p[2]}/{p[3]}"
        out.append({
            "subject": s,
            "read_direction": str(v.get("value")),
            "where": {"page": int(p[1]), "system": int(p[2]),
                      "staff": int(p[3]), "cell": int(p[4]),
                      "glyph": int(p[5])},
            "cls": klass.get(s),
            "bbox_page_px": pboxes[s],
            "bbox_canonical": heads[s],
            "staff_key": sk,
            "staff_lines": lines_of.get(sk),
            "staff_spacing": spacing_of.get(sk),
        })
    print(f"{a.label}: {len(out)} heads with a DECIDED stem direction")
    if not out:
        print("DEAD: no decided stem on this record", file=sys.stderr)
        return 2
    n_up = sum(1 for r in out if r["read_direction"] == "up")
    print(f"   up {n_up}   down {len(out) - n_up}")
    Path(a.json).write_text(json.dumps(
        {"label": a.label, "decided": len(out), "rows": out}, indent=1))
    print(f"wrote {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
