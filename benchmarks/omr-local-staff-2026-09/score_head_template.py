#!/usr/bin/env python3
"""lane-ledger-template (2026-10-02): re-score the real truth set with
head TEMPLATE matching (`tools/omr/annotate/head_template.
template_middle_rung_evidence`) substituted for round 8's own box-centre
probe (`ledger_grid.head_middle_rung_evidence`) inside `derive_far_head_
step` -- the SAME local-monkeypatch measurement harness
`score_shape_trace.py` already used for the oval trace (held back, net
negative). MEASUREMENT ONLY (CLAUDE.md rule 9): nothing here is wired
into the shipped reader or any product/default path.

Per doc, builds templates ONCE from that page's own CLEAN, isolated,
one-per-cell on-staff noteheads (never from the far heads being scored),
then re-scores all four rows:

  * geometry            -- unchanged control.
  * round8              -- `score_doc(doc_id, four_causes_cd=True)`.
  * template            -- the SAME call, evidence swapped for the
    template match, run on EVERY far head.
  * template_where_undecided -- the template evidence is consulted ONLY
    for heads round 8 itself left `abstain` (its own `no_rung_before_
    the_head` branch) -- everywhere round 8 already answered, round 8's
    own answer is kept unchanged. This isolates the template's effect on
    exactly the population the task brief's two named heads come from,
    without risking a regression on heads round 8 already gets right.

    python3 benchmarks/omr-local-staff-2026-09/score_head_template.py
"""
from __future__ import annotations

import collections
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import score_truth_set_rungs as score  # noqa: E402
import truth_set_2_44c as ts  # noqa: E402
from tools.omr.staged import export as EXP  # noqa: E402
from tools.omr.staged.record import Q  # noqa: E402
from tools.omr.annotate import ledger_grid as lg  # noqa: E402
from tools.omr.annotate import head_template as ht  # noqa: E402

UNDECIDED_TWO = ["glyph/3/0/7/0/7", "glyph/3/0/7/2/4"]

# A box of this class, any OTHER glyph, intersecting the exemplar's own
# template WINDOW disqualifies it -- "not near a beam/slur box", read
# literally and conservatively: ANY other glyph's box in the window
# (`stem` excluded -- the module masks that one explicitly).
ISOLATION_IGNORE_CLASSES = {"stem", "staff"}


def _by_subject(per_head) -> Dict[str, Dict[str, Any]]:
    return {h["subject"]: h for h in per_head}


def _page_glyph_boxes(rec: EXP.Record) -> Dict[int, List[Tuple[str, str, tuple]]]:
    """Every `Q.GLYPH_BOX` row, by page, as `(subject, class_name, box)` --
    used both for the isolation check and `exclude_boxes` at match time."""
    out: Dict[int, List[Tuple[str, str, tuple]]] = collections.defaultdict(list)
    for o in rec.observations:
        if o["quantity"] != Q.GLYPH_BOX:
            continue
        value = o.get("value")
        if not value:
            continue
        sub = o["subject"]
        page = int(sub.split("/")[1])
        detail = o.get("detail") or {}
        pb = detail.get("bbox_page_px")
        if pb:
            out[page].append((sub, value[0], tuple(float(v) for v in pb)))
    return out


def _window_box(cx: float, cy: float, spacing: float) -> Tuple[float, float, float, float]:
    from tools.omr.staged.geometry import (
        STANDARD_HEAD_WIDTH_SPACES, STANDARD_HEAD_HEIGHT_SPACES,
    )
    head_w = STANDARD_HEAD_WIDTH_SPACES * spacing
    head_h = STANDARD_HEAD_HEIGHT_SPACES * spacing
    half_w = ht.WINDOW_HALF_WIDTH_HEAD_WIDTHS * head_w
    half_h = (ht.WINDOW_HALF_HEIGHT_HEAD_HEIGHTS * head_h
              + ht.WINDOW_HALF_HEIGHT_EXTRA_SPACES * spacing)
    return (cx - half_w, cy - half_h, cx + half_w, cy + half_h)


