"""ROADMAP 2.58b -- one identity per physical mark.

Sean, 2026-10-06: *"give each note or symbol some sort of identifier that
allows us to make sure that it only shows up once."* `OMR_MARK_GROUPS`
(default OFF) files a `Q.MARK_GROUP` row on every notehead, rest and
accidental box; `glyph_owner` then rules once per group and EXPORT writes each
group once, counting the rest under `mark_group_duplicate`.

Every refusal has a positive control in the same class, and the accounting
stays an EQUALITY.
"""

import os
import types
import unittest
import xml.etree.ElementTree as ET
from unittest import mock

from tools.omr.staged import export as SX
from tools.omr.staged import gather as G
from tools.omr.staged.adjudicators import ownership as OWN
from tools.omr.staged.record import (Kind, Log, Outcome, Q, READERS, Verdict,
                                     Subject)
from tools.omr.staged import record as R

QUARTER = {"beats": 1.0, "written": 1.0, "dots": 0}


def _item(key, box, cat="notehead", scope=(0, 0), conf=0.9):
    return {"key": key, "box": box, "category": cat, "scope": scope,
            "conf": conf}


class TestClustering(unittest.TestCase):
    def test_overlapping_same_family_boxes_are_one_mark(self):
        g = G.cluster_marks([_item("a", (0, 0, 20, 20)),
                             _item("b", (4, 0, 24, 20))])
        self.assertEqual(g, [[0, 1]])

    def test_positive_control_apart_boxes_are_two_marks(self):
        g = G.cluster_marks([_item("a", (0, 0, 20, 20)),
                             _item("b", (60, 0, 80, 20))])
        self.assertEqual(g, [[0], [1]])

    def test_a_mark_is_never_grouped_across_families_or_systems(self):
        g = G.cluster_marks([_item("a", (0, 0, 20, 20)),
                             _item("b", (0, 0, 20, 20), cat="rest"),
                             _item("c", (0, 0, 20, 20), scope=(0, 1))])
        self.assertEqual(g, [[0], [1], [2]])

    def test_the_gate_is_over_a_chain_not_a_pair(self):
        g = G.cluster_marks([_item("a", (0, 0, 20, 20)),
                             _item("b", (6, 0, 26, 20)),
                             _item("c", (12, 0, 32, 20))])
        self.assertEqual(g, [[0, 1, 2]])


def _two_glyph_log(boxes, cats=("notehead", "notehead")):
    log = Log()
    for i, (b, cat) in enumerate(zip(boxes, cats)):
        sub = R.glyph(0, 0, i % 2, 0, i)
        log.observe(sub, Q.GLYPH_BOX, ("x", 0, 0, 1, 1), reader=READERS.DETECTOR,
                    frame="cell:0", score=0.9 - 0.1 * i, category=cat,
                    bbox_page_px=list(b))
    return log


class TestFiling(unittest.TestCase):
    def test_every_member_carries_the_same_group_and_a_singleton_its_own(self):
        log = _two_glyph_log([(0, 0, 20, 20), (4, 0, 24, 20), (200, 0, 220, 20)],
                             ("notehead",) * 3)
        n = G.mark_groups_from_log(log)
        self.assertEqual(n, 2)
        gids = [log.rows(Q.MARK_GROUP, R.glyph(0, 0, i % 2, 0, i))[0].value
                for i in range(3)]
        self.assertEqual(gids[0], gids[1])
        self.assertNotEqual(gids[0], gids[2])
        first = log.rows(Q.MARK_GROUP, R.glyph(0, 0, 0, 0, 0))[0]
        self.assertEqual(first.detail["rep"], "glyph/0/0/0/0/0")   # most confident
        self.assertEqual(first.detail["size"], 2)

    def test_DYNAMICS_are_not_grouped_the_ff_has_two_f_at_IoU_0317(self):
        """⚠️ dedupe FINDINGS §6.3: a flat IoU rule over dynamics deletes the
        second `f` of a real `ff`. The positive control is the notehead test
        above, which groups the same geometry."""
        log = _two_glyph_log([(0, 0, 20, 20), (4, 0, 24, 20)],
                             ("dynamic", "dynamic"))
        self.assertEqual(G.mark_groups_from_log(log), 0)
        self.assertEqual(log.rows(Q.MARK_GROUP, R.glyph(0, 0, 0, 0, 0)), ())

    def test_the_gather_is_OFF_by_default_and_on_with_the_flag(self):
        cell = types.SimpleNamespace(
            page_index=0, staff_index=0, measure_index=0,
            bbox_page_px=(100.0, 100.0, 500.0, 300.0), upscale_factor=2.0)

        def det(x):
            return types.SimpleNamespace(category="notehead", confidence=0.8,
                                         smufl_name="noteheadBlack",
                                         x_canonical=x, y_canonical=40.0,
                                         width_canonical=40.0,
                                         height_canonical=40.0)
        dets = {"cell/0/0/0/0": [det(100.0), det(104.0)]}
        local = {0: (0, 0)}
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ["OMR_MARK_GROUPS"] = "0"   # default ON since 2026-10-07: OFF is explicit
            log = Log()
            self.assertEqual(G.gather_mark_groups(log, [cell], local, dets), 0)
            self.assertEqual(
                log.rows(Q.MARK_GROUP, R.glyph(0, 0, 0, 0, 0)), ())
        with mock.patch.dict(os.environ, {"OMR_MARK_GROUPS": "1"}):
            log = Log()
            self.assertEqual(G.gather_mark_groups(log, [cell], local, dets), 1)
            a = log.rows(Q.MARK_GROUP, R.glyph(0, 0, 0, 0, 0))[0].value
            b = log.rows(Q.MARK_GROUP, R.glyph(0, 0, 0, 0, 1))[0].value
            self.assertEqual(a, b)


