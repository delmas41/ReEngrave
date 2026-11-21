"""ROADMAP 2.331 fixes (STAGED). Both built OFF.

A -- `OMR_WORD_LETTER_NOT_DYNAMIC` (ADJUDICATE, `text.adjudicate_dynamic` + `claims.letter_is_the_words`): a letter that is part of a printed word is that
word's ink, never a dynamic; a dynamic NEXT TO a word stays. Controls are the REAL rows of the six places the 2.331 pricing found (frozen-sample ON gathers of
2026-11-21, `lr-r7-frozen`): every detector box on the letter's ink with its page box, the CV neighbour reading off the page pixels, and the OCR word as read.
Four are letters of a word written as dynamics (the p of `Pizz.`, `pesante`, `poco f`; the `do` of `perdendosi` boxed as f); two are real dynamics beside a word
(`piu p`, read `sempre A`; `p cresc.`, read `cresc.`).

B -- `OMR_FOLD_FAR_BY_LEDGER` (EXPORT, `export._settle_folded_pitches`): a far head is never placed by its ink position.
"""
from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401
from tools.omr.staged import gather as G
from tools.omr.staged import record as R
from tools.omr.staged import claims as CL
from tools.omr.staged.record import Log, Q, READERS

FLAG_A = "OMR_WORD_LETTER_NOT_DYNAMIC"

# (letter, page box, (ink left, ink right)) -- real rows; (word as read, its page box)
PIZZ = dict(  # Litolff p9 system 0, cell 7: `Pizz.` under the real `p` of the staff above
    letters=[("p", [1389.315, 1902.115, 1421.76, 1927.0], (False, True)),      # glyph/9/0/10/7/4
             ("p", [1389.0, 1902.5875, 1410.105, 1927.0], (False, False)),     # glyph/9/0/10/7/5 (tight on the bowl: "alone")
             ("p", [1390.89, 1902.3725, 1407.1125, 1931.0375], (False, False)),  # glyph/9/0/11/7/5
             ("p", [1391.0475, 1901.7425, 1417.98, 1930.88], (False, True)),   # glyph/9/0/11/7/6
             ("p", [1399.08, 1861.48, 1426.485, 1895.185], (False, False))],   # glyph/9/0/10/7/3: the REAL p above the word
    words=[("Pizz", [1389.0, 1899.0, 1460.0, 1937.0])])
PESANTE = dict(  # Brahms p4 system 0
    letters=[("p", [1142.0673828125, 2539.5576171875, 1171.9833984375, 2583.8671875], (False, False)),
             ("p", [1155.896484375, 2539.5576171875, 1182.42578125, 2583.0205078125], (False, True)),
             ("p", [1138.6806640625, 2539.38671875, 1179.603515625, 2584.54296875], (False, True)),
             ("p", [1149.6875, 2539.6689453125, 1182.7080078125, 2582.849609375], (False, True)),
             ("p", [1188.634765625, 2537.4111328125, 1239.435546875, 2572.4072265625], (True, True))],
    words=[("pesante", [1144.0, 2527.0, 1394.0, 2585.0])])
PERDENDOSI = dict(  # Brahms p8 system 1: the `do` boxed four times as f, the `n` as m
    letters=[("f", [2624.55, 6501.35, 2660.3, 6554.15], (False, False)),
             ("f", [2615.75, 6500.525, 2667.175, 6554.15], (False, False)),
             ("f", [2620.425, 6500.8, 2690.0, 6553.875], (False, True)),
             ("f", [2620.7, 6501.3, 2660.575, 6553.275], (False, False)),
             ("m", [2574.775, 6515.05, 2614.1, 6553.0], (False, True))],
    words=[("perdendosi", [2386.0, 6501.0, 2750.0, 6571.0])])
POCO_F = dict(  # Brahms p25 system 1
    letters=[("p", [2705.845, 5770.1025, 2739.145, 5815.6125], (False, False)),
             ("p", [2732.2075, 5770.6575, 2755.5175, 5812.2825], (False, True)),
             ("p", [2705.29, 5770.285, 2739.145, 5817.7375], (False, False)),
             ("p", [2715.835, 5770.84, 2759.4025, 5816.905], (False, True)),
             ("p", [2726.6575, 5771.95, 2759.68, 5814.9625], (False, True)),
             ("f", [2766.6175, 5771.95, 2813.7925, 5808.58], (True, True))],      # the `c`, boxed as f
    words=[("poco f", [2705.0, 5760.0, 2926.0, 5832.0])])
