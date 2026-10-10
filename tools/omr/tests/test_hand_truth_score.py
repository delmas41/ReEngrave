"""ROADMAP 1.7, plan D1 + D2: the hand-truth scorer and its controls.

SYNTHETIC page, synthetic record: nothing here reads a score PDF, a weights file or the library, so
this file stays in the fast tier (CLAUDE.md §6c).

Rule 7: a control that has only ever passed has proved nothing. ``TestEachControlCanFail`` seeds the
bug each control exists to catch into the scorer (an owner comparison that always says "right", a
matcher that matches nothing, a frame check that never trips ...) and requires the control to go RED.
Every refusal sits beside a positive control of its own class.
"""
from __future__ import annotations

import json

import pytest

from tools.omr.hand_truth import score as S
from tools.omr.hand_truth import score_controls as C
from tools.omr.hand_truth.store import ALL_INK_PASS, Box, Cell, PageTruth
from tools.omr.staged import readout as RO

SP = 20.0           # staff space, px
STAVES = 3
BARS = 3
BAR_W = 400.0
TOP0, STAFF_STRIDE = 300.0, 300.0


def _top(staff: int) -> float:
    return TOP0 + staff * STAFF_STRIDE


def synth_truth(*, sean_owners: bool = False, all_ink: bool = True, cautionary: bool = False) -> PageTruth:
    """3 staves x 3 bars, system 0. Per bar four heads (two drawn, two confirmed pre-fills) plus a stem,
    a slur and a far head with a ledger line; bar 0 carries the header (clef, 3 flats, 6/8)."""
    page = PageTruth(edition="synthetic", pdf_page_index=0, dpi=600, width=2000, height=1500)
    n = 0

    def box(cls, rect, origin, cell, owner=None, pos=None):
        nonlocal n
        b = Box(id=f"b{n}", cls=cls, rect=tuple(float(v) for v in rect), origin=origin, labeler="sean",
                cell_id=cell, owner_staff=owner, staff_position=pos)
        n += 1
        page.boxes.append(b)

    for st in range(STAVES):
        top = _top(st)
        for m in range(BARS):
            x0 = 100.0 + m * BAR_W
            cid = f"s0-st{st}-m{m}"
            rect = (x0, top - 4 * SP, x0 + BAR_W, top + 8 * SP)
            page.cells.append(Cell(id=cid, kind="measure", rect=rect, canonical_w=int(BAR_W),
                                   canonical_h=int(12 * SP), system=0, staff=st, measure=m,
                                   staff_line_ys=[4 * SP + i * SP for i in range(5)],
                                   inspected=[ALL_INK_PASS] if all_ink else []))
            for k, pos in enumerate((1, 3, 5, 7)):  # half-steps down from the top line
                x = x0 + 120 + 60 * k
                cy = top + pos * SP / 2
                origin = "drawn" if k < 2 else "prefill-confirmed"
                owner = (0, st) if sean_owners else None
                sp_mid = (4 - pos) if sean_owners else None  # steps from the middle line, up positive
                box("noteheadBlackInSpace" if pos % 2 else "noteheadBlackOnLine",
                    (x - 12, cy - 10, x + 12, cy + 10), origin, cid, owner, sp_mid)
            # a DOWN stem stands at the LEFT edge of its head (CLAUDE.md §10), so the stem control's truth direction is
            # judged: the head box is x0+108..132 and this stem's centre is left of the head's
            box("stem", (x0 + 105, top + 5, x0 + 109, top + 70), "prefill-confirmed", cid)
            box("slur", (x0 + 100, top - 30, x0 + 300, top - 5), "drawn", cid)
            # a far head: 3 staff spaces above the top line, with its ledger lines
            box("noteheadBlackOnLine", (x0 + 330, top - 3 * SP - 10, x0 + 354, top - 3 * SP + 10), "drawn", cid)
            for r in (1, 2, 3):  # the rung chain from the staff to the head, which sits on the third
                box("ledgerLine", (x0 + 322, top - r * SP - 2, x0 + 362, top - r * SP + 2), "drawn", cid)
        if cautionary:  # the sliver after the final barline: 3 spaces wide, holding a cautionary 9/8
            x0 = 100.0 + BARS * BAR_W
            cid = f"s0-st{st}-m{BARS}"
            page.cells.append(Cell(id=cid, kind="measure", rect=(x0, top - 4 * SP, x0 + 3 * SP, top + 8 * SP),
                                   canonical_w=int(3 * SP), canonical_h=int(12 * SP), system=0, staff=st,
                                   measure=BARS, staff_line_ys=[4 * SP + i * SP for i in range(5)],
                                   inspected=[ALL_INK_PASS]))
            box("timeSig9", (x0 + 8, top + 2, x0 + 28, top + 2 * SP - 2), "prefill-confirmed", cid)
            box("timeSig8", (x0 + 8, top + 2 * SP + 2, x0 + 28, top + 4 * SP - 2), "prefill-confirmed", cid)
        # the header, bar 0
        c0 = f"s0-st{st}-m0"
        box("clefG" if st < 2 else "clefF", (110, top + 5, 150, top + 70), "prefill-confirmed", c0)
        for j in range(3):
            box("keyFlat", (160 + 14 * j, top + (1 + j) * SP / 2 - 12, 172 + 14 * j, top + (1 + j) * SP / 2 + 12),
                "prefill-confirmed", c0)
        box("timeSig6", (220, top + 2, 240, top + 2 * SP - 2), "prefill-confirmed", c0)
        box("timeSig8", (220, top + 2 * SP + 2, 240, top + 4 * SP - 2), "prefill-confirmed", c0)
    page.validate()
    return page


