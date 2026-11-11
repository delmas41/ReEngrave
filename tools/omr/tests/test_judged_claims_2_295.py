"""ROADMAP 2.295: Sean's answered CLAIM tiles, replayed. Fast tier: the normaliser on his real phrases, the registry
(regenerates from the per-lane answers files; no tile invented), and the overlap rule on a synthetic ledger canvas that can
fail every way (agrees / contradicts / unclaimed / cannot tell)."""
import json
import types
import unittest

import numpy as np

from tools.omr.staged import claim_readout as CR
from tools.omr.staged import judged_claims as JC


def N(words):
    return JC.normalise(words)


class TestNormaliser(unittest.TestCase):
    """His own words, as the lanes recorded them (benchmarks/*/answers)."""

    def test_part_of_a_flag_on_an_eighth_note_is_a_partial_flag_not_a_note(self):
        n = N("part of a flag on an eighth note")
        self.assertEqual((n["kind"], n["whole"]), ("flag", False))

    def test_half_of_a_quarter_note_rest_is_a_partial_QUARTER_rest(self):
        n = N("half of a quarter rest")
        self.assertEqual((n["kind"], n["whole"], n["value"]), ("rest:quarter", False, "quarter"))
        self.assertEqual(N("half of a quarter note rest")["kind"], "rest:quarter")      # "half" is the part, not the value

    def test_the_CR_from_crescendo_is_part_of_a_word(self):
        n = N("the CR from crescendo")
        self.assertEqual((n["kind"], n["whole"]), ("word", False))

    def test_a_large_rectangle_around_quarter_notes_is_a_partial_note_body(self):
        n = N("a large rectangle around quarter notes and a good amount of stem either side (part of a chord)")
        self.assertEqual((n["kind"], n["whole"], n["value"]), ("notehead", False, "quarter"))

    def test_rests_by_value_and_a_rest_is_never_a_note(self):
        self.assertEqual(N("whole rest")["kind"], "rest:whole")
        self.assertEqual(N("whole note rest")["kind"], "rest:whole")
        self.assertEqual(N("an eighth rest")["kind"], "rest:eighth")
        self.assertEqual(N("whole rest (corrected from 'whole note')")["kind"], "rest:whole")      # the parenthesis is the lane's gloss

    def test_notes_and_their_parts(self):
        self.assertEqual(N("an eighth note")["kind"], "notehead")
        self.assertEqual(N("eighth note and its stem")["kind"], "notehead")
        self.assertEqual(N("8 note")["value"], "eighth")
        self.assertEqual(N("a stem")["kind"], "stem")
        self.assertEqual(N("a beam")["kind"], "beam")
        self.assertEqual(N("part of an eighth note's flag")["kind"], "flag")
        n = N("most of a half note")
        self.assertEqual((n["kind"], n["whole"], n["value"]), ("notehead", False, "half"))

    def test_accidentals_dynamics_arcs_barlines_lines(self):
        self.assertEqual(N("a natural sign")["kind"], "accidental:natural")
        self.assertEqual(N("part of a sharp"), {"kind": "accidental:sharp", "value": "sharp", "whole": False, "why": None})
        self.assertEqual(N("flat")["kind"], "accidental:flat")
        for w in ("f", "ff", "sf", "dynamic p", "ff (box very large, reaches into the staff, includes a couple of half notes)"):
            self.assertEqual(N(w)["kind"], "dynamic", w)
        self.assertEqual((N("f from ff")["kind"], N("f from ff")["whole"]), ("dynamic", False))
        self.assertEqual((N("arc tip")["kind"], N("arc tip")["whole"]), ("arc", False))
        self.assertEqual(N("part of a barline")["whole"], False)
        self.assertEqual(N("a tremolo slash")["kind"], "tremolo")
        self.assertEqual(N("a ledger line")["kind"], "ledger_line")
        self.assertEqual(N("part of a staff line")["kind"], "staff_line")
        self.assertEqual(N("part of the (C) crook label by the instrument names")["kind"], "word")

    def test_words_that_do_not_map_cleanly_stay_unmapped_never_guessed(self):
        for w in ("the half note of a tempo (metronome) marking", "empty staff space between a barline and a note", "notehead and accidental", "", "?? unclear"):
            self.assertEqual(N(w)["kind"], "unmapped", w)
            self.assertTrue(N(w)["why"], w)


