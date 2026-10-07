"""Crops of every dot whose ROLE changes with OMR_DOT_FOLLOWS_NOTE (staccato -> augmentation is the risky direction).
  python3 dot_not_a_note_rolecrops.py <replay dir> <doc: brahms|lito> [--max 24]
Orange = the dot, green = the note it now trails; caption = before -> after."""
import json, sys, random
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import cv2, numpy as np
import truth_set_2_44c as ts
from frame import render_page_matching_gather
DOC = {"brahms": "brahms1-breitkopf", "lito": "beethoven5-litolff"}


def main(d, short, mx, only=None, tag=''):
    off = json.loads((Path(d) / f"{short}_all_off.json").read_text())
    on = json.loads((Path(d) / f"{short}_all_on.json").read_text())
    rows = []
    for k, a in off["dots"].items():
        b = on["dots"][k]
        ra, rb = (a["role"] or {}).get("v"), (b["role"] or {}).get("v")
        if ra != rb:
            rows.append((f"{ra}->{rb}", k, a, b))
    if only:
        rows = [r for r in rows if r[0] == only]
    rows.sort(key=lambda r: r[0])
    stac = [r for r in rows if r[0].startswith("staccato")]
    print(short, "role changes", len(rows), "staccato->aug", len(stac))
    random.Random(1).shuffle(rows)
    pick = (stac + [r for r in rows if r not in stac])[:mx]
    g = {}
    tiles = []
    for why, k, a, b in pick:
        page = int(k.split("/")[1])
        if page not in g:
            g[page] = cv2.cvtColor(render_page_matching_gather(ts.DOCS[DOC[short]]["pdf"], page, 600).rgb, cv2.COLOR_RGB2GRAY)
        im = g[page]
        bx = b["box"]
        cx, cy = (bx[0] + bx[2]) / 2, (bx[1] + bx[3]) / 2
        h = 70
        crop = cv2.cvtColor(im[int(cy - h):int(cy + h), int(cx - h * 1.6):int(cx + h * 0.6)], cv2.COLOR_GRAY2BGR)
        x0, y0 = cx - h * 1.6, cy - h
        crop = cv2.resize(crop, None, fx=2, fy=2, interpolation=cv2.INTER_NEAREST)
        hk = ((b["role"] or {}).get("d") or {}).get("head")
        hb = (on["boxes"].get(hk) or {}).get("box") if hk else None
        if hb:
            cv2.rectangle(crop, (int((hb[0] - x0) * 2), int((hb[1] - y0) * 2)), (int((hb[2] - x0) * 2), int((hb[3] - y0) * 2)), (0, 170, 0), 2)
        cv2.rectangle(crop, (int((bx[0] - x0) * 2), int((bx[1] - y0) * 2)), (int((bx[2] - x0) * 2), int((bx[3] - y0) * 2)), (0, 140, 255), 2)
        pad = np.full((30, crop.shape[1], 3), 255, np.uint8)
        cv2.putText(pad, f"{len(tiles) + 1}. {short} p{page} {k.split('/', 2)[2]}", (2, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 0, 0), 1, cv2.LINE_AA)
        cv2.putText(pad, why, (2, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (90, 90, 90), 1, cv2.LINE_AA)
        tiles.append(np.vstack([pad, crop]))
    cols = 4
    while len(tiles) % cols:
        tiles.append(np.full_like(tiles[0], 255))
    img = np.vstack([np.hstack(tiles[i:i + cols]) for i in range(0, len(tiles), cols)])
    out = HERE.parents[1] / f"out/print/dot_role_changes_{short}{tag}.png"
    cv2.imwrite(str(out), img)
    print("wrote", out)


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[0], a[1], int(a[a.index("--max") + 1]) if "--max" in a else 24,
         a[a.index("--only") + 1] if "--only" in a else None, a[a.index("--tag") + 1] if "--tag" in a else '')
