"""ROADMAP 2.261: write the three 2-page-per-plate development samples (NOT the frozen sample) next to sample-r3.json."""
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
base = json.load(open(HERE / "sample-r3.json"))


def mk(name, what, lit, br):
    d = dict(base)
    d["what"] = what
    d["plates"] = {"litolff": {**base["plates"]["litolff"], "pages": lit, "context_pages": [1]},
                   "brahms": {**base["plates"]["brahms"], "pages": br, "context_pages": [0]}}
    json.dump(d, open(HERE / ("%s.json" % name), "w"), indent=1)


mk("sample-261-fix1", "ROADMAP 2.261 fix 1 (NOT the frozen sample): Litolff p3 (beam read as a crescendo) + p6; Brahms p8 + p19 (hairpins 2.254 gained)", [3, 6], [8, 19])
mk("sample-261-fix2", "ROADMAP 2.261 fix 2 (NOT the frozen sample): Litolff p6 (faster over heads) + p9 (pizz. retry word control); Brahms p8 + p19 (retry words dim./pesante)", [6, 9], [8, 19])
mk("sample-261-fix3", "ROADMAP 2.261 fix 3 (NOT the frozen sample): Litolff p6 + p14 (27 notes unpitched); Brahms p4 + p5", [6, 14], [4, 5])
