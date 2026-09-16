"""GATHER ONCE, ADJUDICATE TWICE — does recording S4 and S6 move any verdict?

The claim this has to establish is a NEGATIVE with a positive control beside
it: `adjudicate_arc_kind`'s VALUE must be untouched (the detector's class
still decides; the grammar is recorded), while `detail["grammar"]` must gain
the two new witnesses on a real page. A run where nothing moves and nothing
appears is a run that compared a file with itself.

⚠️⚠️ THIS IS AN ADJUDICATE-ONLY INSTRUMENT AND THAT IS CORRECT FOR THIS
CHANGE, which is why it is used rather than a re-gather. `readjudicate.py`'s
own docstring records that it is STRUCTURALLY BLIND to a GATHER change — it
rebuilds a `Log` from a saved record's rows, so a new row never enters. **This
change gathers nothing.** `Q.STEM` and `Q.ARC_BOX` were already in the log
(1,920 and 779 rows on this record); what changed is that `adjudicate_arc_kind`
now reads them. So the blind spot is not engaged, and the control is valid.
⚠️ It would NOT be valid for the WIP on `claude/arc-grammar-sean-rules`, whose
availability claim is about which heads the flanking rule reaches.

    python3 .../arc_grammar_arm.py <record.json> --control
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.omr.staged import adjudicate                          # noqa: E402
from tools.omr.staged import adjudicators                        # noqa: E402,F401
from tools.omr.staged.record import Log, Q, Subject              # noqa: E402


def rebuild(rec: dict) -> Log:
    """One Log holding exactly the saved record's GATHER rows, in order.

    Transcribed from `benchmarks/omr-staged-duration-beams-2026-09/
    readjudicate.py`, deliberately — that file is the instrument this repo
    already trusts for an ADJUDICATE-only arm, and a second, subtly different
    rebuild is how two arms stop being comparable.
    """
    log = Log()
    rows = [(r, "obs") for r in rec["observations"]]
    rows += [(r, "abs") for r in rec.get("abstentions", [])]
    rows.sort(key=lambda t: t[0]["id"])
    for r, kind in rows:
        sub = Subject.from_key(r["subject"])
        detail = dict(r.get("detail") or {})
        if kind == "obs":
            log.observe(sub, r["quantity"], r["value"], reader=r["reader"],
                        frame=r["frame"], score=r.get("score"), **detail)
        else:
            log.abstain(sub, r["quantity"], reader=r["reader"],
                        frame=r["frame"], reason=r["reason"], **detail)
    return log


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("record")
    ap.add_argument("--control", action="store_true")
    a = ap.parse_args()

    rec = json.load(open(a.record))["record"]
    log = rebuild(rec)
    adjudicate.run(log)
    got = {v["subject"]: v for v in log.to_json()["verdicts"]
           if v["quantity"] == Q.ARC_KIND}
    want = {v["subject"]: v for v in rec["verdicts"]
            if v["quantity"] == Q.ARC_KIND}

    same = diff = 0
    kinds: Counter = Counter()
    for key, w in want.items():
        g = got.get(key)
        if g is None:
            kinds["absent from the rebuild"] += 1
            diff += 1
            continue
        if (g["outcome"] == w["outcome"] and g.get("value") == w.get("value")
                and g.get("reason") == w.get("reason")):
            same += 1
        else:
            diff += 1
            kinds[f"{w.get('value')}->{g.get('value')}"] += 1
    extra = len(got) - len(want)
    print(f"CONTROL: {same} of {len(want)} arc_kind VALUES reproduced "
          f"exactly, {diff} differ, {extra:+d} extra")
    if kinds:
        print("        ", kinds.most_common())

    # ── the positive control: the witnesses actually appear ──────────────────
    # ⚠️ WITHOUT THIS, "779 of 779 reproduced" is indistinguishable from an
    # arm that never ran the new code at all — the exact failure this repo
    # records as *a control that was never testing what its name says*.
    s4 = sum(1 for v in got.values()
             if "s4_stem_position" in (v["detail"].get("grammar") or {}))
    s4_on = sum(1 for v in got.values()
                if ((v["detail"].get("grammar") or {})
                    .get("s4_stem_position") or {}).get("any_endpoint_on_a_stem"))
    s6 = sum(1 for v in got.values()
             if (v["detail"].get("grammar") or {}).get("s6_stacked_with"))
    old_s4 = sum(1 for v in want.values()
                 if "s4_stem_position" in (v["detail"].get("grammar") or {}))
    old_s6 = sum(1 for v in want.values()
                 if (v["detail"].get("grammar") or {}).get("s6_stacked_with"))
    print(f"WITNESSES: s4 recorded on {s4} arcs (was {old_s4}), "
          f"of which endpoint-on-a-stem {s4_on}; "
          f"s6 recorded on {s6} arcs (was {old_s6})")
    grammar_says = Counter(
        (v["detail"].get("grammar") or {}).get("says") for v in got.values())
    print("grammar 'says':", grammar_says.most_common())

    if a.control:
        ok = (diff == 0 and extra == 0)
        if not (s4 and s6):
            print("DEAD: the new witnesses appear on no arc — the arm did not "
                  "exercise the change.", file=sys.stderr)
            return 2
        if old_s4 or old_s6:
            print("SUSPECT: the BASE record already carries the witnesses, so "
                  "this record was not made by the pre-change tree.",
                  file=sys.stderr)
            return 3
        return 0 if ok else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
