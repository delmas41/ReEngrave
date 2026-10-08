"""lane-farhead-vs-geometry (2026-10-07), step 1: on the 10-07 DAY records, the decided far heads where the note-first reader
and plain geometry give DIFFERENT answers and exactly one fails Sean's through-or-edge check (the named line runs through the
box, or lies on its staff-side edge) on the verifier's GRID rows, split by cause.  GATHER+ADJUDICATE verdicts only; READ ONLY
(the day extract `night_1007_extract.py` and the replay `night_1007_replay.py`, which reproduces the record's positions).

  python3 farhead_vs_geometry.py <dir with <doc>-20261007-day.json and rep_<doc>.json> <out.json> [--ink]

Grid rows = the per-bar five lines (the reader's `lines_used`), ledger rows EXTRAPOLATED at one staff space each
(`offbox_check.Rows(lines)`, no rungs) -- the rows `night_1006_report` calls "reader-independent".  Own rows =
`Rows(lines, rungs)`: the ledger rows the reader measured.

DECOMPOSITION (`decompose`; rules fixed before counting), for a head the READER fails on the grid and geometry passes:
  grid_extrapolation  the reader passes the same check on its own measured rows
  box                 it fails there too, and passes on the box the reader used, or its line is a staff-side edge line farther
                      than EDGE_TOL from the detector box edge (the box is looser than the head ink)
  on_line_off_centre  it fails there too: ON a line whose row is outside the central 50 % of the box
  other               the rest
and for a head GEOMETRY fails on the grid and the reader passes: whether geometry fails on the measured rows too.

INK CHECK (`--ink`, independent of the reader's rungs): row(q) = the centre of the ink run (>= 50 % dark over the flank columns
0.05-0.8 sp beside the box) within 0.5 sp of the grid row of q's named line; Sean's rule on those rows for the reader's answer
and for geometry's, over every decided replayed head whose two rows both have ink.
"""
from __future__ import annotations
import collections, json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import numpy as np
import offbox_check as C
import overnight_1004_report as R

TAG = "20261007-day"
DOCS = R.DOCS


def named_line(p):
    """the even position whose line the answer names: itself if even, else the staff-side bounding line."""
    return p if p % 2 == 0 else (p + 1 if p < 0 else p - 1)


def decompose(r):
    own = C.Rows(r["lines"], r["rungs"])
    if not r["reader_pass"]:
        if C.passes(r["reader"], r["box"], own):
            return "grid_extrapolation", ("geometry_also_fails_measured_rows" if not C.passes(r["geo"], r["box"], own) else "geometry_passes_measured_rows")
        p = r["reader"]
        if r["box_used"] and C.passes(p, r["box_used"], own):
            return "box", "passes_on_the_reader_box"
        if r["kind"] == "space" and r["how"] == "staff_side_edge":
            return "box", "edge_line_farther_than_tol_from_box_edge"
        if r["kind"] == "on":
            return "on_line_off_centre", ""
        return "other", str(r["how"])
    return "geometry_fails_grid", ("geometry_fails_measured_rows_too" if not C.passes(r["geo"], r["box"], own) else "geometry_passes_measured_rows")


class InkRows(C.Rows):
    """Rows snapped to the ink: row(q) = centre of the ink run within 0.5 sp of the grid row; None where there is none."""

    def __init__(self, lines, gray, box):
        super().__init__(lines)
        self.gray, self.box, self.cache = gray, box, {}

    def y(self, q):
        if q not in self.cache:
            self.cache[q] = _snap(self.gray, super().y(q), self.box, self.sp)
        return self.cache[q]


def _snap(gray, y, box, sp):
    thr = min(int(np.percentile(gray[int(y - 2 * sp):int(y + 2 * sp), int(box[0] - 3 * sp):int(box[2] + 3 * sp)], 25) + 40), 140)
    best = None
    for x0, x1 in ((int(box[0] - 0.8 * sp), int(box[0] - 0.05 * sp)), (int(box[2] + 0.05 * sp), int(box[2] + 0.8 * sp))):
        x0 = max(0, x0)
        rows = [r for r in range(int(y - 0.5 * sp), int(y + 0.5 * sp) + 1) if 0 <= r < gray.shape[0] and (gray[r, x0:x1] <= thr).mean() >= 0.5]
        runs, cur = [], []
        for r in rows:
            if cur and r == cur[-1] + 1:
                cur.append(r)
            else:
                if cur:
                    runs.append(cur)
                cur = [r]
        if cur:
            runs.append(cur)
        for c in runs:
            v = float(np.mean(c))
            if best is None or abs(v - y) < abs(best - y):
                best = v
    return best