@pytest.fixture(scope="module")
def page() -> PageTruth:
    return synth_truth()


@pytest.fixture(scope="module")
def items(page):
    return S.truth_items(page, derive=True)


def record_for(page, items, **kw) -> RO.Run:
    return C.run_of(C.synthetic_result(page, items, **kw))


# ─────────────────────────────────────────────────────────────────────────────
# the scorer
# ─────────────────────────────────────────────────────────────────────────────


class TestSelfScore:
    def test_the_truth_against_itself_is_perfect(self, page, items):
        rep = S.score(page, record_for(page, items), derive=True, items=items, trained_cells=())
        for fam, d in rep["families"].items():
            assert d["status"] == "scored"
            for view in ("gather", "adjudicate"):
                assert d[view]["recall"] == 1.0, (fam, view)
                assert d[view]["precision"] == 1.0, (fam, view)
        n = rep["noteheads"]["all"]
        assert n["matched"] == n["truth_noteheads"] == STAVES * BARS * 5
        assert rep["frame_control"]["ok"], rep["frame_control"]["reasons"]
        assert rep["headers"]["summary"]["clef"] == {"right": 3, "accuracy_of_judged": 1.0}
        assert rep["headers"]["summary"]["key"]["right"] == 3
        assert rep["headers"]["summary"]["meter"]["right"] == 3

    def test_owner_and_position_without_derive_are_no_truth_not_wrong(self, page):
        its = S.truth_items(page, derive=False)
        rep = S.score(page, record_for(page, S.truth_items(page, derive=True)), items=its, trained_cells=())
        n = rep["noteheads"]["all"]
        assert n["owner"]["no_truth"] == n["matched"] and n["owner"]["wrong"] == 0
        assert n["position"]["no_truth"] == n["matched"]
        assert n["owner"]["accuracy_of_judged"] is None  # nothing judged: a rate of None, never 0.0

    def test_derived_reference_is_labelled_and_leaves_far_heads_unjudged(self, page, items):
        rep = S.score(page, record_for(page, items), derive=True, items=items, trained_cells=())
        n = rep["noteheads"]["all"]
        # in-staff heads from the staff lines; the far head from Sean's ledger-line box under it
        assert n["owner_truth_source"] == {"derived:staff": 4 * STAVES * BARS, "derived:ledger": STAVES * BARS}
        assert n["owner"]["no_truth"] == 0
        assert n["owner"]["right"] == 5 * STAVES * BARS

    def test_a_far_head_with_no_ledger_box_stays_unlabeled_and_is_not_guessed(self):
        pg = synth_truth()
        pg.boxes = [b for b in pg.boxes if b.cls != "ledgerLine"]
        its = S.truth_items(pg, derive=True)
        rep = S.score(pg, record_for(pg, its), derive=True, items=its, trained_cells=())
        n = rep["noteheads"]["all"]
        assert n["owner"]["no_truth"] == STAVES * BARS and n["owner"]["wrong"] == 0
        assert n["owner_truth_source"].get("derived:ledger") is None

    def test_seans_labels_outrank_the_derived_reference_and_are_named_sean(self):
        pg = synth_truth(sean_owners=True)
        its = S.truth_items(pg, derive=True)
        rep = S.score(pg, record_for(pg, its), derive=True, items=its, trained_cells=())
        n = rep["noteheads"]["all"]
        assert n["owner_truth_source"].get("sean") == 4 * STAVES * BARS
        assert n["position_truth_source"].get("sean") == 4 * STAVES * BARS
        assert n["owner"]["wrong"] == 0 and n["position"]["wrong"] == 0
        assert rep["scope"]["owner_or_position_written_by_sean"] == 4 * STAVES * BARS


