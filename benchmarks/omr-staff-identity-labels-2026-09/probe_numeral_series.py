#!/usr/bin/env python3
"""Is the numeral-series fragment a FAMILY, or one page of one publisher?

Phase 2 (ii-b), asked before it is built. The shared-block rule (ii-a) is
geometric — a name engraved midway between two staves — and it leaves eight
fragments behind. Six are Bach Brandenburg's `I` / `III` beside a
`Violini II`, where the name is printed on the MIDDLE staff of a bracketed
three and each staff carries only its own numeral. No geometry reaches that:
the name's block is centred ON its own tick (0.029 off), so it is
indistinguishable in position from an ordinary one-staff label.

The only rule that reaches it is an INFERENCE — a bare-numeral fragment
inherits the instrument of an adjacent label whose own text ends in a numeral
of the same series. Before writing that, count how many staves in the corpus it
could ever fire on, and on how many distinct editions. A rule fitted to one
page of one publisher is a rule fitted to a page.

⚠️ This counts OPPORTUNITY, not correctness. A staff where the rule COULD fire
is not a staff where it would be right; the point is the denominator.

════════════════════════════════════════════════════════════════════════════
MEASURED 2026-09-05, AND THE RULE IS REFUSED.

    staves the numeral-series rule could fire on : 6
    distinct rows                                : 1
    distinct editions                            : 1
    of those 6, staves carrying hand-read truth  : 0

All six are `bach-brandenburg3-mvt1-468678-p1` system 0 — `I` and `III`
beside `Violini II`, `Viole II`, `Violoncelli II`. One page, one publisher,
and works.json hand-reads no staff on that row, so a rule written here could
be neither validated nor regression-tested. Three further reasons, each
independent:

* it is INFERENCE, not geometry. The shared-block rule (ii-a) reads a fact
  off the page — a block centred between two ticks — and this reads a
  convention off a printing tradition. The repo's own record is that a
  constant read off a gap survives and a constant fitted to a corpus does
  not.
* the donor is not always ABOVE. Bach prints the name on the MIDDLE staff of
  a bracketed three, so the rule needs "nearest in either direction", and
  that is exactly the freedom that would let a fragment reach across a
  family boundary on a page laid out differently.
* the same page's phase-1 segmentation is a known failure — it reads
  `[12, 12]` here against the `[12, 3, 3, 3, 1, 2]` in the era's committed
  fixtures — and the staff-identity audit scores NO signal on that row for
  that reason.

What would reopen it: a second edition in the corpus that prints a bracketed
group's name once with per-staff numerals. Re-run this probe after any
widening; if `distinct editions` reaches 2 with truth on both, the rule has a
denominator and can be measured.
════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO))

from tools.omr.instruments import lookup, normalize_label      # noqa: E402

_NUMERAL_ONLY = re.compile(r"^[\s|(\[]*([IVXivx]+|\d+)[\s|)\].,]*$")
_ENDS_NUMERAL = re.compile(r"([IVXivx]+|\d+)[\s.,)]*$")


def main() -> int:
    d = json.loads((HERE / "ladder.json").read_text())
    opportunities, by_row, by_publisher = [], Counter(), Counter()
    for r in d["rows"]:
        by_sys: dict[int, list] = {}
        for s in r["staves"]:
            by_sys.setdefault(s["system"], []).append(s)
        for sysi, staves in sorted(by_sys.items()):
            staves.sort(key=lambda s: s["position"])
            for i, s in enumerate(staves):
                txt = (s.get("ladder_text") or "").strip()
                if not txt or s.get("ladder_resolved"):
                    continue
                if not _NUMERAL_ONLY.match(txt):
                    continue
                # an adjacent staff whose label resolves AND ends in a numeral
                for j in (i - 1, i + 1):
                    if not (0 <= j < len(staves)):
                        continue
                    n = staves[j]
                    if not n.get("ladder_resolved"):
                        continue
                    if not _ENDS_NUMERAL.search(
                            (n.get("ladder_text") or "").strip()):
                        continue
                    opportunities.append({
                        "row_id": r["row_id"], "system": sysi,
                        "position": s["position"], "fragment": txt,
                        "donor_position": n["position"],
                        "donor_text": n.get("ladder_text"),
                        "donor": n["ladder_resolved"],
                        "truth": s.get("TRUTH_name"),
                    })
                    by_row[r["row_id"]] += 1
                    by_publisher[r["publisher"][:34]] += 1
                    break
    print(f"staves the numeral-series rule could fire on: {len(opportunities)}")
    print(f"  distinct rows       : {len(by_row)}")
    print(f"  distinct editions   : {len(by_publisher)}")
    print()
    for k, v in by_row.most_common():
        print(f"    {v:>3}  {k}")
    print()
    for o in opportunities:
        print(f"  {o['row_id'][:30]:30} s{o['system']} p{o['position']:>2} "
              f"{o['fragment']!r:8} <- p{o['donor_position']} "
              f"{o['donor_text']!r:22} = {o['donor']:12} TRUTH {o['truth']!r}")
    (HERE / "numeral-series.json").write_text(json.dumps(opportunities, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
