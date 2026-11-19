"""ROADMAP 2.321 small test (read-only on product code) -- every bar of the frozen sample where two stems stand at one place.

    OMR_SURYA_KEEP_ALIVE=0 PYTHONPATH=. python3 benchmarks/voice-line-of-time-2026-11/measure.py PLATE OUT.json

STAGED. Replays the 20261117-night slice of PLATE (the lane-report slice of exactly the frozen pages; never the whole record) through
ADJUDICATE..EXPORT on the current tree (`--from adjudicate`, as `lane_report.run_arm` does), with `export._two_stems_bar_verdict` WRAPPED (not
changed) so that the first call per bar -- the one `_decide_two_stems_bars` makes, on the bar's full heads, before 2.89's refusal -- is recorded with
the code's own reason word and a snapshot of the bar's events. After the export, the bars written red are read from the report.
Population: a bar holding two chord events at one place (within one head width) whose heads stand on two different DECIDED stem ids (the pair
`_two_stems_unsafe` / `_stem_pair_streams` look at), or an up-stem and a down-stem event at one place (`_divisi_pairs`).
"""
import collections
import json
import os
import sys
import time

os.environ.setdefault("OMR_SURYA_KEEP_ALIVE", "0")

from tools.omr.staged import export as E               # noqa: E402
from tools.omr.staged import lane_report as LR          # noqa: E402
from tools.omr.staged.record import Q                   # noqa: E402

TAG = "20261117-night"


def head_row(h, pbox):
    return dict(glyph=h.get("glyph"), stem_id=h.get("stem_id"), dir=h.get("stem_direction"), dir_read=h.get("stem_direction_read"),
                beats=h.get("duration_beats"), type=h.get("duration_type"), dots=h.get("dots"),
                guess=(h.get("guess") or {}).get("quantity") if h.get("guess") else None, y=E._head_y(h), w=(h.get("bbox") or [0, 0, 0, 0])[2],
                page_box=pbox.get(h.get("glyph")))


def event_row(e, divisions, pbox):
    r = dict(kind=e.get("kind"), x=float(e.get("x_position") or 0.0), certain=E._event_duration_certain(e))
    try:
        r["units"] = E._event_units(e, divisions)
    except Exception as ex:                               # a value the writer cannot count
        r["units"] = None
        r["units_error"] = type(ex).__name__
    if e.get("kind") == "rest":
        rr = e.get("rest") or {}
        g = e.get("glyph") or rr.get("glyph")
        r.update(rest_class=rr.get("class"), measure_rest=bool(rr.get("measure_rest")), glyph=g, page_box=pbox.get(g), y=E._event_y(e))
    else:
        r["heads"] = [head_row(h, pbox) for h in (e.get("noteheads") or ())]
    return r


def stem_columns(events):
    """Every pair of chord events at one place on two different decided stems: (i, j, read dirs a, read dirs b, decided dirs a, b)."""
    chords = [(k, e) for k, e in enumerate(events) if e.get("kind") == "chord" and e.get("noteheads")]
    widths = [h["bbox"][2] for _, e in chords for h in e["noteheads"] if h.get("bbox")]
    tol = (sum(widths) / len(widths)) if widths else 30.0
    out = []
    for n, (i, a) in enumerate(chords):
        sa = {h.get("stem_id") for h in a["noteheads"]}
        for j, b in chords[n + 1:]:
            if abs(float(a["x_position"]) - float(b["x_position"])) > tol:
                continue
            sb = {h.get("stem_id") for h in b["noteheads"]}
            if None in sa or None in sb or not sa or not sb or sa & sb:
                continue
            out.append(dict(i=i, j=j,
                            read_a=sorted(str(h.get("stem_direction_read")) for h in a["noteheads"]),
                            read_b=sorted(str(h.get("stem_direction_read")) for h in b["noteheads"]),
                            dec_a=sorted(str(h.get("stem_direction")) for h in a["noteheads"]),
                            dec_b=sorted(str(h.get("stem_direction")) for h in b["noteheads"])))
    return out