class TestScope:
    def test_an_unlabeled_cell_is_unscored_never_a_miss_or_a_false_positive(self):
        pg = synth_truth()
        pg.cells[0].inspected = []
        its = S.truth_items(pg, derive=True)
        # the record reads the unlabeled cell's boxes too (the detector fires everywhere)
        rep = S.score(pg, record_for(pg, its), derive=True, items=its, trained_cells=())
        nh = rep["families"]["notehead"]
        assert nh["gather"]["recall"] == 1.0 and nh["gather"]["precision"] == 1.0
        assert nh["unscored_truth_boxes"] > 0 and nh["unscored_read_boxes"] > 0
        assert rep["scope"]["cells_fully_labeled"] == len(pg.cells) - 1

    def test_positive_control_the_same_cell_counts_once_it_is_inspected(self):
        pg = synth_truth()
        its = S.truth_items(pg, derive=True)
        rep = S.score(pg, record_for(pg, its), derive=True, items=its, trained_cells=())
        assert rep["families"]["notehead"]["unscored_truth_boxes"] == 0

    def test_a_family_no_cell_was_inspected_for_is_refused_not_zero(self):
        pg = synth_truth()
        for c in pg.cells:
            c.inspected = ["slur"]
        its = S.truth_items(pg, derive=True)
        rep = S.score(pg, record_for(pg, its), derive=True, items=its, trained_cells=())
        assert rep["families"]["notehead"]["status"].startswith("REFUSED")
        assert "recall" not in rep["families"]["notehead"]
        assert rep["families"]["slur"]["status"] == "scored"  # positive control: the inspected family scores

    def test_trained_cells_are_reported_apart(self, page, items):
        trained = ["s0-st0-m0", "s0-st1-m1"]
        rep = S.score(page, record_for(page, items), derive=True, items=items, trained_cells=trained)
        n = rep["noteheads"]
        assert n["trained_cells"]["truth_noteheads"] > 0
        assert (n["trained_cells"]["truth_noteheads"] + n["not_trained_cells"]["truth_noteheads"]
                == n["all"]["truth_noteheads"])
        none = S.score(page, record_for(page, items), derive=True, items=items, trained_cells=())
        assert none["noteheads"]["trained_cells"]["truth_noteheads"] == 0  # an empty side is reported, not hidden

    def test_split_is_not_applied_to_weights_that_are_not_production(self, tmp_path, page):
        inv = tmp_path / "INVENTORY.json"
        inv.write_text(json.dumps({"production_scan_weights": "prod.pt",
                                   "held_out_cells_trained_by_production": {"synthetic:0": ["s0-st0-m0"]}}))
        cells, why = S.trained_cells_for(page, "/x/other.pt", inv)
        assert cells == [] and "not the production" in why
        cells, why = S.trained_cells_for(page, "/x/prod.pt", inv)  # positive control
        assert cells == ["s0-st0-m0"]


