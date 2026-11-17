"""2.281: arcs gained / lost between two arms of a saved re-adjudication, by (kind, start head, stop head), per page; and on Brahms p0 which KEY arcs flip right <-> not right.

    python3 diff_arms_281.py ARMS_DIR PLATE ARM_A ARM_B       (A = before, B = after)
"""
import collections
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "page-ink-2026-11" / "step2"))
sys.path.insert(0, str(HERE))
import arcs as A  # noqa: E402
import score_key as K  # noqa: E402


def page_of(k):
    return int(k.split("/")[1])


def arcs(d, plate, arm):
    xml = (pathlib.Path(d) / ("%s.%s.musicxml" % (plate, arm))).read_text()
    return {(a["kind"], a["start"], a["stop"]) for a in A.arcs_of_xml(xml)}


if __name__ == "__main__":
    d, plate, a, b = sys.argv[1:5]
    A_, B_ = arcs(d, plate, a), arcs(d, plate, b)
    gained, lost = B_ - A_, A_ - B_
    by = collections.defaultdict(lambda: collections.Counter())
    for k, s, z in gained:
        by[page_of(s)]["+" + k] += 1
    for k, s, z in lost:
        by[page_of(s)]["-" + k] += 1
    print(plate, a, "->", b, "arcs", len(A_), "->", len(B_))
    for pg in sorted(by):
        print("  page", pg, dict(by[pg]))
    if plate == "brahms":
        ra = K.score(K.written(d, "%s.%s" % (plate, a)))[1]
        rb = K.score(K.written(d, "%s.%s" % (plate, b)))[1]
        ra = {r[0]: r[4] for r in ra}
        rb = {r[0]: r[4] for r in rb}
        flips = collections.Counter((ra[k], rb[k]) for k in ra if ra[k] != rb[k])
        print("  p0 key flips (before, after):", dict(flips))
        for k in ra:
            if ra[k] == "right" and rb[k] != "right":
                print("   LOST", k)
