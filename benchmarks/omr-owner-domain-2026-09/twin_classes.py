"""ROADMAP 2.6 — WHICH AXIS handed each newly-contested glyph in, and whether
the two twins disagree about the HEAD TYPE.

⚠️ THE QUESTION THIS ANSWERS IS THE ONE §10 FLAGGED AS THE CHANGE'S ONE RISK.
`noteheadBlack…` and `noteheadHalf…` are both `category="notehead"`, so the
category test admits a pair the smufl-name test rejected — and if the loser's
DROP settled the head type, a duration would have been chosen by an ownership
decision. It does not: `adjudicate_duration` reads `Q.NOTEHEAD_CLASS` on the
GLYPH'S OWN subject (`rhythm._head_class`), the loser's row stays on the record
(export REFUSES it, `transcribe` DELETES it), and nothing copies a class across
a contest. This file counts how often the case arises at all.

It reads the record and `regather_ownership.py`'s `--json`, and decides
nothing: for every subject the arm gave a band row and the base did not, it
names the twin(s) that let it in and splits them by how the two spellings
differ.

    python3 benchmarks/omr-owner-domain-2026-09/twin_classes.py \\
        <record.json> out/<name>.json
"""
from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

for _p in list(Path(__file__).resolve().parents):
    if (_p / "tools" / "omr" / "staged" / "record_io.py").exists():
        sys.path.insert(0, str(_p))
        break

from tools.omr.staged.record_io import load_record          # noqa: E402
from tools.omr.staged.gather import CONTEST_IOU, _iou       # noqa: E402

BASE_IOU = 0.5          # what the staged gather restated before ROADMAP 2.6


def head_family(name: str) -> str:
    """`noteheadBlackOnLine` -> `noteheadBlack`. The suffix is the head's
    position RELATIVE TO A STAFF, i.e. the quantity in dispute."""
    for suf in ("OnLine", "InSpace"):
        if name.endswith(suf):
            return name[: -len(suf)]
    return name


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    record_path, arm_json = argv[0], argv[1]
    added = set(json.loads(Path(arm_json).read_text())["band_subjects_added"])
    rec = load_record(record_path)["record"]

    glyphs = {}
    for o in rec["observations"]:
        if o["quantity"] != "glyph_box":
            continue
        d = o.get("detail") or {}
        box = d.get("bbox_page_px")
        if box is None:
            continue
        glyphs[o["subject"]] = (str(o["value"][0]), str(d.get("category")),
                                [float(v) for v in box])
    by_system = collections.defaultdict(list)
    for sub in glyphs:
        p = sub.split("/")
        by_system[(p[1], p[2])].append(sub)

    axis = collections.Counter()
    split = collections.Counter()
    cat = collections.Counter()
    examples = collections.defaultdict(list)
    for sub in sorted(added):
        name, category, box = glyphs[sub]
        p = sub.split("/")
        best = None
        for other in by_system[(p[1], p[2])]:
            if other == sub or other.split("/")[3] == p[3]:
                continue
            oname, ocat, obox = glyphs[other]
            if ocat != category:
                continue
            v = _iou(box, obox)
            if v <= CONTEST_IOU:
                continue
            if best is None or v > best[0]:
                best = (v, other, oname)
        if best is None:
            axis["⚠️ no admitting twin found (should be 0)"] += 1
            continue
        v, other, oname = best
        cat[category] += 1
        if oname == name and v > BASE_IOU:
            axis["⚠️ neither axis (should be 0)"] += 1
        elif oname == name:
            axis["the IoU floor alone (same name, 0.3 < IoU <= 0.5)"] += 1
        elif v > BASE_IOU:
            axis["the category test alone (IoU already over 0.5)"] += 1
        else:
            axis["BOTH axes were needed"] += 1
        if oname == name:
            split["identical smufl name"] += 1
        elif head_family(oname) == head_family(name):
            split["SAME head, OnLine vs InSpace"] += 1
        elif (name.startswith("notehead") and oname.startswith("notehead")):
            split["both noteheads, head TYPE differs"] += 1
            examples["head TYPE differs"].append((sub, name, other, oname,
                                                  round(v, 3)))
        else:
            split["same category, different class"] += 1
            examples["same category, different class"].append(
                (sub, name, other, oname, round(v, 3)))

    print(f"{len(added)} subjects gained a band row")
    print("\nWHICH AXIS ADMITTED IT")
    for k, n in axis.most_common():
        print(f"  {k:52s} {n:5d}")
    print("\nHOW THE TWO SPELLINGS DIFFER")
    for k, n in split.most_common():
        print(f"  {k:52s} {n:5d}")
    print("\nBY CATEGORY")
    for k, n in cat.most_common():
        print(f"  {k:52s} {n:5d}")
    for k, rows in examples.items():
        print(f"\n{k} — first 10 of {len(rows)}")
        for sub, name, other, oname, v in rows[:10]:
            print(f"  {sub:22s} {name:24s}  vs  {other:22s} {oname:24s}"
                  f"  IoU {v}")
    out = Path(arm_json).with_name(Path(arm_json).stem + "-twins.json")
    out.write_text(json.dumps(
        {"record": record_path, "added": len(added), "axis": dict(axis),
         "spelling": dict(split), "by_category": dict(cat),
         "head_type_pairs": examples.get("head TYPE differs", []),
         "cross_class_pairs": examples.get("same category, different class",
                                           [])}, indent=1))
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
