"""lane-offbox-check (2026-10-05): Sean's rule -- "the line a far note's position names must run THROUGH the note's
box (note ON a line) or lie on the box's STAFF-SIDE edge (note in the space beyond it). A line anywhere else
cannot be right."  Built as a check on a (position, box, local staff lines) triple.

CONSTANTS, FIXED BEFORE ANY RESULT WAS LOOKED AT:
  BAND     = 0.50   ON-line: the named line's row must lie within the central 50% of the box height
                    (|y_line - box_centre| <= 0.25 * box_height).
  EDGE_TOL = 0.25   in-space: the bounding line on the STAFF side (p+1 for a head above the staff, p-1 below) must lie
                    within 0.25 staff spaces of the box's staff-side edge (box bottom above the staff, box top below).
                    A position inside the staff (odd p, 1..7) is bounded on both sides: BOTH lines must be within
                    EDGE_TOL of the box's two edges.

ROW CONVERSION. Position p (half-steps, 0 = top staff line, 8 = bottom, negative above): row(p) = top + p*(bot-top)/8
with top/bot = the staff's outer lines AT THE HEAD'S x (`far_head_reader.frame_lines_for_head`, which reads the local
lines on the gather's raster and falls back to the record's staff-wide lines only where no local read exists).
For a ledger position that is an EXTRAPOLATION of the local grid (no measured ledger row is used here); the
grid-vs-measured offset is quantified separately by `offbox_calibrate.py` (replay of the reader, its measured rungs).

"HOW FAR OFF" = the nearest position q (|q-p| smallest, integers within +-8) that WOULD pass the check on the same box
and lines; reported as |q-p| steps (half-staff-spaces). Ties between two directions report the same |q-p|.

  python3 offbox_check.py <dir with the extracted JSONs> <out.json>
Reads only the small JSONs `overnight_1004_extract.py` wrote (run-2 files must carry `boxes`).
"""
from __future__ import annotations
import collections, json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import cv2
import overnight_1004_report as R
import truth_set_2_44c as ts
from frame import render_page_matching_gather
from tools.omr.annotate import far_head_reader as FH

BAND = 0.50
EDGE_TOL = 0.25
DOCS = R.DOCS
RUNS = (("RUN1", "20261004-farhead"), ("RUN2", "20261004-farhead-all"))


