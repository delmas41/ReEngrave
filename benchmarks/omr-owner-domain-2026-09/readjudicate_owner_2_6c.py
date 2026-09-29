"""ROADMAP 2.6c (second half) — the ONE saved-record read.

Re-decides ONLY `glyph_owner` (every contest on the record) and 2.7b's
`notehead_is_not_a_notehead` (every head whose saved verdict carries a
`nearer_staff_signal` past the filed band, the only ones the rung exception
can reach) in memory, on today's tree, against the record's own GATHER rows
(`review.rerun.rebuild_gather`) plus the upstream verdicts those two read
(`ledger_is_not_a_ledger`, `instrument`, `clef`) injected as saved. No
re-gather, no export. Prints and writes counts:

  * contests whose WINNER changes, by (old reason -> new reason);
  * contests that newly abstain `far_no_rungs`;
  * nearer-staff verdicts that change;
  * the named heads' new verdicts;
  * the distributions the three ladder thresholds are argued from
    (`missing` and `reach_spaces` on every side that has a rung toward it).

⚠️ A GATHER change would be invisible here; this lane changes no GATHER.
⚠️ The record's verdicts were decided on an older tree (the 27b arm, before
2.6c's first half), so a change is "saved -> today" and folds in 2.6c's
first half too; `reason_transitions` shows every pair, so a change this lane
did not make (e.g. `range_veto -> hairpin_separates`) is visible as such.
THIS LANE's effect alone is base vs arm: run the script from an extracted
base tree (`git archive 8100c9ff tools`) and from this branch with `--dump`,
then `diff_base_arm_2_6c.py` (FINDINGS §2.6c.2).

    python3 benchmarks/omr-owner-domain-2026-09/readjudicate_owner_2_6c.py \
        <record.json> --out <summary.json> [--dump <verdicts.json>] \
        [--pages 3,4] [--heads k1,k2]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import Counter

sys.path.insert(0, os.getcwd())

from tools.omr.staged import adjudicate as A  # noqa: E402
from tools.omr.staged import adjudicators  # noqa: E402,F401
from tools.omr.staged.record import (  # noqa: E402
    Candidate, Outcome, Q, Subject, Verdict)
from tools.omr.staged.record_io import load_record  # noqa: E402
from tools.omr.staged.review.rerun import rebuild_gather  # noqa: E402

INJECT = (Q.LEDGER_IS_NOT_A_LEDGER, Q.INSTRUMENT, Q.CLEF)


def _outcome(v):
    return {"decided": Outcome.DECIDED, "narrowed": Outcome.NARROWED,
            "abstained": Outcome.ABSTAINED}[v["outcome"]]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--out")
    ap.add_argument("--pages", default="")
    ap.add_argument("--heads", default="")
    ap.add_argument("--dump", help="write every re-decided verdict here")
    a = ap.parse_args(argv)
    pages = {int(p) for p in a.pages.split(",") if p.strip()}
    named = [h for h in a.heads.split(",") if h.strip()]

    t0 = time.time()
    rec = load_record(a.record)["record"]
    log, _ids = rebuild_gather(rec)
    log.freeze()
    # ⚠️ ONLY THE CURRENT VERDICT per (quantity, subject) -- the last one no
    # later verdict supersedes, exactly `Log.verdict`'s rule -- because a
    # clef revised by the second EVALUATE pass is two rows on the record and
    # the log refuses a second un-bounded adjudication.
    superseded = {v.get("supersedes") for v in rec["verdicts"]
                  if v.get("supersedes")}
    current = {}
    for v in rec["verdicts"]:
        if v["id"] in superseded:
            continue
        current[(v["quantity"], v["subject"])] = v
    saved = {}
    for (q, key), v in current.items():
        if q in INJECT:
            log.record(Verdict(
                id=log._next_id("vrd"), subject=Subject.from_key(key),
                quantity=q, outcome=_outcome(v), value=v["value"],
                decider=v["decider"], reason=v["reason"],
                candidates=tuple(Candidate(c["value"], c["support"])
                                 for c in (v.get("candidates") or ()))))
        elif q in (Q.GLYPH_OWNER, Q.NOTEHEAD_IS_NOT_A_NOTEHEAD):
            saved[(q, key)] = v
    A._ensure_decisions()
    t_load = time.time() - t0

    def in_scope(key):
        return not pages or int(key.split("/")[1]) in pages

    # ── glyph_owner, every contest ────────────────────────────────────────
    spec = A.REGISTRY[Q.GLYPH_OWNER]
    t1 = time.time()
    trans = Counter()
    changed_winner = Counter()
    far = Counter()
    unchanged_same = 0
    miss_hist, reach_hist = Counter(), Counter()
    new_owner = {}
    far_subjects, moved = [], []
    far_why, far_refused = Counter(), Counter()
    n = 0
    for (q, key), old in sorted(saved.items()):
        if q != Q.GLYPH_OWNER or not in_scope(key):
            continue
        n += 1
        v = A.adjudicate_one(log, spec, Subject.from_key(key))
        new_owner[key] = v
        o = (old["outcome"], old["value"], old["reason"])
        nv = (v.outcome.value, v.value, v.reason)
        trans[(o[2], nv[2])] += 1
        if o[1] != nv[1]:
            changed_winner[(o[2], nv[2])] += 1
        elif o[2] == nv[2]:
            unchanged_same += 1
        if v.reason == "far_no_rungs":
            far[o[2]] += 1
            far_subjects.append(key)
            # WHY no rung: a box at a step that 3.4g-2 refused, or nothing
            # boxed at any step at all (detector recall)
            sides = ((v.detail or {}).get("ledger") or {}).get("sides") or {}
            refused_here = Counter()
            for sd in sides.values():
                for why, c in (sd.get("refused") or {}).items():
                    refused_here[why] += c
            far_why["a_refused_box_at_a_step" if refused_here
                    else "nothing_boxed_at_any_step"] += 1
            far_refused.update(refused_here)
        if o[1] != nv[1]:
            moved.append([key, list(o), list(nv)])
        led = (v.detail or {}).get("ledger") or {}
        for side in (led.get("sides") or {}).values():
            if side.get("frame") == "page" and side.get("toward", 0) >= 1:
                miss_hist[side["missing"]] += 1
                rs = side.get("reach_spaces")
                if rs is not None:
                    reach_hist[round(rs * 4) / 4] += 1
    t_owner = time.time() - t1

    # ── 2.7b's nearer-staff rule, where it can reach ─────────────────────
    npspec = A.REGISTRY[Q.NOTEHEAD_IS_NOT_A_NOTEHEAD]
    np_trans = Counter()
    np_changed = []
    new_np = {}
    for (q, key), old in sorted(saved.items()):
        if q != Q.NOTEHEAD_IS_NOT_A_NOTEHEAD or not in_scope(key):
            continue
        sig = (old.get("detail") or {}).get("nearer_staff_signal") or {}
        if (sig.get("filed_spaces") or 0) <= 3.0 and key not in named:
            continue
        v = A.adjudicate_one(log, npspec, Subject.from_key(key))
        new_np[key] = v
        a0 = (old["value"], old["reason"])
        a1 = (v.value, v.reason)
        np_trans[(a0, a1)] += 1
        if a0 != a1:
            np_changed.append(key)

    heads = {}
    for k in named:
        e = {}
        if k in new_owner:
            v = new_owner[k]
            e["glyph_owner"] = {"saved": [saved[(Q.GLYPH_OWNER, k)][x] for x
                                          in ("outcome", "value", "reason")],
                                "today": [v.outcome.value, v.value, v.reason],
                                "ledger": (v.detail or {}).get("ledger")}
        if k in new_np:
            v = new_np[k]
            e["notehead_is_not_a_notehead"] = {
                "saved": [saved[(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, k)][x]
                          for x in ("outcome", "value", "reason")],
                "today": [v.outcome.value, v.value, v.reason],
                "ledger": ((v.detail or {}).get("nearer_staff_signal")
                           or {}).get("ledger")}
        heads[k] = e

    out = {
        "record": a.record, "pages": sorted(pages) or "all",
        "seconds": {"load_and_rebuild": round(t_load, 1),
                    "glyph_owner": round(t_owner, 1)},
        "glyph_owner": {
            "contests": n,
            "winner_changed": sum(changed_winner.values()),
            "winner_changed_by_reason": {f"{a}->{b}": c for (a, b), c
                                         in changed_winner.most_common()},
            "newly_far_no_rungs": sum(far.values()),
            "far_no_rungs_was": dict(far),
            "reason_transitions": {f"{a}->{b}": c for (a, b), c
                                   in trans.most_common()},
            "unchanged_value_same_reason": unchanged_same,
            "far_no_rungs_why": dict(far_why),
            "far_no_rungs_refused_boxes_by_reason": dict(far_refused),
            "far_no_rungs_subjects": far_subjects,
            "winner_changed_subjects": moved,
        },
        "ladder_thresholds": {
            "missing_on_sides_with_a_rung_toward": dict(sorted(
                miss_hist.items())),
            "reach_spaces_quarter_bins_on_those_sides": dict(sorted(
                reach_hist.items())),
        },
        "nearer_staff": {
            "reread": sum(np_trans.values()),
            "changed": len(np_changed),
            "transitions": {f"{a}->{b}": c for (a, b), c
                            in np_trans.most_common()},
            "changed_subjects": np_changed,
        },
        "heads": heads,
    }
    print(json.dumps(out, indent=1, default=str))
    if a.out:
        with open(a.out, "w") as f:
            json.dump(out, f, indent=1, default=str)
    if a.dump:
        # every re-decided verdict, so two trees' runs can be diffed
        # subject by subject (base vs arm on ONE record, CLAUDE.md §6b)
        with open(a.dump, "w") as f:
            json.dump({
                "glyph_owner": {k: [v.outcome.value, v.value, v.reason]
                                for k, v in new_owner.items()},
                "notehead_is_not_a_notehead": {
                    k: [v.outcome.value, v.value, v.reason]
                    for k, v in new_np.items()}}, f)


if __name__ == "__main__":
    main()
