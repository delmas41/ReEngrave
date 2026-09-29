"""ROADMAP 3.2b -- the ONE saved-record read: decide `Q.TIE_PAIR` on today's
tree over a saved record's own GATHER rows, then export base (the record as
saved, exporter pairing) and arm (the record + the new verdicts, record
pairing) from the SAME record in one process. No re-gather.

    python3 benchmarks/omr-tie-pairing-2026-09/probe/readjudicate_tie_pair.py \
        REC --out SUMMARY.json [--musicxml ARM.musicxml] [--base-musicxml B] \
        [--truth PAGETRUTH --truth-page 0]

`Q.TIE_PAIR` reads five upstream verdicts (`arc_kind`, `arc_owner`,
`arc_is_not_an_arc`, `glyph_owner`, `notehead_is_not_a_notehead`); they are
INJECTED as saved, so this prices this decision alone against the record's
own upstream answers. ⚠️ A GATHER change would be invisible here; this lane
changes no GATHER.

Prints the population first and exits 2 when no arc is decided `tie`
(reach before accuracy).
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import re
import sys
import time

sys.path.insert(0, os.getcwd())

from tools.omr.staged import adjudicate as A  # noqa: E402
from tools.omr.staged import adjudicators  # noqa: E402,F401
from tools.omr.staged import export as SX  # noqa: E402
from tools.omr.staged.record import (  # noqa: E402
    Candidate, Outcome, Q, Subject, Verdict)
from tools.omr.staged.record_io import load_record  # noqa: E402
from tools.omr.staged.review.rerun import rebuild_gather  # noqa: E402

INJECT = (Q.ARC_KIND, Q.ARC_OWNER, Q.ARC_IS_NOT_AN_ARC, Q.GLYPH_OWNER,
          Q.NOTEHEAD_IS_NOT_A_NOTEHEAD)


def _outcome(v):
    return {"decided": Outcome.DECIDED, "narrowed": Outcome.NARROWED,
            "abstained": Outcome.ABSTAINED}[v["outcome"]]


def _counts(xml):
    return {"tie_start": len(re.findall(r'<tie type="start"', xml)),
            "tie_stop": len(re.findall(r'<tie type="stop"', xml)),
            "tied": len(re.findall(r"<tied ", xml))}


def decide(result):
    """`result` with this tree's `Q.TIE_PAIR` verdicts appended."""
    rec = result["record"]
    log, id_map = rebuild_gather(rec)
    back = {new: old for old, new in id_map.items()}
    superseded = {v.get("supersedes") for v in rec["verdicts"]
                  if v.get("supersedes")}
    current = {}
    for v in rec["verdicts"]:
        if v["id"] not in superseded:
            current[(v["quantity"], v["subject"])] = v
    log.freeze()
    for (q, key), v in current.items():
        if q in INJECT:
            log.record(Verdict(
                id=log._next_id("vrd"), subject=Subject.from_key(key),
                quantity=q, outcome=_outcome(v), value=v["value"],
                decider=v["decider"], reason=v["reason"],
                candidates=tuple(Candidate(c["value"], c["support"])
                                 for c in (v.get("candidates") or ()))))
    A._ensure_decisions()
    spec = A.REGISTRY[Q.TIE_PAIR]
    subjects = A.subjects_for(log, spec)
    new = []
    for n, sub in enumerate(subjects):
        v = A.adjudicate_one(log, spec, sub).to_json()
        v["id"] = f"vrd:t32b{n:06d}"
        for f in ("considered", "used", "basis"):
            v[f] = [back.get(i, i) for i in v.get(f) or ()]
        v["correlated"] = [[back.get(i, i) for i in g]
                           for g in v.get("correlated") or ()]
        v["supersedes"] = None
        new.append(v)
    arm = dict(result)
    arm["record"] = dict(rec)
    arm["record"]["verdicts"] = list(rec["verdicts"]) + new
    return arm, new


def _only_pages(result, pages):
    """The record restricted to `pages` (a subject's first coordinate).

    ⚠️ A DOCUMENT-level row (`document`) has no page and is kept. A slice is a
    cheaper INPUT, not a different reader: the tie decision looks at most one
    bar either side and never across a system, so it cannot see the cut.
    """
    def keep(row):
        parts = row["subject"].split("/")
        return len(parts) < 2 or int(parts[1]) in pages
    rec = dict(result["record"])
    for k in ("observations", "verdicts", "abstentions"):
        rec[k] = [r for r in rec.get(k) or () if keep(r)]
    out = dict(result)
    out["record"] = rec
    return out


