"""WHICH of the staged path's four known divergences produces its extra ink.

The staged gather and the legacy `transcribe` read the SAME page with the SAME
weights and match the SAME 294 printed symbols. The staged side emits more
detections. There are four documented reasons it could:

  1. NMS       `gather.py:292` passes neither `iou_threshold` nor
               `agnostic_nms`, taking `YoloDetector.detect`'s own defaults
               0.7 / **False** where `transcribe` passes 0.5 / **True**.
  2. cross-staff  the legacy path runs `_dedupe_cross_staff_detections`;
               the staged path files an ownership VERDICT instead and (since
               2026-09-11) refuses the loser at EXPORT, so the row survives
               in the record.
  3. clipped fragments  `_drop_clipped_notehead_fragments` — legacy only.
  4. unladdered noteheads  `_drop_unladdered_noteheads` — legacy only.

Only (1) and (2) can be told apart from the two artefacts alone, and they can:
(1) leaves a twin in the SAME cell, (2) leaves one in a DIFFERENT staff's cell
at the same page position. (3) and (4) are notehead-only, so a page where the
notehead counts AGREE has nothing for them to have done — which is a negative
result about those two filters and is reported as one.

    python3 benchmarks/omr-staged-engraved-2026-09/attribute_extras.py \
        --record out/engraved-p0.record.json --legacy out/legacy-p0.omr.json \
        --page 0

⚠️ THIS COMPARES THE RECORD AGAINST THE LEGACY JSON, so it can only speak about
rows that EXIST on one side and not the other. It cannot say what the detector
would have returned under different NMS — that needs a second gather, which is
a GATHER change and is named as out of scope.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools.omr.score_reading import detector_family  # noqa: E402


def _iou(a: Tuple[float, float, float, float],
         b: Tuple[float, float, float, float]) -> float:
    ix0, iy0 = max(a[0], b[0]), max(a[1], b[1])
    ix1, iy1 = min(a[2], b[2]), min(a[3], b[3])
    if ix1 <= ix0 or iy1 <= iy0:
        return 0.0
    inter = (ix1 - ix0) * (iy1 - iy0)
    aa = (a[2] - a[0]) * (a[3] - a[1])
    bb = (b[2] - b[0]) * (b[3] - b[1])
    u = aa + bb - inter
    return inter / u if u > 0 else 0.0


def staged_dets(result: Dict[str, Any], page: int) -> List[dict]:
    own = {v["subject"]: v.get("value")
           for v in result["record"]["verdicts"]
           if v.get("quantity") == "glyph_owner" and v.get("outcome") == "decided"}
    out = []
    for o in result["record"]["observations"]:
        if o.get("quantity") != "glyph_box":
            continue
        parts = o["subject"].split("/")
        if len(parts) != 6 or int(parts[1]) != page:
            continue
        box = (o.get("detail") or {}).get("bbox_page_px")
        if not box:
            continue
        v = o.get("value") or []
        owner = own.get(o["subject"])
        mine = "/".join(["staff", parts[1], parts[2], parts[3]])
        out.append({
            "subject": o["subject"],
            "cell": "/".join(parts[2:5]),          # sys/staff/measure
            "staff": parts[3],
            "class": v[0] if v else None,
            "family": detector_family(v[0] if v else ""),
            "box": tuple(float(x) for x in box),
            "conf": o.get("score") or 0.0,
            "owner": owner,
            "disowned": bool(owner) and owner != mine,
        })
    return out


def legacy_dets(result: Dict[str, Any], page: int) -> List[dict]:
    out = []
    pages = result.get("pages", [])
    if page >= len(pages):
        return out
    for si, system in enumerate(pages[page].get("systems", [])):
        for ti, staff in enumerate(system.get("staves", [])):
            for meas in staff.get("measures", []):
                bb = meas.get("bbox_page_px") or [0, 0, 0, 0]
                up = float(meas.get("upscale_factor") or 1.0) or 1.0
                for d in meas.get("detections", []):
                    b = d.get("bbox")
                    if not b or len(b) != 4:
                        continue
                    x0 = bb[0] + b[0] / up
                    y0 = bb[1] + b[1] / up
                    out.append({
                        "cell": f"{si}/{ti}/{meas.get('measure_index')}",
                        "staff": str(ti),
                        "class": d.get("class"),
                        "family": detector_family(d.get("class") or ""),
                        "box": (x0, y0, x0 + b[2] / up, y0 + b[3] / up),
                        "conf": float(d.get("confidence") or 0.0),
                    })
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--record", type=Path, required=True)
    ap.add_argument("--legacy", type=Path, required=True)
    ap.add_argument("--page", type=int, default=0)
    ap.add_argument("--match-iou", type=float, default=0.5,
                    help="a staged row is 'the same ink' as a legacy row above "
                         "this. Reported as a sweep, never as one value.")
    ap.add_argument("--json-out", type=Path)
    args = ap.parse_args()

    S = staged_dets(json.loads(args.record.read_text()), args.page)
    L = legacy_dets(json.loads(args.legacy.read_text()), args.page)
    print(f"REACH: staged {len(S)} detections, legacy {len(L)}, page {args.page}")
    if not S or not L:
        print("DEAD: one side is empty. Nothing below would be a result.")
        return 2

    cs, cl = Counter(d["class"] for d in S), Counter(d["class"] for d in L)
    print(f"\n{'class':28s} {'staged':>7s} {'legacy':>7s} {'delta':>6s}")
    for k in sorted(set(cs) | set(cl), key=lambda k: -(cs[k] - cl[k])):
        if cs[k] != cl[k]:
            print(f"{k:28s} {cs[k]:7d} {cl[k]:7d} {cs[k] - cl[k]:+6d}")

    # ── which staged rows have NO legacy counterpart ────────────────────────
    by_cell_l: Dict[str, List[dict]] = defaultdict(list)
    for d in L:
        by_cell_l[d["cell"]].append(d)

    for tol in (0.3, 0.5, 0.7):
        used = {id(d): False for d in L}
        extras = []
        for s in S:
            best, best_i = None, tol
            for d in by_cell_l.get(s["cell"], []):
                if used[id(d)] or d["class"] != s["class"]:
                    continue
                i = _iou(s["box"], d["box"])
                if i >= best_i:
                    best, best_i = d, i
            if best is not None:
                used[id(best)] = True
            else:
                extras.append(s)
        print(f"\nIoU {tol}: {len(extras)} staged rows with no same-class legacy "
              f"row in the same cell")
        if tol != args.match_iou:
            continue

        # ── attribute each extra ────────────────────────────────────────────
        # ⚠️ `CONTEST_IOU = 0.5` on the staged side against the legacy
        # `_CROSS_STAFF_DUPLICATE_IOU = 0.3`, so a pair overlapping between
        # those two numbers is DEDUPED by `transcribe` and never even contested
        # here — it gets no ownership verdict, so applying ownership cannot
        # remove it. That band is reported apart from the resolved contests
        # because the repair differs: one is a threshold, the other is not a
        # fault at all.
        verdict = Counter()
        detail: Dict[str, List[str]] = defaultdict(list)
        for e in extras:
            twin_same_cell = max(
                (_iou(e["box"], o["box"]) for o in S
                 if o is not e and o["cell"] == e["cell"]
                 and o["family"] == e["family"]), default=0.0)
            twin_other_staff = max(
                (_iou(e["box"], o["box"]) for o in S
                 if o is not e and o["staff"] != e["staff"]
                 and o["class"] == e["class"]), default=0.0)
            if e["disowned"]:
                k = ("cross-staff, RESOLVED: its own Q.GLYPH_OWNER verdict "
                     "names another staff")
            elif twin_other_staff >= 0.5:
                k = ("cross-staff, kept: a twin at IoU >= CONTEST_IOU (0.5) "
                     "and this copy WON or the contest disagreed")
            elif twin_other_staff >= 0.3:
                k = ("cross-staff, NOT CONTESTED: twin at IoU 0.3-0.5 — "
                     "legacy dedupes at 0.3, staged contests at 0.5")
            elif twin_same_cell >= 0.3:
                k = "NMS: a same-cell, same-family twin (IoU >= 0.3)"
            else:
                k = "unexplained by any of the four"
            verdict[k] += 1
            detail[k].append(f"{e['class']}@{e['cell']} "
                             f"same_cell={twin_same_cell:.2f} "
                             f"other_staff={twin_other_staff:.2f}"
                             f"{' DISOWNED' if e['disowned'] else ''}")
        print(f"\nattribution of the {len(extras)} extras "
              f"(IoU {args.match_iou}):")
        for k, n in verdict.most_common():
            print(f"   {n:4d}  {k}")
            for line in detail[k][:6]:
                print(f"           {line}")
            if len(detail[k]) > 6:
                print(f"           ... and {len(detail[k]) - 6} more")

        fam = Counter(e["family"] for e in extras)
        print(f"\n   by scored family: {dict(fam.most_common())}")
        print(f"   of the {len(extras)}, "
              f"{sum(1 for e in extras if e['disowned'])} are already refused "
              f"at EXPORT as `owned_by_another_staff`")

        # ── the ownership verdicts themselves ───────────────────────────────
        with_v = [d for d in S if d["owner"]]
        print(f"\nQ.GLYPH_OWNER: {len(with_v)} glyphs carry a decided verdict; "
              f"{sum(1 for d in with_v if d['disowned'])} name another staff, "
              f"{sum(1 for d in with_v if not d['disowned'])} name their own.")
        print(f"   by class: {dict(Counter(d['class'] for d in with_v))}")
        # ⚠️ A CONTEST of two copies should leave exactly ONE naming its own
        # staff. Two winners is the DISAGREEMENT case CLAUDE.md calls a swap,
        # and it is counted rather than netted away.
        by_class_kept = Counter(d["class"] for d in with_v if not d["disowned"])
        by_class_drop = Counter(d["class"] for d in with_v if d["disowned"])
        for k in sorted(set(by_class_kept) | set(by_class_drop)):
            flag = ("   ⚠️ every copy kept — the contest DISAGREED"
                    if by_class_drop[k] == 0 else "")
            print(f"   {k:16s} kept {by_class_kept[k]:3d}  "
                  f"disowned {by_class_drop[k]:3d}{flag}")

        # ── the notehead filters: a NEGATIVE result, stated ─────────────────
        nh_s = sum(1 for d in S if d["family"] == "notehead")
        nh_l = sum(1 for d in L if d["family"] == "notehead")
        print(f"\nnoteheads: staged {nh_s}, legacy {nh_l}, delta {nh_s - nh_l:+d}"
              f"  — the two legacy-only NOTEHEAD filters "
              f"(`_drop_clipped_notehead_fragments`, `_drop_unladdered_"
              f"noteheads`) can only have removed noteheads, so a delta of 0 "
              f"means they cost the staged path NOTHING on this page.")
        if args.json_out:
            args.json_out.write_text(json.dumps(
                {"staged": len(S), "legacy": len(L),
                 "extras": len(extras), "attribution": dict(verdict),
                 "by_family": dict(fam),
                 "noteheads": {"staged": nh_s, "legacy": nh_l}}, indent=1))
            print(f"\nwrote {args.json_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
