"""ROADMAP 2.26 -- price the `paired_by_crook` fix, GATHER FIXED.

Rebuilds a `Log` from a saved record's own GATHER rows (`observations` +
`abstentions`, exactly `readjudicate.py`'s recipe --
`benchmarks/omr-staged-duration-beams-2026-09/readjudicate.py`) and re-runs
ADJUDICATE alone with THIS TREE's code. `adjudicate.run` is pure logic over
rows already gathered -- no raster, no detector -- so this is cheap
regardless of document size, and it is blind to any GATHER change by the
same construction (stated so a green run here is never read as more than
an ADJUDICATE-only price).

Three checks, always in this order:
  1. CONTROL -- every staff whose short-system pairing was NOT tied
     (i.e. everything `_forced_pairing` already resolved, or that never
     entered the short-system branch at all) reproduces the SAVED record's
     own `Q.SLOT_INDEX` verdict exactly. A rebuild that cannot even
     reproduce what it did not touch is not a price.
  2. THE MOVE -- every `ambiguous_pairing` staff in the saved record: does
     it now decide `paired_by_crook`, and does the crook it decided match
     the reference slot whose OWN raw text carries the same crook.
  3. UNTOUCHED -- every `unnamed_in_short_system` staff (the bare-crook,
     no-root-word half this fix does not claim) stays exactly as abstained
     as it was.

Then re-runs the EXACT `staff_not_identified` ladder from
`probe_2_26_holdout.py` against the rebuilt log, to report the heads/rests
released.

    python3 benchmarks/omr-staff-identity-2026-09/probe/price_2_26_crook.py \
        <record.json>
"""
from __future__ import annotations

import collections
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from tools.omr.staged import adjudicate, evaluate, infer  # noqa: E402
from tools.omr.staged import adjudicators, consequences  # noqa: E402,F401
from tools.omr.staged import inferences  # noqa: E402,F401 -- registers rules
from tools.omr.staged.record import Log, Subject, Q  # noqa: E402
from tools.omr.staged.record_io import load_record  # noqa: E402
from tools.omr.staged import export as X  # noqa: E402
from tools.omr.staged import adjudicate as A  # noqa: E402
from tools.omr.staged.adjudicators.ownership import (  # noqa: E402
    OWNER_NOT_READ_REASONS)

sys.path.insert(0, str(Path(__file__).resolve().parent))
from probe_2_26_holdout import _classify, _parse, _staff_key  # noqa: E402


def rebuild(rec: dict) -> Log:
    """One Log holding exactly the saved record's GATHER rows, in order.
    Verbatim from `readjudicate.py` (not imported -- see that file's own
    comment on why: its directory name is not an identifier)."""
    log = Log()
    rows = [(r, "obs") for r in rec["observations"]]
    rows += [(r, "abs") for r in rec.get("abstentions", [])]
    rows.sort(key=lambda t: t[0]["id"])
    for r, kind in rows:
        sub = Subject.from_key(r["subject"])
        detail = dict(r.get("detail") or {})
        if kind == "obs":
            log.observe(sub, r["quantity"], r["value"], reader=r["reader"],
                        frame=r["frame"], score=r.get("score"), **detail)
        else:
            log.abstain(sub, r["quantity"], reader=r["reader"],
                        frame=r["frame"], reason=r["reason"], **detail)
    return log


