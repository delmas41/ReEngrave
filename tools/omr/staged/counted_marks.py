"""ROADMAP 2.316 -- COUNT PRINTED NOTES AND ARCS, NOT DETECTOR BOXES. PATH: STAGED tooling. Reads, decides nothing, changes no verdict and no byte of
the exported file (the tapped export below is byte-identical to `export.to_musicxml` once its `rg=` stamps are removed; a test shows it).

WHY (the cause, from the 20261117-night read-out). Our measuring tools counted the detector's BOXES and called them notes and arcs:
  * "notes reaching file 9065/12039" divided the `<note>` elements in the file by every NOTEHEAD box the detector drew. Most boxes not written are a
    second box on a written note, a neighbouring staff's copy of one, or ink that is not a note at all (a barline, clef, key, bracket, dot), and the
    9065 itself counts a head twice where the file writes it twice (a unison's second voice, a condensed staff's doubled copy).
  * "ties and slurs not written" added boxes the page-arc pass REPLACED (`replaced_by_page_arc`, bookkeeping: the arc is written once, by its run)
    and boxes the old path retired, and never counted a page arc run that was read and not written.
The process lesson: a count of boxes is a count of the detector, not of the page; a figure that names a printed thing counts that thing (CLAUDE rule 7).

WHAT A NOTE IS HERE. One printed head. Every NOTEHEAD box is exactly one of (the identity is asserted, so a box cannot go missing):
  written                       the head is in the file (a pitched `<note>` carries its glyph key). A head written twice (unison second voice, condensed copy) is one note.
  written_as_a_rest             a head-shaped box the file writes as a rest (an eighth rest)                                  -- NOT a note
  dropped_at_render             placed, then left out when its bar was refused (a bar held out, an unread gap)             -- a candidate lost note
  duplicate_of_written          not written, and a WRITTEN head stands at its place (the same ink: a second box, a neighbouring staff's copy) -- NOT a note
  non_note_ink                  not written and refused as ink that is not a note (claimed by a barline/clef/key/bracket/word/dot, a rest, a beam
                                piece, an arc tail, a tremolo slash, a dynamic letter)                                     -- NOT a note
  duplicate_no_written_twin     refused as a duplicate of another box, but no written head stands there (a rest's twin, or the other copy is also
                                not written)                                                                              -- named apart, never a lost note
  candidate lost                every other unwritten head: boxes that overlap are ONE note, split by the exporter's own fate:
                                value_undecided / no_pitch / owned_no_twin / clipped / too_narrow / dropped_at_render / other.
"Candidate" because a note with no written twin and not claimed as other ink may still be a box on ink that is not a note (a crop-cut piece); a crop
look or Sean's tiles settle it, the count does not. The headline is `written / (written + candidate lost)`; the old box figure stays printed beside it.

ARCS. One arc is a page-ink RUN written once (or not), never a box. `arcs_count` counts: old-box refusals that are still refusals; page runs read
and not written, by reason; and names apart the boxes the page pass replaced / the old path retired (bookkeeping) and the unwitnessed runs (no detector
box agrees; the 2.274 gather measured about 4.8 fakes a page, so they are not called lost arcs).

CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED: that boxes overlapping by `judged.boxes_overlap` (IoU >= 0.3, or a centre inside the other)
are one printed ink; a crop of a "duplicate" with no note under it would falsify it. NOT CONFIRMED beyond the Brahms p0 hand truth (a control).

    python3 -m tools.omr.staged.counted_marks record REC.record.json OUT.json     # load, tapped export, census (a big record loads big: ~12 GB for Brahms)
    python3 -m tools.omr.staged.counted_marks facts FACTS.json [OUT.json]         # census from a note-loss-funnel `extract.py` facts file
    python3 -m tools.omr.staged.counted_marks arcs REPORT.json                    # arcs row from an export report
"""
from __future__ import annotations

import collections
import contextlib
import json
import re
import sys
from typing import Any, Dict, Iterator, List, Optional, Sequence, Tuple

DERIVED_CHECK = True

# ───────────────────────────── 1. the fates ─────────────────────────────

#: the exporter's own refusal names for a head box that is a COPY of another box (`export._place_notes`)
DUPLICATE_FATES = frozenset({
    "mark_group_duplicate", "not_a_notehead:notehead_is_a_duplicate_box", "not_a_notehead:stacked_head_duplicate",
    "not_a_notehead:is_a_rest_twin", "not_a_notehead:belongs_to_a_nearer_staff", "not_a_notehead:head_cut_piece"})
