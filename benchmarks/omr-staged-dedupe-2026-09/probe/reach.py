"""REACH: how much duplicated ink does the staged record hold, by family?

⚠️ READ THE DEFINITION BEFORE THE NUMBER. A "duplicate" here is the LEGACY
rule's own definition, borrowed rather than invented: two detections of the
SAME FAMILY whose page boxes overlap by more than
`transcribe._CROSS_STAFF_DUPLICATE_IOU` (imported, never restated) — the
threshold swept over three orchestral works in
`benchmarks/omr-orchestral-e2e/DEDUPE_THRESHOLD.md`.

⚠️ ONE THING IS DELIBERATELY DIFFERENT, AND IT IS THE POINT OF THE PROBE.
`_dedupe_cross_staff_detections` opens its pair test with `if si == sj:
continue` — it is a CROSS-STAFF contest, and a duplicate inside one staff is
outside its scope BY CONSTRUCTION. This probe reports the two populations
APART, because they are different questions with different answers: a
cross-staff pair is a contest between two staves over one piece of ink; a
within-staff pair is one staff holding the same ink twice.

⚠️ The record's `bbox_page_px` is a CORNER box `[x0,y0,x1,y1]` while
`_bbox_iou_xywh` wants a WIDTH box `[x,y,w,h]`. CLAUDE.md records that exact
confusion costing a session, and a fixture at the origin cannot tell the two
spellings apart — so the conversion is explicit here and the tests place their
boxes away from the origin.
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.omr.transcribe import (_CROSS_STAFF_DUPLICATE_IOU,  # noqa: E402
                                  _bbox_iou_xywh)

# Which quantity names the FAMILY of a glyph subject. A subject carries several
# quantities (a notehead subject also carries `glyph_box`), so the family is
# read off the specific quantity and never off a name prefix — the reason
# `gather_glyph_families` is routed by CLASS: a prefix test spells a crescendo
# hairpin into a dynamic word.
FAMILY_QUANTITIES = (
    "notehead_class", "rest", "arc_box", "dynamic_letter", "articulation_mark",
    "fermata_mark", "ornament_mark", "wedge_box", "flag", "aug_dot",
    "keysig_marker", "clef_glyph", "meter_glyph",
)

SCOPES = ("same_cell", "same_staff_other_cell", "same_system_other_staff",
          "same_page_other_system")

# ⚠️ A PAGE-PIXEL BOX IS A FACT ABOUT ONE PAGE. The first run of this probe
# compared every subject with every other and reported 152 "other_system"
# duplicates — page 1's ink overlapping page 3's, because both pages number
# their pixels from their own top-left corner and two pages superimpose
# exactly. Comparison is scoped to one page, which is the same frame discipline
# `Q.ONSET_COLUMN` paid for when a canonical x made two staves agree by
# construction.


def corners_to_xywh(b):
    x0, y0, x1, y1 = b
    return [x0, y0, x1 - x0, y1 - y0]


def page_box(o):
    return (o.get("detail") or {}).get("bbox_page_px")


def addr(subject):
    """(page, system, staff, cell) out of `glyph/p/sys/staff/cell/glyph`."""
    return tuple(subject.split("/")[1:5])


def scope_of(a, b):
    pa, pb = addr(a), addr(b)
    if pa[:3] == pb[:3]:
        return "same_cell" if pa == pb else "same_staff_other_cell"
    if pa[:2] == pb[:2]:
        return "same_system_other_staff"
    return "same_page_other_system"


def duplicate_pairs(observations, iou=_CROSS_STAFF_DUPLICATE_IOU):
    family, conf, boxes, klass = {}, {}, {}, {}
    for o in observations:
        if o["quantity"] in FAMILY_QUANTITIES:
            family.setdefault(o["subject"], o["quantity"])
        elif o["quantity"] == "glyph_conf":
            conf[o["subject"]] = o["value"]
    for o in observations:
        b = page_box(o)
        if b is None:
            continue
        s = o["subject"]
        if s in boxes:
            continue
        boxes[s] = corners_to_xywh(b)
        v = o["value"]
        klass[s] = v[0] if isinstance(v, list) else v

    subjects = [s for s in boxes if s in family]

    # Bucket by vertical position so this stays linear-ish on a dense page,
    # exactly as the legacy function does.
    by_bucket = collections.defaultdict(list)
    BUCKET = 64
    for s in subjects:
        x, y, w, h = boxes[s]
        key = int(y + h / 2.0) // BUCKET
        page = addr(s)[0]          # ⚠️ page pixels are a fact about ONE page
        for k in (key - 1, key, key + 1):
            by_bucket[(page, k)].append(s)

    seen, pairs = set(), []
    for idxs in by_bucket.values():
        for i in range(len(idxs)):
            for j in range(i + 1, len(idxs)):
                a, b = sorted((idxs[i], idxs[j]))
                if (a, b) in seen:
                    continue
                seen.add((a, b))
                if family[a] != family[b]:
                    continue
                v = _bbox_iou_xywh(boxes[a], boxes[b])
                if v <= iou:
                    continue
                pairs.append({
                    "a": a, "b": b, "family": family[a],
                    "scope": scope_of(a, b),
                    "class_a": klass[a], "class_b": klass[b],
                    "same_class": klass[a] == klass[b],
                    "iou": round(v, 4),
                    "conf_a": conf.get(a), "conf_b": conf.get(b),
                    "box_a": boxes[a], "box_b": boxes[b],
                })
    return subjects, family, pairs


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--iou", type=float, default=_CROSS_STAFF_DUPLICATE_IOU)
    ap.add_argument("--json-out")
    args = ap.parse_args(argv)

    obs = json.load(open(args.record))["record"]["observations"]
    subjects, family, pairs = duplicate_pairs(obs, args.iou)

    print(f"glyph subjects with a page box AND a family: {len(subjects)}")
    print(f"IOU threshold (imported from transcribe): {args.iou}")
    print(f"\nduplicate PAIRS: {len(pairs)}")

    tab = collections.Counter((p["family"], p["scope"]) for p in pairs)
    fams = sorted({f for f, _ in tab})
    w = max([len(f) for f in fams] + [10])
    head = f"{'family':<{w}} " + " ".join(f"{s:>23}" for s in SCOPES)
    print("\n" + head + "   total")
    for f in fams:
        row = [tab.get((f, s), 0) for s in SCOPES]
        print(f"{f:<{w}} " + " ".join(f"{v:>23}" for v in row)
              + f"   {sum(row)}")
    row = [sum(v for (_f, s2), v in tab.items() if s2 == s) for s in SCOPES]
    print(f"{'TOTAL':<{w}} " + " ".join(f"{v:>23}" for v in row)
          + f"   {len(pairs)}")

    subj_by_fam = collections.defaultdict(set)
    for p in pairs:
        subj_by_fam[p["family"]].update((p["a"], p["b"]))
    print("\nSUBJECTS in at least one duplicate pair, by family:")
    for f in sorted({family[s] for s in subjects}):
        tot = sum(1 for s in subjects if family[s] == f)
        n = len(subj_by_fam[f])
        print(f"  {f:<20} {n:>5} of {tot:>5}  ({n / tot:.1%})")

    if args.json_out:
        Path(args.json_out).write_text(json.dumps(
            {"iou": args.iou, "n_subjects": len(subjects), "pairs": pairs},
            indent=1))
        print(f"\nwrote {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
