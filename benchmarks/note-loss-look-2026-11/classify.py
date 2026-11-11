"""2.289 classify: sort every `owned_by_another_staff` and `claimed_by:barline` subject from capture.py's fates.json into
(a) twin of a written note, (b) not a notehead (automatic PROXY only), (c) written elsewhere, (d) lost, (e) cannot tell.
The sort is the pipeline's own data: NOT evidence (CLAUDE rule 7). Crops and Sean's tiles decide.

    python3 benchmarks/note-loss-look-2026-11/classify.py CAPDIR OUT.json
"""
import collections
import json
import pathlib
import sys

HEAD_W = {"litolff": 23.0, "brahms": 38.5}      # median written head width in page px, measured by this script's first pass
IOU_TWIN = 0.3                                   # the pipeline's own SAME_INK_IOU (export.py); the test is stated, not tuned
WRITTEN = ("written", "written_relocated")
OWNED = "owned_by_another_staff"
BARLINE = ("not_a_notehead:claimed_by:barline", "not_a_rest:claimed_by:barline")


def iou(a, b):
    x0, y0, x1, y1 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    i = max(0.0, x1 - x0) * max(0.0, y1 - y0)
    u = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i
    return i / u if u > 0 else 0.0


def twin_of(row, pool, min_iou=IOU_TWIN):
    """The best-overlapping row of `pool` (same page) with IoU > min_iou, else None. Must be able to fail: see selftest()."""
    best = None
    for t in pool:
        if t is row or t["page"] != row["page"] or not t["box"]:
            continue
        v = iou(row["box"], t["box"])
        if v > min_iou and (best is None or v > best[0]):
            best = (v, t)
    return best


def classify_owned(r, heads_by_staff, heads_all):
    """-> (class, detail). Looks for a WRITTEN head with the same ink on the staff the box was assigned to."""
    ok = tuple(int(v) for v in r["owner"].split("/")[1:4])
    on_owner = heads_by_staff.get(ok, [])
    t_any = twin_of(r, on_owner)
    if t_any and t_any[1]["fate"] in WRITTEN:
        return "a_twin_written_on_owner", {"iou": round(t_any[0], 2), "twin": t_any[1]["sub"]}
    if t_any:  # the owner's copy exists but is not written: is any OTHER written head on this ink?
        for t in heads_all:
            if t is r or t is t_any[1] or t["page"] != r["page"] or t["fate"] not in WRITTEN or not t["box"]:
                continue
            if iou(r["box"], t["box"]) > IOU_TWIN:
                return "c_written_elsewhere", {"twin": t["sub"], "staff": t["staff"]}
        f = t_any[1]["fate"]
        if f == "mark_group_duplicate":
            return "e_group_twin_check", {"twin": t_any[1]["sub"], "twin_fate": f}
        return "d_candidate_lost_owner_copy_not_written", {"twin": t_any[1]["sub"], "twin_fate": f}
    for t in heads_all:      # no box on the owner staff: written anywhere else on this ink?
        if t is r or t["page"] != r["page"] or t["fate"] not in WRITTEN or not t["box"]:
            continue
        if iou(r["box"], t["box"]) > IOU_TWIN:
            return "c_written_elsewhere", {"twin": t["sub"], "staff": t["staff"]}
    return "d_candidate_lost_no_twin_box", {}


def classify_barline(r, heads_written, plate):
    b = r["box"]
    w = b[2] - b[0]
    t = twin_of(r, heads_written)
    if t:
        return "a_twin_written", {"iou": round(t[0], 2), "twin": t[1]["sub"]}
    if w < 0.4 * HEAD_W[plate]:
        return "b_proxy_narrow_sliver", {"w": round(w, 1)}
    return "e_wide_box_on_barline", {"w": round(w, 1)}


def selftest():
    """The twin test must be able to FAIL: a constructed case with no twin, and one whose twin is not written."""
    mk = lambda sub, box, fate, staff: {"sub": sub, "page": 0, "staff": staff, "box": box, "fate": fate}
    loser = mk("L", [100, 100, 120, 120], OWNED, 1)
    owner_twin_written = mk("T", [101, 101, 121, 121], "written", 0)
    owner_twin_dropped = mk("T2", [101, 101, 121, 121], "duration_narrowed", 0)
    far = mk("F", [400, 100, 420, 120], "written", 0)
    loser["owner"] = "glyph/0/0/0"
    by = lambda rows: {(0, 0, 0): [r for r in rows if r["staff"] == 0]}
    r1 = classify_owned(loser, by([owner_twin_written]), [loser, owner_twin_written])
    r2 = classify_owned(loser, by([far]), [loser, far])
    r3 = classify_owned(loser, by([owner_twin_dropped]), [loser, owner_twin_dropped])
    assert r1[0] == "a_twin_written_on_owner", r1
    assert r2[0] == "d_candidate_lost_no_twin_box", r2      # fails (= reports no twin) when the twin is elsewhere
    assert r3[0].startswith("d_candidate_lost_owner_copy"), r3  # fails when the twin exists but was not written
    return "selftest ok: twin found, no-twin reported, unwritten-twin reported"


def main(capdir, out):
    print(selftest())
    result = {}
    for plate in ("litolff", "brahms"):
        R = json.load(open(pathlib.Path(capdir, plate + ".fates.json")))
        heads = [r for r in R if r["head"] and r["box"]]
        by = collections.defaultdict(list)
        for r in heads:
            by[(r["page"], r["system"], r["staff"])].append(r)
        written = [r for r in heads if r["fate"] in WRITTEN]
        rows = []
        for r in R:
            if r["fate"] == OWNED:
                c, d = classify_owned(r, by, heads)
                reason = OWNED
            elif r["fate"] in BARLINE:
                c, d = classify_barline(r, written, plate)
                reason = r["fate"]
            else:
                continue
            rows.append(dict(r, cls=c, detail=d, reason=reason))
        result[plate] = rows
        cnt = collections.Counter((x["reason"], x["cls"]) for x in rows)
        print(plate)
        for k, v in sorted(cnt.items()):
            print("  %4d  %s  %s" % (v, k[0], k[1]))
    json.dump(result, open(out, "w"))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
