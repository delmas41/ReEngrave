"""Is the flag-on/flag-off null REAL, or did the arm not run?

A pooled figure that does not move supports two incompatible claims, and the
harness has already produced the wrong one once (`scan_eval` caches fixtures, so
an untagged second arm reuses the first arm's transcriptions and reports
"identical" without running). So the null needs three levels checked, not one:

  1. the two arms produced DIFFERENT transcription files at all
  2. the LABELS inside them differ on the rows the exposure probe said would
  3. the exported MUSICXML is identical anyway

Only 1 AND 2 AND 3 together mean "the label change is real and does not reach
the metric". 1 failing means the arm never ran; 2 failing means the flag never
reached the pipeline.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

FIX = Path("benchmarks/omr-scan-e2e-2026-09/fixtures")


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:12] if p.is_file() else "-"


def _labels(js: Path):
    """Every margin label the transcription recorded, per staff."""
    if not js.is_file():
        return None
    doc = json.loads(js.read_text())
    ctx = doc.get("contextual") or {}
    out = {}
    for page in doc.get("pages", []):
        for sysm in page.get("systems", []):
            for staff in sysm.get("staves", []):
                lab = staff.get("label") or staff.get("instrument")
                if lab:
                    out[str(staff.get("staff_index"))] = lab
    return out or ctx.get("staff_labels") or ctx


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default=".-qual")
    ap.add_argument("--rows", nargs="*")
    args = ap.parse_args()

    rows = args.rows or sorted({p.name.split(".")[0]
                                for p in FIX.glob("*.omr.musicxml")})
    n_xml_same = n_xml_diff = n_json_same = n_json_diff = 0
    for row in rows:
        a_x, b_x = FIX / f"{row}.omr.musicxml", FIX / f"{row}{args.tag}.omr.musicxml"
        a_j, b_j = FIX / f"{row}.omr.json", FIX / f"{row}{args.tag}.omr.json"
        if not b_x.is_file():
            continue
        xs, xd = _sha(a_x), _sha(b_x)
        js, jd = _sha(a_j), _sha(b_j)
        same_x, same_j = xs == xd, js == jd
        n_xml_same += same_x
        n_xml_diff += not same_x
        n_json_same += same_j
        n_json_diff += not same_j
        la, lb = _labels(a_j), _labels(b_j)
        lab_diff = [k for k in set(la or {}) | set(lb or {})
                    if (la or {}).get(k) != (lb or {}).get(k)]
        flag = ""
        if lab_diff:
            flag = f"  LABELS DIFFER on staves {sorted(lab_diff, key=str)}"
        print(f"  {row:38s} json {'same' if same_j else 'DIFF'}   "
              f"musicxml {'same' if same_x else 'DIFF'}{flag}")

    print()
    print(f"transcription JSON: {n_json_diff} differ, {n_json_same} identical")
    print(f"exported MusicXML : {n_xml_diff} differ, {n_xml_same} identical")
    print()
    if n_json_diff == 0:
        print("⚠️  THE ARMS PRODUCED IDENTICAL TRANSCRIPTIONS — the flag did not "
              "reach the pipeline, or the run was cached. The null is NOT real.")
    elif n_xml_diff == 0:
        print("The null IS real at the export: the arms transcribed differently "
              "and exported identically, so the label change does not reach "
              "OMR-NED on this pool.")
    else:
        print("The arms differ in the export too — the pooled tie is a "
              "coincidence of offsetting rows, not a no-op. Open the per-row diff.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
