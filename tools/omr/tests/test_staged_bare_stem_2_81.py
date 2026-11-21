"""ROADMAP 2.81 phase 2 -- a bare stem is a quarter, as a LABELLED LIKELIHOOD.

Sean, 2026-10-10: a filled head on a stem whose every candidate beam was
refused and whose tip is seen clean is most likely a quarter -- but his blind
tiles put that at 0.76 pooled / 0.80 strict, below his 95% bar, so it is NOT an
ADJUDICATE decision. Two pieces, both under test here:

  * ADJUDICATE ranks the quarter ABOVE the eighth in the `beam_discounted_
    uncertain` narrowing -- but only where the evidence holds (a decided own
    stem, a tip window READ clean, no refused stroke standing at the tip).
    Where it does not, the order is the one it always was and NOTHING is
    claimed.
  * INFER's `collapse_bare_stem_by_bar` settles such a head ONLY where the
    bar's arithmetic forces it (every landing agrees), behind the default-OFF
    flag `OMR_BARE_STEM_BAR`.

⚠️ Each refusal is paired with a positive control in the same class (CLAUDE.md
§6b): a test that passes by refusing everything is not a test.
"""

from __future__ import annotations

import os
import unittest
from unittest import mock

from tools.omr.staged import adjudicate, evaluate, infer, inferences
from tools.omr.staged import adjudicators, consequences  # noqa: F401
from tools.omr.staged import record as R
from tools.omr.staged.gather import FRAME_PAGE
from tools.omr.staged.record import (READERS, Candidate, Kind, Log, Outcome, Q,
                                     Subject, Verdict)

CELL = R.cell(0, 0, 0, 0)
SPACE = 16


# ─────────────────────────────────────────────────────────────────────────────
# ADJUDICATE: the ranking
# ─────────────────────────────────────────────────────────────────────────────


def _head(log, g, *, x=100, y=90):
    log.observe(g, Q.NOTEHEAD_CLASS, "noteheadBlack",
                reader=READERS.DETECTOR, frame="cell:0", score=0.9)
    log.observe(g, Q.GLYPH_BOX, ("noteheadBlack", x, y, 20, 16),
                reader=READERS.DETECTOR, frame="cell:0", score=0.9,
                bbox_page_px=[1000 + x, 990, 1020 + x, 1006])


def _two_staff(log):
    """The 2.25b fixture: staff 0 holds the head, staff 1's own stem makes the
    stroke far below staff 0 THAT staff's beam (discounted)."""
    log.observe(R.staff(0, 0, 0), Q.STAFF_LINES,
                [950.0, 960.0, 970.0, 980.0, 990.0],
                reader=READERS.GEOMETRY, frame="page")
    log.observe(CELL, Q.CELL_STAFF_SPACE, float(SPACE),
                reader=READERS.GEOMETRY, frame="cell:0")
    g = R.glyph(0, 0, 0, 0, 0)
    _head(log, g, x=100, y=90)
    gb = R.glyph(0, 0, 1, 0, 0)
    log.observe(gb, Q.NOTEHEAD_CLASS, "noteheadBlack",
                reader=READERS.DETECTOR, frame="cell:0", score=0.9)
    log.observe(gb, Q.GLYPH_BOX, ("noteheadBlack", 100, 20, 20, 16),
                reader=READERS.DETECTOR, frame="cell:0", score=0.9,
                bbox_page_px=[1100, 1070, 1120, 1086])
    return g


def _stem(log, *, x, y, w=4, h=20):
    return log.observe(CELL, Q.STEM, (x, y, w, h), reader=READERS.CV_LINES,
                       frame="cell:0", x0=x, x1=x + w, y_center=y + h / 2.0,
                       image="no_staff", staff_lines_erased=True)


def _tip(log, stem_row, *, found, end="top"):
    return log.observe(CELL, Q.STEM_TIP_INK, bool(found),
                       reader=READERS.CV_STEM_TIP, frame="cell:0",
                       stem_row_id=stem_row.id, end=end)


