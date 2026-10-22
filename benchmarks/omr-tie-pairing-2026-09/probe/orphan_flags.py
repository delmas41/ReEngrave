"""A tie flag whose TIE GLYPH is not in the staff any more. No truth file.

⚠️ FOUND BY A CONTROL FAILING, NOT BY LOOKING FOR IT. `repair_arm.py --control`
replays both shipped tie rules over a stored `.omr.json` and requires the flags
to come back identical. They do not: three engraved rows come back SHORT. The
missing flags sit on noteheads in staves that hold no tie glyph anywhere near
them — and the glyph that set them is sitting in the NEXT STAFF DOWN.

The ordering says why, and it is not subtle. In `transcribe`:

    line 2289   `_pair_ties_in_cell`   sets flags
    line 5356   `_pair_ties_in_staff`  sets flags
    line 5557   `_dedupe_cross_staff_detections`   REMOVES the losing staff's
                copy of a contested glyph

A measure cell is padded above and below, so a neighbouring staff's tie is
detected in this staff's cell too. Both copies pair. Then dedupe awards the
glyph to one staff and deletes the other copy — AND THE FLAGS THE DELETED COPY
SET STAY BEHIND. So the losing staff exports a `<tied>` for ink the pipeline
itself decided was not its own, and the winning staff gets no extra tie because
pairing has already run. The same cross-staff padding this project has recorded
for noteheads, hairpins, dynamic letters and (in `export.py`) for arcs — here
arriving as a STALE CONSEQUENCE rather than as a wrong attribution.

This counts them: a flagged notehead is ORPHANED when its own staff holds no
`tie` glyph whose flank windows could reach it, under the same `3x notehead
width` / `3x notehead height` windows `_pair_ties_in_staff` uses — widened
here, deliberately, by also admitting a glyph merely OVERLAPPING the head in x,
so a within-cell pairing cannot be counted as an orphan by a window mismatch.

⚠️ IT IS AN UPPER BOUND ON ONE CAUSE AND A LOWER BOUND ON ANOTHER. A flag whose
glyph moved to a staff that ALSO has its own tie near that x is not counted —
so the true stale-flag population is at least this. And a legitimate flag whose
glyph was dropped for some other reason would be counted here too.

    python3 .../orphan_flags.py <dir-or-file>...
"""
from __future__ import annotations

import collections
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))


def _staff_rows(result):
    for page in result.get("pages", []):
        for sys_ in page.get("systems", []):
            staves = sys_.get("staves", [])
            for idx, staff in enumerate(staves):
                yield idx, staff, staves


def _arcs(staff, cls):
    for m in staff.get("measures", []):
        for d in m.get("detections", []):
            bp = d.get("bbox_page")
            if bp and len(bp) == 4 and (d.get("class") or "").lower() == cls:
                yield bp


def _reachable(bp_head, ties) -> bool:
    hx0, hy0, hw, hh = bp_head
    xc, yc = hx0 + hw / 2.0, hy0 + hh / 2.0
    for tx0, ty0, tw, th in ties:
        if abs((ty0 + th / 2.0) - yc) > max(hh * 3, 30):
            continue
        # flanked on either side, within the rule's own dx window...
        if 0 <= tx0 - xc < hw * 3 or 0 <= xc - (tx0 + tw) < hw * 3:
            return True
        # ...or simply overlapping it in x, which is the within-cell case.
        if tx0 <= xc <= tx0 + tw:
            return True
    return False


def main() -> int:
    files: list[pathlib.Path] = []
    for a in sys.argv[1:]:
        p = pathlib.Path(a)
        files += sorted(p.glob("*.omr.json")) if p.is_dir() else [p]
    if not files:
        sys.stderr.write("FATAL: no `.omr.json`\n")
        return 2
    pooled: collections.Counter = collections.Counter()
    print(f"{'file':46s} {'flagged':>8s} {'ORPHAN':>7s} "
          f"{'of which a NEIGHBOUR staff has the tie':>40s}")
    for f in files:
        c: collections.Counter = collections.Counter()
        result = json.loads(f.read_text())
        for idx, staff, staves in _staff_rows(result):
            own = list(_arcs(staff, "tie"))
            near = []
            for j in (idx - 1, idx + 1):
                if 0 <= j < len(staves):
                    near += list(_arcs(staves[j], "tie"))
            for m in staff.get("measures", []):
                for d in m.get("detections", []):
                    if not (d.get("tied_to_next") or d.get("tied_from_prev")):
                        continue
                    bp = d.get("bbox_page")
                    if not bp or len(bp) != 4:
                        continue
                    c["flagged"] += 1
                    if _reachable(bp, own):
                        continue
                    c["orphan"] += 1
                    if _reachable(bp, near):
                        c["orphan_neighbour_has_it"] += 1
        pooled += c
        print(f"{f.name[:46]:46s} {c['flagged']:8d} {c['orphan']:7d} "
              f"{c['orphan_neighbour_has_it']:40d}")
    print(f"\n{'POOLED':46s} {pooled['flagged']:8d} {pooled['orphan']:7d} "
          f"{pooled['orphan_neighbour_has_it']:40d}")
    if not pooled["flagged"]:
        sys.stderr.write("⚠️ ZERO flagged noteheads — a dead instrument.\n")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
