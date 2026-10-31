"""ROADMAP 2.240 step 2 -- ONE OWNER PER PAGE MARK, and arcs / hairpins read PAGE-WIDE (STAGED GATHER; decides nothing a reader uses yet).

    python3 -m tools.omr.staged.page_owner readout REC [REC ...] [--pages 0,4] [--out DIR] [--tiles DIR] [--cell-map DIR]
    python3 -m tools.omr.staged.page_owner controls REC --page N [--cell-map DIR]

WHY (benchmarks/page-ledger-2026-10/FINDINGS.md). Step 1 gave every detector box a PAGE-MARK id (boxes of one family from two padded cells
on the same page ink are one mark). But "whose mark is it?" is still asked per cell: a head in the gap is a copy on each staff, and ~10
later rules (`glyph_owner`'s `distance`, `owned_by_another_staff`, `belongs_to_a_nearer_staff`, the twin rules) pick the copy to keep. Here
the question is asked ONCE, of the mark, from what the page shows.

WHAT IT FILES (flag `OMR_PAGE_OWNER`, default OFF, allow-list; needs `OMR_PAGE_MARKS`):

* `Q.PAGE_MARK_OWNER`, one row per page mark, on its first member's glyph subject. `value` = the owner staff key; `detail` = `status`
  (`decided` | `guessed`), `reason`, `candidates` (both staves when guessed), `members`, `family`, `witnesses` (what each view said). A mark
  no witness names ABSTAINS with the reason (`owner_no_rungs`, `owner_no_witness`, `owner_follows_its_note`, `owner_inside_two_staves`).
* `Q.PAGE_SPAN`, one row per arc or hairpin READ PAGE-WIDE (Sean 2026-10-30, step-1 tiles: "the actual symbols reach past cell and should
  be read page wide"; page-facts §1). `value` = `arc` | `hairpin`; `detail` = the page-wide extent, the cells and staves it was seen from,
  its member boxes and page marks, the system-arc views it joins, and each view's end candidates (NOT bound: binding is ROADMAP 2.223).

THE OWNER RULE (Sean's rulings, in order; never nearness -- `distance` decides nothing here):
  1. `inside_staff`: the mark's centre stands on or between a staff's five lines, or in the space just outside them (within
     `INSIDE_SPACES` of the outer line, measured on the staff's own lines in the bar at the mark's x) -> that staff. Two such staves ->
     abstain `owner_inside_two_staves`.
  2. Heads only. `ledger`: the far-head note-first ledger reading (`Q.FAR_HEAD_OWNER_LEDGER`, GATHER) of every view of the mark. Two views
     of one ink are ONE witness (CLAUDE §4): they agree -> it names the owner; they name two staves -> GUESSED with both
     (`ledger_views_disagree`).
  3. Heads only. `stem` (`Q.HEAD_STEM_REACH`, GATHER): a head clearly outside the lines whose stem points at exactly one staff and reaches its
     band. Where the ledger named a staff and the stem names the other, the LEDGER decides, plain (`ledger_over_stem`; Sean 2026-10-28
     option B, DECISIONS: "the ledger lines decide ... plain, not blue", which reverses the 10-27 "GUESSED" for this case; his 2.216 tiles
     8/8). Where no ledger reading named a staff, the stem alone names it (`stem`; DECISIONS 2026-10-27 "one readable -> use it").
  4. Otherwise: a head with ledger readings that named no staff ABSTAINS `owner_no_rungs` (counted: our failure, page-facts §3); a head with
     no witness `owner_no_witness`; any other family outside every staff `owner_follows_its_note` (its owner is the note it binds to --
     a later page-wide step, ROADMAP 2.223 / step 3; never the nearer staff).

THE PAGE-WIDE SPAN RULE. Arcs: `gather_system_arcs` (2.166) already traces one curve per (system, staff) across barlines from each
slur/tie box; a curve in the gap is traced once from EACH staff's copy. Two traced views are ONE page-wide arc when their seed boxes are one
page mark, or their traces run the same page columns on overlapping rows for at least `SAME_TRACE_SHARE` of the shorter trace (same ink,
not a near box). An arc box no trace followed is a WITNESS only (abstain `span_untraced`), never a mark. Hairpins: each CV wedge
(`Q.WEDGE_BOX`, the page-wide reader 2.68) is one hairpin; two wedge reads whose boxes share `SAME_TRACE_SHARE` of the smaller box are one;
every page mark (of any family -- the detector boxes hairpins as beams and slurs, Sean's step-1 tile 10) whose box lies mostly inside the
wedge is recorded as a witness `boxed_as`. A detector hairpin box no wedge read holds is abstained `span_untraced`.

CONVENTION ASSUMED: the ledger lines name a far note's staff, its stem is a second witness (page-facts §3, ROADMAP 2.216); a head in the
space just outside a staff needs no ledger line; an arc is one thin curve and two traces of it from two crops cover the same page pixels.
WHAT WOULD FALSIFY IT: an owner Sean calls the other staff; a page-wide arc he calls two marks, or two he calls one (the tiles,
out/print/2.240-s2-tiles). NOT CONFIRMED beyond Litolff 984073 and Brahms 317803; `INSIDE_SPACES` and `SAME_TRACE_SHARE` are conventions
stated before any count, not cuts tuned here.
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import pathlib
import sys
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

DERIVED_CHECK = False

#: a mark whose centre is no more than this many of the staff's own spaces beyond its outer line stands IN that staff's band (on a line,
#: between lines, or in the space just outside: no ledger line can stand between it and the staff)
INSIDE_SPACES = 0.75
#: the stem speaks only for a head at least this far outside every candidate's lines (`ownership.STEM_MIN_OUTSIDE_SPACES`, the same word)
STEM_MIN_OUTSIDE_SPACES = 0.9
#: a stem tip "reaches" a staff within this many of its spaces of the near outer line (`ownership.STEM_REACH_BAND_SPACES`)
STEM_REACH_BAND_SPACES = 1.0
#: two traces / two wedge boxes are ONE mark when they cover the same page ink for this share of the smaller (the register's one cut)
SAME_TRACE_SHARE = 0.5
#: a page mark's box lies inside a wedge when this share of its box area is inside the wedge's box
BOXED_AS_SHARE = 0.5

FAMILY_HEAD = "head"
SPAN_FAMILIES = ("arc", "hairpin")


def enabled() -> bool:
    from .page_marks import owner_enabled
    return owner_enabled()


# ───────────────────────────── 1. rows: one interface over the log (GATHER) and a slice (readout) ─────────────────────────────

class LogRows:
    """`obs(q, key)` -> [(value, detail)], `abs(q, key)` -> [(reason, detail)] off the GATHER log."""

    def __init__(self, log: Any):
        self.log = log

    def obs(self, q: str, key: str) -> List[Tuple[Any, Dict[str, Any]]]:
        from . import record as R
        return [(r.value, dict(r.detail or {})) for r in self.log.rows(q, R.Subject.from_key(key))]

    def abs(self, q: str, key: str) -> List[Tuple[str, Dict[str, Any]]]:
        from . import record as R
        return [(r.reason, dict(r.detail or {})) for r in self.log.refusals(q, R.Subject.from_key(key))]


class SliceRows:
    """The same interface over a slice's rows (`claim_readout.read_rows`)."""

    QUANTITIES = ("far_head_owner_ledger", "head_stem_reach", "glyph_band_distance")

    def __init__(self, rows: Dict[str, List[dict]]):
        self._o: Dict[Tuple[str, str], list] = collections.defaultdict(list)
        self._a: Dict[Tuple[str, str], list] = collections.defaultdict(list)
        for o in rows.get("observations", ()):
            if o.get("quantity") in self.QUANTITIES:
                self._o[(o["quantity"], o["subject"])].append((o.get("value"), o.get("detail") or {}))
        for a in rows.get("abstentions", ()):
            if a.get("quantity") in self.QUANTITIES:
                self._a[(a["quantity"], a["subject"])].append((a.get("reason"), a.get("detail") or {}))

    def obs(self, q: str, key: str):
        return self._o.get((q, key), [])

    def abs(self, q: str, key: str):
        return self._a.get((q, key), [])