class TestRegistry(unittest.TestCase):
    def test_the_registry_on_disk_is_what_the_answers_files_produce(self):
        self.assertEqual(JC.check_registry(), [])

    def test_the_check_can_fail(self):
        reg = JC.build_registry()
        reg["tiles"][0]["kind"] = "arc"
        self.assertNotEqual(JC._dump(reg), JC.REGISTRY.read_text())

    def test_every_tile_is_kept_with_a_kind_from_the_vocabulary_and_a_page_box_or_a_named_reason(self):
        reg = JC.load_registry()
        self.assertGreaterEqual(len(reg["tiles"]), 150)
        ids = [t["id"] for t in reg["tiles"]]
        self.assertEqual(len(ids), len(set(ids)))
        for t in reg["tiles"]:
            self.assertIn(t["kind"].split(":")[0], JC.KINDS, t["id"])
            if t["kind"] == "unmapped":
                self.assertTrue(t["why_unmapped"], t["id"])
            if t["box"] is None:
                self.assertIn(t["lane"], ("2.292 r1",), t["id"])        # only a staff START has no box
            else:
                self.assertEqual(len(t["box"]), 4, t["id"])
                self.assertLess(t["box"][0], t["box"][2], t["id"])
                self.assertLess(t["box"][1], t["box"][3], t["id"])

    def test_the_2_288_r3_false_claim_is_in_it_as_an_eighth_note(self):
        t = {x["id"]: x for x in JC.load_registry()["tiles"]}["2.288 r3 #4"]
        self.assertEqual((t["plate"], t["page"], t["kind"], t["box"]), ("brahms", 14, "notehead", [2520.0, 6851.0, 2549.0, 6884.0]))
        self.assertEqual(t["words"], "eighth note")


def canvas(fam_by_region, *, staff_rows=(), size=(60, 60)):
    """A stand-in for a finished `LedgerInk`: a solid dark 10x20 mark at x 20..30, y 20..40, owners `{kind: (x0,y0,x1,y1)}` as READ claims."""
    ink = np.zeros(size, bool)
    ink[20:40, 20:30] = True
    fam = np.zeros(size, np.uint32)
    for k, (x0, y0, x1, y1) in fam_by_region.items():
        fam[y0:y1, x0:x1] |= CR.FINE_BIT[k]
    st = np.full(size, CR.ST_ONE, np.uint8)
    for r in staff_rows:
        ink[r, 15:35] = True
        st[r, 15:35] = CR.ST_STAFF
    return types.SimpleNamespace(shape=size, ink=ink, state=st, fam_eff=fam, weak=np.zeros(size, np.uint32), uk=np.zeros(size, np.uint8))


def tile(kind, box=(18, 18, 32, 42), words="x"):
    return {"id": "t #1", "lane": "t", "plate": "brahms", "page": 0, "box": list(box), "words": words, "kind": kind}


MARK = (20, 20, 30, 40)


