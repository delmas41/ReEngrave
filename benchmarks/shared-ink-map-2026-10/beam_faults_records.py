"""ROADMAP 2.202b (read-only, no gather): the measures behind faults 2 (a fused double beam) and 3 (a beam that ends short of its stem), from the
gathered 2.202 ON records, and the re-settle of the narrowed heads under the new code.
usage: beam_faults_records.py REPORT_OUT_DIR LIVE_DIR OUT.json [--gaps|--settle]
 REPORT_OUT_DIR = the milestone lane_report dir (work/<plate>.on.{mini-record,gathered.record}.json); LIVE_DIR = beam_faults_live.py output (<plate>.json)."""
import collections, json, pathlib, sys
import ijson
sys.path.insert(0, ".")
sys.path.insert(0, "benchmarks/shared-ink-map-2026-10")
from tools.omr.staged import beam_strokes as BS
import beams_cause as BC

BASE = 375000


def load_views(path):
    """{cell key 'p/s/t/c': [StrokeView ...]} for every cell of a gathered record (stroke rows only), plus {cell: [beam glyph boxes]}."""
    rows = collections.defaultdict(list)
    with open(path, "rb") as f:
        for o in ijson.items(f, "record.observations.item", use_float=True):
            s = o["subject"]
            if s.startswith("glyph/") and o["quantity"] == "stroke":
                rows["/".join(s.split("/")[1:5])].append(o)
    return {c: BC.views_of(r) for c, r in rows.items()}


def gap_px(a, b):
    ax0, ay0, aw, ah = a; bx0, by0, bw, bh = b
    dx = max(0.0, max(ax0, bx0) - min(ax0 + aw, bx0 + bw)); dy = max(0.0, max(ay0, by0) - min(ay0 + ah, by0 + bh))
    return (dx * dx + dy * dy) ** 0.5


def main():
    rep = pathlib.Path(sys.argv[1]); out = {}
    for plate in ("litolff", "brahms"):
        views = load_views(rep / "work" / ("%s.on.gathered.record.json" % plate))
        # fused: thickness of role-beam strokes (>= 2 stems) in 0.1 sp bins from 0.6
        th = collections.Counter(); pairs = collections.Counter(); ex = []
        for c, vs in views.items():
            role = BS.roles(vs); by = {v.ordinal: v for v in vs}
            for v in vs:
                r = role[v.ordinal]
                if r["role"] in ("beam", "span_thin") and v.kind == "horizontal" and r.get("stems", 0) >= 2:
                    th["%.1f" % (int(v.thickness * 10) / 10.0)] += 1
                # join: a beam-role stroke and a stem it does not touch, gap in staff spaces
                if r["role"] == "beam":
                    for s in vs:
                        if s.kind == "vertical" and s.length <= BS.STEM_MAX_SPACES and s.ordinal not in r["stem_ordinals"]:
                            g = gap_px(v.box, s.box) / max(1.0, v.space_px)
                            if g <= 1.5:
                                pairs["%.2f" % (int(g * 10) / 10.0)] += 1
        out[plate] = dict(thickness_hist=dict(sorted(th.items())), nontouching_beam_stem_gap_hist=dict(sorted(pairs.items())))
        print(plate, json.dumps(out[plate]), flush=True)
    json.dump(out, open(sys.argv[3], "w"), indent=1)

def all_heads(mini):
    out = {}
    for v in mini["verdicts"]:
        if v["quantity"] != "duration" or v.get("supersedes"):
            continue
        d = (v.get("detail") or {}).get("beams_from_strokes")
        side = (v.get("detail") or {}).get("beam_side")
        if d and d.get("tip") and side in ("up", "down"):
            out[v["subject"]] = dict(settled=d["settled"], before=d["before"], after=d["after"], stem=d["tip"]["stem"], side=side,
                                     flag_levels=d.get("flag_levels"), rec_levels=d["tip_levels"])
    return out


def tip_count(views, stem_ord, side, off):
    """Level count at a head's tip, from `views`; `off` switches the 2.202b fused/join code off (= the 2.202 reading)."""
    import dataclasses
    keep = (BS.FUSED_DOUBLE_MIN_THICKNESS_SPACES, BS.JOIN_MAX_GAP_SPACES)
    try:
        if "fused" in off:
            BS.FUSED_DOUBLE_MIN_THICKNESS_SPACES = 1e9
        if "join" in off:
            BS.JOIN_MAX_GAP_SPACES = -1.0
        by = {v.ordinal: v for v in views}
        if stem_ord not in by:
            return None, {}
        role = BS.roles(views)
        t = BS.tip_reading(views, role, by[stem_ord], side)
        return len(t["beams"]), t
    finally:
        BS.FUSED_DOUBLE_MIN_THICKNESS_SPACES, BS.JOIN_MAX_GAP_SPACES = keep


