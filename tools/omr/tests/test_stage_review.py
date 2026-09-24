"""ROADMAP 3.4 lane B — the STAGE REVIEW viewer.

Four questions, and each test was run RED before it was believed:

1. **The sidecar round-trips and satisfies the contract with lane (A).** Run
   RED by relaxing `validate_action` to `return action` — every rejection case
   then passes silently, which is precisely the failure mode a validator has.
2. **Crop pixels ↔ page pixels, BOTH WAYS, on a known box.** ⚠️ A round-trip
   alone is not the test: `to_page(to_crop(p)) == p` holds for the identity
   too, and this repo has already paid once for two frames that were
   indistinguishable on a fixture whose boxes started at 0. So the expected
   crop coordinates are computed BY HAND here, from a frame whose origin is
   not 0 and whose zoom is not 1, and the round trip is checked on top.
3. **Every view renders on a fixture record** — including a staff whose clef
   ABSTAINED, because a viewer that only works where everything was decided
   is a viewer that cannot show the one staff it was built for.
The fourth question — does the pick list's funnel reproduce the
notehead-funnel FINDINGS on the REAL record — is in
`test_stage_review_real_record.py`, which the fast/slow split marks slow by
its own content rule (it names machine-local state).

⚠️ No test here asserts on module source text (CLAUDE.md §6c).
"""

import json
import tempfile
import unittest
from pathlib import Path

from tools.omr.staged import reach as REACH
from tools.omr.staged.record import Q
from tools.omr.staged.review import server as R


# ─────────────────────────────────────────────────────────────────────────
# A fixture record: one page, one system, two staves, one of which has a
# clef that ABSTAINED — the Litolff Viola's own shape, in miniature.
# ─────────────────────────────────────────────────────────────────────────

def _obs(i, subject, quantity, value, *, reader="detector", frame="cell:0",
         score=0.9, **detail):
    return {"id": f"obs:{i:06d}", "subject": subject, "quantity": quantity,
            "value": value, "reader": reader, "frame": frame,
            "score": score, "detail": detail, "basis": []}


def _abs(i, subject, quantity, reason, *, reader="cv", frame="cell:0", **detail):
    return {"id": f"abs:{i:06d}", "subject": subject, "quantity": quantity,
            "reader": reader, "frame": frame, "reason": reason,
            "detail": detail, "basis": []}


def _vrd(i, subject, quantity, value, outcome="decided", reason="x",
         decider="adjudicate_clef", candidates=(), basis=(), used=()):
    return {"id": f"vrd:{i:06d}", "subject": subject, "quantity": quantity,
            "outcome": outcome, "value": value, "decider": decider,
            "reason": reason, "considered": list(used), "used": list(used),
            "missing": [], "declined": [], "excluded": [], "correlated": [],
            "candidates": list(candidates), "basis": list(basis),
            "margin": None, "supersedes": None, "detail": {}}


def fixture_record() -> dict:
    """Two staves on one system: staff 0 reads its clef, staff 1 abstains.

    The geometry is in PAGE pixels the way a real record spells it, so the
    crop frame can be cut from it without a PDF.
    """
    obs, vrd, abst = [], [], []
    n = 0
    for st in (0, 1):
        top = 100 + st * 200
        lines = [top + 16 * k for k in range(5)]
        obs.append(_obs(n, f"staff/0/0/{st}", Q.STAFF_LINES, lines,
                        reader="staff_detector", frame="page"))
        n += 1
        obs.append(_obs(n, f"staff/0/0/{st}", Q.STAFF_SPACING, 16.0,
                        reader="staff_detector", frame="page"))
        n += 1
        for c in range(2):
            box = [50 + 300 * c, top - 40, 340 + 300 * c, top + 104]
            obs.append(_obs(n, f"cell/0/0/{st}/{c}", Q.CELL_BOX, box,
                            reader="measure_extractor", frame="page"))
            n += 1
            obs.append(_obs(n, f"cell/0/0/{st}/{c}", Q.INK, "components",
                            reader="ink", frame="page",
                            ink_n_components=7))
            n += 1
            for g in range(2):
                sub = f"glyph/0/0/{st}/{c}/{g}"
                x = 80 + 300 * c + 60 * g
                obs.append(_obs(n, sub, Q.GLYPH_BOX,
                                ["noteheadBlackOnLine", x, top + 16, 26, 22],
                                bbox_page_px=[float(x), float(top + 16),
                                              float(x + 26), float(top + 38)],
                                category="notehead"))
                n += 1
                obs.append(_obs(n, sub, Q.GLYPH_CONF, 0.77))
                n += 1
                obs.append(_obs(n, sub, Q.NOTEHEAD_CLASS, "noteheadBlackOnLine"))
                n += 1
                if st == 0:
                    vrd.append(_vrd(n, sub, Q.PITCH, "G4",
                                    decider="restate_pitch", reason="clef",
                                    used=[f"obs:{n - 3:06d}"]))
                    n += 1
                vrd.append(_vrd(n, sub, Q.DURATION, {"written": 1.0, "beats": 1.0,
                                                     "dots": 0, "beam_levels": 0},
                                decider="adjudicate_duration",
                                reason="notehead_class"))
                n += 1
        vrd.append(_vrd(n, f"staff/0/0/{st}", Q.MEASURE_PARTITION, 2,
                        decider="adjudicate_measure_partition",
                        reason="barlines"))
        n += 1
        vrd.append(_vrd(n, f"staff/0/0/{st}", Q.SLOT_INDEX, st,
                        decider="adjudicate_slot_index", reason="ordinal"))
        n += 1
        if st == 0:
            vrd.append(_vrd(n, "staff/0/0/0", Q.CLEF, "treble",
                            decider="adjudicate_clef", reason="glyph",
                            used=[]))
            n += 1
        else:
            # ⚠️ THE WHOLE POINT OF THE FIXTURE. The clef abstained, so
            # nothing downstream of pitch exists for this staff.
            abst.append(_abs(n, "staff/0/0/1", Q.CLEF_GLYPH, "no_detections"))
            n += 1
            abst.append(_abs(n, "staff/0/0/1", Q.CLEF_LOCATED, "occupied",
                             locator_branch="occupied",
                             cluster_w_spaces=2.09, cluster_h_spaces=4.5))
            n += 1
            vrd.append(_vrd(n, "staff/0/0/1", Q.CLEF, None,
                            outcome="abstained", reason="no_candidates",
                            decider="adjudicate_clef"))
            n += 1
    vrd.append(_vrd(n, "system/0/0", Q.SYSTEM_STAFF_COUNT, 2,
                    decider="adjudicate_system_staff_count", reason="grouping"))
    n += 1
    vrd.append(_vrd(n, "document", Q.PART_PARTITION,
                    {"join": "ordinal", "staves_per_system": 2},
                    decider="adjudicate_part_partition", reason="ordinal"))
    return {"record": {"observations": obs, "verdicts": vrd,
                       "abstentions": abst, "counts": {}},
            "summary": {}, "provenance": {"commit": "0" * 40, "dirty": False,
                                          "settings": {"args": {"dpi": 600}}}}


