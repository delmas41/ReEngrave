"""Stream a whole-movement record and count EVERY verdict by (decider, outcome, value, reason).

Part of ROADMAP 2.207 (the rule page).  Reads only.  Superseded verdicts ARE counted:
"how often does this rule fire" is a question about the rule's own verdict, and an
ADJUDICATE abstention later filled by INFER (`fill_part_key`) or EVALUATE is still a
firing of that ADJUDICATE rule.  (`superseded` is reported for context.)
Gather-side refusals are verdicts too (`*_is_not_*` deciders, value True), so one
pass covers adjudicators and filters.  Usage:
    python3 count_fires.py REC.record.json OUT.json
"""
import collections, json, sys
import ijson


def count(path):
    seen = {}
    superseded = set()
    with open(path, "rb") as f:
        for v in ijson.items(f, "record.verdicts.item", use_float=True):
            val = v.get("value")
            vb = val if isinstance(val, bool) else None
            seen[v["id"]] = (v.get("decider"), v.get("outcome"), v.get("reason"), vb)
            s = v.get("supersedes")
            if s:
                for x in (s if isinstance(s, list) else [s]):
                    superseded.add(x)
    c = collections.Counter(seen.values())
    rows = [{"decider": d, "outcome": o, "reason": r, "value": b, "n": n}
            for (d, o, r, b), n in sorted(c.items(), key=lambda kv: (str(kv[0][0]), -kv[1]))]
    return {"verdicts_total": len(seen), "superseded": len(superseded & set(seen)), "rows": rows}


if __name__ == "__main__":
    out = count(sys.argv[1])
    json.dump(out, open(sys.argv[2], "w"), separators=(",", ":"))
    print(sys.argv[1].split("/")[-1], out["verdicts_total"], out["superseded"], len(out["rows"]))