#: refusals that say the ink is something else (the adjudicator named what); `claimed_by:*` is any earlier layer's claim
NON_NOTE_FATES = frozenset({
    "not_a_notehead:on_a_rest", "not_a_notehead:is_a_rest_shape", "ink_is_a_whole_rest", "not_a_notehead:is_a_beam_piece",
    "not_a_notehead:is_an_arc_tail", "not_a_notehead:tremolo_slash_crosses_stem", "not_a_notehead:on_a_dynamic_letter"})
WRITTEN_FATES = frozenset({"written", "written_relocated"})
VALUE_FATES = frozenset({"duration_narrowed", "chord_value_undecided", "duration_abstained"})

#: the cause names of a candidate lost note, in the order a cluster of boxes takes its name
LOST_CAUSES = ("value_undecided", "no_pitch", "dropped_at_render", "owned_no_twin", "clipped", "too_narrow", "other")


def fate_group(fate: Optional[str]) -> str:
    """`written` / `duplicate` / `non_note` / a LOST cause, for one exporter fate string. A fate not named here is `other` (a candidate), never dropped."""
    if fate in WRITTEN_FATES:
        return "written"
    if fate in DUPLICATE_FATES:
        return "duplicate"
    if fate in NON_NOTE_FATES or (isinstance(fate, str) and fate.startswith("not_a_notehead:claimed_by")):
        return "non_note"
    if fate in VALUE_FATES:
        return "value_undecided"
    if fate == "no_pitch":
        return "no_pitch"
    if fate == "owned_by_another_staff":
        return "owned_no_twin"
    if fate == "not_a_notehead:clipped_fragment":
        return "clipped"
    if fate == "not_a_notehead:too_narrow":
        return "too_narrow"
    return "other"


def non_note_kind(fate: Optional[str]) -> str:
    """What non-note ink a refusal names: `claimed_by:barline` -> `barline`, `on_a_rest` -> `rest`, ..."""
    f = str(fate)
    if f.startswith("not_a_notehead:claimed_by:"):
        return f.split(":", 2)[2]
    return {"not_a_notehead:on_a_rest": "rest", "not_a_notehead:is_a_rest_shape": "rest", "ink_is_a_whole_rest": "rest",
            "not_a_notehead:is_a_beam_piece": "beam", "not_a_notehead:is_an_arc_tail": "arc",
            "not_a_notehead:tremolo_slash_crosses_stem": "tremolo", "not_a_notehead:on_a_dynamic_letter": "dynamic_letter"}.get(f, f)


# ───────────────────────────── 2. the places ─────────────────────────────

_CELL = 64.0           # px grid for the neighbour search (a head box is ~20-45 px at 600 dpi)


def _same_ink(a: Sequence[float], b: Sequence[float]) -> bool:
    from .judged import boxes_overlap
    return bool(boxes_overlap(a, b)[0])


