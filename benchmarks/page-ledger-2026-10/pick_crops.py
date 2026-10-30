"""ROADMAP 2.240: choose the places for the six tiles (writes crop_picks.json; crops.py cuts them). Seeded, so re-runnable.

kinds: straddle (ink continuous across a barline column, from measure_cells.py out/*.json), twin (one class boxed from two staves'
cells at IoU >= 0.5, centre in the gap between them), other_line (a flat box filed on one staff standing on ANOTHER staff's line).
"""
import json
import pathlib
import random
import sys

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE))
from measure_cells import iou  # noqa: E402

SL = pathlib.Path("/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/lane-report-slices-20261029-night")


def rows(plate):
    staff, boxes = {}, []
    with open(SL / plate / "observations.jsonl") as fh:
        for line in fh:
            h = line[:200]
            if '"quantity": "staff_lines"' in h:
                r = json.loads(line)
                p = r["subject"].split("/")
                staff[(int(p[1]), int(p[2]), int(p[3]))] = r["value"]
            elif '"quantity": "glyph_box"' in h:
                r = json.loads(line)
                p = r["subject"].split("/")
                bb = (r.get("detail") or {}).get("bbox_page_px")
                if bb:
                    boxes.append(((int(p[1]), int(p[2]), int(p[3])), r["value"][0], bb, r["subject"]))
    return staff, boxes


def main():
    random.seed(240)
    picks = []
    for plate, n in (("litolff", 1), ("brahms", 1)):
        d = json.loads((HERE / "out" / ("%s.json" % plate)).read_text())
        off = [s for s in d["straddles"] if not s["inside"] and s["rows"] >= 3]
        for s in random.sample(off, n):
            picks.append({"plate": plate, "page": s["page"], "kind": "straddle", "x": s["x"], "y": s["y"]})
    staff, boxes = rows("brahms")
    gap_twins, other_line = [], []
    by_pc = {}
    for b in boxes:
        by_pc.setdefault((b[0][0], b[1]), []).append(b)
    for (pg, cls), lst in by_pc.items():
        if not cls.startswith("notehead"):
            continue
        for i in range(len(lst)):
            for j in range(i + 1, len(lst)):
                a, b = lst[i], lst[j]
                if a[0] != b[0] and iou(a[2], b[2]) >= 0.5:
                    gap_twins.append((pg, a, b))
    for key, cls, bb, sub in boxes:
        if cls not in ("tie", "beam"):
            continue
        cy = (bb[1] + bb[3]) / 2
        for k2, v2 in staff.items():
            if k2[0] != key[0] or k2 == key:
                continue
            sp2 = (v2[-1] - v2[0]) / 4.0
            if min(abs(cy - y) for y in v2) <= 0.25 * sp2 and (bb[3] - bb[1]) <= 0.8 * sp2 and v2[0] <= cy <= v2[-1]:
                other_line.append((key[0], cls, bb, sub, k2))
                break
    for pg, a, b in random.sample(gap_twins, 2):
        u = [min(a[2][0], b[2][0]), min(a[2][1], b[2][1]), max(a[2][2], b[2][2]), max(a[2][3], b[2][3])]
        picks.append({"plate": "brahms", "page": pg, "kind": "twin", "box": [int(round(v)) for v in u], "glyphs": [a[3], b[3]], "cls": a[1]})
    for pg, cls, bb, sub, k2 in random.sample(other_line, 2):
        picks.append({"plate": "brahms", "page": pg, "kind": "other_line", "box": [int(round(v)) for v in bb], "glyph": sub, "cls": cls,
                      "on_staff": list(k2)})
    print("candidates: twins %d, other_line %d" % (len(gap_twins), len(other_line)))
    random.shuffle(picks)
    picks.sort(key=lambda p: (p["plate"], p["page"]))
    (HERE / "crop_picks.json").write_text(json.dumps(picks, indent=1))
    print(json.dumps(picks, indent=0)[:1500])


if __name__ == "__main__":
    main()