#: the last `o` of `poco` boxed twice as p (cell 4 of that staff): the reading has an `o` there, so the rule cannot tell -- it stays what it was (a known leftover)
POCO_LAST_O = [("p", [2816.22, 5773.3375, 2853.6825, 5808.025], (True, False)), ("p", [2814.555, 5773.9875, 2855.3475, 5811.1725], (True, False))]
PIU_P = dict(  # Litolff p8 system 0: `sempre piu p`, the OCR read `sempre A`; the p is REAL (Sean 2.296/2.301 tiles: the dynamic)
    letters=[("p", [1828.7925, 1291.99, 1859.505, 1309.0], (False, False)),
             ("p", [1827.375, 1292.31, 1859.19, 1325.7], (True, False)),
             ("f", [1788.0, 1285.69, 1846.1175, 1309.0], (True, False)),
             ("f", [1792.095, 1269.0, 1821.2325, 1315.305], (False, False))],
    words=[("sempre A", [1613.0, 1247.0, 1871.0, 1330.0])])
P_CRESC = dict(  # Brahms p12 system 0: `p cresc.`, the OCR read `cresc.` from the c on; the p is REAL
    letters=[("f", [4646.4875, 703.785, 4688.1125, 756.2325], (True, False)),
             ("p", [4660.085, 704.0625, 4703.6525, 750.405], (False, False)),
             ("p", [4648.1525, 703.785, 4703.6525, 756.51], (True, False)),
             ("p", [4644.8225, 703.785, 4688.1125, 756.2325], (True, False)),
             ("p", [4646.765, 703.375, 4692.275, 756.3775], (True, False)),
             ("p", [4664.525, 702.82, 4703.93, 748.885], (False, False)),
             ("f", [4645.655, 703.375, 4686.4475, 755.545], (True, False)),
             ("p", [4652.0375, 703.6525, 4703.6525, 754.99], (True, False))],
    words=[("cresc.", [4658.0, 694.0, 4890.0, 742.0])])


def _dynamic(place):
    """`Q.DYNAMIC` of the one bar holding the place's real rows (every row in one cell: ownership plays no part here)."""
    log = Log()
    cell = R.cell(0, 0, 0, 0)
    for i, (letter, box, (left, right)) in enumerate(place["letters"]):
        g = R.glyph(0, 0, 0, 0, i)
        cy = (box[1] + box[3]) / 2.0
        log.observe(g, Q.DYNAMIC_LETTER, "dynamic" + letter.upper(), reader=READERS.DETECTOR, frame=G.FRAME_PAGE, score=0.8,
                    letter=letter, cell_frame="cell:0", bbox_page_px=list(box), x_center_page=(box[0] + box[2]) / 2.0,
                    y_center_page=cy, staff_bottom_line_page=box[1] - 40.0, staff_spacing_px=20.0, band_offset_spaces=1.7,
                    in_hairpin_band=True)
        log.observe(g, Q.DYNAMIC_LETTER_NEIGHBOURS, {"left": left, "right": right, "left_spaces": None, "right_spaces": None},
                    reader=READERS.CV_LETTER_NEIGHBOURS, frame=G.FRAME_PAGE)
    for j, (text, box) in enumerate(place["words"]):
        log.observe(R.glyph(0, 0, 0, 0, 900 + j), Q.DIRECTION_WORD, text, reader=READERS.TESSERACT, frame="page",
                    bbox_page_px=list(box), category="expression")
    log.freeze()
    adjudicate.run(log)
    v = log.verdict(Q.DYNAMIC, cell)
    return v


def _written(v):
    return sorted(v.value) if v is not None and isinstance(v.value, list) else v.value if v is not None else None


@pytest.mark.parametrize("name,place", [("Pizz.", PIZZ), ("pesante", PESANTE), ("perdendosi", PERDENDOSI), ("poco f", POCO_F)])
def test_A_flag_off_the_letter_of_the_word_is_written_as_a_dynamic(monkeypatch, name, place):
    """THE CONTROL THAT FAILS: with the flag off the word's letter reaches the file as a dynamic (what the 2.331 pricing found)."""
    monkeypatch.delenv(FLAG_A, raising=False)
    v = _dynamic(place)
    assert v.detail.get("letters_of_the_word_ink", 0) == 0
    letters = "".join(_written(v) or [])
    assert ("f" if name == "perdendosi" else "p") in letters, (name, _written(v))


@pytest.mark.parametrize("name,place", [("Pizz.", PIZZ), ("pesante", PESANTE), ("perdendosi", PERDENDOSI), ("poco f", POCO_F)])
def test_A_flag_on_the_letter_of_the_word_is_the_words(monkeypatch, name, place):
    monkeypatch.setenv(FLAG_A, "1")
    v = _dynamic(place)
    assert v.detail.get("letters_of_the_word_ink", 0) >= 1, (name, v.detail)
    w = _written(v) or []
    if name == "Pizz.":
        assert w == ["p"]           # the real p printed above `Pizz.` stays, once
    else:
        assert not any(("f" if name == "perdendosi" else "p") in x for x in w), (name, w)


