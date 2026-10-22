"""ROADMAP 2.114 round 2 blind tiles: `out/print/2.114-round2/`. Same format and question as round 1 (`make_tiles.py`): one question per tile,
*Hollow or black? (or: not a note)*, 32 px per staff space, the print as printed, ONE red corner bracket on the subject box, NOTHING of ours drawn.
Sources (cap 20 incl. 2 controls; none of the 17 already answered is re-asked):
  * THRESHOLD tiles (from `interior_variants.json`, Litolff 95 clean cells): the 8 lowest-reading production "black" boxes under variant (c) (the
    staff/barline junction skipped) and the 3 highest-reading truth hollow heads. The manifest records their interior readings under (a), (b), (c).
  * ROUND-2 tiles: heads the second detector touched in the NEW ON record that round 1 did not ask about, spread over how the rule settled them.
  * 2 controls of known answer (a Brahms truth-black head and a Brahms hollow head both detectors call hollow), not the two used in round 1.
usage: make_tiles2.py interior_variants.json rec-lit-on.json rec-bra-on.json score.json OUTDIR"""
import collections, json, random, sys
from pathlib import Path
import cv2, numpy as np
sys.path.insert(0, ".")
from tools.omr.preprocessing import render_page
from tools.omr.staged import readout as RO
LIT = "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf"
BRA = "/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"
PAGES = {"litolff": (LIT, 1), "brahms": (BRA, 0)}
QUESTION = "Hollow or black? (or: not a note)"
CAP, HDR = 20, 56
ASKED = {t["hidden"]["key"] for t in json.load(open("out/print/2.114-second-detector/manifest.json"))["tiles"]}

