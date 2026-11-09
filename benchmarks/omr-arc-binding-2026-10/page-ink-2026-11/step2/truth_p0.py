"""2.274 step 2: the exported file against Sean's Brahms p0 hand arcs, by PRINTED ARC (his per-cell boxes joined across a barline), not by box.

    python3 truth_p0.py WORKDIR [--list OFF|ON]

`benchmarks/omr-arc-binding-2026-10/p0_spans.py` scores a written span against ONE hand box: an arc that crosses a barline is two hand boxes (one per cell), so a span
that is RIGHT across the barline matches neither and counts as "matching no truth" -- the scorer built for a per-cell file penalises exactly what this lane writes. Here the
hand boxes of one printed arc are joined (`score.printed_arcs`, step 1's rule: same staff, next cell, abutting) and a written span is RIGHT when its start head lies within
REACH spaces (x) of the printed arc's left end and its stop head within REACH of its right end, on the same staff, with the truth's kind; `other kind` when the ends match and the kind
does not. Ends only (the hand truth names no head); a chord's member is not asked.
"""
import collections
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[2]))
sys.path.insert(0, str(HERE.parent))

import arcs as A  # noqa: E402
import score as S  # noqa: E402

SP = 32.0
REACH = 2.5


def boxes_p0(mini):
    out = {}
    for o in json.loads(pathlib.Path(mini).read_text())["observations"]:
        b = (o.get("detail") or {}).get("bbox_page_px")
        if b and o["subject"].startswith("glyph/0/"):
            out[o["subject"]] = [float(v) for v in b]
    return out


def score(work, arm, listing=False):
    xml = (pathlib.Path(work) / ("brahms.%s.musicxml" % arm)).read_text()
    boxes = boxes_p0(pathlib.Path(work) / ("brahms.%s.mini-record.json" % arm))
    spans = []
    for a in A.arcs_of_xml(xml):
        if not a["start"].startswith("glyph/0/") or a["start"] not in boxes or a["stop"] not in boxes:
            continue
        sa, sz = a["start"].split("/")[2:4], a["stop"].split("/")[2:4]
        if sa != sz:
            continue
        ba, bz = boxes[a["start"]], boxes[a["stop"]]
        spans.append((a["kind"], "/".join(sa), (ba[0] + ba[2]) / 2, (bz[0] + bz[2]) / 2, a))
    printed = S.printed_arcs(SP)
    used = set()
    res = {"tie": [0, 0, 0], "slur": [0, 0, 0]}          # printed arcs, bound right, ends right but the other kind
    rows = []
    for pa in printed:
        cls = pa["cls"][0] if len(pa["cls"]) == 1 else "slur"
        res[cls][0] += 1
        cell = pa["ids"][0]
        # staff of the group: from its hand boxes' cell ids
        st = None
        for b in json.load(open(S.TRUTH))["boxes"]:
            if b["id"] == pa["ids"][0]:
                c = b["cell_id"].split("-")
                st = "%s/%s" % (c[0][1:], c[1][2:])
        best = None
        for i, (k, s, ca, cz, a) in enumerate(spans):
            if s != st or i in used:
                continue
            if abs(ca - pa["x0"]) <= REACH * SP and abs(cz - pa["x1"]) <= REACH * SP:
                if best is None or k == cls:
                    best = (i, k)
        if best is not None:
            used.add(best[0])
            res[cls][1 if best[1] == cls else 2] += 1
            rows.append((cls, st, round(pa["x0"]), round(pa["x1"]), "right" if best[1] == cls else "other_kind", spans[best[0]][4]["start"], spans[best[0]][4]["stop"]))
        else:
            rows.append((cls, st, round(pa["x0"]), round(pa["x1"]), "none", None, None))
    nt = collections.Counter(spans[i][0] for i in range(len(spans)) if i not in used)
    w = collections.Counter(s[0] for s in spans)
    return res, nt, w, rows


if __name__ == "__main__":
    work = sys.argv[1]
    out = {}
    for arm in ("off", "on"):
        res, nt, w, rows = score(work, arm)
        out[arm] = rows
        print("%-4s " % arm + "  ".join("%ss: printed %d, bound right %d, other kind %d; written %d, matching no printed arc %d" % (k, res[k][0], res[k][1], res[k][2], w[k], nt[k])
                                           for k in ("tie", "slur")))
    # per printed arc: right in OFF and not in ON (a loss) / the reverse
    off = {(r[0], r[1], r[2], r[3]): r for r in out["off"]}
    on = {(r[0], r[1], r[2], r[3]): r for r in out["on"]}
    lost = [k for k in off if off[k][4] == "right" and on[k][4] != "right"]
    won = [k for k in off if off[k][4] != "right" and on[k][4] == "right"]
    print("printed arcs right in OFF and not in ON: %d | right in ON and not in OFF: %d" % (len(lost), len(won)))
    if "--list" in sys.argv:
        for k in lost:
            print("LOST", k, "OFF", off[k][5:], "ON", on[k][4], on[k][5:])
        for k in won:
            print("WON ", k, "OFF", off[k][4], "ON", on[k][5:])