def _data(tmp: Path) -> R.ReviewData:
    p = tmp / "fixture.record.json"
    p.write_text(json.dumps(fixture_record()))
    return R.ReviewData(p, None)


# ─────────────────────────────────────────────────────────────────────────
# 1. The sidecar
# ─────────────────────────────────────────────────────────────────────────

class TestSidecarContract(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.path = self.tmp / "review-actions.json"

    def _sc(self):
        return R.Sidecar(self.path, record="rec.json", staff="staff/3/0/9")

    def test_round_trip_every_kind(self):
        sc = self._sc()
        sc.append({"stage": "gather", "kind": "add_box",
                   "bbox_page_px": [1.0, 2.0, 3.0, 4.0],
                   "category": "noteheadBlack", "note": "a head we missed"})
        sc.append({"stage": "gather", "kind": "delete_box",
                   "glyph": "glyph/3/0/9/12/4", "note": "barline sliver"})
        sc.append({"stage": "gather", "kind": "redraw_box",
                   "glyph": "glyph/3/0/9/12/4",
                   "bbox_page_px": [5, 6, 7, 8], "note": ""})
        sc.append({"stage": "adjudicate", "kind": "disagree",
                   "verdict": "vrd:012111", "note": "that is an alto clef"})
        sc.append({"stage": "export", "kind": "agree", "verdict": "vrd:9",
                   "note": ""})

        doc = json.loads(self.path.read_text())
        self.assertEqual(doc["record"], "rec.json")
        self.assertEqual(doc["staff"], "staff/3/0/9")
        self.assertEqual([a["id"] for a in doc["actions"]],
                         ["act-0001", "act-0002", "act-0003", "act-0004",
                          "act-0005"])
        for a in doc["actions"]:
            R.validate_action(a)          # the file validates as written
            self.assertTrue(a["t"].endswith("+00:00"))

        # re-opening the SAME file re-validates every row and keeps numbering
        again = self._sc()
        self.assertEqual(len(again.doc["actions"]), 5)
        self.assertEqual(again.next_id(), "act-0006")

    def test_undo_takes_one_back_and_nothing_else(self):
        sc = self._sc()
        sc.append({"stage": "gather", "kind": "delete_box", "glyph": "g/1"})
        sc.append({"stage": "gather", "kind": "delete_box", "glyph": "g/2"})
        self.assertTrue(sc.undo("act-0001"))
        self.assertFalse(sc.undo("act-0001"))
        self.assertEqual([a["glyph"] for a in
                          json.loads(self.path.read_text())["actions"]],
                         ["g/2"])

    def test_one_staff_per_file(self):
        self._sc()
        with self.assertRaises(R.ContractError):
            R.Sidecar(self.path, record="rec.json", staff="staff/3/0/8")

    def test_it_refuses_what_the_contract_forbids(self):
        """⚠️ THE POSITIVE CONTROL IS ABOVE: `test_round_trip_every_kind`
        writes one of every kind and every one is accepted, so this test
        cannot pass by refusing everything."""
        bad = [
            ({"id": "a", "t": "x", "stage": "gather"}, "no kind"),
            ({"id": "a", "t": "x", "stage": "gather", "kind": "nope"},
             "unknown kind"),
            ({"id": "a", "t": "x", "stage": "nowhere", "kind": "agree",
              "verdict": "v"}, "unknown stage"),
            ({"id": "a", "t": "x", "stage": "adjudicate", "kind": "add_box",
              "bbox_page_px": [1, 2, 3, 4], "category": "c"},
             "a GATHER kind under another stage"),
            ({"id": "a", "t": "x", "stage": "gather", "kind": "agree",
              "verdict": "v"}, "agree under GATHER"),
            ({"id": "a", "t": "x", "stage": "gather", "kind": "add_box",
              "bbox_page_px": [1, 2, 3, 4]}, "add_box without a category"),
            ({"id": "a", "t": "x", "stage": "gather", "kind": "add_box",
              "category": "c", "bbox_page_px": [4, 2, 1, 4]},
             "an inverted rectangle"),
            ({"id": "a", "t": "x", "stage": "gather", "kind": "add_box",
              "category": "c", "bbox_page_px": [1, 2, 3]},
             "a three-number box"),
            ({"id": "a", "t": "x", "stage": "gather", "kind": "delete_box"},
             "delete_box with no glyph"),
        ]
        for action, why in bad:
            with self.subTest(why=why):
                with self.assertRaises(R.ContractError):
                    R.validate_action(action)


# ─────────────────────────────────────────────────────────────────────────
# 2. The coordinate frame
# ─────────────────────────────────────────────────────────────────────────

class TestCropFrame(unittest.TestCase):
    """⚠️ The numbers are the REAL Litolff p3 Viola window
    (`crop.page_px == [295, 1689, 2663, 1973]`, zoom 2) and the box is the
    real header notehead `glyph/3/0/9/0/1`, so a conversion that silently
    dropped the zoom or the origin would have to be wrong here by a visible
    amount rather than by nothing on a fixture that starts at 0."""

    FRAME = R.CropFrame(x0=295, y0=1689, x1=2663, y1=1973, zoom=2, dpi=600)
    BOX = [388.5175, 1828.1925, 415.135, 1850.085]

    def test_page_to_crop_is_computed_by_hand(self):
        f = self.FRAME
        self.assertEqual(f.width, (2663 - 295) * 2)
        self.assertEqual(f.height, (1973 - 1689) * 2)
        got = f.box_to_crop(self.BOX)
        want = [(388.5175 - 295) * 2, (1828.1925 - 1689) * 2,
                (415.135 - 295) * 2, (1850.085 - 1689) * 2]
        for g, w in zip(got, want):
            self.assertAlmostEqual(g, w, places=6)
        # and the box lands inside the window it was cut for
        self.assertTrue(0 < got[0] < f.width and 0 < got[1] < f.height)

    def test_crop_to_page_is_computed_by_hand(self):
        f = self.FRAME
        self.assertEqual(f.to_page(0, 0), (295.0, 1689.0))
        self.assertEqual(f.to_page(f.width, f.height), (2663.0, 1973.0))
        self.assertEqual(f.to_page(187.035, 278.385),
                         (187.035 / 2 + 295, 278.385 / 2 + 1689))

    def test_round_trip_both_ways(self):
        f = self.FRAME
        back = f.box_to_page(f.box_to_crop(self.BOX))
        for g, w in zip(back, self.BOX):
            self.assertAlmostEqual(g, w, places=6)
        crop = [17.0, 3.0, 201.5, 88.25]
        again = f.box_to_crop(f.box_to_page(crop))
        for g, w in zip(again, crop):
            self.assertAlmostEqual(g, w, places=6)

    def test_zoom_one_is_not_a_special_case(self):
        f = R.CropFrame(x0=10, y0=20, x1=110, y1=70, zoom=1, dpi=300)
        self.assertEqual(f.to_crop(35, 45), (25, 25))
        self.assertEqual(f.to_page(25, 25), (35, 45))


# ─────────────────────────────────────────────────────────────────────────
# 3. Every view, on a fixture
# ─────────────────────────────────────────────────────────────────────────

class TestViewsOnAFixture(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.D = _data(cls.tmp)

    def test_the_export_control_ran_and_the_record_loaded(self):
        self.assertEqual(len(self.D.staff_keys), 2)
        self.assertIn("staff/0/0/0", self.D.glyphs_by_staff)
        self.assertEqual(len(self.D.glyphs_by_staff["staff/0/0/1"]), 4)

    def test_the_control_can_fail(self):
        """⚠️ RULE 7. Seen failing before it is trusted where it passes."""
        p = self.tmp / "fixture.record.json"
        with self.assertRaises(R.ControlFailed):
            R.ReviewData(p, None, break_control=True)

    def test_pick_list_is_ordered_by_heads_lost(self):
        rows = self.D.funnels()
        self.assertEqual([r["staff"] for r in rows][0], "staff/0/0/1")
        lost = [r["heads_lost"] for r in rows]
        self.assertEqual(lost, sorted(lost, reverse=True))
        abstaining = next(r for r in rows if r["staff"] == "staff/0/0/1")
        self.assertEqual(abstaining["heads_boxed"], 4)
        self.assertEqual(abstaining["heads_written"], 0)
        self.assertEqual(abstaining["refused"], {"no_pitch": 4})
        self.assertEqual(abstaining["clef"]["outcome"], "abstained")
        self.assertEqual(abstaining["clef"]["reason"], "no_candidates")
        reading = next(r for r in rows if r["staff"] == "staff/0/0/0")
        self.assertEqual(reading["heads_written"], 4)
        self.assertEqual(reading["heads_lost"], 0)

    def test_gather_view_without_a_pdf_still_describes_the_staff(self):
        g = R.gather_view(self.D, "staff/0/0/1", 2)
        self.assertEqual(len(g["boxes"]), 4)
        self.assertEqual(len(g["cells"]), 2)
        self.assertEqual(len(g["ink"]), 2)
        self.assertEqual(g["ink"][0]["n_components"], 7)
        self.assertEqual(g["crop"]["zoom"], 2)
        self.assertTrue(all(b["bbox_page_px"] for b in g["boxes"]))
        self.assertTrue(all(b["refused"] == ["no_pitch"] for b in g["boxes"]))

    def test_a_crop_without_a_pdf_refuses_rather_than_draws(self):
        frame, geom = R.crop_frame_for(self.D, "staff/0/0/1", 2)
        with self.assertRaises(FileNotFoundError):
            R.render_crop(self.D, "staff/0/0/1", frame, geom)

    def test_adjudicate_view_shows_the_abstentions_with_their_reasons(self):
        v = R.staff_stage_view(self.D, "staff/0/0/1", "adjudicate")
        head = next(b for b in v["staff_level"]
                    if b["subject"] == "staff/0/0/1")
        reasons = {a["reason"] for a in head["abstentions"]}
        self.assertEqual(reasons, {"no_detections", "occupied"})
        occupied = next(a for a in head["abstentions"]
                        if a["reason"] == "occupied")
        # the cluster geometry travels with the abstention, not beside it
        self.assertEqual(occupied["detail"]["cluster_h_spaces"], 4.5)
        clef = next(s for s in head["verdicts"] if s["quantity"] == Q.CLEF)
        self.assertEqual(clef["outcome"], "abstained")
        self.assertEqual(clef["reason"], "no_candidates")
        self.assertEqual(len(v["glyphs"]), 4)

    def test_evaluate_view_is_empty_where_the_clef_abstained(self):
        """⚠️ EMPTY, AND SAID SO. A staff with no pitch has no `restate_pitch`
        consequence, and the difference between *the stage declined* and *the
        stage never ran on this subject* is the reason the record exists."""
        with_clef = R.staff_stage_view(self.D, "staff/0/0/0", "evaluate")
        without = R.staff_stage_view(self.D, "staff/0/0/1", "evaluate")
        self.assertEqual(len(with_clef["glyphs"]), 4)
        self.assertEqual(len(without["glyphs"]), 0)

    def test_infer_view_reports_its_gates_even_at_reach_zero(self):
        v = R.infer_view(self.D, "staff/0/0/1")
        self.assertTrue(v["did_not_run"])
        self.assertEqual(v["inferences"], [])
        self.assertIn("collapse_slot_index_to_family_block", v["gates"])
        for g in v["gates"].values():
            self.assertTrue(g["env"].startswith("OMR_"))
            self.assertIn("on", g)

    def test_export_view_names_the_bucket_per_head(self):
        v = R.export_view(self.D, "staff/0/0/1")
        self.assertEqual(len(v["heads"]), 4)
        self.assertTrue(all(h["state"] == "refused" for h in v["heads"]))
        self.assertTrue(all(h["refused"] == ["no_pitch"] for h in v["heads"]))
        ok = R.export_view(self.D, "staff/0/0/0")
        self.assertTrue(all(h["state"] == "written" for h in ok["heads"]))
        self.assertEqual(ok["heads"][0]["note"]["step"], "G")
        self.assertEqual(ok["heads"][0]["note"]["octave"], 4)
        self.assertIsNone(ok["heads"][0]["note"]["alter"])
        self.assertEqual(ok["heads"][0]["note"]["type"], "quarter")

    def test_subject_view_keeps_absent_apart_from_declined(self):
        refused = R.subject_view(self.D, "glyph/0/0/1/0/0")
        self.assertEqual(refused["stages"]["gather"]["state"], "read")
        self.assertEqual(refused["stages"]["evaluate"]["state"], "absent")
        self.assertTrue(refused["stages"]["evaluate"]["did_not_run"])
        self.assertEqual(refused["stages"]["export"]["state"], "refused")
        self.assertEqual(refused["stages"]["export"]["buckets"], ["no_pitch"])

        written = R.subject_view(self.D, "glyph/0/0/0/0/0")
        self.assertEqual(written["stages"]["export"]["state"], "written")
        self.assertEqual(written["stages"]["evaluate"]["state"], "read")
        # the rows a verdict read are resolved, not left as ids
        ev = written["stages"]["evaluate"]["verdicts"][0]
        self.assertTrue(all("row" in r for r in ev["rows_read"]))

    def test_staff_level_verdicts_are_shown_on_the_staff_subject(self):
        v = R.subject_view(self.D, "staff/0/0/1")
        quantities = {s["quantity"]
                      for s in v["stages"]["adjudicate"]["verdicts"]}
        self.assertIn(Q.CLEF, quantities)
        self.assertEqual(v["stages"]["gather"]["state"], "read")

    def test_every_view_renders_for_every_staff(self):
        """The blunt one: nothing raises on any staff, either stage state."""
        for staff in self.D.staff_keys:
            with self.subTest(staff=staff):
                R.gather_view(self.D, staff, 2)
                for stage in ("adjudicate", "evaluate"):
                    R.staff_stage_view(self.D, staff, stage)
                R.infer_view(self.D, staff)
                R.export_view(self.D, staff)
                for g in self.D.glyphs_by_staff.get(staff, ()):
                    R.subject_view(self.D, g)


class TestTheAppItself(unittest.TestCase):
    """⚠️⚠️ THIS CLASS EXISTS BECAUSE THE VIEW TESTS ABOVE ALL PASSED WHILE THE
    SERVER COULD NOT START. `create_app` is where FastAPI resolves each
    route's signature through pydantic, and with `from __future__ import
    annotations` a return annotation naming a symbol imported INSIDE
    `create_app` raises `PydanticUndefinedAnnotation` — at start-up, not at
    import. Every function-level test was green; the first real run died
    before it listened. A test that calls the view functions is not a test
    that the app serves them.
    """

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.D = _data(cls.tmp)
        from fastapi.testclient import TestClient
        cls.app = R.create_app(cls.D, cls.tmp / "sidecar.json", "staff/0/0/1")
        cls.c = TestClient(cls.app)

    def test_every_endpoint_answers(self):
        st = "staff/0/0/1"
        self.assertEqual(self.c.get("/").status_code, 200)
        self.assertIn("stage review", self.c.get("/").text.lower())
        for path, params in (
                ("/api/session", {}),
                ("/api/staves", {}),
                ("/api/classes", {}),
                ("/api/gather", {"staff": st}),
                ("/api/crop_meta", {"staff": st}),
                ("/api/stage", {"staff": st, "stage": "adjudicate"}),
                ("/api/stage", {"staff": st, "stage": "evaluate"}),
                ("/api/stage", {"staff": st, "stage": "infer"}),
                ("/api/stage", {"staff": st, "stage": "export"}),
                ("/api/subject", {"key": "glyph/0/0/1/0/0"}),
                ("/api/sidecar", {"staff": st}),
                ("/api/feedback", {"staff": st}),
                ("/api/render.svg", {"staff": st}),
        ):
            with self.subTest(path=path, params=params):
                r = self.c.get(path, params=params)
                self.assertEqual(r.status_code, 200, r.text[:300])

    def test_an_unknown_staff_is_404_not_an_empty_page(self):
        r = self.c.get("/api/gather", params={"staff": "staff/9/9/9"})
        self.assertEqual(r.status_code, 404)

    def test_an_action_is_saved_and_can_be_taken_back(self):
        st = "staff/0/0/1"
        r = self.c.post("/api/sidecar/action", json={
            "staff": st, "stage": "adjudicate", "kind": "disagree",
            "verdict": "vrd:000027", "quantity": "clef",
            "note": "that is an alto clef"})
        self.assertEqual(r.status_code, 200, r.text[:300])
        aid = r.json()["action"]["id"]
        doc = json.loads(Path(r.json()["path"]).read_text())
        self.assertEqual(doc["staff"], st)
        self.assertEqual(doc["actions"][-1]["verdict"], "vrd:000027")
        r = self.c.post("/api/sidecar/undo", json={"staff": st, "id": aid})
        self.assertTrue(r.json()["removed"])

    def test_a_malformed_action_is_400_and_reaches_no_file(self):
        r = self.c.post("/api/sidecar/action", json={
            "staff": "staff/0/0/1", "stage": "adjudicate", "kind": "agree"})
        self.assertEqual(r.status_code, 400)
        self.assertIn("verdict", r.text)

    def test_a_gather_action_is_refused_without_a_crop(self):
        """⚠️ A BOX ON NO RASTER IS NOT EVIDENCE. This fixture has no PDF, so
        the frame control cannot be run — and the box action is REFUSED
        rather than saved with a caveat."""
        r = self.c.post("/api/sidecar/action", json={
            "staff": "staff/0/0/1", "stage": "gather", "kind": "add_box",
            "bbox_page_px": [1, 2, 3, 4], "category": "noteheadBlack"})
        self.assertEqual(r.status_code, 409, r.text[:300])

    def test_rerun_says_so_when_lane_a_is_absent_and_never_fakes_one(self):
        r = self.c.post("/api/rerun", json={"staff": "staff/0/0/1"})
        body = r.json()
        self.assertEqual(r.status_code, 200)
        if not R.rerun_available():
            self.assertFalse(body["available"])
            self.assertIn("not available", body["message"])
            self.assertNotIn("returncode", body)
        else:
            self.assertTrue(body["available"])
            self.assertIn("returncode", body)


class TestTheStaticPageParses(unittest.TestCase):
    """⚠️ THE SECOND THING NO PYTHON TEST COULD SEE. `app.js` shipped with an
    unbalanced parenthesis in the pick list — 27 green tests, a server that
    served it, and a page that rendered nothing at all. Python cannot parse
    JS, so this asks `node`. It SKIPS where node is absent, and a skip is
    reported as a skip."""

    def test_app_js_parses(self):
        import shutil
        import subprocess
        node = shutil.which("node")
        if not node:
            raise unittest.SkipTest("node is not on this machine")
        js = (Path(R.__file__).parent / "static" / "app.js")
        p = subprocess.run([node, "--check", str(js)], capture_output=True,
                           text=True)
        self.assertEqual(p.returncode, 0, p.stderr[:600])


class TestPackageIsRegistered(unittest.TestCase):

    def test_no_staged_module_is_unregistered(self):
        """⚠️ `reach`'s own guard, not a source-text assertion: every `.py`
        under `staged/` must be in `STAGE_OF_FILE` or `NOT_A_STAGE`, and this
        package's `server.py` is a new one. Seen failing before the line was
        added (`reach --check` exited 1 naming `review/server.py`)."""
        self.assertEqual(REACH.unaccounted_modules(), [])


# ─────────────────────────────────────────────────────────────────────────
# 6. ROADMAP 3.4c — THE LABEL SET, AND THE SELECTION PANEL'S PAYLOAD
#
# ⚠️ RUN RED FIRST. Against 2666f383 (before 3.4c) every test in these two
# classes fails: the four label verbs did not exist (`ContractError: kind
# 'relabel_box' is not one of ...`), `/api/labels` 404'd, and `gather_view`
# carried neither `system_staves` nor `size_spaces` (`KeyError`).
# ─────────────────────────────────────────────────────────────────────────

class TestTheLabelVerbsAreOneTable(unittest.TestCase):
    """⚠️ THE POINT IS THAT THERE IS ONE TABLE, NOT THAT THERE ARE FIVE ROWS.
    Sean's ask ends in *"etc."*, so the set has to be extensible in one place
    — and a test that listed the five by name would make adding the sixth a
    two-file change with a red suite in between."""

    def test_the_server_offers_exactly_lane_As_verbs(self):
        from tools.omr.staged.review import human_evidence as HE
        self.assertEqual(
            set(R.KIND_REQUIRES) - {"agree", "disagree"},
            set(HE.KIND_REQUIRES),
            "the viewer and the ingest disagree about which verbs exist — "
            "one of the two refusals is then a lie")
        self.assertEqual(R._GATHER_KINDS, frozenset(HE.GATHER_KINDS))

    def _action_for(self, entry, drop=None):
        action = {"id": "a", "t": "x", "stage": "gather",
                  "kind": entry["kind"]}
        for fld in entry["needs"]:
            if fld == drop:
                continue
            action[fld] = {"category": "clefCAlto", "staff": "staff/3/0/8",
                           "of": "glyph/3/0/9/0/6"}.get(fld,
                                                        "glyph/3/0/9/0/1")
        return action

    def test_every_label_in_the_table_validates_as_an_action(self):
        """⚠️ THE POSITIVE CONTROL for the refusal test below: if the shapes
        this table declares were themselves rejected, that test would pass by
        refusing everything."""
        from tools.omr.staged.review import human_evidence as HE
        for entry in HE.HUMAN_BOX_LABELS:
            with self.subTest(kind=entry["kind"]):
                R.validate_action(self._action_for(entry))

    def test_a_label_missing_its_own_field_is_REFUSED(self):
        from tools.omr.staged.review import human_evidence as HE
        for entry in HE.HUMAN_BOX_LABELS:
            for drop in entry["needs"]:
                with self.subTest(kind=entry["kind"], without=drop):
                    with self.assertRaises(R.ContractError):
                        R.validate_action(self._action_for(entry, drop=drop))

    def test_a_relabel_with_no_category_is_refused_by_the_INGEST_too(self):
        """⚠️ BOTH ENDS, because either end alone is a promise. Lane (B)
        refuses to write it; lane (A) refuses to read it."""
        from tools.omr.staged.review import human_evidence as HE
        good = {"id": "a1", "kind": "relabel_box", "stage": "gather",
                "glyph": "glyph/3/0/9/0/1", "category": "clefCAlto"}
        HE.check_sidecar({"actions": [good]})           # the positive control
        with self.assertRaises(HE.SidecarError):
            HE.check_sidecar({"actions": [
                {k: v for k, v in good.items() if k != "category"}]})


class TestTheSelectionPanelsPayload(unittest.TestCase):
    """What the panel needs, answered by the API rather than by the JS."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.D = _data(cls.tmp)
        cls.staff = "staff/0/0/0"

    def test_a_box_carries_its_size_in_STAFF_SPACES(self):
        """⚠️ Staff spaces, not page pixels: every measured rule in the tree
        is stated in them (`omr-notehead-width-2026-09`'s 1.0-space floor),
        and a panel showing pixels makes the reviewer convert in his head."""
        g = R.gather_view(self.D, self.staff, zoom=2)
        sized = [b for b in g["boxes"] if b["size_spaces"]]
        self.assertTrue(sized, "no box carried a size — the panel would show "
                               "nothing and this test would prove nothing")
        for b in sized:
            self.assertEqual(len(b["size_spaces"]), 2)
            self.assertGreater(b["size_spaces"][0], 0)
        for b in g["boxes"]:
            if not b["bbox_page_px"]:
                self.assertIsNone(
                    b["size_spaces"],
                    "a row with no page rectangle got a size — a canonical "
                    "cell frame cannot answer a page question")

    def test_the_panel_can_offer_the_staff_ABOVE_and_BELOW_by_name(self):
        g = R.gather_view(self.D, self.staff, zoom=2)
        rows = g["system_staves"]
        self.assertEqual([r["staff"] for r in rows],
                         ["staff/0/0/0", "staff/0/0/1"])
        self.assertEqual([r["staff_ordinal"] for r in rows],
                         sorted(r["staff_ordinal"] for r in rows))
        self.assertEqual([r["staff"] for r in rows if r["is_this_one"]],
                         [self.staff])
        for r in rows:
            self.assertIn("part_name", r)

    def test_the_panel_payload_for_a_subject_carries_its_VERDICTS(self):
        """⚠️ THE PANEL RE-USES `/api/subject`, it does not re-derive. Sean's
        ask was *select a box and re-label it*; what makes that a review
        rather than a guess is seeing what the stages already said about it."""
        g = R.gather_view(self.D, self.staff, zoom=2)
        self.assertTrue(g["boxes"], "the fixture staff has no boxes")
        sub = g["boxes"][0]["glyph"]
        v = R.subject_view(self.D, sub)
        self.assertEqual(v["subject"], sub)
        self.assertIn("verdicts", v["stages"]["adjudicate"])
        self.assertIn(v["stages"]["adjudicate"]["state"],
                      ("read", "declined", "absent"))
        self.assertTrue(
            [s["quantity"] for s in v["stages"]["adjudicate"]["verdicts"]],
            "the fixture's own glyph carries no ADJUDICATE verdict, so this "
            "test would pass against a panel that showed none")

    def test_api_labels_is_served_from_lane_As_table(self):
        from fastapi.testclient import TestClient
        from tools.omr.staged.review import human_evidence as HE
        app = R.create_app(self.D, self.tmp / "labels-sc.json", self.staff)
        body = TestClient(app).get("/api/labels").json()
        self.assertEqual([e["kind"] for e in body["labels"]],
                         [e["kind"] for e in HE.HUMAN_BOX_LABELS])
        wants = (body["what_a_human_box_can_and_cannot_reach"]["labels"]
                 ["on_the_machines_own_subject"]["adjudicate_wants"])
        self.assertIn("adjudicate_glyph_owner", wants)
        self.assertIn("adjudicate_notehead_is_not_a_notehead", wants)


# ─────────────────────────────────────────────────────────────────────────
# 7. ROADMAP 3.4d — THE CROP IS THE SCREEN.
#
# Sean, after his second round on the page: *"The UI still feels very hard to
# use — I just want to click a box and type in what I think it is and save
# it, and then be able to draw a box around something that didn't get caught,
# or resize the box for the actual symbol — all without scrolling down the
# page. Make it as simple as you can."*
#
# ⚠️⚠️ THE WORDS AND THE FILTER ARE JAVASCRIPT, SO THESE TESTS ASK `node`.
# A table only the browser can read is a table nothing checks — and the way
# this fails is not a crash: a class with no friendly name, or two classes
# sharing one, is a class he CANNOT TYPE and will never notice is missing.
# Run RED by returning a constant from `friendlyName`: the collision test
# then fails with 157 names collapsed onto one, and the ranking tests fail
# with it.
# ─────────────────────────────────────────────────────────────────────────

_STATIC = Path(R.__file__).parent / "static"


def _node():
    import shutil
    n = shutil.which("node")
    if not n:
        raise unittest.SkipTest("node is not on this machine")
    return n


def _run_js(body: str, payload: dict) -> dict:
    """Run `body` with `L` (labels.js) and `IN` (the payload) in scope; what
    it returns comes back as JSON."""
    import subprocess
    node = _node()
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / "in.json").write_text(json.dumps(payload))
        (d / "run.js").write_text(
            f"const L = require({str(_STATIC / 'labels.js')!r});\n"
            f"const IN = require({str(d / 'in.json')!r});\n"
            f"const OUT = (() => {{\n{body}\n}})();\n"
            "process.stdout.write(JSON.stringify(OUT));\n")
        p = subprocess.run([node, str(d / "run.js")], capture_output=True,
                           text=True)
        if p.returncode != 0:                     # pragma: no cover - a red
            raise AssertionError(p.stderr[:1200])
        return json.loads(p.stdout)


def _canonical_names():
    from tools.omr.class_aliases import canonical, vocabulary
    return sorted({canonical(n) for n in vocabulary()})


class TestTheFriendlyNamesRoundTripEveryClass(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.names = _canonical_names()
        cls.table = _run_js("return L.friendlyTable(IN.names);",
                            {"names": cls.names})

    def test_every_canonical_class_has_a_name(self):
        """⚠️ The fallback is the RAW name, so this cannot fail by accident —
        it fails only where the table returns nothing at all."""
        self.assertEqual(sorted(self.table), self.names)
        blank = [k for k, v in self.table.items() if not v]
        self.assertEqual(blank, [], "a class with no words cannot be typed")

    def test_no_two_classes_share_a_name(self):
        """⚠️ A collision makes ONE OF THE TWO unreachable by typing, and the
        page gives no sign of it: the list shows the same words twice."""
        seen = {}
        clash = []
        for cls, words in sorted(self.table.items()):
            if words in seen:
                clash.append((seen[words], cls, words))
            seen[words] = cls
        self.assertEqual(clash, [])

    def test_a_name_never_collides_with_another_classs_RAW_name(self):
        """The filter matches BOTH spellings, so a friendly name that is
        another class's canonical name would route the query to the wrong
        row."""
        raw = set(self.names)
        bad = [(c, w) for c, w in self.table.items() if w in raw and w != c]
        self.assertEqual(bad, [])

    def test_the_names_a_musician_uses_are_the_ones_on_the_page(self):
        """The handful Sean named, spelled the way a reader says them."""
        for cls, want in (("clefCAlto", "alto clef"),
                          ("accidentalFlat", "flat"),
                          ("keyFlat", "flat (key signature)"),
                          ("restQuarter", "quarter rest"),
                          ("augmentationDot", "dot"),
                          ("dynamicF", "f (dynamic letter)"),
                          ("timeSig4", "4 (time signature)"),
                          ("beam", "beam"), ("stem", "stem"),
                          ("tie", "tie"), ("slur", "slur")):
            with self.subTest(cls=cls):
                self.assertEqual(self.table[cls], want)
        for cls, must in (("noteheadBlackOnLine", "quarter/eighth head"),
                          ("noteheadHalfOnLine", "half head")):
            with self.subTest(cls=cls):
                self.assertIn(must, self.table[cls])


class TestThePopoverFilter(unittest.TestCase):
    """One field, one list. ⚠️ The ranking is the whole design: he types two
    letters and presses Enter, so the FIRST row is the answer."""

    @classmethod
    def setUpClass(cls):
        from tools.omr.staged.review import human_evidence as HE
        cls.payload = {
            "names": _canonical_names(),
            "labels": [{"kind": e["kind"], "label": e["label"]}
                       for e in HE.HUMAN_BOX_LABELS],
            "staves": [
                {"staff": "staff/3/0/8", "part_name": "Oboe",
                 "is_this_one": False},
                {"staff": "staff/3/0/9", "part_name": "Viola",
                 "is_this_one": True},
                {"staff": "staff/3/0/10", "part_name": "Cello",
                 "is_this_one": False}],
            "current": "noteheadBlackOnLine",
            "queries": ["alto", "no", "half head", "flat", "above", "unsure",
                        "dup", "clefCAlto", ""],
        }
        cls.out = _run_js("""
            const items = L.buildAnswers({classes: IN.names, labels: IN.labels,
              staves: IN.staves, current: IN.current});
            const out = {};
            for (const q of IN.queries) {
              out[q] = L.filterAnswers(items, q).slice(0, 5).map(
                i => ({text: i.text, cls: i.cls || null, kind: i.kind,
                       staff: i.staff || null}));
            }
            out['__n'] = items.length;
            return out;
        """, cls.payload)

    def test_alto_finds_the_alto_clef_first(self):
        first = self.out["alto"][0]
        self.assertEqual(first["text"], "alto clef")
        self.assertEqual(first["cls"], "clefCAlto")

    def test_no_finds_NOTHING_first_and_not_a_notehead(self):
        """⚠️ `no` is a prefix of `noteheadBlack…` too, and the notehead list
        is 20 rows long. A human answer outranks a class at the same
        literalness or the fastest answer on the page is the hardest to
        type."""
        first = self.out["no"][0]
        self.assertEqual(first["text"], "nothing")
        self.assertEqual(first["kind"], "delete_box")

    def test_the_human_answers_are_words_not_verbs(self):
        for q, word, kind in (("above", "above", "own_box"),
                              ("unsure", "unsure", "unsure_box"),
                              ("dup", "duplicate", "dup_box")):
            with self.subTest(q=q):
                first = self.out[q][0]
                self.assertEqual(first["text"], word)
                self.assertEqual(first["kind"], kind)
        self.assertEqual(self.out["above"][0]["staff"], "staff/3/0/8",
                         "'above' must name the staff ABOVE this one, from "
                         "the record's own system_staves")

    def test_the_canonical_name_still_works_for_whoever_types_it(self):
        self.assertEqual(self.out["clefCAlto"][0]["cls"], "clefCAlto")

    def test_the_whole_vocabulary_is_offered(self):
        """⚠️ THE POSITIVE CONTROL for every ranking test above: a filter over
        an empty list would satisfy none of them, and a list that had dropped
        half the vocabulary would satisfy all of them."""
        self.assertGreaterEqual(self.out["__n"], len(_canonical_names()))
        self.assertTrue(self.out[""], "an empty query shows nothing at all")


class TestTheBrowsersFrameIsTheSERVERS(unittest.TestCase):
    """⚠️⚠️ The page draws in SCREEN pixels, over a CROP, whose numbers are
    PAGE pixels. `labels.js` owns the last hop and it must be the exact
    inverse of `CropFrame` — in BOTH directions, on a frame whose origin is
    not 0 and whose zoom is not 1 (`TestCropFrame`'s own reason)."""

    FRAME = R.CropFrame(x0=295, y0=1689, x1=2663, y1=1973, zoom=2, dpi=600)
    BOX = [388.5175, 1828.1925, 415.135, 1850.085]
    CROP_BOX = [17.0, 3.0, 201.5, 88.25]

    def test_the_two_conversions_agree_box_for_box(self):
        crop = {"page_px": [295, 1689, 2663, 1973], "zoom": 2,
                "width": self.FRAME.width, "height": self.FRAME.height}
        got = _run_js("""
            return {to_crop: L.boxToCrop(IN.crop, IN.page_box),
                    to_page: L.boxToPage(IN.crop, IN.crop_box),
                    round_trip: L.boxToPage(IN.crop,
                                            L.boxToCrop(IN.crop, IN.page_box))};
        """, {"crop": crop, "page_box": self.BOX, "crop_box": self.CROP_BOX})
        for g, w in zip(got["to_crop"], self.FRAME.box_to_crop(self.BOX)):
            self.assertAlmostEqual(g, w, places=6)
        for g, w in zip(got["to_page"], self.FRAME.box_to_page(self.CROP_BOX)):
            self.assertAlmostEqual(g, w, places=6)
        for g, w in zip(got["round_trip"], self.BOX):
            self.assertAlmostEqual(g, w, places=6)

    def test_it_is_not_the_identity(self):
        """A conversion that dropped the origin and the zoom would round-trip
        just as happily. The hand-computed numbers are the control."""
        self.assertNotEqual(self.FRAME.box_to_crop(self.BOX)[:2], self.BOX[:2])


class TestTheActionsTheScreenPOSTS(unittest.TestCase):
    """⚠️ SHAPE FOR SHAPE WITH YESTERDAY'S. The screen was rebuilt; the
    sidecar was not. Every answer posts the fields this table names and no
    others, and the file on disk carries exactly them plus `id` and `t`.

    ⚠️ The bodies here are the ACTIONS `app.js` builds; `fileAction` merges
    `{review_staff, stage:"gather", note:""}` under each and the route puts
    the first of those aside (see `split_action_body`). A change to either
    side that is not a change to the other fails here rather than in a re-run
    three days later.
    """

    POSTS = {
        "relabel_box": {"stage": "gather", "kind": "relabel_box",
                        "glyph": "glyph/3/0/9/12/4", "category": "clefCAlto",
                        "note": ""},
        "confirm_box": {"stage": "gather", "kind": "confirm_box",
                        "glyph": "glyph/3/0/9/12/4",
                        "category": "noteheadBlackOnLine", "note": ""},
        "delete_box": {"stage": "gather", "kind": "delete_box",
                       "glyph": "glyph/3/0/9/12/4", "note": ""},
        "own_box": {"stage": "gather", "kind": "own_box",
                    "glyph": "glyph/3/0/9/12/4", "staff": "staff/3/0/8",
                    "note": ""},
        "dup_box": {"stage": "gather", "kind": "dup_box",
                    "glyph": "glyph/3/0/9/12/4", "of": "glyph/3/0/9/12/5",
                    "note": ""},
        "unsure_box": {"stage": "gather", "kind": "unsure_box",
                       "glyph": "glyph/3/0/9/12/4", "note": ""},
        "add_box": {"stage": "gather", "kind": "add_box",
                    "bbox_page_px": [388.5, 1828.1, 415.1, 1850.0],
                    "crop_px": [187.0, 278.3, 240.2, 322.1],
                    "cell": "cell/3/0/9/12", "category": "noteheadBlack",
                    "note": ""},
        "redraw_box": {"stage": "gather", "kind": "redraw_box",
                       "glyph": "glyph/3/0/9/12/4",
                       "bbox_page_px": [390.0, 1830.0, 417.0, 1852.0],
                       "prior_bbox_page_px": [388.5, 1828.1, 415.1, 1850.0],
                       "crop_px": [190.0, 282.0, 244.0, 326.0],
                       "note": ""},
    }

    def test_every_answer_validates_and_lands_unchanged(self):
        tmp = Path(tempfile.mkdtemp())
        path = tmp / "review-actions.json"
        sc = R.Sidecar(path, record="rec.json", staff="staff/3/0/9")
        for name, body in self.POSTS.items():
            with self.subTest(answer=name):
                saved = sc.append(dict(body))
                self.assertEqual(set(saved) - {"id", "t"}, set(body))
                for k, v in body.items():
                    self.assertEqual(saved[k], v)
        doc = json.loads(path.read_text())
        self.assertEqual(len(doc["actions"]), len(self.POSTS))
        for a in doc["actions"]:
            R.validate_action(a)

    def test_the_ingest_requires_exactly_what_the_screen_sends(self):
        """⚠️ BOTH ENDS. The table above is checked against lane (A)'s
        `KIND_REQUIRES` rather than against a copy of it."""
        from tools.omr.staged.review import human_evidence as HE
        for kind, needs in HE.KIND_REQUIRES.items():
            with self.subTest(kind=kind):
                self.assertIn(kind, self.POSTS,
                              f"the screen posts nothing for {kind!r} — a "
                              f"verb the ingest knows and the page cannot "
                              f"reach")
                for fld in needs:
                    self.assertIn(fld, self.POSTS[kind])

    def test_a_drawn_rectangle_with_no_class_is_refused(self):
        """⚠️ Nothing is saved until a class is chosen: a human box with no
        name is `Q.INK`, which GATHER already files."""
        with self.assertRaises(R.ContractError):
            R.validate_action({"id": "a", "t": "x", "stage": "gather",
                               "kind": "add_box",
                               "bbox_page_px": [1, 2, 3, 4]})


class TestTheAgreementOnABox(unittest.TestCase):
    """ROADMAP 3.4d. Typing the class the machine already gave the box is an
    ANSWER, and it is filed.

    ⚠️ IT IS NOT `agree`. That verb is a stance on a VERDICT and lane (A)
    resolves it with `verdict_by_id`; a detector box is an Observation of
    `Q.GLYPH_BOX`, so an `agree` naming one would be refused as naming
    nothing. This class is the control on that claim.
    """

    def test_agree_on_an_observation_id_names_nothing(self):
        from tools.omr.staged.review import human_evidence as HE
        rec = fixture_record()["record"]
        obs_id = next(o["id"] for o in rec["observations"]
                      if o["quantity"] == Q.GLYPH_BOX)
        self.assertIsNone(HE.verdict_by_id(rec, obs_id))
        self.assertIsNotNone(
            HE.verdict_by_id(rec, rec["verdicts"][0]["id"]),
            "the positive control failed — `verdict_by_id` finds no verdict "
            "at all, so the assertion above proves nothing")

    def test_confirm_box_is_one_row_in_lane_As_table(self):
        from tools.omr.staged.review import human_evidence as HE
        entry = next(e for e in HE.HUMAN_BOX_LABELS
                     if e["kind"] == "confirm_box")
        self.assertEqual(tuple(entry["needs"]), ("glyph", "category"))
        self.assertIn("confirm_box", HE.GATHER_KINDS)
        self.assertIn("confirm_box", R.KIND_REQUIRES)
        HE.check_sidecar({"actions": [
            {"id": "c1", "kind": "confirm_box", "stage": "gather",
             "glyph": "glyph/3/0/9/0/1", "category": "noteheadBlackOnLine"}]})
        with self.assertRaises(HE.SidecarError):
            HE.check_sidecar({"actions": [
                {"id": "c1", "kind": "confirm_box", "stage": "gather",
                 "glyph": "glyph/3/0/9/0/1"}]})

    def test_the_value_parses_to_a_verb_NO_DECISION_ACTS_ON(self):
        """⚠️ `human_says` is the one parser. `confirmed` must come back as
        its own verb — not as `not_a_symbol`, and not as an `is_a`, which
        would make an agreement REFUSE the head it agreed with."""
        from tools.omr.staged.review import human_evidence as HE
        verb, arg = HE.human_says("confirmed:noteheadBlackOnLine")
        self.assertEqual((verb, arg), ("confirmed", "noteheadBlackOnLine"))
        self.assertNotIn(verb, ("not_a_symbol", "is_a", "owner",
                                "duplicate_of"))


class TestTheStaticPageIsOneSCREEN(unittest.TestCase):
    """⚠️ Sean's sentence ends *"all without scrolling down the page"*, and
    the only way a browser cannot put something under the fold is
    `overflow:hidden` on the body. Checked on the SERVED files, because a
    page that scrolls is exactly the complaint."""

    def test_the_body_cannot_scroll(self):
        css = (_STATIC / "app.css").read_text()
        self.assertRegex(css, r"body\s*\{[^}]*overflow\s*:\s*hidden")

    def test_the_page_loads_the_words_before_the_screen(self):
        html = (_STATIC / "index.html").read_text()
        self.assertLess(html.index("labels.js"), html.index("app.js"),
                        "app.js reads labels.js's globals at boot")

    def test_both_scripts_parse(self):
        import subprocess
        node = _node()
        for name in ("labels.js", "app.js"):
            with self.subTest(file=name):
                p = subprocess.run([node, "--check", str(_STATIC / name)],
                                   capture_output=True, text=True)
                self.assertEqual(p.returncode, 0, p.stderr[:600])


class TestTheRouteKeepsTheTWOSTAVESApart(unittest.TestCase):
    """⚠️⚠️ FOUND IN THE BROWSER, NOT IN A TEST. *"belongs to the staff
    above"* is one of Sean's five answers and it could not be filed at all:
    the viewer spread the action over the POST body, `own_box`'s own `staff`
    (the OWNER) won the key the route uses for the staff being REVIEWED, and
    the route then stripped it as its own parameter — so every `own_box`
    came back `400 'own_box' needs 'staff'`.

    ⚠️ Invisible to every test here, and this says why: the fixture has no
    PDF, so a GATHER action is refused by the frame control (409) BEFORE it
    is ever validated. The 409 below is therefore the positive control that
    the body was split correctly — a 400 means it was not.
    """

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.D = _data(cls.tmp)
        from fastapi.testclient import TestClient
        cls.c = TestClient(R.create_app(cls.D, cls.tmp / "two-staves.json",
                                        "staff/0/0/0"))

    def test_the_owner_survives_the_split(self):
        staff, action = R.split_action_body({
            "review_staff": "staff/0/0/0", "stage": "gather",
            "kind": "own_box", "glyph": "glyph/0/0/0/0/1",
            "staff": "staff/0/0/1", "note": ""})
        self.assertEqual(staff, "staff/0/0/0")
        self.assertEqual(action["staff"], "staff/0/0/1")
        R.validate_action({"id": "a", "t": "x", **action})

    def test_a_kind_with_no_staff_field_still_reads_the_old_way(self):
        staff, action = R.split_action_body({
            "staff": "staff/0/0/0", "stage": "gather", "kind": "delete_box",
            "glyph": "glyph/0/0/0/0/1"})
        self.assertEqual(staff, "staff/0/0/0")
        self.assertNotIn("staff", action)

    def test_the_AMBIGUOUS_body_is_refused_rather_than_guessed(self):
        with self.assertRaises(R.ContractError):
            R.split_action_body({"staff": "staff/0/0/1", "stage": "gather",
                                 "kind": "own_box",
                                 "glyph": "glyph/0/0/0/0/1"})

    def test_own_box_reaches_the_frame_control_instead_of_a_400(self):
        r = self.c.post("/api/sidecar/action", json={
            "review_staff": "staff/0/0/0", "stage": "gather",
            "kind": "own_box", "glyph": "glyph/0/0/0/0/1",
            "staff": "staff/0/0/1", "note": ""})
        self.assertEqual(r.status_code, 409, r.text[:300])
        self.assertIn("no crop", r.text)

    def test_the_old_ambiguous_shape_is_a_400_that_SAYS_WHY(self):
        r = self.c.post("/api/sidecar/action", json={
            "staff": "staff/0/0/1", "stage": "gather", "kind": "own_box",
            "glyph": "glyph/0/0/0/0/1"})
        self.assertEqual(r.status_code, 400)
        self.assertIn("review_staff", r.text)
