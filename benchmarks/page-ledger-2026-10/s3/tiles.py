"""Cut the 12 blind tiles of 2.240 step 2 round 2 (out/print/2.240-s3-tiles/): the places of s2 tiles 5, 8, 11 plus changed owners (head owners moved by
the ledger filter / the hairpin witness, hairpin disagreements, arcs whose owner is a staff they were not traced from).

    python3 benchmarks/page-ledger-2026-10/s3/tiles.py OUTDIR  "litolff|ON.record.json|2,4" "brahms|ON.record.json|4,5" "litolff|litolff:20261029-night|6"
"""
import collections
import json
import pathlib
import random
import sys

from tools.omr.staged import cell_map as CM
from tools.omr.staged import claim_readout as CR
from tools.omr.staged import page_owner as PO

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import measure as M  # noqa: E402

S2KEY = pathlib.Path("out/print/2.240-s2-tiles/key.json")


def overlap(a, b):
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    return ix * iy / max(1e-9, min((a[2] - a[0]) * (a[3] - a[1]), (b[2] - b[0]) * (b[3] - b[1])))


def main():
    out = pathlib.Path(sys.argv[1])
    cm = CM.ROOT_DEFAULT
    pool = []
    O_before = {}
    for spec in sys.argv[2:]:
        plate, rec, pages = spec.split("|")
        pages = [int(p) for p in pages.split(",")]
        src = CR.resolve_source(rec)
        pdf = CR.LIB / CR.edition_info(CR.read_rows(src, pages))["edition_path"]
        H, spans = M.arms(rec, pages, cm, pdf, True)
        F, _ = M.arms(rec, pages, cm, pdf, False)
        for k, h in H.items():
            if h["family"] != "head" or h["status"] == "abstain" or h["reason"] == "inside_staff":
                continue
            f = F.get(k, {})
            pool.append({"kind": "owner", "page": h["page"], "pdf": str(pdf), "cm_root": str(cm), "box": h["box"], "status": h["status"],
                         "reason": h["reason"], "owner": h["owner"], "candidates": h["candidates"], "members": h["members"],
                         "staves": sorted(set(h["candidates"]) | set(h["seen_from"])),
                         "without_hairpin": [f.get("status"), f.get("owner"), f.get("reason")], "seen_from": h["seen_from"],
                         "changed": bool(f) and (f.get("owner"), f.get("status")) != (h["owner"], h["status"])})
        for pg, sps in spans.items():
            for s in sps:
                if s["kind"] != "arc":
                    continue
                ow = s.get("owner") or {}
                if ow.get("status") == "abstain" or not ow.get("owner"):
                    continue
                pool.append({"kind": "arc", "page": pg, "pdf": str(pdf), "cm_root": str(cm), "owner_row": {k: v for k, v in ow.items() if k != "ends"},
                             "arc_ends": ow.get("ends"), "seen_from": s["staves_seen_from"], "staves": [ow["owner"]],
                             "differs": ow["owner"] not in s["staves_seen_from"],
                             "span": {k: v for k, v in s.items() if k in ("views", "staves_seen_from", "pieces", "x0", "x1", "box", "joined_by", "crosses_barline")}})
    s2 = {t["tile"]: t for t in json.loads(S2KEY.read_text())}
    chosen, why = [], []

    def add(it, w):
        if it is not None and all(it is not c for c in chosen):
            chosen.append(it)
            why.append(w)

    # the places of s2 tiles 11 (a head), 5 and 8 (arcs)
    add(next((p for p in pool if p["kind"] == "owner" and set(p["members"]) & set(s2[11]["members"])), None), "place of s2 tile 11")
    for t in (5, 8):
        b = s2[t]["span"]["box"]
        add(next((p for p in pool if p["kind"] == "arc" and p["page"] == s2[t]["page"] and overlap(p["span"]["box"], b) > 0.5), None), "place of s2 tile %d" % t)
    rnd = random.Random(2403)
    add(next((p for p in pool if p["kind"] == "owner" and "glyph/4/0/10/5/5" in p["members"]), None), "owner newly decided by the filtered ledger evidence")
    for p in [p for p in pool if p["kind"] == "owner" and p["reason"] in ("hairpin_disagrees", "hairpin")][:3]:
        add(p, "hairpin witness")
    arcs = [p for p in pool if p["kind"] == "arc" and p["differs"]]
    rnd.shuffle(arcs)
    for p in arcs:
        if len(chosen) >= 8:
            break
        add(p, "arc owner not a staff it was traced from")
    los = [p for p in pool if p["kind"] == "owner" and p["reason"] == "ledger_over_stem"]
    rnd.shuffle(los)
    for p in los[:3]:
        add(p, "ledger over stem (decided plain, Sean 10-28)")
    rest = [p for p in pool if p["kind"] == "arc" and not p["differs"]] + [p for p in pool if p["kind"] == "owner" and not p["changed"]]
    rnd.shuffle(rest)
    for p in rest:
        if len(chosen) >= 12:
            break
        add(p, "control: owner unchanged")
    order = list(range(len(chosen)))
    rnd.shuffle(order)
    chosen = [chosen[i] for i in order]
    why = [why[i] for i in order]
    PO.pick_tiles = lambda pool_, n=12, seed=0: pool_[:n]
    PO.cut_tiles(chosen, out, n=12)
    key = json.loads((out / "key.json").read_text())
    for k, w in zip(key, why):
        k["why"] = w
    (out / "key.json").write_text(json.dumps(key, indent=1, default=str))
    from PIL import Image, ImageDraw
    tiles = [Image.open(out / "tiles" / ("tile_%02d.png" % (i + 1))) for i in range(len(key))]
    cols, W = 4, 560
    rows = (len(tiles) + cols - 1) // cols
    h = max(t.height for t in tiles)
    sheet = Image.new("RGB", (cols * (W + 8) + 8, rows * (h + 30) + 8), (255, 255, 255))
    d = ImageDraw.Draw(sheet)
    for n, t in enumerate(tiles):
        x, y = 8 + (n % cols) * (W + 8), 8 + (n // cols) * (h + 30)
        d.text((x, y + 2), "%d" % (n + 1), fill=(0, 0, 0))
        sheet.paste(t, (x, y + 18))
    sheet.save(out / "tiles" / "sheet.png")
    print(collections.Counter(why))


if __name__ == "__main__":
    main()
