"""ROADMAP 2.107 -- dynamic letters the detector never boxed are READ.

Sean, 2026-10-13: *"sf should be read as a dynamic - it is letters"*; *"we added
a whole library of text to be checked"*. Case: `out/print/2.90-review` tile 9
(Litolff pdf page 2, system 1, flute staff, bar 7): the `f` of an `sf` boxed
`noteheadBlackOnLine`, the `s` as two `rest16th`, no dynamic box.

STAGED. GATHER reads (`gather.gather_letter_look`, `letter_look`), ADJUDICATE
refuses the head/rest boxes whose ink the letters are (`adjudicators.
letter_cover`), the 2.68 machinery spells and EXPORT writes.

RED on the unrepaired tree (origin/main f2ed5a68) for the plain reason that
`staged.letter_look`, `Q.LETTER_LOOK_COVER`, `READERS.LETTER_LOOK`,
`gather_letter_look` and `adjudicators.letter_cover` do not exist there: every
test below fails at import.

The detector is SCRIPTED (`_FakeModel`): it reports a letter wherever the ink
the look hands it has the shape the scenario says, so these tests pin the
reader's GATING -- the vote, the library, the controls -- not the model's eyes.
The model's eyes are measured on the real page (FINDINGS 2.107).

CONTROLS THAT CAN FAIL, each beside the case it guards:
  * a string the library does not hold is not a dynamic (`fs`, `pppp`);
  * a letter drawn from fragments is not read by a weak vote (`m` at 0.514 on
    five looks -- the first build's `mf` for Sean's `sf`);
  * a real note / real rest beside a dynamic has no cover row and stays;
  * a dynamic the detector already boxed is not doubled;
  * an unread letter beside a read one NARROWS, it never guesses.
"""
from __future__ import annotations

from types import SimpleNamespace

import cv2
import numpy as np
import pytest

from tools.omr.staged import gather as G
from tools.omr.staged import letter_look as LL
from tools.omr.staged import record as R
from tools.omr.staged.adjudicators import letter_cover as LC
from tools.omr.staged.record import Log, Q, READERS

SP = 16.0


# ── the library is the vocabulary ───────────────────────────────────────────

@pytest.mark.parametrize("text", ["f", "ff", "fff", "p", "pp", "ppp", "mf", "mp",
                                  "sf", "sfz", "sffz", "fz", "rfz", "fp", "sfp"])
def test_the_library_holds_the_dynamics_the_issue_names(text):
    assert LL.library_dynamic(text), text


@pytest.mark.parametrize("text", ["s", "z", "m", "r", "fs", "sm", "pf", "x",
                                  "pppp", "ffff", "sfpp", ""])
def test_a_string_the_library_does_not_hold_is_not_a_dynamic(text):
    """`pppp`/`ffff`/`sfpp` are NOT in the 1,760-term export: the reader says so
    rather than reaching for a typed list. A lone `s` is no dynamic either."""
    assert LL.library_dynamic(text) is None, text


# ── ink: the staff lines come out, the strokes that cross them stay ─────────

def _staff_page(w=240, h=200):
    img = np.zeros((h, w), np.uint8)
    for k in range(5):
        y = 60 + int(SP * k)
        img[y:y + 3, :] = 255
    return img