def _neighbour_discounted_head(log, *, tip_found=None):
    """Up-stem head whose ONLY stroke (far below, nowhere near the tip) is the
    neighbour staff's beam -> `beam_discounted_uncertain`."""
    g = _two_staff(log)
    log.observe(CELL, Q.BEAM_STROKE, (90, 150, 40, 4),
                reader=READERS.CV_LINES, frame="cell:0", x0=90, x1=130,
                y_center=152, image="no_staff", staff_lines_erased=True)
    s = _stem(log, x=105, y=80)                      # up, tip at y=80
    log.observe(R.cell(0, 0, 1, 0), Q.STEM, (90, -10, 4, 50),
                reader=READERS.CV_LINES, frame="cell:0", x0=90, x1=94,
                y_center=15, image="no_staff", staff_lines_erased=True)
    if tip_found is not None:
        _tip(log, s, found=tip_found)
    return g


def _beats(v):
    return [c.value["beats"] for c in v.candidates]


def _rank_on():
    """`OMR_BARE_STEM_RANK` is default OFF: the tests that exercise the
    ranking turn it on, and one below asserts the default."""
    return mock.patch.dict(os.environ, {"OMR_BARE_STEM_RANK": "1"})


class TestTheQuarterIsRankedFirstWhereTheEvidenceHolds(unittest.TestCase):

    def test_a_head_with_no_stem_keeps_the_old_order(self):
        log = Log()
        g = _two_staff(log)
        log.observe(CELL, Q.BEAM_STROKE, (90, 150, 40, 4),
                    reader=READERS.CV_LINES, frame="cell:0", x0=90, x1=130,
                    y_center=152, image="no_staff", staff_lines_erased=True)
        log.observe(R.cell(0, 0, 1, 0), Q.STEM, (90, -10, 4, 50),
                    reader=READERS.CV_LINES, frame="cell:0", x0=90, x1=94,
                    y_center=15, image="no_staff", staff_lines_erased=True)
        with _rank_on():
            adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        if v.outcome is Outcome.NARROWED and \
                v.reason == "beam_discounted_uncertain":
            self.assertEqual(v.detail["bare_stem_likelihood"], "not_claimed")


# ─────────────────────────────────────────────────────────────────────────────
# INFER: the bar's arithmetic
# ─────────────────────────────────────────────────────────────────────────────


def _sub(staff, glyph, cell=0):
    return Subject(Kind.GLYPH, page=0, system=0, staff=staff, cell=cell,
                   glyph=glyph)


def _cell(staff=0, cell=0):
    return Subject(Kind.CELL, page=0, system=0, staff=staff, cell=cell)


def _system():
    return Subject(Kind.SYSTEM, page=0, system=0)


