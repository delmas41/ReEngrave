"""ROADMAP 2.222 cause lane: where does an oversized written notehead box come from? STAGED, read-only.

    python3 benchmarks/notehead-box-cap-2026-10/cause/trace.py rows     # per-box table -> cause/rows.json + counts
    python3 benchmarks/notehead-box-cap-2026-10/cause/trace.py sheets   # contact sheets of every oversized box + controls (scratch)

Input: the 2.221 census extract (branch lane-2.221-m0, `census.py extract`) of the 2.202f ON-arm saved gathers + exported
symbols (hosts = notes EXPORT wrote, matched to the glyph key AND the same page box -- census.py's own match), and the page
rasters `render_page(pdf, p, dpi=600).binary` cached as .npy by the 2.221/2.222 lanes (re-rendered if absent).

Per written-note head box: its READER (which GATHER step filed the box: `detector` = the production detector pass,
`yolo_rescue_lowconf` / `yolo_rescue_stem_head` = the same detector re-run below the floor), its size in its own staff's spaces,
and what INK is in it (staff-line rows of that staff removed):
  ink_w/ink_h   tight bbox of the ink inside the box (spaces)
  slack         box size minus that tight ink size, per axis (spaces): how much empty paper the box takes in
  comp          the 8-connected ink component holding most of the box's ink: its bbox (spaces) and the share of it inside the box
  stem_in_box   the longest vertical ink run inside the box, in spaces (a head is ~1 sp tall; a stem run inside the box is > 1.3)
  n_marks       ink components with >= 15% of a head's area inside the box
"""
import collections, json, os, pathlib, pickle, random, sys
import cv2, numpy as np

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
SCR = pathlib.Path("/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-agent-manager-workflow-356c39/7e1ea73e-2fd3-4d6c-a450-36868f7e14c0/scratchpad")
PKL = SCR / "census-extract.pkl"
LIB = pathlib.Path("/Users/seanjohnson/Desktop/ReEngrave/library")
PDF = {"litolff": "editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
       "brahms": "editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"}
BIG_W, BIG_H = 1.9, 1.8
N_CONTROL = 15          # per plate, random normal-sized boxes


def page(plate, p):
    f = SCR / ("page_%s_%d.npy" % (plate, p))
    if f.exists():
        return np.load(f)
    from tools.omr.preprocessing import render_page
    a = render_page(str(LIB / PDF[plate]), p, dpi=600).binary
    np.save(f, a)
    return a


def load():
    d = pickle.loads(PKL.read_bytes())
    out = {}
    for plate, D in d.items():
        rows = D["rows"]
        sp = {r["subject"]: float(r["value"]) for r in rows["staff_spacing"]}
        lines = {r["subject"]: [float(v) for v in r["value"]] for r in rows["staff_lines"]}
        thick = {r["subject"]: float(np.mean(r["detail"].get("thickness_px") or [4])) for r in rows.get("staff_skew", [])}
        by = {r["subject"]: r for r in rows["glyph_box"]}
        notes = collections.defaultdict(list)
        for h in D["hosts"]:
            if h["kind"] == "note":
                notes[h["rg"]].append(h)
        items = []
        for rg, hs in notes.items():
            r = by[rg]
            b = r["detail"]["bbox_page_px"]
            assert all(max(abs(h["box"][i] - b[i]) for i in range(4)) < 1 for h in hs)   # the written box IS the gathered box
            p = rg.split("/")
            sk = "staff/%s/%s/%s" % (p[1], p[2], p[3])
            s = sp[sk]
            items.append(dict(plate=plate, key=rg, page=int(p[1]), cls=r["value"][0], reader=r["reader"], score=None,
                              box=b, sp=s, w=(b[2] - b[0]) / s, h=(b[3] - b[1]) / s, n_notes=len(hs),
                              pitches=[h["pitch"] for h in hs], lines=lines.get(sk, []), thick=thick.get(sk, 4.0),
                              detail={k: v for k, v in r["detail"].items() if k != "bbox_page_px"}))
        out[plate] = items
    return out


