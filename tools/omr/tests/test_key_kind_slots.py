"""ROADMAP 2.299: OMR_KEY_KIND_FROM_SLOTS reads the key's KIND and COUNT from where the key object's measured slots sit; nothing else."""
import pytest

from tools.omr.staged import key_kind_slots as K
from tools.omr.staged import key_object as KO

SP = 20.0


def _row(acc, n, clef="treble", h=2.7, dstep=0.0, shapes=None, more=False, gap=1.1, skip_step=None):
    """A key object whose k-th slot stands exactly where the k-th `acc` of the fixed order stands for `clef` (+ `dstep` on every slot)."""
    pcs = []
    for k in range(1, n + 1):
        e = KO.expected_step(clef, acc, k)
        off = KO.glyph_offset_steps(acc, h)
        pcs.append({"slot": k, "cx": 100.0 + (k - 1) * gap * SP, "step": None if skip_step == k else round(e - off + dstep, 2), "h": h,
                    "shape": (shapes or {}).get(k, "flat" if acc == "b" else "sharp"), "basis": "piece"})
    return {"ko": {"own_slots": n, "system_count": n, "more_than_system": more, "read_pieces": pcs}, "space": SP}


@pytest.mark.parametrize("clef", ["treble", "bass", "alto", "tenor"])
@pytest.mark.parametrize("n", [1, 2, 3, 4, 5, 6, 7])
def test_flats_are_read_as_flats_every_clef(clef, n):
    r = K.read(_row("b", n, clef), clef)
    assert (r["kind"], r["count"], r["standing"]) == ("flat", n, "READ"), r
    assert K.fifths_of(r) == -n


@pytest.mark.parametrize("clef", ["treble", "bass", "alto", "tenor"])
@pytest.mark.parametrize("n", [1, 2, 3, 4, 5, 6, 7])
def test_sharps_are_read_as_sharps_every_clef(clef, n):
    r = K.read(_row("#", n, clef), clef)
    assert (r["kind"], r["count"], r["standing"]) == ("sharp", n, "READ"), r
    assert K.fifths_of(r) == n


def test_a_crushed_bowl_alone_reads_at_its_pitch():
    # h ~1.2: the detector's box covers the bowl only; the flat's centre stands on its pitch (glyph_offset_steps -> 0)
    r = K.read(_row("b", 3, h=1.2), "treble")
    assert K.fifths_of(r) == -3


def test_flag_default_on(monkeypatch):
    monkeypatch.delenv(K.ENV, raising=False)
    assert K.enabled()
    for v in ("", "1", "true", "YES", "on"):
        monkeypatch.setenv(K.ENV, v)
        assert K.enabled()
    for v in ("0", "false", "OFF", "no"):
        monkeypatch.setenv(K.ENV, v)
        assert not K.enabled()


def test_slots_off_their_steps_abstain():
    for d in (2.5, -2.5, 4.0):
        r = K.read(_row("b", 3, dstep=d), "treble")
        assert r["standing"] is None, (d, r)
        assert K.fifths_of(r) is None


def test_a_flat_reads_anywhere_between_its_two_anchors():
    # a crushed piece covers an unknown part of the glyph: its centre is between the whole flat's (e - 1.25) and the bowl alone's (e)
    for frac in (0.0, 0.5, 1.0):
        row = _row("b", 3)
        for k, p in enumerate(row["ko"]["read_pieces"], start=1):
            e = KO.expected_step("treble", "b", k)
            p["step"] = round(e - 1.25 * frac, 2)
        assert K.fifths_of(K.read(row, "treble")) == -3, frac


def test_a_staff_that_read_fewer_than_the_system_is_not_read():
    # two crushed flats of three (or a B-flat clarinet in one): the system's count is not this staff's to supply
    row = _row("b", 2)
    row["ko"]["system_count"] = 3
    r = K.read(row, "treble")
    assert r["standing"] is None and r["why"] == "fewer_than_system"
    row["ko"]["system_count"] = None
    assert K.read(row, "treble")["why"] == "no_system_count"


def test_one_blob_counted_twice_does_not_read():
    row = _row("b", 3)
    row["ko"]["read_pieces"][2]["step"] = row["ko"]["read_pieces"][1]["step"]       # slots 2 and 3 are the same ink
    assert K.fifths_of(K.read(row, "treble")) is None


def test_a_slot_out_of_order_abstains():
    row = _row("b", 3)
    row["ko"]["read_pieces"][1]["step"] = row["ko"]["read_pieces"][2]["step"]
    r = K.read(row, "treble")
    assert r["standing"] is None


def test_the_wrong_clef_does_not_read_a_key():
    # treble flats against a bass staff: the steps do not fit either bass order
    r = K.read(_row("b", 3, "treble"), "bass")
    assert K.fifths_of(r) is None


def test_no_clef_and_no_key_object_and_no_slots():
    assert K.read(_row("b", 3), None)["why"] == "no_clef"
    assert K.read(None, "treble")["why"] == "no_key_object"
    assert K.read({"ko": {"read_pieces": []}, "space": SP}, "treble")["why"] == "no_slots"


def test_a_clef_without_a_slot_table_abstains():
    assert K.read(_row("b", 3), "percussion")["why"] == "clef_without_slot_table"


def test_unmeasured_slot_or_scale_abstains():
    assert K.read(_row("b", 3, skip_step=2), "treble")["why"] == "slot_not_measured"
    row = _row("b", 3)
    row["space"] = None
    assert K.read(row, "treble")["why"] == "no_staff_space"


def test_past_the_system_count_abstains():
    assert K.read(_row("b", 3, more=True), "treble")["why"] == "more_than_system"


def test_a_gap_abstains():
    assert K.read(_row("b", 3, gap=2.6), "treble")["why"] == "slots_not_one_apart"
    assert K.read(_row("b", 3, gap=0.2), "treble")["why"] == "slots_not_one_apart"


def test_a_natural_shaped_slot_is_out_of_scope():
    r = K.read(_row("b", 3, shapes={2: "natural"}), "treble")
    assert r["standing"] is None and r["why"] == "natural_shaped_slot"


def test_an_unclear_or_wrong_shape_does_not_veto_a_position_that_fits():
    # the shape reader calls a crushed flat a sharp (2.256: 8 of 90): position decides, the shape can only abstain on a NATURAL
    r = K.read(_row("b", 3, shapes={1: "sharp", 3: "unclear"}), "treble")
    assert K.fifths_of(r) == -3


def test_the_order_is_not_a_count_of_boxes():
    # three slots that fit flats 1..3 read three flats; the same slots shifted to the SHARP steps of slots 1..3 read sharps
    assert K.fifths_of(K.read(_row("b", 3), "treble")) == -3
    assert K.fifths_of(K.read(_row("#", 3), "treble")) == 3


def test_a_read_says_how_close_it_came():
    r = K.read(_row("b", 3), "treble")
    assert r["margin"] >= K.MIN_MARGIN_STEPS and max(r["flat_devs"]) <= K.KIND_TOL_STEPS and max(r["sharp_devs"]) > K.KIND_TOL_STEPS
