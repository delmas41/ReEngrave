"""ROADMAP 2.206c step 2 (docs/measuring.md fail-fast rule): the refusal reason of EVERY note present OFF and absent ON, grouped by reason.

    python3 benchmarks/staff-eraser-2026-10/lost_notes.py WORKDIR PLATE [--json OUT]

Reads WORKDIR/{plate}.{off,on}.symbols.json (the exported notes, by glyph key) and the arms' `*.gathered.record.json` (the verdicts).
A note's reason = for the glyph, the LAST verdict per quantity (`duration`, `notehead`, ...) that is not a plain decision, as `quantity:outcome:reason`,
plus how the ON arm's verdict differs from the OFF arm's. Reports the group table and one line per lost glyph.
"""
import collections, json, sys

def load(path):
    return json.load(open(path))

def notes(path):
    s = load(path)
    return {h["rg"]: h for h in s["hosts"] if h.get("kind") == "note"}

def verdict_index(rec):
    idx = collections.defaultdict(dict)
    for v in rec["verdicts"]:
        idx[v["subject"]][v["quantity"]] = v
    return idx

def summary(idx, rg):
    out = {}
    for q, v in idx.get(rg, {}).items():
        if q in ("duration", "notehead", "is_a_notehead", "note", "head_precision", "glyph_owner", "stem_value", "pitch"):
            out[q] = f'{v["outcome"]}:{v.get("reason")}'
    return out

def main():
    work, plate = sys.argv[1], sys.argv[2]
    off, on = notes(f"{work}/{plate}.off.symbols.json"), notes(f"{work}/{plate}.on.symbols.json")
    ridx = {a: verdict_index(load(f"{work}/{plate}.{a}.gathered.record.json")["record"]) for a in ("off", "on")}
    lost = sorted(set(off) - set(on))
    groups = collections.defaultdict(list)
    rows = []
    for rg in lost:
        so, sn = summary(ridx["off"], rg), summary(ridx["on"], rg)
        diff = {q: (so.get(q), sn.get(q)) for q in set(so) | set(sn) if so.get(q) != sn.get(q)}
        key = "; ".join(f"{q}: {a} -> {b}" for q, (a, b) in sorted(diff.items())) or "verdicts identical (dropped later: EVALUATE/INFER/EXPORT)"
        groups[key].append(rg)
        rows.append({"rg": rg, "off": so, "on": sn, "reason": key, "type": off[rg].get("type")})
    print(f"{plate}: {len(lost)} notes present OFF, absent ON ({len(off)} OFF, {len(on)} ON)")
    for k, v in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        print(f"  {len(v):3d}  {k}\n        {', '.join(v)}")
    if "--json" in sys.argv:
        json.dump(rows, open(sys.argv[sys.argv.index("--json") + 1], "w"), indent=1)

if __name__ == "__main__":
    main()
