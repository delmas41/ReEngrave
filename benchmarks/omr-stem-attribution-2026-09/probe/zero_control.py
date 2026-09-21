"""Is *"none of the print-adjudicated heads has a stem"* a FACT or my BUG?

⚠️ A FILTER THAT SILENTLY EMPTIES A FILE LOOKS EXACTLY LIKE AN EMPTY FILE.
This probe found 0 overlapping stems for all 44 heads the print has ever
adjudicated on this thread, which is the shape of a parsing fault. Three
controls, each able to fail:

  1. POSITIVE -- the same index finds stems for other heads in the SAME cells.
     If the cells are stemless the zero is about the cells, not the heads.
  2. NEAREST -- how far is the nearest stem, in staff spaces? A head whose
     nearest stroke is 40 spaces away is genuinely stemless; one at 0.1 would
     say the overlap test is the thing at fault.
  3. VERDICT -- what reason does the RECORD itself give these heads? If the
     shipped pipeline says `beam_mate`/`no_stem` on them, that independently
     confirms `_stems_on` came back empty, from the pipeline's own mouth
     rather than from my re-derivation.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from reach import cell_of, collect, overlap  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from omr_ledger_extrapolation_shim import stream_array  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--subjects", nargs="+", required=True,
                    help="JSON files with rows carrying a 'subject'")
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    wanted = []
    for p in args.subjects:
        d = json.load(open(p))
        rows = d.get("rows") or d.get("index") or []
        for r in rows:
            if r.get("subject"):
                wanted.append((Path(p).name, r.get("id") or r.get("i"),
                               r["subject"]))
    wset = {s for _f, _i, s in wanted}

    stems, heads, _ = collect(args.record)
    hbox = {}
    for c, hs in heads.items():
        for subj, _hid, hb in hs:
            hbox[subj] = hb

    # 3. what the RECORD's own verdict says about each
    verdicts = {}
    for v in stream_array(args.record, "verdicts"):
        if v.get("quantity") == "stem_direction" and v.get("subject") in wset:
            verdicts[v["subject"]] = (v.get("reason"), v.get("value"),
                                      v.get("outcome"))

    rows, reasons = [], Counter()
    for fname, rid, subj in wanted:
        c = cell_of(subj)
        ss = stems.get(c, [])
        hb = hbox.get(subj)
        near = None
        if hb is not None and ss:
            # vertical/horizontal separation to the nearest stroke box
            def gap(sb):
                dx = max(0.0, max(sb[0] - (hb[0] + hb[2]), hb[0] - (sb[0] + sb[2])))
                dy = max(0.0, max(sb[1] - (hb[1] + hb[3]), hb[1] - (sb[1] + sb[3])))
                return (dx * dx + dy * dy) ** 0.5
            near = round(min(gap(sb) for _sid, sb in ss), 1)
        rec = verdicts.get(subj, (None, None, None))
        reasons[rec[0]] += 1
        rows.append({
            "file": fname, "id": rid, "subject": subj,
            "cell": c,
            "stems_in_this_cell": len(ss),
            "other_heads_in_cell_with_a_stem": sum(
                1 for s2, _h2, b2 in heads.get(c, [])
                if s2 != subj and any(overlap(sb, b2) for _s, sb in ss)),
            "nearest_stem_gap_px": near,
            "record_reason": rec[0], "record_value": rec[1],
        })

    out = {
        "record": args.record,
        "n_subjects": len(rows),
        "subjects_whose_cell_HAS_stems": sum(
            1 for r in rows if r["stems_in_this_cell"] > 0),
        "subjects_in_a_cell_where_ANOTHER_head_takes_a_stem": sum(
            1 for r in rows if r["other_heads_in_cell_with_a_stem"] > 0),
        "record_reason_histogram": dict(reasons),
        "rows": rows,
    }
    print(json.dumps({k: v for k, v in out.items() if k != "rows"}, indent=2))
    print()
    for r in rows:
        print(f"  {r['file'][:22]:22s} {str(r['id']):4s} {r['subject']:20s} "
              f"cell_stems={r['stems_in_this_cell']:3d} "
              f"other_heads_stemmed={r['other_heads_in_cell_with_a_stem']:3d} "
              f"nearest={r['nearest_stem_gap_px']} "
              f"reason={r['record_reason']}")
    if args.out:
        Path(args.out).write_text(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
