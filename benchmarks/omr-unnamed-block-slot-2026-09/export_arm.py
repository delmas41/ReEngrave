"""WHAT THE BLOCK RULE PUTS BACK IN THE FILE — one gather, exported twice.

`OMR_HOLD_OUT_UNIDENTIFIED` (default ON, Sean: *"hold out - I want truth"*)
keeps a staff the join could not NAME out of the file altogether and counts
its music under `staff_not_identified`. The gate it reads is
`Q.SLOT_INDEX` -- so a staff this rule places stops being held out, and the
music that was counted-and-dropped becomes music in a part.

That is the number Sean's question is actually about (*"the first system had
twice as many staffs as the pdf"*, *"all of them empty"*), and it is not the
same number as *how many slots the rule got right*: a correctly placed staff
whose notes were never read puts nothing back.

⚠️ SAME BLIND SPOTS AS `block_arm.py`, plus one. It re-decides `slot_index`
over a FIXED gather and holds every other verdict at the committed value --
INCLUDING `part_partition`, which is the decision that says whether the
exporter joins by slot at all. So this measures the file under the join the
committed run already chose, and says nothing about a run where a fuller slot
table would have changed that choice.
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "benchmarks/omr-infer-stage-2026-09"))

import reinfer                                                   # noqa: E402
from tools.omr.staged import adjudicate, evaluate, infer          # noqa: E402
from tools.omr.staged import adjudicators, inferences             # noqa: E402,F401
from tools.omr.staged import export as EX                         # noqa: E402
from tools.omr.staged.adjudicators import identity                # noqa: E402
from tools.omr.staged.record import Q                             # noqa: E402


def arm(rec, *, enabled: bool, with_infer: bool, only_block: bool = False):
    log = reinfer.rebuild(rec, skip_verdicts=frozenset({Q.SLOT_INDEX}))
    real = identity._place_in_family_block
    if not enabled:
        identity._place_in_family_block = lambda *a, **k: None
    try:
        adjudicate.run(log, order=(Q.SLOT_INDEX,))
    finally:
        identity._place_in_family_block = real
    if with_infer:
        # ⚠️⚠️ THE DURATION RULES ARE A CONFOUND AND THE FIRST RUN OF THIS ARM
        # CARRIED IT. `infer.run` fires every registered rule, so an OFF ->
        # INFER delta mixes this rule with `collapse_duration_by_column` and
        # `collapse_duration_to_barline` -- which between them collapsed 16
        # narrowed durations and put 13 more events in the file, on WIND
        # staves this rule never touches. The tell was four wind parts gaining
        # notes in a change about strings. `only_block` runs this rule alone.
        keep = list(infer.RULES)
        if only_block:
            mine = [r for r in keep if r.target == Q.SLOT_INDEX]
            assert mine, "the rule under test is not registered"
            infer.RULES[:] = mine
        try:
            infer.run(log, evaluate.Report(fired=[], skipped=[], stubs=[]))
        finally:
            infer.RULES[:] = keep
    xml, report = EX.to_musicxml({"record": log.to_json()})
    return xml, report


def figures(xml: str, report: dict) -> dict:
    dropped = report.get("notes_not_written") or {}
    # ⚠️ `part_join`, NOT `provenance`. The first draft of this arm read a key
    # that does not exist and printed `None` for three fields -- which reads
    # as a zero, and would have reported "no staff is held out" on a run
    # holding 25 out. `.get` on the wrong key is the quietest way to measure
    # nothing; the fields below are asserted non-None by the caller.
    prov = report.get("part_join") or {}
    bal = report.get("balance") or {}
    return {
        "parts": xml.count("<score-part "),
        "measures": xml.count("<measure "),
        # ⚠️ `<note` COUNTS RESTS TOO -- a MusicXML rest is a `<note>` with a
        # `<rest/>` inside it -- so the pitched count is the one that answers
        # "did music reach the file", and the two move in OPPOSITE directions
        # here: a bar that was padded with a measure rest because the staff
        # was held out gains real notes and LOSES the rest.
        "note_elements": xml.count("<note"),
        "pitched_notes": xml.count("<pitch>"),
        "rests": xml.count("<rest"),
        "held_out_staves": prov.get("held_out_staves"),
        "unidentified_parts": len(prov.get("unidentified_parts") or []),
        "join_used": prov.get("join_used"),
        "staff_not_identified": dropped.get("staff_not_identified"),
        "notes_not_written_total": report.get("notes_not_written_total"),
        # ⚠️ THE ACCOUNTING CONTROL, CARRIED RATHER THAN ASSUMED. It is an
        # EQUALITY and `to_musicxml` RAISES when it fails, so a run that
        # reaches here has it -- but a figure quoted without it is a figure
        # whose reader cannot tell.
        "balanced": bal.get("balanced"),
        "events_in_log": bal.get("events_in_log"),
        "events_written": bal.get("events_written"),
        # ⚠️ EVERY BUCKET, NOT JUST THE ONE UNDER TEST. `staff_not_identified`
        # falling by 642 while the TOTAL falls by 655 means thirteen events
        # left some OTHER bucket, and a report that carried only the headline
        # would leave that difference unexplained -- which is how a change
        # outside its intended population goes unnoticed.
        "dropped": dict(dropped),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--json", default=str(HERE / "out" / "export-arm.json"))
    a = ap.parse_args()
    doc = json.load(open(a.record))
    rec = doc["record"] if "record" in doc else doc
    print(f"record provenance: {doc.get('provenance')}")

    out = {}
    for name, kw in (("off", dict(enabled=False, with_infer=False)),
                     ("on", dict(enabled=True, with_infer=False)),
                     ("block", dict(enabled=True, with_infer=True,
                                    only_block=True)),
                     ("infer", dict(enabled=True, with_infer=True))):
        xml, report = arm(rec, **kw)
        out[name] = figures(xml, report)
        (HERE / "out" / f"{name}.musicxml").write_text(xml)
        print(f"\n── {name.upper()}")
        for k, v in out[name].items():
            print(f"   {k:<26} {v}")
        for k in ("held_out_staves", "join_used", "balanced"):
            if out[name][k] is None:
                print(f"⚠️ {k} came back None — this arm is reading a key "
                      f"that does not exist, and None renders as a zero.",
                      file=sys.stderr)

    print("\n── DELTA (off -> block: THIS RULE ALONE)")
    for k in out["off"]:
        x, y = out["off"][k], out["block"][k]
        if isinstance(x, int) and isinstance(y, int) and x != y:
            print(f"   {k:<26} {x} -> {y}  ({y - x:+d})")
    Path(a.json).write_text(json.dumps(out, indent=1, default=str))
    print(f"\nwrote {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