def _owner(log, sub, value, outcome=Outcome.DECIDED):
    return log.record(Verdict(
        id=log._next_id("vrd"), subject=sub, quantity=Q.GLYPH_OWNER,
        outcome=outcome, value=value, decider="t", reason="x"))


class TestOwnerRulesOncePerGroup(unittest.TestCase):
    def _grouped(self):
        log = _two_glyph_log([(0, 0, 20, 20), (4, 0, 24, 20)])
        G.mark_groups_from_log(log)
        return log, R.glyph(0, 0, 0, 0, 0), R.glyph(0, 0, 1, 0, 1)

    def test_an_abstained_copy_takes_the_decided_copys_owner(self):
        log, a, b = self._grouped()
        _owner(log, a, "staff/0/0/0")
        _owner(log, b, None, Outcome.ABSTAINED)
        census = OWN.reconcile_group_owners(log)
        self.assertEqual(log.verdict(Q.GLYPH_OWNER, b).value, "staff/0/0/0")
        self.assertEqual(census["adopted_after_abstaining"], 1)
        # superseded, never deleted: both rulings stay on the record
        self.assertEqual(len(log.verdicts(Q.GLYPH_OWNER, b)), 2)

    def test_a_DECIDED_verdict_is_never_overturned_and_a_conflict_files_nothing(self):
        log, a, b = self._grouped()
        _owner(log, a, "staff/0/0/0")
        _owner(log, b, "staff/0/0/1")
        census = OWN.reconcile_group_owners(log)
        self.assertEqual(census["conflict"], 1)
        self.assertEqual(log.verdict(Q.GLYPH_OWNER, a).value, "staff/0/0/0")
        self.assertEqual(log.verdict(Q.GLYPH_OWNER, b).value, "staff/0/0/1")

    def test_a_group_nobody_decided_stays_silent(self):
        log, a, b = self._grouped()
        _owner(log, a, None, Outcome.ABSTAINED)
        _owner(log, b, None, Outcome.ABSTAINED)
        census = OWN.reconcile_group_owners(log)
        self.assertEqual(census["all_silent"], 1)
        self.assertIsNone(log.verdict(Q.GLYPH_OWNER, a).value)

    def test_an_uncontested_twin_on_the_owner_staff_is_left_alone(self):
        log, a, b = self._grouped()
        _owner(log, b, "staff/0/0/1")          # b stays home, a never contested
        census = OWN.reconcile_group_owners(log)
        self.assertEqual(census.get("adopted_uncontested", 0), 1)
        self.assertEqual(log.verdict(Q.GLYPH_OWNER, a).value, "staff/0/0/1")

    def test_a_record_with_no_groups_is_untouched(self):
        log = _two_glyph_log([(0, 0, 20, 20), (4, 0, 24, 20)])
        _owner(log, R.glyph(0, 0, 0, 0, 0), "staff/0/0/0")
        self.assertEqual(OWN.reconcile_group_owners(log), {})


# ── export ──────────────────────────────────────────────────────────────────


def _obs(i, subject, quantity, value, **detail):
    return {"id": f"obs:{i:06d}", "subject": subject, "quantity": quantity,
            "value": value, "reader": "detector", "frame": "cell:0",
            "score": detail.pop("score", 0.9), "detail": detail, "basis": []}


def _vrd(i, subject, quantity, value, outcome="decided", reason="x",
         decider="t"):
    return {"id": f"vrd:{i:06d}", "subject": subject, "quantity": quantity,
            "outcome": outcome, "value": value, "decider": decider,
            "reason": reason, "considered": [], "used": [], "missing": [],
            "declined": [], "excluded": [], "correlated": [],
            "candidates": [], "basis": [], "margin": None,
            "supersedes": None, "detail": {}}


