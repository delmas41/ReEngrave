"""Is a SLOT's clef a constant of that slot? -- the clef channel's premise.

The clef channel in `probe_reach.py` constrains a staff to slots whose own
staff ON THE REFERENCE SYSTEM read the same clef. That is CONTINUITY -- the
page answering a question about itself, never a table of what instruments are
conventionally written in -- and it is the form the prior art used.

⚠️ IT HAS A PREMISE, AND THE PREMISE IS AN ENGRAVING CLAIM: that a part is
written in ONE clef throughout. This asks the documents whether that is true,
using each staff's slot as the shipped reader already decided it (`Q.SLOT_
INDEX`, `paired_by_name` / `named`) so that no result here depends on any rule
this session wrote.

A disagreement is NOT necessarily a misread: cellos, bassoons and trombones
change clef mid-piece as a matter of course, which is exactly what would make
the premise false.
"""
import collections
import json
import sys

import channels


def main() -> int:
    record = sys.argv[1] if len(sys.argv) > 1 else "litolff"
    staves, counts, raw = channels.load(record)
    ref_sys, ref_names, _ = channels.reference(staves, counts)
    ref = {s.ordinal: s for s in staves if s.sys_key == ref_sys}
    ref_clef = {i: (s.clef if s.clef_outcome == "decided" else None)
                for i, s in ref.items()}

    print("=" * 78)
    print("CLEF STABILITY  --  record %s   md5 %s" % (record, raw["_record_md5"]))
    print("=" * 78)
    print("  reference system p%d/s%d" % ref_sys)
    for i in sorted(ref_clef):
        print("    slot %2d  %-14s clef %s" % (i, ref_names[i] or "-", ref_clef[i]))

    rows = []
    agree = disagree = silent = 0
    by_slot = collections.defaultdict(collections.Counter)
    for s in staves:
        if s.sys_key == ref_sys:
            continue
        if s.slot_outcome != "decided" or s.slot is None:
            continue
        mine = s.clef if s.clef_outcome == "decided" else None
        want = ref_clef.get(s.slot)
        by_slot[s.slot][mine] += 1
        if mine is None or want is None:
            silent += 1
            continue
        if mine == want:
            agree += 1
        else:
            disagree += 1
            rows.append({"subject": s.subject, "slot": s.slot,
                         "slot_name": ref_names[s.slot], "read": mine,
                         "reference_read": want, "margin": s.clef_margin})

    print()
    print("  Over staves the SHIPPED reader already placed (slot decided),")
    print("  excluding the reference system itself:")
    print("    clef agrees with the slot's reference clef   %d" % agree)
    print("    clef DISAGREES                               %d" % disagree)
    print("    one side silent                              %d" % silent)
    print()
    print("  PER SLOT -- what clefs this slot's staves read across the document:")
    for slot in sorted(by_slot):
        seen = dict(by_slot[slot])
        flag = "  <== NOT CONSTANT" if len([k for k in seen if k]) > 1 else ""
        print("    slot %2d  %-14s ref=%-7s  read %s%s"
              % (slot, ref_names[slot] or "-", ref_clef.get(slot), seen, flag))
    if disagree:
        print()
        print("  THE DISAGREEMENTS:")
        for r in rows:
            print("    %-18s slot %2d %-14s read %-7s reference read %-7s (margin %s)"
                  % (r["subject"], r["slot"], r["slot_name"] or "-",
                     r["read"], r["reference_read"], r["margin"]))

    out = channels.HERE / "out" / ("clef-stability-%s.json" % record)
    out.write_text(json.dumps(
        {"record_md5": raw["_record_md5"], "reference_system": list(ref_sys),
         "reference_clefs": {str(k): v for k, v in ref_clef.items()},
         "agree": agree, "disagree": disagree, "silent": silent,
         "per_slot": {str(k): {str(kk): vv for kk, vv in v.items()}
                      for k, v in by_slot.items()},
         "disagreements": rows}, indent=1))
    print()
    print("wrote %s" % out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
