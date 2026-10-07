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
    cand = (off["dropped"].get("owned_by_another_staff", 0)
            - on["dropped"].get("owned_by_another_staff", 0))
    print("OFF  notes written %d  not written %d  %s" % (
        off["notes"], off["balance"]["events_not_written"],
        off["dropped"]))
    print("ON   notes written %d  not written %d  %s" % (
        on["notes"], on["balance"]["events_not_written"], on["dropped"]))
    named = {k: v for k, v in on["dropped"].items()
             if k.startswith("relocation_") or k in (
                 "owner_staff_has_no_measures", "staff_not_identified")}
    print("candidates (owner holds no twin): %d" % cand)
    print("  written on the owner: %d" % on["relocated"])
    print("  counted under a named reason: %s" % named)
    print("  written nowhere (candidates - written - counted): %d" % (
        cand - on["relocated"]
        - sum(v for k, v in named.items() if k.startswith("relocation_"))
        - (on["dropped"].get("owner_staff_has_no_measures", 0)
           - off["dropped"].get("owner_staff_has_no_measures", 0))
        - (on["dropped"].get("staff_not_identified", 0)
           - off["dropped"].get("staff_not_identified", 0))))
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
