#!/usr/bin/env python3
"""Do RESOLVED non-treble labels actually reach the clef, or are they dropped?

The last live route from labels to clefs. `probe_clef_reach.py` closed the
reach half — all 29 unresolved staves in a non-treble family print no label at
all, so more reading cannot help them. That leaves the other half: **60 staves
whose family's conventional clef is bass or alto AND whose label DID resolve.**
If those come out treble anyway, the label was computed correctly and dropped
on the way to its consumer, which is worth far more than any reach work — a
wrong clef carries into every pitch on the staff and into which slot table the
key signature is fitted.

Two numbers, and they mean different things:

    ends non-treble        the label reached the clef, one way or another
    ends treble            it did not, and then:
      declined             `propose_clef` was consulted and said no, or the
                           proposal was recorded `applied: false`
      never consulted      the staff's slot carried no instrument at all

⚠️ MEASUREMENT ONLY, AND DELIBERATELY NOT A FIX. `correct_clefs_from_instruments`
and its caller live in `contextual.py`, which this workstream does not edit.
Everything here is read from committed transcription JSON.

⚠️ THE CLEF THE DETECTOR READ IS NOT A DEFECT. `do_apply = apply and not
detected` — the pass only acts where the detector saw no clef glyph, and a
proposal against a READ clef is recorded `applied: false` ON PURPOSE, so a
disagreement is surfaced without being acted on. A staff that ends treble
because its own printed clef was read as treble is a DETECTOR question, not a
label one, and is counted separately. Conflating the two would manufacture a
defect out of a documented design decision.

⚠️ FIXTURE PROVENANCE IS MIXED AND IS PRINTED PER ROW. Six rows are the
`.sharedON` transcriptions this session produced on the current tree; the rest
are the committed `..graft09` fixtures in the MAIN checkout. The label A/B
showed 0 label changes on those rows, and their re-detected staff structure
matched the fixture's, so the substrate is fair — but it is not the same run,
and a reader must be able to see which is which.

════════════════════════════════════════════════════════════════════════════
MEASURED 2026-09-05. **NOT A CLASS-1 DEFECT. THE LABELS→CLEFS ROUTE IS
CLOSED END TO END, AND IT IS CLOSED BY DESIGN.**

    resolved non-treble-family staves measured : 60
      ENDS NON-TREBLE                          : 53   (0.883)
      ends treble, proposal WITHHELD (clef READ):  4
      ends treble, NO proposal (too few heads)  :  3
      ends treble, NEVER CONSULTED              :  0

**Zero staves are "never consulted."** On all 7 that end treble the label is
present, the slot carries the right instrument, and `clef_source` is
`detector` — the staff's own printed clef was READ as treble. So nothing is
being dropped between the label and its consumer.

The two declines are both documented behaviour, verified rather than assumed:

* **3 declined on register evidence, honestly.** Re-running `propose_clef` on
  the exact staff dicts gives `None` for all three, and the reason is
  `n < MIN_NOTEHEADS` — they carry 9, 8 and 0 noteheads against a floor of 12.
  A register estimate on 8 notes is not worth acting on.
* **4 proposed and withheld** because `do_apply = apply and not detected`: a
  clef the detector actually read outranks one deduced from a convention.

⚠️ BUT THE WITHHELD FOUR CARRY STRIKING EVIDENCE, and that is the finding
worth carrying forward. Three of them are not close calls:

    Brahms p4 s0 Kontrafagott   treble->bass  fit 1.000 vs current 0.000 (13)
    Brahms p4 s1 Kontrafagott   treble->bass  fit 1.000 vs current 0.000 (18)
    Brahms p3 s0 Pauken         treble->bass  fit 0.821 vs current 0.107 (28)
    Beethoven p1 s0 Viola       treble->alto  fit 1.000 vs current 1.000 (30)

A `current_fit` of 0.000 means the register says the clef in effect places
**not one note** inside the instrument's written range. The tier that exists
for exactly this — `OMR_INSTRUMENT_CLEF_DEFAULT` / `treble_override` — is off
by default and gated on `TREBLE_OVERRIDE_INSTRUMENTS`. The fourth, the Viola,
is a genuine tie (1.000 vs 1.000), which is the ambiguity `propose_clef`'s own
docstring warns about.

⚠️⚠️ **A CROSS-SESSION INTERACTION, AND IT RUNS THE WRONG WAY.**
`TREBLE_OVERRIDE_INSTRUMENTS = ("Viola", "Bassoon", "Timpani")` — Contrabassoon
is NOT in it. And Contrabassoon only became the resolved instrument for those
staves TODAY: before the contra- cross product landed, `K-Fag.` resolved to
**Bassoon**, which IS in the table (measured on `24911c35` in this
directory's Phase 1). So a correct lexicon fix silently moved two Brahms
staves OUT of the override tier's reach. Nothing changed in practice, because
the flag is off by default — but if it is ever turned on, the CORRECTED label
now gets less help than the wrong one did. The table is keyed on instrument
names and was written when one of those names could not occur.

⚠️ NOT ACTED ON HERE. `TREBLE_OVERRIDE_INSTRUMENTS` lives in
`clef_correction.py` and its caller in `contextual.py`; this workstream edits
`staff_labels*`, `instruments.py` and the margin crop. Reported, not changed.
════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO))

from tools.omr.instruments import lookup                       # noqa: E402

MAIN = Path("/Users/seanjohnson/Desktop/ReEngrave")
FX = [REPO / "benchmarks" / "omr-scan-e2e-2026-09" / "fixtures",
      MAIN / "benchmarks" / "omr-scan-e2e-2026-09" / "fixtures"]


def find(row_id: str):
    """-> (path, provenance). This session's arm first, then the committed one."""
    for d in FX:
        p = d / f"{row_id}.sharedON.omr.json"
        if p.is_file():
            return p, "sharedON (this session, current tree)"
    for d in FX:
        for p in sorted(d.glob(f"{row_id}*graft09.omr.json")):
            return p, "..graft09 (committed)"
    return None, None