def ink_measure(pg, it):
    s = it["sp"]
    x0, y0, x1, y1 = it["box"]
    m = int(3 * s)
    X0, Y0 = max(0, int(x0) - m), max(0, int(y0) - m)
    X1, Y1 = min(pg.shape[1], int(x1) + m + 1), min(pg.shape[0], int(y1) + m + 1)
    win = (pg[Y0:Y1, X0:X1] == 0).astype(np.uint8)
    for ly in it["lines"]:                                  # staff-line rows out (a line is see-through)
        hh = int(round(it["thick"] / 2.0)) + 1
        a, b = int(round(ly)) - hh - Y0, int(round(ly)) + hh + 1 - Y0
        a, b = max(0, a), min(win.shape[0], b)
        if b > a:
            # keep columns where ink continues just above AND below the line (a head or stem crossing it)
            up = win[max(0, a - 2):a].any(axis=0) if a > 0 else np.zeros(win.shape[1], bool)
            dn = win[b:b + 2].any(axis=0) if b < win.shape[0] else np.zeros(win.shape[1], bool)
            keep = up & dn
            win[a:b, ~keep] = 0
    bx0, by0, bx1, by1 = int(round(x0)) - X0, int(round(y0)) - Y0, int(round(x1)) - X0, int(round(y1)) - Y0
    inb = np.zeros_like(win); inb[by0:by1, bx0:bx1] = 1
    n, lab, st, _ = cv2.connectedComponentsWithStats(win, connectivity=8)
    res = dict(ink_w=0.0, ink_h=0.0, slack_w=it["w"], slack_h=it["h"], comp_w=0.0, comp_h=0.0, comp_in=0.0, stem_in_box=0.0, n_marks=0)
    box_ink = win * inb
    ys, xs = np.nonzero(box_ink)
    if len(xs) == 0:
        return res
    res["ink_w"] = (xs.max() - xs.min() + 1) / s
    res["ink_h"] = (ys.max() - ys.min() + 1) / s
    res["slack_w"] = it["w"] - res["ink_w"]
    res["slack_h"] = it["h"] - res["ink_h"]
    ids, cnt = np.unique(lab[box_ink > 0], return_counts=True)
    best = ids[np.argmax(cnt)]
    cx, cy, cw, ch, ca = st[best]
    res["comp_w"], res["comp_h"] = cw / s, ch / s
    res["comp_in"] = float(cnt.max()) / ca
    head_area = 1.2 * 1.0 * s * s * 0.8
    res["n_marks"] = int(sum(c >= 0.15 * head_area for c in cnt))
    col = box_ink[by0:by1, bx0:bx1]
    best_run = 0
    for c in range(col.shape[1]):
        v = col[:, c]
        run = r = 0
        for x in v:
            r = r + 1 if x else 0
            run = max(run, r)
        best_run = max(best_run, run)
    res["stem_in_box"] = best_run / s
    # the HEAD-LIKE part of the box's ink: rows at least 0.6 sp wide, columns at least 0.5 sp tall (a stem is ~0.1-0.2 sp
    # wide, a beam or a thick line ~0.5 sp tall, so stems drop out of dense_h and thin strokes out of dense_w)
    res["dense_h"] = float((col.sum(axis=1) >= 0.6 * s).sum()) / s
    res["dense_w"] = float((col.sum(axis=0) >= 0.5 * s).sum()) / s
    return res


