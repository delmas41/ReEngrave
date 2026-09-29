"""ROADMAP 2.25 -- price the ledger-line-stroke connection on a saved record.

PATH: STAGED. Re-decides ONE fixed gather (`review.rerun.rebuild_gather` +
`run_stages`), exports it, writes the MusicXML, and runs the INDEPENDENT
`bar_sum_check` control against the FILE (never against the exporter's own
arithmetic -- CLAUDE.md §2 rule 7).

The tree this runs under is whichever `ROOT` resolves to -- copy this SAME
file (unmodified) into an extracted `origin/main` for the base arm, exactly
as `redecide_arm.py`'s own §11.9 precedent:

    git archive origin/main tools benchmarks/omr-missing-notes-2026-09/probe \\
        benchmarks/omr-bar-sum-holdout-2026-09/probe | tar -x -C <base_dir>
    python3 <base_dir>/.../price_2_25.py <record> --out <base.json> \\
        --musicxml <base.musicxml>
    python3 benchmarks/omr-missing-notes-2026-09/probe/price_2_25.py \\
        <record> --out <arm.json> --musicxml <arm.musicxml>
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--out", required=True)
    ap.add_argument("--musicxml", required=True)
    ap.add_argument("--page", type=int, default=None)
    a = ap.parse_args()

    from tools.omr.staged.record import Q
    from tools.omr.staged.record_io import load_record
    from tools.omr.staged.review import rerun as RR

    def _page_of(key: str):
        parts = key.split("/")
        if parts[0] in ("page", "system", "staff", "cell", "glyph") \
                and len(parts) > 1:
            return int(parts[1])
        return None

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
    xml, rep, refusals, _placed = RR.export_with_subjects(result)
    Path(a.musicxml).write_text(xml)

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
                  "beams_ledger_line": d.get("beams_ledger_line"),
                  "beams_beyond_stem": d.get("beams_beyond_stem")}

    refusal_of = {s: r for s, r in refusals}
    ledger_touched = [s for s, d in dur.items()
                      if (d.get("beams_ledger_line") or 0) > 0]

    out = {"record": a.record, "root": str(ROOT), "page": a.page,
           "notes_in_file": xml.count("<note"),
           "notes_not_written": rep.get("notes_not_written"),
           "written_notes": (rep.get("written") or {}).get("notes"),
           "bars_held_out_sum": ((rep.get("bars_held_out_sum") or {})
                                 .get("bars")),
           "balanced": rep.get("balanced"),
           "n_heads_ledger_line_touched": len(ledger_touched),
           "ledger_line_touched": {
               s: {"outcome": dur[s]["outcome"], "reason": dur[s]["reason"],
                   "beats": dur[s]["beats"],
                   "export_refusal": refusal_of.get(s)}
               for s in ledger_touched},
           "durations": dur}
    Path(a.out).write_text(json.dumps(out, indent=1, default=str))
    print(f"@ {ROOT.name}: duration_narrowed "
          f"{(rep.get('notes_not_written') or {}).get('duration_narrowed')}, "
          f"notes written {out['written_notes']}, <note> {out['notes_in_file']}, "
          f"heads touched by the ledger-line rule: {len(ledger_touched)}, "
          f"balanced={rep.get('balanced')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
