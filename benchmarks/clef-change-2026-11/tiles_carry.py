"""2.251 carry: 12 blind tiles for Sean. Heads the carry RE-PITCHED (ON: `Q.PITCH` reason `position_and_clef_change`, a value other
than the OFF arm's), each tile ONE staff from just left of the clef in force to just right of the head, so the tile shows the clef
AND the head (Sean 2026-11-01); one thin orange box on the head; nothing else drawn. Plus the no-box F clefs read (witness
`f_body_template`) as their own tiles, the box on the clef. Key outside tiles/.

python3 work-2.251/tiles_carry.py WORKDIR OUTDIR SEED [N_CLEF]
"""
import json, os, random, sys
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.join(os.getcwd(), "work-2.251"))
sys.path.insert(0, os.getcwd())
import crops  # noqa: E402
from tools.omr.staged import judged as J  # noqa: E402


FIXED = [
    dict(kind="clef", plate="litolff", page=14, system=0, staff=10, cell=12, box=[2246, 1800, 2300, 1844], read="bass",
         note="no-box F READ (body 0.77), Vc bar 411"),
    dict(kind="clef", plate="litolff", page=5, system=0, staff=3, cell=2, box=[861, 998, 896, 1041], read=None,
         note="no-box F CANDIDATE (body 0.68, a head through it), Fag bar 115: stops the carry"),
    dict(kind="clef", plate="litolff", page=12, system=0, staff=10, cell=7, box=[1447, 1785, 1493, 1835], read=None,
         note="F CANDIDATE (box refused for dots; body 0.69), Vc bar 346"),
]


def load(path):
    pitch, box, claims = {}, {}, {}
    for v in J.iter_array(path, "verdicts"):
        if v.get("quantity") == "pitch" and v.get("outcome") == "decided":
            pitch[v["subject"]] = v
    for o in J.iter_array(path, "observations"):
        q = o.get("quantity")
        if q == "glyph_box" and str(o["value"][0]).startswith("notehead"):
            box[o["subject"]] = (o.get("detail") or {}).get("bbox_page_px")
        elif q == "claimed_area" and (o.get("detail") or {}).get("source") == "clef_pagewide":
            claims[o["id"]] = o
    return pitch, box, claims


def staff_lines(plate, page, system, staff):
    d = crops.cmap(plate, page)
    st = sorted([t for t in d["staves"] if t["system_index"] == system], key=lambda t: t["line_ys"][0])[staff]
    return st["line_ys"]


def draw(plate, page, system, staff, x_from, x_to, mark):
    ly = staff_lines(plate, page, system, staff)
    sp = (ly[4] - ly[0]) / 4.0
    x0, x1 = int(x_from - 1.0 * sp), int(x_to + 3.0 * sp)
    y0, y1 = int(ly[0] - 4 * sp), int(ly[4] + 4 * sp)
    im = crops.page_img(plate, page).crop((x0, y0, x1, y1)).convert("RGB")
    z = max(1, min(3, int(1800 / max(1, im.width))))
    im = im.resize((im.width * z, im.height * z), Image.LANCZOS)
    ImageDraw.Draw(im).rectangle([(mark[0] - x0) * z, (mark[1] - y0) * z, (mark[2] - x0) * z, (mark[3] - y0) * z],
                                 outline=(255, 140, 0), width=2)
    return im


def main():
    work, out, seed = sys.argv[1], sys.argv[2], int(sys.argv[3])
    n_clef = int(sys.argv[4]) if len(sys.argv) > 4 else 3
    rng = random.Random(seed)
    os.makedirs(os.path.join(out, "tiles"), exist_ok=True)
    pool, clefs = [], []
    for wd, plate in [(w, pl) for w in work.split(",") for pl in ("litolff", "brahms")]:
        on = os.path.join(wd, "%s.on.gathered.record.json" % plate)
        off = os.path.join(wd, "%s.off.gathered.record.json" % plate)
        if not os.path.exists(on):
            continue
        p_on, b_on, c_on = load(on)
        p_off, _b, _c = load(off)
        for subj, v in p_on.items():
            if v.get("reason") != "position_and_clef_change" or subj not in b_on or not b_on[subj]:
                continue
            w = p_off.get(subj)
            if w is not None and w.get("value") == v.get("value"):
                continue
            crow = next((c_on[b] for b in v.get("basis") or () if b in c_on), None)
            if crow is None:
                continue
            _, pg, s, st, c, g = subj.split("/")
            pool.append(dict(kind="head", plate=plate, page=int(pg), system=int(s), staff=int(st), cell=int(c), subject=subj,
                             box=[round(float(x), 1) for x in b_on[subj]], clef_x=float(crow["value"][0]),
                             clef_kind=(crow.get("detail") or {}).get("kind"), on=v.get("value"),
                             off=(w or {}).get("value")))
        for cid, o in c_on.items():
            d = o.get("detail") or {}
            if "f_body_template" in (d.get("witnesses") or ()) and d.get("change"):
                _, pg, s, st = o["subject"].split("/")
                clefs.append(dict(kind="clef", plate=plate, page=int(pg), system=int(s), staff=int(st), cell=d.get("cell"),
                                  box=[round(float(x), 1) for x in o["value"]], read=d.get("kind"), shape=d.get("shape")))
    # the no-box F reads and candidates off the sample pages (offline scan, the gather's own functions; Litolff pp. 5, 12, 14)
    for t in FIXED:
        if not any((c["plate"], c["page"], c["system"], c["staff"]) == (t["plate"], t["page"], t["system"], t["staff"])
                   and abs(c["box"][0] - t["box"][0]) < 30 for c in clefs):
            clefs.append(dict(t))
    print("pool: heads", len(pool), "no-box clefs", len(clefs))
    pick_c = clefs[:n_clef] if len(clefs) <= n_clef else rng.sample(clefs, n_clef)
    # heads: one per (plate, page, system, staff, cell) at most, spread over places
    by = {}
    for t in pool:
        by.setdefault((t["plate"], t["page"], t["system"], t["staff"], t["cell"]), []).append(t)
    keys = list(by)
    rng.shuffle(keys)
    pick_h = [rng.choice(by[k]) for k in keys[:12 - len(pick_c)]]
    pick = pick_c + pick_h
    rng.shuffle(pick)
    key = []
    for i, t in enumerate(pick, 1):
        if t["kind"] == "head":
            im = draw(t["plate"], t["page"], t["system"], t["staff"], t["clef_x"], t["box"][2], t["box"])
        else:
            im = draw(t["plate"], t["page"], t["system"], t["staff"], t["box"][0] - 4 * 16, t["box"][2] + 2 * 16, t["box"])
        im.save(os.path.join(out, "tiles", "%02d.png" % i))
        key.append(dict(tile=i, **t))
    json.dump({"seed": seed, "what": "2.251 carry tiles: heads the carry re-pitched (ON differs from OFF), one per bar, plus no-box F clef "
               "reads; drawn from the ON arm's record; crop from the clef in force to the head", "tiles": key},
              open(os.path.join(out, "key.json"), "w"), indent=1)
    with open(os.path.join(out, "QUESTION.txt"), "w") as fh:
        fh.write("Tiles with a box on a NOTE: What note is in the box (name and octave if you can), and which clef is it read in?\n"
                 "Tiles with a box on a CLEF-sized mark: Is this a clef? Which one?\n"
                 "The orange box is the only thing drawn; everything else is the print.\n")


if __name__ == "__main__":
    main()
