"""night 2026-10-08 read, step 3: NEW (`...20261008-night`, main 178d1035, defaults + `OMR_STEM_OWNER` ON, numeral_shaped
refusal, staccato from any staff's note, mark-group no-owner rules) vs BASE (`...20261007-day`, main 2baf8875),
GATHER+ADJUDICATE verdicts only, numbers first.  Reads only the small JSONs `day_1007_extract.py` and `night_1007_replay.py`
wrote (x/<doc>-<tag>.json, x/rep_{new,base}_<short>.json, x/truth.json).  Reuses `day_1007_report` (far heads, owners, dots,
marks, per-quantity diff) with the tags swapped and adds the 10-08 blocks: owner changes by rule and how many went to the
FARTHER staff, `numeral_shaped` refusals, dot roles.

  python3 night_1008_report.py <dir holding x/> [--docs a,b]
"""
from __future__ import annotations
import collections, json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import day_1007_report as DR
import night_1007_report as NR
import night_1006_report as R6
import overnight_1004_report as R

NEWTAG, BASETAG = "20261008-night", "20261007-day"
DR.NEWTAG, DR.BASETAG = NEWTAG, BASETAG
NR.R6.NEWTAG, NR.R6.BASETAG = NEWTAG, BASETAG


def staff_dist(lines, cy):
    top, bot = min(lines), max(lines)
    return 0.0 if top <= cy <= bot else min(abs(cy - top), abs(cy - bot))


def sp_of(lines):
    return (lines[-1] - lines[0]) / 4.0


def stem_block(N, B):
    """Owner verdicts matched BY SUBJECT (control: same class and box). Transition counts by (BASE reason -> NEW reason) and
    how many of the heads that CHANGED owner went to the staff farther from the head."""
    out = {}
    tr = collections.Counter()
    far = collections.Counter()
    ctrl = collections.Counter()
    ex = collections.defaultdict(list)
    sl = N["staff_lines"]
    for s, g in N["glyphs"].items():
        o = g.get("own")
        b = B["glyphs"].get(s)
        if b is None:
            ctrl["subject not in BASE"] += 1
            continue
        if b.get("cls") != g.get("cls") or any(abs(x - y) > 0.5 for x, y in zip(b.get("box", [0] * 4), g.get("box", [0] * 4))):
            ctrl["box/class differs"] += 1
            continue
        ctrl["subject matched"] += 1
        bo = b.get("own")
        if not o and not bo:
            continue
        if (o or {}).get("outcome") == (bo or {}).get("outcome") and (o or {}).get("value") == (bo or {}).get("value"):
            if (o or {}).get("reason") != (bo or {}).get("reason"):
                tr[f"same owner, reason {bo['reason']} -> {o['reason']}"] += 1
            continue
        key = f"{(bo or {}).get('outcome')}:{(bo or {}).get('reason')} -> {(o or {}).get('outcome')}:{(o or {}).get('reason')}"
        tr[key] += 1
        if len(ex[key]) < 6:
            ex[key].append(s)
        if o and bo and o["outcome"] == "decided" and bo["outcome"] == "decided" and g.get("box"):
            cy = (g["box"][1] + g["box"][3]) / 2
            ln, lb = sl.get(o["value"]), sl.get(bo["value"])
            if ln and lb:
                dn, db = staff_dist(ln, cy), staff_dist(lb, cy)
                f = "farther" if dn > db + 0.25 * sp_of(ln) else ("nearer" if dn < db - 0.25 * sp_of(ln) else "about equal")
                far[f"{(o or {}).get('reason')}: moved to {f} staff"] += 1
    out["control"] = dict(ctrl)
    out["transitions"] = dict(tr.most_common())
    out["moved_by_new_rule_and_distance"] = dict(far.most_common())
    out["examples"] = dict(ex)
    for name, D in (("NEW", N), ("BASE", B)):
        c = collections.Counter()
        for g in D["glyphs"].values():
            o = g.get("own")
            if o:
                c[f"{o['outcome']}:{o['reason']}"] += 1
        out[f"owner_by_reason_{name}"] = dict(c.most_common())
    return out


def numeral_block(N, B):
    out = {}
    for name, D in (("NEW", N), ("BASE", B)):
        c = collections.Counter()
        for s, g in D["glyphs"].items():
            fa = g.get("fh_abs") or {}
            lr = str(fa.get("ledger_reason", ""))
            npv = g.get("np") or {}
            if "numeral_shaped" in lr or "numeral_shaped" in json.dumps(npv):
                c["numeral_shaped"] += 1
                c["numeral_shaped, class " + str(g.get("cls"))] += 1
            if lr.startswith("not_a_note"):
                c["not_a_note total"] += 1
        out[name] = dict(c)
    return out


def main(d, docs):
    d = Path(d)
    summ = {}
    for doc in docs:
        N = json.loads((d / "x" / f"{doc}-{NEWTAG}.json").read_text())
        B = json.loads((d / "x" / f"{doc}-{BASETAG}.json").read_text())
        print("\n" + "=" * 100 + f"\n{doc}")
        summ[doc] = dict(stem=stem_block(N, B), numeral=numeral_block(N, B))
        print("STEM / OWNER", json.dumps(summ[doc]["stem"], indent=1))
        print("NUMERAL", json.dumps(summ[doc]["numeral"], indent=1))
    (d / "report_night1008_extra.json").write_text(json.dumps(summ, indent=1, default=str))
    DR.main(d, docs)


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[0], tuple(a[a.index("--docs") + 1].split(",")) if "--docs" in a else R.DOCS)
