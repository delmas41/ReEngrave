"""shared loaders for the 2.274 r3 census (Brahms p0). No pipeline code changed."""
import json
import pathlib
import sys
import xml.etree.ElementTree as ET

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PI = ROOT / "benchmarks/omr-arc-binding-2026-10/page-ink-2026-11"
sys.path[:0] = [str(PI), str(PI / "step2"), str(ROOT)]
import score as S      # noqa: E402
import arcs as A       # noqa: E402,F401

SP = 32.0
REACH = 2.5
WORK = HERE / "work"


def staff_of_hand(cell_id):
    c = cell_id.split("-")
    return "%s/%s" % (c[0][1:], c[1][2:])


def printed():
    truth = json.load(open(S.TRUTH))
    byid = {b["id"]: b for b in truth["boxes"]}
    out = S.printed_arcs(SP)
    for p in out:
        p["staff"] = staff_of_hand(byid[p["ids"][0]]["cell_id"])
        p["kind"] = p["cls"][0] if len(p["cls"]) == 1 else "slur"
    out.sort(key=lambda p: (int(p["staff"].split("/")[0]), int(p["staff"].split("/")[1]), p["x0"]))
    for k, p in enumerate(out):
        p["n"] = k
    heads = [dict(rect=b["rect"], staff=staff_of_hand(b["cell_id"]), cls=b["cls"]) for b in truth["boxes"] if b["cls"].startswith("notehead")]
    return out, heads


def record(arm):
    return json.load(open(WORK / ("%s.record.json" % arm)))


def inside(px, py, rects, g):
    return any(r[0] - g <= px <= r[2] + g and r[1] - g <= py <= r[3] + g for r in rects)


def covered(spans, x0, x1):
    return S.covered(spans, x0, x1)


def xml_notes(arm):
    """rg keys of the notes the file writes"""
    root = ET.fromstring((WORK / ("%s.musicxml" % arm)).read_text())
    return {el.get("rg") for el in root.iter("note") if el.get("rg")}


def marks():
    """printed arcs merged into MARKS: one printed mark is counted once however Sean's per-cell boxes were labelled.
    * a printed arc whose hand label sits in the neighbouring staff's cell pad (cell staff != the staff the arc is nearest) is not joined by score.printed_arcs (same-staff rule): join
      any two printed arcs of one system whose facing edges meet within 1.5 sp and whose y bands overlap (`half`);
    * two labels over one mark (|dx0|, |dx1| <= 40 px, y bands overlap): `dup`.
    Returns (marks, heads); each mark has members (printed arc numbers of printed()), x0/x1/box/rects/ids/kind/staff and the relations used."""
    pa, heads = printed()
    n = len(pa)
    par = list(range(n))

    def find(i):
        while par[i] != i:
            par[i] = par[par[i]]
            i = par[i]
        return i
    rel = {}
    cand = {}
    for i in range(n):
        a = pa[i]
        for j in range(i + 1, n):
            b = pa[j]
            if a["staff"].split("/")[0] != b["staff"].split("/")[0]:
                continue
            ya, yb = a["box"], b["box"]
            yov = min(ya[3], yb[3]) - max(ya[1], yb[1])
            if abs(a["x0"] - b["x0"]) <= 40 and abs(a["x1"] - b["x1"]) <= 40 and yov >= 0 and (a["x1"] - a["x0"]) < 35 * SP:
                par[find(i)] = find(j)
                rel[(i, j)] = "dup"
            elif a["staff"] != b["staff"]:
                for l, r in ((a, b), (b, a)):
                    h = min(ya[3] - ya[1], yb[3] - yb[1])
                    if abs(r["x0"] - l["x1"]) <= 1.5 * SP and yov >= 0.5 * h:
                        cand.setdefault(("R", id(l)), []).append((i, j))
                        cand.setdefault(("L", id(r)), []).append((i, j))
    for k, v in cand.items():
        pass
    for (side, _), v in list(cand.items()):
        pass
    seen = set()
    for (i, j) in {pr for v in cand.values() for pr in v}:
        # one-to-one: neither arc has a second candidate on the facing side
        ok = all(len(v) == 1 for k, v in cand.items() if (i, j) in v)
        sizes = [sum(1 for t in range(n) if find(t) == find(x)) for x in (i, j)]
        if ok and sizes == [1, 1]:
            par[find(i)] = find(j)
            rel[(i, j)] = "half"
    comp = {}
    for i in range(n):
        comp.setdefault(find(i), []).append(i)
    out = []
    for mem in comp.values():
        ps = [pa[i] for i in mem]
        rects = [r for p in ps for r in p["rects"]]
        m = dict(members=sorted(mem), ids=[i for p in ps for i in p["ids"]], rects=rects, x0=min(p["x0"] for p in ps), x1=max(p["x1"] for p in ps),
                 cls=sorted({c for p in ps for c in p["cls"]}), staff=ps[0]["staff"], kind=ps[0]["kind"], kinds=sorted({p["kind"] for p in ps}),
                 box=[min(r[0] for r in rects), min(r[1] for r in rects), max(r[2] for r in rects), max(r[3] for r in rects)],
                 rel=sorted({v for (i, j), v in rel.items() if i in mem}))
        out.append(m)
    out.sort(key=lambda m: (int(m["staff"].split("/")[0]), int(m["staff"].split("/")[1]), m["x0"]))
    for k, m in enumerate(out):
        m["n"] = k
    return out, heads, pa
