"""ROADMAP 2.50 -- the real-data measurement over `Q.HOLLOW_HEAD_CENTRE`,
off the small re-gather (GATHER+ADJUDICATE only, `acceptance_quick`'s
default mode, Litolff p3, `--weights auto`).

NO new measurement and NO wiring change: this script only READS the
record's own rows (`Q.HOLLOW_HEAD_CENTRE`, `Q.GLYPH_BOX`, `Q.CELL_STAFF_
SPACE`, `Q.NOTEHEAD_STAFF_POSITION`) and reports population, the box-vs-
hole delta, and how many hollow heads would change ROUNDED staff position
if the hole centre were used instead of the box centre -- CLAUDE.md rule
5 ("print before default"): nothing here flips a default.

Usage: python3 benchmarks/omr-local-staff-2026-09/analyze_2_50.py <record.json>
"""
from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from tools.omr.staged import record_io
from tools.omr.staged.record import Q


def main(path: str) -> None:
    rec = record_io.load_record(path)["record"]
    obs = rec["observations"]
    abst = rec["abstentions"]

    hollow_obs = [o for o in obs if o["quantity"] == Q.HOLLOW_HEAD_CENTRE]
    hollow_abs = [a for a in abst if a["quantity"] == Q.HOLLOW_HEAD_CENTRE]
    reasons = collections.Counter(a["reason"] for a in hollow_abs)

    print(f"hollow heads MEASURED (one enclosed hole found): {len(hollow_obs)}")
    print(f"hollow heads ABSTAINED: {len(hollow_abs)}, by reason:")
    for reason, n in reasons.most_common():
        print(f"  {n:4d}  {reason}")

    # box (GLYPH_BOX) by subject, for the matching glyph's own canonical centre
    box_by_subject = {}
    for o in obs:
        if o["quantity"] == Q.GLYPH_BOX:
            v = o["value"]
            if isinstance(v, (list, tuple)) and len(v) >= 5:
                _, x, y, w, h = v
                box_by_subject[o["subject"]] = (x + w / 2.0, y + h / 2.0)

    # Q.CELL_STAFF_SPACE half_step by CELL subject (parent of the glyph)
    half_step_by_cell = {}
    for o in obs:
        if o["quantity"] == Q.CELL_STAFF_SPACE:
            det = o.get("detail") or {}
            if "half_step" in det:
                half_step_by_cell[o["subject"]] = float(det["half_step"])

    def cell_of(glyph_subject: str) -> str:
        # "glyph/p/s/st/c/g" -> "cell/p/s/st/c"
        parts = glyph_subject.split("/")
        return "cell/" + "/".join(parts[1:5])

    # Q.NOTEHEAD_STAFF_POSITION rounded value by subject (box-centre-based)
    pos_by_subject = {}
    for o in obs:
        if o["quantity"] == Q.NOTEHEAD_STAFF_POSITION:
            pos_by_subject[o["subject"]] = (o["value"], (o.get("detail") or {}).get("rounded"))

    dxs, dys = [], []
    changed = []
    for o in hollow_obs:
        sub = o["subject"]
        hx, hy = o["value"]
        box = box_by_subject.get(sub)
        half_step = half_step_by_cell.get(cell_of(sub))
        pos = pos_by_subject.get(sub)
        if box is None or half_step is None or pos is None:
            continue
        bx, by = box
        dxs.append(hx - bx)
        dys.append(hy - by)
        pos_float_box, rounded_box = pos
        pos_float_hole = pos_float_box + (hy - by) / half_step
        rounded_hole = int(round(pos_float_hole))
        if rounded_hole != rounded_box:
            changed.append((sub, rounded_box, rounded_hole, hy - by, half_step))

    def stats(xs):
        if not xs:
            return (0.0, 0.0)
        mean = sum(xs) / len(xs)
        var = sum((x - mean) ** 2 for x in xs) / len(xs)
        return (mean, var ** 0.5)

    mx, sx = stats(dxs)
    my, sy = stats(dys)
    print()
    print(f"hole-centre MINUS box-centre, canonical cell px (n={len(dxs)}):")
    print(f"  horizontal: mean={mx:+.3f}  stdev={sx:.3f}")
    print(f"  vertical:   mean={my:+.3f}  stdev={sy:.3f}")
    print()
    print(f"hollow heads whose ROUNDED staff position would CHANGE if the "
          f"hole centre were used instead of the box centre: {len(changed)} "
          f"of {len(dxs)}")
    for sub, rb, rh, dy, half_step in changed:
        print(f"  {sub}: box-rounded={rb:+d} hole-rounded={rh:+d} "
              f"dy={dy:+.2f}px half_step={half_step:.2f}px")

    out = {
        "record": path,
        "measured": len(hollow_obs),
        "abstained": len(hollow_abs),
        "abstained_by_reason": dict(reasons),
        "delta_px": {"horizontal_mean": mx, "horizontal_stdev": sx,
                     "vertical_mean": my, "vertical_stdev": sy, "n": len(dxs)},
        "rounded_position_changes": [
            {"subject": sub, "box_rounded": rb, "hole_rounded": rh,
             "dy_px": dy, "half_step_px": half_step}
            for sub, rb, rh, dy, half_step in changed],
    }
    out_path = Path(__file__).parent / "analyze_2_50_output.json"
    out_path.write_text(json.dumps(out, indent=2))
    print(f"\nwrote {out_path}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else
         str(REPO_ROOT / "benchmarks/acceptance/quick/out/beethoven5-litolff/"
             "beethoven5-litolff-p3.record.json"))
