"""Does the direction reader work on a SCAN? The benchmark cannot say.

`FINDINGS.md` measures the reader on pages LilyPond engraved, where every note
is known by construction and the ink is perfect. It says in as many words that
nothing had met broken ink, foxing or bleed-through, and that the expected
failure — silence rather than nonsense — was a prediction and not a measurement.
This is the measurement.

## What stands in for truth, and what it is worth

A scan has no MusicXML. Two things substitute, and neither is truth on its own:

- **The PDF's own text layer.** Some IMSLP scans carry one, and it names what is
  printed and where. It is another OCR's opinion rather than ground truth — this
  edition's layer reads `Fag:` for `Fag.` and emits `tJ` and `JJ` out of
  noteheads — so it corroborates, it does not adjudicate. Where both readers
  independently say `sempre` at the same spot on the page, that is strong; where
  they disagree, the crop decides.
- **The crops.** Every accepted word is written out as a PNG so a person can
  look at what the reader was looking at. That is the only real arbiter here,
  and it is why `--crops-dir` is not optional in practice.

## What it reports

    precision   accepted words that the text layer corroborates in place
    recall      text-layer direction words inside a system that we accepted
    silence     candidates proposed and refused, on pages with no directions

**Recall against a text layer is a FLOOR, not a rate.** The layer misses words
too, and it also holds margin labels and titles this reader deliberately never
looks at, so its raw count is not the denominator. The report separates
text-layer words that fall inside a staff's own x-range — the only ones this
reader could ever propose — from the rest.

    python3 benchmarks/omr-direction-text-2026-09/eval_on_scan.py \\
        library/editions/beethoven/symphony-5-op67/beethoven--*imslp575951.pdf \\
        --pages 16 22 39 78 84 --crops-dir /tmp/scan-crops
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2
import fitz
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.omr.direction_lexicon import lookup            # noqa: E402
from tools.omr.direction_text import (crop_for, default_readers,  # noqa: E402
                                      find_candidates, read_directions)
from tools.omr.preprocessing import render_page           # noqa: E402
from tools.omr.staff_detector import detect_staves        # noqa: E402
from tools.omr.transcribe import DEFAULT_WEIGHTS, transcribe  # noqa: E402

#: How close a text-layer word must sit to an accepted reading to count as the
#: same mark, in staff spaces. Generous: the two readers box a word
#: differently, and the question is "is this the same printed thing", not
#: "do the boxes agree".
#:
#: MATCHING IS 2-D, and that is not a detail. Matching on x alone looked
#: plausible and reported zero corroboration on a page where both readers had
#: independently found the same two `cresc.` — a page number four staves away
#: happened to share their column. On a 20-staff page every x is crowded.
MATCH_SPACES = 3.0


def _near(ax, ay, word, spacing):
    """Distance in staff spaces from `(ax, ay)` to a text-layer word's box."""
    wx, wy = (word[1] + word[3]) / 2.0, (word[2] + word[4]) / 2.0
    return ((ax - wx) ** 2 + (ay - wy) ** 2) ** 0.5 / spacing


def text_layer_words(pdf: Path, page_index: int, dpi: int):
    """`(text, x0, y0, x1, y1)` in PAGE PIXELS at `dpi`, for every word."""
    with fitz.open(pdf) as doc:
        scale = dpi / 72.0
        return [(w[4], w[0] * scale, w[1] * scale, w[2] * scale, w[3] * scale)
                for w in doc[page_index].get_text("words")]


