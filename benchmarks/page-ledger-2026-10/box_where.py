"""ROADMAP 2.240: where each detector box stands relative to the staves (record rows only, page px; STAGED GATHER rows).

Per box: OWN = centre inside its own staff's five lines +-0.5 sp; PAD = in its own cell but outside every staff band; ON_OTHER = centre
inside ANOTHER staff's band (+-0.5 sp) -- that staff's ink seen through this cell's pad; ON_OTHER_LINE = flat and within 0.25 sp of one
of that staff's lines (the neighbour's staff line, which this cell's eraser does not remove, boxed as a mark).
Usage: python3 benchmarks/page-ledger-2026-10/box_where.py litolff|brahms
"""
import collections
import json
import pathlib
import sys

SL = pathlib.Path("/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/lane-report-slices-20261029-night")


def main(plate):
    staff = {}
    boxes = []
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
                    boxes.append(((int(p[1]), int(p[2]), int(p[3])), r["value"][0], bb))
    by_page = collections.defaultdict(list)
    for k, v in staff.items():
        by_page[k[0]].append((k, v))
    where = collections.Counter()
    cls_other = collections.Counter()
    cls_otherline = collections.Counter()
    for key, cls, bb in boxes:
        cy = (bb[1] + bb[3]) / 2
        own = staff.get(key)
        if not own:
            where["no_staff"] += 1
            continue
        sp = (own[-1] - own[0]) / 4.0
        if own[0] - 0.5 * sp <= cy <= own[-1] + 0.5 * sp:
            where["own_band"] += 1
            continue
        hit = None
        for k2, v2 in by_page[key[0]]:
            if k2 == key:
                continue
            sp2 = (v2[-1] - v2[0]) / 4.0
            if v2[0] - 0.5 * sp2 <= cy <= v2[-1] + 0.5 * sp2:
                hit = (k2, v2, sp2)
                break
        if hit is None:
            where["pad_gap"] += 1
            continue
        where["on_other_band"] += 1
        cls_other[cls] += 1
        if min(abs(cy - y) for y in hit[1]) <= 0.25 * hit[2] and (bb[3] - bb[1]) <= 0.8 * hit[2]:
            where["on_other_line_flat"] += 1
            cls_otherline[cls] += 1
    print(plate, dict(where), "boxes", len(boxes))
    print(" centre in ANOTHER staff's band, by class:", cls_other.most_common(14))
    print(" ... flat and on that staff's line:", cls_otherline.most_common(8))


if __name__ == "__main__":
    main(sys.argv[1])
