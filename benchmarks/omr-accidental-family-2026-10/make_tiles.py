"""2.201: 12 fresh blind tiles from a lane report's two arms. Every tile = one WRITTEN ACCIDENTAL that differs OFF vs ON (or, for 3 controls, one that
does not), an orange box on the accidental's own ink (the detector's box, from the arm's glyph boxes: the nearest accidental-class box directly left
of the note), the note in the crop, nothing of ours drawn, no two tiles on one ink. Drawn in proportion to the changes by (plate, side).
usage: make_tiles.py REPORT_DIR OUT_DIR [--seed N]"""
import collections, json, os, pathlib, random, sys
sys.path.insert(0, ".")
from tools.omr.staged import lane_report as LR

QUESTION = ("Which accidental is printed directly in front of the note at the orange box (or in the box): sharp, flat, natural, or none?")


def accidental_boxes(mini, unit):
    out = collections.defaultdict(list)
    for o in mini["observations"]:
        d = o.get("detail") or {}
        if d.get("category") == "accidental" and d.get("bbox_page_px") and not d.get("one_ink_absorbed_by"):
            pg = LR.page_of(o["subject"])
            out[pg].append(d["bbox_page_px"])
    return out


def box_on_accidental(item, boxes, unit):
    nb = item["box"]
    best = None
    for b in boxes.get(item["page"], ()):
        gap = nb[0] - b[2]
        if -0.5 * unit <= gap <= 2.5 * unit and b[3] > nb[1] - unit and b[1] < nb[3] + unit:
            sc = abs(gap) + abs((b[1] + b[3]) / 2 - (nb[1] + nb[3]) / 2) / 3.0
            if best is None or sc < best[0]:
                best = (sc, b)
    return list(best[1]) if best else None


def main(rep_dir, out_dir, seed=2201):
    rep_dir, out_dir = pathlib.Path(rep_dir), pathlib.Path(out_dir)
    work = rep_dir / "work"
    cases, controls, boxes = [], [], {}
    for plate in ("litolff", "brahms"):
        off = json.load(open(work / ("%s.off.symbols.json" % plate)))
        on = json.load(open(work / ("%s.on.symbols.json" % plate)))
        d = LR.diff_arms(off, on, tol=0.5 * LR.PLATES[plate]["unit"])
        unit = LR.PLATES[plate]["unit"]
        bx = {a: accidental_boxes(json.load(open(work / ("%s.%s.mini-record.json" % (plate, a)))), unit) for a in ("off", "on")}
        for c in d["changes"]:
            if c["kind"] != "accidental" or not c.get("box") or c.get("page") is None:
                continue
            arm = "off" if c["side"] == "lost" else "on"
            b = box_on_accidental(c, bx[arm], unit)
            cases.append(dict(c, plate=plate, accidental_box_found=b is not None, note_box=c["box"], box=b or c["box"]))
        for s in d["same"]:
            if s["kind"] == "accidental" and s.get("box") and s.get("page") is not None:
                b = box_on_accidental(s, bx["on"], unit)
                if b:
                    controls.append(dict(s, plate=plate, note_box=s["box"], box=b, side="unchanged", accidental_box_found=True))
    cases = [c for c in cases if c["accidental_box_found"]]
    strata = collections.defaultdict(list)
    for c in cases:
        strata[(c["plate"], c["side"])].append(c)
    rng = random.Random(seed)
    for k in strata:
        rng.shuffle(strata[k])
    quota = LR.tile_quota({"%s/%s" % k: len(v) for k, v in strata.items()}, 9)
    picked = []
    for k in sorted(strata):
        got = 0
        for c in strata[k]:
            if got >= quota.get("%s/%s" % k, 0):
                break
            if any(LR._same_ink(c, x) for x in picked):
                continue
            picked.append(dict(c, role="case"))
            got += 1
    rng.shuffle(controls)
    ctl = []
    for c in controls:
        if len(ctl) >= 3:
            break
        if any(LR._same_ink(c, x) for x in picked + ctl):
            continue
        ctl.append(dict(c, role="control"))
    items = picked + ctl
    rng.shuffle(items)
    out_dir.mkdir(parents=True, exist_ok=True)
    info = LR.cut_tiles(items, out_dir)
    (out_dir / "tiles" / "README.md").write_text(
        "# 2.201 accidental family: 12 blind tiles\n\nEach picture is a piece of a scanned score page with ONE orange box and nothing else drawn. The box is on a mark "
        "that may be an accidental; the note it would belong to is in the picture.\n\n**Question, for every tile:** " + QUESTION +
        "\n\nAnswer by tile number (e.g. `1 nat, 2 flat, 3 none ...`).\n")
    print(info, "strata sizes", {"%s/%s" % k: len(v) for k, v in strata.items()}, "quota", quota)


if __name__ == "__main__":
    a = sys.argv[1:]
    seed = int(a[a.index("--seed") + 1]) if "--seed" in a else 2201
    main(a[0], a[1], seed)
