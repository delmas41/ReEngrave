"""2.302 cause table: for each of Sean's judged staff starts, what `staff_run` returned (pieces, from_stems) and what a plain vertical-run
count finds in the key zone (every thin vertical stroke, NO chain / slot test), with each stroke's top and bottom in steps below the staff's
top line (local lines) against the fixed-order step of the j-th flat for the READ clef.

    PYTHONPATH=. python3 benchmarks/key-object-counts-flats-2026-11/cause.py PLATE EX.json OUT.json PAGE:SYS:LI [PAGE:SYS:LI ...]

MEASURE ONLY. Calls the production `gather_key_object` through the replay harness with `find_object` wrapped to capture each staff's inputs."""
import json
import os
import sys

import numpy as np

from tools.omr.staged import cell_map as CM
from tools.omr.staged import claims as CL
from tools.omr.staged import gather as G
from tools.omr.staged import key_object as KO
from tools.omr.staged import lane_report as LR
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Q, READERS


class _Det:
    def __init__(self, name, box):
        self.smufl_name = name
        self.pbox = tuple(box)


def strokes(binary, ly, sp, x_lo, x_hi, min_run=1.4, max_run=4.6, max_w=0.55):
    """Every thin vertical ink stroke in the zone: columns whose longest vertical run (staff lines included) is in [min_run, max_run] spaces."""
    ly = [float(v) for v in ly]
    H, W = binary.shape
    x0, x1 = max(0, int(x_lo)), min(W, int(x_hi))
    y0, y1 = max(0, int(ly[0] - KO.BAND_SPACES * sp)), min(H, int(ly[-1] + KO.BAND_SPACES * sp))
    sub = binary[y0:y1, x0:x1] == 0
    cur = np.zeros(sub.shape[1], dtype=np.int32)
    best = np.zeros(sub.shape[1], dtype=np.int32)
    btop = np.zeros(sub.shape[1], dtype=np.int32)
    for y in range(sub.shape[0]):
        cur = (cur + 1) * sub[y]
        upd = cur > best
        best = np.where(upd, cur, best)
        btop = np.where(upd, y - cur + 1, btop)
    ok = (best >= min_run * sp) & (best <= max_run * sp)
    out, c = [], 0
    while c < len(ok):
        if not ok[c]:
            c += 1
            continue
        c2 = c
        while c2 + 1 < len(ok) and ok[c2 + 1]:
            c2 += 1
        if (c2 + 1 - c) <= max_w * sp:
            i = c + int(np.argmax(best[c:c2 + 1]))
            top, bot = y0 + int(btop[i]), y0 + int(btop[i]) + int(best[i])
            cx = x0 + (c + c2 + 1) / 2.0
            sh = KO.local_line_shift(binary, ly, sp, cx - 0.5 * sp, cx + 0.5 * sp)
            out.append({"cx": cx, "run": round(best[i] / sp, 2), "w": round((c2 + 1 - c) / sp, 2),
                        "top": round((top - (ly[0] + sh)) / (sp / 2), 2), "bot": round((bot - (ly[0] + sh)) / (sp / 2), 2)})
        c = c2 + 1
    return out


def main():
    plate, exp, outp = sys.argv[1:4]
    wanted = [tuple(int(v) for v in a.split(":")) for a in sys.argv[4:]]
    pages = sorted({w[0] for w in wanted})
    ex = json.load(open(exp))
    G._page_box = lambda cell, det: det.pbox
    real = KO.find_object
    pdf = LR.LIB / LR.PLATES[plate]["pdf"]
    res = {}
    # the capture above cannot know the system; do it again, system by system, with the staves' own first line as the id
    cap2 = {}

    def wrap2(binary, staves, **kw):
        obj = real(binary, staves, **kw)
        for st in staves:
            cap2[round(float(st["lines"][0]))] = (binary, st, obj["by_staff"][st["key"]], obj["N"])
        return obj
    KO.find_object = wrap2
    for pws, cells in CM.load_prepared(pdf, pages, root=LR.CELL_MAP_ROOT):
        p = pws.page.page_index
        local = G._system_local(pws.staves)
        cap2.clear()
        log = Log()
        dets = {}
        for c in cells:
            if c.measure_index != 0:
                continue
            s, li = local[c.staff_index]
            row = ex.get("%d/%d/%d" % (p, s, li)) or {"dets": [], "meter_left": None}
            dets[R.cell(p, s, li, 0).to_key()] = [_Det(d["name"], d["box"]) for d in row["dets"]]
            if row.get("meter_left") is not None:
                log.observe(R.staff(p, s, li), Q.CLAIMED_AREA, [row["meter_left"], 0.0, row["meter_left"] + 1.0, 1.0], reader=READERS.CV_KEY_OBJECT,
                            frame="cell:0", cell=0, owner=CL.OWNER_METER, unit="area", standing="READ", source="replay")
        G.gather_key_object(log, pws, cells, local, dets)
        by_line = {}
        for st in pws.staves:
            s, li = local[st.staff_index]
            by_line[(s, li)] = round(float(list(st.line_ys)[0]))
        for (wp, ws, wl) in wanted:
            if wp != p:
                continue
            y = by_line[(ws, wl)]
            binary, st, me, N = cap2[y]
            sp, ly = st["spacing"], st["lines"]
            clef = st.get("clef_measured")
            zone = strokes(binary, ly, sp, st["x_start"] - 0.3 * sp, min(st["x_hi"], st["x_start"] + 8 * sp))
            fs = KO.flat_stems(binary, ly, sp, st["x_start"], st["x_hi"], clef)
            if os.environ.get("CROPS"):
                from PIL import Image
                x0c, x1c = int(st["x_start"] - 3 * sp), int(st["x_start"] + 9 * sp)
                y0c, y1c = int(ly[0] - 3 * sp), int(ly[-1] + 3 * sp)
                im = Image.fromarray(binary[y0c:y1c, x0c:x1c]).convert("L").resize(((x1c - x0c) * 3, (y1c - y0c) * 3), Image.NEAREST)
                im.save(os.path.join(os.environ["CROPS"], "%d_%d_%d.png" % (wp, ws, wl)))
            res["%d/%d/%d" % (wp, ws, wl)] = {
                "clef": clef, "N": N, "pieces": len(me["pieces"]), "piece_src": [q.get("src") for q in me["pieces"]],
                "piece_rel": [round((q["cx"] - st["x_start"]) / sp, 2) for q in me["pieces"]], "flat_stems_chain": len(fs),
                "x_start": st["x_start"], "x_hi": st["x_hi"], "sp": sp,
                "boxes": [[round((b[0] - st["x_start"]) / sp, 2), round((b[2] - st["x_start"]) / sp, 2)] for b in st["boxes"]],
                "expected_flat_top_steps": [KO.expected_step(clef, "b", j) for j in (1, 2, 3)],
                "strokes": [dict(s_, rel=round((s_["cx"] - st["x_start"]) / sp, 2)) for s_ in zone]}
    json.dump(res, open(outp, "w"), indent=0)
    for k, v in res.items():
        print(k, "clef", v["clef"], "N", v["N"], "pieces", v["pieces"], "chain", v["flat_stems_chain"], "exp", v["expected_flat_top_steps"])
        for s_ in v["strokes"]:
            print("    rel %5.2f run %4.2f w %4.2f top %6.2f bot %6.2f" % (s_["rel"], s_["run"], s_["w"], s_["top"], s_["bot"]))


if __name__ == "__main__":
    main()
