"""ROADMAP 2.6b — print crops for the `glyph_owner` CONTEST LOSERS, at
whole-movement scale.

⚠️ Reads `out/o26b-cache.json` (produced once by `extract_losers_2_6b.py`
over the fresh Brahms 1/i record, `library` … `imslp317803`, main `f4168dfd`)
— this file does not touch the record again; it is the crop-cutting half only.
Every glyph here is a NOTEHEAD whose `glyph_owner` verdict named a staff
other than the one its cell was cut from, i.e. it is dropped at EXPORT under
`owned_by_another_staff` (`export.py:956`, `is_relocated_copy`). Nothing here
says whether the drop was right. Sean adjudicates; every manifest row carries
`VERDICT_none_yet: null`.

⚠️ FRAME CONTROL FIRST, AND IT CAN FAIL — both candidate staves' own
`Q.STAFF_LINES` must be materially darker than a half-space off them on the
render, or the crop is REFUSED (`crop_contested._frame_ok`'s precedent).

⚠️ BOTH STAVES ARE DRAWN, ALWAYS. GREEN = the staff the record AWARDED the
ink to; BLUE = the staff it was FILED on (this one lost). A crop in the gap
between two staves commits to neither unless both are drawn (Sean,
2026-09-23, `feedback_send_sean_the_crop`). The subject head is bracketed RED.

Population: heads whose `glyph_owner` verdict is DECIDED, category
`notehead`, and whose OWN staff is not the winner — stratified by the
deciding TERM (`ladder` / `range_veto` / `distance`) and by DIRECTION (is the
losing staff the upper or the lower one of the pair). 20 losers + 4 winners
(the kept twin on the winning staff, for the same contest, so Sean can see
whether the drop was a duplicate).

    python3 benchmarks/omr-owner-domain-2026-09/crop_losers_2_6b.py
"""
from __future__ import annotations

import json
import random
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CACHE = Path(__file__).resolve().parent / "out" / "o26b-cache.json"
PDF = REPO_ROOT / ("library/editions/brahms/symphony-1-op68/"
                    "brahms--symphony-1-op68--breitkopf-hartel-brahms--"
                    "imslp317803.pdf")
OUT_DIR = REPO_ROOT / "benchmarks/omr-owner-domain-2026-09/out/print"
DPI = 600
SEED = 20260928

# desired counts per (reason, direction) bucket, 20 losers total, roughly
# proportional to the measured population (§ below) with every bucket
# represented at least twice.
LOSER_TARGETS = {
    ("distance", "own_is_upper_lost_to_lower"): 5,
    ("distance", "own_is_lower_lost_to_upper"): 4,
    ("ladder", "own_is_upper_lost_to_lower"): 4,
    ("ladder", "own_is_lower_lost_to_upper"): 3,
    ("range_veto", "own_is_upper_lost_to_lower"): 2,
    ("range_veto", "own_is_lower_lost_to_upper"): 2,
}
# one winner (kept twin) per each of the four largest buckets
WINNER_BUCKETS = [
    ("distance", "own_is_upper_lost_to_lower"),
    ("distance", "own_is_lower_lost_to_upper"),
    ("ladder", "own_is_upper_lost_to_lower"),
    ("ladder", "own_is_lower_lost_to_upper"),
]


def _frame_ok(arr, line_ys, spacing, *, margin=8.0):
    """`crop_contested._frame_ok`'s precedent, reused verbatim."""
    a = arr if arr.ndim == 2 else arr.mean(axis=2)
    h, w = a.shape
    x0, x1 = int(w * 0.15), int(w * 0.85)
    on, off = [], []
    half = max(1, int(round(spacing / 2.0)))
    for y in line_ys:
        y = int(round(y))
        if not (half < y < h - half):
            continue
        on.append(a[y, x0:x1].mean())
        off.append((a[y - half, x0:x1].mean() + a[y + half, x0:x1].mean()) / 2)
    if not on:
        return False, 0.0
    c = float(sum(off) / len(off) - sum(on) / len(on))
    return c >= margin, c