def main():
    plate, out_path = sys.argv[1], sys.argv[2]
    count_pages = set(LR.load_sample()["plates"][plate]["pages"])
    t0 = time.time()
    from tools.omr.staged.review import rerun as RR
    rec = LR.load_slices(LR.slice_dir(plate, TAG))
    rec["verdicts"] = []
    log, _ = RR.rebuild_gather(rec)
    RR.run_stages(log)
    result = {"record": log.to_json(), "summary": log.summary()}
    del log, rec
    t1 = time.time()
    seen = {}
    cells = {}
    pbox_cache = {}
    orig = E._two_stems_bar_verdict

    def pboxes(r):
        if "x" not in pbox_cache:
            m = {}
            for o in r.obs_of(Q.GLYPH_BOX):
                b = E._page_box_of(o)
                if b:
                    m.setdefault(o["subject"], [round(float(v), 1) for v in b])
            pbox_cache["x"] = m
        return pbox_cache["x"]

    def wrapped(r, run, cell_index, cell, judged, divisions):
        verdict = orig(r, run, cell_index, cell, judged, divisions)
        key = (run.page, run.system, run.staff, cell_index)
        if key in seen or run.page not in count_pages or cell is None or not cell.detections:
            return verdict
        events = E._events(cell)
        cols = stem_columns(events)
        divisi = E._divisi_pairs(events)
        if not cols and not divisi:
            seen[key] = None
            return verdict
        pb = pboxes(r)
        streams = E._voice_split(r, run, cell_index, events, [])
        wq = E._bar_quarters(judged)
        row = dict(plate=plate, page=run.page, system=run.system, staff=run.staff, cell=cell_index, run=run.key, name=run.name,
                   verdict=verdict, n_streams=(len(streams) if streams else 1),
                   want=(int(round(wq * divisions)) if wq is not None else None), divisions=divisions,
                   meter=judged, stem_pair_columns=cols, divisi_pairs=len(divisi),
                   divisi_idx=[[next(k for k, e in enumerate(events) if e is u), next(k for k, e in enumerate(events) if e is d)] for u, d in divisi],
                   events=[event_row(e, divisions, pb) for e in events],
                   directions=[[float(x), k, t] for x, k, t in (cell.directions or [])],
                   cell_box=run.cell_boxes.get(cell_index), prev_box=run.cell_boxes.get(cell_index - 1), next_box=run.cell_boxes.get(cell_index + 1),
                   top_line=run.top_line, spacing=run.spacing)
        seen[key] = row
        cells[key] = cell
        return verdict

    E._two_stems_bar_verdict = wrapped
    try:
        xml, report = E.to_musicxml(result)
    finally:
        E._two_stems_bar_verdict = orig
    red = report.get("bars_written_red") or {}
    red_keys = {(b["page"], b["system"], b["staff"], b["cell"]): b for b in (red.get("bars_list") or [])}
    rows = []
    for key, row in seen.items():
        if row is None:
            continue
        row["red"] = key in red_keys
        if row["red"]:
            b = red_keys[key]
            row["red_detail"] = {k: b.get(k) for k in ("want_quarters", "counted_quarters", "words", "two_voice", "measure", "part", "events") if k in b}
        c = cells[key]
        row["unplaced"] = [dict(sub=u.get("sub"), reason=u.get("reason")) for u in (c.unplaced or [])]
        rows.append(row)
    rows.sort(key=lambda r: (r["page"], r["system"], r["staff"], r["cell"]))
    json.dump(dict(plate=plate, tag=TAG, pages=sorted(count_pages), seconds_stages=round(t1 - t0), seconds_export=round(time.time() - t1),
                   red_bars_total=red.get("bars"), bars_seen=len(seen), rows=rows), open(out_path, "w"), default=str)
    print("%s: %d bars seen, %d in population, %d red total, %.0fs" % (plate, len(seen), len(rows), red.get("bars") or -1, time.time() - t0))


if __name__ == "__main__":
    main()
