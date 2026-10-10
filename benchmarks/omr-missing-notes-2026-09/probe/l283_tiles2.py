#!/usr/bin/env python3
"""l283_tiles2: the blind tiles for Sean -- ROADMAP 2.83, same style as `out/print/2.81-review/` (this replaces `l283_tiles.py`, which
took one arm record per movement; the arm here is several records).

QUESTION on every tile: *What is the printed value of the note in the red brackets?* Nothing of ours is drawn but a red corner
bracket on the head. Our reading (BASE and ARM) and every other hidden field is in `manifest.json` only, never on the tile.

THE SAMPLE: heads whose standing ADJUDICATE duration verdict CHANGED between base and arm (`l283_compare.py --list-changed`), drawn at
random per CLASS of change so the rare classes are not drowned by the common one:
    tip      the arm decided / narrowed it by the TIP reader (`hooks_counted`, `flag_ink_unread`)
    reach    the arm attached a detector flag box to a stem only the ruler read (`head_and_marks`, level 1)
    hollow   the 2.70 bare-stem rule (`hollow_head_bare_stem`) fired or stopped firing where the tip became readable
    regress  base decided a level >= 1 that the arm no longer decides (a flag lost): ALL of them are drawn, up to the cap
    other    anything else that changed
Sean's 30 already-judged 2.81 tiles are excluded. Plus CONTROLS from his hand-truth page (Brahms pdf 0): heads his boxes show FLAGGED
(an eighth) and BARE (a quarter). The cut, the normalisation (32 px per staff space) and the frame control (a control that can fail: the
same measure on the page shifted 1.6 head widths must fail on most tiles) are `l281_tiles.cut` / `frame_control`.

    python3 l283_tiles2.py --out DIR --seed 20261010 --spec brahms=ARM.json:CHANGED.json ... --spec litolff=ARM.json:CHANGED.json ...
        --controls truth_rows.json:ARM_CONTROL_RECORD.json --plan tip=3,reach=2,hollow=2,regress=2,other=1 --n-controls 4
"""
import argparse
import collections
import json
import random
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import cv2  # noqa: E402
import numpy as np  # noqa: E402

from l281_tiles import PDFS, QUESTION, TILE_SP, cut, frame_control  # noqa: E402
from l283_tiles import head_info  # noqa: E402
from tools.omr.staged import readout as RD  # noqa: E402

JUDGED = REPO / "out" / "print" / "2.81-review" / "manifest.json"


