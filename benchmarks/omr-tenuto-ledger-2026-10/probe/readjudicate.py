"""ROADMAP 2.84 -- base vs arm on ONE saved GATHER: re-decide
`Q.ARTICULATION_IS_NOT_AN_ARTICULATION` (and every decision whose verdict it
reads, transitively) with the code under `--root`, and write one row per mark.

    # base: a clean worktree at origin/main; arm: this tree
    python3 .../readjudicate.py REC.json --root <tree> --out base.json
    python3 .../readjudicate.py --diff base.json arm.json

ADJUDICATE only, GATHER fixed: the change is an ADJUDICATE change, so this is
the instrument that can see it (CLAUDE.md §6b; it is blind to GATHER, which
this lane does not touch). THE CONTROL THAT CAN FAIL: the rebuilt
`Q.GLYPH_OWNER` verdicts must equal the saved record's on the arm's own
inputs -- a replay that drops a prerequisite reads a hole there.
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import sys
from pathlib import Path


def _replay(record: str, root: str) -> dict:
    sys.path.insert(0, root)
    from tools.omr.staged import adjudicate, adjudicators  # noqa: F401
    from tools.omr.staged.record import Log, Q, Subject
    from tools.omr.staged.record_io import load_record

    adjudicate._ensure_decisions()
    chain = {Q.ARTICULATION_IS_NOT_AN_ARTICULATION, Q.GLYPH_OWNER,
             Q.NOTEHEAD_IS_NOT_A_NOTEHEAD}
    todo = list(chain)
    while todo:
        spec = adjudicate.REGISTRY.get(todo.pop())
        if spec is None:
            continue
        for w in spec.wants:
            if w in adjudicate.REGISTRY and w not in chain:
                chain.add(w)
                todo.append(w)
    order = [q for q in adjudicate.ORDER if q in chain]
    keep = set()
    for q in order:
        keep.update(adjudicate.REGISTRY[q].wants)
        keep.add(adjudicate.REGISTRY[q].subjects_from or q)
    keep.add(Q.MARK_GROUP)
    keep.discard(None)
    if os.environ.get("RA_BREAK_CONTROL"):
        # RED for the control: drop the ownership evidence it must reproduce
        keep.discard(Q.GLYPH_BAND_DISTANCE)
        keep.add(Q.GLYPH_BAND_DISTANCE + "__dropped")

    data = load_record(record)
    rec = data.get("record", data)
    log = Log()
    rows = [(r, "obs") for r in rec["observations"] if r["quantity"] in keep]
    rows += [(r, "abs") for r in rec.get("abstentions", [])
             if r["quantity"] in keep]
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
    log.freeze()
    adjudicate.run(log, order=order)

    saved_go = {v["subject"]: v for v in rec["verdicts"]
                if v["quantity"] == Q.GLYPH_OWNER}
    same = sum(1 for k, v in saved_go.items()
               if (lambda m: m is not None and m.value == v.get("value")
                   and m.outcome.value == v["outcome"])(
                   log.verdict(Q.GLYPH_OWNER, Subject.from_key(k))))
    marks = []
    box = {o["subject"]: o for o in rec["observations"]
           if o["quantity"] == Q.GLYPH_BOX}
    for o in rec["observations"]:
        if o["quantity"] != Q.ARTICULATION_MARK:
            continue
        v = log.verdict(Q.ARTICULATION_IS_NOT_AN_ARTICULATION,
                        Subject.from_key(o["subject"]))
        marks.append({
            "subject": o["subject"], "class": o["value"],
            "page_box": (box.get(o["subject"], {}).get("detail") or {}).get(
                "bbox_page_px"),
            "outcome": None if v is None else v.outcome.value,
            "value": None if v is None else v.value,
            "reason": None if v is None else v.reason,
            "detail": None if v is None else json.loads(
                json.dumps(v.detail, default=str))})
    return {"record": record, "root": root,
            "provenance": data.get("provenance"),
            "control_glyph_owner_rebuilt_equals_saved": [same, len(saved_go)],
            "marks": marks}


def _diff(a: str, b: str) -> None:
    A, B = json.load(open(a)), json.load(open(b))
    print("control glyph_owner base", A["control_glyph_owner_rebuilt_equals_saved"],
          "arm", B["control_glyph_owner_rebuilt_equals_saved"])
    bm = {m["subject"]: m for m in B["marks"]}
    t = collections.Counter()
    for m in A["marks"]:
        n = bm[m["subject"]]
        t[(f"{m['outcome']}/{m['reason']}", f"{n['outcome']}/{n['reason']}",
           "tenuto" if "Tenuto" in m["class"] else "other")] += 1
    for (x, y, k), c in sorted(t.items()):
        print(f"{c:5d}  {k:7s} {x:30s} -> {y}")
    print("marks", len(A["marks"]), len(B["marks"]))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record", nargs="?")
    ap.add_argument("--root")
    ap.add_argument("--out")
    ap.add_argument("--diff", nargs=2)
    a = ap.parse_args(argv)
    if a.diff:
        _diff(*a.diff)
        return 0
    res = _replay(a.record, str(Path(a.root).resolve()))
    Path(a.out).write_text(json.dumps(res, indent=1, default=str))
    print(a.out, "control", res["control_glyph_owner_rebuilt_equals_saved"],
          "marks", len(res["marks"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
