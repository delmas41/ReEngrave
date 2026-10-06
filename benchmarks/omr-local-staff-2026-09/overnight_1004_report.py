"""overnight 2026-10-04 re-gathers, step 2: reach, run-vs-run difference, in-sample truth check, out-of-sample
agreement. Reads only the small JSONs `overnight_1004_extract.py` wrote (and `overnight_1004_truth.py`'s).

  python3 overnight_1004_report.py <dir with the extracted JSONs> [--json out.json]

RUN 1 = 20261004-farhead (2.56 reader wired, no fixes); RUN 2 = 20261004-farhead-all (+ jut-from-ink + chord
split + through-head); BASE = 20261001 (the newest earlier whole-movement record: geometry only).
Heads in different records are matched by box overlap on the same page, never by glyph index.
"""
from __future__ import annotations
import collections, json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
from tools.omr.annotate import ledger_grid as lg

DOCS = ("beethoven5-litolff", "brahms1-breitkopf")
RUNS = (("RUN1", "20261004-farhead"), ("RUN2", "20261004-farhead-all"), ("BASE", "20261001"))
# pages the far-head rules were written / tuned on (the truth set's own pages, per the brief: Litolff p1-3, Brahms p0-1)
IN_SAMPLE_PAGES = {"beethoven5-litolff": {1, 2, 3}, "brahms1-breitkopf": {0, 1}}
IOU_MIN = 0.5


def page_of(s):
    return int(s.split("/")[1])


def iou(a, b):
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    i = ix * iy
    u = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i
    return i / u if u > 0 else 0.0


def geo_pos(g):
    gr = g.get("geo_rounded")
    if gr is None and g.get("geo") is not None:
        gr = int(round(float(g["geo"])))
    return None if gr is None else int(gr)


def is_far(g):
    if "fh" in g or "fh_abs" in g:
        return True
    p = geo_pos(g)
    return p is not None and lg.far_head_needs_ledger_read(p)


def decided_pos(g):
    """The position a run ends with for this head: the standing Q.NOTEHEAD_POSITION verdict where DECIDED; None
    where it ABSTAINED; the geometry position where the head was never a far head (no far-head question asked)."""
    np_ = g.get("np")
    if np_ is not None:
        return int(round(float(np_["value"]))) if np_["outcome"] == "decided" else None
    return geo_pos(g)


def load(d, doc, tag):
    return json.loads((Path(d) / f"{doc}-{tag}.json").read_text())


def best_match(box, page, cand):
    best, bi = None, 0.0
    for s, g in cand.get(page, []):
        v = iou(box, g["box"])
        if v > bi:
            best, bi = (s, g), v
    return (best, bi) if bi >= IOU_MIN else (None, bi)


def by_page(glyphs):
    out = collections.defaultdict(list)
    for s, g in glyphs.items():
        if "box" in g and "geo" in g:
            out[page_of(s)].append((s, g))
    return out


def reach(doc, tag, data):
    G = data["glyphs"]
    far = {s: g for s, g in G.items() if is_far(g) and "geo" in g}
    n_fh = sum(1 for g in far.values() if "fh" in g)
    n_abs = collections.Counter((g["fh_abs"]["reason"]) for g in far.values() if "fh_abs" in g)
    np_dec = sum(1 for g in far.values() if g.get("np", {}).get("outcome") == "decided")
    np_abs = collections.Counter(g["np"]["reason"] for g in far.values()
                                 if g.get("np", {}).get("outcome") == "abstained")
    no_np = sum(1 for g in far.values() if "np" not in g)
    pages = collections.defaultdict(lambda: collections.Counter())
    for s, g in far.items():
        p = page_of(s)
        if g.get("np", {}).get("outcome") == "decided":
            pages[p]["decided"] += 1
        elif "np" in g:
            pages[p][g["np"]["reason"]] += 1
        else:
            pages[p]["no_verdict"] += 1
    srcs = collections.Counter((g["fh"]["shape_source"] or "?").split(" n=")[0] for g in far.values() if "fh" in g)
    boxs = collections.Counter(g["fh"]["box_source"] for g in far.values() if "fh" in g)
    absr = collections.Counter(g["fh_abs"]["ledger_reason"] for g in far.values() if "fh_abs" in g)
    pool_pages = sorted({page_of(s) for s, g in far.items() if "fh" in g and (g["fh"]["shape_source"] or "").startswith("document pool")})
    own_pages = sorted({page_of(s) for s, g in far.items() if "fh" in g and (g["fh"]["shape_source"] or "").startswith("page")})
    return dict(abstention_ledger_reason=dict(absr), pages_read_with_pooled_shape=pool_pages,
                pages_read_with_own_shape=own_pages, far=len(far), far_head_row=n_fh, far_head_abstention=dict(n_abs), np_decided=np_dec,
                np_abstained=dict(np_abs), far_without_np_verdict=no_np,
                pages={p: dict(c) for p, c in sorted(pages.items())}, shape_source=dict(srcs),
                box_source=dict(boxs))