def _stroke(img, x0, y0, x1, y1, t=5):
    n = int(max(abs(x1 - x0), abs(y1 - y0)))
    for i in range(n + 1):
        x = int(round(x0 + (x1 - x0) * i / max(1, n)))
        y = int(round(y0 + (y1 - y0) * i / max(1, n)))
        img[y - t // 2:y + t // 2 + 1, x - t // 2:x + t // 2 + 1] = 255


def test_erasing_the_staff_keeps_a_stroke_that_crosses_it():
    img = _staff_page()
    _stroke(img, 100, 50, 100, 140)            # a vertical stroke across 4 lines
    clean = LL.erase_staff_lines(img, SP)
    assert clean[60:75, 100].any(), "the crossing stroke must survive the erase"
    assert not clean[61, 20:60].any(), "the line itself must be gone"


def test_erasing_the_staff_leaves_no_line_to_be_read_as_ink():
    """Negative control for the one above: with NO stroke the staff erases to
    nothing at all, so a group can never be seeded from a line."""
    assert not LL.erase_staff_lines(_staff_page(), SP).any()


# ── the vote ────────────────────────────────────────────────────────────────

def _hyps(cls, conf, scales, box=(10, 10, 40, 50)):
    return [LL.Hypothesis(cls, conf, box, s) for s in scales]


def test_a_letter_seen_strongly_on_enough_looks_is_read():
    regs = LL.regions_from(_hyps("dynamicF", 0.88, LL.LOOK_SCALES))
    assert [(r.how, r.letters) for r in regs] == [("read", ("f",))]


def test_the_first_builds_mf_for_an_sf_is_not_read():
    """Sean's `sf` (2.90 tile 9): the broken `s` was voted `m` at 0.514 on five
    looks and read as `mf`. Under the strong bar it is a weak region."""
    regs = LL.regions_from(_hyps("dynamicM", 0.514, LL.LOOK_SCALES))
    assert [r.how for r in regs] == ["weak"]
    regs = LL.regions_from(_hyps("dynamicF", 0.88, LL.LOOK_SCALES[:3]))
    assert [r.how for r in regs] == ["weak"], "three looks are not enough"


def test_two_overlapping_boxes_of_one_class_at_each_scale_are_two_letters():
    """Sean's tile 8 (Brahms `ff`): the two `f` boxes overlap at IoU ~0.41 and
    voted as ONE. Two confident same-class boxes at one scale, on >= 3 scales,
    are two letters. CONTROL: one `p` whose single box wanders across scales is
    one letter."""
    a, b = (0, 0, 72, 70), (30, 0, 102, 70)
    hyps = [LL.Hypothesis("dynamicF", 0.85, box, s)
            for s in LL.LOOK_SCALES for box in (a, b)]
    assert [r.letters for r in LL.regions_from(hyps)] == [("f",), ("f",)]
    wander = [LL.Hypothesis("dynamicP", 0.85, (0, 0, 60 + 3 * i, 70), s)
              for i, s in enumerate(LL.LOOK_SCALES)]
    assert len(LL.regions_from(wander)) == 1


# ── the spelling is the library's ───────────────────────────────────────────

def _region(letters, how="read", box=(0, 0, 10, 10), conf=0.9, looks=5):
    return LL.Region(box=box, letters=tuple(letters), how=how, conf=conf,
                     scales_seen=looks)


def test_two_read_letters_spell_a_library_dynamic():
    sp = LL.spell([_region("s", box=(0, 0, 10, 10)),
                   _region("f", box=(12, 0, 24, 10))])
    assert (sp.status, sp.text) == ("spelled", "sf")


def test_letters_the_library_does_not_spell_are_rejected_with_what_was_tried():
    sp = LL.spell([_region("f", box=(0, 0, 10, 10)),
                   _region("s", box=(12, 0, 24, 10))])
    assert sp.status == "rejected" and sp.reason == "not_in_library"
    assert sp.tried == ("fs",)


def test_an_unread_letter_before_an_f_narrows_it_never_guesses():
    """A slot that no vote named is any letter; what the library completes is
    the candidate set, and the dynamic is NARROWED."""
    sp = LL.spell([_region("", how="unread", box=(0, 0, 10, 10), conf=0.0, looks=0),
                   _region("f", box=(12, 0, 24, 10))])
    assert sp.status == "narrowed"
    assert set(sp.candidates) == {"ff", "mf", "rf", "sf"}
    assert sp.text is None


def test_no_read_letter_no_dynamic():
    assert LL.spell([]).status == "rejected"
    assert LL.spell([_region("", how="unread")]).status == "rejected"


# ── the scripted model ──────────────────────────────────────────────────────

class _FakeModel:
    """Stands in for `YoloDetector.detect_image`. For the ink it is handed it
    returns the scripted letters: `(class, conf, x0_frac, x1_frac)` slices of the
    ink's own width, whatever the scale. Anything it is not told to see it does
    not see."""

    def __init__(self, letters, rival=None):
        self.letters = letters
        self.rival = rival
        self.calls = 0

    def __call__(self, img, imgsz):
        self.calls += 1
        gray = img if img.ndim == 2 else cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        ys, xs = np.nonzero(gray < 128)
        if not len(xs):
            return []
        x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
        w = x1 - x0
        out = [(cls, conf, (x0 + w * a, y0, x0 + w * b, y1))
               for cls, conf, a, b in self.letters]
        if self.rival:
            out.append((self.rival[0], self.rival[1], (x0, y0, x1, y1)))
        return out


def _sf_ink():
    """The ink of an `sf` on a staff: an `s` (two strokes) left of an `f` (a
    stem across three lines, a hook, a crossbar), all letter-sized."""
    img = _staff_page()
    _stroke(img, 110, 70, 110, 85)                  # the s, as three strokes
    _stroke(img, 110, 70, 120, 70)
    _stroke(img, 110, 85, 120, 85)
    _stroke(img, 128, 100, 136, 60)                 # the f's stem, 2.5 spaces
    return img


def _members():
    # (id, page box): the head the detector boxed on the f, a 16th rest on the s
    return {"head": (124.0, 52.0, 146.0, 90.0), "rest": (106.0, 66.0, 124.0, 90.0)}


def _clean_and_groups(img, members):
    clean = LL.erase_staff_lines(img, SP)
    groups = LL.find_groups(clean, list(members.items()), SP)
    return clean, groups


def test_a_group_is_made_of_letter_sized_pieces_and_a_note_is_not_one():
    """CONTROL: a note with its stem is taller than any letter, so it seeds no
    group at all -- a real note beside a dynamic is never read."""
    img = _staff_page()
    _stroke(img, 60, 130, 60, 60, t=4)              # a stem, 4.4 spaces
    cv2.circle(img, (54, 134), 8, 255, -1)          # its head
    members = {"note": (44.0, 124.0, 66.0, 144.0)}
    clean, groups = _clean_and_groups(img, members)
    assert groups == [] or all(not any(c.h > 3.4 * SP for c in g.comps)
                               for g in groups)
    seeded = [g for g in groups if "note" in g.seeds]
    assert not seeded or all(
        (g.box()[3] - g.box()[1]) <= 3.4 * SP for g in seeded)


def test_read_group_reads_an_sf_and_covers_the_boxes_on_its_ink():
    img = _sf_ink()
    members = _members()
    clean, groups = _clean_and_groups(img, members)
    assert groups, "the ink under the boxes must form a letter group"
    model = _FakeModel([("dynamicS", 0.9, 0.0, 0.4), ("dynamicF", 0.9, 0.4, 1.0)])
    gr = LL.read_page_group(clean, groups[0], members, SP, model)
    assert gr.status == "read", (gr.status, gr.reason)
    assert gr.spelling.text == "sf"
    assert gr.spelling.term == "Sforzando"
    assert set(gr.seed_ids) == {"head", "rest"}
    assert min(gr.cover) >= LC.COVER_REFUSE_SHARE, gr.cover


def test_a_group_that_draws_no_letter_costs_only_the_probe():
    """COST CONTROL (can fail): nothing letter-shaped at the two probe scales ->
    exactly the probe's calls, none of the full look's; a letter group gets the
    full look (positive control in the same class)."""
    img = _sf_ink()
    members = _members()
    clean, groups = _clean_and_groups(img, members)
    blind = _FakeModel([], rival=("rest16th", 0.8))
    gr = LL.read_page_group(clean, groups[0], members, SP, blind)
    assert gr.probe_only and blind.calls == len(LL.PROBE_SCALES)
    seeing = _FakeModel([("dynamicS", 0.9, 0.0, 0.4), ("dynamicF", 0.9, 0.4, 1.0)])
    gr = LL.read_page_group(clean, groups[0], members, SP, seeing)
    assert not gr.probe_only and seeing.calls > len(LL.PROBE_SCALES)


def test_a_look_that_sees_notes_not_letters_reads_nothing():
    """CONTROL (can fail): the SAME ink, the model scripted to see a rest."""
    img = _sf_ink()
    members = _members()
    clean, groups = _clean_and_groups(img, members)
    gr = LL.read_page_group(clean, groups[0], members, SP,
                            _FakeModel([], rival=("rest16th", 0.8)))
    assert gr.status == "rejected" and gr.reason == "no_letter_read"
    assert gr.rival == ("rest16th", 0.8)


def test_a_dynamic_the_detector_already_boxed_is_not_doubled():
    img = _sf_ink()
    members = _members()
    clean, groups = _clean_and_groups(img, members)
    ub = groups[0].box()
    model = _FakeModel([("dynamicS", 0.9, 0.0, 0.4), ("dynamicF", 0.9, 0.4, 1.0)])
    gr = LL.read_page_group(clean, groups[0], members, SP, model,
                            dynamic_boxes=[(ub[0] - 2.0, ub[1] - 2.0,
                                            ub[2] + 2.0, ub[3] + 2.0)])
    assert gr.status == "skipped" and gr.reason == "already_boxed_as_a_dynamic"


def test_a_weak_s_beside_a_strong_f_narrows_the_dynamic():
    """The 2.90 tile 9 case, as the real model sees it: the `f` read strongly,
    the `s` only as a weak `m`. Not `mf`, not `f`: NARROWED to the library's
    completions."""
    img = _sf_ink()
    members = _members()
    clean, groups = _clean_and_groups(img, members)
    model = _FakeModel([("dynamicM", 0.514, 0.0, 0.4), ("dynamicF", 0.88, 0.4, 1.0)])
    gr = LL.read_page_group(clean, groups[0], members, SP, model)
    assert gr.status == "narrowed", (gr.status, gr.reason, gr.spelling)
    assert "sf" in gr.spelling.candidates and "mf" in gr.spelling.candidates
    assert gr.spelling.text is None


def test_a_group_whose_letters_spell_nothing_in_the_library_is_rejected():
    img = _sf_ink()
    members = _members()
    clean, groups = _clean_and_groups(img, members)
    model = _FakeModel([("dynamicF", 0.9, 0.0, 0.4), ("dynamicS", 0.9, 0.4, 1.0)])
    gr = LL.read_page_group(clean, groups[0], members, SP, model)
    assert gr.status == "rejected" and gr.reason == "not_in_library"
    assert gr.spelling.tried == ("fs",)


def test_a_real_rest_beside_the_dynamic_is_not_covered():
    """CONTROL: an eighth rest well clear of the `sf` ink is no part of it."""
    img = _sf_ink()
    _stroke(img, 200, 66, 205, 84, t=4)             # a rest-like stroke, 70 px right
    members = dict(_members())
    members["real_rest"] = (194.0, 62.0, 212.0, 90.0)
    clean, groups = _clean_and_groups(img, members)
    sf_group = [g for g in groups if "head" in g.seeds][0]
    model = _FakeModel([("dynamicS", 0.9, 0.0, 0.4), ("dynamicF", 0.9, 0.4, 1.0)])
    gr = LL.read_page_group(clean, sf_group, members, SP, model)
    assert "real_rest" not in gr.seed_ids


# ── Sean's tile 8 (Brahms p5): ONE f read, the second f beside it unexplained ─

def _ff_ink(two=True):
    """Two joined f strokes (one connected piece, like the Brahms `ff`), or one."""
    img = _staff_page(w=300)
    _stroke(img, 100, 110, 112, 64)                 # first f, 2.9 spaces
    _stroke(img, 108, 64, 122, 60)
    if two:
        _stroke(img, 132, 110, 144, 64)             # second f, touching via a bar
        _stroke(img, 140, 64, 154, 60)
        _stroke(img, 112, 88, 140, 88)
    return img


def _ff_members():
    return {"head": (96.0, 56.0, 126.0, 112.0)}


def test_one_f_read_beside_unexplained_letter_ink_is_not_decided():
    """Sean, 2.107 tile 8: the look read `f` and the print is `ff`. The second f
    is letter-sized ink beside the read one on the same baseline: the dynamic
    is NARROWED with the read f fixed and the neighbour open, never `f`."""
    img = _ff_ink()
    members = _ff_members()
    clean, groups = _clean_and_groups(img, members)
    model = _FakeModel([("dynamicF", 0.9, 0.0, 0.5)])
    gr = LL.read_page_group(clean, groups[0], members, SP, model)
    assert gr.status == "narrowed", (gr.status, gr.reason, gr.spelling)
    assert gr.spelling.text is None
    assert "ff" in gr.spelling.candidates and "f" not in gr.spelling.candidates


def test_two_f_read_and_one_clean_f_stay_decided():
    """POSITIVE CONTROLS in the same class (tiles 3/5/6/9): both letters read
    -> `ff`; a single f with nothing beside it -> `f`."""
    members = _ff_members()
    clean, groups = _clean_and_groups(_ff_ink(), members)
    two = _FakeModel([("dynamicF", 0.9, 0.0, 0.5), ("dynamicF", 0.9, 0.5, 1.0)])
    gr = LL.read_page_group(clean, groups[0], members, SP, two)
    assert (gr.status, gr.spelling.text) == ("read", "ff")
    clean, groups = _clean_and_groups(_ff_ink(two=False), members)
    one = _FakeModel([("dynamicF", 0.9, 0.0, 1.0)])
    gr = LL.read_page_group(clean, groups[0], members, SP, one)
    assert (gr.status, gr.spelling.text) == ("read", "f")


# ── ADJUDICATE: one reason for a head, one for a rest ───────────────────────

def _cover(log, g, share, **detail):
    log.observe(g, Q.LETTER_LOOK_COVER, share, reader=READERS.LETTER_LOOK,
                frame="page", read_as=detail.get("read_as", "sf"),
                candidates=[], status="read", letters=["glyph/0/0/0/0/9"],
                group_box_page=[0, 0, 10, 10], library_term="Sforzando")


def _decide_head(share):
    from tools.omr.staged import adjudicate
    from tools.omr.tests.test_staged_dynamic_letter_not_a_head_2026_10_09 import _head
    from tools.omr.tests.test_staged_notehead_precision import _cell_geometry, _verdict
    log = Log()
    _cell_geometry(log)
    g = _head(log, 0)
    if share is not None:
        _cover(log, g, share)
    log.freeze()
    adjudicate._ensure_decisions()
    adjudicate.run(log, order=(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD,))
    return _verdict(log, g)


def _decide_rest(share):
    from tools.omr.staged import adjudicate
    from tools.omr.tests.test_staged_duplicate_rest import _rest_box
    log = Log()
    g = _rest_box(log, 0, "rest16th", x_c=100.0, y_c=100.0, w_c=60.0,
                  h_c=100.0, score=0.5)
    if share is not None:
        _cover(log, g, share)
    log.freeze()
    adjudicate._ensure_decisions()
    adjudicate.run(log, order=(Q.REST_IS_NOT_A_REST,))
    return log.verdict(Q.REST_IS_NOT_A_REST, g)


def test_a_head_mostly_a_read_letters_ink_is_not_a_note():
    v = _decide_head(1.0)
    assert v.value is True and v.reason == "on_a_dynamic_letter"
    assert v.detail["read_by"] == "letter_look"
    assert v.margin == pytest.approx(0.5)


def test_a_rest_mostly_a_read_letters_ink_is_not_a_rest():
    v = _decide_rest(0.93)
    assert v.value is True and v.reason == "rest_on_a_dynamic_letter"
    assert v.detail["read_by"] == "letter_look"


def test_a_head_or_rest_with_no_cover_row_stays():
    """CONTROL (can fail, same class and geometry as the refusals above): no row
    means the box is clear of every read letter."""
    assert _decide_head(None).value is False
    assert _decide_rest(None).value is False


def test_a_low_share_is_spared_and_its_signal_is_recorded():
    """CONTROL: a real note or rest touching a letter's ink: spared, with the
    margin on record for the near-miss gallery."""
    for v in (_decide_head(0.3), _decide_rest(0.3)):
        assert v.value is False
        assert v.detail["letter_look_signal"]["margin"] == pytest.approx(-0.2)


def test_the_reasons_are_declared():
    from tools.omr.staged import adjudicate
    assert "rest_on_a_dynamic_letter" in adjudicate.REGISTRY[
        Q.REST_IS_NOT_A_REST].reasons
    assert "on_a_dynamic_letter" in adjudicate.REGISTRY[
        Q.NOTEHEAD_IS_NOT_A_NOTEHEAD].reasons


# ── GATHER end to end on a synthetic page ───────────────────────────────────

PAGE_W, PAGE_H = 300, 400


class _Det:
    def __init__(self, name, category, x, y, w, h):
        self.smufl_name, self.category = name, category
        self.x_canonical, self.y_canonical = x, y
        self.width_canonical, self.height_canonical = w, h
        self.confidence = 0.4
        self.x_center, self.y_center = x + w // 2, y + h // 2


def _gathered(img, dets_spec, model, extra_dets=()):
    full = np.zeros((PAGE_H, PAGE_W), np.uint8)
    full[100:100 + img.shape[0], 20:20 + img.shape[1]] = img
    rgb = np.full((PAGE_H, PAGE_W, 3), 255, np.uint8)
    rgb[full > 0] = 0
    ys = [160, 176, 192, 208, 224]
    staff = SimpleNamespace(staff_index=0, system_index=0, line_ys=ys, top_y=160,
                            x_start=0, x_end=PAGE_W, line_thickness_px=None,
                            line_wander_px=None)
    pws = SimpleNamespace(page=SimpleNamespace(page_index=0, binary=None, rgb=rgb),
                          staves=[staff])
    cell = SimpleNamespace(staff_index=0, page_index=0, measure_index=0,
                           bbox_page_px=[0.0, 0.0, float(PAGE_W), float(PAGE_H)],
                           upscale_factor=1.0, image_no_staff=None)
    detector = SimpleNamespace(detect_image=lambda im, conf, imgsz: model(im, imgsz))
    dets = [_Det(n, c, x + 20, y + 100, w, h) for n, c, x, y, w, h in dets_spec]
    dets += list(extra_dets)
    detections = {R.cell(0, 0, 0, 0).to_key(): dets}
    log = Log()
    census = G.gather_letter_look(log, pws, [cell], {0: (0, 0)}, detections,
                                  detector=detector)
    return log, census, detections, cell


def _spec():
    return [("rest16th", "rest", 106, 66, 18, 24),
            ("noteheadBlackOnLine", "notehead", 124, 52, 22, 38)]


def test_gather_appends_the_letters_and_files_cover_on_the_boxes_they_explain():
    model = _FakeModel([("dynamicS", 0.9, 0.0, 0.4), ("dynamicF", 0.9, 0.4, 1.0)])
    log, census, detections, _cell = _gathered(_sf_ink(), _spec(), model)
    assert census["read"] == 1 and census["letters_added"] == 2, census
    dets = detections[R.cell(0, 0, 0, 0).to_key()]
    assert [d.smufl_name for d in dets[2:]] == ["dynamicS", "dynamicF"]
    for k in (2, 3):
        rows = log.rows(Q.GLYPH_BOX, R.glyph(0, 0, 0, 0, k))
        assert rows and rows[-1].reader == READERS.LETTER_LOOK
    covers = [(r.subject.to_key(), r.value) for r in log.all_rows()
              if r.quantity == Q.LETTER_LOOK_COVER
              and r.value >= LC.COVER_REFUSE_SHARE]
    assert {k for k, _v in covers} == {R.glyph(0, 0, 0, 0, 0).to_key(),
                                       R.glyph(0, 0, 0, 0, 1).to_key()}


def test_gather_files_nothing_on_a_group_it_could_not_read_but_says_why():
    """CONTROL (can fail): the same page and boxes, a model that sees a rest.
    No letter, no cover row, and an abstention carrying how close it came."""
    model = _FakeModel([], rival=("rest16th", 0.8))
    log, census, detections, _cell = _gathered(_sf_ink(), _spec(), model)
    assert census["letters_added"] == 0 and census["rejected"] == 1
    assert not [r for r in log.all_rows() if r.quantity == Q.LETTER_LOOK_COVER]
    ab = [a for a in log.refusals(Q.GLYPH_BOX, R.cell(0, 0, 0, 0))
          if a.reader == READERS.LETTER_LOOK]
    assert ab and ab[-1].detail["best_note_or_rest"] == ["rest16th", 0.8]
    assert len(detections[R.cell(0, 0, 0, 0).to_key()]) == 2


def test_gather_does_nothing_without_a_detector_that_can_look():
    log, census, _d, _c = _gathered(_sf_ink(), _spec(), _FakeModel([]))
    log2 = Log()
    assert G.gather_letter_look(log2, SimpleNamespace(page=SimpleNamespace(
        rgb=None)), [], {}, {}, detector=None)["groups"] == 0


def test_a_letter_row_is_attributed_to_the_reader_that_boxed_it():
    """`gather_dynamic_letters` must not call a letter the look read the
    production detector's: that is how a consumer would trust it blind."""
    model = _FakeModel([("dynamicS", 0.9, 0.0, 0.4), ("dynamicF", 0.9, 0.4, 1.0)])
    log, _c, detections, cell = _gathered(_sf_ink(), _spec(), model)
    page = SimpleNamespace(page_index=0)
    G.gather_dynamic_letters(log, SimpleNamespace(page=page, staves=[]), [cell],
                             {0: (0, 0)}, detections)
    rows = [r for r in log.all_rows() if r.quantity == Q.DYNAMIC_LETTER
            and r.subject.to_key() in (R.glyph(0, 0, 0, 0, 2).to_key(),
                                       R.glyph(0, 0, 0, 0, 3).to_key())]
    assert rows and all(r.reader == READERS.LETTER_LOOK for r in rows)


import pytest as _pytest_2176


@_pytest_2176.fixture(autouse=True)
def _pin_head_on_another_mark_off_2_176(monkeypatch):
    """ROADMAP 2.176 flipped OMR_HEAD_ON_ANOTHER_MARK ON; these fixtures put a head at a system's first cell, so pin it OFF here."""
    monkeypatch.setenv("OMR_HEAD_ON_ANOTHER_MARK", "0")
