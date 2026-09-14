"""The slot rule against HAND-READ PRINT TRUTH, on the reader's own committed output.

⚠️⚠️ WHAT THIS IS, AND THE ONE THING IT IS NOT. It runs the DECISION'S OWN
`_forced_pairing` and the DECISION'S OWN lexicon (`instruments.lookup`) over the
margin labels the reader ACTUALLY produced on this document -- committed, in
`benchmarks/omr-part-join-phase2-2026-09/out/margin-label-reach.log` -- and
scores the slot each staff gets against the hand-read lineup in
`printed-lineups.json`. So it measures THE RULE, on real reader output, against
print truth.

⚠️ IT IS NOT AN END-TO-END RUN. A cloud container holds no `omr-weights/` and no
`library/`, so GATHER cannot read a page here; `slot_arm.py` beside this file is
the end-to-end arm and needs a record this container cannot make. What that
costs is real and is stated rather than papered over: this cannot catch a fault
in how names REACH the decision (`_names_by_system`, the ordinal indexing, the
`Q.INSTRUMENT` verdicts), only a fault in what the decision DOES with them.
Those are separately covered by `test_staged_slot_by_name.py`.

⚠️ THE TWO SOURCES ARE INDEPENDENT AND NEITHER IS THE OTHER'S RASTER. The truth
is a human on the print (corroborated by `printed-staves.json` prose); the names
are Surya + Tesseract + the text layer. A row where they agree is not circular.

    python3 benchmarks/omr-slot-index-2026-09/probe_rule_vs_print.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO))

from tools.omr.instruments import lookup                                # noqa: E402
from tools.omr.staged.adjudicators.identity import _forced_pairing      # noqa: E402

PHASE2 = REPO / "benchmarks" / "omr-part-join-phase2-2026-09"
REACH = PHASE2 / "out" / "margin-label-reach.log"
TRUTH = PHASE2 / "printed-lineups.json"

#: ⚠️ A CONDENSED STAFF CARRIES TWO REFERENCE PARTS, and the truth says so in
#: words (`Violoncello e Basso`). Scored as CORRECT for either slot: the staff
#: really is both, and demanding one would charge the rule for the engraving.
CONDENSED = {"Violoncello e Basso": ("Violoncello", "Basso")}


def read_labels():
    """{(page, page_staff_index): raw label text} from the committed log."""
    out, page = {}, None
    for line in REACH.read_text().splitlines():
        m = re.match(r"^page (\d+):", line)
        if m:
            page = int(m.group(1))
            continue
        m = re.match(r"^\s+staff\s+(\d+)\s+'([^']*)'", line)
        if m and page is not None:
            out[(page, int(m.group(1)))] = m.group(2)
    return out


def main() -> int:
    truth = json.loads(TRUTH.read_text())
    systems = truth["systems"]
    labels = read_labels()

    # page -> [system rows in printed order]
    by_page = {}
    for e in systems:
        by_page.setdefault(e["page"], []).append(e)
    for rows in by_page.values():
        rows.sort(key=lambda e: e["system"])

    # (page, system) -> [read name or None, by system-local ordinal]
    read = {}
    for page, rows in sorted(by_page.items()):
        base = 0
        for e in rows:
            names = []
            for k in range(e["staves"]):
                text = labels.get((page, base + k))
                match = lookup(text) if text else None
                names.append(match.instrument.name if match else None)
            read[(page, e["system"])] = names
            base += e["staves"]

    # the reference: the document's largest system, as the rule picks it
    widest = max(e["staves"] for e in systems)
    ref_rows = [e for e in systems if e["staves"] == widest]
    ref_row = max(ref_rows, key=lambda e: sum(
        1 for n in read[(e["page"], e["system"])] if n is not None))
    ref_names = read[(ref_row["page"], ref_row["system"])]
    ref_truth = ref_row["lineup"]
    print(f"reference: p{ref_row['page']}/s{ref_row['system']}, {widest} staves, "
          f"{sum(1 for n in ref_names if n)} names read")
    print(f"  read      {ref_names}")
    print(f"  truth     {ref_truth}\n")

    def truth_slots(name):
        """Reference indices this truth name legitimately occupies."""
        if name in CONDENSED:
            return tuple(ref_truth.index(x) for x in CONDENSED[name]
                         if x in ref_truth)
        return (ref_truth.index(name),) if name in ref_truth else ()

    tally = {"correct": 0, "wrong": 0, "abstained": 0, "untruthable": 0}
    ord_tally = {"correct": 0, "wrong": 0}
    rows = []
    for e in systems:
        key = (e["page"], e["system"])
        names = read[key]
        short = e["staves"] < widest
        pairing = (_forced_pairing(names, ref_names) if short
                   else list(range(e["staves"])))
        for k in range(e["staves"]):
            want = truth_slots(e["lineup"][k])
            got = pairing[k] if k < len(pairing) else None
            if not want:
                tally["untruthable"] += 1
                verdict = "no-truth-slot"
            elif got is None:
                tally["abstained"] += 1
                verdict = "abstain"
            elif got in want:
                tally["correct"] += 1
                verdict = "ok"
            else:
                tally["wrong"] += 1
                verdict = "WRONG"
            # the incumbent: the staff's own ordinal, always
            if want:
                ord_tally["correct" if k in want else "wrong"] += 1
            rows.append((key, k, e["lineup"][k], names[k], got, verdict))

    print(f"{'system':>8} {'ord':>3}  {'printed':<22} {'read':<14} {'slot':>4}  verdict")
    for key, k, printed, name, got, verdict in rows:
        if verdict in ("ok", "no-truth-slot") and name is None:
            continue
        flag = "  <<<" if verdict == "WRONG" else ""
        print(f"  p{key[0]}/s{key[1]:<3} {k:>3}  {printed:<22} "
              f"{str(name):<14} {str(got):>4}  {verdict}{flag}")

    n = sum(tally.values())
    print(f"\nTHE RULE      {n} staves: correct {tally['correct']}, "
          f"WRONG {tally['wrong']}, abstained {tally['abstained']}, "
          f"no truth slot {tally['untruthable']}")
    print(f"THE ORDINAL   correct {ord_tally['correct']}, "
          f"WRONG {ord_tally['wrong']}   (the incumbent, every staff placed)")
    named = sum(1 for _, _, _, nm, _, _ in rows if nm is not None)
    print(f"\nREACH         {named} of {n} staves carry a read name")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