def ink_check(doc, data, rep):
    import cv2
    import truth_set_2_44c as ts
    from frame import render_page_matching_gather
    by_page = collections.defaultdict(list)
    for s, g in data["glyphs"].items():
        if R.is_far(g) and "box" in g and "geo" in g and (g.get("np") or {}).get("outcome") == "decided":
            m = rep.get(s)
            if m and m.get("repro") and m.get("lines"):
                by_page[R.page_of(s)].append((s, g, m))
    tot = collections.Counter()
    for page, hs in sorted(by_page.items()):
        gray = cv2.cvtColor(render_page_matching_gather(ts.DOCS[doc]["pdf"], page, 600).rgb, cv2.COLOR_RGB2GRAY)
        for s, g, m in hs:
            p, q = int(round(float(g["np"]["value"]))), R.geo_pos(g)
            ir = InkRows(m["lines"], gray, g["box"])
            ok = {}
            for lab, pos in (("reader", p), ("geometry", q)):
                ok[lab] = None if ir.y(named_line(pos)) is None else C.passes(pos, g["box"], ir)
            if ok["reader"] is None or ok["geometry"] is None:
                tot["unmeasured"] += 1
                continue
            tot["n"] += 1
            tot["reader_pass"] += ok["reader"]
            tot["geometry_pass"] += ok["geometry"]
            if p != q:
                tot["differ"] += 1
                tot["differ_reader_pass"] += ok["reader"]
                tot["differ_geometry_pass"] += ok["geometry"]
        print(doc, "ink page", page, dict(tot), flush=True)
    return dict(tot)


def main(d, out, ink=False):
    res = {}
    for doc in DOCS:
        if not (Path(d) / f"rep_{doc}.json").exists():
            continue
        data = json.loads((Path(d) / f"{doc}-{TAG}.json").read_text())
        rep = json.loads((Path(d) / f"rep_{doc}.json").read_text())["heads"]
        tot = collections.Counter()
        rows_out = []
        for s, g in data["glyphs"].items():
            if not R.is_far(g) or "box" not in g or "geo" not in g:
                continue
            np_ = g.get("np") or {}
            if np_.get("outcome") != "decided":
                continue
            m = rep.get(s)
            if not m or not m.get("repro") or not m.get("lines"):
                tot["not_replayed"] += 1
                continue
            rows = C.Rows(m["lines"])
            p = int(round(float(np_["value"])))
            q = R.geo_pos(g)
            rp, gp = C.passes(p, g["box"], rows), C.passes(q, g["box"], rows)
            tot["n"] += 1
            tot["reader_pass"] += rp
            tot["geo_pass"] += gp
            tot["same_answer"] += (p == q)
            tot[("R" if rp else "r") + ("G" if gp else "g")] += 1
            if p != q and rp != gp:
                rows_out.append(dict(subject=s, doc=doc, reader=p, geo=q, reader_pass=bool(rp), geo_pass=bool(gp),
                                     box=g["box"], lines=m["lines"], line_y=m.get("line_y"), edge_y=m.get("edge_y"),
                                     kind=m.get("kind"), how=m.get("how"), k=m.get("k"), between=m.get("between"),
                                     box_used=m.get("box_used"), rungs=m.get("rungs"), own=(g.get("own") or {}).get("value")))
        dec = collections.Counter(decompose(r) for r in rows_out)
        res[doc] = dict(tally=dict(tot), rows=rows_out, decomposition={f"{a}|{b}": v for (a, b), v in dec.items()})
        n = tot["n"]
        print(doc, "decided & replayed", n, "| reader passes the grid check", tot["reader_pass"], f"({100 * tot['reader_pass'] / n:.1f}%)",
              "| geometry passes", tot["geo_pass"], f"({100 * tot['geo_pass'] / n:.1f}%) | same answer", tot["same_answer"])
        print("   R/G = reader/geometry passes (lower case = fails):", {k: tot[k] for k in ("RG", "Rg", "rG", "rg")})
        for (a, b), v in sorted(dec.items()):
            print("   ", a, b, v)
        if ink:
            t = res[doc]["ink"] = ink_check(doc, data, rep)
            print("   INK check:", t, f"reader {100 * t['reader_pass'] / t['n']:.1f}%  geometry {100 * t['geometry_pass'] / t['n']:.1f}%  (n={t['n']})")
    Path(out).write_text(json.dumps(res))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], "--ink" in sys.argv)
