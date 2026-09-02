"""Who resolves the margin is a required choice, and it can change mid-run."""
import io

import pytest

from tools.omr.assist import MODES, Assist


class _Tty(io.StringIO):
    """A stream that claims to be a terminal, so the prompt will run."""

    def isatty(self) -> bool:
        return True


class TestThereIsNoDefault:
    """The two paid options spend different things — a cent a system, or
    somebody's attention — so choosing one silently spends one without asking."""

    def test_the_contextual_pass_refuses_to_guess(self):
        from tools.omr.contextual import apply_contextual_analysis
        with pytest.raises(TypeError, match="deliberately no"):
            apply_contextual_analysis({}, pdf_path="x.pdf")

    def test_asking_without_a_terminal_is_an_error_not_a_choice(self):
        with pytest.raises(RuntimeError, match="no terminal"):
            Assist.ask(stream=io.StringIO("h\n"), out=io.StringIO())

    def test_an_empty_answer_is_asked_again(self):
        out = io.StringIO()
        assist = Assist.ask(stream=_Tty("\n\nv\n"), out=out)
        assert assist.mode == "vision"
        assert out.getvalue().count("please answer") == 2

    @pytest.mark.parametrize("typed,expected", [
        ("h\n", "human"), ("human\n", "human"),
        ("v\n", "vision"), ("n\n", "none")])
    def test_each_mode_can_be_chosen(self, typed, expected):
        assert Assist.ask(stream=_Tty(typed), out=io.StringIO()).mode == expected

    def test_none_is_a_choice_not_an_absence(self):
        """'Run on the free tiers and abstain' is a legitimate answer — it is
        what a batch that will be checked some other way should say."""
        assert "none" in MODES
        assert Assist("none").mode == "none"


class TestSwitchingMidRun:
    def test_a_switch_is_recorded_with_its_reason(self):
        assist = Assist("human")
        assist.switch("vision", "handed over at page 4")
        assert assist.mode == "vision"
        assert assist.summary["switched"] == [
            {"from": "human", "to": "vision", "why": "handed over at page 4"}]

    def test_switching_to_the_mode_already_set_records_nothing(self):
        assist = Assist("vision")
        assist.switch("vision", "no-op")
        assert assist.summary["switched"] == []

    def test_a_bad_mode_is_refused_on_the_way_in_and_on_a_switch(self):
        with pytest.raises(ValueError):
            Assist("magic")
        with pytest.raises(ValueError):
            Assist("human").switch("magic")


class TestTheHumanTierAsksAboutVeryLittle:
    def test_only_staves_a_trigger_fired_on(self):
        """Not every staff — the ones with no usable label. On Beethoven 5 p.48
        that is one question, and it is worth three clefs."""
        from types import SimpleNamespace

        from tools.omr.instruments import lookup
        from tools.omr.staff_labels import StaffLabel
        from tools.omr.staff_labels_human import _questions

        staves = [SimpleNamespace(staff_index=i, system_index=0, top_y=i * 100,
                                  bottom_y=i * 100 + 40) for i in range(4)]
        have = {
            0: StaffLabel(0, "Fl.", lookup("Fl.").instrument, 0, 20.0, "high", "fl"),
            1: StaffLabel(1, "A.", None, 0, 120.0),          # read, unresolved
            # staff 2 has no label at all
            3: StaffLabel(3, "Ob.", lookup("Ob.").instrument, 0, 320.0, "high", "ob"),
        }
        asked = _questions(None, staves, have)
        assert [s.staff_index for s, _, _ in asked] == [1, 2]
        assert asked[0][1] == "A." and "lexicon" in asked[0][2]
        assert asked[1][1] is None and "no label" in asked[1][2]

    def test_it_will_not_prompt_when_nobody_is_there(self):
        """`human` chosen but running headless: the free readers' answer stands,
        loudly, rather than the run blocking on a prompt nobody can see."""
        from tools.omr.staff_labels_human import read_staff_labels_human
        from pathlib import Path

        assist = Assist("human")
        got = read_staff_labels_human(None, [], assist, out_dir=Path("."),
                                      stream=io.StringIO(), out=io.StringIO())
        assert got == []
