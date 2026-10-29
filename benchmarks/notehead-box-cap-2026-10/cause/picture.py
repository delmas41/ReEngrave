"""2.222 cause: ONE picture for Sean -> out/print/2.222-cause/example.png
Four real written-note head boxes. BLUE (thick) = the detector's own box, recomputed from ultralytics' raw output (capture.py);
RED (thin, dashed) = the box the exported note carries. GREEN ruler (top-left corner) = the size of one notehead, 1.4 x 1.0 spaces.
    python3 benchmarks/notehead-box-cap-2026-10/cause/picture.py
"""
import json, pathlib, pickle
import cv2, numpy as np

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SCR = pathlib.Path("/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-agent-manager-workflow-356c39/7e1ea73e-2fd3-4d6c-a450-36868f7e14c0/scratchpad")
OUT = ROOT / "out" / "print" / "2.222-cause"
PICK = [("litolff", "glyph/2/1/1/12/3", "1. Two heads printed touching:\none box round both"),
        ("litolff", "glyph/2/0/8/3/4", "2. Heads + stem in one\nink column: one box"),
        ("litolff", "glyph/2/1/2/12/2", "3. Re-read below the confidence\nfloor (rescue): two heads, one box"),
        ("brahms", "glyph/5/1/12/3/3", "4. A stem and its flag,\nboxed as a notehead")]
rows = {r["key"]: r for r in json.loads((HERE / "rows.json").read_text())}


def raw_box(plate, page, kept):
    calls = json.loads((SCR / "cap" / ("%s.p%d.raw.json" % (plate, page))).read_text())
    best = None
    for c in calls:
        x0, y0 = c["cell_bbox_page_px"][:2]; u = c["upscale"]
        for r in c.get("raw", []):
            a = r["xyxy"]; b = [x0 + a[0] / u, y0 + a[1] / u, x0 + a[2] / u, y0 + a[3] / u]
            d = max(abs(b[i] - kept[i]) for i in range(4))
            if best is None or d < best[0]:
                best = (d, b, r)
    return best


def grey(plate, page):
    f = SCR / ("grey_%s_%d.npy" % (plate, page))
    if f.exists():
        return np.load(f)
    import sys
    sys.path.insert(0, str(ROOT))
    from tools.omr.preprocessing import render_page
    PDF = {"litolff": "editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
           "brahms": "editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"}
    g = cv2.cvtColor(render_page("/Users/seanjohnson/Desktop/ReEngrave/library/" + PDF[plate], page, dpi=600).rgb, cv2.COLOR_RGB2GRAY)
    np.save(f, g)
    return g


def dashed(img, p0, p1, col):
    x0, y0 = p0; x1, y1 = p1
    for (a, b) in (((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))):
        n = int(max(abs(b[0] - a[0]), abs(b[1] - a[1])) // 8) + 1
        for k in range(0, n, 2):
            s = (int(a[0] + (b[0] - a[0]) * k / n), int(a[1] + (b[1] - a[1]) * k / n))
            e = (int(a[0] + (b[0] - a[0]) * (k + 1) / n), int(a[1] + (b[1] - a[1]) * (k + 1) / n))
            cv2.line(img, s, e, col, 2)


tiles, notes = [], []
for plate, key, title in PICK:
    r = rows[key]; page = r["page"]; sp = r["sp"]
    pg = grey(plate, page)          # the GREY page the detector is fed (cell.image is cut from rgb), not our binarisation
    kept = r["box"]
    d, raw, rr = raw_box(plate, page, kept)
    cx, cy = (kept[0] + kept[2]) / 2, (kept[1] + kept[3]) / 2
    half = max(4.5 * sp, 0.65 * max(kept[2] - kept[0], kept[3] - kept[1]))
    X0, Y0 = int(cx - half), int(cy - half)
    crop = cv2.cvtColor(pg[Y0:Y0 + int(2 * half), X0:X0 + int(2 * half)], cv2.COLOR_GRAY2BGR)
    S = 380
    f = S / crop.shape[0]
    crop = cv2.resize(crop, (S, S), interpolation=cv2.INTER_AREA)
    P = lambda x, y: (int(round((x - X0) * f)), int(round((y - Y0) * f)))
    cv2.rectangle(crop, P(raw[0], raw[1]), P(raw[2], raw[3]), (220, 90, 0), 5)          # blue (BGR)
    dashed(crop, P(kept[0], kept[1]), P(kept[2], kept[3]), (0, 0, 230))                   # red
    gw, gh = 1.4 * sp * f, 1.0 * sp * f
    cv2.rectangle(crop, (8, 8), (int(8 + gw), int(8 + gh)), (0, 160, 0), 3)               # green ruler
    cv2.rectangle(crop, (0, 0), (S - 1, S - 1), (0, 0, 0), 1)
    t = np.full((S + 70, S, 3), 255, np.uint8); t[:S] = crop
    for i, line in enumerate(title.split("\n")):
        cv2.putText(t, line, (6, S + 24 + 22 * i), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1, cv2.LINE_AA)
    tiles.append(t)
    notes.append(dict(plate=plate, key=key, page=page, kept=kept, raw=raw, max_corner_diff_px=round(d, 3), raw_class=rr["cls"],
                      raw_conf=round(rr["conf"], 3), size_spaces=[round(r["w"], 2), round(r["h"], 2)], reader=r["reader"], eye=r.get("eye")))
gap = np.full((S + 70, 12, 3), 255, np.uint8)
row = np.hstack(sum([[t, gap] for t in tiles], [])[:-1])
legend = np.full((120, row.shape[1], 3), 255, np.uint8)
L = [("thick BLUE box = what the detector itself drew (its own raw output)", (220, 90, 0)),
     ("dashed RED box = the box our exported note carries (it sits exactly on the blue one: we did not change it)", (0, 0, 230)),
     ("small GREEN box, top left = the size of ONE notehead (1.4 x 1.0 staff spaces), for scale", (0, 160, 0))]
for i, (s, c) in enumerate(L):
    cv2.rectangle(legend, (10, 14 + 34 * i), (40, 34 + 34 * i), c, 3)
    cv2.putText(legend, s, (52, 32 + 34 * i), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 0), 1, cv2.LINE_AA)
OUT.mkdir(parents=True, exist_ok=True)
cv2.imwrite(str(OUT / "example.png"), np.vstack([row, legend]))
(OUT / "example.json").write_text(json.dumps(notes, indent=1))
print(json.dumps(notes, indent=1))