@pytest.mark.parametrize("name,place", [("piu p", PIU_P), ("p cresc.", P_CRESC)])
def test_A_a_dynamic_next_to_a_word_is_never_dropped(monkeypatch, name, place):
    """The other side of the boundary: the space between the word and the dynamic. Same file with the flag on as off."""
    monkeypatch.delenv(FLAG_A, raising=False)
    off = _written(_dynamic(place))
    monkeypatch.setenv(FLAG_A, "1")
    v = _dynamic(place)
    assert v.detail.get("letters_of_the_word_ink", 0) == 0
    assert _written(v) == off


def test_A_rule_words():
    """`claims.letter_is_the_words` on its boundary, in the words of the rule."""
    box = [100.0, 0.0, 400.0, 50.0]          # 6 characters of `poco f`: 50 px each
    # the word's own first letter, read as that letter: the word's
    assert CL.letter_is_the_words([[100, 5, 140, 45]], "p", box, "poco f", True) == "the_words_edge_letter"
    # inside the word: the word's
    assert CL.letter_is_the_words([[160, 5, 190, 45]], "p", box, "poco f", True) == "inside_the_word"
    # the dynamic token of the reading: stays
    assert CL.letter_is_the_words([[355, 5, 395, 45]], "f", box, "poco f", True) is None
    # a different letter at the word's edge (`p cresc.` read `cresc.`): stays
    assert CL.letter_is_the_words([[100, 5, 140, 45]], "p", box, "cresc.", True) is None
    # a lone letter in the reading (`sempre A`): stays
    assert CL.letter_is_the_words([[355, 5, 395, 45]], "p", [100.0, 0.0, 420.0, 50.0], "sempre A", True) is None
    # never an edge letter without letter ink beside it (`p dolce`, the p clear of the word); inside the word the reading is the witness
    assert CL.letter_is_the_words([[100, 5, 140, 45]], "p", box, "poco f", False) is None
    assert CL.letter_is_the_words([[160, 5, 190, 45]], "p", box, "poco f", False) == "inside_the_word"
    # never outside the word's box
    assert CL.letter_is_the_words([[20, 5, 60, 45]], "p", box, "poco f", True) is None


def test_A_flag_default_off(monkeypatch):
    monkeypatch.delenv(FLAG_A, raising=False)
    assert not CL.word_letter_not_dynamic_enabled()
    monkeypatch.setenv(FLAG_A, "1")
    assert CL.word_letter_not_dynamic_enabled()


# ── B: a far head is never placed by its ink position ────────────────────────

FLAG_B = "OMR_FOLD_FAR_BY_LEDGER"
#: the real rows (frozen-sample Litolff ON gather, re-adjudicated on this lane's tree): mg/10/1/40 = p10 the F5/Ab5 dyad a third apart folded into one head (the
#: Ab5 box's ledger count `ledger_not_read`); mg/8/0/162 = p8 two boxes of the A5 with its printed natural (ledger -2 decided on both, the natural owned by /4)
ROWS = json.loads(r'''{"glyph/10/1/1/0/10": {"glyph_box":{"detail": {"bbox_page_px": [525.0475, 2233.4075, 549.775, 2256.56]}}, "notehead_staff_position": {"value": -0.4, "detail": {"rounded": 0, "hole_ink_position": -0.207}}, "mark_group": {"value": "mg/10/1/40", "detail": {"identity": "page_head"}}, "glyph_conf": 0.34388890862464905, "notehead_position": null, "accidental_owner": []}, "glyph/10/1/1/0/11": {"glyph_box": {"detail": {"bbox_page_px": [524.89, 2234.9825, 549.775, 2266.325]}}, "notehead_staff_position": {"value": 0.32, "detail": {"rounded": 0, "hole_ink_position": null}}, "mark_group": {"value": "mg/10/1/40", "detail": {"identity": "page_head"}}, "glyph_conf": 0.33606868982315063, "notehead_position": null, "accidental_owner": []}, "glyph/10/1/1/0/12": {"glyph_box": {"detail": {"bbox_page_px": [525.6775, 2227.7375, 548.2, 2244.7475]}}, "notehead_staff_position": {"value": -1.5, "detail": {"rounded": -2}}, "mark_group": {"value": "mg/10/1/40", "detail": {"identity": "page_head"}}, "glyph_conf": 0.25975123047828674, "notehead_position": {"outcome": "abstained", "value": null, "reason": "ledger_not_read"}, "accidental_owner": []}, "glyph/8/0/1/11/2": {"glyph_box": {"detail": {"bbox_page_px": [1527.6125, 547.8625, 1553.7575, 571.4875]}}, "notehead_staff_position": {"value": -2.46, "detail": {"rounded": -2}}, "mark_group": {"value": "mg/8/0/162", "detail": {"identity": "page_head"}}, "glyph_conf": 0.6505852937698364, "notehead_position": {"outcome": "decided", "value": -2, "reason": "ledger_position"}, "accidental_owner": []}, "glyph/8/0/1/11/4": {"glyph_box": {"detail": {"bbox_page_px": [1527.77, 547.705, 1554.545, 572.1175]}}, "notehead_staff_position": {"value": -2.44, "detail": {"rounded": -2}}, "mark_group": {"value": "mg/8/0/162", "detail": {"identity": "page_head"}}, "glyph_conf": 0.571317732334137, "notehead_position": {"outcome": "decided", "value": -2, "reason": "ledger_position"}, "accidental_owner": [{"outcome": "decided", "value": "glyph/8/0/1/11/4", "subject": "glyph/8/0/1/11/0"}]}}''')
PITCH = {"glyph/10/1/1/0/10": "F5", "glyph/10/1/1/0/11": "F5", "glyph/10/1/1/0/12": "Ab5", "glyph/8/0/1/11/2": "Ab5", "glyph/8/0/1/11/4": "A5"}


