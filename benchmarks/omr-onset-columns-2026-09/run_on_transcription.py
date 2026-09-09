"""Run `adjudicate_event` + `adjudicate_onset_column` on REAL committed ink.

⚠️ THIS EXISTS BECAUSE THIS CONTAINER CANNOT READ A PAGE. `omr-weights/` and
`library/` are gitignored, so the staged pipeline's own GATHER stage cannot
run here (CLAUDE.md, "cloud session capabilities"). What IS committed is a
whole transcription — Brahms 1 / Breitkopf p1-p3, 83 staves, 10,523
detections — so the log is built from that instead: the same quantities
`gather_detections` and `gather_glyph_families` emit, from the same detector
output, at the same subject addresses.

⚠️ It is a harness, NOT a second gatherer. It emits four quantities and no
more, and nothing in the tree imports it. The decision under test is the
registered one, reached through `adjudicate.run`.
"""
from __future__ import annotations

import argparse
import json
import random
import statistics
from pathlib import Path

from tools.omr.staged import adjudicate
from tools.omr.staged import record as R
from tools.omr.staged.gather import FRAME_PAGE, frame_cell
from tools.omr.staged.record import Log, Q, READERS

NOTEHEAD = "notehead"
REST = "rest"


def _circular_null(xs: list, rng: random.Random) -> dict:
    """A CIRCULAR SHIFT of one staff-bar's page x values, as the null control.

    ⚠️ THE NULL IS THE RESULT HERE, NOT AN AFTERTHOUGHT. A conductor's page is
    dense, so on a crowded bar most alignment is available BY CHANCE, and a
    corroboration rate quoted without a null is a measure of how many staves
    the page prints.

    ⚠️ It is a circular shift rather than a re-draw ON PURPOSE, and that makes
    it the STRONGER control: a re-draw destroys each staff's own rhythmic
    spacing along with the cross-staff phase, so beating it would only show
    that music is not uniform noise. A shift keeps every within-staff interval
    and every chord exactly as printed and destroys the PHASE alone — so what
    it tests is precisely the claim: that the staves agree about WHERE in the
    bar the instants are.
    """
    if len(xs) < 2:
        return {x: x for x in xs}
    lo, hi = min(xs), max(xs)
    span = hi - lo
    if span <= 0:
        return {x: x for x in xs}
    u = rng.uniform(0.0, span)
    return {x: lo + ((x - lo) + u) % span for x in xs}


def build_log(doc: dict, page_limit: int | None = None,
              null_seed: int | None = None) -> Log:
    log = Log()
    rng = random.Random(null_seed) if null_seed is not None else None
    for pi, page in enumerate(doc["pages"]):
        if page_limit is not None and pi >= page_limit:
            break
        p = page.get("page_index", pi)
        for si, sysm in enumerate(page["systems"]):
            for sti, staff in enumerate(sysm["staves"]):
                geom = staff.get("staff_geometry") or {}
                spacing = geom.get("line_spacing_px")
                sub = R.staff(p, si, sti)
                if spacing:
                    log.observe(sub, Q.STAFF_SPACING, float(spacing),
                                reader=READERS.GEOMETRY, frame=FRAME_PAGE)
                for m in staff.get("measures", ()):
                    ci = m["measure_index"]
                    shift = None
                    if rng is not None:
                        centres = [b[0] + b[2] / 2.0
                                   for b in (d.get("bbox_page")
                                             for d in m.get("detections", ()))
                                   if b]
                        shift = _circular_null(centres, rng)
                    for gi, d in enumerate(m.get("detections", ())):
                        g = R.glyph(p, si, sti, ci, gi)
                        name = d["class"]
                        bb = d.get("bbox") or [0, 0, 0, 0]
                        conf = float(d.get("confidence") or 0.0)
                        detail = {"category": d.get("category")}
                        pb = d.get("bbox_page")
                        if pb:
                            x, y, w, h = pb
                            xc = x + w / 2.0
                            if shift is not None:
                                xc = shift.get(xc, xc)
                            detail.update(
                                bbox_page_px=[x, y, x + w, y + h],
                                x_center_page=xc,
                                y_center_page=y + h / 2.0)
                        else:
                            detail["frame_note"] = "no page box"
                        log.observe(g, Q.GLYPH_BOX,
                                    (name, bb[0], bb[1], bb[2] - bb[0],
                                     bb[3] - bb[1]),
                                    reader=READERS.DETECTOR,
                                    frame=frame_cell(ci), score=conf, **detail)
                        if name.startswith(NOTEHEAD):
                            log.observe(g, Q.NOTEHEAD_CLASS, name,
                                        reader=READERS.DETECTOR,
                                        frame=frame_cell(ci), score=conf)
                        elif name.lower().startswith(REST):
                            log.observe(g, Q.REST, name,
                                        reader=READERS.DETECTOR,
                                        frame=frame_cell(ci), score=conf)
    return log


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("transcription", type=Path)
    ap.add_argument("--pages", type=int, default=None)
    ap.add_argument("--json-out", type=Path, default=None)
    ap.add_argument("--null", type=int, default=None,
                    help="seed: circular-shift each staff-bar's page x, the "
                         "null control")
    a = ap.parse_args()

    doc = json.loads(a.transcription.read_text())
    log = build_log(doc, a.pages, null_seed=a.null)
    adjudicate.run(log, order=(Q.EVENT, Q.ONSET_COLUMN))

    cols = [v for v in log.all_verdicts() if v.quantity == Q.ONSET_COLUMN]
    decided = [v for v in cols if v.value is not None]
    print(f"{Q.ONSET_COLUMN}: {len(cols)} subjects, {len(decided)} decided, "
          f"{len(cols) - len(decided)} abstained")
    for v in cols:
        if v.value is None:
            print(f"  {v.subject.to_key()}  ABSTAIN {v.reason}")

    residuals, n_col, n_corr, n_alone, n_bars = [], 0, 0, 0, 0
    summary = []
    for v in decided:
        d = v.detail
        n_col += d["n_columns"]; n_corr += d["n_corroborated"]
        n_alone += d["n_alone"]; n_bars += d["n_bars"]
        for bar in v.value["bars"]:
            for c in bar.get("columns", ()):
                if c["n_witness"] > 1:
                    residuals.append(c["residual_spaces"])
        summary.append({"subject": v.subject.to_key(), **d})
        print(f"  {v.subject.to_key()}  bars={d['n_bars']} "
              f"columns={d['n_columns']} corroborated={d['n_corroborated']} "
              f"alone={d['n_alone']} median_residual={d['median_residual_spaces']}")

    print(f"\nPOOLED: {n_bars} bars, {n_col} columns, {n_corr} corroborated "
          f"({n_corr / n_col:.3f}), {n_alone} standing alone")
    if residuals:
        print(f"  residual spaces: median {statistics.median(residuals):.4f}, "
              f"mean {statistics.mean(residuals):.4f}, max {max(residuals):.4f}")

    evs = [v for v in log.all_verdicts() if v.quantity == Q.EVENT]
    print(f"  (Q.EVENT: {len(evs)} cells, "
          f"{sum(1 for v in evs if v.value is not None)} decided)")

    if a.json_out:
        a.json_out.parent.mkdir(parents=True, exist_ok=True)
        a.json_out.write_text(json.dumps(
            {"systems": summary,
             "pooled": {"bars": n_bars, "columns": n_col,
                        "corroborated": n_corr, "alone": n_alone,
                        "median_residual_spaces":
                            round(statistics.median(residuals), 4)
                            if residuals else None}}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
