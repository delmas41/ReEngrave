"""WHERE DOES THE CONVENTION FAIL? Split it until the failure names itself.

Sean: *"The convention is strong. The failure is elsewhere."*

⚠️ THE STRONGEST SINGLE TEST IS DISTANCE FROM THE MIDDLE LINE. The convention
is a claim about a BOUNDARY, so a note far above or below the middle line is
unambiguous and a note ON it is the only genuinely conventional case. If the
convention is strong and merely noisy near its own boundary, accuracy must
RISE STEEPLY with distance. If it is FLAT with distance, the failure is not
the convention at all -- something is wrong with the head, the staff it was
filed under, or the grid its position was measured against, and a note five
steps clear of the middle line is getting called wrong.

⚠️ AND THE SECOND SPLIT NAMES A CANDIDATE: a head standing in the WRONG
STAFF'S CELL. A measure cell is cut with padding above and below, so on a
conductor's page one piece of ink is detected once per staff. Such a head's
STEM and BEAM come from the neighbour's music -- so the two ink readings agree
with each other -- while its POSITION is measured against THIS staff's lines
and is wrong by several steps. `Q.GLYPH_OWNER` already names them.
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))

MIDDLE_LINE = 4.0


def convention(pos):
    return "down" if pos <= MIDDLE_LINE else "up"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--json", default=str(HERE / "out" / "where-it-fails.json"))
    a = ap.parse_args()
    doc = json.load(open(a.record))
    rec = doc["record"] if "record" in doc else doc

    pos_of, resid = {}, {}
    for o in rec["observations"]:
        if o["quantity"] == "notehead_staff_position":
            try:
                pos_of[o["subject"]] = float(o["value"])
            except (TypeError, ValueError):
                continue
            r = (o.get("detail") or {}).get("residual")
            if r is not None:
                resid[o["subject"]] = float(r)

    proj = {v["subject"]: v["value"] for v in rec["verdicts"]
            if v["quantity"] == "stem_direction"
            and v["reason"] == "stem_projection"}
    owner = {v["subject"]: v for v in rec["verdicts"]
             if v["quantity"] == "glyph_owner"}

    rows = [(s, pos_of[s], d) for s, d in proj.items() if s in pos_of]
    print(f"heads scored: {len(rows)}")

    # ── 1. by distance from the middle line ────────────────────────────────
    bands = collections.defaultdict(collections.Counter)
    for s, p, d in rows:
        dist = abs(p - MIDDLE_LINE)
        band = ("0-1" if dist <= 1 else "1-2" if dist <= 2 else
                "2-4" if dist <= 4 else "4-6" if dist <= 6 else "6+")
        bands[band]["right" if convention(p) == d else "wrong"] += 1
    print("\n── by DISTANCE from the middle line (steps)")
    print(f"{'band':<8} {'n':>7} {'right':>7} {'wrong':>7} {'accuracy':>9}")
    out = {"by_distance": {}}
    for band in ("0-1", "1-2", "2-4", "4-6", "6+"):
        c = bands[band]
        n = c["right"] + c["wrong"]
        if not n:
            continue
        out["by_distance"][band] = {"n": n, "right": c["right"],
                                    "accuracy": round(c["right"] / n, 4)}
        print(f"{band:<8} {n:>7} {c['right']:>7} {c['wrong']:>7} "
              f"{c['right'] / n:>9.3f}")

    # ── 2. by whether the head is a relocated copy ─────────────────────────
    by_owner = collections.defaultdict(collections.Counter)
    for s, p, d in rows:
        v = owner.get(s)
        if v is None:
            key = "no ownership verdict"
        elif v["outcome"] != "decided":
            key = "ownership abstained"
        else:
            key = ("owned by ANOTHER staff" if str(v.get("value")) != s.rsplit("/", 1)[0]
                   and str(v.get("value")) not in ("", "None")
                   else "owned by this staff")
        by_owner[key]["right" if convention(p) == d else "wrong"] += 1
    print("\n── by what `glyph_owner` says")
    out["by_owner"] = {}
    for key, c in sorted(by_owner.items()):
        n = c["right"] + c["wrong"]
        out["by_owner"][key] = {"n": n, "accuracy": round(c["right"] / n, 4)}
        print(f"{key:<26} {n:>7} {c['right'] / n:>9.3f}")

    # ── 3. by how cleanly the position sits on the grid ────────────────────
    #  ⚠️ `residual` is |pos - round(pos)| -- how far the head's centre is
    #  from a line or a space. A head the grid cannot place lands between
    #  them, and that is a measurement of the GRID rather than of the music.
    by_res = collections.defaultdict(collections.Counter)
    for s, p, d in rows:
        r = resid.get(s)
        key = ("no residual" if r is None else
               "clean (<0.15)" if r < 0.15 else
               "0.15-0.30" if r < 0.30 else "off-grid (>=0.30)")
        by_res[key]["right" if convention(p) == d else "wrong"] += 1
    print("\n── by the position's own RESIDUAL (how far off a line/space)")
    out["by_residual"] = {}
    for key, c in sorted(by_res.items()):
        n = c["right"] + c["wrong"]
        out["by_residual"][key] = {"n": n, "accuracy": round(c["right"] / n, 4)}
        print(f"{key:<26} {n:>7} {c['right'] / n:>9.3f}")

    # ── 4. THE ANOMALY, CROSSED. Accuracy rises with distance -- 0.537 at
    #  the boundary to 0.939 four-to-six steps out -- and then FALLS to 0.765
    #  beyond six. That reversal is the finding: a note three spaces clear of
    #  the middle line is the LEAST ambiguous case the convention has, so it
    #  cannot be the convention that fails there. Beyond the staff the grid is
    #  no longer reading printed lines, it is extrapolating past them -- which
    #  this repo has already measured mis-suggesting 38-39% of second-ledger
    #  variants against 4.6% inside the staff.
    cross = collections.defaultdict(collections.Counter)
    for s_, p_, d in rows:
        dist = abs(p_ - MIDDLE_LINE)
        band = "inside the staff (<=4)" if dist <= 4 else \
               "just outside (4-6)" if dist <= 6 else "ledger country (6+)"
        r = resid.get(s_)
        key = (band, "off-grid" if (r is not None and r >= 0.30) else "on-grid")
        cross[key]["right" if convention(p_) == d else "wrong"] += 1
    print("\n── the anomaly, crossed with the position's residual")
    print(f"{'band':<24} {'grid':<10} {'n':>6} {'accuracy':>9}")
    out["cross"] = {}
    for key in sorted(cross):
        c = cross[key]
        n = c["right"] + c["wrong"]
        out["cross"][" / ".join(key)] = {"n": n,
                                         "accuracy": round(c["right"] / n, 4)}
        print(f"{key[0]:<24} {key[1]:<10} {n:>6} {c['right'] / n:>9.3f}")

    Path(a.json).write_text(json.dumps(out, indent=1))
    print(f"\nwrote {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
