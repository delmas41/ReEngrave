"""ROADMAP 2.292 tallies from analyze.py JSON.
    python3 tally.py X.json [--rows]

1. Blue notes by reason (distinct note = one glyph subject; a note may carry several reasons).
2. Per staff-system that has a FILLED key / clef: the first upstream cause (the abstention reason of the superseded verdict + what the
   staff read + the key-object / marker evidence), and the notes it made blue.
"""
import collections
import json
import sys


def staff_of(sub):
    p = sub.split("/")
    return "staff/%s/%s/%s" % (p[1], p[2], p[3])


def cat(r):
    b = r.split("[")[0]
    if b == "key_fill":
        return "key_fill"
    if b == "clef_fill":
        return "clef_fill"
    if b.startswith("pitch_infer"):
        return "pitch_infer_other"
    if b.startswith("accidental_or_oneink"):
        return "accidental"
    if b.startswith("far:"):
        return "far"
    if b.startswith("value:"):
        return "value"
    if b.startswith("claim:"):
        return "claim(head presence)"
    return b


def reasons_for(s):
    cs = set(cat(r) for r in s["reasons"])
    f = s.get("first")
    if f and not cs:
        # a late mark applied after the reasons above (partial-bar onset, voice split, claimed gap)
        cs.add("bar_structure(" + f + ")")
    return cs


def notes_table(d, label):
    S = [s for s in d["symbols"] if not s["is_rest"]]
    blue = [s for s in S if s["blue"]]
    c = collections.Counter()
    excl = collections.Counter()
    for s in blue:
        cs = reasons_for(s)
        for x in cs:
            c[x] += 1
        excl[tuple(sorted(cs))] += 1
    pitch = [s for s in blue if {"key_fill", "clef_fill"} & reasons_for(s)]
    only = [s for s in blue if reasons_for(s) <= {"key_fill", "clef_fill"}]
    hidden = [s for s in pitch if (s.get("first") not in ("fill_part_key", "fill_clef_gap"))]
    print("== %s  pages %s  distinct notes written %d, blue %d (%.1f%%)" % (label, d["pages"], len(S), len(blue), 100.0 * len(blue) / max(1, len(S))))
    print("   blue for PITCH (key and/or clef filled): %d = %.1f%% of notes, %.1f%% of blue" % (len(pitch), 100.0 * len(pitch) / max(1, len(S)), 100.0 * len(pitch) / max(1, len(blue))))
    print("   blue ONLY for pitch (no other reason): %d" % len(only))
    print("   pitch reason HIDDEN behind another first-reported rule: %d" % len(hidden))
    for k, n in c.most_common():
        print("     any-reason  %-40s %4d" % (k, n))
    print("   exclusive combinations:")
    for k, n in excl.most_common():
        print("     %4d  %s" % (n, "+".join(k) or "(none)"))
    return blue


def staff_table(d, label, show=True):
    S = d["staffs"]
    sym = collections.defaultdict(list)
    for s in d["symbols"]:
        if not s["is_rest"]:
            sym[staff_of(s["sub"])].append(s)
    rows = []
    for k, v in sorted(S.items(), key=lambda kv: tuple(int(x) for x in kv[0].split("/")[1:])):
        kf = v["key"] and v["key"][0]["decider"].startswith("infer")
        cf = v["clef"] and v["clef"][0]["decider"].startswith("infer")
        if not (kf or cf):
            continue
        notes = sym.get(k, [])
        kb = sum(1 for s in notes if s["blue"] and "key_fill" in reasons_for(s))
        cb = sum(1 for s in notes if s["blue"] and "clef_fill" in reasons_for(s))
        row = {"staff": k, "notes": len(notes), "blue_key": kb, "blue_clef": cb}
        if kf:
            f = v["key"][0]
            p = v["key"][-1]
            pd = p.get("detail") or {}
            row.update(key_fill=f["value"], key_tier=(f.get("detail") or {}).get("tier"), offset=(f.get("detail") or {}).get("fifths_offset"),
                       key_prior=p["reason"], staff_read=pd.get("written_fifths"), read_by=pd.get("read_by"),
                       marker_slots=pd.get("keysig_marker_slots"), disagreeing=[(x["reader"], x["fifths"]) for x in pd.get("disagreeing_readers", [])],
                       system_tally=pd.get("system_tally"), slot_from_infer=(f.get("detail") or {}).get("part_from_an_inference"))
        if cf:
            f = v["clef"][0]
            p = v["clef"][-1]
            row.update(clef_fill=f["value"], clef_tier=f["reason"], clef_prior="%s:%s" % (p["outcome"], p["reason"]),
                       clef_slot_from_infer=(f.get("detail") or {}).get("part_from_an_inference"),
                       clef_inst=(f.get("detail") or {}).get("instrument"))
        rows.append(row)
    if show:
        print("== %s staff-systems with a filled key or clef: %d of %d" % (label, len(rows), len(S)))
        for r in rows:
            print("  ", json.dumps(r, default=str))
    return rows


if __name__ == "__main__":
    d = json.load(open(sys.argv[1]))
    notes_table(d, d["plate"])
    staff_table(d, d["plate"], show="--rows" in sys.argv)
