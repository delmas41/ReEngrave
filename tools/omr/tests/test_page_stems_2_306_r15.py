"""ROADMAP 2.306 r15 -- a stem joins the head whose INK it touches (Sean 2026-11-18: "when joining things or separating things, we use the ink to
distinguish or connect, not the boxes"). `page_stems.read`, flag `OMR_PAGE_STEMS` (default OFF).

Controls are REAL marks Sean has labelled (CLAUDE rule 7): his swept Brahms 317803 page 0 (data/hand-truth/pages/imslp317803/0.json), staff 4 bars 3
and 4, cut from a real gather's page-stem inputs (`fixtures/page_stems_2_306_r15_p0_both_ways.json`, benchmarks/page-ledger-2026-11/2306/
r15_cut_fixture.py). There a stem stroke was also read the OTHER way by a box whose ink does not touch it, and the reader refused every head on it
(`stroke_read_both_ways`); Sean's labels give both heads that stem. Each control is shown failing with the rule off: the same page with the page map's
contacts removed refuses them again.
"""
import json
import os

from tools.omr.staged import page_stems as PS

HERE = os.path.dirname(__file__)
FX = os.path.join(HERE, "fixtures", "page_stems_2_306_r15_p0_both_ways.json")
TRUTH = os.path.join(HERE, "..", "..", "..", "data", "hand-truth", "pages", "imslp317803", "0.json")


def _load(no_contacts=False):
    with open(FX) as f:
        fx = json.load(f)
    heads = [dict(h, box=tuple(h["box"])) for h in fx["heads"]]
    verts = [dict(v, box=tuple(v["box"])) for v in fx["verticals"]]
    cross = [dict(c, box=tuple(c["box"])) for c in fx["crossers"]]
    strokes = {int(k): dict(v, box=tuple(v["box"]), touches=[] if no_contacts else v["touches"]) for k, v in fx["strokes"].items()}
    held = {int(k): v for k, v in fx["held"].items()}
    return fx, PS.read(heads, verts, held, crossers=cross, strokes=strokes), {v["ord"]: v["box"] for v in verts}


def _seans_stem(box):
    with open(TRUTH) as f:
        t = json.load(f)
    for b in t["boxes"]:
        if b["cls"] != "stem":
            continue
        s = b["rect"]
        if abs((s[0] + s[2]) / 2.0 - (box[0] + box[2]) / 2.0) <= 8 and min(s[3], box[3]) - max(s[1], box[1]) >= 0.3 * min(s[3] - s[1], box[3] - box[1]):
            return s
    return None


def test_a_stroke_read_both_ways_goes_to_the_heads_whose_ink_it_touches():
    fx, res, vbox = _load()
    for hid, stroke in fx["expect"].items():
        r = res["heads"][int(hid)]
        assert r["state"] == "one" and r["stroke"] == int(stroke) and r["direction"] == "up", (hid, r)
        # Sean's own stem label is that stroke
        assert _seans_stem(vbox[int(stroke)]) is not None, hid


def test_control_without_the_ink_contacts_the_same_heads_are_refused():
    fx, res, _ = _load(no_contacts=True)
    for hid in fx["expect"]:
        assert res["heads"][int(hid)]["how"] == "stroke_read_both_ways", res["heads"][int(hid)]


def _toy(touch_a, touch_b, directions=("down", "down")):
    """Two strokes at one head's left edge (both read 'down'); the head's own ink is stroke 10."""
    head = dict(id=0, members=["glyph/0/0/0/0/0"], box=(100.0, 100.0, 120.0, 114.0), sp=16.0, ink=True, strokes=[10])
    a = dict(ord=1, box=(99.0, 104.0, 103.0, 170.0), sp=16.0)
    b = dict(ord=2, box=(95.0, 104.0, 98.0, 160.0), sp=16.0)
    strokes = {10: dict(box=(101.0, 100.0, 120.0, 114.0), kind="blob", touches=[]),
               1: dict(box=a["box"], kind="vertical", touches=[[10, 1.0]] if touch_a else []),
               2: dict(box=b["box"], kind="vertical", touches=[[10, 1.0]] if touch_b else [])}
    return PS.read([head], [a, b], {}, crossers=[], strokes=strokes)["heads"][0]


def test_of_two_strokes_on_one_side_only_the_one_touching_the_head_ink_joins():
    r = _toy(True, False)
    assert r["state"] == "one" and r["stroke"] == 1 and r["how"] == "engraving_side_by_ink"


def test_never_chosen_when_both_or_neither_touch():
    assert _toy(True, True)["how"] == "two_candidates"
    assert _toy(False, False)["how"] == "two_candidates"


def test_head_ink_is_never_an_upright_nor_a_held_stroke():
    head = dict(id=0, box=(0.0, 0.0, 20.0, 20.0), strokes=[])
    strokes = {1: dict(box=(5.0, 5.0, 15.0, 15.0), kind="blob"), 2: dict(box=(9.0, 2.0, 11.0, 18.0), kind="vertical"),
               3: dict(box=(4.0, 4.0, 16.0, 16.0), kind="blob"), 4: dict(box=(30.0, 30.0, 40.0, 40.0), kind="blob")}
    assert PS.head_ink([head], strokes, {3: "accidental"})[0] == {1}