def _boxes_intersect(a, b) -> bool:
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    return ax0 < bx1 and bx0 < ax1 and ay0 < by1 and by0 < ay1


def collect_page_exemplars(rec: EXP.Record, gray, page: int,
                           glyph_boxes: List[Tuple[str, str, tuple]]
                          ) -> List[Dict[str, Any]]:
    """Every CLEAN, isolated, one-per-cell on-staff notehead on `page` --
    build-ready dicts for `head_template.build_templates`. Never a far
    head (`far_head_needs_ledger_read` excludes it by construction, same
    gate the reader's own population uses)."""
    by_subject = {s: (cls, box) for (s, cls, box) in glyph_boxes}
    exemplars: List[Dict[str, Any]] = []
    for o in rec.observations:
        if o["quantity"] != Q.NOTEHEAD_STAFF_POSITION:
            continue
        sub = o["subject"]
        if int(sub.split("/")[1]) != page:
            continue
        pos = float(o["value"])
        if lg.far_head_needs_ledger_read(int(round(pos))):
            continue
        entry = by_subject.get(sub)
        if entry is None:
            continue
        class_name, box = entry
        parts = sub.split("/")
        staff_key = f"staff/{parts[1]}/{parts[2]}/{parts[3]}"
        line_rows = rec.obs(Q.STAFF_LINES, staff_key)
        if not line_rows:
            continue
        global_lines = [float(y) for y in line_rows[-1]["value"]]
        lines = score.frame_lines_for_head(gray, global_lines, box)
        spacing = (max(lines) - min(lines)) / 4.0
        if spacing <= 0:
            continue
        x0, y0, x1, y1 = box
        cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
        window = _window_box(cx, cy, spacing)
        isolated = True
        for (osub, ocls, obox) in glyph_boxes:
            if osub == sub or ocls in ISOLATION_IGNORE_CLASSES:
                continue
            if _boxes_intersect(window, obox):
                isolated = False
                break
        cell_key = "cell/" + "/".join(parts[1:5])
        exemplars.append(dict(
            box=box, spacing=spacing, class_name=class_name,
            position=int(round(pos)), cell_key=cell_key, isolated=isolated,
        ))
    return exemplars


