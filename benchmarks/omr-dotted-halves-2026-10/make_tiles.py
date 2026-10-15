"""2.130 blind tiles for Sean: `python3 benchmarks/omr-dotted-halves-2026-10/make_tiles.py REC_DIR OUT_DIR` where REC_DIR holds bra{6,7,10}-base.json
(GATHER+ADJUDICATE records) and rp-bra{p}-{off,on}.json (replay.py outputs). Nothing of ours is drawn but a small red corner bracket on the head.
Question on the sheet: what is this note's value? (quarter / half / dotted half / whole / other). Order is shuffled with a fixed seed; the hidden
manifest (what flag OFF said, what ON says, the role of each tile) is written to OUT_DIR/_hidden/manifest.json."""
import json, random, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, ".")
from tools.omr.preprocessing import render_page
from tools.omr.staged import readout as RO

BRA = "library/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"
SP = 27.5
CHANGED = ["glyph/10/1/3/3/22", "glyph/7/1/3/10/17", "glyph/6/1/0/5/23",   # Sean's 2.127 tiles 9, 10, 13
           "glyph/10/1/3/4/12", "glyph/10/1/5/3/7", "glyph/10/1/6/3/18", "glyph/10/1/13/3/6", "glyph/10/1/13/0/20",
           "glyph/7/0/3/4/19", "glyph/7/1/3/4/21", "glyph/6/1/5/8/6", "glyph/6/0/5/7/12", "glyph/7/1/2/7/4"]
CONTROLS = {}   # filled from the records: one unchanged half-class half note, one unchanged black quarter


def sig(r):
    if r is None:
        return None
    if r["outcome"] == "decided":
        v = r["value"]
        return {"decided": v.get("written") if isinstance(v, dict) else v, "reason": r["reason"]}
    return {"narrowed": sorted({c.get("written") for c in r["cands"]}), "reason": r["reason"]}


def main(rec_dir, out_dir):
    rec_dir, out = Path(rec_dir), Path(out_dir)
    (out / "_hidden").mkdir(parents=True, exist_ok=True)
    runs, off, on, pages = {}, {}, {}, {}
    for p in (6, 7, 10):
        runs[p] = RO.load_run(str(rec_dir / f"bra{p}-base.json"))
        off[p] = json.load(open(rec_dir / f"rp-bra{p}-off.json"))["durations"]
        on[p] = json.load(open(rec_dir / f"rp-bra{p}-on.json"))["durations"]
    # controls: first two unchanged glyphs of the right kind that are plainly decided
    ctl = []
    for want_cls, want_val in (("noteheadHalf", 2.0), ("noteheadBlack", 1.0)):
        for p in (10, 7, 6):
            for g in runs[p].glyphs.values():
                r = on[p].get(g.key)
                if (g.cls or "").startswith(want_cls) and r and r["outcome"] == "decided" and r["reason"] == "head_and_marks" \
                        and r["value"].get("written") == want_val and sig(off[p][g.key]) == sig(r) and g.box_page \
                        and (want_cls != "noteheadBlack" or r["value"].get("beam_levels") == 0) \
                        and 1.2 * SP <= (g.box_page[2] - g.box_page[0]) < 1.9 * SP and (g.box_page[3] - g.box_page[1]) >= 0.8 * SP \
                        and [v.get("reason") for v in runs[p].verdicts_at(g.key, None, "head_stem")] == ["one_stem"] \
                        and (min(runs[p].obs_at(g.key, "notehead_ink")[-1].get("detail", {}).get(k, {}).get("windows", {}).get("center", 9)
                                 for k in ("ink_raw", "ink_net", "ink_off_line")) <= 0.6 if want_cls == "noteheadHalf" else
                             min(runs[p].obs_at(g.key, "notehead_ink")[-1].get("detail", {}).get(k, {}).get("windows", {}).get("center", 0)
                                 for k in ("ink_raw", "ink_net", "ink_off_line")) >= 0.95):
                    ctl.append((g.key, "control_" + want_cls)); break
            else:
                continue
            break
    items = [(k, "changed" if k not in CHANGED[:3] else "sean_2.127_tile") for k in CHANGED] + ctl
    random.Random(130).shuffle(items)
    tiles, manifest = [], []
    for i, (key, role) in enumerate(items, 1):
        p = int(key.split("/")[1]); g = runs[p].glyphs[key]
        if p not in pages:
            im = render_page(Path(BRA), p, dpi=600).rgb
            im = im if im.ndim == 2 else im[..., :3].mean(axis=2)
            pages[p] = np.where(im < 128, 0, 255).astype(np.uint8)
        x0, y0, x1, y1 = g.box_page; cx, cy = (x0 + x1) / 2, (y0 + y1) / 2; r = int(2.6 * SP)
        crop = pages[p][max(0, int(cy - r)):int(cy + r), max(0, int(cx - r)):int(cx + r)]
        S = 300; I = Image.fromarray(crop).convert("RGB").resize((S, S)); d = ImageDraw.Draw(I); s = S / (2 * r)
        bx0, by0, bx1, by1 = [(v - o) * s for v, o in zip((x0, y0, x1, y1), (cx - r, cy - r, cx - r, cy - r))]
        L = 14
        for (px, py, dx, dy) in ((bx0, by0, 1, 1), (bx1, by0, -1, 1), (bx0, by1, 1, -1), (bx1, by1, -1, -1)):
            d.line([(px, py), (px + dx * L, py)], fill=(255, 0, 0), width=2); d.line([(px, py), (px, py + dy * L)], fill=(255, 0, 0), width=2)
        d.text((4, 4), str(i), fill=(0, 0, 255)); tiles.append(I)
        manifest.append({"tile": i, "subject": key, "role": role, "class": g.cls, "flag_off": sig(off[p].get(key)), "flag_on": sig(on[p].get(key))})
    cols = 4; w = h = 300; rows = (len(tiles) + cols - 1) // cols
    head = 28; sheet = Image.new("RGB", (w * cols, h * rows + head), "white")
    ImageDraw.Draw(sheet).text((6, 8), "What is the red-cornered note's value?   quarter / half / dotted half / whole / other", fill=(0, 0, 0))
    for i, t in enumerate(tiles):
        sheet.paste(t, ((i % cols) * w, head + (i // cols) * h))
    sheet.save(out / "values-review.png")
    (out / "_hidden" / "manifest.json").write_text(json.dumps(manifest, indent=1))
    print("tiles", len(tiles), "->", out)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
