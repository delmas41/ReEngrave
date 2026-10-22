"""ROADMAP 2.12f -- GATHER ONCE, ADJUDICATE TWICE for the articulation side.

    python3 benchmarks/omr-shape-role-2026-09/readjudicate_artic_side.py \
        <record.json> --label <id> --out <json>

Rebuilds a Log from a saved record's GATHER rows, runs the articulation /
fermata ownership chain on THIS tree, and writes one row per mark: the
verdicts, the mark's page box and the owning head's page box (for tiles).

Run it before the change (the BASE) and after (the ARM) on the same record:
the two outputs differ by this lane and nothing else. ADJUDICATE-ONLY by
construction -- `Q.ARTICULATION_MARK`, `Q.GLYPH_BOX`, `Q.FERMATA_MARK` are
GATHER rows this lane does not change -- so a saved record is a valid input;
a GATHER change would be invisible to it (CLAUDE.md Sec.6b).

THE CONTROL THAT CAN FAIL (printed before any delta): every `Q.GLYPH_OWNER`
verdict the chain rebuilds is compared with the one the record itself
carries. A number short of N of N means the rebuild is not the pipeline
(rows dropped, order wrong) and nothing downstream of it is evidence. The
record's own `articulation_owner` verdicts are NOT a baseline -- the shared
records predate several landings (CLAUDE.md Sec.6b) -- and their agreement
with the rebuild is printed for information only.

Every record is read through `record_io.load_record`, never a naive json.load.
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools.omr.staged import adjudicate                      # noqa: E402
from tools.omr.staged import adjudicators                    # noqa: E402,F401
from tools.omr.staged.record import Log, Q, Subject          # noqa: E402
from tools.omr.staged.record_io import load_record           # noqa: E402

#: The chain this lane touches, in ORDER's own order. `GLYPH_OWNER` first
#: because both owners read it; the side decision exists only after the lane.
CHAIN = [Q.GLYPH_OWNER, Q.ARTICULATION_OWNER,
         getattr(Q, "ARTICULATION_SIDE", None), Q.FERMATA_OWNER]


def _order() -> list:
    """`adjudicate.ORDER`'s own sequence restricted to the chain AND to every
    decision whose VERDICT the chain reads, transitively -- a chain that
    leaves a prerequisite out reads a hole where the pipeline read a verdict,
    and the glyph_owner control below is what catches that."""
    adjudicate._ensure_decisions()
    want = {q for q in CHAIN if q is not None}
    todo = list(want)
    while todo:
        q = todo.pop()
        spec = adjudicate.REGISTRY.get(q)
        if spec is None:
            continue
        for w in spec.wants:
            if w in adjudicate.REGISTRY and w not in want:
                want.add(w)
                todo.append(w)
    return [q for q in adjudicate.ORDER if q in want]


def rebuild(rec: dict, keep: set) -> Log:
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
    return log


def _vd(v) -> dict | None:
    if v is None:
        return None
    return {"outcome": getattr(v.outcome, "value", str(v.outcome)),
            "reason": v.reason,
            "value": v.value if not isinstance(v.value, (set, frozenset)) else sorted(v.value),
            "detail": json.loads(json.dumps(v.detail, default=str))}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--label", default="")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)

    data = load_record(a.record)
    rec = data["record"]
    order = _order()
    adjudicate._ensure_decisions()
    keep = set()
    for q in order:
        keep.update(adjudicate.REGISTRY[q].wants)
        keep.add(adjudicate.REGISTRY[q].subjects_from or q)
    # positions + the page boxes the tiles need ride in the same rows
    keep.add(Q.ARTICULATION_POSITION)
    # `adjudicate.run` calls `reconcile_group_owners` after GLYPH_OWNER, which
    # reads these rows directly (not through any `wants`)
    keep.add(Q.MARK_GROUP)
    keep.discard(None)
    log = rebuild(rec, keep)
    adjudicate.run(log, order=order)

    # ---- the control that can fail --------------------------------------
    saved_go = {v["subject"]: v for v in rec["verdicts"]
                if v["quantity"] == Q.GLYPH_OWNER}
    n = same = 0
    for subj, v in saved_go.items():
        mine = log.verdict(Q.GLYPH_OWNER, Subject.from_key(subj))
        n += 1
        if mine is not None and mine.value == v.get("value") \
                and getattr(mine.outcome, "value", mine.outcome) == v["outcome"]:
            same += 1
    print(f"CONTROL glyph_owner rebuilt == saved: {same} of {n}")

    saved_ao = {v["subject"]: v for v in rec["verdicts"]
                if v["quantity"] == Q.ARTICULATION_OWNER}
    ao_same = ao_n = 0
    marks = [o for o in rec["observations"] if o["quantity"] == Q.ARTICULATION_MARK]
    box = {o["subject"]: o for o in rec["observations"]
           if o["quantity"] == Q.GLYPH_BOX}
    out_rows = []
    for o in marks:
        subj = o["subject"]
        s = Subject.from_key(subj)
        ow = log.verdict(Q.ARTICULATION_OWNER, s)
        sd = (log.verdict(Q.ARTICULATION_SIDE, s)
              if getattr(Q, "ARTICULATION_SIDE", None) else None)
        sv = saved_ao.get(subj)
        if sv is not None:
            ao_n += 1
            if ow is not None and ow.value == sv.get("value") \
                    and getattr(ow.outcome, "value", ow.outcome) == sv["outcome"]:
                ao_same += 1
        owner_key = ow.value if ow is not None and ow.value else None
        d = o.get("detail") or {}
        out_rows.append({
            "subject": subj, "class": o["value"], "page": s.page,
            "suffix_side": d.get("side"),
            "mark_bbox_page": d.get("bbox_page_px"),
            "owner": _vd(ow), "side": _vd(sd),
            "owner_bbox_page": ((box[owner_key].get("detail") or {})
                                .get("bbox_page_px") if owner_key in box else None),
        })
    print(f"INFO articulation_owner rebuilt == saved: {ao_same} of {ao_n}")

    fer = []
    for o in rec["observations"]:
        if o["quantity"] != Q.FERMATA_MARK:
            continue
        s = Subject.from_key(o["subject"])
        fer.append({"subject": o["subject"], "class": o["value"],
                    "suffix_side": (o.get("detail") or {}).get("side"),
                    "owner": _vd(log.verdict(Q.FERMATA_OWNER, s))})

    c = collections.Counter()
    for r in out_rows:
        ow = r["owner"] or {}
        c["owner:%s/%s" % (ow.get("outcome"), ow.get("reason"))] += 1
        if r["side"]:
            c["side:%s/%s" % (r["side"]["outcome"], r["side"]["reason"])] += 1
    fc = collections.Counter()
    for r in fer:
        ow = r["owner"] or {}
        fc["owner:%s/%s" % (ow.get("outcome"), ow.get("reason"))] += 1
    summary = {"marks": len(out_rows), "fermatas": len(fer),
               "articulation": dict(sorted(c.items())),
               "fermata": dict(sorted(fc.items())),
               "control_glyph_owner": [same, n],
               "info_articulation_owner_vs_saved": [ao_same, ao_n]}
    pdf = ((data.get("provenance") or {}).get("settings") or {}).get(
        "args", {}).get("pdf")
    # WHICH CODE ADJUDICATED -- the record's own `provenance.commit` names the
    # tree that GATHERED it, which is a different fact (CLAUDE.md Sec.4b).
    import subprocess
    try:
        head = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=str(REPO),
            stderr=subprocess.DEVNULL).decode().strip()
        dirty = bool(subprocess.check_output(
            ["git", "status", "--porcelain", "--untracked-files=no"],
            cwd=str(REPO), stderr=subprocess.DEVNULL).decode().strip())
    except Exception:                                  # noqa: BLE001
        head, dirty = None, None
    res = {"label": a.label, "record": a.record, "pdf": pdf,
           "adjudicated_on": {"commit": head, "dirty": dirty},
           "gathered_on": data.get("provenance", {}).get("commit"),
           "tree": data.get("provenance", {}).get("commit"),
           "order": order, "summary": summary,
           "articulations": out_rows, "fermatas": fer}
    pathlib.Path(a.out).write_text(json.dumps(res, indent=1, sort_keys=True))
    print(json.dumps(summary, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
