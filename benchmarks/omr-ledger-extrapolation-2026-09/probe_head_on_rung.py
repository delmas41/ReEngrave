"""THE DECISIVE TEST: a head standing on a printed rung has a TRUE position
that comes from COUNTING INK, and the grid can be scored against it.

Everything else on this thread -- the stem convention, the residual, the
projection -- is one of our readings agreeing or disagreeing with another of
our readings. This is not. A ledger line is a LINE: a head sitting on the
m-th rung out from the staff is at position `edge +/- 2m`, FULL STOP, and m
is obtained by counting the rungs printed between the staff and the head in
that head's own x-column. No grid enters that count.

So for every such head:

    true_pos  = 0 - 2m   (above)  |  8 + 2m  (below)      <- from ink
    read_pos  = Q.NOTEHEAD_STAFF_POSITION                 <- from the grid
    error     = read_pos - true_pos

and `round(read_pos) != true_pos` is a head the pipeline places on the wrong
staff position, which through any clef is **the wrong PITCH**.

⚠️ THE CALIBRATION THAT LICENSES THIS. 1,107 `ledgerLine` detections on this
record land INSIDE the staff, every one of them at 0/2/4/6/8 -- the five
PRINTED staff lines, whose positions are known exactly. Scored there the
class's box carries a bias of +0.011 staff spaces at sd 0.048, so it locates
a printed horizontal line to a twentieth of a space. That is measured, not
assumed, and it is what makes a rung usable as truth.

⚠️ WHAT THIS STILL IS NOT. It is not the PRINT: a rung the detector missed
makes m too small, and a spurious rung makes it too large. Both are counted
and reported. The crop pass is still owed.
"""
from __future__ import annotations

import argparse
import collections
import json
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from recordstream import stream_array  # noqa: E402

TOP_LINE, BOTTOM_LINE = 0.0, 8.0
# One rung per staff SPACE, the window `measure_ledger_rungs` uses
# (0.65-1.35 of the local pitch), expressed in HALF-steps.
LADDER_MIN, LADDER_MAX = 1.30, 2.70
# ⚠️ IS THE HEAD *ON* THE RUNG, OR IN THE SPACE BESIDE IT? A notehead box on
# this record is a median 2.62 half-steps tall -- taller than the step it
# sits on -- so "the rung is inside the box" also admits the neighbouring
# space, and an earlier cut of this probe scored those as line notes for an
# invented -1.0 half-step error. The discriminator is the head's OWN height,
# which is not the grid: measured over the 836 heads INSIDE the staff whose
# line-or-space is not in doubt, |rung - head centre| / head height reads
#   ON a line   n=430  median 0.022  p95 0.062  max 0.143
#   IN a space  n=406  median 0.374  p5  0.292  min 0.129
# an empty interval either side of 0.25, which is where these sit.
# ⚠️⚠️ AND THE TWO CUTS DO NOT MEET -- A HEAD BETWEEN THEM ABSTAINS. A first
# cut put a single threshold at 0.25 and the FIRST CROP refuted it: the head
# `glyph/1/0/3/9/3` sits in the SPACE above the first rung, 0.22 head-heights
# off it, and was scored as a line note for an invented 1.0 half-step error.
# The bias is vicious, because a head misclassified that way is scored WRONG
# BY CONSTRUCTION -- so the very population one would crop first is the
# population the classifier is wrong about. The measured distributions leave
# a gap (ON p95 0.062 / max 0.143; SPACE p5 0.292 / min 0.129) and this now
# refuses to answer inside it, which is the empty-interval discipline this
# repo already applies to dot windows, tie flanks and bracket columns.
ON_RUNG_MAX = 0.15
IN_SPACE_MIN, IN_SPACE_MAX = 0.29, 0.60