class TestOverlapRule(unittest.TestCase):
    def test_agrees_when_a_READ_claim_of_his_kind_owns_the_ink(self):
        self.assertEqual(JC.judge_tile(canvas({"rest": MARK}), tile("rest:whole"))["verdict"], "agrees")

    def test_contradicts_when_a_READ_claim_of_another_kind_owns_the_ink_he_named(self):
        r = JC.judge_tile(canvas({"rest": MARK}), tile("notehead", words="eighth note"))
        self.assertEqual(r["verdict"], "contradicts")
        self.assertEqual(r["read_kinds"], {"rest": 1.0})

    def test_a_note_is_not_contradicted_by_its_own_stem_beam_flag_but_by_a_rest_it_is(self):
        for k in ("stem", "beam", "flag", "notehead"):
            self.assertEqual(JC.judge_tile(canvas({k: MARK}), tile("notehead"))["verdict"], "agrees", k)
        self.assertEqual(JC.judge_tile(canvas({"accidental": MARK}), tile("notehead"))["verdict"], "contradicts")

    def test_unclaimed_when_nothing_READ_owns_it_and_a_weak_claim_does_not_count_as_READ(self):
        c = canvas({})
        c.weak[20:40, 20:30] = CR.FINE_BIT["rest"]
        r = JC.judge_tile(c, tile("rest:quarter"))
        self.assertEqual(r["verdict"], "unclaimed")
        self.assertEqual(r["weak_kinds"], {"rest": 1.0})

    def test_a_staff_line_or_ledger_line_crossing_the_mark_is_the_marks_not_a_contradiction(self):
        c = canvas({"rest": MARK, "staff_line": (20, 29, 30, 31), "ledger_line": (20, 35, 30, 36)})
        self.assertEqual(JC.judge_tile(c, tile("rest:whole"))["verdict"], "agrees")
        c = canvas({"staff_line": MARK})              # but a mark owned ONLY by staff lines is not claimed: unclaimed, never agrees, never contradicts
        self.assertEqual(JC.judge_tile(c, tile("rest:whole"))["verdict"], "unclaimed")

    def test_eraser_taken_staff_ink_is_left_out_unless_he_named_a_staff_line(self):
        c = canvas({"rest": MARK}, staff_rows=(25, 26, 27, 28))
        r = JC.judge_tile(c, tile("rest:whole"))
        self.assertEqual((r["verdict"], r["ink_px"]), ("agrees", 160))        # 4 staff rows x 10 px of the mark are the staff's, left out
        self.assertEqual(JC.judge_tile(canvas({}, staff_rows=(25, 26)), tile("staff_line", box=(15, 24, 35, 28)))["verdict"], "agrees")

    def test_cannot_tell_is_never_agrees(self):
        c = canvas({"rest": MARK})
        self.assertEqual(JC.judge_tile(c, tile("rest:whole", box=(0, 0, 10, 10)))["verdict"], "cannot_tell")        # box on no ink
        self.assertEqual(JC.judge_tile(c, tile("unmapped"))["verdict"], "cannot_tell")
        t = tile("rest:whole")
        t["box"] = None
        self.assertEqual(JC.judge_tile(c, t)["why"], "no_page_box")
        self.assertEqual(JC.judge_tile(c, tile("rest:whole", box=(100, 100, 120, 120)))["why"], "box_off_page")

    def test_a_claim_the_readout_files_under_other_is_not_guessed_either_way(self):
        r = JC.judge_tile(canvas({"other": MARK}), tile("accidental:sharp"))
        self.assertEqual(r["verdict"], "cannot_tell")
        self.assertIn("unnamed", r["why"])

    def test_the_rule_can_fail_a_box_shifted_off_the_mark_stops_agreeing(self):
        c = canvas({"rest": MARK})
        self.assertEqual(JC.judge_tile(c, tile("rest:whole"))["verdict"], "agrees")
        self.assertNotEqual(JC.judge_tile(c, tile("rest:whole"), dx=40)["verdict"], "agrees")
        self.assertNotEqual(JC.judge_tile(c, tile("rest:whole", box=(10, 10, 19, 19)))["verdict"], "agrees")

    def test_a_minority_of_wrong_kind_ink_does_not_contradict_an_agreeing_mark(self):
        c = canvas({"rest": MARK, "beam": (20, 20, 30, 24)})             # 20% of the ink also a beam: R still 1.0, Wa 0.2 < 0.3
        self.assertEqual(JC.judge_tile(c, tile("rest:whole"))["verdict"], "agrees")

    def test_2_295b_a_wrong_READ_claim_standing_on_30_percent_contradicts_even_where_his_kind_owns_it(self):
        # CHANGED RULE (2.295b): before, a mark that was 60% his kind and 40% a beam "agreed" (R wins). A READ claim of another kind on >= 30% of the ink
        # is a wrong claim whether or not his kind also stands there: CONTRADICTS, flagged `twice`.
        c = canvas({"rest": (20, 20, 30, 32), "beam": (20, 32, 30, 40)})
        r = JC.judge_tile(c, tile("rest:whole"))
        self.assertEqual((r["verdict"], r["twice"]), ("contradicts", True))
        self.assertAlmostEqual(r["wrong_any"], 0.4, places=2)

    def test_summary_line_counts_four_ways(self):
        rs = [{"verdict": "agrees"}, {"verdict": "agrees"}, {"verdict": "contradicts"}, {"verdict": "unclaimed"}, {"verdict": "cannot_tell"}]
        self.assertIn("agrees 2 / contradicts 1 / unclaimed 1 / cannot tell 1", JC.summary_line("brahms", rs))
        self.assertEqual(JC.tally(rs), {"agrees": 2, "contradicts": 1, "unclaimed": 1, "cannot_tell": 1})


if __name__ == "__main__":
    unittest.main()
