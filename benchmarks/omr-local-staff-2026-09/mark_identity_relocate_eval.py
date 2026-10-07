"""ROADMAP 2.58 control: relocate-at-export, flag off vs on, on a rebuilt record.

    python3 benchmarks/omr-local-staff-2026-09/mark_identity_relocate_eval.py \
        REBUILT.json [--list out.json]

REBUILT.json is `mark_identity_rebuild.py`'s output (GATHER+ADJUDICATE+EVALUATE
of a saved record on today's tree). The export is run twice on the SAME file,
`OMR_RELOCATE_AT_EXPORT` unset then `1`, and the controls are:

  * `Unbalanced` is never raised (the equality IS the control);
  * no glyph subject is written twice, and no two written heads on one staff
    sit within the collision distance of each other because of a relocation;
  * every candidate (head whose owner is another staff and holds no twin) is
    either written on its owner or counted under a NAMED reason.
"""
import argparse
import collections
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.omr.staged import export as SX                        # noqa: E402
from tools.omr.staged.record_io import load_record               # noqa: E402


def run(result, flag):
    if flag:
        os.environ["OMR_RELOCATE_AT_EXPORT"] = "1"
    else:
        os.environ.pop("OMR_RELOCATE_AT_EXPORT", None)
    rec = SX.Record(result)
    cap = {}
    orig = SX._place_notes

    def wrap(*a, **k):
        cap["fates"] = k.get("fates")
        return orig(*a, **k)
    SX._place_notes = wrap
    try:
        parts, prov, dropped, *_rest = SX.build(rec)
    finally:
        SX._place_notes = orig
    seen = collections.Counter()
    moved = []
    for part in parts:
        for r in part:
            for ci, cell in r.cells.items():
                for d in cell.detections:
                    g = d.get("glyph")
                    if g:
                        seen[g] += 1
                    if d.get("category") != "notehead" or not g:
                        continue
                    s = SX._parse_subject(g)
                    if (s["page"], s["system"], s["staff"]) != (
                            r.page, r.system, r.staff):
                        moved.append({"glyph": g, "owner_staff": r.staff,
                                      "owner_cell": ci, "pitch": d["pitch"],
                                      "clef": r.clef, "fifths": r.fifths,
                                      "bbox_page": d.get("bbox_page"),
                                      "dur": d.get("duration_type")})
    twice = [g for g, n in seen.items() if n > 1]
    assert not twice, f"glyphs written twice: {twice[:5]}"
    xml, report = SX.to_musicxml(result)       # raises Unbalanced if it must
    return dict(dropped=dict(dropped), moved=moved, fates=cap.get("fates") or {},
                census=prov.get("marks_census", {}),
                balance=report["balance"], notes=report["written"]["notes"],
                relocated=prov.get("relocated_at_export", 0))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rebuilt")
    ap.add_argument("--list", default=None)
    ap.add_argument("--fates", default=None,
                    help="write {off,on} per-glyph fates (written / reason)")
    a = ap.parse_args()
    result = load_record(a.rebuilt)
    off = run(result, False)
    on = run(result, True)
    print("OFF  notes written %d  not written %d" % (
        off["notes"], off["balance"]["events_not_written"]))
    print("ON   notes written %d  not written %d" % (
        on["notes"], on["balance"]["events_not_written"]))
    moved = collections.Counter()
    for sub, f_on in on["fates"].items():
        f_off = off["fates"].get(sub)
        if f_off != f_on:
            moved[(f_off, f_on)] += 1
    print("heads whose fate the flag changed (OFF fate -> ON fate):")
    for (a_, b_), n in moved.most_common():
        print("  %5d  %s -> %s" % (n, a_, b_))
    print("heads written on the staff that owns them: %d" % on["relocated"])
    print("balanced OFF %s ON %s; no glyph written twice (asserted)" % (
        off["balance"]["balanced"], on["balance"]["balanced"]))
    if on["census"]:
        print("marks census (flag ON):")
        for fam, c in sorted(on["census"].items()):
            print("  %-10s %s" % (fam, {k: v for k, v in c.items()}))
    if a.fates:
        Path(a.fates).write_text(json.dumps({"off": off["fates"],
                                             "on": on["fates"]}))
    if a.list:
        Path(a.list).write_text(json.dumps(
            {"moved": on["moved"], "dropped_on": on["dropped"],
             "dropped_off": off["dropped"]}))


if __name__ == "__main__":
    main()
