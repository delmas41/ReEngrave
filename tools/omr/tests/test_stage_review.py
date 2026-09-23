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