def kind(r):
    """What the oversized box holds, from the ink alone (verified by eye on cause sheets; see FINDINGS)."""
    if r["slack_w"] > 0.4 or r["slack_h"] > 0.4:
        return "loose"            # >= 0.4 sp of empty paper inside the box on one axis
    if r["dense_h"] >= 1.6:
        return "tall_ink"         # box tight on ink that is head-wide for >= 1.6 sp: two heads a step/third apart in one blob, or a tall mark
    if r["dense_w"] >= 1.9:
        return "wide_ink"         # box tight on ink that is >= 1.9 sp wide: head + neighbour side by side, or a wide mark (ff, beam)
    if r["h"] > BIG_H:
        return "stem_in_box"      # head-sized dense ink, the extra height is a run of stem inside the box
    return "edge"                 # head-sized ink, box just over the cut


def rows():
    data = load()
    rnd = random.Random(2222)
    allrows = []
    for plate, items in data.items():
        big = [it for it in items if it["w"] > BIG_W or it["h"] > BIG_H]
        normal = [it for it in items if not (it["w"] > BIG_W or it["h"] > BIG_H)]
        ctl = rnd.sample(normal, N_CONTROL)
        for grp, L in (("big", big), ("control", ctl)):
            for it in L:
                pg = page(plate, it["page"])
                it.update(ink_measure(pg, it)); it["group"] = grp
                allrows.append(it)
        print(plate, "written note boxes", len(items), "big", len(big), "by reader", dict(collections.Counter(i["reader"] for i in big)),
              "| all by reader", dict(collections.Counter(i["reader"] for i in items)), flush=True)
    for r in allrows:
        r.pop("lines", None)
        r["kind"] = kind(r) if r["group"] == "big" else "control"
    for plate in ("litolff", "brahms"):
        c = collections.Counter((r["reader"], r["kind"]) for r in allrows if r["plate"] == plate and r["group"] == "big")
        print(plate, "oversized by (reader, kind):")
        for k, v in sorted(c.items()):
            print("   ", k, v)
        ctl = [r for r in allrows if r["plate"] == plate and r["group"] == "control"]
        print(plate, "controls: slack_w/h max %.2f/%.2f, dense_h max %.2f, dense_w max %.2f" % (
            max(r["slack_w"] for r in ctl), max(r["slack_h"] for r in ctl), max(r["dense_h"] for r in ctl), max(r["dense_w"] for r in ctl)))
    (HERE / "rows.json").write_text(json.dumps(allrows, indent=0, default=float))


