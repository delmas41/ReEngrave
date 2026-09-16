"""How many CAUTIONARIES does the committed corpus hold, and how many of them
could contest anything?

⚠️⚠️ REACH BEFORE ANYTHING ELSE, AND HERE REACH *IS* THE RESULT. The question
this benchmark exists for — *can a courtesy time signature be put to the
opening it announces as a competing candidate* — is only askable where a
cautionary exists. This probe counts them before any contest is designed, and
**exits non-zero when it finds none**, so a dead instrument can never read as
a clean negative.

⚠️ IT READS ONLY COMMITTED ARTEFACTS. A cloud container has no `omr-weights/`
and no `library/`, so no fresh gather is possible and none is attempted.

    python3 benchmarks/omr-meter-cautionary-2026-09/probe_reach.py
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from common import BOUNDARY, load_arms, next_system_of, truth_for  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json-out", default=str(HERE / "out" / "reach.json"))
    a = ap.parse_args()

    arms = load_arms(BOUNDARY / "out")
    if not arms:
        print(f"DEAD: no committed *.meter.json under {BOUNDARY / 'out'}.")
        return 2

    fixtures = sorted({arm.fixture for arm in arms})
    gens = sorted({arm.generation for arm in arms})

    # ── the cautionary inventory, deduped on the ADDRESS OF THE INK ─────────
    caut: dict = {}
    for arm in arms:
        for sub, value in arm.meters():
            c = (value or {}).get("cautionary")
            if not c:
                continue
            key = (arm.fixture, sub, int(c["from_cell"]), c["raw"])
            row = caut.setdefault(key, {"c": c, "arms": [], "gens": set()})
            row["arms"].append(f"{arm.tag}-{arm.flag_arm}")
            row["gens"].add(arm.generation)

    print("═══ REACH ═══")
    print(f"  committed arms read ............ {len(arms)}")
    print(f"  distinct fixtures .............. {len(fixtures)}")
    for f in fixtures:
        print(f"        {f}")
    print(f"  tree generations .............. {gens}")
    print(f"      ⚠️ only generations >= 5 carry the cautionary rule at all")
    print(f"  DISTINCT CAUTIONARIES ......... {len(caut)}")
    if not caut:
        print("\nDEAD: the committed corpus records no cautionary. The "
              "contest this benchmark asks about has no instance to run on.")
        return 2

    by_fixture: dict = {}
    for (fix, sub, cell, raw) in caut:
        by_fixture.setdefault(fix, []).append((sub, cell, raw))
    print(f"  ...on how many fixtures ....... {len(by_fixture)} of "
          f"{len(fixtures)}")
    for fix in sorted(by_fixture):
        print(f"        {fix}: {len(by_fixture[fix])}")
    silent = [f for f in fixtures if f not in by_fixture]
    print(f"  fixtures with ZERO ............ {len(silent)}")
    for f in silent:
        print(f"        {f}")

    # ── the contest pairs ──────────────────────────────────────────────────
    print("\n═══ CONTESTABLE PAIRS ═══")
    print("  A cautionary names the meter of the NEXT system, so a pair "
          "exists\n  only where that next system is in the same run.\n")
    rows = []
    for (fix, sub, cell, raw), row in sorted(caut.items()):
        c = row["c"]
        gen = max(row["gens"])
        arm = next(x for x in arms if x.fixture == fix and x.generation == gen)
        nxt = next_system_of(arm, sub)
        nxt_truth = truth_for(fix, nxt) if nxt else None
        op_ev: dict = {}
        opening = None
        if nxt is None:
            state = "NO_NEXT_SYSTEM_IN_RUN"
        else:
            v = arm.verdict(nxt) or {}
            op_ev = v.get("detail") or {}
            if v.get("outcome") == "decided" and v.get("reason") != "change_only":
                opening = (v.get("value") or {}).get("raw")
            # ⚠️ `change_only` says in its own reason that the OPENING is
            # unknown; its top-level `raw` is the CHANGE. Reading that as the
            # opening is the mistake `report_boundary.py` records making once.
            state = ("OPENING_UNKNOWN" if opening is None
                     else "AGREE" if opening == raw else "DISAGREE")
        caut_ok = (raw == nxt_truth) if nxt_truth else None
        op_ok = (opening == nxt_truth) if (nxt_truth and opening) else None
        rows.append({
            "fixture": fix, "system": sub, "from_cell": cell,
            "cautionary_raw": raw, "support": c.get("support"),
            "staves_reading_it": len(c.get("staves_reading_it") or []),
            "loose_digits": c.get("loose_digits"),
            "bars_fit": c.get("bars_fit"),
            "bars_contradict": c.get("bars_contradict"),
            "next_system": nxt, "next_opening_raw": opening,
            "next_opening_n_staves_spoke": op_ev.get("n_staves_spoke"),
            "next_opening_share": op_ev.get("share"),
            "truth_of_next_system": nxt_truth,
            "cautionary_correct": caut_ok, "opening_correct": op_ok,
            "state": state,
            "generations": sorted(row["gens"]),
            "arms": sorted(row["arms"]),
        })
        print(f"  {fix}  {sub}  cell {cell}")
        print(f"      CAUTIONARY  {raw:>5}   support {c.get('support'):>6}"
              f"   staves {len(c.get('staves_reading_it') or []):>3}"
              f"   loose {c.get('loose_digits')}")
        print(f"      it announces {nxt}")
        print(f"      OPENING     {str(opening):>5}   share   "
              f"{str(op_ev.get('share')):>6}"
              f"   staves {str(op_ev.get('n_staves_spoke')):>3}")
        print(f"      TRUTH       {str(nxt_truth):>5}   -> {state}"
              f"   cautionary={'RIGHT' if caut_ok else 'WRONG' if caut_ok is False else '?'}"
              f"  opening={'RIGHT' if op_ok else 'WRONG' if op_ok is False else 'n/a'}")
        print(f"      seen in {len(row['arms'])} arms: {sorted(row['arms'])}\n")

    # ── the structural blind spot, asserted against the SOURCE ─────────────
    #
    # ⚠️⚠️ THE RECORDED REACH UNDERSTATES THE PRINTED ONE, AND BY A KNOWN
    # MECHANISM. `_meter_changes` skips `cell == 0` outright — *"cell 0 states
    # the staff's OPENING"* — so on a system whose ONLY cell is cell 0 the
    # courtesy signature standing after its final barline can never become a
    # cautionary row. The boundary benchmark records exactly such a page
    # (`boundary-m150-180` page 1, "m154 alone, the fermata bar") and says in
    # its own §4b that the one-cell shape is what hid the cautionary bug from
    # that fixture. This is a CLAIM ABOUT THE CODE, so it is checked against
    # the code rather than asserted in prose.
    print("\n═══ THE STRUCTURAL BLIND SPOT (checked against the source) ═══")
    src = (BOUNDARY.parents[1] / "tools" / "omr" / "staged" / "adjudicators"
           / "rhythm.py").read_text()
    skip = 'if cell is None or int(cell) == 0:' in src
    print(f"  `_meter_changes` skips cell 0 ...... {skip}")
    if not skip:
        print("  ⚠️ the source no longer skips cell 0 — this note is STALE "
              "and the blind spot below may be closed. Re-read before "
              "quoting it.")
    else:
        print("  -> a system whose only cell IS cell 0 cannot produce a "
              "cautionary row,\n     however clearly the courtesy signature "
              "is printed on it.")

    n_pairs = sum(1 for r in rows if r["state"] != "NO_NEXT_SYSTEM_IN_RUN")
    n_dis = sum(1 for r in rows if r["state"] == "DISAGREE")
    n_agree = sum(1 for r in rows if r["state"] == "AGREE")
    n_unk = sum(1 for r in rows if r["state"] == "OPENING_UNKNOWN")
    docs = sorted({r["fixture"] for r in rows})
    print("═══ SUMMARY ═══")
    print(f"  cautionaries ................... {len(rows)}")
    print(f"  ...with a next system in the run {n_pairs}")
    print(f"      AGREE (a control) .......... {n_agree}")
    print(f"      DISAGREE (a CONTEST) ....... {n_dis}")
    print(f"      OPENING UNKNOWN (a FILL) ... {n_unk}")
    print(f"  fixtures carrying one .......... {len(docs)}  {docs}")
    print(f"  DISTINCT PIECES OF MUSIC ....... "
          f"{len({d.split('-')[0] for d in docs})}")

    Path(a.json_out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.json_out).write_text(json.dumps(
        {"arms_read": len(arms), "fixtures": fixtures, "generations": gens,
         "cautionaries": rows}, indent=1) + "\n")
    print(f"\nwrote {a.json_out}")

    if n_dis == 0:
        print("\nDEAD FOR THE CONTEST: no cautionary DISAGREES with the "
              "opening it announces, so there is nothing to arbitrate.")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
