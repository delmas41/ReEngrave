"""The ledgerLine population on a record, in staff steps — ROADMAP 3.4g.

    python3 benchmarks/omr-family-refusals-2026-09/probe/ledger_geometry.py <record.json> ...

⚠️ IT MEASURES BEFORE ANY RULE EXISTS, which is the only order in which the
tolerance can be derived rather than chosen. Sean's convention (DECISIONS
2026-09-23) says a ledger line stands OUTSIDE the staff at a WHOLE NUMBER OF
SPACES beyond line 1 or line 5. That claim has a distribution: every
`ledgerLine` box that is UNAMBIGUOUSLY outside the staff, and how far its
centre lands from the nearest rung step. The p5/p50/p95 of |offset| over that
population is what a tolerance may be set from; choosing a round number first
and reporting the catch afterwards is how a threshold comes to be fitted to
its own result.

⚠️ THE DERIVATION POPULATION EXCLUDES THE BAND EDGE ON PURPOSE. A box at step
-0.5 has no nearest rung inside half a space — the first legal rung is -2 —
so including it would put a 0.75-space "offset" in a histogram that is
supposed to measure ENGRAVING SCATTER around a rung. The first run of this
probe did exactly that and reported a 0.995-space maximum on a lattice whose
spacing is 1.0. The derivation therefore uses only boxes at least one full
rung clear of the outer line (|beyond| >= 1.25 spaces), where the nearest
rung is always within 0.5 spaces by construction and the number measured is
scatter and nothing else.

⚠️ PAGE FRAME THROUGHOUT. `Q.STAFF_LINES` / `Q.STAFF_SPACING` are page px and
`Q.GLYPH_BOX` carries `bbox_page_px` beside its canonical box; the canonical
box is measured inside one rescaled cell and cannot be compared with a staff's
own lines at all. The HEIGHT is measured in the canonical frame against
`Q.CELL_STAFF_SPACE`, which is that frame's own unit.
"""
import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.omr.staged import record_io                        # noqa: E402
from tools.omr.staged.record import Q, Subject, Kind          # noqa: E402
from tools.omr.staged.adjudicators.rhythm import _staff_step  # noqa: E402

LEDGER = "ledgerLine"
#: bottom line 0 … top line 8, in half-space STEPS (`_staff_step`'s frame).
LINE_STEPS = (0.0, 2.0, 4.0, 6.0, 8.0)
#: How far clear of the outer line a box must be before its offset is
#: SCATTER rather than band-edge clamping. See the module docstring.
DERIVATION_CLEAR_SPACES = 1.25


def pct(xs, p):
    if not xs:
        return None
    s = sorted(xs)
    i = min(len(s) - 1, max(0, int(round((p / 100.0) * (len(s) - 1)))))
    return round(s[i], 4)


def beyond_spaces(step):
    """How far outside the staff band, in SPACES. 0 inside, + either side."""
    if step < 0.0:
        return -step / 2.0
    if step > 8.0:
        return (step - 8.0) / 2.0
    return 0.0


def rung_offset_spaces(step):
    """|distance to the nearest whole space beyond line 1 or line 5|."""
    b = beyond_spaces(step)
    if b <= 0.0:
        return None
    return abs(b - round(b))


def rows(path):
    data = record_io.load_record(path)
    # ⚠️ A RUN FILE, NOT A BARE LOG. `staged` writes `{"record": {...},
    # "summary": ..., "provenance": ...}`; reading the top level for
    # `observations` returns an empty list and a clean, believable zero — the
    # first run of this probe printed exactly that for 1,878 ledger boxes.
    rec = data.get("record", data)
    lines, spacing, cellspace = {}, {}, {}
    boxes, heads = [], collections.defaultdict(list)
    for o in rec.get("observations") or ():
        q = o.get("quantity")
        if q == Q.STAFF_LINES:
            lines[o["subject"]] = o["value"]
        elif q == Q.STAFF_SPACING:
            spacing[o["subject"]] = o["value"]
        elif q == Q.CELL_STAFF_SPACE:
            cellspace[o["subject"]] = o["value"]
        elif q == Q.GLYPH_BOX:
            v = o.get("value")
            if not (isinstance(v, (list, tuple)) and len(v) == 5):
                continue
            if v[0] == LEDGER:
                boxes.append(o)
            elif str(v[0]).lower().startswith("notehead"):
                heads[Subject.from_key(o["subject"]).at(Kind.CELL).to_key()
                      ].append(o)
    out = []
    for o in boxes:
        sub = Subject.from_key(o["subject"])
        st = sub.at(Kind.STAFF).to_key()
        cell = sub.at(Kind.CELL).to_key()
        pb = (o.get("detail") or {}).get("bbox_page_px")
        _n, x_c, _y, w_c, h_c = o["value"]
        sp = cellspace.get(cell)
        step = _staff_step(pb, lines.get(st), spacing.get(st))
        out.append(dict(
            id=o["id"], subject=o["subject"], cell=cell, staff=st,
            step=step, page_box=pb,
            beyond=None if step is None else beyond_spaces(step),
            offset=None if step is None else rung_offset_spaces(step),
            line_gap=None if step is None else
            min(abs(step - t) for t in LINE_STEPS) / 2.0,
            h_spaces=(h_c / float(sp)) if sp else None,
            aspect=(h_c / float(w_c)) if w_c else None,
            # a head standing on this rung: same cell, x overlapping the box
            heads_over=sum(
                1 for hh in heads.get(cell, ())
                if min(hh["value"][1] + hh["value"][3], x_c + w_c)
                - max(hh["value"][1], x_c) > 0.0),
        ))
    return out