def _write_crop_cache(result, arm_rep, new, path):
    """Page boxes of both heads, every naming arc, and the home staff's lines
    -- so the crop script never touches the record."""
    rec = result["record"]
    boxes, lines, spacing = {}, {}, {}
    for o in rec["observations"]:
        q = o["quantity"]
        if q in (Q.GLYPH_BOX, Q.ARC_BOX) and (o.get("detail") or {}).get(
                "bbox_page_px"):
            boxes[o["subject"]] = o["detail"]["bbox_page_px"]
        elif q == Q.STAFF_LINES:
            lines[o["subject"]] = o["value"]
        elif q == Q.STAFF_SPACING:
            spacing[o["subject"]] = o["value"]
    home = {v["subject"]: (v.get("detail") or {}).get("home_staff")
            for v in new}
    reason = {v["subject"]: v.get("reason") for v in new}

    def entry(kind, item):
        arcs = item.get("arcs") or []
        staff = next((home[a] for a in arcs if home.get(a)), None) or \
            "staff/" + "/".join(item["start"].split("/")[1:4])
        return {"kind": kind, "start": item["start"], "stop": item["stop"],
                "pitches": item.get("pitches") or [item.get("pitch")] * 2,
                "arcs": arcs, "staff": staff,
                "reasons": sorted({reason.get(a) for a in arcs
                                   if reason.get(a)}),
                "start_box": boxes.get(item["start"]),
                "stop_box": boxes.get(item["stop"]),
                "arc_boxes": [boxes.get(a) for a in arcs],
                "staff_lines": lines.get(staff),
                "staff_spacing": spacing.get(staff)}

    cache = {"record": result.get("provenance"),
             "linked": [entry("linked", t) for t in
                        arm_rep.get("tie_links") or ()],
             "contradictions": [entry(c["kind"], c) for c in
                                arm_rep.get("tie_contradictions") or ()],
             # ⚠️ 3.2c: every chord pairing, marked or not -- a pair whose
             # end a held-out bar swallowed is still a claim about the print.
             "chord": [entry("chord", {**v["value"], "arcs": [v["subject"]],
                                       "pitches": [None, None]})
                       for v in new if v.get("reason") == "paired_in_a_chord"]}
    json.dump(cache, open(path, "w"), indent=1)


