"""ROADMAP 2.10b — one HEADER crop per staff whose NARROWED clef this rule
filled, for Sean.

Same convention as `benchmarks/omr-clef-gap-2026-09/probe/crop_clef.py`
(2.10's own crop tool for the ABSTAINED case), adapted for the NARROWED
case: the caption additionally names the CANDIDATES the staff's own contest
kept (`adjudicate_clef`'s `margin_below_floor` narrowing) beside the value
the other-systems majority supplied, because the whole question a reader
needs settled here is "is the value this rule chose really one of the two
or three the contest could not separate, printed at this exact staff".

⚠️ THE FRAME CONTROL AND THE ROW INDEX ARE IMPORTED, NOT COPIED, from
`benchmarks/omr-infer-duration-print-2026-09/probe/crop_inferred.py` — same
reason `crop_clef.py` gives.

    python3 benchmarks/omr-no-pitch-2026-09/probe/crop_filled_2_10b.py \\
        --arm benchmarks/omr-no-pitch-2026-09/out/210b-arm/litolff-2-10b-arm.record.json \\
        --pdf <the Litolff edition.pdf> --label litolff-210b \\
        --subject staff/6/1/9 --subject staff/10/0/9 \\
        --out-dir benchmarks/omr-no-pitch-2026-09/out/print
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "benchmarks" / "omr-infer-duration-print-2026-09"
                      / "probe"))

from crop_inferred import _frame_ok                       # noqa: E402
from tools.omr.staged.record_io import load_record        # noqa: E402

RULE = "fill_clef_gap"


def _index(rec):
    want = {"cell_box", "staff_lines", "staff_spacing"}
    out = {}
    for o in rec["observations"]:
        if o["quantity"] in want:
            out.setdefault(o["quantity"], {})[o["subject"]] = o["value"]
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True,
                    help="the ARM record from replay.py --write-arm")
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--subject", action="append", required=True,
                    help="staff/<p>/<s>/<st>, repeatable, ≤6 total")
    ap.add_argument("--out-dir",
                    default="benchmarks/omr-no-pitch-2026-09/out/print")
    ap.add_argument("--width-spaces", type=float, default=22.0)
    ap.add_argument("--pad-spaces", type=float, default=5.0)
    a = ap.parse_args()

    if len(a.subject) > 6:
        print(f"⚠️ {len(a.subject)} subjects named, over the 6-crop budget; "
              "refusing rather than silently cropping all of them.",
              file=sys.stderr)
        return 2

    import fitz
    import numpy as np
    from PIL import Image, ImageDraw

    d = load_record(a.arm)
    rec = d["record"] if "record" in d else d
    idx = _index(rec)

    superseded = {v["supersedes"] for v in rec["verdicts"] if v.get("supersedes")}
    by_subject = {v["subject"]: v for v in rec["verdicts"]
                 if v["quantity"] == "clef" and v["id"] not in superseded
                 and str(v.get("decider", "")).endswith(RULE)}
    jobs = []
    missing = []
    for s in a.subject:
        v = by_subject.get(s)
        if v is None:
            missing.append(s)
            continue
        jobs.append(v)
    if missing:
        print(f"⚠️ NOT FOUND as a live `fill_clef_gap` verdict on this arm: "
              f"{missing}. Either the subject was never filled, or its "
              f"verdict has since been superseded.", file=sys.stderr)

    print(f"{len(jobs)} of {len(a.subject)} requested subjects to crop")

    out_dir = Path(a.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(a.pdf)
    pages, frames = {}, {}
    manifest, refused = [], [{"staff": s, "why": "not found"} for s in missing]

    for v in jobs:
        subj = v["subject"]
        _, p, sy, st = subj.split("/")
        p, sy, st = int(p), int(sy), int(st)
        lines = idx["staff_lines"].get(subj)
        spacing = idx["staff_spacing"].get(subj)
        cbox = idx["cell_box"].get(f"cell/{p}/{sy}/{st}/0")
        if not all((lines, spacing, cbox)):
            refused.append({"staff": subj, "why": "geometry missing"})
            continue

        if p not in pages:
            pm = doc[p].get_pixmap(dpi=a.dpi)
            im = (Image.frombytes("RGB", (pm.width, pm.height), pm.samples)
                  if pm.n >= 3 else
                  Image.frombytes("L", (pm.width, pm.height),
                                  pm.samples).convert("RGB"))
            pages[p] = im
            frames[p] = np.asarray(im.convert("L"), dtype=float)
        im, arr = pages[p], frames[p]

        ok, contrast = _frame_ok(arr, lines, spacing)
        if not ok:
            refused.append({"staff": subj, "why": "FRAME CONTROL FAILED",
                            "contrast": round(contrast, 2)})
            continue

        sp = float(spacing)
        x0 = max(0, cbox[0] - 2.0 * sp)
        x1 = min(im.width, x0 + a.width_spaces * sp)
        y0 = max(0, min(lines) - a.pad_spaces * sp)
        y1 = min(im.height, max(lines) + a.pad_spaces * sp)
        crop = im.crop((int(x0), int(y0), int(x1), int(y1)))
        Z = 4
        crop = crop.resize((crop.width * Z, crop.height * Z), Image.LANCZOS)
        dr = ImageDraw.Draw(crop)

        for ly in lines:
            y = (ly - y0) * Z
            if 0 <= y < crop.height:
                dr.line([(0, y), (crop.width, y)], fill=(0, 160, 60), width=1)

        hx0, hx1 = 2, int((cbox[0] + 4.0 * sp - x0) * Z)
        hy0, hy1 = (min(lines) - y0 - 1.5 * sp) * Z, (max(lines) - y0 + 1.5 * sp) * Z
        arm_len = max(8, int((hx1 - hx0) * 0.25))
        R, W = (220, 0, 0), 2
        for (ax, ay, dx, dy) in ((hx0, hy0, 1, 1), (hx1, hy0, -1, 1),
                                 (hx0, hy1, 1, -1), (hx1, hy1, -1, -1)):
            dr.line([(ax, ay), (ax + dx * arm_len, ay)], fill=R, width=W)
            dr.line([(ax, ay), (ax, ay + dy * arm_len)], fill=R, width=W)

        step = sp * Z
        y, k = (lines[0] - y0) * Z, 0
        while y < crop.height:
            if y >= 0:
                dr.line([(2, y), (14 if k % 5 else 22, y)],
                        fill=(0, 90, 200), width=1)
            y += step
            k += 1

        det = v.get("detail") or {}
        # ⚠️ `candidates` TRAVELS ON THE VERDICT ITSELF (`infer._admit`:
        # "the candidates the reader kept travel FORWARD onto the inferred
        # verdict"), NOT inside `detail` -- `detail["candidates"]` is only
        # set on a DECLINE (`clef_gap_census`'s own record of what it turned
        # down), which this crop never shows because it crops FILLS.
        candidates = [c["value"] for c in (v.get("candidates") or ())]
        prior_outcome = det.get("prior_outcome")
        band_h = 86
        out_im = Image.new("RGB", (crop.width, crop.height + band_h), "white")
        out_im.paste(crop, (0, band_h))
        cd = ImageDraw.Draw(out_im)
        cd.text((6, 4), f"{subj}   page {p} (pdf index), system {sy}, "
                        f"staff {st}", fill=(0, 0, 0))
        cd.text((6, 20), "FILED ON this staff — its 5 lines are drawn GREEN; "
                         "the RED bracket is the header window",
                fill=(0, 120, 45))
        if prior_outcome == "narrowed":
            cd.text((6, 36),
                    f"⚠️ ROADMAP 2.10b: the reader NARROWED this staff's own "
                    f"clef to {candidates} (margin_below_floor) and could "
                    f"not separate them. INFERRED: {v.get('value')}, chosen "
                    f"from THAT set by the other systems' majority.",
                    fill=(140, 0, 0))
        else:
            cd.text((6, 36),
                    f"the reader ABSTAINED here (no_candidates). INFERRED "
                    f"CLEF: {v.get('value')}   ({v.get('reason')})",
                    fill=(140, 0, 0))
        cd.text((6, 60), f"part: slot {det.get('slot')} "
                         f"{det.get('instrument') or '(unnamed)'}   |   other "
                         f"systems read {det.get('tally')}   |   independent "
                         f"witnesses {det.get('n_independent_witnesses')}",
                fill=(60, 60, 60))

        name = (f"{a.label}-p{p}-s{sy}-st{st}-{prior_outcome}-"
                f"{v.get('value')}.png")
        out_im.save(out_dir / name)
        manifest.append({
            "file": name, "staff": subj,
            "inferred_clef": v.get("value"), "reason": v.get("reason"),
            "prior_outcome": prior_outcome, "candidates": candidates,
            "slot": det.get("slot"), "instrument": det.get("instrument"),
            "tally": det.get("tally"),
            "n_systems_read": det.get("n_systems_read"),
            "n_independent_witnesses": det.get("n_independent_witnesses"),
            "page": p, "system": sy, "staff_ordinal": st,
            "frame_contrast": round(contrast, 2),
            "dpi": a.dpi,
            # ⚠️ Sean's column. It stays null until he has looked.
            "VERDICT_none_yet": None,
        })

    (out_dir / f"crop-manifest-{a.label}.json").write_text(
        json.dumps({"crops": manifest, "refused": refused}, indent=2))
    print(f"wrote {len(manifest)} crops, refused {len(refused)}")
    for r in refused:
        print("  REFUSED", r)
    return 0 if not refused else 1


if __name__ == "__main__":
    raise SystemExit(main())
