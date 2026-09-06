"""The clef consumer's PROVENANCE gate: what does excluding `score_order` cost
in reach?

`contextual.py:1203` builds `read_instruments` by dropping every slot whose
`instrument_source` is `score_order` (and `roster`, unless `OMR_ROSTER_CLEF`).
That is the §7 provenance rule as a hard gate -- a deduced identity may not feed
the clef consumer at all. This measures the population it removes, split by the
only thing that decides whether the consumer could have acted: was the clef read?

    reach(fill tier) = staves with NO clef read AND an admissible instrument
                       AND enough noteheads AND a proposal that survives
"""
from __future__ import annotations

import collections
import glob
import json
import os
import sys

ROOT = os.environ.get("OMR_FIXTURE_ROOT", os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..")))
sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from probe_propose_clef_branches import branch  # noqa: E402
from tools.omr.instruments import lookup  # noqa: E402

# contextual.py:1203 -- the default set (OMR_ROSTER_CLEF=0)
NOT_CLEF_EVIDENCE = {"score_order", "roster"}

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
        tab = collections.Counter()
        gained = []
        for path in paths:
            for page in json.load(open(path)).get("pages", []):
                for sysm in page.get("systems", []):
                    for st in sysm.get("staves", []):
                        unread = not st.get("clef_source")
                        src = st.get("instrument_source") or "(none)"
                        admissible = src not in NOT_CLEF_EVIDENCE \
                            and src != "(none)"
                        tab[("unread" if unread else "read", src)] += 1
                        if not unread:
                            continue
                        tab[("UNREAD-admissible" if admissible
                             else "UNREAD-refused", "")] += 1
                        name = st.get("instrument")
                        if admissible or not name:
                            continue
                        inst = getattr(lookup(name), "instrument", None)
                        if inst is None or getattr(inst, "unpitched", False) \
                                or not getattr(inst, "written_range", None):
                            continue
                        b, fits = branch(st, inst)
                        if b.startswith("PROPOSAL"):
                            gained.append(
                                (os.path.basename(path)[:36],
                                 st.get("staff_index"), name, src, b,
                                 {k: round(v, 2) for k, v in fits.items()}))
        print(f"\n{'='*76}\n{fam.upper()}\n{'='*76}")
        for (grp, src), n in sorted(tab.items()):
            print(f"   {grp:20s} {src:24s} {n:5d}")
        print(f"\n   proposals the provenance gate REFUSES on unread-clef "
              f"staves: {len(gained)}")
        for g in gained:
            print("     *", g)


if __name__ == "__main__":
    main()
