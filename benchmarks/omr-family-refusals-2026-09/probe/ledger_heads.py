"""Sean's second ledger convention, MEASURED BEFORE IT IS WRITTEN — 3.4g-2.

    python3 .../ledger_heads.py <record.json> ...

Sean, 2026-09-24 (`docs/DECISIONS.md`): *"the ledger lines will only be on the
OUTSIDE of the staff and only happen if there are actual notes in the
staff"*. The second half is a claim about a DISTANCE — how far from a rung
does the notehead that stands on it sit — and that distance has never been
measured. `probe/ledger_geometry.py` computed a `heads_over` field last
lane and §6.5 of the FINDINGS states plainly that it is x-overlap ALONE and
was used as evidence nowhere. This probe measures the VERTICAL half of it.

⚠️ THE CANONICAL CELL FRAME, FOR BOTH BOXES AND FOR THE UNIT. A rung and a
notehead in ONE cell are measured in that cell's rescaled frame and
`Q.CELL_STAFF_SPACE` is that frame's own staff space — so the three numbers
come from one ruler. The staff STEP is the other half of the geometry and is
page pixels (`Q.STAFF_LINES`); the two are never compared, exactly as
`family_precision._ledger_geometry` says.

⚠️ THE TOLERANCE IS DERIVED FROM THE RUNGS THE SHIPPED RULES KEEP, which is
the only population available that is not the rule's own output: a box
outside the staff band, off every staff line by more than the measured
registration scatter, and rung-thick. Choosing a round number first and
reporting the catch afterwards is how a threshold comes to be fitted to its
own result.

⚠️ A LEDGER RUN IS WHY THE DISTRIBUTION HAS A TAIL AND NOT AN ERROR. A note
three spaces above the staff prints THREE rungs and stands on the outermost:
the inner two are 1 and 2 spaces from the only head that x-overlaps them. So
the p95 of this distance is not "how thick is a notehead", it is "how long is
a ledger run on this plate", and that is the number the rule needs.
"""
import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.omr.staged import record_io                        # noqa: E402
from tools.omr.staged.record import Q, Subject, Kind          # noqa: E402
from tools.omr.staged.adjudicators.rhythm import _staff_step  # noqa: E402
# ⚠️ ONE NOTEHEAD TEST, IMPORTED NOT RESTATED — the same one the decision
# reads, so the probe cannot measure a population the rule does not see.
from tools.omr.staged.gather import _NOTEHEAD_PREFIX as NOTEHEAD  # noqa: E402

LEDGER = "ledgerLine"
LINE_STEPS = (0.0, 2.0, 4.0, 6.0, 8.0)
#: The shipped tolerance, so "kept under the shipped rules" means the same
#: thing here as it does in the decision.
TOL = 0.25
TALL = 0.5


def pct(xs, p):
    if not xs:
        return None
    s = sorted(xs)
    i = min(len(s) - 1, max(0, int(round((p / 100.0) * (len(s) - 1)))))
    return round(s[i], 4)


def beyond_spaces(step):
    if step < 0.0:
        return -step / 2.0
    if step > 8.0:
        return (step - 8.0) / 2.0
    return 0.0


def rows(path):
    data = record_io.load_record(path)
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
            elif str(v[0]).startswith(NOTEHEAD):
                heads[Subject.from_key(o["subject"]).at(Kind.CELL).to_key()
                      ].append(o)
    out = []
    for o in boxes:
        sub = Subject.from_key(o["subject"])
        st = sub.at(Kind.STAFF).to_key()
        cell = sub.at(Kind.CELL).to_key()
        pb = (o.get("detail") or {}).get("bbox_page_px")
        _n, x_c, y_c, w_c, h_c = o["value"]
        sp = cellspace.get(cell)
        step = _staff_step(pb, lines.get(st), spacing.get(st))
        rung_mid = y_c + h_c / 2.0
        over, dists, outward = 0, [], []
        # ⚠️ 3.4g-2 SIGNED HALF. Which side of the rung the head stands on:
        # + = FARTHER from the staff than the rung (the side a ledger run
        # grows towards), - = between the rung and the staff. The canonical
        # cell frame has y growing DOWN the page, so for a rung above the
        # staff "outward" is up (smaller y) and below the staff it is down.
        sign = None
        if step is not None and step > 8.0:
            sign = -1.0
        elif step is not None and step < 0.0:
            sign = 1.0
        for hh in heads.get(cell, ()):
            _hn, hx, hy, hw, hh_ = hh["value"]
            if min(hx + hw, x_c + w_c) - max(hx, x_c) <= 0.0:
                continue
            over += 1
            if sp:
                dy = ((hy + hh_ / 2.0) - rung_mid) / float(sp)
                dists.append(abs(dy))
                if sign is not None:
                    outward.append(sign * dy)
        out.append(dict(
            id=o["id"], subject=o["subject"], cell=cell, staff=st,
            step=step,
            beyond=None if step is None else beyond_spaces(step),
            line_gap=None if step is None else
            min(abs(step - t) for t in LINE_STEPS) / 2.0,
            h_spaces=(h_c / float(sp)) if sp else None,
            heads_in_cell=len(heads.get(cell, ())),
            heads_over=over,
            head_dist=min(dists) if dists else None,
            head_outward_max=max(outward) if outward else None,
        ))
    return out


def kept_by_the_shipped_rules(rs):
    """Outside the band, off every line by more than TOL, rung-thick."""
    return [r for r in rs
            if r["step"] is not None
            and r["beyond"] > 0.0
            and r["line_gap"] > TOL
            and not ((r["h_spaces"] or 0.0) > TALL)]