class _Rec:
    """The export `Record` lookups the settle reads, over the real rows."""

    def obs(self, quantity, sub):
        from tools.omr.staged import export as E
        r = ROWS.get(sub) or {}
        key = {E.Q.GLYPH_BOX: "glyph_box", E.Q.NOTEHEAD_STAFF_POSITION: "notehead_staff_position", E.Q.MARK_GROUP: "mark_group"}.get(quantity)
        return [r[key]] if key and r.get(key) else []

    def verdict(self, quantity, sub):
        from tools.omr.staged import export as E
        if quantity == E.Q.NOTEHEAD_POSITION:
            return (ROWS.get(sub) or {}).get("notehead_position")
        if quantity == E.Q.ACCIDENTAL_OWNER:
            return next((a for r in ROWS.values() for a in r["accidental_owner"] if a["subject"] == sub), None)
        return None

    def verdicts_of(self, quantity):
        from tools.omr.staged import export as E
        return [a for r in ROWS.values() for a in r["accidental_owner"]] if quantity == E.Q.ACCIDENTAL_OWNER else []


def _settle(gid):
    from tools.omr.staged import export as E
    run = SimpleNamespace(spacing=15.75)
    queued = [(gid, float(r["glyph_conf"]), s, run, 0, {"category": "notehead", "pitch": PITCH[s]}, {})
              for s, r in ROWS.items() if r["mark_group"]["value"] == gid]
    best = {}
    for g, conf, sub, *_r in queued:
        cur = best.get(g)
        if cur is None or (-conf, sub) < (-cur[0], cur[1]):
            best[g] = (conf, sub)
    E._settle_folded_pitches(_Rec(), queued, best)
    written = next(q for q in queued if q[2] == best[gid][1])
    return written[5]["pitch"], bool(written[5].get("guess"))


def test_B_flag_off_the_p10_dyad_is_written_F5_plain_by_its_ink(monkeypatch):
    """THE CONTROL THAT FAILS: the ink witness (the hole at -0.21) picks the F5 box and writes it plain; the Ab5 above it has no ledger reading."""
    monkeypatch.delenv(FLAG_B, raising=False)
    assert _settle("mg/10/1/40") == ("F5", False)


def test_B_flag_on_the_p10_dyad_is_guessed_never_plain(monkeypatch):
    monkeypatch.setenv(FLAG_B, "1")
    pitch, blue = _settle("mg/10/1/40")
    assert blue, "a fold with a far member whose ledger reading is missing is GUESSED"


def test_B_flag_off_the_p8_A_natural_is_written_A_flat(monkeypatch):
    """THE CONTROL THAT FAILS: the more confident box (no accidental of its own) is written: A-flat, where the page prints a natural."""
    monkeypatch.delenv(FLAG_B, raising=False)
    assert _settle("mg/8/0/162") == ("Ab5", True)


def test_B_flag_on_the_printed_natural_decides_the_A(monkeypatch):
    """Both boxes stand on the first ledger line above (ledger -2, decided); only the alteration differs, and the natural is printed on the head."""
    monkeypatch.setenv(FLAG_B, "1")
    assert _settle("mg/8/0/162") == ("A5", False)


def test_B_flag_default_off(monkeypatch):
    from tools.omr.staged import export as E
    monkeypatch.delenv(FLAG_B, raising=False)
    assert not E.fold_far_by_ledger_enabled()
