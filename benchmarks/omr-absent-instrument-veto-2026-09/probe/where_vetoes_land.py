"""Split the vetoes into the ones truth can judge and the ones it cannot.

`score_full_systems` can only score a system carrying the whole printed lineup —
nothing can be added to a full lineup, so it needs no page-by-page reading.
Reduced systems have no truth here: which parts the engraver suppressed is a
fact about the page. A veto count pooled over both hides the distinction that
matters, so this separates them.

Usage:  where_vetoes_land.py FULL.extract.json [window] [rule]
"""
from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from score_full_systems import LINEUPS                         # noqa: E402
from tools.omr.absent_instrument import find_vetoes            # noqa: E402


def main(path, window=0, rule="span", work="beet5"):
    r = json.load(open(path))
    b = (r.get("contextual") or {}).get("absent_instrument_veto")
    ev = {}
    for e in b["label_evidence"]:
        ev.setdefault(e["page_index"], {})[e["staff_index"]] = e["instrument"]
    sbs = {(s["page_index"], s["system_index"], s["staff_index"]): s["slot"]
           for s in b["staff_slots"]}
    nm = {s["slot"]: s["instrument"] for s in b["slot_instruments"]}
    src = {s["slot"]: s["source"] for s in b["slot_instruments"]}
    refn = len((r.get("contextual") or {}).get("reference") or [])

    truth = {}      # (page, system, staff_index) -> printed name
    emitted = {}
    for page in r.get("pages", []):
        pi = page.get("page_index")
        for sy in page.get("systems", []):
            sts = sorted(sy.get("staves", []),
                         key=lambda s: s.get("staff_geometry", {})
                         .get("line_ys_page", [0])[0])
            for st in sts:
                emitted[(pi, sy.get("system_index"),
                         st.get("staff_index"))] = st.get("instrument")
            for lo, hi, n, names in LINEUPS[work]:
                if lo <= pi <= hi and len(sts) == n:
                    for st, want in zip(sts, names):
                        truth[(pi, sy.get("system_index"),
                               st.get("staff_index"))] = want
                    break

    vs = find_vetoes(staff_keys=list(sbs), slot_by_staff=sbs,
                     instrument_name_by_slot=nm, instrument_source=src,
                     evidence=ev, window=window, rule=rule, reference_size=refn)
    print(f"=== {Path(path).name}  rule={rule} window={window}")
    print(f"INPUT ASSERTION: staves={len(sbs)} with-truth={len(truth)} "
          f"vetoes={len(vs)}")
    judged = collections.Counter()
    unjudged = collections.Counter()
    for v in vs:
        key = (v["page_index"], v["system_index"], v["staff_index"])
        got = emitted.get(key)
        want = truth.get(key)
        if want is None:
            unjudged[(got, "before finale" if v["page_index"] < 44
                      else "finale")] += 1
        else:
            judged[("REMOVED A WRONG NAME" if got != want
                    else "removed a CORRECT name", got, want)] += 1
    print()
    print("on staves the printed lineup can judge:")
    for (verdict, got, want), n in judged.most_common():
        print(f"  {n:5d}  {verdict:24s} emitted {got} / printed {want}")
    if not judged:
        print("  (none)")
    print()
    print("on staves with no truth here (reduced systems):")
    for (got, where), n in unjudged.most_common():
        print(f"  {n:5d}  {str(got):16s} {where}")
    return 0


if __name__ == "__main__":
    a = sys.argv
    raise SystemExit(main(a[1], int(a[2]) if len(a) > 2 else 0,
                          a[3] if len(a) > 3 else "span"))
