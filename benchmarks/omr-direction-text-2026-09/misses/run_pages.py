"""Re-read pickled pages with the CURRENT direction_text; time them; draw one review image per page.
python3 run_pages.py <outdir> tag...   (tags like lit_4, br_12; pickles from dump_page.py)"""
import json, os, pickle, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]; sys.path.insert(0, str(ROOT))
os.environ["OMR_SURYA_KEEP_ALIVE"] = "0"
import cv2, numpy as np
from tools.omr import direction_text as DT
from tools.omr import staff_labels_surya as SU

def draw(pws, boxes, words, path, title):
    page = pws.page.rgb
    sp = float(np.median([s.line_ys[4] - s.line_ys[0] for s in pws.staves])) / 4.0
    systems = {}
    for s in pws.staves: systems.setdefault(s.system_index, []).append(s)
    strips = []; W = 1400
    for si, sts in sorted(systems.items()):
        y0 = max(0, int(min(s.line_ys[0] for s in sts) - 6 * sp)); y1 = min(page.shape[0], int(max(s.line_ys[4] for s in sts) + 6 * sp))
        x0 = max(0, int(min(s.x_start for s in sts) - 2 * sp)); x1 = min(page.shape[1], int(max(s.x_end for s in sts) + 2 * sp))
        img = np.ascontiguousarray(page[y0:y1, x0:x1])
        k = W / float(x1 - x0)
        img = cv2.resize(img, (W, max(1, int((y1 - y0) * k))), interpolation=cv2.INTER_AREA)
        ids = {s.staff_index for s in sts}; n = 0
        for w, bb in zip(words, boxes):
            if not (y0 <= bb[1] < y1 and x0 <= bb[0] < x1): continue
            a, b, c2, d = bb
            p0 = (int((a - x0) * k) - 3, int((b - y0) * k) - 3); p1 = (int((c2 - x0) * k) + 3, int((d - y0) * k) + 3)
            cv2.rectangle(img, p0, p1, (0, 160, 0), 3)
            ty = p0[1] - 8 if p0[1] > 30 else p1[1] + 28
            cv2.putText(img, w.text, (max(2, p0[0]), ty), cv2.FONT_HERSHEY_SIMPLEX, 0.95, (255, 255, 255), 6)
            cv2.putText(img, w.text, (max(2, p0[0]), ty), cv2.FONT_HERSHEY_SIMPLEX, 0.95, (0, 110, 0), 2)
            n += 1
        head = np.full((40, W, 3), 255, np.uint8)
        cv2.putText(head, f"system {si}  ({n} word{'s' if n != 1 else ''} boxed)", (6, 29), cv2.FONT_HERSHEY_SIMPLEX, 0.85, (0, 0, 0), 2)
        strips += [head, img, np.full((14, W, 3), 128, np.uint8)]
    top = np.full((46, W, 3), 255, np.uint8)
    cv2.putText(top, title, (6, 33), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 160), 2)
    cv2.imwrite(str(path), cv2.cvtColor(np.vstack([top] + strips), cv2.COLOR_RGB2BGR))

out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
cm = SU.worker_session(); cm.__enter__()
summary = {}
try:
    for tag in sys.argv[2:]:
        pws, pd = pickle.load(open(f"/private/tmp/dtmiss/{tag}.pkl", "rb"))
        t = time.perf_counter()
        words, info = DT.read_directions(pws, pd, scan_order=True)
        dt = time.perf_counter() - t
        doc, pg = tag.split("_")
        name = ("litolff" if doc == "lit" else "brahms") + f"_page_{int(pg):02d}"
        draw(pws, info["word_boxes"], words, out / f"{name}.png", f"{name}: green = word read (reader in log)")
        summary[tag] = dict(seconds=round(dt, 1), found=len(words), n_candidates=info["n_candidates"],
                            unread=[[info["candidates"][i].staff_index, info["candidates"][i].measure_index, list(info["candidates"][i].bbox_page), t] for i, t in info.get("seen", {}).items() if sum(ch.isalpha() for x in t for ch in x) >= 3],
                            words=[[w.staff_index, w.measure_index, w.x_page, w.text, w.reader] for w in words])
        print(tag, round(dt, 1), "s", len(words), "words", {k: v for k, v in info.items() if k in ("first_looks_s","sibling_s","n_lettered","n_sibling_windows","n_sibling_read")}, flush=True)
finally:
    cm.__exit__(None, None, None)
    Path(f"/private/tmp/dtmiss/summary_{out.name}.json").write_text(json.dumps(summary, indent=1))