def _summarise(rs, name):
    with_step = [r for r in rs if r["step"] is not None]
    inside = [r for r in with_step if r["beyond"] == 0.0]
    clear = [r for r in with_step
             if r["beyond"] >= DERIVATION_CLEAR_SPACES]
    offs = [r["offset"] for r in clear]
    hs = [r["h_spaces"] for r in rs if r["h_spaces"] is not None]
    asp = [r["aspect"] for r in rs if r["aspect"] is not None]
    out = {
        "record": name,
        "n_ledger_boxes": len(rs),
        "no_page_frame": len(rs) - len(with_step),
        "n_inside_the_staff_band": len(inside),
        "n_inside_and_on_a_line_within_0p25": sum(
            1 for r in inside if r["line_gap"] <= 0.25),
        "n_outside_the_staff_band": len(with_step) - len(inside),
        "n_derivation_population_clear_of_the_edge": len(clear),
        "rung_offset_spaces_over_the_clear_population": {
            k: pct(offs, v) for k, v in
            (("p5", 5), ("p25", 25), ("p50", 50), ("p75", 75), ("p90", 90),
             ("p95", 95), ("p99", 99), ("max", 100))},
        "height_spaces": {"p5": pct(hs, 5), "p50": pct(hs, 50),
                          "p95": pct(hs, 95), "p99": pct(hs, 99),
                          "max": pct(hs, 100), "n": len(hs)},
        "aspect_h_over_w": {"p5": pct(asp, 5), "p50": pct(asp, 50),
                            "p95": pct(asp, 95), "max": pct(asp, 100),
                            "n": len(asp)},
        "taller_than_wide": sum(1 for r in rs if (r["aspect"] or 0) > 1.0),
        "height_over_half_a_space": sum(
            1 for r in rs if (r["h_spaces"] or 0) > 0.5),
        "offset_hist_spaces_clear_population": {
            f"{k:.2f}": v for k, v in sorted(collections.Counter(
                round(o / 0.05) * 0.05 for o in offs).items())},
    }
    # ── the REACH of each candidate rule, swept ─────────────────────────────
    sweep = {}
    for tol in (0.10, 0.15, 0.20, 0.25, 0.30, 0.40):
        on_line = [r for r in with_step
                   if r["beyond"] == 0.0 and r["line_gap"] <= tol]
        seen = {r["id"] for r in on_line}
        not_rung = [r for r in with_step if r["id"] not in seen
                    and (r["offset"] is None or r["offset"] > tol)]
        seen |= {r["id"] for r in not_rung}
        kept = [r for r in with_step if r["id"] not in seen]
        sweep[f"{tol:.2f}"] = {
            "on_a_staff_line": len(on_line),
            "not_at_a_rung_step": len(not_rung),
            "kept": len(kept),
            # ⚠️ THE POSITIVE CONTROL, COUNTED: a rung with a notehead's x
            # over it that the rule would refuse anyway.
            "refused_with_a_head_over_them":
                sum(1 for r in on_line + not_rung if r["heads_over"] > 0),
            "kept_with_a_head_over_them":
                sum(1 for r in kept if r["heads_over"] > 0),
        }
    out["sweep_by_tolerance_spaces"] = sweep
    return out


def line_gap_stats(rs):
    """How close a ledgerLine box lands to the MODELLED staff line.

    ⚠️ THIS IS THE TOLERANCE'S DERIVATION AND THE RUNG LATTICE IS NOT.
    `Q.STAFF_LINES` models a staff as five ideal rows; a scanned staff tilts
    and bows (rhythm.py measures 8-17 page px on this plate, up to a whole
    STEP). So the question a tolerance answers is *how far from its modelled
    line does ink that IS on a line land* — which is measured over the boxes
    INSIDE the staff band, where a ledger line cannot be and a staff-line
    fragment is the only thing the ink can be.
    """
    inside = [r for r in rs if r["step"] is not None and r["beyond"] == 0.0]
    gaps = [r["line_gap"] for r in inside]
    return {"n_inside": len(inside),
            **{k: pct(gaps, v) for k, v in
               (("p50", 50), ("p75", 75), ("p90", 90), ("p95", 95),
                ("p99", 99), ("max", 100))}}


if __name__ == "__main__":
    out = []
    for p in sys.argv[1:]:
        rs = rows(p)
        dest = (Path(__file__).resolve().parents[1] / "out" /
                f"ledger-rows-{Path(p).name.split('.')[0]}.json")
        dest.write_text(json.dumps(rs))
        summary = _summarise(rs, Path(p).name)
        summary["line_gap_spaces_inside_the_band"] = line_gap_stats(rs)
        summary["rows_cached_at"] = str(dest)
        out.append(summary)
    print(json.dumps(out, indent=1))
