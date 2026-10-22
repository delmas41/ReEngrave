"""ROADMAP 2.12f ROUND 2 -- BASE vs ROUND 2, one tree's rule at a time, one record.

    python3 benchmarks/omr-shape-role-2026-09/compare_artic_r2.py \
        <base.json> <r2.json> [--round1 <round1 arm.json>] [--out <json>]

Inputs are `readjudicate_artic_side.py` outputs. BASE is the rule as it stood
before 2.12f (nearest in x on the class's side); ROUND1 is the arm that recorded
`nearest_declared_side_head`; R2 is the owner by the NOTEHEAD side of the stem.

Prints the CONTROL line each side printed first (CLAUDE.md Sec.6b), then:

  * the transition table, base (outcome/reason) -> r2 (outcome/reason), with
    decided -> decided split into SAME head / MOVED head;
  * the INVARIANTS the change promises, each a number that can fail:
      - no base-ABSTAINED mark becomes decided (the class still GATES the
        candidates and the x window is unchanged, so r2's candidates are a subset
        of base's);
      - every r2-decided owner's measured side equals the class's side;
      - the fermata owner's outcome and value are identical;
  * where a MOVED owner went: to the nearest declared-side head round 1 recorded,
    or elsewhere;
  * r2-decided by rule (notehead side / stem side) and r2 abstentions by reason;
  * the cross-staff question: of r2's abstained marks, how many have a DECIDED
    same-ink twin in another cell (owned via the neighbour's cell), and how many
    decided marks have a decided twin whose owner differs (one mark, two owners).
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib


def _key(v):
    return "none" if not v else "%s/%s" % (v["outcome"], v["reason"])


def compare(base, r2, round1=None):
    b = {r["subject"]: r for r in base["articulations"]}
    a = {r["subject"]: r for r in r2["articulations"]}
    r1 = {r["subject"]: r for r in round1["articulations"]} if round1 else {}
    out = {"marks": len(b)}
    trans = collections.Counter()
    inv = collections.Counter()
    moved = []
    for s, br in b.items():
        ar = a[s]
        bo, ao = br["owner"], ar["owner"]
        bk, ak = _key(bo), _key(ao)
        if bo["outcome"] == "decided" and ao["outcome"] == "decided":
            ak = "decided/%s (%s head)" % (
                ao["reason"], "SAME" if ao["value"] == bo["value"] else "MOVED")
            if ao["value"] != bo["value"]:
                touching = (r1.get(s, {}).get("owner") or {}).get(
                    "detail", {}).get("nearest_declared_side_head")
                moved.append({"subject": s, "from": bo["value"], "to": ao["value"],
                              "round1_nearest_declared_side_head": touching,
                              "to_is_that_head": (ao["value"] == touching)
                              if touching else None})
        trans[(bk, ak)] += 1
        if bo["outcome"] != "decided" and ao["outcome"] == "decided":
            inv["VIOLATION base_abstained_became_decided"] += 1
        if ao["outcome"] == "decided":
            d = ao["detail"]
            inv["decided_measured_side_equals_class"
                if d.get("measured_side") == d.get("suffix_side")
                else "VIOLATION decided_measured_side_differs_from_class"] += 1
    out["transitions"] = {"%s -> %s" % k: v for k, v in sorted(trans.items())}
    out["invariants"] = dict(sorted(inv.items()))
    mv = collections.Counter(
        "to the round-1 nearest declared-side head" if m["to_is_that_head"]
        else "to another head" if m["to_is_that_head"] is False
        else "round-1 record absent" for m in moved)
    out["moved_owners"] = {"n": len(moved), "where": dict(mv)}

    rule = collections.Counter()
    for r in r2["articulations"]:
        o = r["owner"]
        if o["outcome"] == "decided":
            d = o["detail"]
            rule["decided:%s" % d["stem_rule"]] += 1
            rule["decided:two_voice" if d["two_voice"] else "decided:single_voice"] += 1
        else:
            rule["%s:%s" % (o["outcome"], o["reason"])] += 1
    out["r2_by_rule_and_reason"] = dict(sorted(rule.items()))

    # cross-staff / twin pairing on the r2 verdicts
    twin = collections.Counter()
    for r in r2["articulations"]:
        o = r["owner"]
        tw = (o["detail"] or {}).get("same_ink_twins") or []
        dec_twins = [a[t] for t in tw if t in a and a[t]["owner"]["outcome"] == "decided"]
        if o["outcome"] != "decided":
            twin["abstained"] += 1
            if tw:
                twin["abstained, has a same-ink twin in another cell"] += 1
            if dec_twins:
                twin["abstained, a twin is DECIDED (owned via the neighbour's cell)"] += 1
        else:
            twin["decided"] += 1
            if dec_twins:
                twin["decided AND a twin is decided (one mark, two owners)"] += 1
                if any(t["owner"]["value"] != o["value"] for t in dec_twins):
                    twin["   ... the two owners differ"] += 1
    out["twins"] = dict(sorted(twin.items()))

    bf = {r["subject"]: r for r in base["fermatas"]}
    af = {r["subject"]: r for r in r2["fermatas"]}
    fc = collections.Counter()
    for s, br in bf.items():
        bo, ao = br["owner"], af[s]["owner"]
        fc["owner_identical" if (bo["outcome"], bo["reason"], bo["value"]) ==
           (ao["outcome"], ao["reason"], ao["value"]) else "VIOLATION owner_changed"] += 1
    out["fermata"] = dict(sorted(fc.items()))
    out["moved"] = moved
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("base")
    ap.add_argument("r2")
    ap.add_argument("--round1", default=None)
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    base, r2 = json.load(open(a.base)), json.load(open(a.r2))
    rd1 = json.load(open(a.round1)) if a.round1 else None
    print("CONTROL base glyph_owner rebuilt == saved: %s of %s"
          % tuple(base["summary"]["control_glyph_owner"]))
    print("CONTROL r2   glyph_owner rebuilt == saved: %s of %s"
          % tuple(r2["summary"]["control_glyph_owner"]))
    print("adjudicated on: base %s  r2 %s" % (
        (base.get("adjudicated_on") or base.get("tree")),
        r2.get("adjudicated_on")))
    res = compare(base, r2, rd1)
    res["label"] = r2.get("label")
    print(json.dumps({k: v for k, v in res.items() if k != "moved"},
                     indent=1, sort_keys=True))
    if a.out:
        pathlib.Path(a.out).write_text(json.dumps(res, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