def build_templates_for_doc(doc_id: str) -> Tuple[Dict[Tuple[str, str], "ht.Template"],
                                                   Dict[str, int]]:
    loaded = ts.load_doc(doc_id)
    rec = loaded["rec"]
    pages = score.PageCache(loaded["cfg"])
    glyph_boxes_by_page = _page_glyph_boxes(rec)
    far_rows = score._far_head_rows(doc_id, loaded)
    far_pages = sorted({r["page"] for r in far_rows})

    merged: Dict[Tuple[str, str], List[Any]] = {}
    total_counts: Dict[str, int] = collections.Counter()
    all_exemplars: List[Dict[str, Any]] = []
    all_gray = {}
    for page in far_pages:
        gray = pages.get(page)
        all_gray[page] = gray
        exemplars = collect_page_exemplars(rec, gray, page,
                                           glyph_boxes_by_page.get(page, []))
        all_exemplars.append((page, gray, exemplars))
        for e in exemplars:
            pass

    # Build ONE template set per page (ink style can differ by page) --
    # `templates_by_page[page]`. A single page's own clean population is
    # often too sparse for one (kind, variant) combo (measured directly:
    # Litolff page 3 alone has 0 clean filled on-line/in-space exemplars,
    # even though the whole document has 6/9) -- `_POOLED_FALLBACK_KEY`
    # (page `None`) is built from every far-head page's exemplars POOLED
    # together, and `lookup_templates_for_page` below falls back to it
    # per (kind, variant) a page's own set is missing. Same print/engine
    # produced every page of one document, so this is a fallback to the
    # SAME SOURCE, never a different edition's ink.
    templates_by_page: Dict[int, Dict[Tuple[str, str], "ht.Template"]] = {}
    for page, gray, exemplars in all_exemplars:
        tmpls, counts = ht.build_templates(gray, exemplars)
        templates_by_page[page] = tmpls
        for k, v in counts.items():
            total_counts[k] += v

    # The pooled fallback needs ONE image to resample patches from --
    # exemplars from different pages are each cropped from THEIR OWN
    # page's image inside `build_templates`'s own `_extract_canonical_
    # patch`, so pooling exemplars across pages would silently crop every
    # one from `pooled_gray` (wrong page). Build the pooled set by
    # AVERAGING the already-built per-page templates instead (each was
    # correctly cropped from its own page), weighted by exemplar count --
    # the same combination `build_templates` itself does internally.
    pooled: Dict[Tuple[str, str], "ht.Template"] = {}
    sums: Dict[Tuple[str, str], Any] = {}
    counts_n: Dict[Tuple[str, str], int] = collections.Counter()
    for page, tmpls in templates_by_page.items():
        for key, tmpl in tmpls.items():
            if key not in sums:
                sums[key] = tmpl.img.astype("float64") * tmpl.n
            else:
                sums[key] = sums[key] + tmpl.img.astype("float64") * tmpl.n
            counts_n[key] += tmpl.n
    for key, total in sums.items():
        n = counts_n[key]
        if n < ht.MIN_TEMPLATE_EXEMPLARS:
            continue
        kind, variant = key
        pooled[key] = ht.Template(
            img=(total / n).astype("float32"), mask=ht.SCORE_MASKS[variant],
            line_mask_components=ht.LINE_MASK_COMPONENTS[variant],
            n=n, kind=kind, variant=variant,
        )
    templates_by_page["pooled"] = pooled
    return templates_by_page, dict(total_counts)


def templates_for_page(templates_by_page, page: int
                       ) -> Dict[Tuple[str, str], "ht.Template"]:
    """This page's own templates, falling back to the document-pooled
    set (built across every far-head page) for any (kind, variant) this
    page's own clean population was too sparse to build."""
    page_tmpls = templates_by_page.get(page, {})
    pooled = templates_by_page.get("pooled", {})
    merged = dict(pooled)
    merged.update(page_tmpls)
    return merged


def _install_template_evidence(templates_by_page, boxes_by_page):
    original_evidence = lg.head_middle_rung_evidence
    original_reader = score.reader_absolute_position

    def _evidence_with_templates(img_gray, head_box, spacing, exclude_boxes=None):
        # The current page is recovered from the closure state stashed by
        # the wrapped reader below (same pattern `score_shape_trace.py`
        # uses for `staff_lines`).
        page = _CURRENT_PAGE[0]
        templates = templates_for_page(templates_by_page, page)
        return ht.template_middle_rung_evidence(
            img_gray, head_box, spacing, exclude_boxes, templates=templates,
        )

    def _wrapped_reader(gray, global_lines, box, subject, page_notehead_boxes,
                        page_accidental_boxes=None, four_causes_cd=False):
        page = int(subject.split("/")[1])
        _CURRENT_PAGE[0] = page
        try:
            return original_reader(
                gray, global_lines, box, subject, page_notehead_boxes,
                page_accidental_boxes=page_accidental_boxes,
                four_causes_cd=four_causes_cd,
            )
        finally:
            _CURRENT_PAGE[0] = None

    lg.head_middle_rung_evidence = _evidence_with_templates
    score.reader_absolute_position = _wrapped_reader
    return original_evidence, original_reader


_CURRENT_PAGE = [None]


def _restore_evidence(originals):
    original_evidence, original_reader = originals
    lg.head_middle_rung_evidence = original_evidence
    score.reader_absolute_position = original_reader