# ───────────────────────────── 2. the staff, measured locally ─────────────────────────────

@dataclass
class StaffBar:
    x0: float
    x1: float
    ys: Tuple[float, ...]          # the five lines, page px, in this bar
    sp: float


def staff_frames(cells: Sequence[Any], local: Dict[int, Tuple[int, int]]) -> Dict[str, List[StaffBar]]:
    """staff key -> its bars' own five lines in page px (`staff_line_ys_canonical` / `upscale_factor` + the cell's page origin)."""
    out: Dict[str, List[StaffBar]] = collections.defaultdict(list)
    for c in cells:
        key = local.get(c.staff_index)
        ys = list(getattr(c, "staff_line_ys_canonical", None) or [])
        bb = getattr(c, "bbox_page_px", None)
        up = getattr(c, "upscale_factor", None)
        if key is None or len(ys) < 5 or not bb or not up:
            continue
        py = tuple(float(bb[1]) + float(y) / float(up) for y in ys[:5])
        sp = (py[-1] - py[0]) / 4.0
        if sp <= 0:
            continue
        out["staff/%d/%d/%d" % (c.page_index, key[0], key[1])].append(StaffBar(float(bb[0]), float(bb[2]), py, sp))
    for v in out.values():
        v.sort(key=lambda b: b.x0)
    return dict(out)


def lines_at(frames: Dict[str, List[StaffBar]], staff_key: str, x: float) -> Optional[StaffBar]:
    """The staff's lines in the bar that holds x (the bar whose edge is closest when x falls on no bar of it: the system's margin)."""
    bars = frames.get(staff_key)
    if not bars:
        return None
    for b in bars:
        if b.x0 <= x <= b.x1:
            return b
    return min(bars, key=lambda b: min(abs(b.x0 - x), abs(b.x1 - x)))


def beyond_spaces(bar: StaffBar, y: float) -> float:
    """How many of the staff's own spaces y stands outside its outer lines (0 inside)."""
    return max(bar.ys[0] - y, y - bar.ys[-1], 0.0) / bar.sp


def bracketing(frames: Dict[str, List[StaffBar]], system: str, x: float, y: float) -> List[str]:
    """The staves of `system` (prefix `staff/p/s/`) just above and just below y at x, by ORDER (which staff is above, which below), never by
    how near: a mark between two staves has exactly these two candidates; above the top staff or below the bottom one, one."""
    st = []
    for k in frames:
        if k.startswith(system):
            b = lines_at(frames, k, x)
            if b is not None:
                st.append(((b.ys[0] + b.ys[-1]) / 2.0, k, b))
    st.sort()
    above = [k for mid, k, b in st if b.ys[-1] < y]
    below = [k for mid, k, b in st if b.ys[0] > y]
    return ([above[-1]] if above else []) + ([below[0]] if below else [])


# ───────────────────────────── 3. the owner of one mark ─────────────────────────────

def _staff_of_glyph(key: str) -> str:
    p = key.split("/")
    return "staff/%s/%s/%s" % (p[1], p[2], p[3])


def ledger_reading(rows: Any, member: str) -> Optional[str]:
    """One view's note-first ledger reading: the ONE fitting staff, or a word (`unread`, `both_fit`, `none_fit`), or None (not read)."""
    fits = sorted({(d or {}).get("candidate") for _v, d in rows.obs("far_head_owner_ledger", member)} - {None})
    refs = rows.abs("far_head_owner_ledger", member)
    if not fits and not refs:
        return None
    if any((d or {}).get("unread") for _r, d in refs):
        return "unread"
    if len(fits) == 1:
        return fits[0]
    return "both_fit" if fits else "none_fit"


