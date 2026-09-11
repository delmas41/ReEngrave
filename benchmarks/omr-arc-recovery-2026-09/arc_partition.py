"""The arc partition on a staged record, and WHY the heads under a refused arc
are missing.

Sean, reading the print: *"almost no ties or slurs are converting."*
CLAUDE.md's answer, from the arc-export session, is that **76% of merged arcs
bind fewer than two noteheads** and that *"on a scan the usual cause is that
the notes under the arc were never detected"* -- a DETECTOR ceiling.

⚠️ This probe exists because that sentence is a HYPOTHESIS and was never
measured. `_noteheads_under` does not see the page's noteheads; it sees
`cell.detections`, which is what `_place_notes` SURVIVED. A head the detector
found, the record adjudicated, and the exporter then declined to write (no
pitch, a narrowed duration, another staff's copy) is invisible to the arc
pairing for a reason that has nothing to do with detection.

So for every merged arc group that binds fewer than two heads it asks: how
many GATHERED noteheads lie under this arc, and what became of each? The
answer is a partition over the record's own rows, not a count of what the file
holds.

⚠️ It is an EXPORT-stage instrument. It replays a saved record, so it is blind
by construction to any GATHER or ADJUDICATE change; it can only say what the
exporter does with the verdicts it was handed.

⚠️ THE COMPARISON IS IN PAGE PIXELS, the only frame two cells share, and the
record spells a page box in CORNERS while every legacy detection box is
`(x, y, w, h)`. `E._corners_to_wh` and `_legacy._SLUR_ARC_PAD_NOTEHEADS` are
IMPORTED rather than re-spelled -- this project has already paid for both
confusions once.
"""
from __future__ import annotations

import argparse
import collections
import json
from typing import Any, Dict, List, Optional, Tuple

from tools.omr import export as _legacy
from tools.omr.staged import export as E
from tools.omr.staged.record import Q


def head_fate(rec, sub: str) -> str:
    """What `_place_notes` did with this notehead row, by ITS OWN branch order.

    ⚠️ The order is `_place_notes`'s and must stay it: a head with neither a
    pitch nor a duration is reported under the first test that refuses it, the
    same one the exporter applies, or the two reports would disagree about a
    head they both decline.
    """
    if not rec.obs(Q.NOTEHEAD_CLASS, sub):
        return "not_a_notehead"
    pitch = rec.value(Q.PITCH, sub)
    dur_v = rec.verdict(Q.DURATION, sub)
    dur = dur_v["value"] if dur_v and dur_v["outcome"] == "decided" else None
    if pitch is None:
        return "no_pitch"
    if not isinstance(dur, dict):
        return "duration_" + (dur_v["outcome"] if dur_v else "absent")
    owner = rec.value(Q.GLYPH_OWNER, sub)
    if E.A.is_relocated_copy(sub, owner):
        return "owned_by_another_staff"
    if dur.get("measure_rest"):
        return "measure_rest"
    if _legacy._dotted_duration_for_beats(
            float(dur.get("written") or dur.get("beats") or 0.0)) is None:
        return "written_value_fits_no_note"
    return "written"


def heads_by_cell(rec) -> Dict[Tuple[Any, ...], List[Dict[str, Any]]]:
    """Every GATHERED notehead row, keyed by the cell its SUBJECT names, with
    its page box and its fate.

    ⚠️ Keyed by the SUBJECT's cell, not the owner's, because that is the cell
    whose arc it could be under: a relocated copy's ink is physically in the
    subject's crop. `_place_notes` places by subject too (and refuses the
    copy), so the two agree about where a head IS.
    """
    out: Dict[Tuple[Any, ...], List[Dict[str, Any]]] = collections.defaultdict(list)
    for o in rec.obs_of(Q.GLYPH_BOX):
        sub = o["subject"]
        s = E._parse_subject(sub)
        if s["glyph"] is None:
            continue
        if not rec.obs(Q.NOTEHEAD_CLASS, sub):
            continue
        out[(s["page"], s["system"], s["staff"], s["cell"] or 0)].append({
            "subject": sub,
            "page_box": E._corners_to_wh(E._page_box_of(o)),
            "fate": head_fate(rec, sub),
        })
    return out