def settle(rep, live_dir, out_path):
    import dataclasses
    res = {}
    for plate in ("litolff", "brahms"):
        mini = json.load(open(rep / "work" / ("%s.on.mini-record.json" % plate)))
        heads = all_heads(mini)
        causes_src = BC.heads_of(mini)
        del mini
        views = load_views(rep / "work" / ("%s.on.gathered.record.json" % plate))
        live = json.load(open(pathlib.Path(live_dir) / ("%s.json" % plate)))
        mism = 0

        def with_thick(cell, which):
            nonlocal mism
            vs = views[cell]
            if which == "old" or cell not in live:
                return vs
            by_i = {r["i"]: r for r in live[cell]}
            out = []
            for v in vs:
                r = by_i.get(v.ordinal)
                if r is not None and tuple(r["box"]) == tuple(int(x) for x in v.box):
                    out.append(dataclasses.replace(v, thickness=float(r[which])))
                else:
                    if r is not None:
                        mism += 1
                    out.append(v)
            return out
        arms = {"2.202": ("old", {"fused", "join"}), "T": ("A", {"fused", "join"}), "TF": ("A", {"join"}), "TFJ": ("A", set()),
                "F_only": ("old", {"join"}), "J_only": ("old", {"fused"})}
        tab = collections.defaultdict(lambda: collections.Counter())
        changed = collections.Counter()
        rows = {}
        for rg, h in heads.items():
            cell = rg.rsplit("/", 1)[0][len("glyph/"):]
            if cell not in views or h["flag_levels"]:
                continue
            main = h["before"][0] if h["before"][0] == h["before"][1] else None
            cause = None
            per = {}
            for name, (which, off) in arms.items():
                n, _t = tip_count(with_thick(cell, which), h["stem"], h["side"], off)
                per[name] = n
            cz = causes_src.get(rg)
            cause = None
            if cz:
                keep = (BS.FUSED_DOUBLE_MIN_THICKNESS_SPACES, BS.JOIN_MAX_GAP_SPACES)
                BS.FUSED_DOUBLE_MIN_THICKNESS_SPACES, BS.JOIN_MAX_GAP_SPACES = 1e9, -1.0      # the cause is the 2.202 reading's: classify with the 2.202b code off
                try:
                    cause = BC.classify(cz, views[cell], [])[0]
                finally:
                    BS.FUSED_DOUBLE_MIN_THICKNESS_SPACES, BS.JOIN_MAX_GAP_SPACES = keep
            rows[rg] = dict(settled=h["settled"], before=h["before"], rec=h["rec_levels"], cause=cause, **per)
            for name in arms:
                n = per[name]
                state = "no_stem" if n is None else ("main_uncertain" if main is None else ("agrees" if n == main else ("more" if n > main else "fewer")))
                tab[name][(h["settled"] if h["settled"] in ("agrees", "stroke_candidate", "disagree_narrowed") else "other", state)] += 1
        by_cause = collections.defaultdict(collections.Counter)
        for rg, r in rows.items():
            if r["cause"] and r["before"][0] == r["before"][1]:
                for n in arms:
                    v = r[n]
                    by_cause[r["cause"] + "|" + n]["agrees" if v == r["before"][0] else ("more" if v is not None and v > r["before"][0] else "fewer")] += 1
        res[plate] = dict(thickness_mismatch=mism, by_cause={k: dict(v) for k, v in sorted(by_cause.items())}, table={n: {"%s/%s" % k: v for k, v in sorted(c.items())} for n, c in tab.items()}, heads=rows)
        print(plate, "mismatch", mism)
        for n, c in tab.items():
            print("  ", n, dict(sorted(c.items())))
        for k, v in sorted(by_cause.items()):
            print("   cause", k, dict(v))
    json.dump(res, open(out_path, "w"))


if __name__ == "__main__":
    if "--settle" in sys.argv:
        settle(pathlib.Path(sys.argv[1]), sys.argv[2], sys.argv[3])
    else:
        main()