class TestMatching:
    def test_the_matcher_is_readouts_own(self, page, items, monkeypatch):
        calls = []
        real = RO.match_glyphs
        monkeypatch.setattr(RO, "match_glyphs", lambda *a, **k: (calls.append(1), real(*a, **k))[1])
        S.score(page, record_for(page, items), derive=True, items=items, trained_cells=())
        assert calls, "the scorer must match through readout.match_glyphs"

    def test_a_wrong_owner_is_wrong_not_a_miss(self, page, items):
        rep = S.score(page, record_for(page, items), derive=True,
                      items=C.shifted_owner_items(items, 1), trained_cells=())
        n = rep["noteheads"]["all"]
        assert n["missed"] == 0 and n["owner"]["wrong"] > 0 and n["owner"]["right"] == 0

    def test_a_head_filed_on_the_wrong_staff_is_wrong_if_uncontested_and_lost_if_given_away(self, page, items):
        heads = [it for it in items if it.family == "notehead" and it.derived_how == "staff"]
        a, b = heads[0], heads[1]
        # a: filed on staff 2 WITH a verdict naming its true owner -> that copy is GIVEN AWAY (dropped by
        #    ADJUDICATE; the winner's copy is not in this record), so the head is lost, not wrong.
        # b: filed on staff 2 and nobody contested it -> it stays there, and the owner is WRONG.
        refile = {a.idx: (2, True), b.idx: (2, False)}
        rep = S.score(page, record_for(page, items, refile=refile), derive=True, items=items, trained_cells=())
        rows = {r["truth_id"]: r for r in rep["noteheads"]["_rows"]}
        assert rows[a.id]["match"] == "missed_at_adjudicate"
        assert rows[b.id]["owner"] == "wrong" and rows[b.id]["owner_outcome"] == "uncontested"
        assert rep["families"]["notehead"]["lost_by_adjudicate"] == 1
        basis = rep["noteheads"]["all"]["owner_read_basis"]
        assert basis.get("decided", 0) == 0 and basis["uncontested"] == len(heads) + STAVES * BARS - 1

    def test_an_abstained_owner_is_abstained_never_the_filed_staff(self, page, items):
        run = record_for(page, items)
        g = next(x for x in S.read_glyphs(run, 0) if x.family == "notehead")
        rows = run.by_subject[g.key]
        from tools.omr.staged.record import Q as QQ
        rows.append(("ADJUDICATE", "verdict", {"id": "vrd:x", "subject": g.key, "quantity": QQ.GLYPH_OWNER,
                                               "outcome": "abstained", "value": None, "reason": "far_no_rungs",
                                               "decider": "adjudicate_glyph_owner"}))
        rep = S.score(page, run, derive=True, items=items, trained_cells=())
        assert rep["noteheads"]["all"]["owner"]["abstained"] == 1
        assert rep["noteheads"]["all"]["owner"]["wrong"] == 0

    def test_position_one_step_off_is_wrong_with_its_delta(self, page, items):
        rep = S.score(page, record_for(page, items, position_shift=1), derive=True, items=items,
                      trained_cells=())
        p = rep["noteheads"]["all"]["position"]
        assert p["right"] == 0 and p["wrong"] == 5 * STAVES * BARS
        assert rep["noteheads"]["all"]["position_delta_read_minus_truth"] == {"1": 5 * STAVES * BARS}

    def test_extra_boxes_are_split_into_duplicate_other_family_and_spurious(self, page, items):
        c = page.cells[0]
        anchor = next(it for it in items if it.family == "notehead" and it.cell_id == c.id)
        x0, y0, x1, y1 = anchor.rect
        spurious = [("noteheadBlackInSpace", (x0 + 1, y0 + 1, x1 + 1, y1 + 1), 0, 0, 0),   # a duplicate
                    ("noteheadBlackInSpace", (c.rect[0] + 5, c.rect[1] + 2, c.rect[0] + 20, c.rect[1] + 14), 0, 0, 0)]
        rep = S.score(page, record_for(page, items, spurious=spurious), derive=True, items=items,
                      trained_cells=())
        why = rep["families"]["notehead"]["gather"]["unmatched_read_because"]
        assert why.get("duplicate") == 1 and why.get("spurious") == 1
        v = rep["families"]["notehead"]["gather"]
        assert v["precision_without_duplicates"] > v["precision"]

    def test_classes_the_truth_has_and_the_detector_never_produced(self, page, items):
        pruned = [it for it in items if it.cls != "stem"]
        rep = S.score(page, record_for(page, pruned), derive=True, items=items, trained_cells=())
        assert "stem" in rep["classes"]["truth_classes_the_detector_never_produced"]
        assert "noteheadBlackInSpace" not in rep["classes"]["truth_classes_the_detector_never_produced"]  # positive control

    def test_prefill_confirmed_and_drawn_recall_are_reported_apart(self, page, items):
        drawn = {it.idx for it in items if it.origin == "drawn" and it.family == "notehead"}
        rep = S.score(page, record_for(page, items, drop=drawn), derive=True, items=items, trained_cells=())
        by = rep["families"]["notehead"]["gather"]["recall_by_origin"]
        assert by["drawn"]["recall"] == 0.0 and by["prefill-confirmed"]["recall"] == 1.0

    def test_commonest_misses_are_ranked_with_an_example_cell(self, page, items):
        stems = {it.idx for it in items if it.cls == "stem"}
        rep = S.score(page, record_for(page, items, drop=stems), derive=True, items=items, trained_cells=())
        kinds = S.miss_kinds(rep)
        assert kinds[0]["truth_class"] == "stem" and kinds[0]["count"] == STAVES * BARS
        assert kinds[0]["example_cell"].startswith("s0-st")