def run(path: str) -> Dict[str, Any]:
    result = json.load(open(path))
    rec = E.Record(result)
    parts, _prov, notes_dropped, arcs_dropped, *_rest = E.build(rec)
    runs = {r.key: r for part in parts for r in part}
    heads = heads_by_cell(rec)

    n_rows = len(rec.obs_of(Q.ARC_BOX))
    placed = sum(len(c.arcs) for r in runs.values() for c in r.cells.values())

    groups: List[Dict[str, Any]] = []
    for part in parts:
        measures, per_measure_arcs, kinds, spacings, tops, breaks = \
            E._flatten_part(part)
        if not measures or not any(per_measure_arcs):
            continue
        cells = E._part_cells_in_order(part)
        for segments in _legacy._merge_arcs_across_barlines(
                measures, per_measure_arcs, spacings, tops, breaks):
            seen = {kinds.get(id(b)) for _m, b in segments}
            kind = "tie" if "tie" in seen else "slur"
            covered = _legacy._noteheads_under(measures, segments)
            # The heads the pairing WOULD have seen if nothing were held back:
            # every gathered notehead of these bars whose page-x centre falls
            # in the padded span. The pad is `_noteheads_under`'s own.
            would: List[Dict[str, Any]] = []
            no_box = 0
            for m_idx, (ax, _ay, aw, _ah) in segments:
                run_, cidx = cells[m_idx]
                pool = heads.get((run_.page, run_.system, run_.staff, cidx)) or []
                boxed = [h for h in pool if h["page_box"]]
                if not boxed:
                    no_box += len(pool)
                    continue
                pad = _legacy._SLUR_ARC_PAD_NOTEHEADS * (
                    sum(h["page_box"][2] for h in boxed) / len(boxed))
                for h in pool:
                    pb = h["page_box"]
                    if pb is None:
                        # A head with no page rectangle cannot be compared
                        # with an arc at all -- reported apart, never assumed
                        # in or out of the span.
                        no_box += 1
                        continue
                    xc = pb[0] + pb[2] / 2.0
                    if ax - pad <= xc <= ax + aw + pad:
                        would.append(h)
            groups.append({
                "kind": kind,
                "n_segments": len(segments),
                "bound": len(covered),
                "would": len(would),
                "fates": dict(collections.Counter(h["fate"] for h in would)),
                "heads_with_no_page_box_in_these_bars": no_box,
                "where": [
                    f"p{cells[m][0].page}/s{cells[m][0].system}"
                    f"/st{cells[m][0].staff}/c{cells[m][1]}"
                    for m, _b in segments],
                "subjects": [h["subject"] for h in would],
            })
    return {
        "arc_rows": n_rows,
        "placed": placed,
        "arcs_dropped_at_placement": dict(arcs_dropped),
        "groups": groups,
        "notes_not_written": dict(notes_dropped),
    }


def report(r: Dict[str, Any]) -> None:
    gs = r["groups"]
    by: "collections.Counter[Tuple[str, str]]" = collections.Counter()
    fate_of_missing: "collections.Counter[str]" = collections.Counter()
    for g in gs:
        b = g["bound"]
        bucket = "binds_0" if b == 0 else "binds_1" if b == 1 else "binds_2+"
        by[(g["kind"], bucket)] += 1
        if b < 2:
            for k, v in g["fates"].items():
                if k != "written":
                    fate_of_missing[k] += v
    print(f"arc rows on the record   {r['arc_rows']}")
    print(f"placed in a cell         {r['placed']}")
    print(f"dropped before placement {r['arcs_dropped_at_placement']}")
    print(f"merged groups            {len(gs)}")
    for k in sorted(by):
        print(f"    {k[0]:5s} {k[1]:9s} {by[k]}")
    refused = [g for g in gs if g["bound"] < 2]
    print(f"\nREFUSED (bind fewer than two heads): {len(refused)}")
    print("heads under them the pairing never saw, by why:")
    for k, v in fate_of_missing.most_common():
        print(f"    {k:28s} {v}")
    rescuable = [g for g in refused
                 if g["bound"] + sum(v for k, v in g["fates"].items()
                                     if k != "written") >= 2]
    print(f"\n  ...refused groups that WOULD reach two heads: {len(rescuable)}")
    print(f"  ...refused groups with NO head under them at all: "
          f"{sum(1 for g in refused if g['would'] == 0)}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    r = run(a.record)
    report(r)
    if a.out:
        json.dump(r, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
