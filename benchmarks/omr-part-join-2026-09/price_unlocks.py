"""What each separated cause is WORTH as assessability, measured.

⚠️ **THIS PRICES AN INSTRUMENT CHANGE, NOT A PIPELINE CHANGE.** Causes B and C
(see `separate_causes.py`) are `run_ledger.part_join_for`'s arity gate refusing
a positional join because the hand-verified LINEUP and our PART LIST count
different things. Relaxing the gate reads no new ink and changes no export; it
changes how much of the page the ledger can assess. Cause A is the reader's own
`_stitch_slots` refusal and is NOT touched here — its fix is `OMR_SLOT_STITCH`,
already on the shelf and already measured.

The two relaxations, each with the fact that licenses it:

  B — the lineup lists one entry per PRINTED staff, including one-line
      percussion rules; `page.n_staves` counts only FIVE-LINE staves, and the
      row's own `n_staves_note` says in words "compare `detected` against
      <n_staves>". Dropping the one-line entries leaves exactly `n_staves`
      entries in printed top-to-bottom order, which is the same footing the 12
      rows whose join already resolves stand on. The dropped entries' truth
      parts then belong to NO predicted part and their symbols stay
      `uncorresponded` — which is correct: that music is genuinely unread.

      ⚠️ WHICH entries are one-line is NOT a structural field in works.json —
      only the COUNT is derivable (`len(staves) - page.n_staves`). The indices
      below are hand-read from each row's own `n_staves_note` prose, and the
      script ASSERTS the count matches, so a drifted declaration fails loudly
      instead of silently joining the wrong staves.

  C — bach's lineup entry 10 is literally named
      "Cembalo (grand staff, 2 printed staves)". We emit the two staves as two
      parts; the reference encodes them as one. So the upper staff takes truth
      part 10 and the lower is declared unresolved. ⚠️ NOT both mapped to truth
      part 10 — that would visit the same truth symbols twice and unbalance the
      ledger's own accounting control.

D (mahler p2, no lineup at all) is NOT priced: it needs a hand-verified fact
that does not exist. Inventing one would be the guess the gate exists to refuse.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.omr.symbol_ledger import (  # noqa: E402
    PartJoin, build_ledger, load_side, summarise,
)

WORKS = ROOT / "benchmarks" / "omr-scan-e2e-2026-09" / "works.json"
FIX = Path("/Users/seanjohnson/Desktop/ReEngrave/benchmarks/omr-scan-e2e-2026-09/fixtures")

# hand-read from each row's own page.n_staves_note; the count is asserted below
ONE_LINE_ENTRIES = {
    "mahler-sym5-mvt1-local-p3": [8, 9],            # Becken, Gr.Tr.
    "mahler-sym5-mvt1-local-p4": [11, 12, 13],      # Becken, Gr.Tr., Kl.Tr.
    "mahler-sym5-mvt1-local-p5": [10, 11, 12, 13],  # + Tamtam
}
# pred part index -> lineup entry it shares, for a lineup entry covering
# several printed staves. The FIRST printed staff keeps the reference part.
GRAND_STAFF_EXTRA = {"bach-brandenburg3-mvt1-468678-p1": [11]}


def staves_of(row, rows):
    st = row.get("staves")
    while isinstance(st, str) and st.startswith("same-as:"):
        st = (rows.get(st.split(":", 1)[1].strip()) or {}).get("staves")
    return st if isinstance(st, list) else None


def joins(rid, row, staves, n_pred):
    """(strict, relaxed) — strict is run_ledger's gate, verbatim in effect."""
    strict = [PartJoin(i, (), "unresolved", reason="arity", source="none")
              for i in range(n_pred)]
    if rid in ONE_LINE_ENTRIES:
        drop = ONE_LINE_ENTRIES[rid]
        want = len(staves) - row["page"]["n_staves"]
        assert len(drop) == want, (
            f"{rid}: declared {len(drop)} one-line entries but "
            f"len(staves)-n_staves == {want}")
        keep = [s for i, s in enumerate(staves) if i not in set(drop)]
        assert len(keep) == n_pred, f"{rid}: {len(keep)} kept vs {n_pred} parts"
        relaxed = [PartJoin(i, tuple(int(p) for p in (s.get("parts") or [])),
                            "resolved" if s.get("parts") else "unresolved",
                            source="works.json, one-line rules dropped")
                   for i, s in enumerate(keep)]
        return strict, relaxed
    if rid in GRAND_STAFF_EXTRA:
        extra = set(GRAND_STAFF_EXTRA[rid])
        assert len(staves) + len(extra) == n_pred, (
            f"{rid}: {len(staves)} lineup + {len(extra)} extra vs {n_pred} parts")
        relaxed = []
        li = 0
        for i in range(n_pred):
            if i in extra:
                relaxed.append(PartJoin(
                    i, (), "unresolved",
                    reason="the lower staff of a grand staff the reference "
                           "encodes as one part",
                    source="works.json lineup name"))
                continue
            s = staves[li]
            li += 1
            relaxed.append(PartJoin(
                i, tuple(int(p) for p in (s.get("parts") or [])),
                "resolved" if s.get("parts") else "unresolved",
                source="works.json, grand staff split"))
        return strict, relaxed
    raise SystemExit(f"no relaxation declared for {rid}")


def main() -> int:
    works = json.loads(WORKS.read_text())
    wrows = {r["row_id"]: r for r in works["rows"]}
    results = []
    for rid in ["mahler-sym5-mvt1-local-p3", "bach-brandenburg3-mvt1-468678-p1"]:
        pred = FIX / f"{rid}.restamp-composed.omr.musicxml"
        truth = FIX / f"{rid}.truth.musicxml"
        if not pred.exists():
            print(f"SKIP {rid}: no committed pair")
            continue
        row = wrows[rid]
        win = row.get("window") or {}
        first, last = win.get("first_ref_measure"), win.get("last_ref_measure")
        exp = (last - first + 1) if (first is not None and last is not None) else None
        _, pmeta = load_side(str(pred), "pred")
        n_pred = len(pmeta["parts"])
        st, rl = joins(rid, row, staves_of(row, wrows), n_pred)
        arms = {}
        for name, pj in (("strict", st), ("relaxed", rl)):
            res = build_ledger(row_id=rid, pred_path=pred, truth_path=truth,
                               part_join=pj, first_ref_measure=first,
                               expected_measures=exp)
            s = summarise(res)
            oc = s["outcomes"]
            tot = sum(oc.values())
            arms[name] = {
                "rows": tot,
                "uncorresponded": oc.get("uncorresponded", 0),
                "assessable": tot - oc.get("uncorresponded", 0),
                "balanced": res.coverage_check()["balanced"],
                "coverage": res.coverage_check(),
                "outcomes": oc,
                "attributes_wrong": s["attributes_wrong"],
            }
        results.append({"row_id": rid, **arms})
        a, b = arms["strict"], arms["relaxed"]
        print(f"\n{rid}")
        print(f"  strict   rows={a['rows']:>5} assessable={a['assessable']:>5} "
              f"balanced={a['balanced']}")
        print(f"  relaxed  rows={b['rows']:>5} assessable={b['assessable']:>5} "
              f"balanced={b['balanced']}")
        print(f"  UNLOCK   +{b['assessable'] - a['assessable']} assessable rows")
        print(f"  relaxed outcomes: {b['outcomes']}")

    out = Path(__file__).resolve().parent / "unlocks.json"
    out.write_text(json.dumps(results, indent=1))
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
