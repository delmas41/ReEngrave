"""ROADMAP 2.311 -- THE FUNNEL AGAINST SEAN'S HAND-LABELLED PAGE (Brahms 317803 pdf 0).

    PYTHONPATH=. python3 benchmarks/note-loss-funnel-2026-11/funnel.py FACTS.json [--page 0] [--json OUT]

Truth: every notehead box in `data/hand-truth/pages/imslp317803/0.json` whose centre lies in a cell inspected for
noteheads (`hand_truth.score.cells_inspected_for`). Matched to the record BY PLACE: a record glyph box is a copy of a
truth head when the two boxes overlap (`judged.boxes_overlap`: IoU >= 0.3 or either centre inside the other, 4 px slack).

Each truth head ends in exactly ONE bucket, the furthest any of its copies got (a copy refused only because ANOTHER box
stands for the same ink -- a twin, a duplicate, the losing staff of a contest -- is set aside while any other copy
exists, so the loss is charged where the surviving copy died):

  A never boxed                     no record glyph box overlaps the head
  B boxed, not as a head            boxes overlap, none carries a notehead class (a rest box, a dynamic, ...)
  C refused as not a note           the exporter's `not_a_notehead:<reason>` / `ink_*` / `unread:*` (ADJUDICATE's refusal)
  D value not decided               `duration_narrowed` / `chord_value_undecided` / `written_value_fits_no_note`
  E given to another staff          `owned_by_another_staff` etc. with no other copy
  F dropped at EXPORT               `staff_not_identified` / `owner_staff_has_no_measures` / `cell_past_the_last_bar` / `no_pitch` ...
  G twin only                       every copy refused as a duplicate of another box
  W written                         plain / blue (GUESSED) / inside a red bar; and its head kind (black / half / whole)
                                    against Sean's class -- the only value his page labels state
The reason word is the exporter's own fate name for that copy (`_place_notes` fates), never ours.

Fakes on this page: written notes whose box centre lies in an inspected cell and overlaps no truth head; each is named by
the truth box it does overlap (Sean's label of that ink), or "nothing labelled".
"""
from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path

from tools.omr.hand_truth import score as S
from tools.omr.hand_truth import store
from tools.omr.staged.judged import boxes_overlap

TRUTH = Path("data/hand-truth/pages/imslp317803/0.json")
TWIN = {"owned_by_another_staff", "mark_group_duplicate", "relocation_collides",
        "not_a_notehead:notehead_is_a_duplicate_box", "not_a_notehead:stacked_head_duplicate",
        "not_a_notehead:is_a_rest_twin", "not_a_notehead:belongs_to_a_nearer_staff"}
VALUE = {"duration_narrowed", "chord_value_undecided", "written_value_fits_no_note"}
EXPORT = {"staff_not_identified", "owner_staff_has_no_measures", "cell_past_the_last_bar", "no_pitch", "owner_not_read",
          "bar_count_not_decided"}
RANK = {"W": 9, "F": 7, "D": 6, "C": 4, "E": 3, "G": 2, "B": 1, "A": 0}


def bucket_of_fate(fate: str) -> str:
    if fate in ("written", "written_relocated"):
        return "W"
    if fate in VALUE:
        return "D"
    if fate in EXPORT:
        return "F"
    if fate in ("owned_by_another_staff", "relocation_collides", "not_a_notehead:belongs_to_a_nearer_staff"):
        return "E"
    if fate in TWIN:
        return "G"
    return "C"


def kind_of_cls(cls: str) -> str:
    c = cls.lower()
    return "whole" if "whole" in c else ("half" if "half" in c else "black")


def kind_of_type(t: str) -> str:
    return {"whole": "whole", "half": "half", "breve": "whole"}.get(t, "black")


def red_places(f: dict) -> set:
    out = set()
    for b in f["bars"]["red_not_add_up"]:
        out.add((str(b["part"]), str(b["measure"])))
    return out


