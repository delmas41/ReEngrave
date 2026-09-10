"""GATHER ONCE, ADJUDICATE TWICE — an A/B that carries no detector jitter.

⚠️ THE POINT IS THE CONTROL. Running the staged CLI twice on a scan compares
two DETECTOR runs as much as two rules; on the engraved fixture the before/after
pair already disagreed with an offline simulation by two bars for exactly that
reason. This rebuilds a `Log` from ONE saved record's observations and
abstentions and re-runs ADJUDICATE over it, so the two arms differ only in the
rule under test.

⚠️ IT VERIFIES ITSELF FIRST. `--control` re-adjudicates with nothing disabled
and compares every duration verdict against the ones the pipeline wrote. A
rebuild that does not reproduce the record is not a control, and a silent
mismatch would make every number here a measurement of the harness.

    python3 .../readjudicate.py <staged.json> --control
    python3 .../readjudicate.py <staged.json> --off marks --out /tmp/off.json
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.omr.staged import adjudicate, evaluate                # noqa: E402
from tools.omr.staged import adjudicators, consequences          # noqa: E402,F401
from tools.omr.staged.record import Log, Subject                 # noqa: E402
from tools.omr.staged.adjudicators import rhythm as RH           # noqa: E402


def rebuild(rec: dict) -> Log:
    """One Log holding exactly the saved record's GATHER rows, in order."""
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


def _disable(which: str) -> None:
    """Switch an attachment off, reproducing the OLD BEHAVIOUR exactly.

    ⚠️ Not "delete the feature" — a flag read on the notehead's own subject and
    a dot likewise is what `adjudicate_duration` DID, and it yields nothing
    because `gather` puts both on the mark's own glyph. Returning empty is that
    same nothing, arrived at honestly.
    """
    if which in ("stem", "all"):
        RH._stem_joined = lambda beams, stems, head_box: ([], [])
    if which in ("marks", "all"):
        RH._attached_flags = lambda ev, cell, attached: ([], 0)
        RH._attached_dots = lambda ev, cell, head_box, space: []


def durations(log: Log) -> dict:
    out = {}
    for v in log.to_json()["verdicts"]:
        if v["quantity"] == "duration":
            out[v["subject"]] = v
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--control", action="store_true",
                    help="re-adjudicate unchanged and diff against the record")
    ap.add_argument("--off", choices=["stem", "marks", "all"], default=None)
    ap.add_argument("--out")
    a = ap.parse_args()

    rec = json.load(open(a.record))["record"]
    if a.off:
        _disable(a.off)
    log = rebuild(rec)
    adjudicate.run(log)
    evaluate.run(log)
    got = durations(log)

    if a.control:
        want = {v["subject"]: v for v in rec["verdicts"]
                if v["quantity"] == "duration"}
        same = diff = 0
        kinds: Counter = Counter()
        for key, w in want.items():
            g = got.get(key)
            if g is None:
                kinds["absent from the rebuild"] += 1
                diff += 1
                continue
            if (g["outcome"] == w["outcome"]
                    and (g.get("value") or {}).get("beats")
                    == (w.get("value") or {}).get("beats")):
                same += 1
            else:
                diff += 1
                kinds[f"{w['outcome']}->{g['outcome']}"] += 1
        extra = len(got) - len(want)
        print(f"CONTROL: {same} of {len(want)} duration verdicts reproduced "
              f"exactly, {diff} differ, {extra:+d} extra")
        if kinds:
            print("        ", kinds.most_common())
        return 0 if (diff == 0 and extra == 0) else 1

    if a.out:
        Path(a.out).write_text(json.dumps({"record": log.to_json()},
                                          indent=1, default=str))
        print(f"wrote {a.out}")
    print(Counter(v["outcome"] for v in got.values()).most_common())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
