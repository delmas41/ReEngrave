"""arcs-r2 fix 1 (an end binds where the ink is): for every bound end of a run (from a replay's `<plate>.on.extra.json`), where does the run's own ink end stand against the
bar cell of the head it bound? An end whose ink stands OUTSIDE the head's cell has a barline between it and the head.

    python3 census_barline.py SLICEDIR PLATE EXTRA.json [PAGE ...]
Prints one line per end with a barline between ink end and bound head (signed px past the cell edge, in staff spaces), and the distribution over all bound ends.
"""
import collections
import json
import pathlib
import sys


def main(slicedir, plate, extra, pages):
    sd = pathlib.Path(slicedir) / plate
    cells, heads, runs = {}, {}, {}
    for line in open(sd / "observations.jsonl"):
        o = json.loads(line)
        q, s = o["quantity"], o["subject"]
        if q == "cell_box":
            cells[s] = o["value"]
        elif q == "glyph_box" and (o.get("detail") or {}).get("category") == "notehead":
            heads[s] = o["detail"]["bbox_page_px"]
        elif q == "page_arc" and o["value"] == "run":
            runs[(s, o["detail"]["ordinal"])] = o["detail"]
    ex = json.load(open(extra))
    n = collections.Counter()
    for v in ex:
        pg = v["subject"]
        if pages and int(pg.split("/")[1]) not in pages:
            continue
        for r in v["detail"]["runs"]:
            d = runs.get((pg, r["ordinal"]))
            if d is None:
                continue
            core = d.get("core_ends") or [e[:2] for e in d["ends"]]
            if r.get("piece") is not None:
                xr = r.get("x_range") or [None, None]
                pts = [q for q in d["points"] if xr[0] <= q[0] <= xr[1]]
            else:
                pts = d["points"]
            ink = [pts[0], pts[-1]]          # the outermost TRACED points (extension included)
            sp = d["space_page_px"]
            for side, e, ie in (("left", core[0], ink[0]), ("right", core[1], ink[1])):
                b = r.get(side)
                if not b or not b.get("head"):
                    continue
                h = b["head"]
                parts = h.split("/")
                cell = "cell/" + "/".join(parts[1:5])
                c = cells.get(cell)
                if c is None:
                    n["no_cell"] += 1
                    continue
                past = (c[0] - e[0]) if e[0] < c[0] else (e[0] - c[2]) if e[0] > c[2] else 0.0
                past_ink = (c[0] - ie[0]) if ie[0] < c[0] else (ie[0] - c[2]) if ie[0] > c[2] else 0.0
                n["bound_ends"] += 1
                if past > 0:
                    n["core_end_outside_head_cell"] += 1
                if past_ink > 0:
                    n["ink_end_outside_head_cell"] += 1
                    # BEHIND: the head stands on the exterior side of the end (left end: head left of the ink end)
                    behind = (side == "left" and c[2] <= ie[0]) or (side == "right" and c[0] >= ie[0])
                    n["behind" if behind else "ahead"] += 1
                    hb = heads[h]
                    gap = (ie[0] - hb[2]) if side == "left" else (hb[0] - ie[0])
                    print("gap(ink end -> head near edge)=%.2f sp" % (gap / sp), end=" ")
                    print("%s %s run %s %s ink end x=%.0f (core %.0f) head %s cell x %.0f-%.0f: ink end %.2f sp %s the cell [%s] | status %s kind %s crosses %s" % (
                        plate, pg, r["ordinal"], side, ie[0], e[0], h, c[0], c[2], past_ink / sp, "left of" if ie[0] < c[0] else "right of", "BEHIND" if behind else "ahead", r["status"], r.get("kind"), r.get("crosses_barline")))
    print(dict(n))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3], {int(x) for x in sys.argv[4:]})
