"""ROADMAP 2.205 (read-only): the measured size of the strokes under the boxes the old rules KEPT, per class group, so the convention sizes in
`stroke_owner.shape_fit` are checked against our two plates before they speak (rule 7: a control must be able to fail).

usage: owner_shape_sizes.py REPORT_OUT_DIR OUT.json      (the 2.202 milestone dir; the ON gathered records)
For each kept head / rest box (its live `notehead_is_not_a_notehead` / `rest_is_not_a_rest` verdict value False): every stroke it COVERS,
by kind: w, h (sp), length, thickness, area -- percentiles; and the same for the strokes `shape_fit` says `no` to, by its `why`."""
import collections
import json
import pathlib
import sys

sys.path.insert(0, ".")
sys.path.insert(0, "benchmarks/shared-ink-map-2026-10")
import multi_claim_census as MC                      # noqa: E402
from tools.omr.staged import stroke_owner as SO      # noqa: E402


def group(cls):
    c = cls.lower()
    if c in SO.BLOCK_RESTS:
        return "rest_block"
    if c.startswith("rest"):
        return "rest_other"
    if c.startswith("notehead"):
        return "head_" + ("hollow" if ("half" in c or "whole" in c) else "black")
    return None


def pct(xs):
    xs = sorted(xs)
    if not xs:
        return None
    return [round(xs[int(q * (len(xs) - 1))], 2) for q in (0.05, 0.25, 0.5, 0.75, 0.95)] + [len(xs)]


def main():
    rep = pathlib.Path(sys.argv[1])
    res = {}
    for plate in ("litolff", "brahms"):
        path = rep / "work" / ("%s.on.gathered.record.json" % plate)
        cells, _areas = MC.stream(path)
        old = MC.old_verdicts(path)
        kept = {k for (q, k), (_o, _r, _d, val) in old.items() if q in ("notehead_is_not_a_notehead", "rest_is_not_a_rest") and val is False}
        dims = collections.defaultdict(lambda: collections.defaultdict(list))
        nos = collections.Counter()
        for _ck, c in cells.items():
            for k, (cov, _partial, _rid) in c["gs"].items():
                if k not in kept or k not in c["boxes"]:
                    continue
                g = group(c["boxes"][k][0])
                if g is None:
                    continue
                for o in cov:
                    t = c["strokes"].get(o)
                    if t is None:
                        continue
                    ink = SO.Ink(o, t[0], tuple(float(v) for v in t[1]), t[2], t[3], MC.area_sp2(t), t[7], t[6], t[9], t[5])
                    d = dims[(g, ink.kind)]
                    d["w"].append(ink.w_sp)
                    d["h"].append(ink.h_sp)
                    d["len"].append(ink.length)
                    d["thick"].append(ink.thickness)
                    d["area"].append(ink.area)
                    fam = "rest" if g.startswith("rest") else "head"
                    fit, why = SO.shape_fit(fam, ink, c["boxes"][k][0])
                    if fit == "no":
                        nos[(g, why.split(":")[0], ink.kind)] += 1
        res[plate] = {"dims": {"%s|%s" % k: {m: pct(v) for m, v in d.items()} for k, d in sorted(dims.items())},
                      "shape_no_on_kept_boxes": {"|".join(k): v for k, v in nos.most_common()}}
        print(plate)
        for k, v in res[plate]["dims"].items():
            print("  ", k, v)
        print("   no:", res[plate]["shape_no_on_kept_boxes"])
    json.dump(res, open(sys.argv[2], "w"), indent=1)


if __name__ == "__main__":
    main()
