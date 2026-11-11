"""ROADMAP 2.303: cut the REAL pixels and rows of five printed words into `tools/omr/tests/data_letters_of_a_word_2_303.npz`, the fixture of the control tests.

    python3 benchmarks/dynamics-not-words-2026-11/make_fixture_2_303.py OUTNPZ litolff=REC brahms=REC     (REC = the saved page gathers `out/lane-2.303/g/*-base.record.json`)

Each case = a crop of the page's binary raster (1 = ink) at its real page origin around one READ word, every direction-word row, every detector dynamic letter (class, page box, the neighbour ink the
CV reader measured beside it) and every detector box of the crop. The words: Litolff p8 `sempre piu p` and `sempre A` (the `mp`/`pp` spelled from the letters of `sempre`), Brahms p14
`dolce sempre` and `piu p` (a real `p` standing in the word's box), Brahms p0 `f espr. e legato` (the real `f`, and the letters of `legato` boxed as `fz` / `fp`).
"""
import json
import pathlib
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
CASES = [
    # name, plate, page, word box (page px), unit
    ("l8_sempre_piu_p", "litolff", 8, [1616, 1573, 1862, 1613]),
    ("l8_sempre_A", "litolff", 8, [1613, 1247, 1871, 1330]),
    ("b14_dolce_sempre", "brahms", 14, [1295, 6652, 1674, 6716]),
    ("b14_piu_p", "brahms", 14, [5251, 6634, 5440, 6692]),
    ("b0_f_espr_e_legato", "brahms", 0, [1622, 6547, 2146, 6637]),
    ("l8_sempre_unread", "litolff", 8, [1510, 787, 1718, 822]),      # Sean's 2.301 r1 tile 4: the word was REFUSED by the lexicon (no READ word row): nothing may change
]
UNIT = {"litolff": 15.75, "brahms": 32.0}


def main():
    from tools.omr.staged import cell_map as CM
    from tools.omr.staged import claim_readout as CR
    from tools.omr.staged import lane_report as LR
    out_path = pathlib.Path(sys.argv[1])
    rec = dict(kv.split("=", 1) for kv in sys.argv[2:])
    out, meta = {}, {}
    for name, plate, page, wbox in CASES:
        rows = CR.read_rows(CR.resolve_source(rec[plate]), [page])
        obs = rows["observations"]
        u = UNIT[plate]
        crop = [int(wbox[0] - 2 * u), int(wbox[1] - 2 * u), int(wbox[2] + 2 * u), int(wbox[3] + 2 * u)]
        x0, y0, x1, y1 = crop

        def inside(b):
            return b[2] > x0 and b[0] < x1 and b[3] > y0 and b[1] < y1
        sides = {o["subject"]: o["value"] for o in obs if o["quantity"] == "dynamic_letter_neighbours"}
        letters = []
        for o in obs:
            if o["quantity"] == "dynamic_letter" and (o.get("detail") or {}).get("bbox_page_px") and inside(o["detail"]["bbox_page_px"]):
                sd = sides.get(o["subject"]) or {}
                letters.append(dict(key=o["subject"], letter=o["detail"]["letter"], box=o["detail"]["bbox_page_px"], left=bool(sd.get("left")), right=bool(sd.get("right")),
                                    left_spaces=sd.get("left_spaces"), right_spaces=sd.get("right_spaces"), id=o["id"]))
        words = []
        for o in obs:
            b = (o.get("detail") or {}).get("bbox_page_px")
            if o["quantity"] == "direction_word" and b and inside(b):
                d = o["detail"]
                words.append(dict(text=o["value"], box=b, dynamics=d.get("dynamics") or [], category=d.get("category"), includes=list(d.get("includes_dynamic_glyphs") or ())))
        dets = []
        for o in obs:
            if o["quantity"] == "glyph_box" and (o.get("detail") or {}).get("bbox_page_px") and not str(o.get("reader") or "").startswith("yolo_rescue"):
                b = o["detail"]["bbox_page_px"]
                if inside(b):
                    dets.append(dict(cls=str(o["value"][0]), category=o["detail"].get("category") or "", box=b, key=o["subject"]))
        (pws, _cells), = CM.load_prepared(LR.LIB / LR.PLATES[plate]["pdf"], [page], root=LR.CELL_MAP_ROOT)
        sub = (pws.page.binary[y0:y1, x0:x1] == 0)
        out[name + "__ink"] = np.packbits(sub, axis=1)
        meta[name] = dict(plate=plate, page=page, crop=crop, word_box=wbox, words=words, letters=letters, dets=dets, shape=list(sub.shape), spacing=LR.PLATES[plate]["unit"])
        print(name, sub.shape, "letters", len(letters), "words", [w["text"] for w in words], "dets", len(dets))
    out["meta"] = np.array(json.dumps(meta))
    np.savez_compressed(out_path, **out)
    print("wrote", out_path, out_path.stat().st_size)


if __name__ == "__main__":
    main()
