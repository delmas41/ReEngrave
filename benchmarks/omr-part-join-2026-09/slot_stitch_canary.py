"""Does the slot join graft one instrument's music onto another? Ask the page.

⚠️ **THE OBVIOUS CANARY DOES NOT REACH THIS, AND I RECOMMENDED IT BEFORE
CHECKING.** `label_contradiction` looked like the free check for exactly this
failure mode — it asks whether `staff → slot → name` is broken and needs no
truth file. It cannot see `OMR_SLOT_STITCH`: the flag is read in `export.py`
(`_slot_stitch_enabled`) and `label_contradiction` is computed during the
CONTEXTUAL pass and stored in the transcription, strictly UPSTREAM of the
export. A transcription's contradiction count is identical with the flag on and
off, by construction. Naming a mechanism is not measuring one.

Its QUESTION does reach it, applied at the join instead of at the staff: the
slot join makes a part out of several staves, one per system, so **if the join
grafts, those staves' OWN margin labels disagree with each other.** That needs
no truth file either — it asks the document to agree with itself, which is what
made `label_contradiction` worth having.

⚠️ Read the ABSTENTION column. A staff with no label read is not evidence of
agreement; on a scan most staves carry no printed label at all, so a part whose
members are all unlabelled is `no_evidence`, never `agree`.

    python3 benchmarks/omr-part-join-2026-09/slot_stitch_canary.py
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.omr import export as E  # noqa: E402

FIX = Path("/Users/seanjohnson/Desktop/ReEngrave/benchmarks/omr-scan-e2e-2026-09/fixtures")


def labels_of(staff: dict) -> set[str]:
    """The instruments THIS staff's own margin was read as, on its own page.

    ⚠️ NOT `staff["instrument_label"]`, which is slot-carried — one raw text
    per SLOT stamped onto every staff of that slot — so an audit on it cannot
    disagree. `contextual.py` says so in its own comment, and
    `test_label_contradiction.py` pins it by AST. Use the per-staff evidence.
    """
    out: set[str] = set()
    for key in ("label_evidence", "absent_instrument"):
        ev = staff.get(key)
        if isinstance(ev, dict):
            ev = ev.get("label_evidence")
        if not isinstance(ev, list):
            continue
        for e in ev:
            if isinstance(e, dict) and e.get("instrument"):
                out.add(str(e["instrument"]))
    if staff.get("instrument") and staff.get("instrument_source") == "label":
        out.add(str(staff["instrument"]))
    return out


def main() -> int:
    rows = sorted(FIX.glob("*.restamp-composed.omr.json"))
    total = Counter()
    print(f"{'row':40} {'parts':>6} {'stitched':>9} {'agree':>6} "
          f"{'DISAGREE':>9} {'no_evidence':>12}")
    any_reached = 0
    for f in rows:
        rid = f.name.replace(".restamp-composed.omr.json", "")
        result = json.loads(f.read_text())
        by_slot = E._stitch_slots_by_slot(result)
        if by_slot is None:
            print(f"{rid:40} {'-':>6} {'ABSTAINS (ordinal join or slots)':>9}")
            continue
        any_reached += 1
        slots, _ = by_slot
        c = Counter()
        offenders = []
        for i, members in enumerate(slots):
            labelled = [labels_of(s) for s in members]
            named = [x for x in labelled if x]
            if not named:
                c["no_evidence"] += 1
            elif len(set(frozenset(x) for x in named)) == 1:
                c["agree"] += 1
            else:
                c["disagree"] += 1
                offenders.append((i, named))
        total.update(c)
        print(f"{rid:40} {len(slots):>6} {'yes':>9} {c['agree']:>6} "
              f"{c['disagree']:>9} {c['no_evidence']:>12}")
        for i, named in offenders:
            print(f"    ⚠️ slot {i}: " + " vs ".join(sorted(",".join(sorted(x))
                                                            for x in named)))
    print("\n" + "=" * 72)
    print(f"reached rows: {any_reached} of {len(rows)}   "
          f"agree {total['agree']}  DISAGREE {total['disagree']}  "
          f"no_evidence {total['no_evidence']}")
    # ⚠️ a positive control: 0 disagreements means nothing if nothing was checked
    print(f"positive control: {total['agree'] + total['disagree']} stitched "
          f"parts had label evidence at all")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