def main():
    iv, lit_p, bra_p, score_p, out = sys.argv[1:6]
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    items = []
    d = json.load(open(iv))["items"]
    L = [i for i in d if i["page"] == "litolff" and i["c"] is not None]
    blacks = sorted([i for i in L if i["label"] == "black"], key=lambda i: i["c"])[1:9]
    holl = sorted([i for i in L if i["label"] == "hollow"], key=lambda i: -i["c"])[:3]
    for i in blacks + holl:
        items.append(dict(doc="litolff", key=i["key"], rect=i["box"], sp=15.75, group="THRESHOLD " + ("black-labelled (production black box, no truth hollow)" if i["label"] == "black" else "truth hollow head"),
                          truth=("production black, not a truth hollow head" if i["label"] == "black" else "truth hollow head"),
                          interior={"a_current": i["a"], "b_recentred": i["b"], "c_recentred_line_rows_out": i["c"]}, threshold_tile=True))
    runs = {"litolff": RO.load_run(lit_p), "brahms": RO.load_run(bra_p)}
    score = json.load(open(score_p))["arms"]["on"]
    rows = []
    for t in score["touched"]:
        if t["relation"] == "agrees" or t["key"] in ASKED or t["doc"] not in runs:
            continue
        g = runs[t["doc"]].glyphs[t["key"]]
        sp = staff_space_page(runs[t["doc"]], g)
        if g.box_page is None or not sp:
            continue
        rows.append({**t, "rect": list(g.box_page), "sp": sp, "group": f"{t['relation']} / {t['settled']}"})
    groups = collections.defaultdict(list)
    for r in rows:
        groups[(r["doc"], r["group"])].append(r)
    budget = CAP - 2 - len(items)
    pick = []
    keys = sorted(groups, key=lambda k: -len(groups[k]))
    while len(pick) < budget and any(groups[k] for k in keys):          # round-robin over groups, biggest first
        for k in keys:
            if groups[k] and len(pick) < budget:
                pick.append(groups[k].pop(len(groups[k]) // 2))
    for r in pick:
        items.append({**{k: r[k] for k in ("doc", "key", "relation", "settled", "reason", "truth", "group") if k in r}, "rect": r["rect"], "sp": r["sp"], "threshold_tile": False})
    # controls (Brahms): a hollow head both detectors call hollow, a truth BLACK head -- neither used in round 1
    ctrl = []
    agrees = [t for t in score["touched"] if t["relation"] == "agrees" and t["truth"] == "truth hollow head" and t["doc"] == "brahms" and t["key"] not in ASKED]
    g = runs["brahms"].glyphs[agrees[0]["key"]]
    ctrl.append(dict(doc="brahms", key=g.key, rect=list(g.box_page), sp=staff_space_page(runs["brahms"], g), group="CONTROL hollow (both detectors, truth hollow)", expected="hollow", threshold_tile=False))
    from tools.omr.hand_truth import store as ST
    page = ST.load(Path("data/hand-truth/pages/imslp317803/0.json"))
    run = runs["brahms"]
    blacks_t = [b for b in page.boxes if b.cls.startswith("noteheadBlack")]
    for b in blacks_t[len(blacks_t) // 2::max(1, len(blacks_t) // 7)]:
        gm = [g for g in run.glyphs.values() if g.box_page and (g.cls or "").startswith("noteheadBlack") and g.key not in ASKED
              and abs((g.box_page[0] + g.box_page[2]) / 2 - (b.rect[0] + b.rect[2]) / 2) < 6 and abs((g.box_page[1] + g.box_page[3]) / 2 - (b.rect[1] + b.rect[3]) / 2) < 6 and staff_space_page(run, g)]
        if gm:
            g = gm[0]
            ctrl.append(dict(doc="brahms", key=g.key, rect=list(g.box_page), sp=staff_space_page(run, g), group="CONTROL black (truth black)", expected="black", threshold_tile=False))
            break
    items += ctrl
    random.Random(20261014).shuffle(items)
    imgs, tiles = {}, []
    for n, it in enumerate(items, 1):
        pdf, idx = PAGES[it["doc"]]
        if it["doc"] not in imgs:
            imgs[it["doc"]] = render_page(Path(pdf), idx, dpi=600).rgb
        img = imgs[it["doc"]]
        x0, y0, x1, y1 = it["rect"]; sp = it["sp"]
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        ax0, ay0 = int(max(0, cx - 6 * sp)), int(max(0, cy - 6.5 * sp))
        ax1, ay1 = int(min(img.shape[1], cx + 6 * sp)), int(min(img.shape[0], cy + 6.5 * sp))
        crop = img[ay0:ay1, ax0:ax1].copy(); sc = 32.0 / sp
        crop = cv2.resize(crop, None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA)
        bx0, by0, bx1, by1 = [int(round(v * sc)) for v in (x0 - ax0, y0 - ay0, x1 - ax0, y1 - ay0)]
        L_ = 10
        for (px, py, dx, dy) in ((bx0, by0, 1, 1), (bx1, by0, -1, 1), (bx0, by1, 1, -1), (bx1, by1, -1, -1)):
            cv2.line(crop, (px, py), (px + dx * L_, py), (220, 30, 30), 2)
            cv2.line(crop, (px, py), (px, py + dy * L_), (220, 30, 30), 2)
        h, w = crop.shape[:2]
        canvas = np.full((h + HDR, max(w, 384), 3), 255, np.uint8); canvas[HDR:, :w] = crop
        cv2.putText(canvas, str(n), (10, HDR - 10), cv2.FONT_HERSHEY_SIMPLEX, 1.9, (0, 0, 0), 4, cv2.LINE_AA)
        cv2.putText(canvas, QUESTION, (70 if n < 10 else 110, HDR - 18), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (60, 60, 60), 1, cv2.LINE_AA)
        cv2.line(canvas, (0, HDR - 1), (canvas.shape[1], HDR - 1), (200, 200, 200), 1)
        fpath = out / f"tile_{n:02d}.png"
        cv2.imwrite(str(fpath), cv2.cvtColor(canvas, cv2.COLOR_RGB2BGR))
        tiles.append({"n": n, "file": fpath.name, "question": QUESTION, "hidden": {k: v for k, v in it.items() if k != "sp"}, "page_box_600dpi": [round(v) for v in it["rect"]], "dpi": 600})
    (out / "manifest.json").write_text(json.dumps({"question": QUESTION, "tile_scale": "32 px per staff space", "tiles": tiles}, indent=1))
    (out / "answers.template.json").write_text(json.dumps({f"tile_{t['n']:02d}": None for t in tiles}, indent=1))
    (out / "LEGEND.md").write_text(
        f"# 2.114 round 2 blind tiles ({len(tiles)})\n\nOne question on every tile: **is the note inside the red bracket hollow (white inside), black, or not a note at all?**\n"
        "The red corner bracket only says which mark; nothing of ours is drawn. 32 px per staff space. Random order; two are controls of known answer.\n"
        "Write answers in `answers.json` (copy `answers.template.json`: \"hollow\", \"black\" or \"not a note\"). `manifest.json` (what each detector said, which tiles are "
        "closest-call threshold tiles and their interior readings) is read only after the answers.\n")
    print(f"{len(tiles)} tiles; thresholds {sum(1 for t in tiles if t['hidden'].get('threshold_tile'))}; groups {collections.Counter(t['hidden']['group'] for t in tiles)}")


def staff_space_page(run, g):
    sp = [o for o in run.observations if o["quantity"] == "cell_staff_space" and o["subject"] == g.cell_key]
    if not sp or g.box_page is None or g.box_canon is None:
        return None
    wc = g.box_canon[2] - g.box_canon[0]
    wp = g.box_page[2] - g.box_page[0]
    return float(sp[-1]["value"]) * (wp / wc) if wc > 0 else None


main()
