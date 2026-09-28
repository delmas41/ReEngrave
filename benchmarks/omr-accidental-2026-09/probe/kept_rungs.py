"""ROADMAP 2.7b — where do the rungs stand that KEEP a far head on its filed
staff? For every head past both bands (filed > 3.0, near <= 2.75 and nearer)
that `belongs_to_a_nearer_staff` KEPT because of a kept rung, the rungs of its
cell between it and the filed staff, measured from the HEAD's centre toward
the staff, in staff spaces. A rung through the head itself (offset ~0) is the
head's own ledger — it says the note is on a ledger line, not WHICH staff the
ledger belongs to — so the distribution says whether the exception is
reading a ladder or reading the note's own line.

    python3 benchmarks/omr-accidental-2026-09/probe/kept_rungs.py <arm.record.json> [--out json]
"""
from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))

from tools.omr.staged.record_io import load_record  # noqa: E402


def main() -> int:
    rec = load_record(sys.argv[1])["record"]
    sup = {v.get("supersedes") for v in rec["verdicts"] if v.get("supersedes")}
    V = {(v["subject"], v["quantity"]): v for v in rec["verdicts"]
         if v["id"] not in sup}
    lines, box, ledgers = {}, {}, collections.defaultdict(list)
    for o in rec["observations"]:
        if o["quantity"] == "staff_lines":
            ys = sorted(float(y) for y in o["value"])
            lines[o["subject"]] = (ys, (ys[-1] - ys[0]) / (len(ys) - 1))
        elif o["quantity"] == "glyph_box":
            pb = (o.get("detail") or {}).get("bbox_page_px")
            if not pb:
                continue
            box[o["subject"]] = pb
            if o["value"][0] == "ledgerLine":
                ledgers["/".join(o["subject"].split("/")[:5])].append(
                    (o["subject"], pb))
    out = []
    for (sub, q), v in V.items():
        if q != "notehead_is_not_a_notehead" or v["value"] is not False:
            continue
        sig = (v.get("detail") or {}).get("nearer_staff_signal") or {}
        f, n = sig.get("filed_spaces", 0), sig.get("near_spaces", 99)
        if not (f > 3.0 and n <= 2.75 and n < f
                and sig.get("kept_rungs_toward_filed", 0) > 0):
            continue
        staff = "staff/" + "/".join(sub.split("/")[1:4])
        ys, sp = lines[staff]
        pb = box[sub]
        y = (pb[1] + pb[3]) / 2.0
        edge = ys[0] if y < ys[0] else ys[-1]
        lo, hi = (y, edge) if y < edge else (edge, y)
        offs = []
        for lsub, lb in ledgers["/".join(sub.split("/")[:5])]:
            ly = (lb[1] + lb[3]) / 2.0
            if not (lo < ly < hi) or min(lb[2], pb[2]) - max(lb[0], pb[0]) <= 0:
                continue
            lv = V.get((lsub, "ledger_is_not_a_ledger"))
            if lv and lv["outcome"] == "decided" and lv["value"] is True:
                continue
            offs.append(round(abs(ly - y) / sp, 3))
        out.append({"head": sub, "filed": f, "near": n, "rung_offsets": offs,
                    "max_offset": max(offs) if offs else None})
    hist = collections.Counter(round(r["max_offset"] * 4) / 4
                               for r in out if r["max_offset"] is not None)
    print(len(out), "kept by a rung; max rung offset from the head (spaces):",
          dict(sorted(hist.items())))
    if len(sys.argv) > 3 and sys.argv[2] == "--out":
        Path(sys.argv[3]).write_text(json.dumps(
            {"kept_by_rung": out, "hist_max_offset": {str(k): v for k, v in
                                                      sorted(hist.items())}},
            indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