def _page_of(sub: str) -> int:
    return int(sub.split("/")[1])


def _bucket_pick(losers_by_bucket, targets, rng):
    """Round-robin by (bucket, page) so the 20 spread across the movement,
    not cluster on one page, before frame rendering ever runs."""
    jobs = []
    for key, n in targets.items():
        pool = list(losers_by_bucket.get(key, []))
        by_page = defaultdict(list)
        for l in pool:
            by_page[_page_of(l["subject"])].append(l)
        for v in by_page.values():
            rng.shuffle(v)
        pages = sorted(by_page)
        rng.shuffle(pages)
        order = []
        while any(by_page[p] for p in pages) and len(order) < len(pool):
            for p in pages:
                if by_page[p]:
                    order.append(by_page[p].pop())
        jobs.append((key, order, n))
    return jobs


def main() -> int:
    import fitz
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont

    font = ImageFont.load_default(size=20)
    rng = random.Random(SEED)

    cache = json.loads(CACHE.read_text())
    losers = cache["losers"]
    lines_of = cache["lines_of"]
    spacing_of = cache["spacing_of"]
    population = cache["population"]
    print("population:", json.dumps(population, indent=1))

    by_bucket = defaultdict(list)
    twin_by_subject = {}
    for l in losers:
        by_bucket[(l["reason"], l["direction"])].append(l)
        twin_by_subject[l["subject"]] = l

    jobs_by_bucket = _bucket_pick(by_bucket, LOSER_TARGETS, rng)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(str(PDF))
    pages, frames = {}, {}

    def get_page(p):
        if p not in pages:
            pm = doc[p].get_pixmap(dpi=DPI)
            im = (Image.frombytes("RGB", (pm.width, pm.height), pm.samples)
                  if pm.n >= 3 else
                  Image.frombytes("L", (pm.width, pm.height),
                                  pm.samples).convert("RGB"))
            pages[p] = im
            frames[p] = np.asarray(im.convert("L"), dtype=float)
        return pages[p], frames[p]

    def make_crop(subject, own_key, win_key, bbox, *, bracket_label,
                  title_lines, out_name):
        """One crop: BOTH staves drawn, subject bracketed. Returns the
        manifest-ready contrast pair, or None (with a refusal reason) if the
        frame control fails."""
        p = _page_of(subject)
        own_lines = lines_of.get(own_key)
        win_lines = lines_of.get(win_key)
        if own_lines is None or win_lines is None:
            return None, "missing staff geometry"
        im, arr = get_page(p)
        sp_own = spacing_of.get(own_key, 40.0)
        sp_win = spacing_of.get(win_key, sp_own)
        ok_own, c_own = _frame_ok(arr, own_lines, sp_own)
        ok_win, c_win = _frame_ok(arr, win_lines, sp_win)
        if not (ok_own and ok_win):
            return None, (f"FRAME CONTROL FAILED own={c_own:.1f} "
                          f"win={c_win:.1f}")

        px0, py0, px1, py1 = bbox
        ys = [py0, py1] + own_lines + win_lines
        pad_x = 10.0 * sp_own
        cx0 = int(max(0, px0 - pad_x))
        cx1 = int(min(im.width, px1 + pad_x))
        cy0 = int(max(0, min(ys) - 1.5 * sp_own))
        cy1 = int(min(im.height, max(ys) + 1.5 * sp_own))
        Z = 3
        crop = im.crop((cx0, cy0, cx1, cy1)).resize(
            ((cx1 - cx0) * Z, (cy1 - cy0) * Z), Image.LANCZOS)
        dr = ImageDraw.Draw(crop)

        for ly in win_lines:
            y = (ly - cy0) * Z
            if 0 <= y < crop.height:
                dr.line([(0, y), (crop.width, y)], fill=(0, 160, 60), width=2)
        for ly in own_lines:
            y = (ly - cy0) * Z
            if 0 <= y < crop.height:
                dr.line([(0, y), (crop.width, y)], fill=(30, 80, 220), width=2)

        bx0, by0 = (px0 - cx0) * Z, (py0 - cy0) * Z
        bx1, by1 = (px1 - cx0) * Z, (py1 - cy0) * Z
        arm_len = max(8, int((bx1 - bx0) * 0.4))
        for (ax, ay, dx, dy) in ((bx0, by0, 1, 1), (bx1, by0, -1, 1),
                                 (bx0, by1, 1, -1), (bx1, by1, -1, -1)):
            dr.line([(ax, ay), (ax + dx * arm_len, ay)], fill=(220, 0, 0),
                    width=3)
            dr.line([(ax, ay), (ax, ay + dy * arm_len)], fill=(220, 0, 0),
                    width=3)

        # ruler: one tick per staff space, off the FILED (own) staff's top line
        step = sp_own * Z
        y = (min(own_lines) - cy0) * Z
        k = 0
        while y < crop.height:
            if y >= 0:
                dr.line([(2, y), (16 if k % 5 else 26, y)],
                        fill=(0, 90, 200), width=2)
            y += step
            k += 1

        band_h = 20 * (len(title_lines) + 1)
        out_im = Image.new("RGB", (crop.width, crop.height + band_h), "white")
        out_im.paste(crop, (0, band_h))
        cd = ImageDraw.Draw(out_im)
        for i, (text, color) in enumerate(title_lines):
            cd.text((6, 4 + i * 20), text, fill=color, font=font)
        out_im.save(OUT_DIR / out_name)
        return {"own_contrast": round(c_own, 2), "win_contrast": round(c_win, 2)}, None

    manifest = []
    refused = []
    n = 0
    selected_losers = []   # (n, loser) for winner cross-reference

    for key, order, target in jobs_by_bucket:
        made = 0
        for l in order:
            if made >= target:
                break
            n += 1
            name = f"o26b-{n:02d}"
            title = [
                (f"{name}  LOSER  {l['subject']}  {l['name']}  "
                 f"conf {l['score']:.2f}", (0, 0, 0)),
                (f"pdf idx {_page_of(l['subject'])}   "
                 f"deciding term: {l['reason']}   margin {l['margin']:.2f}"
                 if l["margin"] is not None else
                 f"pdf idx {_page_of(l['subject'])}   "
                 f"deciding term: {l['reason']}",
                 (80, 0, 120)),
                (f"BLUE = {l['own_staff']}: FILED here (LOST)",
                 (30, 80, 220)),
                (f"GREEN = {l['winning_staff']}: record AWARDS the ink here",
                 (0, 120, 45)),
                ("Q: right staff dropped (correct) / wrong staff dropped "
                 "(this staff's own note) / not a note?", (0, 0, 0)),
            ]
            contrast, why = make_crop(
                l["subject"], l["own_staff"], l["winning_staff"], l["bbox"],
                bracket_label="loser", title_lines=title, out_name=f"{name}.png")
            if contrast is None:
                n -= 1
                refused.append({"subject": l["subject"], "bucket": list(key),
                                "why": why})
                continue
            made += 1
            manifest.append({
                "n": n, "file": f"{name}.png", "kind": "loser",
                "subject": l["subject"], "detector_class": l["name"],
                "detector_conf": round(l["score"], 3),
                "filed_staff": l["own_staff"],
                "winning_staff": l["winning_staff"],
                "deciding_term": l["reason"],
                "margin": l["margin"],
                "direction": l["direction"],
                "twin_subject": l["twin_subject"],
                "twin_kept": l["twin_kept"],
                "twin_reason": l["twin_reason"],
                "frame_contrast": contrast,
                "page_box": [round(c, 1) for c in l["bbox"]],
                "question": ("right staff dropped (correct) / wrong staff "
                            "dropped (this staff's own note) / not a note"),
                "VERDICT_none_yet": None,
            })
            selected_losers.append((n, l))
        print(f"bucket {key}: requested {target}, made {made}")

    # ── the 4 winners: the KEPT twin on the winning staff, same contest ─────
    winners_made = 0
    for key in WINNER_BUCKETS:
        cand = [pair for pair in selected_losers if
                (pair[1]["reason"], pair[1]["direction"]) == key
                and pair[1]["twin_subject"] and pair[1]["twin_kept"]]
        if not cand:
            continue
        loser_n, l = cand[0]
        twin_sub = l["twin_subject"]
        # find the twin's own glyph box (it lives among the *losers* only if
        # it too lost a DIFFERENT contest; look it up directly in the raw
        # per-page glyph list is unavailable here, so re-derive its bbox from
        # the same cache: twins are always on `winning_staff`, and their bbox
        # is not carried in the slim cache -- reopen only the tiny per-glyph
        # record slice via the loser's own bbox neighbourhood is not enough,
        # so the twin's bbox was captured at extraction time under
        # `twin_bbox` if present.
        twin_bbox = l.get("twin_bbox")
        if twin_bbox is None:
            refused.append({"subject": twin_sub, "why": "no cached bbox for twin"})
            continue
        n += 1
        name = f"o26b-{n:02d}"
        title = [
            (f"{name}  WINNER (kept twin of #{loser_n:02d})  {twin_sub}",
             (0, 0, 0)),
            (f"pdf idx {_page_of(twin_sub)}   contest term: {l['reason']}",
             (80, 0, 120)),
            (f"GREEN = {l['winning_staff']}: kept here (this glyph's own staff)",
             (0, 120, 45)),
            (f"BLUE = {l['own_staff']}: the OTHER staff of this same contest "
             f"(where #{loser_n:02d} was filed and dropped)", (30, 80, 220)),
            ("Q: is this a duplicate of the loser, or a different note?",
             (0, 0, 0)),
        ]
        contrast, why = make_crop(
            twin_sub, l["winning_staff"], l["own_staff"], twin_bbox,
            bracket_label="winner", title_lines=title, out_name=f"{name}.png")
        if contrast is None:
            n -= 1
            refused.append({"subject": twin_sub, "why": why})
            continue
        winners_made += 1
        manifest.append({
            "n": n, "file": f"{name}.png", "kind": "winner",
            "subject": twin_sub, "kept_twin_of_loser_n": loser_n,
            "kept_twin_of_subject": l["subject"],
            "filed_staff": l["winning_staff"],
            "winning_staff": l["winning_staff"],
            "deciding_term": l["reason"],
            "margin": None,
            "direction": l["direction"],
            "twin_subject": l["subject"],
            "twin_kept": True,
            "twin_reason": l["reason"],
            "frame_contrast": contrast,
            "page_box": [round(c, 1) for c in twin_bbox],
            "question": "is this a duplicate of its paired loser, or a different note",
            "VERDICT_none_yet": None,
        })

    print(f"winners made: {winners_made} of {len(WINNER_BUCKETS)} requested")
    print(f"total crops: {len(manifest)}  refused: {len(refused)}")

    (OUT_DIR / "o26b-manifest.json").write_text(json.dumps({
        "roadmap_item": "2.6b",
        "record": ("/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/"
                    "redecide-f4168dfd/out-redecide/brahms/"
                    "amended.record.json (re-decided on main f4168dfd; "
                    "read-only, machine-local, not committed)"),
        "pdf": str(PDF.relative_to(REPO_ROOT)),
        "dpi": DPI, "seed": SEED,
        "population": population,
        "loser_targets": {f"{k[0]}|{k[1]}": v for k, v in LOSER_TARGETS.items()},
        "crops": manifest,
        "refused": refused,
    }, indent=2))
    for r in refused:
        print("  REFUSED", r)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
