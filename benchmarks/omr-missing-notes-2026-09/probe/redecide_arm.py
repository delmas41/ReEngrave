"""ROADMAP 2.18b -- re-decide ONE saved record with the code tree this file
sits in, and dump the census + every standing duration.

PATH: STAGED. ADJUDICATE->EXPORT over a FIXED gather (`review.rerun.rerun`).
The tree is the one this file lives in (`ROOT = parents[2]`), so a copy of it
placed in an extracted `origin/main` (`git archive origin/main tools
benchmarks/... | tar -x`) runs MAIN's code on the same record -- that is the
base of the 2.18b controls (FINDINGS §11.9), and it is why this script
patches nothing unless asked:

  --arm plain   the tree as it is (main or branch)
  --arm off     STEM_JOIN_TOLERANCE_SPACES = 0 (branch only): must equal
                `plain` on main, verdict for verdict -- the control

`--page N` keeps only the gather rows of PDF page N (plus rows filed above
any page) before re-deciding, for a whole-movement record.

    python3 .../redecide_arm.py <record.json> --arm plain --out <arm.json>
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))


def _page_of(key: str):
    parts = key.split("/")
    if parts[0] in ("page", "system", "staff", "cell", "glyph") \
            and len(parts) > 1:
        return int(parts[1])
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--arm", choices=["plain", "off"], default="plain")
    ap.add_argument("--page", type=int, default=None)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    from tools.omr.staged.record import Q
    from tools.omr.staged.record_io import load_record
    from tools.omr.staged.review import rerun as RR

    if a.arm == "off":
        from tools.omr.staged.adjudicators import rhythm as RH
        RH.STEM_JOIN_TOLERANCE_SPACES = 0.0

    doc = load_record(a.record)
    rec = doc["record"] if "record" in doc else doc
    if a.page is not None:
        keep = lambda r: _page_of(r["subject"]) in (None, a.page)
        rec = {**rec,
               "observations": [r for r in rec["observations"] if keep(r)],
               "abstentions": [r for r in rec.get("abstentions") or ()
                               if keep(r)],
               "verdicts": []}
    log, _ = RR.rebuild_gather(rec)
    RR.run_stages(log)
    result = RR._to_result(log, doc, None)
    xml, rep, _ref, _placed = RR.export_with_subjects(result)
    standing = RR._verdict_index(result["record"]["verdicts"])
    dur = {}
    for (q, s), v in standing.items():
        if q != Q.DURATION:
            continue
        val = v.get("value") if isinstance(v.get("value"), dict) else {}
        d = v.get("detail") or {}
        dur[s] = {"outcome": v["outcome"], "reason": v.get("reason"),
                  "beats": val.get("beats"), "written": val.get("written"),
                  "dots": val.get("dots"), "beam_levels": val.get("beam_levels"),
                  "flags_attached": d.get("flags_attached"),
                  "beams_beyond_stem": d.get("beams_beyond_stem")}
    out = {"record": a.record, "arm": a.arm, "page": a.page, "root": str(ROOT),
           "notes_in_file": xml.count("<note"),
           "notes_not_written": rep.get("notes_not_written"),
           "written_notes": (rep.get("written") or {}).get("notes"),
           "bars_held_out_sum": ((rep.get("bars_held_out_sum") or {})
                                 .get("bars")),
           "durations": dur}
    Path(a.out).write_text(json.dumps(out, indent=1, default=str))
    print(f"{a.arm} @ {ROOT.name}: duration_narrowed "
          f"{(rep.get('notes_not_written') or {}).get('duration_narrowed')}, "
          f"notes written {out['written_notes']}, <note> {out['notes_in_file']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
