"""Population table from replay rows.  usage: pop.py rows.json [rows2.json ...]"""
import json
import sys
import collections

for path in sys.argv[1:]:
    rows = json.load(open(path))
    kept = [r for r in rows if not r["refused"]]
    print("==", path, "arcs", len(rows), "kept (not refused)", len(kept))
    c = collections.Counter()
    why = collections.Counter()
    for r in kept:
        rule = r.get("rule") or {}
        tn = rule.get("two_note") or {}
        det = r["det"]
        if not tn.get("evaluated"):
            why[tn.get("why")] += 1
        c[(det, r["kind"] or "ABSTAIN", rule.get("rule") or r["reason"])] += 1
    print(" not evaluated, by why:", dict(why))
    print(" (detector class, final kind, reason):")
    for k, v in sorted(c.items(), key=lambda kv: -kv[1]):
        print("   ", k, v)
    # evaluated two-note readings by relation
    rel = collections.Counter()
    for r in kept:
        tn = ((r.get("rule") or {}).get("two_note")) or {}
        if tn.get("evaluated"):
            rel[(r["det"], "between" if tn["between"] else "two_note",
                 tn.get("relation"), tn.get("accidental"))] += 1
    print(" evaluated (detector, between?, relation, accidental):")
    for k, v in sorted(rel.items(), key=lambda kv: -kv[1]):
        print("   ", k, v)
    st = collections.Counter()
    for r in kept:
        s = (r.get("rule") or {}).get("stack")
        if s:
            st[(r["det"], s.get("role"), s.get("side"), r["kind"], (r.get("rule") or {}).get("conflict"))] += 1
    print(" stacked (detector, role, side, final, conflict):")
    for k, v in sorted(st.items(), key=lambda kv: -kv[1]):
        print("   ", k, v)
    changed = [r for r in kept if (r["kind"] or "ABSTAIN") != r["det"]]
    print(" CHANGED arcs:", len(changed), collections.Counter((r["det"], r["kind"] or "ABSTAIN") for r in changed))
