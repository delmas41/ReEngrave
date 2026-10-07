"""night 2026-10-07 read, step 3: NEW (20261007-night) vs BASE (20261006-night-combined), numbers first.

Reuses `night_1006_report` for the far-head block (reach, Sean's through-or-edge rule on the reader's rows and on the
reader-independent grid rows, truth set, whole-record sanity) with the two tags swapped, and adds what 10-07 changed:
in-staff head position changes, whole-record owner changes, the summary-count diff, mark groups (marks detected 2+
times).  Reads only small JSONs (`night_1007_extract.py`, `night_1006_replay.py`, `overnight_1004_truth.py`).

  python3 night_1007_report.py <dir holding x/> [--docs a,b]
"""
from __future__ import annotations
import collections, json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import night_1006_report as R6
import overnight_1004_report as R

R6.NEWTAG, R6.BASETAG = "20261007-night", "20261006-night-combined"
IOU_CLUSTER = 0.3


def pct(a, b):
    return f"{a}/{b} ({100.0 * a / b:.1f}%)" if b else f"{a}/0"


def head_changes(N, B):
    """In-staff (not a far head in EITHER run) heads matched by box: geometry rounded position, NEW vs BASE."""
    bb = R.by_page(B["glyphs"])
    far_n = R6.far_set(N)
    hist = collections.Counter()
    n = same = 0
    far_hist = collections.Counter()
    for s, g in N["glyphs"].items():
        if "box" not in g or "geo" not in g:
            continue
        m, v = R.best_match(g["box"], R.page_of(s), bb)
        if not m:
            continue
        gp, bp = R.geo_pos(g), R.geo_pos(m[1])
        isfar = (s in far_n) or R.is_far(m[1])
        d = gp - bp
        if isfar:
            far_hist[d] += 1
            continue
        n += 1
        if d == 0:
            same += 1
        else:
            hist[d] += 1
    return dict(matched_in_staff=n, same=same, changed=n - same, delta_steps=dict(sorted(hist.items())),
                far_matched=sum(far_hist.values()), far_changed=sum(v for k, v in far_hist.items() if k),
                far_delta_steps=dict(sorted(far_hist.items())))


def owner_changes(N, B):
    bb = R.by_page(B["glyphs"])
    c = collections.Counter()
    to = collections.Counter()
    unmatched = 0
    for s, g in N["glyphs"].items():
        o = g.get("own")
        if not o or "box" not in g:
            continue
        m, v = R.best_match(g["box"], R.page_of(s), bb)
        if not m:
            unmatched += 1
            continue
        bo = m[1].get("own")
        if not bo:
            c["BASE no verdict"] += 1
            continue
        if (o["outcome"], o["value"]) == (bo["outcome"], bo["value"]):
            c["same"] += 1
            continue
        if o["outcome"] == "decided" and bo["outcome"] == "decided":
            if o["value"] == "staff/" + "/".join(s.split("/")[1:4]):
                c["decided -> decided: now on filing staff"] += 1
            else:
                c["decided -> decided: other staff"] += 1
        elif o["outcome"] == "decided":
            c["abstained -> decided"] += 1
        else:
            c["decided -> abstained"] += 1
        to[o.get("reason")] += 1
    return dict(counts=dict(c), unmatched=unmatched, reason_of_new_verdict_where_changed=dict(to.most_common(8)))


def summary_diff(N, B):
    out = {}
    for q in sorted(set(N["summary"]) | set(B["summary"])):
        n, b = N["summary"].get(q, {}), B["summary"].get(q, {})
        if n != b:
            out[q] = {k: (b.get(k, 0), n.get(k, 0)) for k in sorted(set(n) | set(b))}
    big = {}
    for q, d in out.items():
        for k, (b, n) in d.items():
            if (b == 0 and n > 50) or (b and abs(n - b) / b > 0.02 and abs(n - b) > 20):
                big[f"{q}.{k}"] = (b, n)
    return dict(all=out, over_2pct=big)


def clusters(boxes, prefix="notehead"):
    """Connected components of same-page same-system boxes of one family under IoU > 0.3 (gather's own rule)."""
    items = [(s, b) for s, c, b in boxes if str(c).startswith(prefix)]
    by = collections.defaultdict(list)
    for s, b in items:
        by[tuple(s.split("/")[1:3])].append((s, b))
    sizes = []
    for key, L in by.items():
        par = list(range(len(L)))

        def f(i):
            while par[i] != i:
                par[i] = par[par[i]]
                i = par[i]
            return i
        for i in range(len(L)):
            for j in range(i + 1, len(L)):
                if R.iou(L[i][1], L[j][1]) > IOU_CLUSTER:
                    par[f(i)] = f(j)
        cnt = collections.Counter(f(i) for i in range(len(L)))
        sizes += list(cnt.values())
    c = collections.Counter(sizes)
    return dict(boxes=len(items), marks=len(sizes), marks_with_2plus=sum(v for k, v in c.items() if k >= 2),
                extra_boxes=sum((k - 1) * v for k, v in c.items()), size_hist=dict(sorted(c.items())))


def groups_from_rows(N):
    """NEW's own `Q.MARK_GROUP` rows, family taken from the box's class (the extract keeps the group id, not the family)."""
    cls = {s: str(c) for s, c, b in N["boxes"]}
    by = collections.defaultdict(list)
    for s, (gid, cat) in N["mark_group"].items():
        c = cls.get(s, "?")
        fam = "notehead" if c.startswith("notehead") else ("rest" if c.startswith("rest") else
              ("accidental" if c.startswith("accidental") else "other"))
        by[gid].append(fam)
    cats = collections.defaultdict(lambda: collections.Counter())
    for gid, L in by.items():
        cats[L[0]]["marks"] += 1
        if len(L) >= 2:
            cats[L[0]]["marks_with_2plus"] += 1
            cats[L[0]]["extra_members"] += len(L) - 1
    return {k: dict(v) for k, v in cats.items()}


def main(d, docs):
    d = Path(d)
    R6.main(d, str(d / "report_far.json"), docs=docs)
    print("\n" + "=" * 100)
    summ = {}
    for doc in docs:
        N = json.loads((d / "x" / f"{doc}-{R6.NEWTAG}.json").read_text())
        B = json.loads((d / "x" / f"{doc}-{R6.BASETAG}.json").read_text())
        s = {}
        print(f"{doc}")
        s["head_changes"] = head_changes(N, B)
        print("  in-staff heads, geometry position NEW vs BASE:", s["head_changes"])
        s["owner_changes"] = owner_changes(N, B)
        print("  owner verdicts NEW vs BASE (matched by box):", s["owner_changes"])
        s["summary_diff"] = summary_diff(N, B)
        print("  summary counts that moved >2% (BASE, NEW):", s["summary_diff"]["over_2pct"])
        s["clusters_new"] = clusters(N["boxes"])
        s["clusters_base"] = clusters(B["boxes"])
        s["rows_new"] = groups_from_rows(N)
        print("  noteheads detected 2+ times, clustered off boxes: NEW", {k: v for k, v in s["clusters_new"].items()},
              "\n     BASE", s["clusters_base"], "\n     NEW's own mark_group rows (control)", s["rows_new"])
        summ[doc] = s
    (d / "report_extra.json").write_text(json.dumps(summ, indent=1, default=str))


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[0], tuple(a[a.index("--docs") + 1].split(",")) if "--docs" in a else R.DOCS)
