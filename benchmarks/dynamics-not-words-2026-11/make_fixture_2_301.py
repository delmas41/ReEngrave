"""ROADMAP 2.301: cut the REAL pixels and rows of Sean's 2.296 r1 tiles 2, 3, 4, 7, 8 (and 1, 5, 9) into `tools/omr/tests/data_dynamic_own_ink_2_301.npz`, the fixture of the control tests.

    python3 benchmarks/dynamics-not-words-2026-11/make_fixture_2_301.py

Each case = a crop of the page's binary raster (1 = ink) at its real page origin, the marking's direction-word row (text, box, the dynamics its text holds, the detector letters it
includes with their page boxes), and the detector boxes of the crop (class + page box). Reads the saved gather slices and the master cell map; writes only the .npz.
"""
import json
import pathlib
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
LIBR = pathlib.Path("/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records")
CASES = [
    # name, plate, slice, page, word box (page px) to find the row by, crop (x0, y0, x1, y1)
    ("t8_brahms_p0_f_legato", "brahms", "claim-readout-slices-2284b-r2-brahms.on.gathered", 0, [1638, 2501, 1901, 2584], [1590, 2470, 1940, 2620]),
    ("t2_brahms_p14_p_dim", "brahms", "claim-readout-slices-brahms-p14-main", 14, [4678, 3310, 4886, 3374], [4660, 3290, 4930, 3400]),
    ("t4_brahms_p14_piu_p", "brahms", "claim-readout-slices-brahms-p14-main", 14, [5251, 6145, 5441, 6199], [5235, 6120, 5470, 6225]),
    ("t7_brahms_p14_p_dim_flat", "brahms", "claim-readout-slices-brahms-p14-main", 14, [4740, 3537, 4885, 3589], [4700, 3470, 4950, 3610]),
    ("t3_litolff_p8_sempre_piu_p", "litolff", "claim-readout-slices-litolff-p8-main", 8, [1620, 1715, 1867, 1749], [1600, 1690, 1890, 1770]),
]


def main():
    from tools.omr.staged import cell_map as CM
    from tools.omr.staged import claim_readout as CR
    from tools.omr.staged import lane_report as LR
    out = {}
    meta = {}
    for name, plate, slc, page, wbox, crop in CASES:
        rows = CR.read_rows(LIBR / slc, [page])
        letters = {}
        for o in rows["observations"]:
            if o["quantity"] == "dynamic_letter":
                letters[o["subject"]] = o
        word = None
        for o in rows["observations"]:
            if o["quantity"] != "direction_word":
                continue
            b = (o.get("detail") or {}).get("bbox_page_px")
            if b and all(abs(float(b[i]) - wbox[i]) <= 12 for i in range(4)):
                word = o
                break
        if word is None:
            # the tile's box is a piece of the word's claim: the row whose box holds it
            for o in rows["observations"]:
                if o["quantity"] == "direction_word":
                    b = (o.get("detail") or {}).get("bbox_page_px")
                    if b and b[0] - 3 <= wbox[0] and b[2] + 3 >= wbox[2] and b[1] - 3 <= wbox[1] and b[3] + 3 >= wbox[3]:
                        word = o
                        break
        assert word is not None, name
        d = word["detail"]
        inc = []
        for k in d.get("includes_dynamic_glyphs") or ():
            lo = letters.get(k)
            if lo:
                inc.append(dict(key=k, letter=lo["detail"]["letter"], box=lo["detail"]["bbox_page_px"]))
        x0, y0, x1, y1 = crop
        dets = []
        for o in rows["observations"]:
            if o["quantity"] == "glyph_box" and (o.get("detail") or {}).get("bbox_page_px"):
                b = o["detail"]["bbox_page_px"]
                if b[2] > x0 and b[0] < x1 and b[3] > y0 and b[1] < y1 and not str(o.get("reader") or "").startswith("yolo_rescue"):
                    dets.append(dict(cls=str(o["value"][0]), category=o["detail"].get("category") or "", box=b, key=o["subject"]))
        (pws, _cells), = CM.load_prepared(LR.LIB / LR.PLATES[plate]["pdf"], [page], root=LR.CELL_MAP_ROOT)
        sub = (pws.page.binary[y0:y1, x0:x1] == 0)
        out[name + "__ink"] = np.packbits(sub, axis=1)
        meta[name] = dict(plate=plate, page=page, crop=crop, word=dict(text=word["value"], box=d["bbox_page_px"], dynamics=d.get("dynamics"), category=d.get("category")),
                          letters=inc, dets=dets, shape=list(sub.shape), spacing=LR.PLATES[plate]["unit"])
        print(name, sub.shape, "letters", len(inc), "dets", len(dets), "text", word["value"])
    out["meta"] = np.array(json.dumps(meta))
    p = ROOT / "tools" / "omr" / "tests" / "data_dynamic_own_ink_2_301.npz"
    np.savez_compressed(p, **out)
    print("wrote", p, p.stat().st_size)


if __name__ == "__main__":
    main()
