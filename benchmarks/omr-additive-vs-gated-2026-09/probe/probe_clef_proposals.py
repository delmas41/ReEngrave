"""`clef_correction` — the range->clef arrow, its reach and its cutoffs.

`propose_clef` computes a real-valued `fit` and `margin` and then quantises them
to high/medium/low (taxonomy Class B) behind three hard `return None` cutoffs
(`MIN_NOTEHEADS`, `MIN_FIT`, `MIN_FIT_MARGIN` -- Class A). This dumps every
proposal that survived, with the staff it landed on and whether the caller was
allowed to apply it, so the funnel can be read end to end:

    staves -> clef unread -> instrument known -> proposal survives -> applied
"""
from __future__ import annotations

import glob
import json
import os

ROOT = os.environ.get("OMR_FIXTURE_ROOT", os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..")))

PATTERNS = [
    ("scan", ROOT + "/benchmarks/omr-scan-e2e-2026-09/fixtures/"
             "*.graft09.omr.json"),
    ("engraved", ROOT + "/benchmarks/omr-orchestral-e2e/fixtures/*.omr.json"),
]


def main():
    for fam, pat in PATTERNS:
        paths = sorted(p for p in glob.glob(pat)
                       if fam == "scan" or ("graft09" not in p
                                            and "restamp" not in p))
        n = n_unread = n_named = n_unread_named = n_prop = 0
        rows = []
        for path in paths:
            doc = json.load(open(path))
            for page in doc.get("pages", []):
                for sysm in page.get("systems", []):
                    for st in sysm.get("staves", []):
                        n += 1
                        unread = not st.get("clef_source")
                        named = bool(st.get("instrument"))
                        n_unread += unread
                        n_named += named
                        n_unread_named += unread and named
                        p = st.get("clef_proposal")
                        if not p:
                            continue
                        n_prop += 1
                        rows.append((os.path.basename(path)[:38],
                                     st.get("staff_index"), unread, p, st))
        print(f"\n{'='*76}\n{fam.upper()}  funnel\n{'='*76}")
        print(f"   staves                                    {n:5d}")
        print(f"   clef NOT read (the fill tier's population) {n_unread:5d}"
              f"  {n_unread/max(1,n):5.1%}")
        print(f"   instrument known                          {n_named:5d}")
        print(f"   both (fill tier is eligible)              {n_unread_named:5d}"
              f"  {n_unread_named/max(1,n):5.1%}")
        print(f"   proposal survived the three cutoffs       {n_prop:5d}"
              f"  {n_prop/max(1,n):5.1%}")
        for name, idx, unread, p, st in rows:
            print(f"     {name:40s} st{idx:<3d} unread={unread!s:5s} "
                  f"{p.get('from_clef')}->{p.get('to_clef')} "
                  f"fit={p.get('fit')} cur={p.get('current_fit')} "
                  f"margin={p.get('margin')} n={p.get('n_noteheads')} "
                  f"{p.get('confidence_label')} applied={p.get('applied')} "
                  f"inst={st.get('instrument')!r}"
                  f"({st.get('instrument_source')})")


if __name__ == "__main__":
    main()
