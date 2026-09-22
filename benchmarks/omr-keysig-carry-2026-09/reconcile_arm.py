"""The SHIPPED reconciler, driven on the staged record, scored against the PRINT.

⚠️ THE FIRST PASS SCORED A SKETCH. `carry_accuracy.py` implements the obvious
carry — same part, take the decided value — and measures it at ONE staff,
because 6 of 7 parts disagree with themselves. That is a finding about the
sketch, not about the mechanism this project already owns:
`key_signature_vote.reconcile` does not carry blindly. It weighs each reading
by how many accidentals were actually SEEN, computes a per-page reference, and
honours an asymmetry the sketch ignores — **a reader loses accidentals and
never invents them** — so a fuller reading outranks a thinner one instead of
tying with it.

So this drives the real module and scores its OUTPUT.

⚠️ THE ONE MAPPING THAT IS A JUDGEMENT, STATED RATHER THAN BURIED.
`can_carry` marks a source that can OVER-count. The record names its source in
the verdict's REASON, and the two readers fail in opposite directions — this
file's own record: *"the locator loses accidentals to broken ink, the template
can match spurious ink and over-count"*. So:

    reason "fitted"            -> the locator  -> can_carry TRUE
    reason "fitted_by_template"-> the template -> can_carry FALSE

That is the module's own distinction, applied to the record's own field. It is
the only place this arm decides anything, and `--all-carry` flips it off as a
control so its effect is visible rather than assumed.

⚠️ `ordinal` IS THE STAFF'S POSITION IN ITS OWN SYSTEM, not the part id — the
module says so, and it is what identifies the instrument across systems when
the systems line up. On this document they do not always (12/11/11/11/8/11/11),
which is a real limit of the module here and is reported, not hidden.

SCORED TWO WAYS, because an abstention is not neutral in a file: a staff with
no `<key>` reads as NO ACCIDENTALS, so on the horns, trumpets and timpani —
which print none — abstaining is accidentally right.
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.omr.key_signature_vote import StaffCandidate, reconcile

HERE = Path(__file__).resolve().parent
REC = Path("/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records")
TRUTH = Path("benchmarks/omr-keysig-truth-2026-09/truth.json")


def litolff_truth():
    t = json.loads(TRUTH.read_text())
    inst = t["instruments"]
    return {(s["page"], s["system"], i): (n, inst[n]["fifths"])
            for s in t["systems"] for i, n in enumerate(s["lineup"])}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all-carry", action="store_true",
                    help="control: let every reading carry, ignoring its source")
    ap.add_argument("--slot-join", action="store_true",
                    help="identify a part by the pipeline's own slot_index "
                         "instead of by position in the system. The module "
                         "uses `ordinal` because it predates the part join; "
                         "this document prints 12/11/11/11/8/11/11 staves, so "
                         "position CANNOT identify a part across its systems.")
    ap.add_argument("--whole-document", action="store_true",
                    help="pool every system of every page into ONE vote. "
                         "`reconcile` is called per PAGE, and page 1 of this "
                         "record prints ONE system -- so a carry has no "
                         "sibling to come from and the page is unreachable by "
                         "construction. A part is the same part across pages.")
    ap.add_argument("--carry-only", action="store_true",
                    help="apply CARRIES and ignore REJECTIONS -- the two halves "
                         "of this module pull opposite ways and nothing "
                         "separates them, so this measures the half that fills "
                         "a silence without the half that creates one")
    a = ap.parse_args()

    truth = litolff_truth()
    d = json.loads((REC / "beethoven5-p1-p4-ink-identity.record.json").read_text())["record"]
    keys = {v["subject"]: v for v in d["verdicts"] if v["quantity"] == "key_signature"}
    slots = {v["subject"]: v for v in d["verdicts"]
             if v["quantity"] == "slot_index" and v["outcome"] == "decided"}

    # one page-wide vote per PAGE, since `ordinal` identifies a part within a page
    by_page = collections.defaultdict(list)
    meta = {}
    for subj, v in sorted(keys.items()):
        _, p, s, i = subj.split("/")
        p, s, i = int(p), int(s), int(i)
        det = v.get("detail") or {}
        decided = v["outcome"] == "decided"
        n_acc = det.get("n_accidentals")
        page_key = 0 if a.whole_document else p
        idx = len(by_page[page_key])
        sv = slots.get(subj)
        ordinal = (int(sv['value']) if (a.slot_join and sv is not None) else i)
        by_page[page_key].append(StaffCandidate(
            staff_index=idx,
            system_index=(p * 10 + s) if a.whole_document else s,
            ordinal=ordinal,
            fifths=v.get("value") if decided else None,
            weight=float(n_acc) if isinstance(n_acc, (int, float)) and n_acc else 1.0,
            source=v.get("reason") or "",
            can_carry=True if a.all_carry else (v.get("reason") != "fitted_by_template"),
        ))
        meta[(page_key, idx)] = (subj, p, s, i)

    tag = ("carry-only" if a.carry_only else
           "all-carry" if a.all_carry else "shipped")
    if a.slot_join:
        tag += "+slotjoin"
    if a.whole_document:
        tag += "+wholedoc"
    before_r = before_f = after_r = after_f = 0
    fixed = broken = 0
    actions = collections.Counter()
    moves = []
    total = 0

    for p, cands in sorted(by_page.items()):
        res = reconcile(cands)
        out = res.verdicts
        for c in cands:
            subj, pp, s, i = meta[(p, c.staff_index)]
            name, tf = truth[(pp, s, i)]
            total += 1
            b = c.fifths
            v = out.get(c.staff_index)
            aft = v.fifths if v is not None else b
            if a.carry_only and v is not None and v.action != "carried":
                aft = b          # leave the reading exactly as it was
            actions[v.action if v is not None else "none"] += 1
            before_r += (b is not None and b == tf)
            after_r += (aft is not None and aft == tf)
            bf = ((b if b is not None else 0) == tf)
            af = ((aft if aft is not None else 0) == tf)
            before_f += bf
            after_f += af
            if b != aft:
                moves.append((subj, name, b, aft, tf, "RIGHT" if af else "wrong",
                              v.action if v else "?"))
            if af and not bf:
                fixed += 1
            elif bf and not af:
                broken += 1

    print(f"ARM      {tag}")
    print(f"REACH    {total} staves; readings that MOVED: {len(moves)}")
    print(f"ACTIONS  {dict(actions)}")
    print()
    print(f"READING  right {before_r} -> {after_r}   ({after_r - before_r:+d})")
    print(f"FILE     right {before_f} -> {after_f}   ({after_f - before_f:+d})")
    print(f"         WRONG->RIGHT {fixed}, RIGHT->WRONG {broken}")
    print()
    if moves:
        print("every staff that moved:")
        for subj, name, b, aft, tf, ok, act in moves:
            print(f"   {subj:<16} {name:<14} {str(b):>5} -> {str(aft):>5} "
                  f"truth {tf:>2}  {ok:<5} [{act}]")

    (HERE / "out" / f"reconcile-{tag}.json").write_text(json.dumps(
        {"arm": tag, "staves": total, "moved": len(moves),
         "reading_before": before_r, "reading_after": after_r,
         "file_before": before_f, "file_after": after_f,
         "fixed": fixed, "broken": broken, "actions": dict(actions)}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
