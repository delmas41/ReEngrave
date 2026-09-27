"""ROADMAP 2.7 — price the accidental GATHER quantity on a SAVED record.

`Q.ACCIDENTAL_STAFF_POSITION` is a GATHER row, and every acceptance record was
gathered before it existed, so no saved record carries one. `readjudicate` /
`reexport_arm` replay GATHER rows and are structurally blind to a GATHER
change (CLAUDE.md §6b). This script is the bridge: it RECOMPUTES the one new
row off rows the record already holds, then re-decides the whole record.

⚠️⚠️ THE ARITHMETIC IS IMPORTED, NOT RESTATED. `gather.gather_accidental_
positions` computes `(anchor_y - top_y) / half_step` from a detection's
canonical box and the cell's `_cell_grid`. Everything but `top_y` is on the
record exactly:

  * the canonical box is `Q.GLYPH_BOX`'s value, integers straight off the
    detector (`yolo_detector.detect` rounds before it files);
  * `half_step` is `Q.CELL_STAFF_SPACE`'s own `detail.half_step`;
  * the class -> alteration and class -> anchor tables are `gather`'s own
    `_alteration_of` and `_ANCHOR_FRACTION`, imported.

`top_y` (the cell's top line, canonical) is NOT filed. It is recovered two
ways and the two are reported against each other:

  * **from a notehead** in the same cell: `gather_notehead_positions` filed
    `pos = (y + h//2 - top_y) / half_step`, so `top_y = y + h//2 - pos *
    half_step` EXACTLY (the float identity, not an estimate);
  * **from the page** where the cell has no notehead: `Q.STAFF_LINES[0]`
    mapped into the cell by the cell's own upscale, derived from any glyph's
    page box against its canonical box. This is the weaker route — the
    cell's canonical lines are measured in the cell and need not be the page
    lines rescaled — and the control below prices it on every cell where
    BOTH routes are available.

A cell whose `Q.CELL_STAFF_SPACE` says `lines < 2` has no grid, and the real
gather files no accidental row there either (`_cell_grid` returns None).

⚠️ The rows are appended AFTER the replayed GATHER rows, so their ids differ
from a real gather's. No decision reads a row by id order, and step 5 of the
landing (one real gather of Litolff p3) is the control that the recompute
matches what GATHER itself files.

    python3 benchmarks/omr-accidental-2026-09/probe/regather_accidentals.py \\
        --record <rec.json> --label litolff --mode arm --out-dir <dir>

`--mode base` re-decides the record with NO accidental rows (the stage
disabled). `--root <tree>` imports `tools` from another tree, which is how
the pre-merge `origin/main` control is run on the same record.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def _args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--mode", choices=("base", "arm", "rows-only"),
                    required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--root", default=str(ROOT),
                    help="the tree whose `tools` package is imported")
    ap.add_argument("--save-record", action="store_true",
                    help="also write the re-decided record (pooled, via "
                         "record_io) for the crop and trace tools")
    ap.add_argument("--break-control", action="store_true",
                    help="perturb ONE recomputed row by +3 positions, so the "
                         "verdict comparison must see a difference")
    return ap.parse_args()


def recompute_rows(rec, G):
    """`[(glyph_key, pos_float, detail)]` — `gather_accidental_positions`'
    rows, off a saved record. Also returns the control figures."""
    boxes = collections.defaultdict(list)     # cell -> [(gi, value, detail)]
    unit = {}                                 # cell -> (half_step, lines)
    npos = {}                                 # glyph -> notehead position
    cbox = {}
    staff_lines = {}
    for o in rec["observations"]:
        q = o["quantity"]
        if q == "glyph_box":
            sub = o["subject"]
            cell = "cell/" + "/".join(sub.split("/")[1:5])
            boxes[cell].append((int(sub.rsplit("/", 1)[1]), o["value"],
                                o.get("detail") or {}, o.get("score")))
        elif q == "cell_staff_space":
            d = o.get("detail") or {}
            if "half_step" in d:
                unit[o["subject"]] = (float(d["half_step"]),
                                      int(d.get("lines") or 0))
        elif q == "notehead_staff_position":
            npos[o["subject"]] = float(o["value"])
        elif q == "cell_box":
            cbox[o["subject"]] = o["value"]
        elif q == "staff_lines":
            staff_lines[o["subject"]] = o["value"]

    rows = []
    ctl = collections.Counter()
    top_diffs = []
    for cell, items in boxes.items():
        u = unit.get(cell)
        accs = [(gi, v, d, s) for gi, v, d, s in items
                if isinstance(v, (list, tuple)) and len(v) == 5
                and G._alteration_of(str(v[0])) is not None]
        if not accs:
            continue
        if u is None or u[1] < 2 or u[0] <= 0:
            ctl["no_grid_cells"] += 1
            ctl["no_grid_glyphs"] += len(accs)
            continue
        half_step = u[0]
        # ── top_y from a notehead: the exact identity ────────────────────
        tops = []
        for gi, v, d, _s in items:
            key = f"glyph/{cell[5:]}/{gi}"
            if key in npos and isinstance(v, (list, tuple)) and len(v) == 5:
                y, h = int(v[2]), int(v[4])
                tops.append((y + h // 2) - npos[key] * half_step)
        # ── top_y from the page, the weaker route ─────────────────────────
        page_top = None
        staff = "staff/" + "/".join(cell.split("/")[1:4])
        lines = staff_lines.get(staff)
        cb = cbox.get(cell)
        ups = [float(v[3]) / (d["bbox_page_px"][2] - d["bbox_page_px"][0])
               for _gi, v, d, _s in items
               if d.get("bbox_page_px") and isinstance(v, (list, tuple))
               and len(v) == 5
               and d["bbox_page_px"][2] > d["bbox_page_px"][0]]
        if lines and cb and ups:
            ups.sort()
            up = ups[len(ups) // 2]
            page_top = (float(lines[0]) - float(cb[1])) * up
        if tops:
            top_y = tops[0]
            ctl["top_from_notehead_cells"] += 1
            if page_top is not None:
                top_diffs.append((page_top - top_y) / half_step)
        elif page_top is not None:
            top_y = page_top
            ctl["top_from_page_cells"] += 1
        else:
            ctl["no_top_cells"] += 1
            ctl["no_top_glyphs"] += len(accs)
            continue
        for gi, v, d, score in accs:
            name, x, y, w, h = str(v[0]), int(v[1]), int(v[2]), int(v[3]), \
                int(v[4])
            frac = G._ANCHOR_FRACTION.get(name.lower(), 0.5)
            anchor_y = y + h * frac
            pos_float = (anchor_y - top_y) / half_step
            centre_pos = ((y + h // 2) - top_y) / half_step
            rows.append((f"glyph/{cell[5:]}/{gi}", pos_float, dict(
                alteration=G._alteration_of(name), detector_class=name,
                anchor_fraction=frac, box_centre_position=centre_pos,
                residual=abs(pos_float - round(pos_float)),
                rounded=int(round(pos_float)),
                x0=float(x), x1=float(x + w), y0=float(y), y1=float(y + h),
                confidence=float(score) if score is not None else None,
                top_from=("notehead" if tops else "page"))))
    td = sorted(abs(t) for t in top_diffs)
    ctl_out = dict(ctl)
    ctl_out["page_vs_notehead_top_positions"] = {
        "n": len(td),
        "median": td[len(td) // 2] if td else None,
        "p90": td[int(len(td) * 0.9)] if td else None,
        "max": td[-1] if td else None,
    }
    return rows, ctl_out


def verdict_digest(record):
    """(subject, quantity) -> the STANDING verdict's shape, for N/N compares.

    ⚠️ The standing one: a superseded verdict is kept on the record and a
    second row at one subject is how supersession shows. Compared as
    `(outcome, value, reason, decider)` — ids are renumbered by every replay.
    """
    superseded = {v.get("supersedes") for v in record["verdicts"]
                  if v.get("supersedes")}
    out = {}
    for v in record["verdicts"]:
        if v["id"] in superseded:
            continue
        out[f'{v["subject"]}|{v["quantity"]}'] = json.dumps(
            [v.get("outcome"), v.get("value"), v.get("reason"),
             v.get("decider")], sort_keys=True, default=str)
    return out


def main() -> int:
    a = _args()
    sys.path.insert(0, a.root)
    from tools.omr.staged import gather as G
    from tools.omr.staged import pipeline, export as E
    from tools.omr.staged.record import Q, READERS, Subject
    from tools.omr.staged.record_io import load_record
    from tools.omr.staged.review.rerun import rebuild_gather

    out_dir = Path(a.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    doc = load_record(a.record)
    rec = doc["record"] if "record" in doc else doc
    print(f"loaded {a.record} in {time.time() - t0:.0f}s", flush=True)

    summary = {"label": a.label, "mode": a.mode, "root": a.root,
               "record": a.record,
               "record_md5": hashlib.md5(Path(a.record).read_bytes())
               .hexdigest()}
    if a.mode in ("arm", "rows-only"):
        rows, ctl = recompute_rows(rec, G)
        summary["recompute"] = {"rows": len(rows), **ctl,
                                "by_class": dict(collections.Counter(
                                    r[2]["detector_class"] for r in rows))}
        print(json.dumps(summary["recompute"], indent=1), flush=True)
        if a.mode == "rows-only":
            (out_dir / f"{a.label}-rows.json").write_text(json.dumps(
                [[k, p, d] for k, p, d in rows]))
            (out_dir / f"{a.label}-rows-summary.json").write_text(
                json.dumps(summary, indent=1))
            return 0
    log, _ = rebuild_gather(rec)
    if a.mode == "arm":
        for i, (key, pos, detail) in enumerate(rows):
            if a.break_control and i == 0:
                pos += 3.0
                summary["break_control_perturbed"] = key
            log.observe(Subject.from_key(key), Q.ACCIDENTAL_STAFF_POSITION,
                        pos, reader=READERS.GEOMETRY,
                        frame=f"cell:{key.split('/')[4]}", **detail)
    t1 = time.time()
    pipeline.decide(log, progress=False)
    summary["decide_seconds"] = round(time.time() - t1)
    result = {"record": log.to_json(), "summary": log.summary()}
    xml, report = E.to_musicxml(result)
    summary["musicxml_md5"] = hashlib.md5(xml.encode()).hexdigest()
    summary["notes_in_file"] = xml.count("<note")
    summary["accidental_elements"] = xml.count("<accidental")
    summary["alter_elements"] = xml.count("<alter>")
    summary["written"] = report.get("written")
    summary["notes_not_written"] = report.get("notes_not_written")
    summary["status_census"] = report.get("status_census")
    summary["accidental_reading"] = report.get("accidental_reading")
    summary["family_refusals"] = report.get("family_refusals")
    (out_dir / f"{a.label}-{a.mode}.musicxml").write_text(xml)
    (out_dir / f"{a.label}-{a.mode}-verdicts.json").write_text(
        json.dumps(verdict_digest(result["record"])))
    # the owner verdicts and the accidental verdicts, whole, for the gate
    keep = [v for v in result["record"]["verdicts"]
            if v["quantity"] in ("accidental_owner", "accidental",
                                 "accidental_is_not_an_accidental")]
    (out_dir / f"{a.label}-{a.mode}-accidental-verdicts.json").write_text(
        json.dumps(keep, default=str))
    if a.save_record:
        from tools.omr.staged.record_io import dumps_for_file
        (out_dir / f"{a.label}-{a.mode}.record.json").write_text(
            dumps_for_file({**result, "provenance": doc.get("provenance")},
                           default=str))
    (out_dir / f"{a.label}-{a.mode}-summary.json").write_text(
        json.dumps(summary, indent=1, default=str))
    print(json.dumps({k: summary[k] for k in (
        "decide_seconds", "notes_in_file", "accidental_elements",
        "alter_elements")}), flush=True)
    print(json.dumps(summary["accidental_reading"], indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
