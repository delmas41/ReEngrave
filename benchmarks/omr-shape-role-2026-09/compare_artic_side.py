"""ROADMAP 2.12f -- BASE vs ARM, one tree, one record, from
`readjudicate_artic_side.py` outputs.

    python3 benchmarks/omr-shape-role-2026-09/compare_artic_side.py \
        <base.json> <arm.json> [--out <json>]

Prints, in this order (CLAUDE.md Sec.6b: reach before accuracy, and the control
before any delta):

  1. the CONTROL line each side printed -- `glyph_owner` rebuilt == saved;
  2. the POPULATION: marks that reach the decision;
  3. the transition table, base (outcome/reason) -> arm (outcome/reason);
  4. the INVARIANTS the change promises, each a number that CAN fail:
       - no mark the base DECIDED changes its owner (it may only leave via
         `level_with_head`);
       - no mark the base ABSTAINED becomes decided (a relabel, not a recovery);
       - every arm-decided owner's measured side equals the class's side;
       - the fermata owner's outcome/value is byte-identical;
  5. the DECIDED population's measurements: gap beyond reach, other-side head;
  6. the fermata record-only numbers: decided carriers, measured vs suffix.
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))


def _key(v):
    if not v:
        return "none"
    return "%s/%s" % (v["outcome"], v["reason"])


def compare(base: dict, arm: dict) -> dict:
    b = {r["subject"]: r for r in base["articulations"]}
    a = {r["subject"]: r for r in arm["articulations"]}
    out = {"marks": len(b)}
    trans = collections.Counter()
    changed = []
    inv = collections.Counter()
    for s, br in b.items():
        ar = a[s]
        bk, ak = _key(br["owner"]), _key(ar["owner"])
        trans[(bk, ak)] += 1
        if bk != ak:
            changed.append({"subject": s, "class": br["class"],
                            "suffix_side": br["suffix_side"],
                            "before": bk, "after": ak,
                            "arm_detail": (ar["owner"] or {}).get("detail"),
                            "mark_bbox_page": br.get("mark_bbox_page"),
                            "page": br["page"]})
        bo, ao = br["owner"], ar["owner"]
        if bo and bo["outcome"] == "decided":
            if ao["outcome"] == "decided":
                inv["base_decided_stays_decided"] += 1
                if ao["value"] != bo["value"]:
                    inv["VIOLATION base_decided_owner_moved"] += 1
            elif ao["reason"] == "level_with_head":
                inv["base_decided_leaves_via_level_with_head"] += 1
            else:
                inv["VIOLATION base_decided_left_other_way"] += 1
        else:
            if ao and ao["outcome"] == "decided":
                inv["VIOLATION base_abstained_became_decided"] += 1
        if ao and ao["outcome"] == "decided":
            d = ao["detail"]
            if d.get("measured_side") != d.get("suffix_side"):
                inv["VIOLATION decided_measured_side_differs_from_class"] += 1
            else:
                inv["decided_measured_side_equals_class"] += 1
    out["transitions"] = {"%s -> %s" % k: v for k, v in sorted(trans.items())}
    out["changed"] = changed
    out["invariants"] = dict(sorted(inv.items()))

    # decided-owner measurements (ARM)
    dd = collections.Counter()
    for r in arm["articulations"]:
        o = r["owner"]
        if o and o["outcome"] == "decided":
            d = o["detail"]
            dd["decided"] += 1
            if d["gap_head_heights"] > 1.5:
                dd["decided_but_beyond_reach(>1.5 head heights)"] += 1
            if d["other_side_head_in_reach"]:
                dd["decided_with_a_head_on_the_other_side_in_reach"] += 1
    out["decided_population"] = dict(sorted(dd.items()))

    # fermata
    bf = {r["subject"]: r for r in base["fermatas"]}
    af = {r["subject"]: r for r in arm["fermatas"]}
    fc = collections.Counter()
    for s, br in bf.items():
        ar = af[s]
        bo, ao = br["owner"], ar["owner"]
        same = (bo["outcome"], bo["reason"], bo["value"]) == (
            ao["outcome"], ao["reason"], ao["value"])
        fc["owner_identical" if same else "VIOLATION owner_changed"] += 1
        if ao["outcome"] == "decided":
            d = ao["detail"]
            fc["decided"] += 1
            fc["measured:%s" % d.get("measured_side")] += 1
            fc["side_agrees:%s" % d.get("side_agrees")] += 1
    out["fermata"] = dict(sorted(fc.items()))
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("base")
    ap.add_argument("arm")
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    base = json.load(open(a.base))
    arm = json.load(open(a.arm))
    print("CONTROL base glyph_owner rebuilt == saved: %s of %s"
          % tuple(base["summary"]["control_glyph_owner"]))
    print("CONTROL arm  glyph_owner rebuilt == saved: %s of %s"
          % tuple(arm["summary"]["control_glyph_owner"]))
    print("trees: base %s  arm %s" % (base.get("tree"), arm.get("tree")))
    res = compare(base, arm)
    res["label"] = arm.get("label")
    print(json.dumps({k: v for k, v in res.items() if k != "changed"},
                     indent=1, sort_keys=True))
    print("changed marks: %d" % len(res["changed"]))
    for c in res["changed"][:40]:
        print("  ", c["subject"], c["class"], c["before"], "->", c["after"])
    if a.out:
        pathlib.Path(a.out).write_text(json.dumps(res, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