def _against_truth(result, arm_rep, truth_path, page_index, new):
    """Each WRITTEN pair against the page truth's drawn tie symbols.

    A written pair is RIGHT when a drawn tie's centre lies between its two
    heads' centres in x and within two head heights of them in y; WRONG
    otherwise. A drawn tie no written pair matches is MISSED. ⚠️ Page truth
    and the gather share the render's pixel frame (300 dpi); a frame error
    would read as every pair WRONG, never as a quiet pass.
    """
    t = json.load(open(truth_path))
    drawn = [s for s in t["pages"][page_index]["symbols"]
             if s.get("family") == "tie" or s.get("class") == "tie"]
    heads = {}
    for o in result["record"]["observations"]:
        if o["quantity"] == Q.GLYPH_BOX and (o.get("detail") or {}).get(
                "bbox_page_px"):
            heads[o["subject"]] = o["detail"]["bbox_page_px"]
    written = set()
    for v in new:
        if v["outcome"] == "decided":
            written.add((v["value"]["start"], v["value"]["stop"]))
    refused = {(c["start"], c["stop"])
               for c in arm_rep.get("tie_contradictions") or ()}
    written -= refused
    used = set()
    right, wrong = [], []
    for start, stop in sorted(written):
        a, b = heads[start], heads[stop]
        xa, xb = (a[0] + a[2]) / 2, (b[0] + b[2]) / 2
        yc = (a[1] + a[3] + b[1] + b[3]) / 4
        h = (a[3] - a[1] + b[3] - b[1]) / 2
        hit = None
        for i, s in enumerate(drawn):
            sx, sy = s["x"] + s["w"] / 2, s["y"] + s["h"] / 2
            if xa <= sx <= xb and abs(sy - yc) <= 2 * h and i not in used:
                hit = i
                break
        if hit is None:
            wrong.append([start, stop])
        else:
            used.add(hit)
            right.append([start, stop])
    missed = [drawn[i] for i in range(len(drawn)) if i not in used]
    return {"drawn": len(drawn), "written_pairs": len(written),
            "right": len(right), "wrong": len(wrong), "wrong_pairs": wrong,
            "missed": len(missed), "missed_symbols": missed}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--out", required=True)
    ap.add_argument("--musicxml")
    ap.add_argument("--base-musicxml")
    ap.add_argument("--truth")
    ap.add_argument("--truth-page", type=int, default=0)
    ap.add_argument("--crops-cache",
                    help="write the geometry of every marked link and every "
                         "contradiction here, for crop_ties_3_2b.py")
    ap.add_argument("--pages", default="",
                    help="keep only these record pages (comma list); "
                         "DOCUMENT-level rows are kept")
    a = ap.parse_args(argv)

    t0 = time.time()
    result = load_record(a.record)
    if a.pages:
        result = _only_pages(result, {int(p) for p in a.pages.split(",")})
    kinds = collections.Counter()
    cur = {}
    for v in result["record"]["verdicts"]:
        if v["quantity"] == Q.ARC_KIND:
            cur[v["subject"]] = v
    for v in cur.values():
        kinds[(v["outcome"], v.get("value"))] += 1
    print("arc_kind (saved):", dict(kinds))
    n_tie = sum(c for (_o, val), c in kinds.items() if val == "tie")
    if n_tie == 0:
        print("DEAD: no arc decided tie on this record")
        return 2

    base_xml, base_rep = SX.to_musicxml(result)
    arm, new = decide(result)
    arm_xml, arm_rep = SX.to_musicxml(arm)
    if a.musicxml:
        open(a.musicxml, "w").write(arm_xml)
    if a.base_musicxml:
        open(a.base_musicxml, "w").write(base_xml)

    by_reason = collections.Counter((v["outcome"], v["reason"]) for v in new)
    print("tie_pair (today):", dict(by_reason))
    tie_w = {k: v for k, v in sorted(arm_rep["written"].items())
             if "tie" in k}
    out = {
        "record": a.record,
        "seconds": round(time.time() - t0, 1),
        "arc_kind_saved": {f"{o}:{v}": c for (o, v), c in kinds.items()},
        "tie_pair": {f"{o}:{r}": c for (o, r), c in by_reason.most_common()},
        "base": {**_counts(base_xml),
                 "written": {k: v for k, v in sorted(
                     base_rep["written"].items()) if "tie" in k},
                 "arcs_not_written_other": {
                     k: v for k, v in sorted(
                         base_rep["arcs_not_written"].items())
                     if not k.startswith("tie")},
                 "tie_pairing": base_rep.get("tie_pairing")},
        "arm": {**_counts(arm_xml), "written": tie_w,
                "tie_pairing": arm_rep.get("tie_pairing"),
                "arcs_not_written": {
                    k: v for k, v in sorted(
                        arm_rep["arcs_not_written"].items())
                    if k.startswith("tie")},
                # ⚠️ 3.2c: the NON-tie buckets too -- on Breitkopf p1 42
                # marked links wrote 0 `<tie>`, and the reason is here
                # (`arc_ends_in_one_chord`, the 2.8 bar-sum hold-out).
                "arcs_not_written_other": {
                    k: v for k, v in sorted(
                        arm_rep["arcs_not_written"].items())
                    if not k.startswith("tie")},
                "bars_held_out_sum": {
                    k: v for k, v in (arm_rep.get("bars_held_out_sum")
                                      or {}).items() if k != "held"},
                "tie_contradictions": arm_rep.get("tie_contradictions")},
        "decided_pairs": [
            {"arc": v["subject"], **v["value"],
             **{k: v["detail"].get(k) for k in
                ("dy_spaces", "dx_spaces", "crosses_barline",
                 "arc_dy_spaces")}}
            for v in new if v["outcome"] == "decided"],
    }
    if a.truth:
        out["truth"] = _against_truth(result, arm_rep, a.truth,
                                      a.truth_page, new)
    if a.crops_cache:
        _write_crop_cache(result, arm_rep, new, a.crops_cache)
    json.dump(out, open(a.out, "w"), indent=1)
    print(json.dumps({k: out[k] for k in out if k != "decided_pairs"},
                     indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
