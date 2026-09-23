"""ROADMAP 2.10 — one HEADER crop per staff whose clef the INFER stage wrote.

Every clef this rule fills is a guess about ink nobody could read, so the only
thing that can settle whether it is right is the print. This cuts the header
of each such staff — the strip where the clef is engraved — at the gather's
own DPI, with that staff's own five `Q.STAFF_LINES` drawn, and names the
inferred clef and the tier it came from in the caption.

⚠️ THE FRAME CONTROL AND THE ROW INDEX ARE IMPORTED, NOT COPIED, from
`benchmarks/omr-infer-duration-print-2026-09/probe/crop_inferred.py`. A second
copy of a control is a control that can drift from the one it was measured
against; `omr-notehead-funnel-2026-09/probe/crop_funnel.py` imports the same
two for the same reason. A page that fails the control is REFUSED and listed,
never cropped with a caveat.

⚠️ THE SUBJECT IS THE STAFF, SO THE STAFF IS WHAT IS MARKED. Sean, 2026-09-23,
on an earlier crop: *"there is a staff at the top and a staff at the bottom -
i dont know which staff the cell is focussing on."* The five GREEN lines are
the record's own `Q.STAFF_LINES` for the staff named in the caption, and the
RED bracket is the header window — the strip from the staff's first cell's
left edge, where a clef is printed.

⚠️ WHAT THIS CROP CAN AND CANNOT SETTLE. It shows what is actually engraved at
the head of the staff, which is the whole question for tier (3) and for the
value of tier (2). It does NOT show whether the OTHER systems the majority was
taken over were read correctly — that needs their headers too, and the tally
on the verdict names how many there were.

    python3 benchmarks/omr-clef-gap-2026-09/probe/crop_clef.py \\
        --arm <replay.py --write-arm dir>/<id>-arm.record.json \\
        --pdf <edition.pdf> --label litolff --dpi 600 \\
        --out-dir benchmarks/omr-clef-gap-2026-09/out/print
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
    """(quantity, subject) -> value, for the quantities THIS probe reads.

    ⚠️ Its own `want` set rather than `crop_inferred._index`'s: that one is
    keyed on a GLYPH's geometry and does not carry `cell_box` for a staff's
    first cell in a form this probe can find by name. The FRAME CONTROL, which
    is the part that can be wrong, is imported.
    """
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
    ap.add_argument("--out-dir",
                    default="benchmarks/omr-clef-gap-2026-09/out/print")
    ap.add_argument("--width-spaces", type=float, default=22.0,
                    help="header window width in STAFF SPACES from the "
                         "staff's first cell's left edge")
    ap.add_argument("--pad-spaces", type=float, default=5.0,
                    help="vertical air above and below the staff")
    a = ap.parse_args()

    import fitz
    import numpy as np
    from PIL import Image, ImageDraw

    d = load_record(a.arm)
    rec = d["record"] if "record" in d else d
    idx = _index(rec)

    superseded = {v["supersedes"] for v in rec["verdicts"] if v.get("supersedes")}
    jobs = [v for v in rec["verdicts"]
            if v["quantity"] == "clef" and v["id"] not in superseded
            and str(v.get("decider", "")).endswith(RULE)]
    jobs.sort(key=lambda v: v["subject"])
    print(f"{len(jobs)} inferred clefs to crop")
    if not jobs:
        # ⚠️ Reach before accuracy. Zero crops because the document holds no
        # unread clef and zero because the probe is broken are the same number
        # on disk, so the tool says which.
        print("⚠️ NOTHING TO CROP. Either the arm record carries no inferred "
              "clef, or `--arm` is the BASE file.", file=sys.stderr)

    out_dir = Path(a.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(a.pdf)
    pages, frames = {}, {}
    manifest, refused = [], []

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

        # ⚠️ THE HEADER IS LEFT OF THE FIRST CELL'S LEFT EDGE AND A LITTLE
        # INSIDE IT. A measure cell is padded (CLAUDE.md §10), so cell 0's box
        # already starts before the first barline; the window runs from a
        # little further left, to catch a clef engraved in front of it.
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

        # ⚠️ THE HEADER WINDOW, BRACKETED. It is where a clef would be, not a
        # claim that one is there -- on this staff the reader found none.
        hx0, hx1 = 2, int((cbox[0] + 4.0 * sp - x0) * Z)
        hy0, hy1 = (min(lines) - y0 - 1.5 * sp) * Z, (max(lines) - y0 + 1.5 * sp) * Z
        arm_len = max(8, int((hx1 - hx0) * 0.25))
        R, W = (220, 0, 0), 2
        for (ax, ay, dx, dy) in ((hx0, hy0, 1, 1), (hx1, hy0, -1, 1),
                                 (hx0, hy1, 1, -1), (hx1, hy1, -1, -1)):
            dr.line([(ax, ay), (ax + dx * arm_len, ay)], fill=R, width=W)
            dr.line([(ax, ay), (ax, ay + dy * arm_len)], fill=R, width=W)

        # a ruler: one tick per staff space down the left edge
        step = sp * Z
        y, k = (lines[0] - y0) * Z, 0
        while y < crop.height:
            if y >= 0:
                dr.line([(2, y), (14 if k % 5 else 22, y)],
                        fill=(0, 90, 200), width=1)
            y += step
            k += 1

        det = v.get("detail") or {}
        band_h = 70
        out_im = Image.new("RGB", (crop.width, crop.height + band_h), "white")
        out_im.paste(crop, (0, band_h))
        cd = ImageDraw.Draw(out_im)
        cd.text((6, 4), f"{subj}   page {p} (pdf index), system {sy}, "
                        f"staff {st}", fill=(0, 0, 0))
        cd.text((6, 20), f"FILED ON this staff — its 5 lines are drawn GREEN; "
                         f"the RED bracket is the header window",
                fill=(0, 120, 45))
        cd.text((6, 36), f"the reader ABSTAINED here. INFERRED CLEF: "
                         f"{v.get('value')}   ({v.get('reason')})",
                fill=(140, 0, 0))
        cd.text((6, 52), f"part: slot {det.get('slot')} "
                         f"{det.get('instrument') or '(unnamed)'}   |   other "
                         f"systems read {det.get('tally')}   |   independent "
                         f"witnesses {det.get('n_independent_witnesses')}",
                fill=(60, 60, 60))

        name = (f"{a.label}-p{p}-s{sy}-st{st}-"
                f"{v.get('value')}-{v.get('reason')}.png")
        out_im.save(out_dir / name)
        manifest.append({
            "file": name, "staff": subj,
            "inferred_clef": v.get("value"), "reason": v.get("reason"),
            "slot": det.get("slot"), "instrument": det.get("instrument"),
            "tally": det.get("tally"),
            "n_systems_read": det.get("n_systems_read"),
            "n_independent_witnesses": det.get("n_independent_witnesses"),
            "part_from_an_inference": det.get("part_from_an_inference"),
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