def summarise(rs, name):
    kept = kept_by_the_shipped_rules(rs)
    d_kept = [r["head_dist"] for r in kept if r["head_dist"] is not None]
    inside = [r for r in rs if r["step"] is not None and r["beyond"] == 0.0]
    d_inside = [r["head_dist"] for r in inside if r["head_dist"] is not None]
    tall = [r for r in rs if (r["h_spaces"] or 0.0) > TALL]
    return {
        "record": name,
        "n_ledger_boxes": len(rs),
        "kept_by_the_shipped_rules": len(kept),
        "kept_with_no_head_x_overlapping": sum(
            1 for r in kept if r["heads_over"] == 0),
        "kept_in_a_cell_with_no_head_at_all": sum(
            1 for r in kept if r["heads_in_cell"] == 0),
        "head_distance_spaces_over_the_kept_rungs": {
            k: pct(d_kept, v) for k, v in
            (("p5", 5), ("p25", 25), ("p50", 50), ("p75", 75), ("p90", 90),
             ("p95", 95), ("p99", 99), ("max", 100))},
        "n_kept_with_a_distance": len(d_kept),
        "head_distance_hist_kept_spaces": {
            f"{k:.1f}": v for k, v in sorted(collections.Counter(
                round(d * 2) / 2.0 for d in d_kept).items())},
        # ⚠️ THE CONTROL POPULATION: the boxes INSIDE the band, which Sean's
        # first convention says cannot be rungs at all. If their head
        # distances looked like the kept rungs', the second rule would be
        # measuring nothing the first does not already say.
        "head_distance_spaces_over_the_inside_the_band_boxes": {
            k: pct(d_inside, v) for k, v in
            (("p50", 50), ("p95", 95), ("max", 100))},
        "inside_the_band_with_no_head_x_overlapping": sum(
            1 for r in inside if r["heads_over"] == 0),
        "n_inside_the_band": len(inside),
        "no_cell_staff_space": sum(1 for r in rs if r["h_spaces"] is None),
        "tall_boxes": {
            "n": len(tall),
            "with_a_head_x_overlapping": sum(
                1 for r in tall if r["heads_over"] > 0),
            "head_distance_spaces": [
                None if r["head_dist"] is None else round(r["head_dist"], 3)
                for r in tall],
            "height_spaces": [round(r["h_spaces"], 3) for r in tall],
            "beyond_spaces": [None if r["beyond"] is None else
                              round(r["beyond"], 3) for r in tall],
        },
    }


def far_heads(rs, t=2.75):
    """⚠️ 3.4g-2: the kept rungs the symmetric head tolerance would REFUSE,
    split by whether an x-overlapping head stands FARTHER OUT than the rung.

    A ledger run grows from the staff towards its note, so the inner rungs of
    a long run are far from the head and the head is OUTWARD of them. If the
    refused tail is mostly `outward`, the symmetric rule is cutting ladders;
    if it is mostly `inward_or_none`, it is cutting junk.
    """
    kept = kept_by_the_shipped_rules(rs)
    far = [r for r in kept if r["head_dist"] is None or r["head_dist"] > t]
    out = collections.Counter()
    for r in far:
        o = r.get("head_outward_max")
        if o is not None and o > t:
            out["a_head_farther_out_than_the_rung"] += 1
        elif r["head_dist"] is None:
            out["no_head_x_overlapping"] += 1
        else:
            out["heads_only_between_the_rung_and_the_staff"] += 1
    ow = [r["head_outward_max"] for r in far
          if r.get("head_outward_max") is not None]
    return {"tolerance": t, "kept_rungs_beyond_it": len(far),
            "by_side": dict(out),
            "outward_distance_of_those_with_one": {
                k: pct(ow, v) for k, v in (("p50", 50), ("p95", 95),
                                           ("max", 100))}}


def sweep(rs, name, tols=(0.5, 1.0, 1.5, 2.0, 2.5, 2.75, 3.0, 4.0)):
    """Reach of the FOUR rules in the order 3.4g-2 ships them, per tolerance.

    inside_the_staff -> tall_not_a_rung (AND no head) -> no_head_on_the_rung
    -> on_a_staff_line -> kept.
    """
    out = {}
    for t in tols:
        c = collections.Counter()
        for r in rs:
            if r["step"] is None:
                c["ABSTAINED"] += 1
                continue
            near = (r["head_dist"] is not None and r["head_dist"] <= t)
            if r["beyond"] == 0.0:
                c["inside_the_staff"] += 1
            elif (r["h_spaces"] or 0.0) > TALL and not near:
                c["tall_not_a_rung"] += 1
            elif not near:
                c["no_head_on_the_rung"] += 1
            elif r["line_gap"] <= TOL:
                c["on_a_staff_line"] += 1
            else:
                c["kept"] += 1
        out[f"{t:.2f}"] = dict(c)
    return out


if __name__ == "__main__":
    out = []
    for p in sys.argv[1:]:
        rs = rows(p)
        dest = (Path(__file__).resolve().parents[1] / "out" /
                f"ledger-head-rows-{Path(p).name.split('.')[0]}.json")
        dest.write_text(json.dumps(rs))
        s = summarise(rs, Path(p).name)
        s["reach_sweep_by_head_tolerance_spaces"] = sweep(rs, Path(p).name)
        s["kept_rungs_past_the_head_tolerance"] = far_heads(rs)
        s["rows_cached_at"] = str(dest)
        out.append(s)
    print(json.dumps(out, indent=1))