class _Grid:
    """Boxes of one page bucketed on a coarse grid, so a neighbour search is not all-pairs."""

    def __init__(self) -> None:
        self.cells: Dict[Tuple[int, int, int], List[Tuple[str, Sequence[float]]]] = collections.defaultdict(list)

    def add(self, page: int, key: str, box: Sequence[float]) -> None:
        for gx in range(int(box[0] // _CELL), int(box[2] // _CELL) + 1):
            for gy in range(int(box[1] // _CELL), int(box[3] // _CELL) + 1):
                self.cells[(page, gx, gy)].append((key, box))

    def near(self, page: int, box: Sequence[float]) -> Iterator[Tuple[str, Sequence[float]]]:
        seen = set()
        for gx in range(int(box[0] // _CELL) - 1, int(box[2] // _CELL) + 2):
            for gy in range(int(box[1] // _CELL) - 1, int(box[3] // _CELL) + 2):
                for k, b in self.cells.get((page, gx, gy), ()):
                    if k not in seen:
                        seen.add(k)
                        yield k, b


# ───────────────────────────── 3. the census ─────────────────────────────

def note_census(heads: Dict[str, Dict[str, Any]], written_keys: Sequence[str], rest_keys: Sequence[str] = (), *,
                only_pages: Optional[Sequence[int]] = None, keep_lists: bool = False) -> Dict[str, Any]:
    """Printed notes from the detector's head boxes.

    `heads`: `{glyph key: {"page": int, "box": [x0, y0, x1, y1], "fate": exporter fate or None}}` -- EVERY NOTEHEAD box of the record.
    `written_keys`: the glyph keys of the pitched `<note>` elements the file holds (a key may repeat: a head written twice).
    `rest_keys`: head boxes the file writes as a REST (an eighth rest drawn on a head-shaped box): not a note, not lost.
    `only_pages`: count only these pages (the boxes of the other pages still count as neighbours).

    Returns `{"notes": {...}, "boxes": {...}, "by_page": {page: {...}}, "identity": {...}}`; see the module docstring. Raises `CensusError` when a box
    is in no bucket (the identity is an equality)."""
    wk = set(written_keys)
    rk = set(rest_keys) - wk
    pages = set(only_pages) if only_pages is not None else None
    written_grid = _Grid()
    for k, h in heads.items():
        if k in wk:
            if h.get("box"):
                written_grid.add(h["page"], k, h["box"])
    bucket: Dict[str, str] = {}
    detail: Dict[str, str] = {}
    unwritten: List[str] = []
    for k, h in heads.items():
        if k in wk:
            bucket[k] = "written"
            continue
        if k in rk:
            bucket[k] = "written_as_a_rest"
            continue
        g = fate_group(h.get("fate"))
        if g == "written":
            bucket[k], detail[k] = "lost", "dropped_at_render"       # placed, then its bar was refused
            unwritten.append(k)
            continue
        twin = bool(h.get("box")) and any(_same_ink(h["box"], b) for _k, b in written_grid.near(h["page"], h["box"]))
        if twin:
            bucket[k] = "duplicate_of_written"
        elif g == "non_note":
            bucket[k], detail[k] = "non_note_ink", non_note_kind(h.get("fate"))
        elif g == "duplicate":
            bucket[k] = "duplicate_no_written_twin"
            unwritten.append(k)
        else:
            bucket[k], detail[k] = "lost", g
            unwritten.append(k)
    # candidate boxes that overlap are ONE note (union-find over the unwritten, not-twin boxes)
    cand = [k for k in unwritten if bucket[k] == "lost"]
    parent = {k: k for k in cand}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    grid = _Grid()
    for k in cand:
        if heads[k].get("box"):
            grid.add(heads[k]["page"], k, heads[k]["box"])
    for k in cand:
        if not heads[k].get("box"):          # a head with no box on the page (a hand-built record) has no neighbours: its own note
            continue
        for k2, b2 in grid.near(heads[k]["page"], heads[k]["box"]):
            if k2 != k and _same_ink(heads[k]["box"], b2):
                parent[find(k)] = find(k2)
    clusters: Dict[str, List[str]] = collections.defaultdict(list)
    for k in cand:
        clusters[find(k)].append(k)
    # a duplicate-fated box with no written twin that overlaps a candidate is that candidate's copy: it joins the cluster (still counted as a box)
    absorbed = 0
    for k in unwritten:
        if bucket[k] != "duplicate_no_written_twin" or not heads[k].get("box"):
            continue
        for k2, b2 in grid.near(heads[k]["page"], heads[k]["box"]):
            if _same_ink(heads[k]["box"], b2):
                bucket[k], detail[k] = "duplicate_of_unwritten_candidate", "joined:" + find(k2)
                absorbed += 1
                break

    def cause_of(members: List[str]) -> str:
        have = {detail[m] for m in members}
        return next(c for c in LOST_CAUSES if c in have)
    in_scope = (lambda k: True) if pages is None else (lambda k: heads[k]["page"] in pages)
    out_pages: Dict[int, Dict[str, Any]] = {}
    totals: Dict[str, Any] = collections.Counter()
    lost_by: Dict[str, int] = collections.Counter()
    nonnote_by: Dict[str, int] = collections.Counter()
    lost_lists: Dict[str, List[List[str]]] = collections.defaultdict(list)
    for k, b in bucket.items():
        if not in_scope(k):
            continue
        pg = heads[k]["page"]
        totals["boxes_" + b] += 1
        pp = out_pages.setdefault(pg, collections.Counter())
        pp["boxes_" + b] += 1
        if b == "non_note_ink":
            nonnote_by[detail[k]] += 1
    for root, members in clusters.items():
        members = [m for m in members if in_scope(m)]
        if not members:
            continue
        c = cause_of(members)
        lost_by[c] += 1
        totals["lost_notes"] += 1
        out_pages.setdefault(heads[members[0]]["page"], collections.Counter())["lost_notes"] += 1
        if keep_lists:
            lost_lists[c].append(sorted(members))
    n_written = sum(1 for k in set(wk) if k in heads and in_scope(k))
    n_heads = sum(1 for k in heads if in_scope(k))
    accounted = sum(v for k, v in totals.items() if k.startswith("boxes_"))
    if accounted != n_heads:
        raise CensusError("%d head boxes, %d in a bucket" % (n_heads, accounted))
    n_lost = int(totals["lost_notes"])
    out = {
        "notes": {
            "written": n_written, "candidate_lost": n_lost, "printed": n_written + n_lost,
            "fraction_written": (n_written / (n_written + n_lost)) if (n_written + n_lost) else None,
            "candidate_lost_by_cause": {c: lost_by.get(c, 0) for c in LOST_CAUSES},
        },
        "boxes": {
            "heads_in_log": n_heads,
            "written": int(totals["boxes_written"]),
            "written_as_a_rest": int(totals["boxes_written_as_a_rest"]),
            "candidate_lost": int(totals["boxes_lost"]),
            "dropped_at_render": sum(1 for k, d in detail.items() if d == "dropped_at_render" and in_scope(k)),
            "duplicate_of_written": int(totals["boxes_duplicate_of_written"]),
            "duplicate_of_unwritten_candidate": int(totals["boxes_duplicate_of_unwritten_candidate"]),
            "duplicate_no_written_twin": int(totals["boxes_duplicate_no_written_twin"]),
            "non_note_ink": int(totals["boxes_non_note_ink"]),
            "non_note_ink_by_kind": dict(nonnote_by),
        },
        "by_page": {str(p): dict(c) for p, c in sorted(out_pages.items())},
        "identity": {"heads_in_log": n_heads, "in_a_bucket": accounted, "ok": accounted == n_heads},
    }
    if keep_lists:
        out["lost_lists"] = dict(lost_lists)
    return out


class CensusError(RuntimeError):
    """A head box that is in no bucket, or a tapped export that did not trace."""


def format_notes(census: Dict[str, Any], old_boxes: Optional[Tuple[int, int]] = None) -> List[str]:
    """The lines a report prints: printed notes first, the old box figure beside it labelled `boxes`, then what is named apart."""
    n, b = census["notes"], census["boxes"]
    lines = ["notes written (printed notes) %d of %d  (%.3f)  | candidate lost notes %d" % (
        n["written"], n["printed"], n["fraction_written"] or 0.0, n["candidate_lost"])]
    if old_boxes is not None:
        lines.append("  boxes (old figure, kept for comparison): %d of %d <note> elements/head boxes" % old_boxes)
    lc = n["candidate_lost_by_cause"]
    lines.append("  candidate lost, by the exporter's fate: " + ", ".join("%s %d" % (c, lc[c]) for c in LOST_CAUSES if lc.get(c)))
    lines.append("  named apart, never lost notes: duplicates of a written note %d boxes; non-note ink %d boxes (%s); "
                 "duplicate with no written twin %d boxes" % (
                     b["duplicate_of_written"], b["non_note_ink"],
                     ", ".join("%s %d" % kv for kv in sorted(b["non_note_ink_by_kind"].items(), key=lambda kv: -kv[1])[:6]),
                     b["duplicate_no_written_twin"]))
    return lines


# ───────────────────────────── 4. the tapped export ─────────────────────────────

_RG = re.compile(r'<note rg="[^"]*"')


def strip_trace(xml: str) -> str:
    """The traced file without its `rg=` stamps: byte-identical to the untraced export (`<note rg="..."` -> `<note`)."""
    return _RG.sub("<note", xml)


def tapped_export(result: Dict[str, Any], strip: bool = True, only_pages: Optional[Sequence[int]] = None
                  ) -> Tuple[str, Dict[str, Any], Dict[str, Any]]:
    """`(xml, report, census)`: `export.to_musicxml(result)` with two read-only taps -- `lane_report.traced_export` (each `<note>` stamped with its glyph key,
    stamps removed again) and `_place_notes`' own `fates` out-param. The returned xml is byte-identical to the untraced export. Raises `CensusError` when the
    taps do not line up (never a census from a mis-aligned trace). `strip=False` keeps the stamps (a lane tool that matches the file's notes to the page by them);
    `only_pages` counts those pages only."""
    from . import export as E
    from . import lane_report as LR
    from .record import Q
    rec = result["record"] if "record" in result else result
    obs = rec["observations"]
    boxes = LR.glyph_boxes(obs)
    head_keys = [o["subject"] for o in obs if o.get("quantity") == Q.NOTEHEAD_CLASS]
    fates_box: Dict[str, Any] = {}
    orig = E._place_notes

    def tapped(*a, **k):
        out = orig(*a, **k)
        fates_box["fates"] = k.get("fates")
        return out
    E._place_notes = tapped
    try:
        with LR.traced_export():
            traced_xml, report = E.to_musicxml(result)
    finally:
        E._place_notes = orig
    if fates_box.get("fates") is None:
        raise CensusError("the tap on export._place_notes saw no `fates` out-param (the call changed shape)")
    fates = fates_box["fates"]
    xml = strip_trace(traced_xml) if strip else traced_xml
    written, rests = [], []
    for m in re.finditer(r'<note rg="([^"]*)"[^>]*>(.*?)</note>', traced_xml, re.S):
        (rests if "<rest" in m.group(2) else written).append(m.group(1))
    heads = {}
    for k in head_keys:
        b = boxes.get(k)
        # a head with no box has no place: it can be written or not, never a twin (every head of a real record has a box; a hand-built test record may not)
        heads[k] = {"page": b["page"] if b else (LR.page_of(k) or 0), "box": b["box"] if b else None, "fate": fates.get(k)}
    return xml, report, note_census(heads, written, rests, only_pages=only_pages)


# ───────────────────────────── 5. arcs ─────────────────────────────

REPLACED, RETIRED = "replaced_by_page_arc", "old_box_path_retired"


def arcs_count(report: Dict[str, Any]) -> Dict[str, Any]:
    """Arcs, not boxes, from the exporter's own report (`arcs_not_written` by reason + the page-arc counters in `written`).

    `not_written_total`  = old-box refusals that are still refusals + page runs read and not written (abstained, written-in-plan-but-not-in-file).
    Named apart: `replaced` / `retired` boxes (bookkeeping: the arc is written once by its run, or left to the page pass), `not_an_arc` (boxes refused
    as ink that is no arc), `unwitnessed` page runs (no detector box agrees: mostly fakes, never called lost arcs).
    A page-arc count the report does not hold is `None` (a record gathered without the page pass), never 0."""
    anw = dict(report.get("arcs_not_written") or {})
    w = report.get("written") or {}
    page_on = "page_arc_runs" in w
    replaced, retired = int(anw.pop(REPLACED, 0)), int(anw.pop(RETIRED, 0))
    not_an_arc = {k: anw.pop(k) for k in [k for k in anw if k.startswith("not_an_arc:")]}
    slur_nif, tie_nif = int(w.get("page_arc_slurs_not_in_file", 0)), int(w.get("page_arc_ties_not_in_file", 0))
    # a bound page curve whose head is not in the file is filed by the exporter under the old names too; count it once, as a page arc
    adjusted: Dict[str, int] = {}
    for name, n in (("slur_bound_end_not_in_file", slur_nif), ("tie_end_not_in_file", tie_nif)):
        if name in anw and n:
            take = min(int(anw[name]), n)
            anw[name] = int(anw[name]) - take
            adjusted[name] = take
    old_by = {k: int(v) for k, v in anw.items() if int(v)}
    page = None
    if page_on:
        page = {
            "runs_read": int(w.get("page_arc_runs", 0)),
            "abstained": int(w.get("page_arc_runs_abstained", 0)),
            "abstained_of_which_kind_unread": int(w.get("page_arc_runs_kind_unread_nothing_written", 0)),
            "written_slur_not_in_file": slur_nif, "written_tie_not_in_file": tie_nif,
            "unwitnessed": int(w.get("page_arc_runs_not_witnessed", 0)),
            "written_in_file": int(w.get("page_arc_slurs_in_file", 0)) + int(w.get("page_arc_ties_in_file", 0)),
        }
    old_total = sum(old_by.values())
    page_unwritten = (page["abstained"] + slur_nif + tie_nif) if page else 0
    return {
        "page_pass_on": page_on,
        "not_written_total": old_total + page_unwritten,
        "old_box_refusals": old_total, "old_box_refusals_by_reason": old_by,
        "page_runs_not_written": page_unwritten if page else None,
        "page_runs": page,
        "apart": {"replaced_by_page_arc_boxes": replaced, "old_box_path_retired_boxes": retired, "not_an_arc_boxes": sum(not_an_arc.values()),
                  "unwitnessed_page_runs": page["unwitnessed"] if page else None},
        "adjusted_for_double_count": adjusted,
        "with_unwitnessed": (old_total + page_unwritten + page["unwitnessed"]) if page else old_total,
        # the old ranking row, for comparison: every reason but `not_an_arc:*`, boxes and all
        "old_figure_boxes": sum(int(v) for k, v in (report.get("arcs_not_written") or {}).items() if not k.startswith("not_an_arc:")),
    }


def format_arcs(a: Dict[str, Any]) -> List[str]:
    lines = ["ties and slurs not written (arcs) %d  = old-box refusals %d + page arc runs read and not written %s" % (
        a["not_written_total"], a["old_box_refusals"], a["page_runs_not_written"])]
    p = a["page_runs"]
    if p:
        lines.append("  page arc runs: read %d, written in file %d; not written: abstained %d (of which kind unread %d), "
                     "written in plan but not in file %d slurs + %d ties" % (
                         p["runs_read"], p["written_in_file"], p["abstained"], p["abstained_of_which_kind_unread"],
                         p["written_slur_not_in_file"], p["written_tie_not_in_file"]))
    ap = a["apart"]
    lines.append("  named apart: boxes replaced by a written page arc %d; old box path retired %d (boxes, bookkeeping); boxes that are no arc %d; "
                 "unwitnessed page runs %s (mostly fakes)" % (ap["replaced_by_page_arc_boxes"], ap["old_box_path_retired_boxes"],
                                                              ap["not_an_arc_boxes"], ap["unwitnessed_page_runs"]))
    return lines


# ───────────────────────────── 6. command line ─────────────────────────────

def census_from_facts(path: str, only_pages: Optional[Sequence[int]] = None) -> Dict[str, Any]:
    """A census from a note-loss-funnel `extract.py` facts file (`glyphs`: head, page, box, fate; `written`: the file's notes with their glyph keys)."""
    f = json.load(open(path))
    heads = {k: {"page": v["page"], "box": v["box"], "fate": v.get("fate")} for k, v in f["glyphs"].items() if v.get("head")}
    written = [h["rg"] for h in f["written"] if h.get("kind") == "note" and h.get("rg")]
    rests = [h["rg"] for h in f["written"] if h.get("kind") == "rest" and h.get("rg")]
    return note_census(heads, written, rests, only_pages=only_pages)


def main(argv: Optional[Sequence[str]] = None) -> int:
    a = list(argv if argv is not None else sys.argv[1:])
    if len(a) < 2 or a[0] not in ("record", "facts", "arcs"):
        print(__doc__.split("\n\n")[0] + "\nusage: counted_marks record REC OUT | facts FACTS [OUT] | arcs REPORT", file=sys.stderr)
        return 2
    cmd = a[0]
    if cmd == "arcs":
        rep = json.load(open(a[1]))
        rep = rep.get("report", rep)
        out = arcs_count(rep)
        print("\n".join(format_arcs(out)))
        return 0
    if cmd == "facts":
        out = census_from_facts(a[1])
    else:
        from .record_io import load_record
        result = load_record(a[1])
        if "record" not in result:
            result = {"record": result, "summary": {}}
        _xml, report, out = tapped_export(result)
        out["old_figure"] = {"n": report["written"]["notes"], "of": report["balance"]["noteheads_in_log"]}
        out["arcs"] = arcs_count(report)
    old = (out["old_figure"]["n"], out["old_figure"]["of"]) if "old_figure" in out else None
    print("\n".join(format_notes(out, old)))
    if len(a) > 2:
        with open(a[2], "w") as fh:
            json.dump(out, fh, indent=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
