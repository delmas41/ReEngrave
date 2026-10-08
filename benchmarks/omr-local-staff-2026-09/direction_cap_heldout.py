"""Held-out check of the direction-word token cap, ONE page per run (2026-10-08).

    python3 direction_cap_heldout.py <pdf> <page> <tag> <out_dir>

Runs the real staged GATHER (--through gather, scan gate OFF) and, at the place `gather_direction_words`
runs, REPLACES it with: ON  = `read_directions` with `default_readers()` (cap 64 + 20 s crop guard),
OFF = same with Surya uncapped (`staff_labels_surya.read_crops_text` as before). Times both, lists words,
and draws ONE review image of the ON words (boxed + labelled, one column).
"""
from __future__ import annotations
import json, os, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.environ["OMR_SURYA_KEEP_ALIVE"] = "0"
os.environ.pop("OMR_DIRECTION_TEXT_SCAN_GATE", None)
import cv2
import numpy as np

WEIGHTS = "omr-weights/deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt"
R: dict = {}


def key(w):
    return (w.staff_index, w.measure_index, w.x_page, " ".join(w.text.lower().replace(".", " ").split()))


def draw(pws, cands, words, path, title):
    page = pws.page.rgb
    byxy = {(c.staff_index, c.measure_index, c.x_page): c for c in cands}
    sp = float(np.median([s.line_ys[4] - s.line_ys[0] for s in pws.staves])) / 4.0
    systems = {}
    for s in pws.staves:
        systems.setdefault(s.system_index, []).append(s)
    strips = []
    W = 1400
    for si, sts in sorted(systems.items()):
        y0 = max(0, int(min(s.line_ys[0] for s in sts) - 6 * sp)); y1 = min(page.shape[0], int(max(s.line_ys[4] for s in sts) + 6 * sp))
        x0 = max(0, int(min(s.x_start for s in sts) - 2 * sp)); x1 = min(page.shape[1], int(max(s.x_end for s in sts) + 2 * sp))
        img = np.ascontiguousarray(page[y0:y1, x0:x1])
        k = W / float(x1 - x0)
        img = cv2.resize(img, (W, max(1, int((y1 - y0) * k))), interpolation=cv2.INTER_AREA)
        staff_ids = {s.staff_index for s in sts}
        n = 0
        for w in words:
            if w.staff_index not in staff_ids:
                continue
            c = byxy.get((w.staff_index, w.measure_index, w.x_page))
            if c is None:
                continue
            a, b, c2, d = c.bbox_page
            p0 = (int((a - x0) * k) - 3, int((b - y0) * k) - 3); p1 = (int((c2 - x0) * k) + 3, int((d - y0) * k) + 3)
            cv2.rectangle(img, p0, p1, (0, 160, 0), 3)
            ty = p0[1] - 8 if p0[1] > 30 else p1[1] + 28
            cv2.putText(img, w.text, (max(2, p0[0]), ty), cv2.FONT_HERSHEY_SIMPLEX, 0.95, (255, 255, 255), 6)
            cv2.putText(img, w.text, (max(2, p0[0]), ty), cv2.FONT_HERSHEY_SIMPLEX, 0.95, (0, 110, 0), 2)
            n += 1
        head = np.full((40, W, 3), 255, np.uint8)
        cv2.putText(head, f"system {si}  ({n} word{'s' if n != 1 else ''} boxed)", (6, 29), cv2.FONT_HERSHEY_SIMPLEX, 0.85, (0, 0, 0), 2)
        strips.append(head); strips.append(img)
        strips.append(np.full((14, W, 3), 128, np.uint8))
    top = np.full((46, W, 3), 255, np.uint8)
    cv2.putText(top, title, (6, 33), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 160), 2)
    out = np.vstack([top] + strips)
    cv2.imwrite(str(path), cv2.cvtColor(out, cv2.COLOR_RGB2BGR))


def experiment(log, pws, cells, local, detections, tag, outdir, pdfname, pageno):
    from tools.omr import direction_text as DT
    from tools.omr import staff_labels_surya as SU
    from tools.omr import staff_labels_tesseract as TE
    from tools.omr.staged import gather as G
    page_dict = G._direction_page_dict(pws, cells, local, detections)
    cands = DT.find_candidates(pws, page_dict)
    R["n_candidates"] = len(cands)
    R["scan_gate_would_fire"] = bool(DT.page_is_scanned(pws.page))
    t = time.perf_counter()
    on, info_on = DT.read_directions(pws, page_dict)
    R["on_s"] = time.perf_counter() - t
    R["on_info_readers"] = info_on.get("readers")
    R["on_words"] = [list(key(w)) + [w.reader] for w in on]
    prev = os.environ.get("DT_REUSE_OFF")      # dir with an earlier run's data_<tag>.json: reuse its unguarded arm
    if prev and (Path(prev) / f"data_{tag}.json").exists():
        old = json.load(open(Path(prev) / f"data_{tag}.json"))
        R["off_s"] = old["off_s"]; R["off_words"] = old["off_words"]
        koff = {tuple(w[:4]) for w in old["off_words"]}
    else:
        t = time.perf_counter()
        off, info_off = DT.read_directions(pws, page_dict, readers=[("surya", SU.read_crops_text), ("tesseract", TE.read_crops_text)])
        R["off_s"] = time.perf_counter() - t
        R["off_words"] = [list(key(w)) + [w.reader] for w in off]
        koff = {key(w) for w in off}
    kon = {key(w) for w in on}
    R["lost_on_vs_off"] = sorted(map(list, koff - kon))
    R["extra_on_vs_off"] = sorted(map(list, kon - koff))
    draw(pws, cands, on, outdir / f"page_{tag}.png", f"{pdfname} pdf page index {pageno}: green = word found by the reader")


def main():
    pdf, page, tag, outdir = sys.argv[1:5]
    outdir = Path(outdir); outdir.mkdir(parents=True, exist_ok=True)
    from tools.omr.staged import gather as G
    from tools.omr import staff_labels_surya as SU

    def patched(log, pws, cells, local, detections):
        try:
            experiment(log, pws, cells, local, detections, tag, outdir, Path(pdf).name[:30], page)
        except Exception:
            import traceback; R["error"] = traceback.format_exc(); print(R["error"])
    G.gather_direction_words = patched
    R.update(pdf=pdf, page=page, tag=tag)
    cm = SU.worker_session(); cm.__enter__()
    try:
        from tools.omr.staged.__main__ import main as staged_main
        staged_main([pdf, "--pages", page, "--weights", WEIGHTS, "--through", "gather"])
    finally:
        cm.__exit__(None, None, None)
        (outdir / f"data_{tag}.json").write_text(json.dumps(R, indent=1, default=str))


if __name__ == "__main__":
    main()
