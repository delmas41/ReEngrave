"""ROADMAP 2.290 r1 -- READ-ONLY: group the head-box fates of `replay_head_fates.py` runs. Boxes, physical marks (mark groups), twins, fates by reason."""
import collections, json, sys

TWIN = ("owned_by_another_staff", "mark_group_duplicate", "not_a_notehead:notehead_is_a_duplicate_box", "not_a_notehead:stacked_head_duplicate",
        "not_a_notehead:is_a_rest_twin")
VALUE = ("duration_narrowed", "chord_value_undecided", "no_pitch", "duration_abstained", "unread:wide_box_unread")

def cls(f):
    if f.startswith("written"): return "written"
    if f in TWIN: return "twin_copy"
    if f in VALUE: return "read_but_value_or_pitch_unwritten"
    return "refused_as_not_a_head_or_claimed"

def main(paths):
    tot = collections.Counter(); byfate = collections.Counter(); marks = collections.Counter()
    for p in paths:
        d = json.load(open(p))
        rows = d["rows"]
        print(d["plate"], d["pages"], "boxes", len(rows))
        c = collections.Counter(cls(r["fate"]) for r in rows)
        mc = (d["marks_census"] or {}).get("notehead") or {}
        print("   by class:", dict(c), "| marks", mc.get("marks"), "detected_more_than_once", mc.get("detected_more_than_once"), "written_once", mc.get("written_once"),
              "marks_with_no_written_member", mc.get("counted_under_a_reason"))
        for k, v in c.items(): tot[(d["plate"], k)] += v
        for r in rows: byfate[(d["plate"], r["fate"])] += 1
        for k in ("marks", "detected_more_than_once", "written_once", "counted_under_a_reason"): marks[(d["plate"], k)] += mc.get(k, 0)
    print("\nTOTAL by plate/class", dict(tot))
    print("TOTAL marks", dict(marks))
    for plate in ("litolff", "brahms"):
        print("\n", plate, "box fates")
        for (pl, f), n in sorted(byfate.items(), key=lambda kv: -kv[1]):
            if pl == plate: print("  %5d  %s" % (n, f))

main(sys.argv[1:])
