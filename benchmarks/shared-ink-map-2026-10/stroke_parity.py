"""ROADMAP 2.195 step 1 -- coverage parity of `Q.STROKE` against the quantities that already measure the same ink.

usage: python3 benchmarks/shared-ink-map-2026-10/stroke_parity.py GATHERED_RECORD.json OUT.json

For each existing row, is its ink covered by a stroke of a compatible kind in the same cell? Not a pixel test (the record holds boxes):
  stem          (Q.STEM, cv_lines)           >= 80% of the stem box's height lies along vertical strokes that overlap it in x
  beam, CV      (Q.BEAM_STROKE cv_lines)     >= 50% of the box's width lies along horizontal/curve strokes that overlap it in y
  beam, detector(Q.BEAM_STROKE detector)     same, and reported apart (it is the box that may be on a flag)
  ledger rung   (Q.LEDGER_RUNG_INK, true)    a horizontal/blob stroke overlaps the rung window (page frame): x overlap >= 50% of the
                                             window, y within half a space of the wanted row
  system arc    (Q.SYSTEM_ARC)               >= 80% of its x span lies along horizontal/curve strokes (page boxes) whose y range
                                             meets the arc's ends' y range +- 2.5 spaces
The control the script carries: `--shuffle` re-draws every stroke's cell at random; coverage must fall far below the real one.
"""
import json
import random
import sys
from collections import defaultdict
sys.path.insert(0, ".")
from tools.omr.staged import record_io


def span_cover(lo, hi, intervals):
    """Share of [lo, hi] covered by the union of intervals."""
    if hi <= lo:
        return 0.0
    iv = sorted((max(lo, a), min(hi, b)) for a, b in intervals if b > lo and a < hi)
    tot, cur = 0.0, lo
    for a, b in iv:
        if b <= cur:
            continue
        tot += b - max(a, cur)
        cur = b
    return tot / (hi - lo)


def cellkey(subj):
    return tuple(subj.split("/")[1:5])


def parity(obs, strokes):
    """obs: iterable of existing rows (dicts); strokes: {cellkey: [stroke-row dicts]}. Returns {kind: {n, covered, misses}}."""
    by_staff = defaultdict(list)
    for k, v in strokes.items():
        by_staff[k[:3]].extend(v)
    res = defaultdict(lambda: dict(n=0, covered=0, misses=[]))


    def note(kind, ok, row):
        r = res[kind]
        r["n"] += 1
        r["covered"] += int(ok)
        if not ok:
            r["misses"].append(row["subject"] + "|" + row["id"])


    for o in obs:
        q = o["quantity"]
        if q == "stem" and o["reader"] == "cv_lines":
            x, y, w, h = o["value"]
            iv = []
            for s in strokes.get(cellkey(o["subject"]), ()):
                if s["value"] != "vertical":
                    continue
                sx, sy, sw, sh = s["detail"]["stroke_box"]
                if sx < x + w and sx + sw > x:
                    iv.append((sy, sy + sh))
            note("stem", span_cover(y, y + h, iv) >= 0.8, o)
        elif q == "beam_stroke":
            x, y, w, h = o["value"]
            iv, iv_any, kinds = [], [], {}
            for s in strokes.get(cellkey(o["subject"]), ()):
                sx, sy, sw, sh = s["detail"]["stroke_box"]
                if sy < y + h and sy + sh > y and sx < x + w and sx + sw > x:
                    iv_any.append((sx, sx + sw))
                    ov = (min(x + w, sx + sw) - max(x, sx)) * (min(y + h, sy + sh) - max(y, sy))
                    kinds[s["value"]] = kinds.get(s["value"], 0) + ov
                if s["value"] not in ("horizontal", "curve"):
                    continue
                if sy < y + h and sy + sh > y:
                    iv.append((sx, sx + sw))
            tag = "beam_" + ("cv" if o["reader"] == "cv_lines" else "detector")
            ok = span_cover(x, x + w, iv) >= 0.5
            note(tag, ok, o)
            note(tag + "_anykind", span_cover(x, x + w, iv_any) >= 0.5, o)
            if not ok:       # which kind of stroke does hold the missed box's ink
                top = max(kinds, key=kinds.get) if kinds else "none"
                note(tag + "_miss_is_" + top, False, o)
        elif q == "ledger_rung_ink" and o["value"] is True:
            x0, y0, x1, y1 = o["detail"]["window_page_px"]
            wy = o["detail"]["want_y_page"]
            sp = None
            ok, ok_any = False, False
            ck = cellkey(o["subject"])
            for s in strokes.get(ck, ()):
                b = s["detail"].get("bbox_page_px")
                if not b:
                    continue
                ov = min(x1, b[2]) - max(x0, b[0])
                if ov >= 0.5 * (x1 - x0) and b[1] - 6 <= wy <= b[3] + 6:
                    ok_any = True
                    if s["value"] in ("horizontal", "blob"):
                        ok = True
                        break
            note("ledger_rung", ok, o)
            note("ledger_rung_anykind", ok_any, o)
        elif q == "system_arc":
            d = o["detail"]
            xl, xr, yl, yr, sp = d["x_left_page"], d["x_right_page"], d["y_left_page"], d["y_right_page"], d["space_page_px"]
            lo, hi = min(yl, yr) - 2.5 * sp, max(yl, yr) + 2.5 * sp
            sub = o["subject"].split("/")
            iv, iv_any = [], []
            # every cell of the arc's staff: an arc is cut at barlines and runs on past the cells its own row lists
            for s in by_staff.get((sub[1], sub[2], sub[3]), ()):
                if True:
                    b0 = s["detail"].get("bbox_page_px")
                    if b0 and b0[1] < hi and b0[3] > lo:
                        iv_any.append((b0[0], b0[2]))
                    if s["value"] not in ("horizontal", "curve"):
                        continue
                    b = s["detail"].get("bbox_page_px")
                    if b and b[1] < hi and b[3] > lo:
                        iv.append((b[0], b[2]))
            note("system_arc", span_cover(xl, xr, iv) >= 0.8, o)
            note("system_arc_anykind", span_cover(xl, xr, iv_any) >= 0.8, o)


    return res


def load_strokes(obs, shuffle=False):
    strokes = defaultdict(list)
    for o in obs:
        if o["quantity"] == "stroke":
            strokes[cellkey(o["subject"])].append(o)
    if shuffle:
        keys = list(strokes)
        perm = keys[:]
        random.Random(1).shuffle(perm)
        strokes = {k: strokes[p] for k, p in zip(keys, perm)}
    return strokes


if __name__ == "__main__":
    SHUF = "--shuffle" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    rec = record_io.load_record(args[0])
    obs = rec["record"]["observations"]
    strokes = load_strokes(obs, SHUF)
    res = parity(obs, strokes)
    out = {k: dict(n=v["n"], covered=v["covered"], pct=round(100.0 * v["covered"] / max(1, v["n"]), 2), misses=v["misses"][:400])
           for k, v in res.items()}
    out["_n_stroke_rows"] = sum(len(v) for v in strokes.values())
    json.dump(out, open(args[1], "w"), indent=1)
    for k, v in out.items():
        if k != "_n_stroke_rows":
            print("%-16s %6d rows  %6d covered  %6.2f%%" % (k, v["n"], v["covered"], v["pct"]))
    print("stroke rows", out["_n_stroke_rows"])
