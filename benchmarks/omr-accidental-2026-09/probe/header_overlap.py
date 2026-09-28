"""ROADMAP 2.7 x 2.9/2.12a — is an `accidental*` glyph that the KEY reader
already counted as a signature marker ALSO being owned as an in-bar
accidental?

2.12a admits header `accidentalFlat` boxes as key-signature markers (the
detector does not always spell a signature flat `keyFlat`). 2.7's GATHER
excludes only the `key*` CLASSES, so a header flat spelled `accidentalFlat`
is gathered twice: once as a key marker, once as an in-bar accidental. This
counts, per record, the accidental owners whose glyph box overlaps a
`Q.KEYSIG_MARKER` row's box on the same staff (page frame), and what they
decided.

    python3 benchmarks/omr-accidental-2026-09/probe/header_overlap.py <arm.record.json> [--out json]
"""
from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))

from tools.omr.staged.record_io import load_record  # noqa: E402


def _box(o):
    d = o.get("detail") or {}
    for k in ("bbox_page_px", "page_box", "box_page_px"):
        if d.get(k):
            return d[k]
    return None


def main() -> int:
    rec = load_record(sys.argv[1])["record"]
    glyph_page = {}
    markers = collections.defaultdict(list)
    sample = None
    for o in rec["observations"]:
        if o["quantity"] == "glyph_box":
            b = _box(o)
            if b:
                glyph_page[o["subject"]] = b
        elif o["quantity"] == "keysig_marker":
            staff = "/".join(o["subject"].split("/")[:4]).replace(
                o["subject"].split("/")[0], "staff", 1)
            sample = sample or o
            markers[staff].append(o)
    # ⚠️ A MARKER ROW IS FILED ON THE STAFF with the glyph's CANONICAL x and
    # y_center in its own `frame` (`cell:N`); it names no glyph. Joined here
    # to the `glyph_box` in that cell with the same x and y + h//2 (+-1 px).
    boxes_by_cell = collections.defaultdict(list)
    for o in rec["observations"]:
        if o["quantity"] == "glyph_box" and isinstance(o["value"], list):
            cell = "cell/" + "/".join(o["subject"].split("/")[1:5])
            boxes_by_cell[cell].append((o["subject"], o["value"]))
    marker_glyphs = set()
    unjoined = 0
    for staff, rows in markers.items():
        for o in rows:
            d = o.get("detail") or {}
            fr = str(o.get("frame") or "")
            if not fr.startswith("cell:") or "x" not in d:
                unjoined += 1
                continue
            cell = staff.replace("staff/", "cell/", 1) + "/" + fr.split(":")[1]
            hit = [g for g, v in boxes_by_cell.get(cell, ())
                   if abs(v[1] - d["x"]) <= 1
                   and abs(v[2] + v[4] // 2 - d.get("y_center", -99)) <= 1]
            if hit:
                marker_glyphs.update(hit)
            else:
                unjoined += 1
    marker_boxes = {}
    sup = {v.get("supersedes") for v in rec["verdicts"] if v.get("supersedes")}
    tally = collections.Counter()
    for v in rec["verdicts"]:
        if v["quantity"] != "accidental_owner" or v["id"] in sup:
            continue
        g = v["subject"]
        staff = "staff/" + "/".join(g.split("/")[1:4])
        hit = g in marker_glyphs
        if not hit and g in glyph_page:
            gb = glyph_page[g]
            for mb in marker_boxes.get(staff, ()):
                ix = min(gb[2], mb[2]) - max(gb[0], mb[0])
                iy = min(gb[3], mb[3]) - max(gb[1], mb[1])
                if ix > 0 and iy > 0:
                    hit = True
                    break
        if hit:
            tally[f"{v['outcome']}:{v['reason']}"] += 1
    out = {"record": sys.argv[1],
           "keysig_marker_rows": sum(len(r) for r in markers.values()),
           "marker_glyphs_joined": len(marker_glyphs),
           "marker_rows_not_joined": unjoined,
           "accidental_owners_on_a_key_marker": dict(tally),
           "sample_marker_row": sample}
    if "--out" in sys.argv:
        Path(sys.argv[sys.argv.index("--out") + 1]).write_text(
            json.dumps(out, indent=1, default=str))
    print(json.dumps(out, indent=1, default=str)[:3000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
