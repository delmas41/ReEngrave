"""Open the GEOMETRY of every tie pairing `_pair_ties_in_staff` makes.

The pairing probe one benchmark over (`omr-chord-tie-2026-09/probe/
pairing_pitches.py`) says a quarter of the links bind two DIFFERENT pitches.
It cannot say why. This re-runs the pairing rule's own arithmetic over a stored
`.omr.json` and reports, per tie glyph, every candidate it considered — so the
question "what did the rule see, and what did it pick" is answerable without a
print and without a truth file.

⚠️ It RE-DERIVES the rule rather than calling it, because `_pair_ties_in_staff`
mutates and returns only a count: it records no link, which is the defect
itself. The `y_tol` and `3x` window are literals INSIDE that function, so they
are restated here and pinned against its source by
`tools/omr/tests/test_tie_pairing.py`, which fails if either drifts.

    python3 .../geometry.py <dir-or-file>... [--list N]
"""
from __future__ import annotations

import collections
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))


def staff_pairs(staff: dict):
    """Yield one record per tie glyph, mirroring `_pair_ties_in_staff`."""
    nh_list = []
    tie_list = []
    for m in staff.get("measures", []):
        for det in m.get("detections", []):
            bp = det.get("bbox_page")
            if not bp or len(bp) != 4:
                continue
            xc = bp[0] + bp[2] / 2.0
            yc = bp[1] + bp[3] / 2.0
            if det.get("category") == "notehead":
                nh_list.append((xc, yc, bp[2], det))
            elif (det.get("class") or "").lower() == "tie":
                tie_list.append(bp)
    if not tie_list or len(nh_list) < 2:
        return
    avg_nh_h = sum(d.get("bbox_page")[3] for _, _, _, d in nh_list) / len(nh_list)
    y_tol = max(avg_nh_h * 3, 30)
    for tie_bp in tie_list:
        tx0, ty0, tw, th = tie_bp
        tie_left, tie_right, tie_yc = tx0, tx0 + tw, ty0 + th / 2.0
        lefts, rights = [], []
        for xc, yc, w, det in nh_list:
            if abs(yc - tie_yc) > y_tol:
                continue
            dxl = tie_left - xc
            if 0 <= dxl < w * 3:
                lefts.append((dxl, yc, det))
            dxr = xc - tie_right
            if 0 <= dxr < w * 3:
                rights.append((dxr, yc, det))
        pick_l = min(lefts, key=lambda t: t[0]) if lefts else None
        pick_r = min(rights, key=lambda t: t[0]) if rights else None
        yield dict(tie=tie_bp, tie_yc=tie_yc, y_tol=y_tol, avg_nh_h=avg_nh_h,
                   lefts=lefts, rights=rights, pick_l=pick_l, pick_r=pick_r)


def walk(result: dict):
    for page in result.get("pages", []):
        for s in page.get("systems", []):
            for staff in s.get("staves", []):
                yield from staff_pairs(staff)


def main() -> int:
    args = sys.argv[1:]
    n_list = 0
    if "--list" in args:
        i = args.index("--list")
        n_list = int(args[i + 1])
        del args[i:i + 2]
    files = []
    for a in args:
        p = pathlib.Path(a)
        files += sorted(p.glob("*.omr.json")) if p.is_dir() else [p]
    if not files:
        sys.stderr.write("FATAL: no `.omr.json`\n")
        return 2
    pooled: collections.Counter = collections.Counter()
    for f in files:
        c: collections.Counter = collections.Counter()
        shown = 0
        for r in walk(json.loads(f.read_text())):
            c["ties"] += 1
            left, right = r["pick_l"], r["pick_r"]
            if left is None or right is None:
                c["unpaired"] += 1
                continue
            if left[2] is right[2]:
                c["self"] += 1
                continue
            c["paired"] += 1
            pl, pr = left[2].get("pitch"), right[2].get("pitch")
            same = pl is not None and pl == pr
            c["same_pitch" if same else "DIFF_pitch"] += 1
            l_p = {d.get("pitch") for _, _, d in r["lefts"]}
            r_p = {d.get("pitch") for _, _, d in r["rights"]}
            if not same and (l_p & r_p):
                c["DIFF_but_a_same_pitch_pair_was_in_range"] += 1
            if len(r["lefts"]) > 1:
                c["left_had_a_choice"] += 1
            if len(r["rights"]) > 1:
                c["right_had_a_choice"] += 1
            if not same and shown < n_list:
                shown += 1
                print(
                    f"    {pl}->{pr}  tie_yc={r['tie_yc']:.0f} "
                    f"y_tol={r['y_tol']:.0f} nh_h={r['avg_nh_h']:.0f}\n"
                    f"      L(dx,pitch,dy): "
                    f"{[(round(d[0]), d[2].get('pitch'), round(d[1] - r['tie_yc'])) for d in r['lefts']]}\n"
                    f"      R(dx,pitch,dy): "
                    f"{[(round(d[0]), d[2].get('pitch'), round(d[1] - r['tie_yc'])) for d in r['rights']]}")
        pooled += c
        print(f"{f.name[:46]:48s} ties={c['ties']:4d} paired={c['paired']:4d} "
              f"same={c['same_pitch']:4d} DIFF={c['DIFF_pitch']:4d} "
              f"unpaired={c['unpaired']:4d} self={c['self']:4d} "
              f"Lchoice={c['left_had_a_choice']:4d} "
              f"Rchoice={c['right_had_a_choice']:4d} "
              f"rescuable={c['DIFF_but_a_same_pitch_pair_was_in_range']:3d}")
    print("\n pooled: " + "  ".join(f"{k}={v}" for k, v in sorted(pooled.items())))
    if not pooled["ties"]:
        sys.stderr.write("⚠️ ZERO tie glyphs — a dead instrument.\n")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