def klass(c):
    base, arm = c["base"], c["arm"]
    blv = c["base"].split("{")[1].rstrip("}") if "{" in base else ""
    alv = c["arm"].split("{")[1].rstrip("}") if "{" in arm else ""
    if "hollow_head_bare_stem" in arm or "hollow_head_bare_stem" in base:
        return "hollow"
    if base.startswith("decided") and blv and int(blv.split(",")[0]) >= 1 and not (arm.startswith("decided") and alv and int(alv.split(",")[0]) >= 1):
        return "regress"
    if "head_and_marks{1}" in arm or "head_and_marks{2}" in arm:
        return "reach"
    if "hooks_counted" in arm or "flag_ink_unread" in arm:
        return "tip"
    return "other"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=20261010)
    ap.add_argument("--spec", action="append", required=True, help="movement=arm.json:changed.json (repeatable)")
    ap.add_argument("--controls", default=None, help="truth_rows.json:arm_record.json (Brahms pdf 0-1)")
    ap.add_argument("--plan", default="tip=3,reach=2,hollow=2,regress=2,other=1")
    ap.add_argument("--n-controls", type=int, default=4)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(a.seed)
    judged = {t["hidden"]["key"] for t in json.loads(JUDGED.read_text())["tiles"] if t["kind"] == "sample"}
    plan = {k: int(v) for k, v in (p.split("=") for p in a.plan.split(","))}
    pool = collections.defaultdict(list)
    runs = {}
    for spec in a.spec:
        mv, rest = spec.split("=", 1)
        arm, ch = rest.split(":", 1)
        run = RD.load_run(arm)
        runs[(mv, arm)] = run
        for c in json.loads(Path(ch).read_text()):
            if c["key"] in judged or not c.get("box_page"):
                continue
            c = dict(c, movement=mv, arm_record=arm)
            pool[klass(c)].append(c)
    items = []
    for k, n in plan.items():
        rows = sorted(pool.get(k, []), key=lambda c: c["key"])
        rng.shuffle(rows)
        # spread over the movements: take round-robin
        by_mv = collections.defaultdict(list)
        for c in rows:
            by_mv[c["movement"]].append(c)
        picked, i = [], 0
        mvs = sorted(by_mv)
        while len(picked) < n and any(by_mv.values()):
            m = mvs[i % len(mvs)]
            if by_mv[m]:
                picked.append(by_mv[m].pop())
            i += 1
        for c in picked:
            items.append({"kind": "sample", "class": k, "c": c})
        print(f"class {k}: pool {len(rows)}, drawn {len(picked)}")
    if a.controls:
        rows_p, ctl_rec = a.controls.split(":", 1)
        rows = json.loads(Path(rows_p).read_text())
        ctl_run = RD.load_run(ctl_rec)
        flagged = [r for r in rows if r["kind"] == "flag" and r.get("arm_key")]
        bare = [r for r in rows if r["kind"] == "bare" and r.get("arm_key")]
        rng.shuffle(flagged)
        rng.shuffle(bare)
        half = a.n_controls // 2
        for r in flagged[:half]:
            items.append({"kind": "control", "control": "flagged", "r": r, "run": ctl_run})
        for r in bare[:a.n_controls - half]:
            items.append({"kind": "control", "control": "bare", "r": r, "run": ctl_run})
    from tools.omr.preprocessing import render_page
    rendered = {}

    def page_img(mv, page):
        k = (mv, page)
        if k not in rendered:
            if len(rendered) > 3:
                rendered.pop(next(iter(rendered)))
            rendered[k] = render_page(PDFS[mv], page, dpi=600).rgb
        return rendered[k]
    order = list(range(len(items)))
    random.Random(a.seed + 2).shuffle(order)
    manifest = {"question": QUESTION, "seed": a.seed, "plan": plan,
                "excluded": "the 30 heads Sean judged on out/print/2.81-review (and Brahms pdf 0 from the sample: its heads are the controls)",
                "tile_scale": f"{TILE_SP:.0f} px per staff space on every tile (600 dpi page, normalised)", "tiles": []}
    fc_true, fc_wrong = [], []
    n_s = n_c = 0
    for pos in order:
        it = items[pos]
        if it["kind"] == "sample":
            c = it["c"]
            run = runs[(c["movement"], c["arm_record"])]
            key, mv = c["key"], c["movement"]
            n_s += 1
            tid = f"tile_{n_s:02d}"
            hidden = {"key": key, "movement": mv, "pdf_page": c["page"], "change_class": it["class"],
                      "base_reading": c["base"], "arm_reading": c["arm"], "base_status": c["base_status"], "arm_status": c["arm_status"]}
        else:
            r = it["r"]
            run = it["run"]
            key, mv = r["arm_key"], "brahms"
            n_c += 1
            tid = f"control_{n_c}"
            hidden = {"key": key, "movement": "brahms", "pdf_page": 0, "control": it["control"],
                      "truth": {"rule": "Sean's hand-truth boxes (Brahms pdf 0): "
                                        + ("a flag is on this head's stem: an EIGHTH" if it["control"] == "flagged"
                                           else "nothing on its stem: a QUARTER"),
                                "truth_id": r["truth"], "truth_level": r["level"]},
                      "base_reading": str(r["base"]), "arm_reading": str(r["arm"])}
        box, sp, stem, page = head_info(run, key)
        img = page_img(mv, page)
        crop, win = cut(img, box, sp, stem)
        cv2.imwrite(str(out / f"{tid}.png"), cv2.cvtColor(crop, cv2.COLOR_RGB2BGR))
        gray = img.mean(axis=2)
        t, l, r_ = frame_control(gray, box)
        t_w, l_w, r_w = frame_control(gray, box, shift_px=int(1.6 * (box[2] - box[0])))
        fc_true.append((t, l, r_))
        fc_wrong.append((t_w, l_w, r_w))
        manifest["tiles"].append({"id": tid, "file": f"{tid}.png", "question": QUESTION, "kind": it["kind"], "hidden": hidden,
                                  "window_page_px": list(win), "space_px_native": round(sp, 2),
                                  "frame_control": {"inside": round(t, 3), "left": round(l, 3), "right": round(r_, 3)}})
    ok_true = sum(1 for t, l, r_ in fc_true if t is not None and t > (l or 0) and t > (r_ or 0))
    ok_wrong = sum(1 for t, l, r_ in fc_wrong if t is not None and t > (l or 0) and t > (r_ or 0))
    manifest["frame_control"] = {"n": len(fc_true), "true_frame_inside_beats_both_neighbours": ok_true,
                                 "wrong_frame_(page_shifted_1.6_heads)_inside_beats_both": ok_wrong,
                                 "reading": "the control can fail: it must pass on the true frame and mostly fail on the shifted one"}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1, default=str))
    (out / "answers.template.json").write_text(json.dumps({t["id"]: None for t in sorted(manifest["tiles"], key=lambda t: t["id"])}, indent=1) + "\n")
    (out / "frame_control.txt").write_text(json.dumps(manifest["frame_control"], indent=1) + "\n")
    print("frame control:", manifest["frame_control"])
    print("wrote", len(manifest["tiles"]), "tiles to", out)


if __name__ == "__main__":
    main()
