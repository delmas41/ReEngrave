"""THE PROPOSED REPAIR, SCORED ON THE RULE'S OWN TRUTH SET -- not on mine.

`probe_who_is_the_partner.py` measures that the pair rule's dominant victim on
Litolff Beethoven 5 is a stroke whose PARTNER also carries a notehead, and
`probe_who_is_the_partner`'s geometry table measures that no single quantity
`detect_stems` can see separates that population from a real accidental pair
(best single cut 0.823 against a 0.723 base rate, no empty interval anywhere).

So the only discriminator available is the NOTEHEAD, and the staged gather
already holds it: `gather_cv_lines` runs AFTER `gather_detections`
(`gather.py:3276` then `:3291`) and simply does not pass it on.

THE PROPOSAL: keep a stroke that meets a notehead, and drop a pair only where
NEITHER member does.

⚠️⚠️ SCORING THAT ON MY OWN LITOLFF PARTITION WOULD BE CIRCULAR. I defined the
two classes BY notehead overlap, so a notehead gate scores 80/80 there by
construction and the number would mean nothing. This arm therefore scores it
on `benchmarks/omr-phase4-lines/hand-labeled-stems.json` -- a hand count on
four OTHER documents, made before this question was asked, whose counting rule
("one stem per note OR CHORD; the vertical strokes of sharps, naturals and
flats are NOT stems") is exactly the distinction under test.

⚠️ It needs the DETECTOR, so it is not a pure-CV arm and its noteheads are as
good as the weights. Where the detector misses a notehead the gate cannot
protect that stroke -- which is the failure direction that leaves the SHIPPED
behaviour in place, not a new one.

⚠️ NOTHING IN `tools/` IS CHANGED. The gated variant is implemented here.

POSITIVE CONTROL: the three arms must not all agree, or the flag and the gate
are both inert and every number is a clean, believable zero.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))

from tools.omr.line_detection import detect_stems, _staff_line_spacing      # noqa: E402
from tools.omr.measure_extractor import detect_barlines, extract_measures   # noqa: E402
from tools.omr.preprocessing import render_page                             # noqa: E402
from tools.omr.staff_detector import detect_staves                          # noqa: E402
from tools.omr.staff_line_removal import remove_staff_lines                 # noqa: E402
from tools.omr.staged.adjudicators.rhythm import _boxes_overlap             # noqa: E402
from tools.omr.training.line_detection_eval import (                        # noqa: E402
    HAND_STEMS_PATH, SCORE_ROOT, _resolve_cells)

GAP_LINES, MIN_OVERLAP = 0.9, 0.6
WEIGHTS = ("/Users/seanjohnson/Desktop/ReEngrave/omr-weights/"
           "deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt")


def box(d):
    return (float(d.x_canonical), float(d.y_canonical),
            float(d.width_canonical), float(d.height_canonical))


def gated(bs, spacing, heads):
    """`_drop_paired_strokes`, with the ONE change under test: a stroke that
    meets a notehead is kept, and a pair is dropped only where NEITHER member
    meets one."""
    if spacing <= 0 or len(bs) < 2:
        return list(bs)
    max_dx = spacing * GAP_LINES
    cen = [b[0] + b[2] / 2.0 for b in bs]
    top = [b[1] for b in bs]
    bot = [b[1] + b[3] for b in bs]
    on_head = [any(_boxes_overlap(h, b) for h in heads) for b in bs]
    kept = []
    for i in range(len(bs)):
        paired = False
        if not on_head[i]:                       # ← the gate
            for j in range(len(bs)):
                if i == j or abs(cen[i] - cen[j]) > max_dx or on_head[j]:
                    continue
                ov = min(bot[i], bot[j]) - max(top[i], top[j])
                if ov <= 0:
                    continue
                if ov / max(1.0, min(bot[i] - top[i], bot[j] - top[j])) >= MIN_OVERLAP:
                    paired = True
                    break
        if not paired:
            kept.append(bs[i])
    return kept


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--weights", default=WEIGHTS)
    ap.add_argument("--json", default=str(HERE / "out" / "proposed-gate.json"))
    a = ap.parse_args()
    if not Path(a.weights).exists():
        print(f"DEAD: no weights at {a.weights}")
        return 2
    from tools.omr.yolo_detector import YoloDetector
    det = YoloDetector(a.weights)

    data = json.loads(HAND_STEMS_PATH.read_text())
    pages, rows = {}, []
    err = {"on": 0, "off": 0, "gated": 0}
    n_scored = n_heads = 0
    print(f"{'cell':>4} {'score':>14} {'truth':>6} {'ON':>5} {'OFF':>5} "
          f"{'GATED':>6} {'heads':>6}")
    for entry in data["cells"]:
        if entry["stems"] is None:
            continue
        spec = data["scores"][entry["score"]]
        pdf = SCORE_ROOT / spec.split(",")[0]
        if not pdf.exists():
            continue
        key = (entry["score"], entry["dpi"])
        if key not in pages:
            page_index = int(spec.rsplit(" ", 1)[-1])
            pws = detect_barlines(detect_staves(
                render_page(pdf, page_index, dpi=entry["dpi"])))
            cells = extract_measures(pws)
            remove_staff_lines(cells)
            pages[key] = cells
        group = _resolve_cells(pages[key], entry)
        if not group:
            print(f"{entry['n']:>4} {entry['score']:>14}  region not "
                  f"resolvable -- excluded")
            continue
        on = off = gat = nh = 0
        for c in group:
            raw = detect_stems(c, drop_accidental_pairs=False)
            heads = [(float(d.x_canonical), float(d.y_canonical),
                      float(d.width_canonical), float(d.height_canonical))
                     for d in (det.detect(c) or [])
                     if "notehead" in str(getattr(d, "smufl_name", "")).lower()]
            nh += len(heads)
            on += len(detect_stems(c))
            off += len(raw)
            gat += len(gated([box(d) for d in raw], _staff_line_spacing(c),
                             heads))
        t = entry["stems"]
        n_scored += 1
        n_heads += nh
        for k, v in (("on", on), ("off", off), ("gated", gat)):
            err[k] += abs(v - t)
        rows.append({"n": entry["n"], "score": entry["score"], "truth": t,
                     "on": on, "off": off, "gated": gat, "noteheads": nh})
        print(f"{entry['n']:>4} {entry['score']:>14} {t:>6} {on:>5} {off:>5} "
              f"{gat:>6} {nh:>6}")

    print(f"\n== REACH: {n_scored} scoreable cells, {n_heads} noteheads "
          f"detected in them")
    if n_scored == 0:
        print("DEAD: nothing scored.")
        return 2
    if n_heads == 0:
        print("DEAD: the detector found NO noteheads -- the gate cannot be "
              "exercised and `gated` is just `off`.")
        return 2
    if all(r["on"] == r["off"] == r["gated"] for r in rows):
        print("DEAD: POSITIVE CONTROL FAILED -- all three arms agree "
              "everywhere.")
        return 2
    print(f"   summed |error|  ON (shipped) {err['on']:4d}"
          f"   OFF {err['off']:4d}   GATED {err['gated']:4d}")
    for k in ("off", "gated"):
        w = sum(1 for r in rows if abs(r[k] - r["truth"])
                > abs(r["on"] - r["truth"]))
        b = sum(1 for r in rows if abs(r[k] - r["truth"])
                < abs(r["on"] - r["truth"]))
        print(f"   {k.upper():>5} vs ON: worse on {w}, better on {b}, "
              f"equal on {n_scored - w - b}")

    out = {"n_scored": n_scored, "noteheads_detected": n_heads,
           "summed_abs_error": err, "rows": rows, "weights": a.weights}
    Path(a.json).parent.mkdir(parents=True, exist_ok=True)
    Path(a.json).write_text(json.dumps(out, indent=1))
    print(f"\nwrote {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