def cell_of(subject: str) -> str | None:
    p = subject.split("/")
    return "cell/" + "/".join(p[1:5]) if p[0] == "glyph" and len(p) == 6 else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--label", required=True)
    ap.add_argument("--json", required=True)
    ap.add_argument("--dump", help="write the per-head table here (for crops)")
    a = ap.parse_args()

    pos_of: dict[str, float] = {}
    box: dict[str, tuple] = {}          # name, x, y, w, h
    page_box: dict[str, list] = {}
    half: dict[str, float] = {}
    for o in stream_array(a.record, "observations"):
        q = o.get("quantity")
        if q == "notehead_staff_position":
            try:
                pos_of[o["subject"]] = float(o["value"])
            except (TypeError, ValueError):
                pass
        elif q == "glyph_box":
            v = o.get("value")
            if isinstance(v, list) and len(v) == 5:
                box[o["subject"]] = (v[0], float(v[1]), float(v[2]),
                                     float(v[3]), float(v[4]))
                bp = (o.get("detail") or {}).get("bbox_page_px")
                if bp:
                    page_box[o["subject"]] = bp
        elif q == "cell_staff_space":
            hs = (o.get("detail") or {}).get("half_step")
            if hs:
                half[o["subject"]] = float(hs)

    owner: dict[str, dict] = {}
    for v in stream_array(a.record, "verdicts"):
        if v.get("quantity") == "glyph_owner":
            owner[v["subject"]] = v

    # grid origin per cell, from the heads that already read on it
    org: dict[str, list] = {}
    for s, po in pos_of.items():
        c = cell_of(s)
        hs = half.get(c) if c else None
        b = box.get(s)
        if c and hs and b:
            org.setdefault(c, []).append(b[2] + b[4] // 2 - po * hs)
    origin = {c: statistics.median(v) for c, v in org.items()}

    rungs_by_cell: dict[str, list[tuple[float, float, float]]] = \
        collections.defaultdict(list)          # (pos, x0, x1)
    for s, b in box.items():
        if b[0] != "ledgerLine":
            continue
        c = cell_of(s)
        if c is None or c not in origin or c not in half:
            continue
        pos = (b[2] + b[4] // 2 - origin[c]) / half[c]
        if pos < TOP_LINE - 0.6 or pos > BOTTOM_LINE + 0.6:
            rungs_by_cell[c].append((pos, b[1], b[1] + b[3]))

    print(f"{a.label}: {len(pos_of)} heads, "
          f"{sum(len(v) for v in rungs_by_cell.values())} rungs outside the "
          f"staff in {len(rungs_by_cell)} cells")

    rows = []
    stats = collections.Counter()
    for s, read in pos_of.items():
        c = cell_of(s)
        if c is None or c not in origin or c not in half or s not in box:
            continue
        if TOP_LINE <= read <= BOTTOM_LINE:
            stats["inside the staff"] += 1
            continue
        b = box[s]
        hx0, hx1 = b[1], b[1] + b[3]
        hy0, hy1 = b[2], b[2] + b[4]
        above = read < TOP_LINE
        # rungs in this head's own x-column, on this head's side
        col = [r for r in rungs_by_cell.get(c, [])
               if r[1] <= (hx0 + hx1) / 2 <= r[2]
               and ((r[0] < TOP_LINE) if above else (r[0] > BOTTOM_LINE))]
        if not col:
            stats["outside, NO rung in its x-column"] += 1
            continue
        # ⚠️ DEDUPE FIRST. One printed rung is routinely detected twice (this
        # record holds a pair 0.02 half-steps apart), and a duplicate counted
        # as a rung shifts every index beyond it.
        col.sort(key=lambda r: -r[0] if above else r[0])
        ladder: list[float] = []
        for pos_r, _, _ in col:
            d = (TOP_LINE - pos_r) if above else (pos_r - BOTTOM_LINE)
            if ladder and abs(d - ladder[-1]) < 0.5:
                continue
            ladder.append(d)
        # ⚠️ THE LADDER MUST BE COMPLETE, and this is the rule the earlier
        # cut of this probe skipped and paid for. `measure_ledger_rungs`
        # walks outward "one rung per space (window 0.65-1.35 of the local
        # pitch)" and its findings record that extrapolating a whole ladder
        # from one distant rung measured WORSE than the constant. On this
        # record `glyph/4/0/5/4/6` stands on the FOURTH rung with only the
        # fourth detected; counted naively it scored as the first, for an
        # invented error of -6.02 half-steps. A broken ladder ABSTAINS.
        m, prev = 0, 0.0
        on_rung = in_space = None
        ambiguous = False
        y_mid = (hy0 + hy1) / 2
        height = max(b[4], 1.0)
        for d in ladder:
            if not (LADDER_MIN <= d - prev <= LADDER_MAX):
                break                      # the trail is lost: stop counting
            m += 1
            prev = d
            y_r = origin[c] + (TOP_LINE - d if above else BOTTOM_LINE + d) * half[c]
            gap = abs(y_r - y_mid) / height
            if gap <= ON_RUNG_MAX:
                on_rung = m
                break
            if gap < IN_SPACE_MIN:
                ambiguous = True
                break
            past = (y_r < hy0) if above else (y_r > hy1)
            if past:
                break                      # the ladder ran past the head
        if ambiguous:
            stats["outside, ON-a-line vs IN-a-space is AMBIGUOUS"] += 1
            continue
        if on_rung is None and m:
            # the head may sit in the SPACE just beyond the outermost rung --
            # equally ink-grounded, and the engraver prints rungs only up to
            # the last LINE below the note, so `m` is that rung's index.
            y_r = origin[c] + (TOP_LINE - prev if above else BOTTOM_LINE + prev) * half[c]
            beyond = (y_mid < y_r) if above else (y_mid > y_r)
            gap = abs(y_r - y_mid) / height
            if beyond and IN_SPACE_MIN < gap <= IN_SPACE_MAX:
                in_space = m
        if on_rung is None and in_space is None:
            stats["outside, ladder broken or head unplaceable"] += 1
            continue
        if on_rung is not None:
            steps, kind = 2 * on_rung, "line"
        else:
            steps, kind = 2 * in_space + 1, "space"
        true_pos = (TOP_LINE - steps) if above else (BOTTOM_LINE + steps)
        v = owner.get(s)
        relocated = bool(v and v.get("outcome") == "decided"
                         and str(v.get("value")) not in ("", "None",
                                                         s.rsplit("/", 2)[0]))
        rows.append({"subject": s, "cell": c, "side": "above" if above else "below",
                     "kind": kind, "m": on_rung if on_rung is not None else in_space, "true_pos": true_pos, "read_pos": read,
                     "rounded": int(round(read)),
                     "error": round(read - true_pos, 4),
                     "wrong": int(round(read)) != true_pos,
                     "relocated": relocated,
                     "page_box": page_box.get(s)})
        stats[f"SCORED: head on a counted ladder ({kind})"] += 1

    print("\n== population")
    for k, n in stats.most_common():
        print(f"  {k:<42} {n:>6}")
    if not rows:
        print("DEAD: no head stands on a counted rung", file=sys.stderr)
        return 2

    out: dict = {"label": a.label, "record": a.record,
                 "population": dict(stats)}

    for tag, sel in (("ALL scored heads", rows),
                     ("owned by THIS staff", [r for r in rows if not r["relocated"]]),
                     ("relocated copies", [r for r in rows if r["relocated"]])):
        if not sel:
            continue
        errs = [r["error"] for r in sel]
        wrong = sum(r["wrong"] for r in sel)
        out[tag] = {"n": len(sel), "mean_error": round(statistics.fmean(errs), 4),
                    "median_error": round(statistics.median(errs), 4),
                    "wrong": wrong, "wrong_rate": round(wrong / len(sel), 4)}
        print(f"\n== {tag}: n={len(sel)}  mean error "
              f"{statistics.fmean(errs):+.4f} half-steps   "
              f"WRONG POSITION {wrong} ({wrong / len(sel):.1%})")

    print("\n== by rung index m  (error should grow as 2m(k-1))")
    print(f"{'side':<6} {'m':>2} {'n':>5} {'mean err':>9} {'median':>8} "
          f"{'wrong':>6} {'rate':>7}")
    out["by_rung"] = {}
    for side in ("above", "below"):
        for m in range(1, 7):
            sel = [r for r in rows if r["side"] == side and r["m"] == m]
            if not sel:
                continue
            errs = [r["error"] for r in sel]
            w = sum(r["wrong"] for r in sel)
            out["by_rung"][f"{side} {m}"] = {
                "n": len(sel), "mean_error": round(statistics.fmean(errs), 4),
                "wrong": w, "wrong_rate": round(w / len(sel), 4)}
            print(f"{side:<6} {m:>2} {len(sel):>5} {statistics.fmean(errs):>+9.4f} "
                  f"{statistics.median(errs):>+8.4f} {w:>6} {w / len(sel):>7.1%}")

    Path(a.json).write_text(json.dumps(out, indent=1))
    if a.dump:
        Path(a.dump).write_text(json.dumps(rows, indent=1))
        print(f"wrote {a.dump} ({len(rows)} heads)")
    print(f"wrote {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
