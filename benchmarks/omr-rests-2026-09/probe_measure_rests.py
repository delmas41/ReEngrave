"""Step 3 — rests, with the part join fed and the condensed merge fixed.

⚠️ SUPERSEDES the corpus half of `probe_rest_durations.py`, whose repro block
runs the bare `python3 -m tools.omr.symbol_ledger` CLI. That CLI takes **no
`part_join`**, so it falls back to a positional join only where the part counts
already agree — against a 38-part Mahler reference they never do, which is why
that probe could assess 9.8% of its own rest rows. This one builds the ledger
the way `run_ledger.py` does, from `works.json`.

⚠️ READ `side` BEFORE READING `attrs` — on a `truth`-side row `attrs` is the
TRUTH and `partner_attrs` is ours. Nothing in the column names says so.

It also asks the question the confusion table cannot: **was our rest the ONLY
event in its bar?** That is what separates a measure-rest convention error
from an ordinary misread duration, and it is why the previous diagnosis
(`_measure_rest_beats` fed `None`) was wrong — see FINDINGS.md §7.

    python3 benchmarks/omr-rests-2026-09/probe_measure_rests.py \
        --pairs benchmarks/omr-part-join-2026-09/pairs-restamp-composed.json
"""

from __future__ import annotations

import argparse
import collections
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.omr.symbol_ledger import (  # noqa: E402
    PartJoin, build_ledger, load_side,
)

WORKS = ROOT / "benchmarks" / "omr-scan-e2e-2026-09" / "works.json"


def staves_of(row, rows):
    st = row.get("staves")
    while isinstance(st, str) and st.startswith("same-as:"):
        st = (rows.get(st.split(":", 1)[1].strip()) or {}).get("staves")
    return st if isinstance(st, list) else None


def rest_only_bars(path):
    """(part_id, measure_number) -> how many `<note>` elements the bar holds,
    for every bar of OURS whose notes are ALL rests. Those are the bars an
    engraver prints as one centred measure rest. ⚠️ Counting only bars with
    exactly ONE note misses the bar we split into several rests, which is the
    same convention error one step further along."""
    out = {}
    for part in ET.parse(path).getroot().iter("part"):
        for m in part.iter("measure"):
            notes = list(m.iter("note"))
            if notes and all(n.find("rest") is not None for n in notes):
                out[(part.get("id"), m.get("number"))] = len(notes)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs", required=True)
    a = ap.parse_args()
    works = json.loads(WORKS.read_text())
    wrows = {r["row_id"]: r for r in works["rows"]}
    pairs = json.loads(Path(a.pairs).read_text())

    conf = collections.Counter()
    out = collections.Counter()
    lone = collections.Counter()
    per_bar = collections.Counter()
    mixed_rows = []
    n = na = 0
    rows_used = []
    for p in pairs:
        rid = p["name"]
        w = wrows.get(rid, {})
        st = staves_of(w, wrows)
        _, pmeta = load_side(p["pred"], "pred")
        n_pred = len(pmeta["parts"])
        if not st or len(st) != n_pred:
            continue          # Step 4's bucket; declared, not silently pooled
        win = w.get("window") or {}
        first, last = win.get("first_ref_measure"), win.get("last_ref_measure")
        exp = (last - first + 1) if (first is not None and last is not None) else None
        pj = [PartJoin(i, tuple(int(x) for x in (s.get("parts") or ())),
                       "resolved" if s.get("parts") else "unresolved")
              for i, s in enumerate(st)]
        res = build_ledger(row_id=rid, pred_path=p["pred"], truth_path=p["truth"],
                           part_join=pj, first_ref_measure=first,
                           expected_measures=exp)
        assert res.coverage_check()["balanced"], f"{rid} unbalanced"
        rows_used.append(rid)
        alone = rest_only_bars(p["pred"])
        pred_ids = [q["id"] for q in pmeta["parts"]]
        for r in res.rows:
            if r.family != "rest":
                continue
            n += 1
            out[r.outcome] += 1
            if r.outcome != "uncorresponded":
                na += 1
            if r.outcome != "matched_attribute_error":
                continue
            if "duration_ql" not in r.attrs_wrong:
                continue
            own, par = r.attrs, r.partner_attrs
            truth, ours = (own, par) if r.side == "truth" else (par, own)
            key = ((ours.get("type"), ours.get("duration_ql")),
                   (truth.get("type"), truth.get("duration_ql")))
            conf[key] += 1
            # ⚠️ CHECK THE FRAME. On a TRUTH-side row `part_index` is the
            # TRUTH part index, not ours — a condensed staff makes those
            # different numbers. Mapping it straight onto `pred_ids` said a
            # Beethoven bar holding no rest at all held one, in the same shape
            # as the cell-frame-vs-page-frame trap the last session paid for.
            if r.side == "truth":
                owner = [q.pred_part for q in pj
                         if r.part_index in q.truth_parts]
                ppart = owner[0] if owner else None
            else:
                ppart = r.part_index
            pid = (pred_ids[ppart]
                   if ppart is not None and ppart < len(pred_ids) else None)
            # the ledger's `measure` is the REFERENCE number; ours is offset
            mine = str((r.measure or 0) - (res.measure_map["offset"] or 0))
            n_in_bar = alone.get((pid, mine))
            lone[(key, n_in_bar is not None)] += 1
            if n_in_bar is not None:
                per_bar[n_in_bar] += 1
            else:
                mixed_rows.append((rid, pid, mine, key))

    print(f"rows measured: {len(rows_used)}  ({', '.join(rows_used)})")
    print(f"\nrest rows {n}, ASSESSABLE {n - out.get('uncorresponded', 0)} "
          f"({(n - out.get('uncorresponded', 0)) / max(n, 1):.1%})")
    for k, v in out.most_common():
        print(f"  {k:28} {v:>6}")
    print(f"\nWRONG REST DURATION — {sum(conf.values())} rows")
    print(f"  {'ours (type, ql)':>22}  {'truth (type, ql)':>22}   "
          f"{'n':>5}  {'our bar held ONLY this rest':>28}")
    for k, v in conf.most_common(12):
        alone_n = lone[(k, True)]
        print(f"  {str(k[0]):>22}  {str(k[1]):>22}   {v:>5}  "
              f"{alone_n:>5} of {v}  ({alone_n/max(v,1):.0%})")
    print("\n  how many rests OUR all-rest bar held: "
          + ", ".join(f"{k} rest(s) x{v}" for k, v in sorted(per_bar.items())))
    print(f"  wrong rest durations in bars of ours that also hold NOTES: "
          f"{len(mixed_rows)}")
    for r in mixed_rows[:8]:
        print(f"    {r[0]} {r[1]} m{r[2]} {r[3]}")
    tot = sum(conf.values())
    tot_alone = sum(v for (k, al), v in lone.items() if al)
    print(f"\n  lone-rest bars account for {tot_alone} of {tot} "
          f"wrong rest durations ({tot_alone/max(tot,1):.1%})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