def run(facts: dict, page_no: int = 0) -> dict:
    page = store.load(TRUTH)
    items = S.truth_items(page)
    scope = S.Scope(S.cells_inspected_for(page, "notehead"))
    heads = [it for it in items if it.family == "notehead" and scope.holds(it.rect)]
    glyphs = {k: g for k, g in facts["glyphs"].items() if g["page"] == page_no}
    written = [h for h in facts["written"] if h["page"] == page_no and h["kind"] == "note"]
    red = red_places(facts)
    # one written note answers one truth head: best overlap first
    pairs = []
    for i, it in enumerate(heads):
        for j, h in enumerate(written):
            ok, iou = boxes_overlap(h["box"], it.rect)
            if ok:
                pairs.append((iou, i, j))
    took_t, took_w, w_of = set(), set(), {}
    for iou, i, j in sorted(pairs, reverse=True):
        if i in took_t or j in took_w:
            continue
        took_t.add(i)
        took_w.add(j)
        w_of[i] = j
    rows = []
    for i, it in enumerate(heads):
        copies = [(k, g) for k, g in glyphs.items() if boxes_overlap(g["box"], it.rect)[0]]
        row = dict(id=it.id, cls=it.cls, origin=it.origin, rect=it.rect, cell=it.cell_id,
                   copies=[(k, g["cls"], g["fate"]) for k, g in copies])
        if i in w_of:
            h = written[w_of[i]]
            row.update(bucket="W", reason=("blue" if h["blue"] else "plain"), rg=h["rg"], type=h["type"],
                       pitch=h["pitch"], in_red=(str(h["part"]), str(h["measure"])) in red,
                       kind_ok=kind_of_type(h["type"]) == kind_of_cls(it.cls))
        elif not copies:
            row.update(bucket="A", reason="no box")
        else:
            hc = [(k, g) for k, g in copies if g["head"]]
            if not hc:
                rc = [g for k, g in copies if g["rest"]]
                row.update(bucket="B", reason=("boxed as a rest:" + rc[0]["cls"]) if rc else
                           ("boxed as " + ",".join(sorted({str(g["cls"]) for k, g in copies}))))
            else:
                fated = [(k, g, g["fate"] or "no_fate") for k, g in hc]
                non_twin = [x for x in fated if x[2] not in TWIN]
                use = non_twin or fated
                k, g, fate = max(use, key=lambda x: RANK[bucket_of_fate(x[2])])
                b = bucket_of_fate(fate)
                if b == "W":
                    # a written copy that a neighbouring truth head took in the one-to-one pairing
                    b, fate = "M", "one box written for two printed heads"
                dv = (g.get("v") or {}).get("duration") or {}
                nv = (g.get("v") or {}).get("notehead_is_not_a_notehead") or {}
                row.update(bucket=b, reason=fate, rg=k, dur=(dv.get("outcome"), dv.get("reason")),
                           nn=(nv.get("outcome"), nv.get("reason")))
        rows.append(row)
    # fakes: written notes on this page, centred in an inspected cell, that answer no truth head
    tboxes = [it for it in items if scope.holds(it.rect)]
    fakes = []
    for j, h in enumerate(written):
        if j in took_w or not scope.holds(h["box"]):
            continue
        if any(boxes_overlap(h["box"], it.rect)[0] for it in heads):
            what = "a truth head already answered by another written note (double write)"
        else:
            over = sorted({it.cls for it in tboxes if boxes_overlap(h["box"], it.rect)[0]})
            what = ",".join(over) if over else "nothing labelled there"
        fakes.append(dict(rg=h["rg"], box=h["box"], type=h["type"], blue=h["blue"], what=what))
    return dict(rows=rows, fakes=fakes, n_written_on_page=len(written))


def render(res: dict) -> str:
    rows = res["rows"]
    n = len(rows)
    out = ["Brahms 317803 pdf 0: %d of Sean's noteheads (cells inspected for noteheads)" % n]
    names = dict(A="never boxed", B="boxed, not as a head", C="refused as not a note (ADJUDICATE)",
                 D="value not decided (ADJUDICATE narrowed, dropped at EXPORT)", E="given to another staff, no twin written",
                 F="dropped at EXPORT (staff / bar)", G="only twin copies, all refused", M="one box written for two printed heads",
                 W="written")
    bc = collections.Counter(r["bucket"] for r in rows)
    for b in "ABCDEGFMW":
        if bc[b]:
            out.append("  %-62s %4d  %5.1f%%" % (names[b], bc[b], 100.0 * bc[b] / n))
            rc = collections.Counter(r["reason"] for r in rows if r["bucket"] == b)
            for k, v in rc.most_common(8):
                out.append("      %-58s %4d" % (k, v))
    w = [r for r in rows if r["bucket"] == "W"]
    if w:
        out.append("  of the written: head kind against Sean's class right %d / wrong %d; inside a red bar %d; blue %d" % (
            sum(r["kind_ok"] for r in w), sum(not r["kind_ok"] for r in w), sum(r["in_red"] for r in w),
            sum(r["reason"] == "blue" for r in w)))
        wk = collections.Counter((r["cls"], r["type"]) for r in w if not r["kind_ok"])
        out.append("     wrong kind: %s" % dict(wk))
    out.append("  by origin (prefill-confirmed = the detector's own box, which it re-finds by construction): %s" % dict(
        collections.Counter((r["origin"], r["bucket"]) for r in rows)))
    f = res["fakes"]
    out.append("Written notes on the page: %d; answering no truth head (fakes by Sean's labels): %d" % (res["n_written_on_page"], len(f)))
    for k, v in collections.Counter(x["what"] for x in f).most_common(12):
        out.append("      %-58s %4d" % (k, v))
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("facts")
    ap.add_argument("--page", type=int, default=0)
    ap.add_argument("--json")
    a = ap.parse_args()
    res = run(json.load(open(a.facts)), a.page)
    print(render(res))
    if a.json:
        Path(a.json).write_text(json.dumps(res, default=str, indent=0))


if __name__ == "__main__":
    main()
