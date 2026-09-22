"""Score the STAGED gather's reading against exact page truth.

    python3 benchmarks/omr-staged-engraved-2026-09/staged_reading.py \
        --record out/engraved-p0.record.json \
        --truth  out/fixture/<stem>.pagetruth.json \
        --page 0 --json-out out/reading-staged-p0.json

`tools/omr/score_reading.py` already asks this question of the LEGACY path.
**It is called here unchanged** — not re-implemented — so the staged number and
the legacy number come out of one scorer and are comparable by construction.
What this file adds is the ADAPTER: a staged record projected into the shape
`score_reading.report` reads.

⚠️ **THE ADAPTER MOVES NO COORDINATE.** `gather_detections` already files
`Q.GLYPH_BOX.detail.bbox_page_px` — the record's own page-pixel rectangle,
computed by `gather._page_box` from the cell's `bbox_page_px` and
`upscale_factor`, which is the same conversion the exporter uses. So the adapter
hands `detections_in_page_px` a synthetic cell at the ORIGIN with
`upscale_factor = 1.0` and puts the page box straight in `det["bbox"]`; that
function's arithmetic (`box[0] + (b[0] + b[2]/2)/up`) then returns the record's
own centre, unchanged. Nothing is re-derived from the canonical frame, which is
the one place a second implementation could introduce a frame error.

⚠️ **A GLYPH WITH NO PAGE BOX IS DROPPED AND COUNTED, NEVER DEFAULTED.**
`gather_detections` declines `bbox_page_px` where the cell has no rectangle,
and writes `frame_note` instead. Giving such a glyph the origin would put a
detection at page (0, 0) and charge the precision for it. The count is printed
so a silent loss is impossible.

⚠️ **THE DECISIVE CONTROL IS A FRAME ARM, NOT A COUNT.** `page_truth`'s own
docstring records the failure this measurement is most exposed to: a constant
offset between truth and detections, where the symbol COUNTS agree almost
exactly and nothing matches at any tolerance. A pooled F1 near zero would be
obvious; a frame error of a *fraction* of a staff space would not. So
`--shift-spaces N` translates every detection by N staff spaces and re-scores:
the score must COLLAPSE. A scorer that reports the same number either way is
measuring something that is not position.

⚠️⚠️ **`--apply-ownership` IS THE ONLY ARM COMPARABLE TO THE LEGACY PATH, AND
THE RAW ONE OVER-COUNTS BY DESIGN.** `transcribe` runs
`_dedupe_cross_staff_detections` and DELETES the losing copy of a contested
glyph; the staged path keeps the row and files a `Q.GLYPH_OWNER` verdict, which
`export._place_notes` honours by REFUSING the loser (`owned_by_another_staff`,
2026-09-11 — "a CONTEST is RESOLVED, not relocated"). So a raw GATHER-stage
count contains rows the pipeline has already decided belong to another staff.
Scoring those as false positives measures WHERE the decision lives, not how
well the page was read. This arm drops a glyph whose standing ownership verdict
names a staff other than its own — applying a decision the record already
holds, never making one.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools.omr import score_reading as SR  # noqa: E402


def _rows(record: Dict[str, Any], quantity: str) -> List[Dict[str, Any]]:
    return [o for o in record["record"]["observations"]
            if o.get("quantity") == quantity]


def _page_of(subject: str) -> int | None:
    """`glyph/<page>/<sys>/<staff>/<cell>/<i>` -> page. None if unparseable."""
    parts = (subject or "").split("/")
    if len(parts) < 2:
        return None
    try:
        return int(parts[1])
    except ValueError:
        return None


def _standing_owner(result: Dict[str, Any]) -> Dict[str, str]:
    """`glyph subject -> the staff subject its standing verdict names`.

    ⚠️ RESOLVED THE WAY `export.Record` RESOLVES IT — drop every row a later
    one SUPERSEDES, then take the last of what is left. A second spelling of
    "last wins" is how the exporter and a probe drift apart.
    """
    verdicts = [v for v in result["record"]["verdicts"]
                if v.get("quantity") == "glyph_owner"]
    superseded = {v["supersedes"] for v in verdicts if v.get("supersedes")}
    out: Dict[str, str] = {}
    fallback: Dict[str, str] = {}
    for v in verdicts:
        if v.get("outcome") != "decided":
            continue
        fallback[v["subject"]] = v.get("value")
        if v["id"] not in superseded:
            out[v["subject"]] = v.get("value")
    for k, val in fallback.items():
        out.setdefault(k, val)
    return {k: v for k, v in out.items() if v}


def _own_staff(glyph_subject: str) -> str:
    """`glyph/<p>/<sys>/<staff>/<cell>/<i>` -> `staff/<p>/<sys>/<staff>`."""
    p = glyph_subject.split("/")
    return "/".join(["staff", p[1], p[2], p[3]]) if len(p) >= 4 else ""


def staged_as_result(result: Dict[str, Any], page_index: int,
                     apply_ownership: bool = False) -> tuple[dict, dict]:
    """A staged record, in the shape `score_reading.report` reads.

    Returns `(result_like, stats)`. `stats` is the reach/loss accounting the
    caller must print: a glyph the adapter could not place is a hole in the
    measurement and has to be visible.
    """
    spacing_vals: List[float] = []
    for o in _rows(result, "staff_spacing"):
        if _page_of(o["subject"]) != page_index:
            continue
        try:
            spacing_vals.append(float(o["value"]))
        except (TypeError, ValueError):
            continue

    owner = _standing_owner(result) if apply_ownership else {}
    dets: List[Dict[str, Any]] = []
    n_rows = n_wrong_page = n_no_box = n_disowned = 0
    for o in _rows(result, "glyph_box"):
        if _page_of(o["subject"]) != page_index:
            n_wrong_page += 1
            continue
        n_rows += 1
        if apply_ownership:
            own = owner.get(o["subject"])
            if own and own != _own_staff(o["subject"]):
                n_disowned += 1
                continue
        detail = o.get("detail") or {}
        box = detail.get("bbox_page_px")
        if not box or len(box) != 4:
            n_no_box += 1
            continue
        value = o.get("value") or []
        smufl = value[0] if isinstance(value, (list, tuple)) and value else None
        x0, y0, x1, y1 = (float(v) for v in box)
        dets.append({
            "class": smufl,
            # ⚠️ [x, y, w, h] in PAGE pixels, against a cell at the origin with
            # upscale 1.0 — see the module docstring.
            "bbox": [x0, y0, x1 - x0, y1 - y0],
            "confidence": o.get("score") or 0.0,
        })

    space = statistics.median(spacing_vals) if spacing_vals else 1.0
    page = {
        "systems": [{
            "staves": [{
                "staff_geometry": {"line_spacing_px": space},
                "measures": [{
                    "bbox_page_px": [0.0, 0.0, 0.0, 0.0],
                    "upscale_factor": 1.0,
                    "detections": dets,
                }],
            }],
        }],
    }
    # ⚠️ PADDED SO THE LIST INDEX IS THE PAGE INDEX. `score_reading` addresses
    # pages POSITIONALLY (`pages[page_index]`) while a staged record addresses
    # them by the PDF's own page number, which is what the subject key carries.
    # The first version of this adapter built a one-element list and handed
    # `report()` a `page_index` of 2, so `page_index >= len(pages)` returned an
    # EMPTY detection list and the scorer printed a complete, plausible table of
    # zeros — a clean believable zero that only the REACH line beside it caught,
    # because that line said 732 detections placed. `_assert_report_sees_them`
    # below makes it impossible to pass again.
    result_like = {"pages": [{"systems": []}
                             for _ in range(page_index)] + [page]}
    stats = {
        "glyph_box_rows_on_page": n_rows,
        "glyph_box_rows_other_pages": n_wrong_page,
        "dropped_no_page_box": n_no_box,
        "apply_ownership": apply_ownership,
        "ownership_verdicts": len(owner),
        "dropped_owned_by_another_staff": n_disowned,
        "detections_placed": len(dets),
        "staff_spacing_rows": len(spacing_vals),
        "staff_space_px": space,
    }
    return result_like, stats


def legacy_as_result(result: Dict[str, Any], page_index: int) -> tuple[dict, dict]:
    """A legacy `transcribe` result, addressable at its own PDF page index.

    ⚠️⚠️ THIS IS A LIVE DEFECT IN A SHIPPED INSTRUMENT AND IT IS REPORTED, NOT
    REPAIRED. `score_reading.report` takes ONE `page_index` and uses it
    positionally on BOTH sides (`page_truth["pages"][i]` and
    `result["pages"][i]`), but `transcribe --pages 2` writes a result whose
    `pages` list has ONE element — carrying `page_index: 2` inside it. So
    scoring any page but the first returns an EMPTY detection list and prints a
    complete table of zeros. Every fixture the existing reading lane uses is
    `--pages 0`, where the list index and the page index coincide, which is why
    it has never shown. Padding here keeps the comparison honest without
    touching `tools/`; the defect belongs to whoever owns that file.
    """
    pages = result.get("pages", [])
    by_index = {int(p.get("page_index", i)): p for i, p in enumerate(pages)}
    if page_index not in by_index:
        return {"pages": []}, {"error": f"no page {page_index} in the result",
                               "pages_present": sorted(by_index)}
    padded = [{"systems": []} for _ in range(page_index)] + [by_index[page_index]]
    n = len(SR.detections_in_page_px({"pages": padded}, page_index))
    return {"pages": padded}, {"detections_placed": n,
                               "pages_present": sorted(by_index),
                               "staff_space_px": SR.staff_space_px(
                                   {"pages": padded}, page_index)}


def _shift(result_like: dict, page_index: int, dx: float, dy: float) -> dict:
    out = json.loads(json.dumps(result_like))
    for m in out["pages"][page_index]["systems"][0]["staves"][0]["measures"]:
        for d in m["detections"]:
            d["bbox"] = [d["bbox"][0] + dx, d["bbox"][1] + dy,
                         d["bbox"][2], d["bbox"][3]]
    return out


def _assert_report_sees_them(result_like: dict, page_index: int,
                             placed: int) -> None:
    """The scorer must read exactly the rows the adapter placed.

    ⚠️ THIS IS NOT BELT-AND-BRACES. `score_reading.detections_in_page_px`
    returns `[]` for a page index past the end of the list rather than raising,
    so a mis-shaped adapter produces a full table of zeros that reads as a
    recognition result. This is the control that makes the zero impossible.
    """
    seen = len(SR.detections_in_page_px(result_like, page_index))
    if seen != placed:
        raise SystemExit(
            f"ADAPTER BROKEN: placed {placed} detections, the scorer sees "
            f"{seen} at page index {page_index}. Refusing to report a number "
            "taken over a population the scorer cannot reach.")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--record", type=Path,
                    help="a staged record (the staged arm)")
    ap.add_argument("--legacy", type=Path,
                    help="a legacy `transcribe` result (the cross-reader arm, "
                         "scored by the SAME scorer on the SAME page)")
    ap.add_argument("--truth", type=Path, required=True)
    ap.add_argument("--page", type=int, default=0)
    ap.add_argument("--tolerance", type=float, nargs="+",
                    default=[0.5, 0.25, 0.75, 1.0, 1.5])
    ap.add_argument("--shift-spaces", type=float, default=2.0,
                    help="the frame control: translate every detection by this "
                         "many staff spaces and re-score. The pooled F1 must "
                         "COLLAPSE, or this is not measuring position.")
    ap.add_argument("--apply-ownership", action="store_true",
                    help="drop a glyph whose standing Q.GLYPH_OWNER verdict "
                         "names another staff — the arm comparable to the "
                         "legacy path's `_dedupe_cross_staff_detections`.")
    ap.add_argument("--json-out", type=Path)
    args = ap.parse_args()

    if bool(args.record) == bool(args.legacy):
        print("give exactly one of --record (staged) or --legacy.")
        return 2
    truth = json.loads(args.truth.read_text())
    if args.legacy:
        result = json.loads(args.legacy.read_text())
        like, stats = legacy_as_result(result, args.page)
        arm = "LEGACY transcribe"
    else:
        result = json.loads(args.record.read_text())
        like, stats = staged_as_result(result, args.page, args.apply_ownership)
        arm = "STAGED"

    print("REACH (the adapter's own accounting — a hole here is a hole in the "
          "measurement):")
    for k, v in stats.items():
        print(f"   {k:28s} {v}")
    if not stats.get("detections_placed"):
        print(f"\nDEAD: the {arm} arm placed no detection on page "
              f"{args.page}. Nothing below would be a result.")
        return 2
    _assert_report_sees_them(like, args.page, stats["detections_placed"])
    prov = (result.get("provenance") or {})
    print(f"   tree {prov.get('commit')} dirty={prov.get('dirty')}")
    print(f"   truth renderer {truth.get('renderer')} dpi {truth.get('dpi')}  "
          f"unreliable={truth.get('render_fidelity', {}).get('unreliable')}")

    cls = Counter(d["class"] for d in SR.detections_in_page_px(like, args.page))
    print(f"\ndetector classes ({len(cls)} distinct): "
          f"{dict(cls.most_common(10))}")

    print(f"\n{'=' * 72}\n{arm} reading, page {args.page}\n{'=' * 72}")
    out = SR.report(truth, like, args.page, list(args.tolerance))
    out["adapter"] = stats

    if args.shift_spaces:
        d = args.shift_spaces * stats["staff_space_px"]
        print(f"\n{'=' * 72}\nFRAME CONTROL — every detection moved "
              f"+{args.shift_spaces} staff spaces ({d:.1f} px) in y\n{'=' * 72}")
        shifted = SR.report(truth, _shift(like, args.page, 0.0, d), args.page,
                            [args.tolerance[0]])
        out["frame_control"] = {"shift_spaces": args.shift_spaces,
                                "pooled": shifted["pooled"]}
        base_f1 = out["pooled"]["f1"]
        ctl_f1 = shifted["pooled"]["f1"]
        ok = ctl_f1 < base_f1 * 0.5
        print(f"\nframe control: pooled F1 {base_f1:.3f} -> {ctl_f1:.3f}  "
              f"{'OK (collapses)' if ok else '⚠️ DID NOT COLLAPSE'}")
        out["frame_control"]["collapsed"] = ok

    if args.json_out:
        args.json_out.write_text(json.dumps(out, indent=1))
        print(f"\nwrote {args.json_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
