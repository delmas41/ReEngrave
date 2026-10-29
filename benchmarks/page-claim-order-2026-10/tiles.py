"""ROADMAP 2.221 milestone 0/0b, second half: the refusal cross-tab and the blind tiles. Read-only; run after census.py count.

    python3 benchmarks/page-claim-order-2026-10/tiles.py crosstab   # which OLD rule already refuses the boxes the census finds
    python3 benchmarks/page-claim-order-2026-10/tiles.py tiles      # 12 blind tiles -> out/print/2.221-census/
"""
from __future__ import annotations

import collections
import json
import pathlib
import pickle
import random
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))
import census as C                          # noqa: E402
from tools.omr.staged import lane_report as LR   # noqa: E402

SEED = 2221
PRINT = C.PRINT_DIR


def load():
    pool = json.loads(C.POOL_JSON.read_text())
    data = pickle.loads(C.CACHE.read_bytes())
    return pool, data


def reasons(data):
    out = {}
    for plate, D in data.items():
        out[plate] = {v["subject"]: ("%s|%s" % (v["value"], v["reason"])) for v in D["verdicts"]["notehead_is_not_a_notehead"]}
    return out


def crosstab():
    pool, data = load()
    R = reasons(data)
    tab = collections.defaultdict(collections.Counter)
    for it in pool["pool"]:
        if it["pop"] != "boxes" or it["share"] < 0.5:
            continue
        tab[(it["plate"], it["group"])][R[it["plate"]].get(it["key"], "?")] += 1
    out = {"%s %s" % k: dict(v.most_common()) for k, v in sorted(tab.items())}
    (HERE / "crosstab.json").write_text(json.dumps(out, indent=1))
    for k, v in out.items():
        print(k, v)
    # 0b pair detail
    for plate, prs in pool["pairs"].items():
        c = collections.Counter((p["kind"], p["other_live"], p["shared_px"] > 0) for p in prs)
        print(plate, "0b (kind, other_live, shares_ink):", dict(c))
        for kind in ("accidental", "rest", "dot"):
            live = sorted(p["shared_px"] / max(1, p["head_ink"]) for p in prs if p["kind"] == kind and p["other_live"])
            if live:
                print("   ", kind, "live: shared/head_ink quantiles", [round(live[int(q * (len(live) - 1))], 3) for q in (0, .25, .5, .75, 1)])


def tiles():
    pool, data = load()
    rng = random.Random(SEED)
    items = []

    def take(cands, n, tag, mk):
        cands = list(cands)
        rng.shuffle(cands)
        got = []
        for c in cands:
            it = mk(c, tag)
            if any(LR._same_ink(it, x) for x in items + got):
                continue
            got.append(it)
            if len(got) >= n:
                break
        items.extend(got)
        return len(got)

    def head_item(c, tag):
        return dict(plate=c["plate"], page=c["page"], box=c["box"], rg=c["key"], group=c["group"], share=c["share"],
                    n_hosts=c.get("n_hosts"), role="case", side=tag)

    P = pool["pool"]
    got = {}
    got["b_dynamic_written_ge0.5"] = take([c for c in P if c["group"] == "b_dynamic" and c["pop"] == "written" and c["share"] >= 0.5], 5, "b_dynamic", head_item)
    got["b_word_written_ge0.5"] = take([c for c in P if c["group"] == "b_word" and c["pop"] == "written" and c["share"] >= 0.5], 1, "b_word", head_item)
    got["a_barline_written_ge0.5"] = take([c for c in P if c["group"] == "a_barline" and c["pop"] == "written" and c["share"] >= 0.5], 2, "a_barline", head_item)

    def pair_item(p, tag):
        hb, ob = p["head_box"], p["other_box"]
        return dict(plate=p["plate"], page=p["page"], box=[min(hb[0], ob[0]), min(hb[1], ob[1]), max(hb[2], ob[2]), max(hb[3], ob[3])],
                    rg=p["head"], other=p["other"], other_cls=p["other_cls"], head_box=hb, other_box=ob,
                    shared_px=p["shared_px"], head_ink=p["head_ink"], role="case", side=tag, group="0b_" + p["kind"])

    pairs = [dict(p) for prs in pool["pairs"].values() for p in prs]
    ok = [p for p in pairs if p["shared_px"] >= 0.10 * max(1, p["head_ink"])]
    got["0b_accidental"] = take([p for p in ok if p["kind"] == "accidental"], 2, "0b", pair_item)
    got["0b_rest_live"] = take([p for p in ok if p["kind"] == "rest" and p["other_live"]], 1, "0b", pair_item)
    got["0b_dot_live"] = take([p for p in pairs if p["kind"] == "dot" and p["other_live"] and p["shared_px"] > 0], 1, "0b", pair_item)
    print("tiles drawn per source:", got, "total", len(items))
    rng.shuffle(items)
    PRINT.mkdir(parents=True, exist_ok=True)
    r = LR.cut_tiles(items, PRINT)
    print(r)
    (PRINT / "tiles" / "README.md").write_text(
        "# 2.221 census tiles (read-only; nothing about any change)\n\n"
        "Each picture is a piece of a scanned score page with ONE orange box on it and nothing else drawn.\n\n"
        "**What the orange box means.** It is a place where our reader WROTE a note into the file (or, on a few tiles, "
        "a note together with an accidental, rest or dot that the detector boxed next to it; the box then holds both). "
        "It says nothing about whether we were right.\n\n"
        "**Question, for every tile:** what is inside the orange box? Is it a real note head, or is it part of "
        "something else (a letter of a dynamic or word, a barline, a bracket, part of a sharp or rest)? "
        "If a note and something else share the ink, which one owns the shared ink?\n\n"
        "Answer by tile number. Our key is in `../key.json`, outside this folder, and is not for the reader.\n")
    print("wrote", PRINT)


if __name__ == "__main__":
    {"crosstab": crosstab, "tiles": tiles}[sys.argv[1]]()