class TestHeaders:
    def test_header_is_read_from_the_first_fully_labeled_cell_only(self):
        pg = synth_truth()
        pg.cells[0].inspected = []  # staff 0's first cell
        its = S.truth_items(pg, derive=True)
        t = S.truth_header(pg, its, 0, 0)
        assert t["scored"] is False  # NOT "no clef printed"
        t1 = S.truth_header(pg, its, 0, 1)
        assert t1["scored"] and t1["clef"] == "treble" and t1["key_fifths"] == -3
        assert t1["meter"]["numerator"] == 6 and t1["meter"]["denominator"] == 8

    def test_a_meter_with_no_digits_in_a_labeled_cell_is_no_truth_not_right(self):
        assert S.judge_meter({"outcome": "decided", "numerator": 4, "denominator": 4}, {"printed": False}) \
            == "no_truth"
        assert S.judge_meter({"outcome": "decided", "numerator": 6, "denominator": 8},
                             {"printed": True, "numerator": 6, "denominator": 8}) == "right"  # positive control

    def test_abstained_is_not_wrong(self):
        assert S.judge_clef({"outcome": "abstained", "value": None}, "treble") == "abstained"
        assert S.judge_key({"outcome": "none", "value": None}, -3) == "abstained"


class TestArcsAndStaffLines:
    def test_adjudicate_view_uses_the_arc_kind_not_the_detectors_first_guess(self, page, items):
        run = record_for(page, items)
        slur = next(g for g in S.read_glyphs(run, 0) if g.family == "slur")
        from tools.omr.staged.record import Q as QQ
        run.by_subject[slur.key].append(("ADJUDICATE", "verdict", {
            "id": "vrd:arc", "subject": slur.key, "quantity": QQ.ARC_KIND, "outcome": "decided",
            "value": "tie", "reason": "x", "decider": "adjudicate_arc_kind"}))
        rep = S.score(page, run, derive=True, items=items, trained_cells=())
        sl = rep["families"]["slur"]
        assert sl["gather"]["recall"] == 1.0          # the detector said slur, and the truth says slur
        assert sl["adjudicate"]["recall"] < 1.0       # ADJUDICATE called one a tie

    def test_staff_lines_are_not_scored_against_a_truth_that_does_not_box_them(self, page, items):
        spur = [("staff", (110.0, 330.0, 150.0, 336.0), 0, 0, 0)]
        rep = S.score(page, record_for(page, items, spurious=spur), derive=True, items=items, trained_cells=())
        assert rep["families"]["staff_line"]["status"].startswith("NOT SCORED")
        assert "precision" not in rep["families"]["staff_line"]