def _twins_page(*, grouped, n_twins=2):
    """ONE printed head detected `n_twins` times in ONE cell under different
    class names (the class-wise-NMS case), distinct confidence."""
    obs, vrd = [], []
    classes = ["noteheadBlackOnLine", "noteheadHalfOnLine", "noteheadBlackOnLine"]
    for gi in range(n_twins):
        sub = f"glyph/0/0/0/0/{gi}"
        box = [100 + gi, 50, 120 + gi, 70]
        obs.append(_obs(10 * gi, sub, Q.GLYPH_BOX, [classes[gi], 10, 10, 20, 20],
                        category="notehead", bbox_page_px=box,
                        score=0.9 - 0.1 * gi))
        obs.append(_obs(10 * gi + 1, sub, Q.NOTEHEAD_CLASS, classes[gi]))
        vrd.append(_vrd(10 * gi + 2, sub, Q.PITCH, "C4"))
        vrd.append(_vrd(10 * gi + 3, sub, Q.DURATION, QUARTER))
        if grouped:
            obs.append(_obs(10 * gi + 4, sub, Q.MARK_GROUP, "mg/0/0/0",
                            family="notehead", size=n_twins))
    vrd += [_vrd(900, "staff/0/0/0", Q.MEASURE_PARTITION, 1),
            _vrd(901, "staff/0/0/0", Q.CLEF, "treble"),
            _vrd(902, "system/0/0", Q.SYSTEM_STAFF_COUNT, 1),
            _vrd(903, "document", Q.PART_PARTITION,
                 {"join": "ordinal", "staves_per_system": 1},
                 reason="ordinal")]
    return {"record": {"observations": obs, "verdicts": vrd,
                       "abstentions": [], "counts": {}}, "summary": {}}


def _pitched(xml):
    return [n for n in ET.fromstring(xml).iter("note")
            if n.find("pitch") is not None]


class TestExportWritesAGroupOnce(unittest.TestCase):
    def test_without_groups_the_twins_are_written_twice_as_before(self):
        xml, rep = SX.to_musicxml(_twins_page(grouped=False))
        self.assertEqual(len(_pitched(xml)), 2)
        self.assertEqual(rep["marks_census"], {})

    def test_with_groups_one_note_and_the_other_is_counted(self):
        xml, rep = SX.to_musicxml(_twins_page(grouped=True))
        self.assertEqual(len(_pitched(xml)), 1)
        self.assertEqual(rep["notes_not_written"], {"mark_group_duplicate": 1})
        self.assertTrue(rep["balance"]["balanced"])

    def test_the_survivor_is_the_most_confident_member(self):
        page = _twins_page(grouped=True)
        for v in page["record"]["verdicts"]:       # tell the twins apart
            if v["quantity"] == Q.PITCH and v["subject"].endswith("/1"):
                v["value"] = "D4"
        for flip, expect in ((False, "C"), (True, "D")):
            for o in page["record"]["observations"]:
                if o["quantity"] == Q.GLYPH_BOX:
                    first = o["subject"].endswith("/0")
                    o["score"] = (0.95 if first else 0.5) if not flip \
                        else (0.5 if first else 0.95)
            xml, _ = SX.to_musicxml(page)
            steps = [n.findtext("pitch/step") for n in _pitched(xml)]
            self.assertEqual(steps, [expect])

    def test_the_census_partitions_and_nothing_is_unaccounted(self):
        _, rep = SX.to_musicxml(_twins_page(grouped=True, n_twins=3))
        c = rep["marks_census"]["notehead"]
        self.assertEqual(c["marks"], 1)
        self.assertEqual(c["detected_more_than_once"], 1)
        self.assertEqual(c["written_once"], 1)
        self.assertEqual(c["written_more_than_once"], 0)
        self.assertEqual(c["unaccounted"], 0)
        self.assertEqual(
            c["marks"], c["written_once"] + c["counted_under_a_reason"]
            + c["written_more_than_once"] + c["unaccounted"])

    def test_a_mark_whose_every_member_is_refused_is_COUNTED_not_lost(self):
        page = _twins_page(grouped=True)
        page["record"]["verdicts"] = [
            v for v in page["record"]["verdicts"]
            if v["quantity"] != Q.PITCH]            # nothing has a pitch
        _, rep = SX.to_musicxml(page)
        c = rep["marks_census"]["notehead"]
        self.assertEqual(c["counted_under_a_reason"], 1)
        self.assertEqual(c["reasons"], {"no_pitch": 1})
        self.assertEqual(c["unaccounted"], 0)


if __name__ == "__main__":
    unittest.main()