def main() -> int:
    lad = json.loads((HERE / "ladder.json").read_text())
    # (row, system, position) -> printed truth name, for staves whose label
    # RESOLVED and whose family's conventional clef is not treble.
    want = {}
    for r in lad["rows"]:
        for s in r["staves"]:
            t = s.get("TRUTH_name")
            if not t or not s.get("ladder_resolved"):
                continue
            h = lookup(t)
            inst = h.instrument if (h and h.instrument) else None
            if inst and inst.default_clef != "treble":
                want[(s["row_id"], s["system"], s["position"])] = (
                    t, inst.name, inst.default_clef, s["ladder_resolved"])

    rows = sorted({k[0] for k in want})
    verdicts, detail, prov = Counter(), [], {}
    missing = 0
    for rid in rows:
        path, p = find(rid)
        prov[rid] = p
        if path is None:
            missing += sum(1 for k in want if k[0] == rid)
            continue
        d = json.loads(path.read_text())
        ctx = d.get("contextual") or {}
        inst_by_slot = {x["slot"]: x.get("instrument")
                        for x in (ctx.get("reference") or [])}
        props = {}
        for rec in ctx.get("proposals") or []:
            props[(rec["page_index"], rec["system_index"],
                   rec["staff_index"])] = rec
        for page in d.get("pages", []):
            for sy in page.get("systems", []):
                staves = sy.get("staves", [])
                for pos, staff in enumerate(staves):
                    key = (rid, sy.get("system_index"), pos)
                    if key not in want:
                        continue
                    tname, iname, want_clef, read_inst = want[key]
                    clef = staff.get("clef")
                    src = staff.get("clef_source")
                    slot = staff.get("slot_index")
                    rec = props.get((page.get("page_index"),
                                     sy.get("system_index"),
                                     staff.get("staff_index")))
                    if clef and clef != "treble":
                        v = "ENDS_NON_TREBLE"
                    elif inst_by_slot.get(slot) is None:
                        v = "treble_NEVER_CONSULTED_no_slot_instrument"
                    elif rec is not None and not rec.get("applied"):
                        v = ("treble_PROPOSED_not_applied_clef_was_READ"
                             if rec.get("clef_was_read")
                             else "treble_PROPOSED_not_applied_OTHER")
                    else:
                        v = "treble_NO_PROPOSAL_declined"
                    verdicts[v] += 1
                    detail.append({
                        "row_id": rid, "system": sy.get("system_index"),
                        "position": pos, "truth": tname,
                        "read_instrument": read_inst,
                        "slot_instrument": inst_by_slot.get(slot),
                        "wants_clef": want_clef, "clef": clef,
                        "clef_source": src, "verdict": v,
                        "proposal": None if rec is None else
                        {k: rec[k] for k in ("from_clef", "to_clef", "fit",
                                             "current_fit", "n_noteheads",
                                             "clef_was_read", "applied")},
                    })

    print("fixture provenance")
    for rid in rows:
        print(f"  {rid:34} {prov.get(rid)}")
    print()
    n = sum(verdicts.values())
    print(f"resolved non-treble-family staves measured: {n}"
          f"{f'  (+{missing} with no transcription)' if missing else ''}")
    for v, c in verdicts.most_common():
        print(f"  {c:>4}  {v}")
    print()
    ends = verdicts["ENDS_NON_TREBLE"]
    print(f"ANSWER 1 — the label reached the clef on {ends}/{n} "
          f"= {ends / max(1, n):.3f}")
    print(f"ANSWER 2 — of the {n - ends} that end treble:")
    for v, c in verdicts.most_common():
        if v != "ENDS_NON_TREBLE":
            print(f"            {c:>4}  {v}")
    print()
    print("clef_source of the staves that end treble:")
    print("  ", dict(Counter(x["clef_source"] for x in detail
                             if x["verdict"] != "ENDS_NON_TREBLE")))
    print()
    for x in detail:
        if x["verdict"] != "ENDS_NON_TREBLE":
            print(f"  {x['row_id'][:30]:30} s{x['system']} p{x['position']:>2} "
                  f"{x['truth']!r:26} {x['slot_instrument']} wants "
                  f"{x['wants_clef']:6} got {x['clef']} ({x['clef_source']}) "
                  f"| {x['verdict']}")
            if x["proposal"]:
                print(f"        proposal {x['proposal']}")
    (HERE / "clef-consumer.json").write_text(json.dumps(
        {"provenance": prov, "verdicts": dict(verdicts), "detail": detail},
        indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