class TestCautionaryMeter:
    def test_a_cautionary_meter_in_the_sliver_after_the_last_barline_is_scored_apart_from_bar_0(self):
        pg = synth_truth(cautionary=True)
        its = S.truth_items(pg, derive=True)
        t = S.truth_header(pg, its, 0, 0)
        assert t["cautionary"]["scored"] and t["cautionary"]["meter"]["raw"] == "9/8"
        assert t["meter"]["raw"] == "6/8"  # bar 0's own meter is untouched
        rep = S.score(pg, record_for(pg, its), derive=True, items=its, trained_cells=())
        assert rep["headers"]["summary"]["cautionary"]["right"] == STAVES
        assert rep["headers"]["summary"]["meter"]["right"] == STAVES

    def test_a_record_reading_the_wrong_cautionary_is_wrong_and_a_full_width_last_cell_is_unscored(self):
        pg = synth_truth(cautionary=True)
        its = S.truth_items(pg, derive=True)
        rep = S.score(pg, record_for(pg, its, header_wrong=True), derive=True, items=its, trained_cells=())
        assert rep["headers"]["summary"]["cautionary"]["wrong"] == STAVES
        plain = synth_truth()  # positive control: no sliver, the last cell holds a bar -> not scored, not "none"
        t = S.truth_header(plain, S.truth_items(plain, derive=True), 0, 0)
        assert t["cautionary"]["scored"] is False


class TestFrameControl:
    def test_a_record_in_another_frame_is_refused_and_the_cli_exits_3(self, page, items, tmp_path):
        sp = 20.0
        bad = C.synthetic_result(page, items, dy=0.35 * sp)
        rec = tmp_path / "bad.record.json"
        rec.write_text(json.dumps(bad))
        pg = tmp_path / "0.json"
        pg.write_text(json.dumps(page.to_json()))
        assert S.main(["--page", str(pg), "--record", str(rec), "--derive"]) == 3
        good = tmp_path / "good.record.json"  # positive control: the same record unshifted passes
        good.write_text(json.dumps(C.synthetic_result(page, items)))
        assert S.main(["--page", str(pg), "--record", str(good), "--derive"]) == 0
        assert S.main(["--page", str(pg), "--record", str(rec), "--derive", "--force"]) == 0

    def test_the_cli_writes_a_json_report(self, page, items, tmp_path):
        rec, pg, out = tmp_path / "r.json", tmp_path / "0.json", tmp_path / "rep.json"
        rec.write_text(json.dumps(C.synthetic_result(page, items)))
        pg.write_text(json.dumps(page.to_json()))
        assert S.main(["--page", str(pg), "--record", str(rec), "--derive", "--out", str(out)]) == 0
        d = json.loads(out.read_text())
        assert d["families"]["notehead"]["status"] == "scored" and "miss_kinds" in d


# ─────────────────────────────────────────────────────────────────────────────
# D2: the controls pass on the clean scorer ...
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("control", C.CONTROLS, ids=lambda c: c.__name__)
def test_each_control_passes_on_the_clean_scorer(control, page):
    res = control(page, True)
    assert res["passes"], json.dumps(res, default=str)


# ... and each goes RED when the bug it exists to catch is seeded in (rule 7).


