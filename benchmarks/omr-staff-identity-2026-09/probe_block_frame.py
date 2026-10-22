#!/usr/bin/env python3
"""Is the S8 bracket block the right FRAME to score the other signals in?

The headline scorecard answers this with a modal-family purity comparison,
which is an oracle for the block's own family. This probe re-asks it as a
genuine prediction, LEAVE-ONE-OUT: predict a staff's instrument family from the
modal family of the OTHER staves in its block, vs from the modal family of
every OTHER staff on the page. Neither ever sees the staff it is predicting.

It also asks the same of S5 (the score-order prior) and reports the CONTINUITY
control: on the two-system rows, does the slot assignment that S6 exposes agree
with the printed truth even where the exporter's ordinal stitch refuses?

    python3 benchmarks/omr-staff-identity-2026-09/probe_block_frame.py
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))
from tools.omr import instruments as INST                     # noqa: E402


def truth_instrument(r):
    n = r.get("CEILING_hand_label")
    m = INST.lookup(n) if n else None
    return m.instrument.name if m else None


def family(name):
    for x in INST.INSTRUMENTS:
        if x.name == name:
            return x.family
    return None


def loo(groups, value):
    """Leave-one-out modal prediction within each group."""
    ok = n = abst = 0
    for members in groups.values():
        vals = [(m, value(m)) for m in members]
        vals = [(m, v) for m, v in vals if v]
        for i, (m, v) in enumerate(vals):
            others = [w for j, (_, w) in enumerate(vals) if j != i]
            if not others:
                abst += 1
                continue
            pred = Counter(others).most_common(1)[0][0]
            n += 1
            ok += (pred == v)
    return {"correct": ok, "n": n, "abstained_singletons": abst,
            "accuracy": round(ok / n, 4) if n else None}


def main():
    E = json.loads((HERE / "evidence.json").read_text())["evidence"]
    T = [r for r in E if truth_instrument(r)]
    out = {}

    by_page = defaultdict(list)
    by_block = defaultdict(list)
    for r in T:
        by_page[(r["row_id"], r["page"], r["system"])].append(r)
        by_block[(r["row_id"], r["page"], r["system"], r["s8_group_index"])].append(r)

    print("=== S8 as a FRAME: leave-one-out family prediction ===")
    pw = loo(by_page, lambda m: family(truth_instrument(m)))
    bl = loo(by_block, lambda m: family(truth_instrument(m)))
    print(f"  page-wide   : {pw['correct']}/{pw['n']} = {pw['accuracy']}")
    print(f"  within-block: {bl['correct']}/{bl['n']} = {bl['accuracy']} "
          f"(+{bl['abstained_singletons']} singleton blocks abstained)")
    print(f"  delta       : {round((bl['accuracy'] or 0) - (pw['accuracy'] or 0), 4)}")
    out["loo_family"] = {"pagewide": pw, "within_block": bl}

    # the same for the exact instrument, which is the harder target
    pwi = loo(by_page, truth_instrument)
    bli = loo(by_block, truth_instrument)
    print(f"\n  (exact instrument, same protocol) page-wide {pwi['accuracy']} "
          f"vs within-block {bli['accuracy']}")
    out["loo_instrument"] = {"pagewide": pwi, "within_block": bli}

    # ── how many blocks does grouping actually find, against the truth's own? ──
    print("\n=== S8 block structure vs the truth's family runs ===")
    rows = []
    for k, members in sorted(by_page.items(), key=lambda kv: str(kv[0])):
        members = sorted(members, key=lambda m: m["staff_index"])
        pred_blocks = len({m["s8_group_index"] for m in members})
        fams = [family(truth_instrument(m)) for m in members]
        runs = 1 + sum(1 for a, b in zip(fams, fams[1:]) if a != b)
        # boundary agreement: does a predicted block boundary sit where the
        # truth's family changes?
        pred_bnd = {i for i in range(1, len(members))
                    if members[i]["s8_group_index"] != members[i - 1]["s8_group_index"]}
        true_bnd = {i for i in range(1, len(fams)) if fams[i] != fams[i - 1]}
        rows.append({"page": list(k), "n_staves": len(members),
                     "predicted_blocks": pred_blocks, "truth_family_runs": runs,
                     "boundaries_predicted": len(pred_bnd),
                     "boundaries_true": len(true_bnd),
                     "boundaries_hit": len(pred_bnd & true_bnd)})
        print(f"  {str(k[0])[:30]:30s} p{k[1]} s{k[2]}  staves {len(members):2d}  "
              f"blocks {pred_blocks}  truth family runs {runs}  "
              f"boundaries {len(pred_bnd & true_bnd)}/{len(true_bnd)} hit, "
              f"{len(pred_bnd)} predicted")
    hit = sum(r["boundaries_hit"] for r in rows)
    tru = sum(r["boundaries_true"] for r in rows)
    pre = sum(r["boundaries_predicted"] for r in rows)
    print(f"  TOTAL: {hit}/{tru} true family boundaries hit "
          f"(recall {round(hit / tru, 4) if tru else None}), "
          f"{pre} predicted (precision {round(hit / pre, 4) if pre else None})")
    out["block_boundaries"] = {"rows": rows, "hit": hit, "true": tru,
                               "predicted": pre,
                               "recall": round(hit / tru, 4) if tru else None,
                               "precision": round(hit / pre, 4) if pre else None}

    # ── S6 continuity, checked against the printed truth ─────────────────────
    print("\n=== S6 continuity, against the printed truth ===")
    cont = {}
    multi = [r for r in E if (r["n_systems_on_page"] or 1) > 1]
    by_rid = defaultdict(list)
    for r in multi:
        by_rid[r["row_id"]].append(r)
    for rid, rs in sorted(by_rid.items()):
        slots = defaultdict(dict)
        for r in rs:
            slots[r["system"]][r["staff_index"]] = (r["s6_slot_index"],
                                                    r.get("CEILING_hand_label"))
        sys_ids = sorted(slots)
        agree = disagree = unknown = 0
        for a, b in zip(sys_ids, sys_ids[1:]):
            # a slot shared between two systems should carry the same label
            by_slot_a = {v[0]: v[1] for v in slots[a].values()}
            for slot, lab in ((v[0], v[1]) for v in slots[b].values()):
                if slot not in by_slot_a:
                    continue
                other = by_slot_a[slot]
                if lab is None or other is None:
                    unknown += 1
                elif INST.lookup(lab) and INST.lookup(other) and \
                        INST.lookup(lab).instrument.name == INST.lookup(other).instrument.name:
                    agree += 1
                else:
                    disagree += 1
        cont[rid] = {"shared_slots_checked": agree + disagree,
                     "same_instrument": agree, "different_instrument": disagree,
                     "no_truth_label": unknown,
                     "precision": round(agree / (agree + disagree), 4)
                     if agree + disagree else None,
                     "system_sizes": [len(slots[s]) for s in sys_ids]}
        print(f"  {rid[:34]:34s} sizes {cont[rid]['system_sizes']}  "
              f"shared slots {agree + disagree}  same instrument {agree}  "
              f"different {disagree}  (no truth {unknown})")
    out["continuity_against_truth"] = cont

    (HERE / "block-frame.json").write_text(json.dumps(out, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
