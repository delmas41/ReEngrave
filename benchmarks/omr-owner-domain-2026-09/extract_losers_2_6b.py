"""ROADMAP 2.6b — extract the `glyph_owner` LOSER population (notehead
category, decided, own staff overturned) from the fresh Brahms 1/i record,
once, into a slim committed cache `out/o26b-cache.json` that
`crop_losers_2_6b.py` reads.

⚠️ READS THE RECORD, WRITES NOTHING TO IT. The record itself
(`.claude/worktrees/redecide-f4168dfd/out-redecide/brahms/
amended.record.json`, main `f4168dfd`) is machine-local, read-only, and NOT
committed (1.6 GB) -- only this script and its slim output are. Per DECISIONS
2026-09-28's proof budget for this lane: one `load_record`, no pipeline runs.

    python3 benchmarks/omr-owner-domain-2026-09/extract_losers_2_6b.py
"""
from __future__ import annotations

import json
import sys
import time
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT))

from tools.omr.staged.record_io import load_record  # noqa: E402

REC_PATH = ("/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/"
            "redecide-f4168dfd/out-redecide/brahms/amended.record.json")
OUT = HERE / "out" / "o26b-cache.json"

NOTEHEAD_PREFIX = "notehead"
CONTEST_IOU = 0.3   # gather.py's own CONTEST_IOU, ROADMAP 2.6


def _iou(a, b):
    ix0, iy0 = max(a[0], b[0]), max(a[1], b[1])
    ix1, iy1 = min(a[2], b[2]), min(a[3], b[3])
    if ix1 <= ix0 or iy1 <= iy0:
        return 0.0
    inter = (ix1 - ix0) * (iy1 - iy0)
    area_a = (a[2] - a[0]) * (a[3] - a[1])
    area_b = (b[2] - b[0]) * (b[3] - b[1])
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


def own_of(sub: str) -> str:
    parts = sub.split("/")
    return "staff/" + "/".join(parts[1:4])