def main(d, out_json=None):
    truth = json.loads((Path(d) / "truth.json").read_text())
    summary = {}
    for doc in DOCS:
        data = {name: load(d, doc, tag) for name, tag in RUNS}
        for name in ("RUN1", "RUN2", "BASE"):
            print(f"\n=== {doc} {name} ({data[name]['src'].split('/')[-1]})")
            r = reach(doc, name, data[name])
            summary[(doc, name, "reach")] = r
            print(f" far heads (geometry outside the first space): {r['far']}")
            print(f" Q.FAR_HEAD_LEDGER_POSITION rows: {r['far_head_row']}  abstentions: {r['far_head_abstention']}")
            print(f" Q.NOTEHEAD_POSITION decided {r['np_decided']}  abstained {r['np_abstained']}  "
                  f"far heads with no verdict {r['far_without_np_verdict']}")
            print(f" why the far-head reader abstained: {r['abstention_ledger_reason']}")
            print(f" pages read with the pooled shape: {r['pages_read_with_pooled_shape']}; with the page's own: {r['pages_read_with_own_shape']}")
            print(f" shape source of the rows: {r['shape_source']}  box source: {r['box_source']}")
            print(" per page (decided / abstained-by-reason):", r["pages"])
            if r["np_decided"] == 0 and name != "BASE":
                print(" *** DEAD: zero decided ***")
        # ---------------- difference RUN1 vs RUN2
        c1, c2 = by_page(data["RUN1"]["glyphs"]), by_page(data["RUN2"]["glyphs"])
        same_subject = 0
        pairs, only1, only2 = [], 0, 0
        for s, g in data["RUN1"]["glyphs"].items():
            if not is_far(g) or "box" not in g:
                continue
            m, v = best_match(g["box"], page_of(s), c2)
            if m is None or not is_far(m[1]):
                only1 += 1
                continue
            same_subject += (m[0] == s)
            pairs.append((s, g, m[0], m[1]))
        seen2 = {p[2] for p in pairs}
        only2 = sum(1 for s, g in data["RUN2"]["glyphs"].items() if is_far(g) and "box" in g and s not in seen2)
        both_dec = [(a, ga, b, gb) for (a, ga, b, gb) in pairs if decided_pos(ga) is not None and decided_pos(gb) is not None]
        diff_val = [(a, b, decided_pos(ga), decided_pos(gb), ga, gb) for (a, ga, b, gb) in both_dec
                    if decided_pos(ga) != decided_pos(gb)]
        flip_a = [(a, b) for (a, ga, b, gb) in pairs if decided_pos(ga) is not None and decided_pos(gb) is None]
        flip_b = [(a, b) for (a, ga, b, gb) in pairs if decided_pos(ga) is None and decided_pos(gb) is not None]
        print(f"\n--- {doc}: RUN1 vs RUN2 far heads matched by box overlap: {len(pairs)} (same glyph id {same_subject}); "
              f"only in RUN1 {only1}, only in RUN2 {only2}")
        print(f"   both decided {len(both_dec)}; decided position DIFFERS on {len(diff_val)}; "
              f"decided->abstained {len(flip_a)}; abstained->decided {len(flip_b)}")
        by = collections.Counter(page_of(a) for (a, b, x, y, ga, gb) in diff_val)
        print("   differing heads by page:", dict(sorted(by.items())))
        for (a, b, x, y, ga, gb) in diff_val[:60]:
            print(f"     {a}: RUN1 {x} ({ga.get('fh', {}).get('box_source')}) -> RUN2 {y} ({gb.get('fh', {}).get('box_source')})"
                  f"  geometry {geo_pos(gb)}")
        summary[(doc, "diff")] = dict(pairs=len(pairs), same_id=same_subject, only1=only1, only2=only2,
                                      both_decided=len(both_dec), differ=len(diff_val),
                                      dec_to_abs=len(flip_a), abs_to_dec=len(flip_b),
                                      differ_list=[(a, b, x, y) for (a, b, x, y, ga, gb) in diff_val])
        # ---------------- in-sample truth check
        print(f"\n--- {doc}: IN-SAMPLE truth-set far heads (n={len(truth[doc])}) -- NOT out-of-sample")
        rows = []
        tal = {n: collections.Counter() for n in ("RUN1", "RUN2", "GEO_RUN2", "GEO_BASE")}
        unmatched = collections.Counter()
        cands = {n: by_page(data[n]["glyphs"]) for n in ("RUN1", "RUN2", "BASE")}
        for h in truth[doc]:
            t = set(h["truth"])
            row = dict(subject=h["subject"], truth=h["truth"])
            for n, key in (("RUN1", "RUN1"), ("RUN2", "RUN2"), ("BASE", "BASE")):
                m, v = best_match(h["box"], h["page"], cands[key])
                if m is None:
                    row[n] = ("unmatched", None, None)
                    unmatched[n] += 1
                    continue
                g = m[1]
                dp = decided_pos(g)
                gp = geo_pos(g)
                row[n] = (m[0], dp, gp)
            for n in ("RUN1", "RUN2"):
                sid, dp, gp = row[n]
                tal[n]["unmatched" if sid == "unmatched" else ("undecided" if dp is None else ("right" if dp in t else "wrong"))] += 1
            for n, key in (("GEO_RUN2", "RUN2"), ("GEO_BASE", "BASE")):
                sid, dp, gp = row[key]
                tal[n]["unmatched" if sid == "unmatched" else ("right" if gp in t else "wrong")] += 1
            rows.append(row)
        for n, c in tal.items():
            print(f"   {n:9s} right {c['right']:3d} wrong {c['wrong']:3d} undecided {c['undecided']:3d} unmatched {c['unmatched']:3d}")
        changed = [r for r in rows if r["RUN1"][1] != r["RUN2"][1]]
        for r in changed:
            t = set(r["truth"])
            print(f"     RUN1->RUN2 changes: {r['subject']} truth {r['truth']} RUN1 {r['RUN1'][1]} RUN2 {r['RUN2'][1]} geometry {r['RUN2'][2]}")
        wrong2 = [r for r in rows if r["RUN2"][1] is not None and r["RUN2"][1] not in set(r["truth"])]
        und2 = [r for r in rows if r["RUN2"][1] is None]
        print("   RUN2 wrong:", [(r["subject"], r["truth"], r["RUN2"][1], r["RUN2"][2]) for r in wrong2])
        print("   RUN2 undecided:", [(r["subject"], r["truth"], r["RUN2"][2]) for r in und2])
        summary[(doc, "insample")] = dict(tally={n: dict(c) for n, c in tal.items()}, rows=rows)
        # ---------------- out-of-sample agreement
        ins = IN_SAMPLE_PAGES[doc]
        print(f"\n--- {doc}: OUT-OF-SAMPLE far heads (pages not in {sorted(ins)}). Agreement with geometry is NOT accuracy.")
        for n in ("RUN1", "RUN2"):
            far = {s: g for s, g in data[n]["glyphs"].items() if is_far(g) and "geo" in g and page_of(s) not in ins}
            agree = dis = ab = 0
            reasons = collections.Counter()
            for s, g in far.items():
                dp = decided_pos(g)
                if dp is None:
                    ab += 1
                    reasons[g.get("np", {}).get("reason")] += 1
                elif dp == geo_pos(g):
                    agree += 1
                else:
                    dis += 1
            print(f"   {n}: far heads {len(far)}  decided & agree with geometry {agree}  decided & DISAGREE {dis}  abstained {ab} {dict(reasons)}")
            summary[(doc, n, "oos")] = dict(far=len(far), agree=agree, disagree=dis, abstained=ab)
    if out_json:
        Path(out_json).write_text(json.dumps({"|".join(k) if isinstance(k, tuple) else k: v for k, v in summary.items()}, default=str))


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[0], a[a.index("--json") + 1] if "--json" in a else None)
