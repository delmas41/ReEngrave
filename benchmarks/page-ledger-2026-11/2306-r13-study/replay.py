"""2.306 r13 study: NEW (`page_stems.read`) re-run offline from the saved gather's own rows, so its path to each answer can be traced.
Inputs rebuilt from the record: page heads (oval, else strongest box), the page map's strokes with their contacts, and the strokes other claims
hold (page-stroke claims; READ area claims by the register's predicate; boxed accidentals by BOX share -- the gather used the ink mask, the one
approximation here). `check()` says for how many heads the replay gives the gathered answer; only those are traced.
Usage (cwd = repo root): replay.py lit|bra"""
import sys, os, collections
sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
from tools.omr.staged import page_stems as PS
from tools.omr.staged import page_claim_names as PCN
from tools.omr.staged import stroke_owner as SO


def inputs(D, p):
    ps = D["pstrokes"][p]
    n = max(ps) + 1
    boxes = [tuple(ps[i]["box"]) if i in ps else (0, 0, 0, 0) for i in range(n)]
    kinds = [ps[i]["kind"] if i in ps else "" for i in range(n)]
    verticals = [dict(ord=i, box=boxes[i], sp=float(ps[i]["sp"] or 16.0)) for i in range(n) if kinds[i] == "vertical"]
    held = {}
    for c in D["claims"][p]:
        if c.get("page_strokes") and (c.get("standing") or "READ") == "READ" and c.get("source") != "page_stems" and c.get("owner") not in ("head", "stem"):
            for i in c["page_strokes"]:
                held.setdefault(int(i), str(c.get("owner") or "?"))
    index = PCN.StrokeIndex(boxes, kinds)
    for c in D["claims"][p]:
        v = c["value"]
        if c.get("unit") != "area" or (c.get("standing") or "READ") != "READ" or c.get("owner") not in SO.AREA_OWNERS or not (isinstance(v, (list, tuple)) and len(v) == 4):
            continue
        for i in PCN.area_names(index, v, c.get("scope") == "system" and c.get("cell") is None, c.get("owner")):
            held.setdefault(int(i), c["owner"])
    for ab in D["accs"].get(p, ()):
        for i in index.meeting(ab):
            b = boxes[i]
            a = max(1.0, (b[2] - b[0]) * (b[3] - b[1]))
            inter = max(0.0, min(b[2], ab[2]) - max(b[0], ab[0])) * max(0.0, min(b[3], ab[3]) - max(b[1], ab[1]))
            if kinds[i] != "barline" and inter / a >= 0.5:
                held.setdefault(int(i), "accidental")
    crossers = []
    for i in range(n):
        if kinds[i] in ("vertical", "") or i not in ps:
            continue
        kind = "slash" if held.get(i) == "tremolo" else ("beam" if kinds[i] == "horizontal" and float(ps[i]["thick"] or 0) >= 0.4 else kinds[i])
        if kinds[i] == "barline":
            continue
        crossers.append(dict(ord=i, box=boxes[i], kind=kind))
    strokes = {i: dict(box=boxes[i], kind=kinds[i], touches=[(int(j), float(c)) for j, c in ps[i]["touches"]]) for i in ps if kinds[i] != "barline"}
    # page heads: one per gathered head id; members from the page mark
    by_head = collections.defaultdict(set)
    for g, r in D["pstem"].items():
        if pg(g) == p and r.get("head") is not None:
            by_head[int(r["head"])].add(g)
    oval, hstrokes = {}, {}
    for ph in D["pheads"].get(p, ()):
        for m in ph["members"]:
            if ph.get("oval"):
                oval[m] = tuple(ph["oval"])
            hstrokes[m] = ph.get("strokes") or []
    heads = []
    for hid, gs in sorted(by_head.items()):
        mem = set(gs)
        for g in gs:
            mem |= set((D["pmark"].get(g) or {}).get("members") or ())
        mem = sorted(m for m in mem if m in D["heads"])
        ov = next((oval[m] for m in mem if m in oval), None)
        rep = max(mem, key=lambda m: float(D["heads"][m].get("score") or 0.0))
        box = ov or tuple(D["heads"][rep]["box"])
        st = next((hstrokes[m] for m in mem if m in hstrokes), [])
        heads.append(dict(id=hid, members=mem, box=tuple(float(v) for v in box), sp=staff_sp(D, rep), ink=ov is not None, strokes=list(st)))
    return heads, verticals, held, crossers, strokes


def run(D, p):
    heads, verticals, held, crossers, strokes = inputs(D, p)
    res = PS.read(heads, verticals, held, crossers=crossers, strokes=strokes)
    return dict(heads=heads, verticals=verticals, held=held, crossers=crossers, strokes=strokes, res=res)


def check(D):
    tot = same = 0
    diff = collections.Counter()
    out = {}
    for p in D["pages"]:
        R = run(D, p)
        out[p] = R
        gh = {}
        for h in R["heads"]:
            for m in h["members"]:
                gh[m] = h["id"]
        R["head_of"] = gh
        for g, rec in D["pstem"].items():
            if pg(g) != p or rec.get("head") is None:
                continue
            r = R["res"]["heads"].get(int(rec["head"]))
            if r is None:
                continue
            tot += 1
            if r["how"] == rec["how"] and r.get("stroke") == rec.get("page_stroke") and r.get("direction") == rec.get("direction"):
                same += 1
            else:
                diff[(rec["how"], r["how"])] += 1
    return out, tot, same, diff


if __name__ == "__main__":
    D = load(sys.argv[1])
    out, tot, same, diff = check(D)
    print(sys.argv[1], "glyph readings", tot, "replay gives the gathered answer", same, "(%.1f%%)" % (100.0 * same / max(1, tot)))
    print(" differing (gathered -> replay):", diff.most_common(12))
