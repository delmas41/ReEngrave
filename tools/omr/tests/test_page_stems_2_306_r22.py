"""ROADMAP 2.306 r22 -- two of the three Litolff bars r21's print read found written WRONG AND PLAIN with the page stem reader on, and the
page stem VIEW's tip read. Controls built from the REAL record rows of those bars (fixture cut verbatim from the r21 Litolff ON gather,
`fixtures/page_stems_2_306_r22.json`); each new-rule test fails on r21's code.

1. Litolff 10/1/2/0 (STAGED GATHER, `page_stems.tall_remainders`): Cl. F4 and A4 half notes on ONE up stem were written as two voices. The
   detector drew one tall box over the dyad and its stem; GATHER read it for the two heads inside it (2.252) and ADJUDICATE refuses it as the
   remainder -- but the page stem reader took it as a third head, paired it with the A4 as "two voices in one column" (r9), and handed the A4
   the rings' left sides (page stroke 404, from the top of the A4's ring to the bottom of the F4's) for a down stem. A box already read for the
   heads inside it IS those heads: it takes no stem and no part in the reading; the A4 then reads stroke 404 as the F4's outline (r19) and
   takes the up stem with the F4.
3. Litolff 1/0/9/6 (STAGED ADJUDICATE, `rhythm.attached_stems`): an eighth rest the detector boxed as a notehead. The page reader gave it no
   stem (the stroke beside it is the next eighth's down stem, held by its head end) -- but the duration reader still attached that stem by box
   overlap, so EVALUATE made the rest a chord mate of the eighth and wrote a D4 eighth. Where the page read a head, the stems it stands on are
   the page's, everywhere the duration reader reads them.
"""
import json
import pathlib

from tools.omr.staged import page_stems as PS

FX = json.loads((pathlib.Path(__file__).parent / "fixtures" / "page_stems_2_306_r22.json").read_text())
TALL, A4, F4 = "glyph/10/1/2/0/10", "glyph/10/1/2/0/11", "glyph/10/1/2/0/12"


def _row(part, subject, quantity):
    return next(r for r in FX[part]["rows"] if r["subject"] == subject and r["quantity"] == quantity)


def _claim_strokes(owner_value):
    return [int(i) for c in FX["dyad"]["claims"] if c["value"] == owner_value for i in c["detail"]["page_strokes"]]


def _dyad_heads():
    """The three page heads as the reader saw them: each box's own page box; the head claims' strokes (claim 13 = the A4's ring, 14 = the
    F4's); the tall box flagged as GATHER's tall read."""
    out = []
    for hid, g, strokes in ((15, TALL, []), (16, A4, _claim_strokes(13)), (17, F4, _claim_strokes(14))):
        bx = _row("dyad", g, "glyph_box")["detail"]
        out.append(dict(id=hid, members=[g], box=tuple(bx["bbox_page_px"]), sp=15.64, sp_own=False, ink=True, strokes=strokes,
                        tall=bool((bx.get("tall_split") or {}).get("read"))))
    return out


def _dyad_strokes():
    vs, all_ = [], {}
    for o, s in FX["dyad"]["page_strokes"].items():
        all_[int(o)] = dict(box=tuple(s["bbox_page_px"]), kind=s["kind"], touches=[(int(j), float(c)) for j, c in s.get("touches") or ()])
        if s["kind"] == "vertical":
            vs.append(dict(ord=int(o), box=tuple(s["bbox_page_px"]), sp=float(s["staff_space_local_px"])))
    crossers = [dict(ord=o, box=v["box"], kind=v["kind"]) for o, v in all_.items() if v["kind"] != "vertical"]
    return vs, crossers, all_


def test_the_fixture_is_the_fault_r21_wrote():
    """The rows say what r21 wrote: the tall box was read for its heads (and refused at ADJUDICATE), yet the A4 took stroke 404 down by the
    two-voices-in-one-column rule, paired with that tall box."""
    assert _row("dyad", TALL, "glyph_box")["detail"]["tall_split"]["read"] is True
    assert _row("dyad", A4, "page_stem")["detail"]["page_stroke"] == 404
    assert _row("dyad", A4, "page_stem")["detail"]["how"] == "two_voices_upper_takes_up"
    refused = {v["subject"]: v for v in FX["dyad"]["verdicts"] if v["quantity"] == "notehead_is_not_a_notehead"}
    assert refused[TALL]["value"] is True and refused[A4]["value"] is False and refused[F4]["value"] is False