def score_doc_with_templates(doc_id: str, templates_by_page) -> Dict[str, Any]:
    boxes_by_page = _page_glyph_boxes(ts.load_doc(doc_id)["rec"])
    originals = _install_template_evidence(templates_by_page, boxes_by_page)
    try:
        return score.score_doc(doc_id, four_causes_cd=True)
    finally:
        _restore_evidence(originals)


def main() -> int:
    overall_ok = True
    for doc_id in ts.DOCS:
        print(f"=== {doc_id} ===")
        templates_by_page, counts = build_templates_for_doc(doc_id)
        print(f"  template exemplar counts: {counts}")

        round8 = score.score_doc(doc_id, four_causes_cd=True)
        template_run = score_doc_with_templates(doc_id, templates_by_page)

        tb, ta = round8["tally"], template_run["tally"]
        n = sum(tb.get("geometry", {}).values())
        g = tb.get("geometry", {})
        print(f"  geometry     right={g.get('right',0):>3} wrong={g.get('wrong',0):>3} "
              f"abstain={g.get('abstain',0):>3}  (n={n})")
        r8 = tb.get("rungs_after", {})
        print(f"  round8       right={r8.get('right',0):>3} wrong={r8.get('wrong',0):>3} "
              f"abstain={r8.get('abstain',0):>3}  (n={n})")
        tmv = ta.get("rungs_after", {})
        print(f"  template     right={tmv.get('right',0):>3} wrong={tmv.get('wrong',0):>3} "
              f"abstain={tmv.get('abstain',0):>3}  (n={n})")

        before_by = _by_subject(round8["per_head"])
        after_by = _by_subject(template_run["per_head"])

        # template_where_undecided: keep round8's own answer EXCEPT where
        # round8 itself abstained -- there, take the template run's
        # answer instead.
        combo_tally = collections.Counter()
        combo_by: Dict[str, str] = {}
        for sub, hb in before_by.items():
            ha = after_by.get(sub)
            if hb["v_after"] == "abstain" and ha is not None:
                combo_by[sub] = ha["v_after"]
            else:
                combo_by[sub] = hb["v_after"]
            combo_tally[combo_by[sub]] += 1
        print(f"  template_where_undecided right={combo_tally.get('right',0):>3} "
              f"wrong={combo_tally.get('wrong',0):>3} "
              f"abstain={combo_tally.get('abstain',0):>3}  (n={n})")

        regressions = [
            sub for sub, hb in before_by.items()
            if hb["v_after"] == "right"
            and after_by.get(sub, {}).get("v_after") != "right"
        ]
        print(f"  regressions (right under round8, not right under template): "
              f"{len(regressions)} {regressions}")
        if regressions:
            overall_ok = False

        flips = [
            sub for sub, hb in before_by.items()
            if hb["v_after"] != after_by.get(sub, {}).get("v_after")
        ]
        print(f"  all flips (round8 -> template): {len(flips)}")
        for sub in flips:
            hb, ha = before_by.get(sub), after_by.get(sub)
            print(f"    {sub:<20} round8={hb['v_after']:<10} "
                  f"template={ha['v_after']:<10} reason={ha['reason']}")

        if doc_id == "beethoven5-litolff":
            print("  the two undecided heads, round8 -> template:")
            for sub in UNDECIDED_TWO:
                hb, ha = before_by.get(sub), after_by.get(sub)
                vb = hb["v_after"] if hb else "not-in-population"
                va = ha["v_after"] if ha else "not-in-population"
                rb = hb["reason"] if hb else ""
                ra = ha["reason"] if ha else ""
                flip = " <-- FLIPPED" if hb and ha and vb != va else ""
                print(f"    {sub:<20} round8={vb:<10} template={va:<10}{flip}")
                print(f"      round8 reason:   {rb}")
                print(f"      template reason: {ra}")
        print()

    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