def run_page(pdf: Path, page_index: int, *, weights: str, dpi: int,
             crops_dir: Path | None) -> dict:
    result = transcribe(pdf_path=pdf, pages=[page_index], weights=weights,
                        dpi=dpi, contextual=False, progress=False,
                        read_direction_text=True)
    page_dict = result["pages"][0]
    info = (result.get("direction_text") or {}).get("pages", [{}])[0]

    accepted = []
    for system in page_dict.get("systems", []):
        for staff in system.get("staves", []):
            for measure in staff.get("measures", []):
                for entry in measure.get("direction_texts", []) or []:
                    accepted.append({**entry, "staff": staff["staff_index"],
                                     "measure": measure["measure_index"]})

    page = render_page(pdf, page_index, dpi=dpi)
    pws = detect_staves(page)
    spacing = float(np.median([s.line_spacing_px for s in pws.staves])) \
        if pws.staves else 40.0

    # Text-layer words the reader could ever have proposed: inside some staff's
    # own x-range. The margin and the page furniture are excluded by design.
    x_ranges = [(s.x_start, s.x_end) for s in pws.staves]
    layer = text_layer_words(pdf, page_index, dpi)
    inside = [w for w in layer
              if any(x0 <= (w[1] + w[3]) / 2 <= x1 for x0, x1 in x_ranges)]
    layer_directions = [w for w in inside if lookup(w[0])]

    # Every candidate, with what the OCR made of it — the three-way split
    # between "never proposed", "proposed and read as nothing" and "read" is
    # the whole diagnosis on a scan, and the summary counts hide it.
    candidates = find_candidates(pws, page_dict)
    by_rung: dict[str, list[str]] = {}
    if candidates:
        crops = [crop_for(page, c, spacing) for c in candidates]
        for name, fn in default_readers():
            try:
                by_rung[name] = list(fn(crops))
            except Exception as exc:                        # noqa: BLE001
                print(f"   rung {name} failed: {exc}", file=sys.stderr)
    per_candidate = []
    for i, c in enumerate(candidates):
        reads = {name: (texts[i] if i < len(texts) else "")
                 for name, texts in by_rung.items()}
        hit = next((r for r in reads.values() if r and lookup(r)), "")
        any_text = next((r for r in reads.values() if r), "")
        per_candidate.append(
            {"staff": c.staff_index, "measure": c.measure_index,
             "placement": c.placement, "y": c.bbox_page[1], "x": c.x_page,
             "reads": reads, "ocr": hit or any_text,
             "verdict": ("accepted" if hit else
                         "refused" if any_text else "unread")})

    # Corroborate each accepted reading against the layer, in TWO dimensions.
    for a in accepted:
        ax = a["x_page"]
        ay = next((c["y"] for c in per_candidate
                   if abs(c["x"] - ax) < 2 and c["verdict"] == "accepted"), None)
        if ay is None:
            ay = 0.0
        best, best_d = None, 1e9
        for w in layer:
            d = _near(ax, ay, w, spacing)
            if d < best_d:
                best, best_d = w, d
        a["layer_nearest"] = best[0] if best else None
        a["layer_dist_spaces"] = round(best_d, 2) if best else None
        a["corroborated"] = bool(best and best_d <= MATCH_SPACES
                                 and lookup(best[0]) is not None)

    # And the reverse: which layer directions did we get? Compared against
    # every CANDIDATE, not just the accepted ones, so a word we proposed and
    # failed to read is not counted as one we never saw.
    def _seen(w):
        return any(_near(c["x"], c["y"], w, spacing) <= MATCH_SPACES
                   for c in per_candidate)

    missed = [w for w in layer_directions if not _seen(w)]
    proposed_unread = [w[0] for w in layer_directions
                       if _seen(w) and not any(
                           _near(a["x_page"], 0, w, spacing) <= MATCH_SPACES
                           for a in accepted)]

    if crops_dir is not None and pws.staves:
        crops_dir.mkdir(parents=True, exist_ok=True)
        for i, c in enumerate(find_candidates(pws, page_dict)):
            cv2.imwrite(str(crops_dir / f"p{page_index:03d}-c{i:03d}"
                                        f"-s{c.staff_index:02d}-{c.placement}.png"),
                        crop_for(page, c, spacing))

    return {
        "page": page_index,
        "staves": len(pws.staves),
        "candidates": info.get("n_candidates", 0),
        "read": info.get("n_read", 0),
        "accepted": accepted,
        "refused": info.get("rejected", []),
        "per_candidate": per_candidate,
        "layer_direction_words_inside_systems": [w[0] for w in layer_directions],
        "never_proposed_vs_layer": [w[0] for w in missed],
        "proposed_but_unread_vs_layer": proposed_unread,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pdf", type=Path)
    ap.add_argument("--pages", nargs="+", type=int, required=True)
    ap.add_argument("--weights", default=DEFAULT_WEIGHTS)
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--crops-dir", type=Path, default=None)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args(argv)

    rows = []
    for page_index in args.pages:
        row = run_page(args.pdf, page_index, weights=args.weights, dpi=args.dpi,
                       crops_dir=args.crops_dir)
        rows.append(row)
        ok = sum(1 for a in row["accepted"] if a["corroborated"])
        print(f"\n=== page {page_index}  {row['staves']} staves  "
              f"{row['candidates']} candidates, {row['read']} read, "
              f"{len(row['accepted'])} accepted ({ok} corroborated)", flush=True)
        for a in row["accepted"]:
            mark = "ok " if a["corroborated"] else "?? "
            print(f"   {mark} staff {a['staff']:2d} m{a['measure']:<3d} "
                  f"{a['text']!r:24s} layer nearest {a['layer_nearest']!r} "
                  f"@{a['layer_dist_spaces']} spaces")
        verdicts = {}
        for c in row["per_candidate"]:
            verdicts[c["verdict"]] = verdicts.get(c["verdict"], 0) + 1
        print(f"   candidate verdicts: {verdicts}")
        rung_counts = {}
        for c in row["per_candidate"]:
            for name, txt in c.get("reads", {}).items():
                if txt and lookup(txt):
                    rung_counts[name] = rung_counts.get(name, 0) + 1
        print(f"   lexicon hits per rung: {rung_counts}")
        refused = [c["ocr"] for c in row["per_candidate"]
                   if c["verdict"] == "refused"]
        if refused:
            print(f"   read but refused by the lexicon: {refused[:12]}")
        print(f"   text layer inside systems: "
              f"{row['layer_direction_words_inside_systems']}")
        print(f"   proposed but unread: {row['proposed_but_unread_vs_layer']}")
        print(f"   never proposed:      {row['never_proposed_vs_layer']}")

    n_acc = sum(len(r["accepted"]) for r in rows)
    n_ok = sum(1 for r in rows for a in r["accepted"] if a["corroborated"])
    n_layer = sum(len(r["layer_direction_words_inside_systems"]) for r in rows)
    n_missed = sum(len(r["never_proposed_vs_layer"]) for r in rows)
    n_unread = sum(len(r["proposed_but_unread_vs_layer"]) for r in rows)
    n_cand = sum(len(r["per_candidate"]) for r in rows)
    n_bad = sum(1 for r in rows for c in r["per_candidate"]
                if c["verdict"] == "refused")
    print(f"\n{'':-<70}")
    print(f"accepted {n_acc}, corroborated by the text layer {n_ok}")
    print(f"text-layer direction words inside systems {n_layer}: "
          f"{n_unread} proposed but unread, {n_missed} never proposed")
    print(f"candidates {n_cand}, of which read-but-refused {n_bad} "
          f"(the false-positive channel)")
    print("READ THE CROPS before believing either number — the layer is "
          "another OCR, not truth.")
    if args.out:
        args.out.write_text(json.dumps(rows, indent=1, default=str) + "\n")
        print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