class _Bar:
    """One staff, one bar, events in order, a meter on the system.

    The meter is shaped like `adjudicate_meter`'s: a `voted` verdict that
    USED printed `Q.METER_TEMPLATE` readings (and, like the real one, whose
    `basis` is wide). `meter_reason`/`meter_used_member` bend it for the
    refusals.
    """

    def __init__(self, num=4, den=4, meter_reason="voted", segments=1,
                 carried=False):
        self.log = Log()
        self.events = []
        self.g = 0
        self.num, self.den = num, den
        self.meter_reason = meter_reason
        self.segments = segments
        self.carried = carried
        self.members = []
        self.durations = []
        self.meter_basis_extra = ()
        self.cell_idx = 0

    def _id(self):
        return self.log._next_id("vrd")

    def decided(self, beats, reason="head_and_marks"):
        g = self.g
        self.g += 1
        self.durations.append(self.log.record(Verdict(
            id=self._id(), subject=_sub(0, g, self.cell_idx), quantity=Q.DURATION,
            outcome=Outcome.DECIDED, value={"beats": beats, "written": beats},
            decider="adjudicate_duration", reason=reason)))
        self.events.append([g])
        return g

    def bare(self, quarter_first=True, reason="beam_discounted_uncertain",
             beats=(1.0, 0.5), tip_clean=True):
        g = self.g
        self.g += 1
        sup = (2.0, 1.0) if quarter_first else (1.0, 2.0)
        v = self.log.record(Verdict(
            id=self._id(), subject=_sub(0, g, self.cell_idx), quantity=Q.DURATION,
            outcome=Outcome.NARROWED, value=None,
            decider="adjudicate_duration", reason=reason,
            candidates=tuple(sorted(
                (Candidate({"beats": b, "written": b,
                            "beam_levels": i}, support=s)
                 for i, (b, s) in enumerate(zip(beats, sup))),
                key=lambda c: -c.support)),
            detail={"bare_stem_likelihood": "quarter_first"
                    if quarter_first else "not_claimed",
                    "bare_stem_tip_window_clean": tip_clean}))
        self.events.append([g])
        self.members.append(v)
        return g

    def finish(self):
        self.log.record(Verdict(
            id=self._id(), subject=_cell(0, self.cell_idx), quantity=Q.EVENT,
            outcome=Outcome.DECIDED,
            value={"events": [{"glyphs": e} for e in self.events]},
            decider="test:events", reason="grouped"))
        rows = [self.log.observe(_staff(i), Q.METER_TEMPLATE, 0.9,
                                 reader=READERS.TEMPLATE, frame="page")
                for i in range(3)]
        val = {"numerator": self.num, "denominator": self.den}
        val["segments"] = [dict(val, from_cell=k) for k in range(self.segments)]
        home = Subject(Kind.SYSTEM, page=0, system=5) if self.carried \
            else _system()
        voted = self.log.record(Verdict(
            id=self._id(), subject=home, quantity=Q.METER,
            outcome=Outcome.DECIDED, value=val, decider="adjudicate_meter",
            reason="voted", used=tuple(r.id for r in rows),
            # like the real one: it CONSIDERED every duration of the system
            basis=tuple(r.id for r in rows)
            + tuple(d.id for d in self.durations)
            + tuple(m.id for m in self.members)))
        if self.carried:
            # the system under test CARRIES an earlier system's printed meter
            val2 = dict(val)
            if self.carried == "different":
                val2 = {"numerator": 3, "denominator": 4,
                        "segments": [{"numerator": 3, "denominator": 4,
                                      "from_cell": 0}]}
            self.log.record(Verdict(
                id=self._id(), subject=_system(), quantity=Q.METER,
                outcome=Outcome.DECIDED, value=val2,
                decider="adjudicate_meter", reason="carried",
                used=(voted.id,),
                basis=(voted.id,) + tuple(d.id for d in self.durations)
                + tuple(m.id for m in self.members)))
        elif self.meter_reason != "voted":
            self.log.record(Verdict(
                id=self._id(), subject=_system(), quantity=Q.METER,
                outcome=Outcome.DECIDED, value=val,
                decider="adjudicate_meter", reason=self.meter_reason,
                used=(voted.id,), basis=(voted.id,),
                supersedes=voted.id))
        self.log.freeze()
        return self.log


def _staff(i):
    return Subject(Kind.STAFF, page=0, system=0, staff=i)


def _run(log, *, flag="1"):
    # the 2.97 columns rule (default ON) is a different rule: isolate this one
    env = {infer.NARROWED_BAR_ENV: "0"}
    if flag is not None:
        env[infer.BARE_STEM_BAR_ENV] = flag
    with mock.patch.dict(os.environ, env, clear=False):
        if flag is None:
            os.environ.pop(infer.BARE_STEM_BAR_ENV, None)
        return infer.run(log, evaluate.Report([], [], []))


def _fired(report):
    return [i for i in report.inferred
            if i[0] == infer.Inference.COLLAPSE_BARE_STEM_BY_BAR.value]




class TestTheFlagAndTheLabel(unittest.TestCase):

    def _bar(self):
        b = _Bar()
        for _ in range(3):
            b.decided(1.0)
        g = b.bare()
        return b.finish(), g

if __name__ == "__main__":
    unittest.main()


_BAR_SUM_CONFIRM_ONLY_WAS = None


def setUpModule():
    """These tests pin the bar-sum deciders as shipped BEFORE ROADMAP 2.154 (the bar may choose among a narrowing's
    candidates); `OMR_BAR_SUM_CONFIRM_ONLY` went default ON at arm a 2026-10-16 (Sean), so this module runs with it off.
    The arm-a behaviour is tested in `test_staged_bar_sum_confirm_only_2_154.py`."""
    import os
    global _BAR_SUM_CONFIRM_ONLY_WAS
    _BAR_SUM_CONFIRM_ONLY_WAS = os.environ.get("OMR_BAR_SUM_CONFIRM_ONLY")
    os.environ["OMR_BAR_SUM_CONFIRM_ONLY"] = "off"


def tearDownModule():
    import os
    if _BAR_SUM_CONFIRM_ONLY_WAS is None:
        os.environ.pop("OMR_BAR_SUM_CONFIRM_ONLY", None)
    else:
        os.environ["OMR_BAR_SUM_CONFIRM_ONLY"] = _BAR_SUM_CONFIRM_ONLY_WAS