def test_r21s_reading_gives_the_a4_the_rings_sides():
    """The control can fail: the reader as r21 called it (every page head, the tall box among them) reproduces the fault from the rows."""
    vs, crossers, all_ = _dyad_strokes()
    res = PS.read(_dyad_heads(), vs, {}, crossers=crossers, strokes=all_)
    assert res["heads"][16]["stroke"] == 404 and res["heads"][16]["direction"] == "down"
    assert res["heads"][16]["how"] == "two_voices_upper_takes_up"


def test_a_box_read_for_its_heads_takes_no_stem_and_the_dyad_is_one_chord():
    heads = _dyad_heads()
    assert PS.tall_remainders(heads) == {15}
    vs, crossers, all_ = _dyad_strokes()
    res = PS.read([h for h in heads if h["id"] not in {15}], vs, {}, crossers=crossers, strokes=all_)
    assert 15 not in res["heads"]
    # both heads stand on the one up stem (524); the rings' sides (404) are no stem
    assert res["heads"][16]["stroke"] == 524 and res["heads"][16]["direction"] == "up"
    assert res["heads"][17]["stroke"] == 524 and res["heads"][17]["direction"] == "up"
    assert 404 not in res["stems"]


def test_never_a_box_that_is_a_head_of_its_own():
    """The boundary: a box not read for heads (no tall read) stays in the reading, and so does each head the tall box was read into."""
    heads = _dyad_heads()
    assert PS.tall_remainders([dict(h, tall=False) for h in heads]) == set()
    assert {16, 17}.isdisjoint(PS.tall_remainders(heads))


# ── 3. the rest boxed as a head, and the stem it was given by box overlap ──

REST, EIGHTH = "glyph/1/0/9/6/6", "glyph/1/0/9/6/0"


class _Ev:
    """The two calls `page_own_stems` makes, answered from the fixture's real rows of one glyph."""

    def __init__(self, glyph):
        from types import SimpleNamespace as NS
        self._rows = [NS(id=r["id"], value=r["value"], detail=r.get("detail")) for r in FX["rest"]["rows"]
                      if r["subject"] == glyph and r["quantity"] == "page_stem"]
        self._ab = [NS(id=a["id"], detail=a.get("detail")) for a in FX["rest"]["abstentions"] if a["subject"] == glyph]

    def rows(self, q, **_kw):
        return self._rows

    def refusals(self, q, **_kw):
        return self._ab


def _cell_stems():
    from types import SimpleNamespace as NS
    return [NS(id=r["id"], value=r["value"]) for r in FX["rest"]["rows"] if r["quantity"] == "stem" and r["subject"] == "cell/1/0/9/6"]


def _canon(glyph):
    return tuple(float(v) for v in _row("rest", glyph, "glyph_box")["value"][1:5])


def test_the_fixture_is_the_rest_r21_wrote_as_an_eighth():
    """The rows: the page gave the rest no stem (the stroke beside it is held by the eighth's head end), yet its duration used the eighth's
    stem row and EVALUATE shared the eighth's value with it."""
    v = {(x["subject"], x["quantity"], x["outcome"]): x for x in FX["rest"]["verdicts"]}
    assert v[(REST, "head_stem", "abstained")]["reason"] == "page_stem_ambiguous"
    assert "obs:011488" in v[(REST, "duration", "narrowed")]["used"]
    assert v[(REST, "duration", "decided")]["reason"] == "chord_mate_shares_the_stem"
    assert _row("rest", EIGHTH, "page_stem")["value"] == "obs:011488"