def main() -> int:
    t0 = time.time()
    print("loading record ...", flush=True)
    rec = load_record(REC_PATH)["record"]
    print(f"loaded in {time.time() - t0:.1f}s  "
          f"obs={len(rec['observations'])} verdicts={len(rec['verdicts'])}",
          flush=True)

    glyph = {}          # subject -> dict(name, category, bbox, score)
    by_page_sys = {}    # (page, system) -> list of notehead subjects
    lines_of = {}
    spacing_of = {}

    for o in rec["observations"]:
        q = o["quantity"]
        if q == "glyph_box":
            d = o.get("detail") or {}
            bbox = d.get("bbox_page_px")
            if bbox is None:
                continue
            name = str(o["value"][0])
            entry = {"name": name, "category": d.get("category"),
                      "bbox": [float(v) for v in bbox],
                      "score": float(o.get("score") or 0.0)}
            glyph[o["subject"]] = entry
            if name.lower().startswith(NOTEHEAD_PREFIX):
                parts = o["subject"].split("/")
                key = (int(parts[1]), int(parts[2]))
                by_page_sys.setdefault(key, []).append(o["subject"])
        elif q == "staff_lines":
            ys = [float(y) for y in o["value"]]
            if len(ys) >= 2:
                lines_of[o["subject"]] = ys
        elif q == "staff_spacing":
            spacing_of[o["subject"]] = float(o["value"])

    print(f"glyph_box (all) entries: {len(glyph)}; "
          f"notehead subjects indexed by (page,system): "
          f"{sum(len(v) for v in by_page_sys.values())}", flush=True)

    sup = {v.get("supersedes") for v in rec["verdicts"] if v.get("supersedes")}
    owner_verdicts = [v for v in rec["verdicts"]
                       if v["quantity"] == "glyph_owner" and v["id"] not in sup]
    print(f"glyph_owner verdicts (current, not superseded): "
          f"{len(owner_verdicts)}", flush=True)
    print("outcome counts:", Counter(v["outcome"] for v in owner_verdicts))
    print("reason counts (decided only):",
          Counter(v["reason"] for v in owner_verdicts
                   if v["outcome"] == "decided"))

    losers = []
    for v in owner_verdicts:
        if v["outcome"] != "decided":
            continue
        sub = v["subject"]
        g = glyph.get(sub)
        if g is None or not g["name"].lower().startswith(NOTEHEAD_PREFIX):
            continue
        own = own_of(sub)
        winner = v["value"]
        if not winner or winner == own:
            continue
        if own not in lines_of or winner not in lines_of:
            continue
        # direction: is the glyph's OWN staff the upper or lower staff of
        # the pair, by mean staff-line y (smaller y = higher on the page).
        own_y = sum(lines_of[own]) / len(lines_of[own])
        win_y = sum(lines_of[winner]) / len(lines_of[winner])
        direction = "own_is_upper_lost_to_lower" if own_y < win_y \
            else "own_is_lower_lost_to_upper"

        # find the TWIN: the same-category glyph on the WINNING staff whose
        # box overlaps this one at > CONTEST_IOU (gather's own contest test,
        # `gather_ownership_evidence`/`_iou`, category equality) -- the
        # winner's OWN detection that made this a contest in the first place.
        parts = sub.split("/")
        page, system = int(parts[1]), int(parts[2])
        twin = None
        best_iou = 0.0
        for cand_sub in by_page_sys.get((page, system), ()):
            if cand_sub == sub:
                continue
            cown = own_of(cand_sub)
            if cown != winner:
                continue
            cg = glyph[cand_sub]
            if cg["category"] != g["category"]:
                continue
            i = _iou(g["bbox"], cg["bbox"])
            if i > CONTEST_IOU and i > best_iou:
                best_iou = i
                twin = cand_sub

        twin_kept = None
        twin_reason = None
        if twin is not None:
            # was the twin's OWN glyph_owner verdict decided for ITS OWN
            # staff (i.e. not itself dropped as owned_by_another_staff)?
            tv = None
            for v2 in owner_verdicts:
                if v2["subject"] == twin:
                    tv = v2
                    break
            if tv is None:
                twin_kept = True   # never contested itself: nothing refuses it
                twin_reason = "uncontested"
            else:
                twin_kept = (tv["outcome"] == "decided"
                             and tv["value"] == own_of(twin))
                twin_reason = tv.get("reason")

        losers.append({
            "subject": sub, "own_staff": own, "winning_staff": winner,
            "reason": v["reason"], "margin": v.get("margin"),
            "detail": v.get("detail"), "name": g["name"],
            "category": g["category"], "bbox": g["bbox"], "score": g["score"],
            "direction": direction,
            "twin_subject": twin, "twin_iou": round(best_iou, 3),
            "twin_bbox": glyph[twin]["bbox"] if twin is not None else None,
            "twin_kept": twin_kept, "twin_reason": twin_reason,
        })

    print(f"losers (notehead, decided, own staff lost): {len(losers)}",
          flush=True)
    by_reason = Counter(l["reason"] for l in losers)
    by_dir = Counter(l["direction"] for l in losers)
    by_both = Counter((l["reason"], l["direction"]) for l in losers)
    print("by reason:", by_reason)
    print("by direction:", by_dir)
    print("by (reason, direction):", by_both)
    print("with a twin found:", sum(1 for l in losers if l["twin_subject"]))
    print("twin kept True:", sum(1 for l in losers if l["twin_kept"] is True))
    print("twin kept False:", sum(1 for l in losers if l["twin_kept"] is False))

    # slim staff geometry cache: only staves that appear as own/winner above
    needed_staves = set()
    for l in losers:
        needed_staves.add(l["own_staff"])
        needed_staves.add(l["winning_staff"])
    lines_slim = {k: lines_of[k] for k in needed_staves if k in lines_of}
    spacing_slim = {k: spacing_of[k] for k in needed_staves if k in spacing_of}

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "record": REC_PATH,
        "losers": losers,
        "lines_of": lines_slim,
        "spacing_of": spacing_slim,
        "population": {
            "total_losers": len(losers),
            "by_reason": dict(by_reason),
            "by_direction": dict(by_dir),
            "by_reason_direction": {f"{r}|{d}": n
                                     for (r, d), n in by_both.items()},
        },
    }, indent=1))
    print(f"wrote {OUT} ({OUT.stat().st_size / 1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