def sheets():
    R = json.loads((HERE / "rows.json").read_text())
    for plate in ("litolff", "brahms"):
        L = [r for r in R if r["plate"] == plate]
        L.sort(key=lambda r: (r["group"] != "big", r["reader"], -max(r["w"], r["h"])))
        tiles = []
        for i, r in enumerate(L):
            pg = page(plate, r["page"])
            s = r["sp"]
            x0, y0, x1, y1 = r["box"]
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            m = 4 * s
            X0, Y0 = int(max(0, cx - m)), int(max(0, cy - m))
            crop = cv2.cvtColor(pg[Y0:int(cy + m), X0:int(cx + m)], cv2.COLOR_GRAY2BGR)
            f = 160.0 / crop.shape[0]
            crop = cv2.resize(crop, (int(crop.shape[1] * f), 160), interpolation=cv2.INTER_AREA)
            cv2.rectangle(crop, (int((x0 - X0) * f), int((y0 - Y0) * f)), (int((x1 - X0) * f), int((y1 - Y0) * f)), (0, 0, 255), 2)
            t = np.full((190, 170, 3), 255, np.uint8)
            t[:160, :min(170, crop.shape[1])] = crop[:, :170]
            lab = "%d %s %.1fx%.1f %s" % (i, {"detector": "D", "yolo_rescue_lowconf": "LC", "yolo_rescue_stem_head": "SH"}.get(r["reader"], r["reader"]),
                                         r["w"], r["h"], "C" if r["group"] == "control" else "")
            cv2.putText(t, lab, (2, 178), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 0, 0), 1)
            tiles.append(t)
        per = 40
        for k in range(0, len(tiles), per):
            chunk = tiles[k:k + per]
            while len(chunk) % 8:
                chunk.append(np.full_like(tiles[0], 255))
            grid = np.vstack([np.hstack(chunk[j:j + 8]) for j in range(0, len(chunk), 8)])
            cv2.imwrite(str(SCR / ("cause_sheet_%s_%d.png" % (plate, k // per))), grid)
        print(plate, len(tiles), "tiles")


def kinds():
    """One zoomed sheet per (plate, kind), for the eye check of `kind`."""
    R = json.loads((HERE / "rows.json").read_text())
    for plate in ("litolff", "brahms"):
        by = collections.defaultdict(list)
        for r in R:
            if r["plate"] == plate and r["group"] == "big":
                by[r["kind"]].append(r)
        for k, L in by.items():
            tiles = []
            for i, r in enumerate(L):
                pg = page(plate, r["page"]); s = r["sp"]
                x0, y0, x1, y1 = r["box"]; cx, cy = (x0 + x1) / 2, (y0 + y1) / 2; m = int(3.5 * s)
                X0, Y0 = int(cx - m), int(cy - m)
                c = cv2.cvtColor(pg[Y0:Y0 + 2 * m, X0:X0 + 2 * m], cv2.COLOR_GRAY2BGR)
                f = 220.0 / c.shape[0]; c = cv2.resize(c, (220, 220), interpolation=cv2.INTER_AREA)
                cv2.rectangle(c, (int((x0 - X0) * f), int((y0 - Y0) * f)), (int((x1 - X0) * f), int((y1 - Y0) * f)), (0, 0, 255), 2)
                cv2.putText(c, "%d %.1fx%.1f n%d" % (i, r["w"], r["h"], r["n_notes"]), (2, 214), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 0, 0), 1)
                tiles.append(c)
            while len(tiles) % 6:
                tiles.append(np.full_like(tiles[0], 255))
            grid = np.vstack([np.hstack(tiles[j:j + 6]) for j in range(0, len(tiles), 6)])
            cv2.imwrite(str(SCR / ("kind_%s_%s.png" % (plate, k))), grid)
            print(plate, k, len(L))


NAMES = {"T": "two_heads_one_blob", "B": "head_merged_with_neighbour_ink", "H": "head_ink_itself_this_big",
         "A": "box_runs_along_stem", "N": "not_a_notehead"}


def count():
    """Counts per cause per plate per reader, from the eye labels (eye_labels.json) on the oversized boxes."""
    R = json.loads((HERE / "rows.json").read_text())
    E = json.loads((HERE / "eye_labels.json").read_text())
    out = {}
    for plate in ("litolff", "brahms"):
        big = [r for r in R if r["plate"] == plate and r["group"] == "big"]
        if plate == "litolff":
            seq = []
            byk = collections.defaultdict(list)
            for r in big:
                byk[r["kind"]].append(r)
            for k, L in byk.items():
                labs = E[plate][k]
                assert len(labs) == len(L), (k, len(labs), len(L))
                seq += list(zip(L, labs))
        else:
            L = sorted(big, key=lambda r: (r["reader"], -max(r["w"], r["h"])))
            assert len(L) == len(E[plate]["_sheet"])
            seq = list(zip(L, E[plate]["_sheet"]))
        c = collections.Counter((NAMES[l], r["reader"]) for r, l in seq)
        tot = collections.Counter(NAMES[l] for r, l in seq)
        two_written_once = sum(1 for r, l in seq if l == "T" and r["n_notes"] == 1)
        out[plate] = {"oversized": len(seq), "by_cause": dict(tot), "by_cause_reader": {"%s|%s" % k: v for k, v in c.items()},
                      "two_heads_written_as_one_note": two_written_once}
        for r, l in seq:
            r["eye"] = NAMES[l]
    (HERE / "counts.json").write_text(json.dumps(out, indent=1))
    (HERE / "rows.json").write_text(json.dumps(R, indent=0, default=float))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    {"rows": rows, "sheets": sheets, "kinds": kinds, "count": count}[sys.argv[1]]()