def test_r21s_box_join_puts_the_rest_on_the_eighths_stem():
    """The control can fail: the box-overlap join r21's duration reader used attaches the eighth's stem row to the rest's box."""
    from tools.omr.staged.adjudicators import rhythm as RH
    assert [s.id for s in RH._stem_joined([], _cell_stems(), _canon(REST))[1]] == ["obs:011488"]


def test_a_head_the_page_joined_to_no_stem_stands_on_none(monkeypatch):
    from tools.omr.staged.adjudicators import rhythm as RH
    monkeypatch.setenv("OMR_PAGE_STEMS", "1")
    stems = _cell_stems()
    own = RH.page_own_stems(_Ev(REST), stems)
    assert own == []
    assert RH.stems_the_head_stands_on(own, stems, _canon(REST)) == []
    # the eighth itself stands on the stem the page read for it
    own8 = RH.page_own_stems(_Ev(EIGHTH), stems)
    assert [s.id for s in RH.stems_the_head_stands_on(own8, stems, _canon(EIGHTH))] == ["obs:011488"]


def test_flag_off_the_box_join_is_unchanged(monkeypatch):
    from tools.omr.staged.adjudicators import rhythm as RH
    monkeypatch.delenv("OMR_PAGE_STEMS", raising=False)
    stems = _cell_stems()
    own = RH.page_own_stems(_Ev(REST), stems)
    assert own is None
    assert [s.id for s in RH.stems_the_head_stands_on(own, stems, _canon(REST))] == ["obs:011488"]


# ── 4. a page-supplied stem's tip is read with the blockers and head boxes the cell reader's stems get ──

def test_a_page_stem_view_reads_its_tip_with_the_cells_blockers_and_heads(monkeypatch):
    """Wiring (fails on r21's code, which handed the view's tip reader `()` and no heads): `_cell_row_for` files a view of a page stroke the
    cell reader has no row for, and its tip read gets `gather.stem_tip_context`'s blockers (the cell's beam rows + the detector's other boxes)
    and head boxes -- the same call the cell reader's own stems go through. Boxes are the real cell 1/0/9/6 rows (fixture)."""
    from types import SimpleNamespace as NS
    from tools.omr.staged import gather as G
    from tools.omr.staged import record as R
    from tools.omr.staged.record import Q, READERS
    seen = {}
    monkeypatch.setattr(G, "_observe_stem_tip_ink", lambda log, sub, frame, c, rid, box, blockers, space, heads=None, **kw:
                        seen.update(blockers=list(blockers), heads=heads))
    monkeypatch.setattr(PS, "_beam_rows_for_view", lambda *a, **k: None)
    eighth = _row("rest", EIGHTH, "glyph_box")["value"]          # ['noteheadBlackInSpace', x, y, w, h] canonical
    det = NS(smufl_name=eighth[0], category="notehead", x_canonical=eighth[1], y_canonical=eighth[2], width_canonical=eighth[3],
             height_canonical=eighth[4], x_center=eighth[1] + eighth[3] / 2.0, y_center=eighth[2] + eighth[4] / 2.0, confidence=0.9)
    beam = NS(reader=READERS.CV_LINES, value=[200.0, 900.0, 400.0, 30.0], id="obs:b")

    class Log:
        def rows(self, q, sub=None, **kw):
            return [beam] if q == Q.BEAM_STROKE else []

        def observe(self, *a, **k):
            return NS(id="obs:view")

    csub = R.cell(1, 0, 9, 6)
    c = NS(bbox_page_px=(1470.0, 2600.0, 1600.0, 2900.0), upscale_factor=6.35, measure_index=6, staff_line_ys_canonical=[500.0, 600.0, 700.0, 800.0, 900.0])
    PS._cell_row_for(Log(), c, csub, (1477.0, 2890.0, 1481.0, 2966.0), {csub.to_key(): [det]})
    assert (200.0, 900.0, 600.0, 930.0) in seen["blockers"]                   # the cell's beam stroke
    assert any(abs(b[0] - 232) < 40 for b in seen["blockers"][1:])           # the detector's other box in the cell
    assert seen["heads"] and len(seen["heads"]) == 1                          # the cell's notehead box, so the hook count stops at its head