class Rows:
    """The rows of the lines a position can name, at one head.  Staff lines: the local grid.  Ledger lines: where the
    reader's MEASURED rungs (`rungs`, y px) exist they are the rows, taken outward from the staff edge in order (a
    gap of k pitches between two rungs puts k-1 INTERPOLATED rows between them; a rung closer than half a space to the
    previous one is the same line); beyond the last measured rung the rows are EXTRAPOLATED at the last pitch.
    With no rungs every ledger row is the grid extrapolation top + p*(bot-top)/8 (pitch = one staff space)."""

    def __init__(self, lines, rungs=None):
        self.top, self.bot = min(lines), max(lines)
        self.sp = (self.bot - self.top) / 4.0
        self.led = {-1: ([], self.top, self.sp), 1: ([], self.bot, self.sp)}
        for side in (-1, 1):
            edge = self.top if side < 0 else self.bot
            outward = sorted((y for y in (rungs or []) if side * (y - edge) > 0.4 * self.sp), key=lambda y: side * (y - edge))
            rows, prev, pitch = [], edge, self.sp
            for y in outward:
                gap = side * (y - prev)
                if gap < 0.5 * self.sp:
                    continue
                m = max(1, int(round(gap / pitch)))
                step = gap / m
                for i in range(1, m):
                    rows.append((prev + side * step * i, "interpolated"))
                rows.append((y, "measured"))
                prev, pitch = y, step
            self.led[side] = (rows, prev, pitch)

    def _locate(self, q):
        """(y, kind) of the line at even position q."""
        if 0 <= q <= 8:
            return self.top + q * (self.bot - self.top) / 8.0, "staff"
        side = -1 if q < 0 else 1
        n = (-q // 2) if q < 0 else ((q - 8) // 2)
        rows, prev, pitch = self.led[side]
        if n <= len(rows):
            return rows[n - 1]
        return prev + side * pitch * (n - len(rows)), "extrapolated"

    def y(self, q):
        return self._locate(q)[0]

    def kind(self, q):
        return self._locate(q)[1]


def _rows(x):
    return x if isinstance(x, Rows) else Rows(x)


def row(lines, p):
    return Rows(lines).y(p) if p % 2 == 0 else Rows(lines).top + p * (Rows(lines).bot - Rows(lines).top) / 8.0


def bounding_lines(q):
    """The even positions whose rows bound an in-space position q on the STAFF side (both sides inside the staff)."""
    if q < 0:
        return (q + 1,)
    if q > 8:
        return (q - 1,)
    return (q - 1, q + 1)


def passes(q, box, rows):
    """True iff position q names a line that runs through the box (ON) or lies on its staff-side edge (in space)."""
    R_ = _rows(rows)
    x0, y0, x1, y1 = box
    h = y1 - y0
    cy = (y0 + y1) / 2.0
    if q % 2 == 0:
        return abs(R_.y(q) - cy) <= (BAND / 2.0) * h
    if q < 0:
        return abs(R_.y(q + 1) - y1) <= EDGE_TOL * R_.sp
    if q > 8:
        return abs(R_.y(q - 1) - y0) <= EDGE_TOL * R_.sp
    return abs(R_.y(q - 1) - y0) <= EDGE_TOL * R_.sp and abs(R_.y(q + 1) - y1) <= EDGE_TOL * R_.sp


def named_kinds(q, rows):
    """kinds of the line(s) the answer names (staff / measured / interpolated / extrapolated)."""
    R_ = _rows(rows)
    return [R_.kind(b) for b in ((q,) if q % 2 == 0 else bounding_lines(q))]


def off_steps(p, box, rows):
    """0 if p passes; else |q-p| of the nearest passing q (None if no q in +-8 passes)."""
    rows = _rows(rows)
    if passes(p, box, rows):
        return 0
    for d in range(1, 9):
        if passes(p - d, box, rows) or passes(p + d, box, rows):
            return d
    return None


def far_heads(data):
    G = data["glyphs"]
    return {s: g for s, g in G.items() if R.is_far(g) and "geo" in g and "box" in g}


def main(d, out):
    truth = json.loads((Path(d) / "truth.json").read_text())
    res = {}
    for doc in DOCS:
        pdf = ts.DOCS[doc]["pdf"]
        data = {n: R.load(d, doc, tag) for n, tag in RUNS}
        far = {n: far_heads(data[n]) for n in data}
        pages = sorted({R.page_of(s) for n in far for s in far[n]})
        per = {n: {} for n in data}
        declined = collections.Counter()
        for page in pages:
            pi = render_page_matching_gather(pdf, page, 600)
            gray = cv2.cvtColor(pi.rgb, cv2.COLOR_RGB2GRAY)
            for n in data:
                SL = data[n]["staff_lines"]
                for s, g in far[n].items():
                    if R.page_of(s) != page:
                        continue
                    key = "staff/" + "/".join(s.split("/")[1:4])
                    gl = SL.get(key)
                    if gl is None:
                        declined[(n, "no_staff_lines")] += 1
                        continue
                    lines = FH.frame_lines_for_head(gray, gl, g["box"])
                    local = list(lines) != list(gl)
                    declined[(n, "local" if local else "global_fallback")] += 1
                    np_ = g.get("np") or {}
                    dec = R.decided_pos(g) if np_.get("outcome") == "decided" else None
                    per[n][s] = dict(box=g["box"], lines=[float(y) for y in lines], local=local,
                                     geo=R.geo_pos(g), dec=dec, reason=np_.get("reason"),
                                     box_source=(g.get("fh") or {}).get("box_source"),
                                     has_fh="fh" in g, cls=g.get("cls"))
            print(doc, "page", page, "done", flush=True)
            del pi, gray
        res[doc] = dict(heads=per, lines_source={f"{k[0]}|{k[1]}": v for k, v in declined.items()},
                        truth=truth[doc])
    Path(out).write_text(json.dumps(res))
    print("wrote", out)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
