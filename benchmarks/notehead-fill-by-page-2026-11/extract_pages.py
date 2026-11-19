"""ROADMAP 2.326 small test (read-only): every notehead-classed detector box on the frozen-sample pages, from the
20261117-night lane-report SLICES (jsonl; no record loaded), with its fill readings and its standing duration /
not-a-notehead verdicts. Writes work/pages-<doc>.json.

    python3 benchmarks/notehead-fill-by-page-2026-11/extract_pages.py litolff
"""
import json
import pathlib
import sys

SL = pathlib.Path("/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/lane-report-slices-20261117-night")
OUT = pathlib.Path(__file__).parent / "work"
OBS_Q = ("notehead_ink", "head_ink", "notehead_class")
V_Q = ("duration", "notehead_is_not_a_notehead")


def main(doc):
    d = SL / doc
    heads = {}
    other = {}
    with open(d / "observations.jsonl") as f:
        for line in f:
            if '"glyph/' not in line[:60]:
                continue
            o = json.loads(line)
            s, q = o["subject"], o["quantity"]
            if q == "glyph_box":
                det = o.get("detail") or {}
                if det.get("category") == "notehead":
                    heads[s] = {"subject": s, "cls": o["value"][0], "score": o.get("score"),
                                "bbox_page_px": det.get("bbox_page_px")}
            elif q in OBS_Q:
                other.setdefault(s, {})[q] = {"value": o.get("value"), "detail": o.get("detail"), "reader": o.get("reader")}
    want = set(heads)
    kept = {}
    with open(d / "verdicts.jsonl") as f:
        for line in f:
            if '"glyph/' not in line[:60]:
                continue
            v = json.loads(line)
            if v.get("subject") in want and v.get("quantity") in V_Q:
                kept.setdefault((v["subject"], v["quantity"]), []).append(
                    {k: v.get(k) for k in ("id", "outcome", "value", "decider", "reason", "margin", "supersedes",
                                           "candidates", "detail")})
    for (s, q), vs in kept.items():
        sup = {x["supersedes"] for x in vs if x.get("supersedes")}
        live = [x for x in vs if x["id"] not in sup] or vs
        heads[s][q] = live[-1]
    for s, h in heads.items():
        h["obs"] = other.get(s, {})
    OUT.mkdir(exist_ok=True)
    json.dump({"doc": doc, "heads": list(heads.values())}, open(OUT / ("pages-%s.json" % doc), "w"), default=str)
    print(doc, len(heads), "notehead boxes")


if __name__ == "__main__":
    main(sys.argv[1])
