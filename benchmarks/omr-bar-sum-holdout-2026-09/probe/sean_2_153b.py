"""ROADMAP 2.153b -- every glyph Sean has given a DURATION answer for, per doc: the judged index's glyph-subject duration rows
plus every out/print/*/answers.json whose tiles carry a `glyph` and a `sean` answer (2.153 keeps its glyphs there, not in the
index). Also EVERY glyph any answers/manifest/index names (to exclude from new tiles).
import: sean_2_153b.load() -> (values {doc: {glyph: (source, beats)}}, named {glyph})"""
import glob
import json
import sys

sys.path.insert(0, ".")
from tools.omr.staged import judged  # noqa: E402


def load():
    vals, named = {}, set()
    for r in json.load(open("benchmarks/acceptance/judged-tiles.json"))["tiles"]:
        subs = [s for s in (r["subjects"] or [r["subject"]]) if s]
        named |= {s for s in subs if s.startswith("glyph/")}
        if r["subject_kind"] == "glyph" and r["answer_kind"] == "duration" and r["value"] is not None and r["doc"]:
            for s in subs:
                vals.setdefault(r["doc"], {})[s] = ("%s/%s" % (r["item"], r["tile"]), float(r["value"]))
    for path in glob.glob("out/print/**/answers.json", recursive=True) + glob.glob("out/print/**/manifest.json",
                                                                                     recursive=True):
        try:
            d = json.load(open(path))
        except (OSError, ValueError):
            continue
        tiles = d.get("tiles") if isinstance(d, dict) else None
        if not isinstance(tiles, list):
            continue
        item = path.split("/")[-2]
        for t in tiles:
            if not isinstance(t, dict) or not str(t.get("glyph", "")).startswith("glyph/"):
                continue
            named.add(t["glyph"])
            if "sean" in t and t.get("doc"):
                kind, val = judged.parse_answer(t["sean"])
                if kind == "duration" and val is not None:
                    vals.setdefault(t["doc"], {}).setdefault(t["glyph"], ("%s/%s" % (item, t.get("n")), float(val)))
    return vals, named


if __name__ == "__main__":
    v, n = load()
    print({d: len(x) for d, x in v.items()}, "named glyphs", len(n))
