#!/usr/bin/env python3
"""l281p2_arm: ROADMAP 2.81 PHASE 2 -- GATHER ONCE, DECIDE TWICE, through INFER.

Rebuilds a `Log` from ONE saved quick record's observations and abstentions (GATHER) and runs the
whole deciding sequence (`pipeline.decide`: ADJUDICATE -> GROUPS -> EVALUATE -> INFER -> the bounded
second EVALUATE) on the CURRENT tree. Two arms therefore differ only in the code under test, with no
detector jitter. Writes `{"record": ...}` -- the shape `l281_extract.py` streams.

    python3 l281p2_arm.py RECORD --control              # the CONTROL: base code must reproduce RECORD
    python3 l281p2_arm.py RECORD --out arm.json [--flag 1]

⚠️ BLIND TO ANY GATHER CHANGE, by construction (CLAUDE.md §6b: `readjudicate`/`reexport_arm` are
structurally blind to one and a zero from them is not evidence). This item changes ADJUDICATE's
RANKING and INFER only, so it is the right instrument; a GATHER change would not be.

⚠️ `--control` compares every DURATION verdict (outcome, value, reason, candidate order) between the
saved record and the replay on the SAME tree the record came from. A replay that does not reproduce
the record is not a control and every number below it would measure the harness. It can fail: pass
`--corrupt` and it must report differences.
"""
import argparse
import collections
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "benchmarks" / "omr-infer-stage-2026-09"))

import reinfer  # noqa: E402
from tools.omr.staged import pipeline  # noqa: E402
from tools.omr.staged.record import Q  # noqa: E402


def key(v):
    cands = tuple((json.dumps(c["value"], sort_keys=True, default=str), c["support"])
                  for c in (v.get("candidates") or ()))
    return (v["outcome"], json.dumps(v.get("value"), sort_keys=True, default=str), v["reason"], cands)


def standing(rows):
    sup = {v.get("supersedes") for v in rows if v.get("supersedes")}
    live = [v for v in rows if v["id"] not in sup]
    return live[-1] if live else rows[-1]


def duration_by_subject(js, stage_prefix=None):
    by = collections.defaultdict(list)
    for v in js["verdicts"]:
        if v["quantity"] == Q.DURATION:
            by[v["subject"]].append(v)
    return {s: standing(rows) for s, rows in by.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--control", action="store_true")
    ap.add_argument("--corrupt", action="store_true", help="control must FAIL: drop every Q.BEAM_STROKE observation")
    ap.add_argument("--out", default=None)
    ap.add_argument("--flag", default=None, help="OMR_BARE_STEM_BAR value for this arm (the INFER rule)")
    ap.add_argument("--rank", default=None, help="OMR_BARE_STEM_RANK value for this arm (the ADJUDICATE order)")
    a = ap.parse_args()
    from tools.omr.staged.record_io import load_record
    doc = load_record(a.record)
    rec = doc["record"] if "record" in doc else doc
    print("record provenance:", doc.get("provenance"))
    gather_only = dict(rec, verdicts=[])
    if a.corrupt:
        gather_only = dict(gather_only, observations=[o for o in gather_only["observations"]
                                                     if o["quantity"] != Q.BEAM_STROKE])
    if a.flag is not None:
        os.environ["OMR_BARE_STEM_BAR"] = a.flag
    if a.rank is not None:
        os.environ["OMR_BARE_STEM_RANK"] = a.rank
    log = reinfer.rebuild(gather_only)
    result = pipeline.decide(log, progress=False)
    js = log.to_json()
    print("replayed:", {k: v for k, v in js["counts"].items()})
    saved = duration_by_subject(rec)
    mine = duration_by_subject(js)
    same = diff = 0
    kinds = collections.Counter()
    for s, v in saved.items():
        w = mine.get(s)
        if w is not None and key(v) == key(w):
            same += 1
        else:
            diff += 1
            kinds[(v["outcome"], None if w is None else w["outcome"])] += 1
    print(f"STANDING DURATION verdicts: {same} of {len(saved)} identical to the record, {diff} differ"
          f"; replay has {len(mine) - len(saved):+d} extra subjects")
    if kinds:
        print("  differ:", dict(kinds))
    if a.control:
        ok = diff == 0 and len(mine) == len(saved)
        if a.corrupt:
            print("CORRUPTED CONTROL:", "FAILS as it must" if not ok else "PASSED -- THE CONTROL CANNOT FAIL")
            return 0 if not ok else 3
        print("CONTROL:", "reproduces the record" if ok else "DOES NOT REPRODUCE THE RECORD")
        return 0 if ok else 2
    infer_report = result.get("inference")
    if infer_report is not None:
        print("inferred by rule:", dict(collections.Counter(i[0] for i in infer_report.inferred)))
        print("disabled:", infer_report.disabled)
    if a.out:
        Path(a.out).write_text(json.dumps({"record": js, "provenance": doc.get("provenance"),
                                           "arm": {"flag": a.flag, "rank": a.rank, "replayed_from": a.record}},
                                          separators=(",", ":"), default=str))
        print("wrote", a.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