def stem_reading(rows: Any, member: str, frames: Dict[str, List[StaffBar]], cands: Sequence[str]) -> Optional[str]:
    """One view's stem witness (`ownership._stem_owner` on GATHER's `Q.HEAD_STEM_REACH`): the ONE candidate its stem points at and reaches,
    or None (silent: no stem read, both ways, a head on or beside a staff's lines, toward neither or both)."""
    got = rows.obs("head_stem_reach", member)
    if not got:
        return None
    way, det = got[-1]
    if way not in ("up", "down"):
        return None
    tip = det.get("%s_tip_y" % way)
    box = det.get("head_box_page")
    if tip is None or not box or len(box) != 4:
        return None
    cx, cy = (float(box[0]) + float(box[2])) / 2.0, (float(box[1]) + float(box[3])) / 2.0
    sign = 1.0 if way == "down" else -1.0
    pointed = []
    for k in cands:
        b = lines_at(frames, k, cx)
        if b is None:
            continue
        if beyond_spaces(b, cy) < STEM_MIN_OUTSIDE_SPACES:
            return None
        near = b.ys[0] if sign > 0 else b.ys[-1]
        on_side = (near - cy) * sign >= 0.0
        reach = float(tip) * sign >= (near - sign * STEM_REACH_BAND_SPACES * b.sp) * sign
        if on_side and reach:
            pointed.append(k)
    return pointed[0] if len(pointed) == 1 else None


def mark_owner(family: Optional[str], members: Sequence[str], box: Sequence[float], frames: Dict[str, List[StaffBar]],
               rows: Any) -> Dict[str, Any]:
    """The owner of ONE page mark (module doc). Returns {status: decided|guessed|abstain, owner, candidates, reason, witnesses, seen_from}."""
    cx, cy = (float(box[0]) + float(box[2])) / 2.0, (float(box[1]) + float(box[3])) / 2.0
    seen_from = sorted({_staff_of_glyph(m) for m in members})
    system = "/".join(seen_from[0].split("/")[:3]) + "/"
    wit: Dict[str, Any] = {"seen_from": seen_from}
    inside = []
    for k in frames:
        if k.startswith(system):
            b = lines_at(frames, k, cx)
            if b is not None and beyond_spaces(b, cy) <= INSIDE_SPACES:
                inside.append(k)
    wit["inside"] = inside

    def out(status, owner, reason, cands=None):
        return {"status": status, "owner": owner, "reason": reason, "candidates": cands or ([owner] if owner else []),
                "witnesses": wit, "seen_from": seen_from}

    if len(inside) == 1:
        return out("decided", inside[0], "inside_staff")
    if len(inside) > 1:
        return out("abstain", None, "owner_inside_two_staves", inside)
    cands = sorted(set(bracketing(frames, system, cx, cy)) | set(seen_from))
    wit["candidates"] = cands
    if family != FAMILY_HEAD:
        return out("abstain", None, "owner_follows_its_note", cands)
    led = {m: ledger_reading(rows, m) for m in members}
    stem = {m: stem_reading(rows, m, frames, cands) for m in members}
    wit["ledger"] = {m: v for m, v in led.items() if v is not None}
    wit["stem"] = {m: v for m, v in stem.items() if v is not None}
    named = sorted({v for v in led.values() if v and v.startswith("staff/")})
    stems = sorted({v for v in stem.values() if v})
    if len(named) > 1:
        return out("guessed", named[0] if not stems or stems[0] not in named else stems[0], "ledger_views_disagree", named)
    if len(named) == 1:
        if stems and len(stems) == 1 and stems[0] != named[0]:
            wit["stem_owner"] = stems[0]
            return out("decided", named[0], "ledger_over_stem", [named[0], stems[0]])
        return out("decided", named[0], "ledger_and_stem" if stems == named else "ledger")
    if len(stems) == 1:
        return out("decided", stems[0], "stem")
    if any(v is not None for v in led.values()):
        return out("abstain", None, "owner_no_rungs", cands)
    return out("abstain", None, "owner_no_witness", cands)


def union_box(boxes: Iterable[Sequence[float]]) -> List[float]:
    bs = list(boxes)
    return [min(b[0] for b in bs), min(b[1] for b in bs), max(b[2] for b in bs), max(b[3] for b in bs)]


def owners(marks: Any, boxes: Sequence[Any], frames: Dict[str, List[StaffBar]], rows: Any) -> Dict[int, Dict[str, Any]]:
    """Every page mark's owner (`page_marks.Marks` + its `BoxInk`s). A mark of no family (not a mark) is skipped."""
    box_of = {b.key: b for b in boxes}
    out = {}
    for n, mem in marks.members.items():
        bs = [box_of[k] for k in mem if k in box_of]
        if not bs or bs[0].family is None:
            continue
        r = mark_owner(bs[0].family, mem, union_box(b.page_box for b in bs), frames, rows)
        r["family"] = bs[0].family
        r["members"] = list(mem)
        r["box"] = union_box(b.page_box for b in bs)
        out[n] = r
    return out


# ───────────────────────────── 4. arcs and hairpins, page-wide ─────────────────────────────

def _trace_cols(tr: Sequence[Sequence[float]]) -> Dict[int, Tuple[float, float]]:
    return {int(t[0]): (float(t[1]), float(t[2])) for t in tr or () if len(t) >= 3}


def trace_share(a: Dict[int, Tuple[float, float]], b: Dict[int, Tuple[float, float]]) -> float:
    """Of the shorter trace's columns, the share the other runs on overlapping rows (same ink)."""
    if not a or not b:
        return 0.0
    n = sum(1 for x, (y0, y1) in a.items() if x in b and min(y1, b[x][1]) >= max(y0, b[x][0]))
    return n / float(min(len(a), len(b)))


def _rect_share_of(a: Sequence[float], b: Sequence[float]) -> float:
    """Share of a's area inside b."""
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    area = max(1e-9, (a[2] - a[0]) * (a[3] - a[1]))
    return ix * iy / area