class TestEachControlCanFail:
    def red(self, control, page):
        res = control(page, True)
        assert not res["passes"], f"{control.__name__} stayed GREEN with the bug seeded: {res}"

    def test_owner_always_right_is_caught_by_the_owner_shift(self, page, monkeypatch):
        monkeypatch.setattr(S, "_same_owner", lambda a, b: True)
        self.red(C.control_owner_shift, page)

    def test_owner_always_wrong_is_caught_by_the_self_score(self, page, monkeypatch):
        monkeypatch.setattr(S, "_same_owner", lambda a, b: False)
        self.red(C.control_self_score, page)

    def test_position_always_right_is_caught_by_the_position_shift(self, page, monkeypatch):
        monkeypatch.setattr(S, "_same_position", lambda a, b: True)
        self.red(C.control_position_shift, page)

    def test_position_always_wrong_is_caught_by_the_self_score(self, page, monkeypatch):
        monkeypatch.setattr(S, "_same_position", lambda a, b: False)
        self.red(C.control_self_score, page)

    def test_a_matcher_that_matches_nothing_is_caught_by_the_self_score(self, page, monkeypatch):
        def nothing(truth, read, **_):
            return {}, sorted(t[0] for t in truth), sorted(r[0] for r in read)
        monkeypatch.setattr(S, "match_boxes", nothing)
        self.red(C.control_self_score, page)

    def test_a_matcher_that_pairs_by_order_is_caught_by_the_displaced_record(self, page, monkeypatch):
        def by_order(truth, read, **_):
            k = min(len(truth), len(read))
            pairs = {truth[i][0]: (read[i][0], 1.0) for i in range(k)}
            return pairs, sorted(t[0] for t in truth[k:]), sorted(r[0] for r in read[k:])
        monkeypatch.setattr(S, "match_boxes", by_order)
        # the self-score cannot tell: a record in truth order IS paired by order. That is why it is not
        # the control for this bug.
        assert C.control_self_score(page, True)["passes"]
        self.red(C.control_no_overlap_no_match, page)

    def test_a_frame_check_that_never_trips_is_caught(self, page, monkeypatch):
        real = S.frame_control
        monkeypatch.setattr(S, "frame_control", lambda *a, **k: S.FrameVerdict(True, [], real(*a, **k).detail))
        self.red(C.control_frame, page)

    def test_a_scorer_that_ignores_the_record_header_is_caught(self, page, monkeypatch):
        monkeypatch.setattr(S, "judge_clef", lambda read, truth: "right")
        monkeypatch.setattr(S, "judge_key", lambda read, truth: "right")
        monkeypatch.setattr(S, "judge_meter", lambda read, truth: "right")
        self.red(C.control_header_wrong, page)

    def test_rates_that_are_always_one_are_caught_by_drop_and_add(self, page, monkeypatch):
        monkeypatch.setattr(S, "_rate", lambda n, d: 1.0)
        self.red(C.control_drop_and_add, page)

    def test_a_scope_that_inspects_everything_is_caught_by_the_refusal_control(self, page, monkeypatch):
        monkeypatch.setattr(S, "cells_inspected_for", lambda pg, fam: list(pg.cells))
        self.red(C.control_refusal, page)

    def test_positive_control_the_unseeded_scorer_is_green_on_all_of_them(self, page):
        assert all(r["passes"] for r in C.run_controls(page, True))


def test_the_displacement_the_control_uses_lands_no_box_on_another(items):
    """The first version used a fixed 8-space shift and FAILED on the real page: it dropped heads onto their
    neighbours. The shift is now searched, and verified here independently of the matcher."""
    dx, dy = C.clear_displacement(items, SP)
    assert (dx, dy) != (0, 0)
    heads = [it for it in items if it.family == "notehead"]
    assert not any(S._iou((a.rect[0] + dx, a.rect[1] + dy, a.rect[2] + dx, a.rect[3] + dy), b.rect) >= S.MIN_IOU
                   for a in heads for b in heads)
    # positive control of the same class: a shift of zero DOES land every box on itself
    assert any(S._iou(a.rect, a.rect) >= S.MIN_IOU for a in heads)


def test_controls_cli_exits_zero_on_a_clean_page(page, tmp_path):
    pg = tmp_path / "0.json"
    pg.write_text(json.dumps(page.to_json()))
    assert S.main(["--page", str(pg), "--controls", "--derive"]) == 0
