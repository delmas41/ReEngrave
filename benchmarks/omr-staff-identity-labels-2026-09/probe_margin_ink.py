#!/usr/bin/env python3
"""Is there any INK beside this staff to read? — the mechanical (a) test.

Class (a) of the Phase-1 split is "no label is printed on the page at all",
and it is the one class no reader improvement can ever reach. Deciding it by
eye over a hundred staves is neither honest nor repeatable, so it is decided by
the page's own ink: count the black pixels in the band beside each staff,
between the page's left edge and the bracket.

    band  y in [top_y - 1.5 sp, bottom_y + 1.5 sp]
    x     [0, x_ref - BRACKET_KEEPOUT_SPACES * sp)

⚠️ THE KEEP-OUT IS WHAT MAKES THIS A TEST AND NOT A TAUTOLOGY. The bracket and
the braces are ink in the margin on EVERY staff of every system; without
excluding them every staff scores "ink present" and the test says nothing. The
keep-out is measured against `x_ref` (the median staff `x_start`) rather than
against a detected bracket, because on these scans the bracket is exactly what
`x_start` is anchored beside.

⚠️ AND INK IS NOT A LABEL. A staff with ink here may carry a printed label the
readers missed (class b/c), a page number, a rehearsal mark, or the tail of a
brace that reaches past the keep-out. The test is only trusted in the negative:
**no ink ⇒ nothing was printed ⇒ class (a), proven.** Every staff WITH ink is
written out as an image for a human to look at, and none is classified here.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO))

WORKS = REPO / "benchmarks" / "omr-scan-e2e-2026-09" / "works.json"
DPI = 600
BRACKET_KEEPOUT_SPACES = 1.5
BAND_PAD_SPACES = 1.5
# Below this, the "ink" is scanner speckle: measured, the blank Litolff and
# Simrock continuation margins run 0-40 px over bands of ~200,000 px while a
# printed `Tr.` runs into the thousands.
SPECKLE_PX = 120


def main() -> int:
    import numpy as np
    from PIL import Image
    from tools.omr.preprocessing import render_page
    from tools.omr.staff_detector import detect_staves
    from tools.library.score_library import library_root

    lib = Path(library_root())
    works = json.loads(WORKS.read_text())
    shots = HERE / "ink-suspects"
    shots.mkdir(exist_ok=True)

    classified = json.loads((HERE / "classified.json").read_text())
    # Run on every staff that did NOT resolve — the ones with no read at all AND
    # the ones a rung answered with a string the lexicon refused. The second set
    # matters: a `|` read off the bracket on a staff with a blank margin is class
    # (a) wearing a refusal's clothes, and only the ink says which.
    empty = {(s["row_id"], s["system"], s["position"])
             for s in classified["staves"]
             if s["class"] in ("bc_EMPTY", "d_REFUSED")}

    out = []
    for row in works["rows"]:
        rid = row["row_id"]
        if not any(k[0] == rid for k in empty):
            continue
        page = render_page(lib / row["edition"]["catalog_path"],
                           row["page"]["pdf_page_index"], dpi=DPI)
        pws = detect_staves(page)
        binary = np.asarray(page.binary)
        # PageImage.binary: ink is the minority class; normalise to ink==True.
        ink = binary < 128 if binary.mean() > 127 else binary > 0
        by_sys: dict[int, list] = {}
        for s in sorted(pws.staves, key=lambda s: s.top_y):
            by_sys.setdefault(s.system_index, []).append(s)
        for sysi, staves in sorted(by_sys.items()):
            hs = sorted(s.bottom_y - s.top_y for s in staves)
            sp = hs[len(hs) // 2] / 4.0
            xs = sorted(s.x_start for s in staves)
            x_ref = xs[len(xs) // 2]
            xcut = max(0, int(x_ref - BRACKET_KEEPOUT_SPACES * sp))
            for i, s in enumerate(staves):
                if (rid, sysi, i) not in empty:
                    continue
                y0 = max(0, int(s.top_y - BAND_PAD_SPACES * sp))
                y1 = min(ink.shape[0], int(s.bottom_y + BAND_PAD_SPACES * sp))
                band = ink[y0:y1, 0:xcut]
                n = int(band.sum())
                rec = {"row_id": rid, "system": sysi, "position": i,
                       "ink_px": n, "band_px": int(band.size),
                       "xcut": xcut, "spacing": round(float(sp), 1),
                       "verdict": "a_NO_INK" if n <= SPECKLE_PX else "INK_look"}
                out.append(rec)
                if n > SPECKLE_PX:
                    Image.fromarray(page.rgb[y0:y1, 0:xcut]).convert("RGB").save(
                        shots / f"{rid}-sys{sysi}-pos{i}.png")
    (HERE / "margin-ink.json").write_text(json.dumps(out, indent=1))

    from collections import Counter
    print("verdicts:", dict(Counter(r["verdict"] for r in out)), "n =", len(out))
    print()
    for r in out:
        if r["verdict"] != "a_NO_INK":
            print(f"  INK  {r['row_id']} sys{r['system']} pos{r['position']}: "
                  f"{r['ink_px']} px of {r['band_px']}")
    print()
    byrow = {}
    for r in out:
        k = (r["row_id"], r["system"])
        byrow.setdefault(k, []).append(r["ink_px"])
    for k, v in sorted(byrow.items()):
        print(f"  {k[0]:38} sys{k[1]}  n={len(v):>2}  ink px {sorted(v)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
