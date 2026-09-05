"""How much of the page did we SEE — scored against the page, not the encoding.

`omr_ned` scores the exported MusicXML against a truth MusicXML: recognition and
serialisation fused into one number. This scores the DETECTIONS against
`page_truth`'s inventory of what the engraver actually drew. Two numbers on the
same page, so a fall in one and not the other says which half moved.

    reading   — did we find the symbol, and call it the right kind
    OMR-NED   — did the file we wrote say what the truth file says

⚠️ **MATCHED ON CENTRES, NOT IoU.** The detector's boxes are learned and the
engraver's are exact; they will never agree on extent, and demanding overlap
would measure box style rather than recognition. A symbol is found if a
detection of the same family has its centre within `--tolerance` staff spaces —
the same unit every geometric decision in this pipeline is expressed in, and the
same reasoning `_dedupe_cross_staff_detections` uses when it resolves a contest
by distance. Report the tolerance sweep, not one value.

⚠️ **A FAMILY IS NOT A CLASS.** `noteheadBlackOnLine` and `noteheadBlackInSpace`
are one glyph on two staff positions; that distinction is the note's PITCH and
is resolved from the staff grid, not from the class. Scoring it here would
charge recognition for a pitch error. So both sides collapse to families, and
pitch stays where it is measured — in the note-accuracy figures.

    python3 -m tools.omr.score_reading truth.pagetruth.json read.omr.json
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

#: Detector class name -> the page-truth family it should be scored against.
#: Prefix-matched, longest first, so `noteheadDoubleWhole` cannot be eaten by
#: `notehead`. A class not listed here is not scored and is reported as such —
#: an inventory, never a silent drop.
_FAMILY_PREFIXES: list[tuple[str, str]] = [
    ("notehead", "notehead"),
    ("rest", "rest"),
    ("accidental", "accidental"),
    ("keysharp", "key_accidental"),
    ("keyflat", "key_accidental"),
    ("keynatural", "key_accidental"),
    ("timesig", "time_signature_digit"),
    ("clef", "clef"),
    ("gclef", "clef"),
    ("fclef", "clef"),
    ("cclef", "clef"),
    ("dynamiccrescendohairpin", None),      # a wedge, not a letter
    ("dynamicdiminuendohairpin", None),
    ("dynamic", "dynamic_letter"),
    ("flag", "flag"),
    ("augmentationdot", "augmentation_dot"),
    ("barline", "barline"),
    ("slur", "slur"),
    ("tie", "tie"),
    ("beam", "beam"),
]

#: A family the RENDERER draws differently from what the encoding says is
#: printed is excluded too, and named by `page_truth.render_fidelity` rather
#: than listed here — see that function for the Verovio accidental case.
#:
#: Families the detector is not expected to supply, with the reason. Scored
#: anyway and reported, because "we emit none of these" is worth seeing — but
#: flagged so a zero is not read as a regression.
CV_SOURCED: dict[str, str] = {
    "beam": "classical CV (`line_detection`), not the YOLO detector",
    "barline": "classical CV (`measure_extractor`), and cell-relative",
}


def detector_family(class_name: str) -> str | None:
    norm = "".join(ch for ch in (class_name or "").lower() if ch.isalnum())
    for prefix, family in _FAMILY_PREFIXES:
        if norm.startswith(prefix):
            return family
    return None


def detections_in_page_px(result: dict[str, Any], page_index: int = 0) -> list[dict]:
    """Every detection of the page, centred in PAGE pixels.

    The pipeline works in each cell's canonical frame; the truth is in page
    pixels. `bbox_page_px` and `upscale_factor` are the only conversion, and
    they are the same ones the exporter uses.
    """
    out = []
    pages = result.get("pages", [])
    if page_index >= len(pages):
        return out
    for system in pages[page_index].get("systems", []):
        for staff in system.get("staves", []):
            for meas in staff.get("measures", []):
                box = meas.get("bbox_page_px") or [0, 0, 0, 0]
                up = float(meas.get("upscale_factor") or 1.0) or 1.0
                for det in meas.get("detections", []):
                    b = det.get("bbox")
                    if not b or len(b) != 4:
                        continue
                    fam = detector_family(det.get("class") or "")
                    out.append({
                        "family": fam,
                        "class": det.get("class"),
                        "cx": float(box[0]) + (b[0] + b[2] / 2.0) / up,
                        "cy": float(box[1]) + (b[1] + b[3] / 2.0) / up,
                        "conf": float(det.get("confidence") or 0.0),
                    })
    return out


def staff_space_px(result: dict[str, Any], page_index: int = 0) -> float:
    vals = []
    pages = result.get("pages", [])
    if page_index < len(pages):
        for system in pages[page_index].get("systems", []):
            for staff in system.get("staves", []):
                s = (staff.get("staff_geometry") or {}).get("line_spacing_px")
                if s:
                    vals.append(float(s))
    return sorted(vals)[len(vals) // 2] if vals else 1.0


def match(truth: list[dict], dets: list[dict], tol_px: float) -> dict[str, Any]:
    """Greedy nearest-centre, one-to-one, within family.

    Greedy rather than optimal (Hungarian) on purpose: at this tolerance the
    assignment is almost never contested, and a greedy pass cannot silently
    turn a localisation result into an assignment-algorithm result.
    """
    by_family_t: dict[str, list[dict]] = defaultdict(list)
    by_family_d: dict[str, list[dict]] = defaultdict(list)
    for s in truth:
        by_family_t[s["family"]].append(s)
    unscored = Counter()
    for d in dets:
        if d["family"] is None:
            unscored[d["class"]] += 1
            continue
        by_family_d[d["family"]].append(d)

    per_family: dict[str, dict[str, int]] = {}
    for family in sorted(set(by_family_t) | set(by_family_d)):
        T = by_family_t.get(family, [])
        D = list(by_family_d.get(family, []))
        used = [False] * len(D)
        hit = 0
        for s in T:
            cx, cy = s["x"] + s["w"] / 2.0, s["y"] + s["h"] / 2.0
            best, best_d = -1, tol_px
            for i, d in enumerate(D):
                if used[i]:
                    continue
                dist = ((d["cx"] - cx) ** 2 + (d["cy"] - cy) ** 2) ** 0.5
                if dist <= best_d:
                    best, best_d = i, dist
            if best >= 0:
                used[best] = True
                hit += 1
        per_family[family] = {"truth": len(T), "pred": len(D), "matched": hit}
    return {"per_family": per_family, "unscored_detections": dict(unscored)}


def confusions(truth: list[dict], dets: list[dict], tol_px: float) -> dict[str, Counter]:
    """For each MISSED symbol, what family stood there instead.

    A recall of 0.176 on ties means one of two very different things — the arcs
    were not seen, or they were seen and called slurs — and precision/recall
    cannot tell them apart. This can: it re-searches each unmatched truth symbol
    against detections of ANY family. `-` means nothing was there at all, which
    is the only reading that means "not seen".
    """
    by_family_d: dict[str, list[dict]] = defaultdict(list)
    for d in dets:
        if d["family"] is not None:
            by_family_d[d["family"]].append(d)

    out: dict[str, Counter] = defaultdict(Counter)
    for family in sorted({s["family"] for s in truth}):
        T = [s for s in truth if s["family"] == family]
        D = list(by_family_d.get(family, []))
        used = [False] * len(D)
        for s in T:
            cx, cy = s["x"] + s["w"] / 2.0, s["y"] + s["h"] / 2.0
            best, best_d = -1, tol_px
            for i, d in enumerate(D):
                if used[i]:
                    continue
                dist = ((d["cx"] - cx) ** 2 + (d["cy"] - cy) ** 2) ** 0.5
                if dist <= best_d:
                    best, best_d = i, dist
            if best >= 0:
                used[best] = True
                continue
            near = [(((d["cx"] - cx) ** 2 + (d["cy"] - cy) ** 2) ** 0.5, d["family"])
                    for d in dets if d["family"] is not None]
            near = [n for n in near if n[0] <= tol_px]
            out[family][min(near)[1] if near else "-"] += 1
    return out


def _prf(m: dict[str, int]) -> tuple[float, float, float]:
    p = m["matched"] / m["pred"] if m["pred"] else 0.0
    r = m["matched"] / m["truth"] if m["truth"] else 0.0
    f = 2 * p * r / (p + r) if (p + r) else 0.0
    return p, r, f


def report(page_truth: dict, result: dict, page_index: int, tolerances) -> dict:
    page = page_truth["pages"][page_index]
    dets = detections_in_page_px(result, page_index)
    space = staff_space_px(result, page_index)
    out: dict[str, Any] = {"staff_space_px": space, "tolerances": {}}

    for tol in tolerances:
        m = match(page["symbols"], dets, tol * space)
        out["tolerances"][str(tol)] = m

    unreliable = set((page_truth.get("render_fidelity") or {}).get("unreliable", []))
    out["unreliable_families"] = sorted(unreliable)
    excluded = set(CV_SOURCED) | unreliable

    main = out["tolerances"][str(tolerances[0])]
    print(f"page {page_index + 1}: {len(page['symbols'])} printed symbols, "
          f"{len(dets)} detections, staff space {space:.1f} px")
    print(f"\n{'family':24s} {'truth':>6s} {'pred':>6s} {'match':>6s} "
          f"{'prec':>6s} {'rec':>6s} {'F1':>6s}")
    tt = pp = mm = 0
    for family, m in sorted(main["per_family"].items()):
        p, r, f = _prf(m)
        note = ("  (CV)" if family in CV_SOURCED
                else "  (RENDER)" if family in unreliable else "")
        print(f"{family:24s} {m['truth']:6d} {m['pred']:6d} {m['matched']:6d} "
              f"{p:6.3f} {r:6.3f} {f:6.3f}{note}")
        if family not in excluded:
            tt += m["truth"]; pp += m["pred"]; mm += m["matched"]
    P = mm / pp if pp else 0.0
    R = mm / tt if tt else 0.0
    F = 2 * P * R / (P + R) if (P + R) else 0.0
    print(f"{'POOLED (scoreable)':24s} {tt:6d} {pp:6d} {mm:6d} "
          f"{P:6.3f} {R:6.3f} {F:6.3f}")
    out["pooled"] = {"truth": tt, "pred": pp, "matched": mm,
                     "precision": P, "recall": R, "f1": F}

    print(f"\ntolerance sweep (pooled F1):")
    for tol in tolerances:
        m = out["tolerances"][str(tol)]
        t2 = sum(v["truth"] for k, v in m["per_family"].items() if k not in excluded)
        p2 = sum(v["pred"] for k, v in m["per_family"].items() if k not in excluded)
        x2 = sum(v["matched"] for k, v in m["per_family"].items() if k not in excluded)
        P2 = x2 / p2 if p2 else 0.0
        R2 = x2 / t2 if t2 else 0.0
        print(f"   {tol:4.2f} spaces -> F1 {2*P2*R2/(P2+R2) if (P2+R2) else 0:.3f}")

    conf = confusions(page["symbols"], dets, tolerances[0] * space)
    rows = {k: v for k, v in conf.items() if v}
    if rows:
        print("\nwhat stood where a symbol was MISSED "
              "(`-` = nothing there, i.e. genuinely not seen):")
        for family in sorted(rows, key=lambda k: -sum(rows[k].values())):
            print(f"   {family:22s} {dict(rows[family].most_common(5))}")
    out["confusions"] = {k: dict(v) for k, v in rows.items()}

    if main["unscored_detections"]:
        print(f"\ndetections in no scored family: "
              f"{sum(main['unscored_detections'].values())} "
              f"{dict(sorted(main['unscored_detections'].items(), key=lambda kv: -kv[1])[:8])}")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("page_truth", type=Path)
    ap.add_argument("transcription", type=Path)
    ap.add_argument("--page", type=int, default=0)
    ap.add_argument("--tolerance", type=float, nargs="+",
                    default=[0.5, 0.25, 0.75, 1.0, 1.5])
    ap.add_argument("--json-out", type=Path)
    args = ap.parse_args()

    out = report(json.loads(args.page_truth.read_text()),
                 json.loads(args.transcription.read_text()),
                 args.page, args.tolerance)
    if args.json_out:
        args.json_out.write_text(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
