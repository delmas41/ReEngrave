"""2.305 r9 -- every WRONG and UNREAD tie / slur on Sean's swept Brahms p0 cells, one line each, with the path that wrote it (replay.py's spans).

    PYTHONPATH=.:benchmarks/note-loss-funnel-2026-11 python3 benchmarks/arcs-combined-2026-11/r9/tally.py OUTPREFIX [--json OUT]

The matching is judge.py's own (same `near`, same order), repeated here only to keep the per-arc detail judge.py counts and drops:
for an UNREAD arc of his, the written arcs that share ONE end with it (a wrong end); for a WRONG written arc, which of his arcs shares one end.
Reads only.
"""
from __future__ import annotations

import collections
import json
import sys

import judge as J


def main():
    pre = sys.argv[1]
    facts = json.load(open(pre + ".facts.json"))
    sp = json.load(open(pre + ".spans.json"))
    # a chord member's mark is written on the chord's notes as MusicXML groups them: key every end by its written chord
    chord_of, head = {}, None
    for h in facts["written"]:
        if h.get("kind") != "note":
            continue
        if not h.get("chord"):
            head = h["rg"]
        chord_of[h["rg"]] = head if h.get("chord") else h["rg"]
    members = collections.defaultdict(set)
    for rg, c in chord_of.items():
        members[c].add(rg)
    ck = lambda rg: chord_of.get(rg, rg)   # noqa: E731
    src_exact = collections.defaultdict(list)
    src_chord = collections.defaultdict(list)
    for s in sp["spans"]:
        src_exact[frozenset((s["a"], s["b"]))].append(s["src"])
        src_chord[frozenset((ck(s["a"]), ck(s["b"])))].append(s["src"])

    class _Src(dict):
        def get(self, key, default=None):
            if key in src_exact:
                return src_exact[key]
            a, b = tuple(key) if len(key) == 2 else (next(iter(key)), next(iter(key)))
            v = src_chord.get(frozenset((ck(a), ck(b))))
            return [x + "~chord" for x in v] if v else default
    src_of = _Src()
    page, truth, u, in_scope, swept = J.load_truth(J.TRUTH)
    glyphs = facts["glyphs"]
    pp = json.load(open(J.ARCS))
    tarcs = [x for x in pp["labels"] if x["kind"] == "arc" and x["state"] == "confirmed"]
    gb = lambda rg: (glyphs.get(rg) or {}).get("box") if rg else None   # noqa: E731
    warcs = J.xml_arcs(facts["xml"], gb)
    tol = 2.0 * u

    def near(box, x, y0, y1):
        return box is not None and abs(J.cx(box) - x) <= tol and y0 - 3 * u <= J.cy(box) <= y1 + 3 * u
    rows = []
    used_w = set()
    for ta in tarcs:
        r = ta["shape"]["rect"]
        if not (in_scope([r[0], r[1], r[0] + 1, r[3]]) and in_scope([r[2] - 1, r[1], r[2], r[3]])):
            continue
        kind = ta.get("sub")
        hit, one_end = None, []
        for n, (k, a, b, ba, bb) in enumerate(warcs):
            ends = (near(ba, r[0], r[1], r[3]), near(bb, r[2], r[1], r[3]))
            if (ends[0] and ends[1]) or (ends[0] and bb is None) or (ends[1] and ba is None):
                if hit is None or k == kind:
                    hit = (n, k)
            elif ends[0] or ends[1]:
                one_end.append(dict(n=n, k=k, a=a, b=b, good_end="start" if ends[0] else "stop",
                                    src=src_of.get(frozenset((a, b)))))
        if hit is None:
            rows.append(dict(who="his", id=ta["id"], kind=kind, verdict="unread", rect=r, one_end=one_end))
        else:
            used_w.add(hit[0])
            k, a, b = warcs[hit[0]][:3]
            rows.append(dict(who="his", id=ta["id"], kind=kind, verdict="right" if hit[1] == kind else "wrong",
                             written=dict(k=k, a=a, b=b, src=src_of.get(frozenset((a, b)))), rect=r))
    for n, (k, a, b, ba, bb) in enumerate(warcs):
        if n in used_w or ba is None or bb is None or not (in_scope(ba) and in_scope(bb)):
            continue
        if (glyphs.get(a) or {}).get("page") != 0:
            continue
        twin = any(m in used_w and {warcs[m][1], warcs[m][2]} == {a, b} for m in range(len(warcs)))
        twin = twin or any(m != n and {warcs[m][1], warcs[m][2]} == {a, b} for m in range(n))
        shares = []
        for ta in tarcs:
            r = ta["shape"]["rect"]
            e = (near(ba, r[0], r[1], r[3]) or near(bb, r[0], r[1], r[3]), near(bb, r[2], r[1], r[3]) or near(ba, r[2], r[1], r[3]))
            if e[0] or e[1]:
                shares.append(ta["id"])
        rows.append(dict(who="ours", kind=k, verdict="wrong", why="double" if twin else "no_arc_of_his", a=a, b=b,
                         box_a=ba, box_b=bb, src=src_of.get(frozenset((a, b))), shares_end_with=shares))
    n = collections.Counter((r["kind"], r["verdict"]) for r in rows)
    print("counts:", {"%s %s" % k: v for k, v in sorted(n.items())})
    by_src = collections.Counter()
    for r in rows:
        if r["verdict"] in ("right", "wrong"):
            s = (r.get("written") or {}).get("src") if r["who"] == "his" else r.get("src")
            by_src[(r["kind"], r["verdict"], "+".join(sorted({x.replace("~chord", "") for x in (s or ["?"])})))] += 1
    print("written verdicts by path:", {"%s %s %s" % k: v for k, v in sorted(by_src.items())})
    for r in rows:
        if r["verdict"] == "right":
            continue
        if r["who"] == "his":
            print("HIS %-4s %-6s %-5s %s" % (r["kind"], r["verdict"], r["id"],
                  ("written %s" % r.get("written")) if r.get("written") else ("one end written by: %s" % [(o["k"], o["a"], o["b"], o["good_end"], o["src"]) for o in r["one_end"]])))
        else:
            print("OURS %-4s wrong %-13s %s -> %s src=%s shares_end_with=%s" % (r["kind"], r["why"], r["a"], r["b"], r["src"], r["shares_end_with"]))
    if "--json" in sys.argv:
        json.dump(rows, open(sys.argv[sys.argv.index("--json") + 1], "w"), default=str, indent=0)


if __name__ == "__main__":
    main()