def arc_spans(system_arcs: Sequence[Dict[str, Any]], mark_of: Dict[str, int], untraced: Sequence[Tuple[int, List[str], List[float]]]
              ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """(page-wide arcs, untraced arc marks). `system_arcs`: [{key, staff, pieces, trace, cells, anchors, x0, x1, cut_at_barline}]."""
    n = len(system_arcs)
    parent = list(range(n))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    cols = [_trace_cols(a.get("trace")) for a in system_arcs]
    marks = [{mark_of[p] for p in a.get("pieces", ()) if p in mark_of} for a in system_arcs]
    why: Dict[Tuple[int, int], str] = {}
    order = sorted(range(n), key=lambda i: system_arcs[i]["x0"])
    for ai, i in enumerate(order):
        for j in order[ai + 1:]:
            if system_arcs[j]["x0"] > system_arcs[i]["x1"]:
                break
            if system_arcs[i]["system"] != system_arcs[j]["system"]:
                continue
            if marks[i] & marks[j]:
                why[(i, j)] = "one_page_mark"
            elif trace_share(cols[i], cols[j]) >= SAME_TRACE_SHARE:
                why[(i, j)] = "same_trace"
            else:
                continue
            parent[find(j)] = find(i)
    groups: Dict[int, List[int]] = collections.defaultdict(list)
    for i in range(n):
        groups[find(i)].append(i)
    spans = []
    for g in sorted(groups.values(), key=lambda g: min(system_arcs[i]["x0"] for i in g)):
        views = [system_arcs[i] for i in g]
        pieces = sorted({p for v in views for p in v.get("pieces", ())})
        ys = [y for i in g for (y0, y1) in cols[i].values() for y in (y0, y1)]
        spans.append({
            "kind": "arc", "subject": min(v["key"] for v in views), "views": [v["key"] for v in views],
            "staves_seen_from": sorted({v["staff"] for v in views}), "pieces": pieces,
            "page_marks": sorted({m for i in g for m in marks[i]}),
            "x0": min(v["x0"] for v in views), "x1": max(v["x1"] for v in views),
            "box": [min(v["x0"] for v in views), min(ys), max(v["x1"] for v in views), max(ys)],
            "cells": sorted({(v["staff"], c) for v in views for c in v.get("cells", ())}),
            "crosses_barline": any(v.get("cut_at_barline") for v in views) or len({c for v in views for c in v.get("cells", ())}) > 1,
            "joined_by": sorted({why[(a, b)] for (a, b) in why if a in g and b in g}),
            "end_candidates": [v.get("anchors") for v in views],
        })
    traced_marks = {m for s in spans for m in s["page_marks"]}
    left = [{"kind": "arc", "page_mark": m, "members": mem, "box": box} for m, mem, box in untraced if m not in traced_marks]
    return spans, left


def hairpin_spans(wedges: Sequence[Dict[str, Any]], mark_boxes: Sequence[Tuple[int, str, List[float], List[str]]]
                  ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """(page-wide hairpins, detector hairpin marks no wedge read holds). `wedges`: [{key, staff, kind, box}] off `Q.WEDGE_BOX` (CV, page-wide);
    `mark_boxes`: [(page mark, family, union box, members)] of every page mark on the page."""
    n = len(wedges)
    parent = list(range(n))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i in range(n):
        for j in range(i + 1, n):
            a, b = wedges[i]["box"], wedges[j]["box"]
            small, big = (a, b) if (a[2] - a[0]) * (a[3] - a[1]) <= (b[2] - b[0]) * (b[3] - b[1]) else (b, a)
            if _rect_share_of(small, big) >= SAME_TRACE_SHARE:
                parent[find(j)] = find(i)
    groups: Dict[int, List[int]] = collections.defaultdict(list)
    for i in range(n):
        groups[find(i)].append(i)
    spans, held = [], set()
    for g in groups.values():
        views = [wedges[i] for i in g]
        box = union_box(v["box"] for v in views)
        boxed_as = []
        for m, fam, mb, mem in mark_boxes:
            if _rect_share_of(mb, box) >= BOXED_AS_SHARE:
                boxed_as.append([m, fam])
                held.add(m)
        spans.append({"kind": "hairpin", "subject": min(v["key"] for v in views), "views": [v["key"] for v in views],
                      "wedge": sorted({v["kind"] for v in views}), "staves_seen_from": sorted({v["staff"] for v in views}),
                      "x0": box[0], "x1": box[2], "box": box, "boxed_as": boxed_as})
    left = [{"kind": "hairpin", "page_mark": m, "members": mem, "box": mb} for m, fam, mb, mem in mark_boxes
            if fam == "hairpin" and m not in held]
    return spans, left


def system_arcs_of(obs: Iterable[Tuple[str, Any, Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """`Q.SYSTEM_ARC` observations (subject, value, detail) -> the span input."""
    out = []
    for subj, _v, d in obs:
        p = subj.split("/")
        tr = d.get("trace") or []
        if not tr:
            continue
        out.append({"key": subj, "staff": "staff/%s/%s/%s" % (p[1], p[2], p[3]), "system": "%s/%s" % (p[1], p[2]),
                    "pieces": list(d.get("pieces") or [subj]), "trace": tr, "cells": list(d.get("cells") or []),
                    "anchors": [d.get("anchor_left"), d.get("anchor_right")], "x0": float(d.get("x_left_page", tr[0][0])),
                    "x1": float(d.get("x_right_page", tr[-1][0])), "cut_at_barline": bool(d.get("cut_at_barline"))})
    return out


def wedges_of(obs: Iterable[Tuple[str, Any, Dict[str, Any]]]) -> List[Dict[str, Any]]:
    out = []
    for subj, v, d in obs:
        bb = d.get("bbox_page_px")
        if not bb:
            continue
        p = subj.split("/")
        out.append({"key": subj, "staff": "staff/%s/%s/%s" % (p[1], p[2], p[3]), "kind": v, "box": [float(t) for t in bb]})
    return out


def page_spans(marks: Any, boxes: Sequence[Any], sys_arc_obs, wedge_obs) -> Dict[str, Any]:
    """Both kinds on one page: {"spans": [...], "untraced": [...]}."""
    box_of = {b.key: b for b in boxes}
    mark_boxes, untraced_arcs = [], []
    for n, mem in marks.members.items():
        bs = [box_of[k] for k in mem if k in box_of]
        if not bs or bs[0].family is None:
            continue
        ub = union_box(b.page_box for b in bs)
        mark_boxes.append((n, bs[0].family, ub, list(mem)))
        if bs[0].family == "arc":
            untraced_arcs.append((n, list(mem), ub))
    arcs, left_a = arc_spans(system_arcs_of(sys_arc_obs), marks.mark_of, untraced_arcs)
    pins, left_h = hairpin_spans(wedges_of(wedge_obs), mark_boxes)
    return {"spans": arcs + pins, "untraced": left_a + left_h}


# ───────────────────────────── 5. the GATHER step ─────────────────────────────

def gather_page_owners(log: Any, pws: Any, cells: Sequence[Any], local: Dict[int, Tuple[int, int]], marks: Any, *,
                       progress: bool = False) -> Optional[Dict[str, Any]]:
    """ROADMAP 2.240 step 2 (flag `OMR_PAGE_OWNER`, default OFF): `Q.PAGE_MARK_OWNER` per page mark and `Q.PAGE_SPAN` per page-wide arc /
    hairpin (module doc). After the far-head ledger readings and the stem reach (it reads them) and the CV wedges; files rows only."""
    if not enabled() or marks is None or not getattr(marks, "boxes", None):
        return None
    from . import record as R
    from .gather import FRAME_PAGE
    from .record import Q, READERS, Scope
    frames = staff_frames(cells, local)
    rows = LogRows(log)
    own = owners(marks, marks.boxes, frames, rows)
    for n, r in own.items():
        subj = R.Subject.from_key(r["members"][0])
        common = dict(reader=READERS.CV_PAGE_OWNER, frame=FRAME_PAGE)
        if r["status"] == "abstain":
            log.abstain(subj, Q.PAGE_MARK_OWNER, reason=r["reason"], page_mark=n, family=r["family"], members=r["members"],
                        candidates=r["candidates"], witnesses=r["witnesses"], **common)
        else:
            log.observe(subj, Q.PAGE_MARK_OWNER, r["owner"], status=r["status"], reason=r["reason"], page_mark=n, family=r["family"],
                        members=r["members"], candidates=r["candidates"], witnesses=r["witnesses"], **common)
    page = marks.boxes[0].cell[0]
    pg = R.page(page)
    sa = [(o.subject.to_key(), o.value, dict(o.detail or {})) for o in log.rows(Q.SYSTEM_ARC, pg, scope=Scope.SELF_AND_DESCENDANTS)]
    wd = [(o.subject.to_key(), o.value, dict(o.detail or {})) for o in log.rows(Q.WEDGE_BOX, pg, scope=Scope.SELF_AND_DESCENDANTS)]
    sp = page_spans(marks, marks.boxes, sa, wd)
    for s in sp["spans"]:
        d = {k: v for k, v in s.items() if k not in ("kind", "subject")}
        d["cells"] = [list(c) for c in d.get("cells", [])]
        log.observe(R.Subject.from_key(s["subject"]), Q.PAGE_SPAN, s["kind"], reader=READERS.CV_PAGE_SPANS, frame=FRAME_PAGE, **d)
    for u in sp["untraced"]:
        log.abstain(R.Subject.from_key(u["members"][0]), Q.PAGE_SPAN, reader=READERS.CV_PAGE_SPANS, frame=FRAME_PAGE,
                    reason="span_untraced", kind=u["kind"], page_mark=u["page_mark"], members=u["members"], box=u["box"])
    if progress:
        st = collections.Counter(r["status"] for r in own.values())
        print("  gather page owners p%s: %s; spans %d, untraced %d" % (page, dict(st), len(sp["spans"]), len(sp["untraced"])))
    return {"owners": own, **sp}


# ───────────────────────────── 6. the readout (from a slice) ─────────────────────────────

def _rows_of(prows: Dict[str, List[dict]], q: str) -> List[Tuple[str, Any, Dict[str, Any]]]:
    return [(o["subject"], o.get("value"), o.get("detail") or {}) for o in prows["observations"] if o.get("quantity") == q]


OLD_RULES = {
    # (quantity, reason) of the old rules that pick between two cells' copies; "keeps" = the verdict names the keeper staff (value),
    # "drops" = the verdict refuses THIS copy (so it says: not this cell's staff)
    ("glyph_owner", None): "keeps",
    ("duration", "owned_by_another_staff"): "drops",
    ("notehead_is_not_a_notehead", "belongs_to_a_nearer_staff"): "drops",
    ("notehead_is_not_a_notehead", "notehead_is_a_duplicate_box"): "drops",
    ("accidental_owner", "owned_by_another_staff"): "drops",
    ("accidental_owner", "head_belongs_to_a_nearer_staff"): "drops",
    ("articulation_owner", "owned_by_another_staff"): "drops",
    ("dot_role", "owned_by_another_staff"): "drops",
}
_OLD_Q = sorted({q for q, _r in OLD_RULES})


def old_verdicts(src: pathlib.Path, pages: Sequence[int]) -> Dict[str, List[Tuple[str, str, Any, str]]]:
    """glyph key -> [(quantity, outcome, value, reason)] of the old cell-copy rules, streamed off the slice's verdicts (filtered by text)."""
    out: Dict[str, List[Tuple[str, str, Any, str]]] = collections.defaultdict(list)
    vf = src / "verdicts.jsonl"
    if not vf.exists():
        return out
    keys = tuple('"quantity": "%s"' % q for q in _OLD_Q)
    pset = set(pages)
    with open(vf) as fh:
        for line in fh:
            head = line[:400]
            if not any(k in head for k in keys):
                continue
            v = json.loads(line)
            s = v.get("subject", "")
            if not s.startswith("glyph/"):
                continue
            if int(s.split("/")[1]) not in pset:
                continue
            q, r = v.get("quantity"), v.get("reason")
            if (q, None) in OLD_RULES or (q, r) in OLD_RULES:
                out[s].append((q, v.get("outcome"), v.get("value"), r))
    return out


def compare_old(own: Dict[int, Dict[str, Any]], old: Dict[str, List[Tuple[str, str, Any, str]]]) -> Dict[str, Dict[str, int]]:
    """Per old rule (quantity:reason), BY PLACE (the page mark's members): `agrees` / `disagrees` with the page owner, or `owner_silent`
    (the page owner abstained) -- step 3 retires a rule only where it agrees, on tiles."""
    res: Dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    for n, r in own.items():
        for m in r["members"]:
            for q, outcome, value, reason in old.get(m, ()):
                kind = OLD_RULES.get((q, None)) if (q, None) in OLD_RULES else OLD_RULES.get((q, reason))
                if kind == "keeps" and outcome != "decided":
                    continue
                if kind == "keeps" and reason == "no_contest" and len(r["seen_from"]) == 1 and r["status"] == "decided" \
                        and r["owner"] == r["seen_from"][0]:
                    label = "glyph_owner:no_contest"
                else:
                    label = "%s:%s" % (q, reason)
                if r["status"] == "abstain":
                    res[label]["owner_silent"] += 1
                    continue
                staff = _staff_of_glyph(m)
                if kind == "keeps":
                    ok = value == r["owner"]
                else:
                    ok = staff != r["owner"]
                res[label]["agrees" if ok else "disagrees"] += 1
                if r["status"] == "guessed":
                    res[label]["of_them_owner_guessed"] += 1
    return {k: dict(v) for k, v in sorted(res.items())}


def page_readout(own: Dict[int, Dict[str, Any]], sp: Dict[str, Any]) -> Dict[str, Any]:
    by = collections.Counter()
    two = collections.Counter()
    for r in own.values():
        by["%s:%s:%s" % (r["family"], r["status"], r["reason"])] += 1
        if len(r["seen_from"]) > 1:
            two["%s:%s" % (r["status"], r["reason"])] += 1
    spans = sp["spans"]
    arcs = [s for s in spans if s["kind"] == "arc"]
    return {"marks": len(own), "owner_by_family_status_reason": dict(sorted(by.items())),
            "marks_seen_from_two_staves_by_status_reason": dict(sorted(two.items())),
            "arc_spans": len(arcs), "arc_spans_joining_two_staves_views": sum(1 for s in arcs if len(s["staves_seen_from"]) > 1),
            "arc_views": sum(len(s["views"]) for s in arcs), "arc_spans_crossing_a_barline": sum(1 for s in arcs if s["crosses_barline"]),
            "hairpin_spans": sum(1 for s in spans if s["kind"] == "hairpin"),
            "hairpin_spans_boxed_as": dict(collections.Counter(f for s in spans if s["kind"] == "hairpin" for _m, f in s["boxed_as"])),
            "untraced": dict(collections.Counter(u["kind"] for u in sp["untraced"]))}


def run(rec: str, pages: Optional[Sequence[int]] = None, out: Optional[pathlib.Path] = None, cm_root: Optional[pathlib.Path] = None,
        log=print, tile_pool: Optional[List[Dict[str, Any]]] = None, with_old: bool = True) -> Dict[str, Any]:
    from . import cell_map as CM
    from . import claim_readout as CR
    from . import page_marks as PM
    src = CR.resolve_source(rec)
    pages = list(pages) if pages else CR.slice_pages(src)
    rows_all = CR.read_rows(src, pages)
    pdf = CR.LIB / CR.edition_info(rows_all)["edition_path"]
    cm_root = cm_root or CM.ROOT_DEFAULT
    man = CM.info(pdf, root=cm_root)
    old = old_verdicts(src, pages) if with_old else {}
    per, cmp_all = {}, []
    for pg in pages:
        prows = {k: [r for r in v if CR.page_of_subject(r.get("subject", "")) in (None, pg)] for k, v in rows_all.items()}
        pws, cells, local, views, verify = PM.page_views(prows, pdf, pg, cm_root)
        ink = pws.page.binary == 0
        boxes = PM.boxes_from_rows(prows, pg, cells, local, views, ink)
        marks = PM.link(boxes, pieces=True)
        frames = staff_frames(cells, local)
        own = owners(marks, boxes, frames, SliceRows(prows))
        sp = page_spans(marks, boxes, _rows_of(prows, "system_arc"), _rows_of(prows, "wedge_box"))
        rep = page_readout(own, sp)
        rep["verify"] = dict(verify)
        c = compare_old(own, old)
        rep["old_rules"] = c
        cmp_all.append(c)
        per[str(pg)] = rep
        if tile_pool is not None:
            tile_pool += tile_candidates(own, sp, pg, str(pdf), str(cm_root), frames)
        log("  page %d: %d marks; two-staff marks %s; arc spans %d (%d join two staves' views); hairpins %d" % (
            pg, rep["marks"], rep["marks_seen_from_two_staves_by_status_reason"], rep["arc_spans"], rep["arc_spans_joining_two_staves_views"],
            rep["hairpin_spans"]))
        del pws, cells, views, ink
    from .page_marks import _sum
    total = _sum([{k: v for k, v in r.items() if k != "verify"} for r in per.values()])
    report = {"record": str(src), "pages": pages, "master": man["version"], "total": total, "per_page": per}
    if out is not None:
        out.mkdir(parents=True, exist_ok=True)
        (out / "page_owner.json").write_text(json.dumps(report, indent=1, sort_keys=True, default=str))
    log("page_owner readout %s pages %s master %s" % (os.path.basename(str(src)), pages, man["version"]))
    log("  marks seen from two staves: %s" % total.get("marks_seen_from_two_staves_by_status_reason"))
    log("  arc spans %s (two-staff joins %s, crossing a barline %s, from %s views); hairpins %s boxed as %s; untraced %s" % (
        total.get("arc_spans"), total.get("arc_spans_joining_two_staves_views"), total.get("arc_spans_crossing_a_barline"),
        total.get("arc_views"), total.get("hairpin_spans"), total.get("hairpin_spans_boxed_as"), total.get("untraced")))
    log("  old cell-copy rules vs the page owner (by place): %s" % total.get("old_rules"))
    return report


# ───────────────────────────── 7. tiles: "which staff's note is this?" / "is this one mark?" ─────────────────────────────

def tile_candidates(own, sp, page, pdf, cm_root, frames) -> List[Dict[str, Any]]:
    out = []
    for n, r in own.items():
        if r["family"] != FAMILY_HEAD or r["status"] == "abstain" or r["reason"] == "inside_staff":
            continue
        out.append({"kind": "owner", "page": page, "pdf": pdf, "cm_root": cm_root, "box": r["box"], "status": r["status"],
                    "reason": r["reason"], "owner": r["owner"], "candidates": r["candidates"], "members": r["members"],
                    "staves": sorted(set(r["candidates"]) | set(r["seen_from"]))})
    for s in sp["spans"]:
        if s["kind"] == "arc" and not (len(s["views"]) > 1 or s["crosses_barline"]):
            continue
        out.append({"kind": s["kind"], "page": page, "pdf": pdf, "cm_root": cm_root, "span": {k: v for k, v in s.items()
                    if k in ("views", "staves_seen_from", "pieces", "x0", "x1", "box", "joined_by", "boxed_as", "wedge", "crosses_barline")},
                    "staves": s["staves_seen_from"]})
    return out


def pick_tiles(pool: List[Dict[str, Any]], n: int = 12, seed: int = 22402) -> List[Dict[str, Any]]:
    """7 owner tiles (every GUESSED and `ledger_over_stem` first, then stem / ledger decisions) + 5 page-wide spans (a hairpin, two-staff
    joins, barline crossings), plates alternated, seeded."""
    import random
    rnd = random.Random(seed)
    own = [t for t in pool if t["kind"] == "owner"]
    spans = [t for t in pool if t["kind"] != "owner"]
    rnd.shuffle(own)
    rnd.shuffle(spans)
    rank = {"ledger_views_disagree": 0, "ledger_over_stem": 1, "stem": 2, "ledger": 3, "ledger_and_stem": 4}
    own.sort(key=lambda t: rank.get(t["reason"], 9))
    chosen: List[Dict[str, Any]] = []

    def take(cands, k, key):
        got, per = [], collections.Counter()
        for t in cands:
            if len(got) >= k:
                break
            if per[(t["pdf"], key(t))] >= max(1, (k + 3) // 4):
                continue
            if any(c["page"] == t["page"] and c["pdf"] == t["pdf"] and abs(_tbox(c)[0] - _tbox(t)[0]) < 80 for c in chosen + got):
                continue
            got.append(t)
            per[(t["pdf"], key(t))] += 1
        return got

    chosen += take(own, 7, lambda t: t["reason"])
    hp = [t for t in spans if t["kind"] == "hairpin"]
    two = [t for t in spans if t["kind"] == "arc" and len(t["span"]["views"]) > 1]
    one = [t for t in spans if t["kind"] == "arc" and len(t["span"]["views"]) == 1]
    chosen += take(hp, 1, lambda t: "h")
    chosen += take(two, 2, lambda t: "two")
    chosen += take(one + two, n - len(chosen), lambda t: "bar")
    rnd.shuffle(chosen)
    return chosen[:n]


def _tbox(t: Dict[str, Any]) -> List[float]:
    return t["box"] if t["kind"] == "owner" else t["span"]["box"]


def cut_tiles(pool: List[Dict[str, Any]], out_dir: pathlib.Path, n: int = 12) -> None:
    """One staff a tile: the staff the record names (an owner tile: the owner staff; a span: the first staff it was seen from), ONE thin
    orange box sized to the mark, nothing else drawn; key.json BESIDE the tile folder."""
    from PIL import Image, ImageDraw
    from . import cell_map as CM
    from .gather import _system_local
    chosen = pick_tiles(pool, n)
    tdir = out_dir / "tiles"
    tdir.mkdir(parents=True, exist_ok=True)
    for f in tdir.glob("*"):
        f.unlink()
    imgs: Dict[Tuple[str, int], Any] = {}
    key = []
    for i, it in enumerate(chosen, 1):
        ik = (it["pdf"], it["page"])
        if ik not in imgs:
            (pws, cells), = CM.load_prepared(pathlib.Path(it["pdf"]), [it["page"]], root=pathlib.Path(it["cm_root"]))
            imgs[ik] = (Image.fromarray(pws.page.rgb).convert("RGB"), staff_frames(cells, _system_local(pws.staves)))
        im, frames = imgs[ik]
        bb = _tbox(it)
        bb = [bb[0] - 2, bb[1] - 2, bb[2] + 2, bb[3] + 2]
        staff = it["owner"] if it["kind"] == "owner" else it["staves"][0]
        bar = lines_at(frames, staff, (bb[0] + bb[2]) / 2.0)
        u = bar.sp if bar else 20.0
        top, bot = (bar.ys[0], bar.ys[-1]) if bar else (bb[1], bb[3])
        cx = (bb[0] + bb[2]) / 2.0
        x0, x1 = max(0, int(min(cx - 6 * u, bb[0] - 1.5 * u))), int(max(cx + 6 * u, bb[2] + 1.5 * u))
        y0, y1 = max(0, int(min(top - 1.5 * u, bb[1] - 1.0 * u))), int(max(bot + 1.5 * u, bb[3] + 1.0 * u))
        crop = im.crop((x0, y0, x1, y1)).copy()
        ImageDraw.Draw(crop).rectangle([round(bb[0] - x0), round(bb[1] - y0), round(bb[2] - x0), round(bb[3] - y0)],
                                       outline=(255, 140, 0), width=max(2, int(u / 10)))
        W = 560
        crop = crop.resize((W, max(1, int(W * crop.height / crop.width))))
        crop.save(tdir / ("tile_%02d.png" % i))
        key.append({**{k: v for k, v in it.items() if k != "cm_root"}, "tile": i, "tile_staff": staff, "crop_origin": [x0, y0]})
    (tdir / "README.md").write_text(
        "# Two plain questions\n\nEach picture is a piece of a score page with ONE orange box on it and nothing else drawn. The box only "
        "says where to look.\n\n**For every tile:** what is the ink in the box (a note, an arc, a hairpin ...), and is it ONE mark or more?"
        "\n\n**If it is a note:** does it belong to the full five-line staff in the picture, or to another staff (the one above or below, "
        "partly shown or not shown)?\n\nAnswer by tile number.\n")
    (out_dir / "key.json").write_text(json.dumps(key, indent=1, default=str))


# ───────────────────────────── 8. controls that can fail ─────────────────────────────

class _NoRows:
    def obs(self, q, key):
        return []

    def abs(self, q, key):
        return []


class _Flip:
    """A row source with ONE view's ledger reading turned to another staff (control (b))."""

    def __init__(self, base: Any, member: str, to: str):
        self.base, self.member, self.to = base, member, to

    def obs(self, q, key):
        if q == "far_head_owner_ledger" and key == self.member:
            return [(0, {"candidate": self.to})]
        return self.base.obs(q, key)

    def abs(self, q, key):
        if q == "far_head_owner_ledger" and key == self.member:
            return []
        return self.base.abs(q, key)


def controls(rec: str, page: int, cm_root: Optional[pathlib.Path] = None, log=print) -> int:
    """(a) NEVER NEARNESS: with every ledger and stem row removed, no head outside every staff's band may get an owner (a nearness rule
    hiding anywhere would still decide them) -- and the broken arm (nearest staff by centre) does decide them, so the control can fail;
    (b) a two-staff head mark the ledger decided, with ONE view's reading turned to the other staff, becomes GUESSED with both staves;
    (c) a two-view arc span: one view's trace moved one staff space down no longer joins (two arcs); unmoved, with no shared page mark, joins."""
    from . import cell_map as CM
    from . import claim_readout as CR
    from . import page_marks as PM
    src = CR.resolve_source(rec)
    rows = CR.read_rows(src, [page])
    pdf = CR.LIB / CR.edition_info(rows)["edition_path"]
    cm_root = cm_root or CM.ROOT_DEFAULT
    pws, cells, local, views, verify = PM.page_views(rows, pdf, page, cm_root)
    boxes = PM.boxes_from_rows(rows, page, cells, local, views, pws.page.binary == 0)
    marks = PM.link(boxes, pieces=True)
    frames = staff_frames(cells, local)
    sr = SliceRows(rows)
    fails = 0
    full = owners(marks, boxes, frames, sr)
    bare = owners(marks, boxes, frames, _NoRows())
    gap = [n for n, r in full.items() if r["family"] == FAMILY_HEAD and not r["witnesses"]["inside"]]
    leaked = [n for n in gap if bare[n]["status"] != "abstain"]
    broken = 0
    for n in gap:
        r = full[n]
        cx, cy = (r["box"][0] + r["box"][2]) / 2.0, (r["box"][1] + r["box"][3]) / 2.0
        near = [k for k in r["witnesses"].get("candidates", []) if lines_at(frames, k, cx) is not None]
        broken += int(bool(near))
    ok = bool(gap) and not leaked and broken == len(gap)
    log("  (a) never nearness: %d heads outside every band; with no ledger/stem rows %d get an owner (must be 0); the nearest-staff arm "
        "would decide %d of them -- %s" % (len(gap), len(leaked), broken, "pass" if ok else ("NOT RUN (no gap head)" if not gap else "FAIL")))
    fails += 0 if ok else 1
    two = [(n, r) for n, r in full.items() if r["family"] == FAMILY_HEAD and len(r["seen_from"]) > 1 and r["reason"].startswith("ledger")
           and sum(1 for v in r["witnesses"]["ledger"].values() if v == r["owner"]) >= 2]
    if not two:
        log("  (b) no two-staff head decided by its ledger lines on page %d: NOT RUN" % page)
        fails += 1
    else:
        n, r = two[0]
        other = [c for c in r["witnesses"]["candidates"] if c != r["owner"]]
        m0 = r["members"][0]
        flipped = mark_owner(r["family"], r["members"], r["box"], frames, _Flip(sr, m0, other[0])) if other else None
        ok = bool(flipped) and flipped["status"] == "guessed" and set(flipped["candidates"]) == {r["owner"], other[0]}
        log("  (b) %s (%s, %s) with view %s's ledger turned to %s: %s -- %s" % (
            r["members"], r["owner"], r["reason"], m0, other[0] if other else None,
            (flipped["status"], flipped["candidates"]) if flipped else None, "pass" if ok else "FAIL"))
        fails += 0 if ok else 1
    sa = system_arcs_of(_rows_of(rows, "system_arc"))
    sp, _ = arc_spans(sa, marks.mark_of, [])
    joined = [s for s in sp if len(s["views"]) == 2]
    if not joined:
        log("  (c) no two-view arc span on page %d: NOT RUN" % page)
        fails += 1
    else:
        s = joined[0]
        a, b = [dict(v) for v in sa if v["key"] in s["views"]][:2]
        bar = lines_at(frames, a["staff"], a["x0"])
        dy = bar.sp if bar else 20.0
        b_far = dict(b, pieces=[b["key"] + "#moved"], trace=[[t[0], t[1] + dy, t[2] + dy] for t in b["trace"]])
        b_same = dict(b, pieces=[b["key"] + "#copy"])
        n_far = len(arc_spans([a, b_far], {}, [])[0])
        n_same = len(arc_spans([a, b_same], {}, [])[0])
        ok = n_far == 2 and n_same == 1
        log("  (c) span %s (%s): view moved one space apart -> %d arcs (must be 2); unmoved, no shared page mark -> %d (must be 1) -- %s" % (
            s["views"], s["joined_by"], n_far, n_same, "pass" if ok else "FAIL"))
        fails += 0 if ok else 1
    log("  cells re-cut and matched: %s" % dict(verify))
    log("controls: %s" % ("ALL PASS" if fails == 0 else "%d FAILED" % fails))
    return fails


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="page_owner")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("readout")
    r.add_argument("rec", nargs="+")
    r.add_argument("--pages", default=None, help="only with one REC")
    r.add_argument("--out", default=None)
    r.add_argument("--tiles", default=None, help="cut 12 blind tiles over all RECs into DIR/tiles (key.json beside)")
    r.add_argument("--cell-map", default=None)
    r.add_argument("--no-old", action="store_true", help="skip the old cell-copy rules' verdicts")
    c = sub.add_parser("controls")
    c.add_argument("rec")
    c.add_argument("--page", type=int, required=True)
    c.add_argument("--cell-map", default=None)
    a = ap.parse_args(argv)
    cm = pathlib.Path(a.cell_map) if a.cell_map else None
    if a.cmd == "readout":
        pages = [int(p) for p in a.pages.split(",")] if a.pages else None
        if pages and len(a.rec) > 1:
            raise SystemExit("--pages takes one REC")
        pool: List[Dict[str, Any]] = []
        for i, rec in enumerate(a.rec):
            out = pathlib.Path(a.out) / ("rec%d" % i) if (a.out and len(a.rec) > 1) else (pathlib.Path(a.out) if a.out else None)
            run(rec, pages, out, cm, tile_pool=pool if a.tiles else None, with_old=not a.no_old)
        if a.tiles:
            cut_tiles(pool, pathlib.Path(a.tiles))
            print("tiles: %s/tiles (key.json beside the folder)" % a.tiles)
        return 0
    return 1 if controls(a.rec, a.page, cm) else 0


if __name__ == "__main__":
    sys.exit(main())