def main(argv):
    record_path = argv[1]
    t0 = time.time()
    loaded = load_record(record_path)
    rec = loaded["record"]
    t1 = time.time()
    print(f"loaded in {t1 - t0:.1f}s", file=sys.stderr)

    baseline_slot = {v["subject"]: v for v in rec["verdicts"]
                     if v["quantity"] == Q.SLOT_INDEX}

    log = rebuild(rec)
    log.freeze()   # end GATHER, exactly as the real pipeline does before
                    # ADJUDICATE -- INFER refuses an unfrozen log (rule 1)
    t2 = time.time()
    print(f"rebuilt Log in {t2 - t1:.1f}s ({len(rec['observations'])} obs, "
          f"{len(rec.get('abstentions', []))} abstentions)", file=sys.stderr)
    adjudicate.run(log)
    t2b = time.time()
    print(f"adjudicate.run in {t2b - t2:.1f}s", file=sys.stderr)
    evaluated = evaluate.run(log)
    t2c = time.time()
    print(f"evaluate.run in {t2c - t2b:.1f}s", file=sys.stderr)
    # ⚠️ SAME PIPELINE ORDER AS `__main__.py`: INFER runs so the CONTROL
    # compares against the saved record's own POST-INFER `Q.SLOT_INDEX`
    # reason strings (`a_condensed_violoncello_e_basso_staff_takes_the_
    # cello_slot` etc.) instead of reading every one of THOSE as a false
    # "differ" against this rebuild's pre-INFER `family_block_not_forced`.
    infer.run(log, evaluated)
    t3 = time.time()
    print(f"infer.run in {t3 - t2c:.1f}s", file=sys.stderr)

    new = log.to_json()
    new_slot = {v["subject"]: v for v in new["verdicts"]
               if v["quantity"] == Q.SLOT_INDEX}

    # ── 1. CONTROL: every non-tied staff reproduces exactly ────────────────
    control_same = control_diff = 0
    moved_from_non_target = []
    for key, w in baseline_slot.items():
        if w.get("reason") in ("ambiguous_pairing",):
            continue  # the population this fix TARGETS -- checked below
        g = new_slot.get(key)
        if g is None:
            control_diff += 1
            continue
        if (g["outcome"] == w["outcome"] and g.get("value") == w.get("value")
                and g.get("reason") == w.get("reason")):
            control_same += 1
        else:
            control_diff += 1
            moved_from_non_target.append(
                (key, w.get("reason"), g.get("outcome"), g.get("reason")))
    print(f"CONTROL (non-ambiguous_pairing staves): {control_same} same, "
          f"{control_diff} differ")
    if moved_from_non_target:
        print("  ⚠️ MOVED OUTSIDE THE TARGET POPULATION (first 10):",
              moved_from_non_target[:10])

    # ── 2. THE MOVE: every ambiguous_pairing staff ──────────────────────────
    targets = {k: w for k, w in baseline_slot.items()
              if w.get("reason") == "ambiguous_pairing"}
    resolved = collections.Counter()
    detail_rows = []
    for key, w in targets.items():
        g = new_slot.get(key)
        outcome = g["outcome"] if g else "absent"
        reason = g.get("reason") if g else None
        resolved[(outcome, reason)] += 1
        detail_rows.append((key, w.get("value"), outcome, reason,
                            g.get("value") if g else None,
                            (g.get("detail") or {}).get("crook") if g else None))
    print(f"THE MOVE: {len(targets)} ambiguous_pairing staves in the saved "
          f"record -> {dict(resolved)}")
    for row in detail_rows[:10]:
        print("   ", row)

    # ── 3. UNTOUCHED: unnamed_in_short_system staves stay abstained ────────
    untouched_targets = {k: w for k, w in baseline_slot.items()
                         if w.get("reason") == "unnamed_in_short_system"}
    unt_same = unt_diff = 0
    for key, w in untouched_targets.items():
        g = new_slot.get(key)
        if g and g["outcome"] == "abstained" and g.get("reason") == w.get("reason"):
            unt_same += 1
        else:
            unt_diff += 1
    print(f"UNTOUCHED (unnamed_in_short_system): {unt_same} same, "
          f"{unt_diff} differ (of {len(untouched_targets)})")

    # ── re-run the export ladder against the REBUILT log ───────────────────
    new_result = {"record": new}
    new_rec = X.Record(new_result)

    join_v = new_rec.verdict(Q.PART_PARTITION, "document")
    join = ((join_v.get("value") or {}).get("join")
           if join_v and join_v["outcome"] == "decided" else None)
    staff_keys = set()
    for q in (Q.SLOT_INDEX, Q.STAFF_ORDINAL):
        for v in new_rec.verdicts_of(q):
            s = _parse(v["subject"])
            if (s.get("staff") is not None and s.get("glyph") is None
                    and s.get("cell") is None):
                staff_keys.add(_staff_key(s["page"], s["system"], s["staff"]))
    held_out = set()
    if join == "slot":
        for k in staff_keys:
            if not isinstance(new_rec.value(Q.SLOT_INDEX, k), int):
                held_out.add(k)

    refuse_whole_rest_ink = X.whole_rest_ink_enabled()
    heads = rests = 0
    for o in new_rec.obs_of(Q.GLYPH_BOX):
        sub = o["subject"]
        s = _parse(sub)
        if s.get("glyph") is None:
            continue
        is_rest = bool(new_rec.obs(Q.REST, sub))
        reason, home = _classify(new_rec, sub, refuse_whole_rest_ink)
        if reason == "reaches_held_out_check" and home in held_out:
            if is_rest:
                rests += 1
            else:
                heads += 1
    print(f"join_used={join}  n_held_out_staves={len(held_out)}  "
         f"heads_held_out={heads}  rests_held_out={rests}  "
         f"total={heads + rests}")
    t4 = time.time()
    print(f"export ladder in {t4 - t3:.1f}s; total {t4 - t0:.1f}s",
          file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv)
