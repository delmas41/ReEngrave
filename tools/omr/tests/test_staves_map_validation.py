"""The confirmation UI must refuse exactly what the merge step refuses.

⚠️ THE GAP THESE TESTS CLOSE. `merge_additions` proves a map by running
`page_normalise.normalise` on the row's own trimmed truth before it writes
`works.json`. Until 2026-09-07 the UI (`server.py`) re-implemented only the
CHEAP structural checks — every part named once, no part named twice, every
staff decided — and never called `page_normalise` at all. So a row could go
green staff by staff, be marked `done`, and refuse at merge time with the
human's whole confirmation pass already spent. Two `page_normalise` faults did
exactly that to Mahler p3 and p4 (`benchmarks/omr-page-normalise-fixes-2026-09/
FINDINGS.md`).

The repair is one shared prover — `merge_additions.prove_normalises` — called
by both. A second implementation would reopen the gap one level down, so the
first test here is an ANTI-DRIFT source assertion in the shape of
`TestEventlessMeasureKeepsItsMarks`: both call sites must exist.

⚠️ AND THE SECOND PRIORITY IS ABOVE THE FIRST: a validation failure must never
cost a verdict. Sean's decisions are irreplaceable human work and the proof is
a nicety beside them, so a prover that RAISES must leave the verdict saved and
say only that the check could not run.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
MAPS = ROOT / "benchmarks" / "omr-staves-map-2026-09"
SCAN = ROOT / "benchmarks" / "omr-scan-e2e-2026-09"


def _load(name: str, directory: Path):
    path = directory / f"{name}.py"
    if not path.is_file():
        pytest.skip(f"{path} not present")
    for d in (SCAN, MAPS):
        if str(d) not in sys.path:
            sys.path.insert(0, str(d))
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _score(tmp_path: Path, n_parts: int = 3) -> Path:
    from music21 import note, stream

    score = stream.Score()
    for i, pitch in enumerate(("C5", "E5", "G5")[:n_parts]):
        part = stream.Part(id=f"P{i}")
        part.partName = f"P{i}"
        m = stream.Measure(number=1)
        m.append(note.Note(pitch, quarterLength=4.0))
        part.append(m)
        score.append(part)
    out = tmp_path / "truth.musicxml"
    score.write("musicxml", fp=str(out))
    return out


# ------------------------------------------------------------- anti-drift

class TestOneProverServesBothCallers:
    """⚠️ Verified to fail when either call site is removed."""

    def test_the_prover_exists_and_runs_page_normalise(self):
        src = (MAPS / "merge_additions.py")
        if not src.is_file():
            pytest.skip("merge_additions.py not present")
        text = src.read_text()
        assert "def prove_normalises(" in text
        body = text.split("def prove_normalises(", 1)[1].split("\ndef ", 1)[0]
        assert "page_normalise.normalise(" in body, \
            "the shared prover must be the thing that calls page_normalise"

    def test_the_merge_step_asks_it(self):
        src = MAPS / "merge_additions.py"
        if not src.is_file():
            pytest.skip("merge_additions.py not present")
        text = src.read_text()
        after = text.split("def check_row(", 1)[1].split("\ndef ", 1)[0]
        assert "prove_normalises(" in after, \
            "check_row must prove the map through the shared prover"

    def test_the_confirmation_ui_asks_it_too(self):
        src = MAPS / "server.py"
        if not src.is_file():
            pytest.skip("server.py not present")
        text = src.read_text()
        assert "from merge_additions import prove_normalises" in text, \
            "the UI must import the SHARED prover, never re-implement it"
        assert "prove_normalises(" in text
        assert "prover.wait(" in text, \
            "`done` must consult the proof, not only the cheap checks"

    def test_the_ui_does_not_reimplement_page_normalise(self):
        src = MAPS / "server.py"
        if not src.is_file():
            pytest.skip("server.py not present")
        text = src.read_text()
        assert "page_normalise.normalise(" not in text, \
            ("a second call site is a second implementation waiting to drift "
             "— go through prove_normalises")


# ------------------------------------------------ what the prover decides

class TestTheSharedProver:

    def test_it_accepts_a_map_that_normalises(self, tmp_path, monkeypatch):
        ma = _load("merge_additions", MAPS)
        truth = _score(tmp_path)
        monkeypatch.setattr(ma, "find_fixture", lambda *a, **k: (truth, None))
        got = ma.prove_normalises(
            "row", [{"name": "A", "parts": [0, 1]}, {"name": "B", "parts": [2]}])
        assert got["ok"] is True
        assert got["unavailable"] is False
        assert got["normalised"]["n_source_parts"] == 3
        assert got["normalised"]["n_output_parts"] == 2

    def test_it_refuses_a_map_page_normalise_refuses(self, tmp_path, monkeypatch):
        """The map is shapely and complete-looking and still cannot merge."""
        ma = _load("merge_additions", MAPS)
        truth = _score(tmp_path)
        monkeypatch.setattr(ma, "find_fixture", lambda *a, **k: (truth, None))
        got = ma.prove_normalises("row", [{"name": "A", "parts": [0, 1]}])
        assert got["ok"] is False
        assert got["unavailable"] is False, \
            "a REFUSAL is not an unavailable check — the two are acted on " \
            "differently by the two callers"
        assert "IncompleteMap" in got["problem"]

    def test_a_missing_fixture_is_unavailable_not_a_refusal(self, monkeypatch):
        ma = _load("merge_additions", MAPS)
        monkeypatch.setattr(ma, "find_fixture", lambda *a, **k: (None, None))
        got = ma.prove_normalises("row", [{"name": "A", "parts": [0]}])
        assert got["ok"] is False
        assert got["unavailable"] is True


# ------------------------------------- what the UI does with that verdict

class TestDoneIsBlockedByTheSameThing:

    def test_a_refused_proof_blocks_done(self):
        srv = _load("server", MAPS)
        got = srv.done_problems(
            {"problems": []},
            {"state": "refused", "problem": "page_normalise REFUSED this map: x"})
        assert got and "REFUSED" in got[0]

    def test_a_proof_that_could_not_run_does_NOT_block_done(self):
        """⚠️ Deliberate asymmetry with `check_row`, which DOES refuse on it.

        The UI writes only the additions file; blocking Sean's keystroke over a
        fixture missing from this machine would cost more than it protects, and
        the merge step still refuses before anything reaches `works.json`.
        """
        srv = _load("server", MAPS)
        assert srv.done_problems(
            {"problems": []},
            {"state": "unavailable", "problem": "no truth on disk"}) == []

    def test_structural_problems_still_block(self):
        srv = _load("server", MAPS)
        got = srv.done_problems({"problems": ["3 staves not yet decided"]},
                                {"state": "ok", "problem": None})
        assert got == ["3 staves not yet decided"]

    def test_both_problems_are_reported_together(self):
        """Never one at a time: a human fixing the first should see the second."""
        srv = _load("server", MAPS)
        got = srv.done_problems({"problems": ["a"]},
                                {"state": "refused", "problem": "b"})
        assert got == ["a", "b"]


# ------------------------------------------------- the priority above all

class TestAProofFailureNeverCostsAVerdict:

    def test_a_prover_that_raises_is_reported_not_propagated(self):
        srv = _load("server", MAPS)
        prover = srv.Prover()

        def boom(*a, **k):
            raise RuntimeError("music21 exploded")

        got = prover._compute("row", [{"name": "A", "parts": [0]}], None)
        assert isinstance(got, dict)
        srv.prove_normalises = boom            # module-level, what _compute calls
        got = prover._compute("row", [{"name": "A", "parts": [0]}], None)
        assert got["state"] == "unavailable"
        assert "could not run" in got["problem"]
        assert srv.done_problems({"problems": []}, got) == [], \
            "a check that fell over must not block the human"

    def test_the_verdict_is_stored_before_any_proof_is_asked_for(self):
        """SOURCE-level: `store.save()` precedes `check(...)` in every mutator.

        A behavioural test would only exercise whichever path its fixture
        happens to take; this asserts the ordering that makes the property
        true for all of them.
        """
        src = MAPS / "server.py"
        if not src.is_file():
            pytest.skip("server.py not present")
        text = src.read_text()
        for route in ("def api_patch(", "def api_insert(", "def api_delete("):
            body = text.split(route, 1)[1].split("\n    @app.", 1)[0]
            assert "store.save()" in body, f"{route} must persist"
            assert body.index("store.save()") < body.index("check(seed, st)"), \
                f"{route} asks for validation BEFORE it saves — a proof that " \
                f"raised could then cost a verdict"

    def test_the_fingerprint_ignores_verdicts(self):
        """The confirmation keystroke must not re-run the proof.

        A pass is ~20 verdict keystrokes per row and one map, so keying the
        cache on the MAP (name + parts) is what keeps the UI at ~3 ms.
        """
        srv = _load("server", MAPS)
        a = [{"name": "A", "parts": [0, 1], "verdict": "pending"}]
        b = [{"name": "A", "parts": [0, 1], "verdict": "confirmed"}]
        assert srv.Prover.fingerprint("r", a) == srv.Prover.fingerprint("r", b)
        c = [{"name": "A", "parts": [0]}]
        assert srv.Prover.fingerprint("r", a) != srv.Prover.fingerprint("r", c)


# ------------------------------- `parts` is ORDERED, and the order is meaning

class TestPartsOrderIsMeaningfulAndPreserved:
    """⚠️ MEASURED, not argued (2026-09-07, on a finished human pass).

    `merge_additions` refused three `done` rows for `parts` "not sorted-unique"
    and the proposed repair was to sort them. `page_normalise.normalise` does
    `keep = parts[idx[0]]` and merges the rest into it, so the FIRST index
    decides which reference part the merged staff IS.

    Priced both ways on those rows' own maps
    (`benchmarks/omr-page-normalise-fixes-2026-09/probe_parts_order*.py`):

      * the NOTES do not move — 15/15, 21/21, 21/21 output parts compare
        bar-for-bar identical;
      * the IDENTITY does. Sorting puts the silent tacet-folded Piccolo first,
        so `Zwei Fagotte.`, `Drei Hoboen.` and `Drei Klarinetten in A` all come
        back named `Piccolo`;
      * and musicdiff re-pairs on the wrong name: -3, +19, -8 edits, +8 net.

    So sortedness is not a spelling of the same truth. Uniqueness is still
    required — a staff cannot carry one part twice.
    """

    def test_an_unsorted_entry_is_accepted(self):
        ma = _load("merge_additions", MAPS)
        # the real shape of the 2026-09-07 pass: printed part first, folds after
        got = ma.shape_problems(
            [{"name": "Fag. 1/2", "parts": [10, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9]}])
        assert got == [], f"an unsorted map is legal; got {got}"

    def test_a_repeated_part_within_one_entry_still_refuses(self):
        ma = _load("merge_additions", MAPS)
        got = ma.shape_problems([{"name": "A", "parts": [3, 4, 3]}])
        assert got and "twice" in got[0]

    def test_the_other_shape_refusals_are_untouched(self):
        ma = _load("merge_additions", MAPS)
        assert ma.shape_problems([]), "an empty map must still refuse"
        assert ma.shape_problems([{"name": "", "parts": [0]}])
        assert ma.shape_problems([{"name": "A", "parts": []}])
        assert ma.shape_problems([{"name": "A", "parts": [0], "extra": 1}])

    def test_a_part_named_by_two_staves_still_refuses(self, tmp_path, monkeypatch):
        """The cross-entry duplicate — caught by check_row, not shape_problems."""
        ma = _load("merge_additions", MAPS)
        truth = _score(tmp_path, n_parts=3)
        monkeypatch.setattr(ma, "find_fixture", lambda *a, **k: (truth, None))
        row = {"reference": {"catalog_path": "x"}}
        add = {"status": "done", "staves_for_works_json": [
            {"name": "A", "parts": [0, 1]}, {"name": "B", "parts": [1, 2]}]}
        got = ma.check_row("row", row, add)
        assert any("more than one staff" in p for p in got["problems"])

    def test_an_unaccounted_part_still_refuses(self, tmp_path, monkeypatch):
        ma = _load("merge_additions", MAPS)
        truth = _score(tmp_path, n_parts=3)
        monkeypatch.setattr(ma, "find_fixture", lambda *a, **k: (truth, None))
        row = {"reference": {"catalog_path": "x"}}
        add = {"status": "done",
               "staves_for_works_json": [{"name": "A", "parts": [0, 1]}]}
        got = ma.check_row("row", row, add)
        assert got["problems"], "dropping part 2 must still be refused"

    def test_the_ui_does_not_sort_a_human_edit(self):
        """SOURCE-level: the editor de-duplicates, it does not canonicalise."""
        src = (MAPS / "server.py").read_text()
        assert "sorted(set(patch.parts))" not in src, \
            ("sorting an edited entry renames the printed staff after a "
             "silent folded part — measured")
        assert "list(dict.fromkeys(patch.parts))" in src


COMPLETION = ROOT / "benchmarks" / "omr-staves-map-completion-2026-09"


class TestUnrepresentableStavesAreShownNotOmitted:
    """A printed staff the reference cannot represent must be VISIBLE.

    ⚠️ THE FAULT THIS CLOSES WAS FOUND BY A HUMAN COUNTING THE PAGE. Mahler p2
    prints 22 staves and its map has 21 entries: the reference writes Becken
    and Grosse Trommel as their own parts and has none for the combined
    `Becken u. Gr.Trommel von einem geschlagen` player, so no entry could name
    a part and `page_normalise` refuses an entry whose `parts` is empty. The
    exclusion is right. What was wrong is that the UI listed 21 rows and said
    nothing, so a reader checking the list against the print found a staff
    missing with no way to tell a deliberate exclusion from a bug.

    ⚠️ AND THE OPPOSITE FAILURE IS WORSE. These are not map entries. If one
    ever reached `staves` it would be an entry naming no part, which is exactly
    what `page_normalise` raises on -- so the display path and the decision
    path must stay separate.
    """

    def _maps(self):
        return _load("candidate_maps", COMPLETION)

    def test_every_entry_carries_a_position_and_a_reason(self):
        cm = self._maps()
        assert cm.UNREPRESENTABLE, "the record must not be empty"
        for row_id, entries in cm.UNREPRESENTABLE.items():
            for e in entries:
                assert isinstance(e, dict), \
                    f"{row_id}: a bare string cannot be placed in the list"
                for key in ("name", "after", "lines", "reason"):
                    assert key in e, f"{row_id}: missing {key!r}"
                assert e["reason"].strip(), f"{row_id}: empty reason"

    def test_after_names_a_real_entry_of_that_rows_map(self):
        """Otherwise the row is placed nowhere and silently vanishes again."""
        cm = self._maps()
        for row_id, entries in cm.UNREPRESENTABLE.items():
            names = {s["name"] for s in cm.CANDIDATES[row_id]}
            for e in entries:
                if e["after"] is None:
                    continue
                assert e["after"] in names, (
                    f"{row_id}: after={e['after']!r} names no map entry; "
                    f"the greyed row would be orphaned")

    def test_an_unrepresentable_staff_is_never_a_map_entry(self):
        """The safety property: display path and decision path stay apart."""
        cm = self._maps()
        for row_id, entries in cm.UNREPRESENTABLE.items():
            names = {s["name"] for s in cm.CANDIDATES[row_id]}
            for e in entries:
                assert e["name"] not in names, (
                    f"{row_id}: {e['name']!r} is BOTH unrepresentable and a "
                    f"map entry — page_normalise would refuse the map")

    def test_mahler_p2_places_it_between_the_two_drums(self):
        """The concrete case, against the print: it is printed below Gr.Tr."""
        cm = self._maps()
        e = cm.UNREPRESENTABLE["mahler-sym5-mvt1-local-p2"][0]
        assert e["after"] == "Grosse Trommel"
        assert e["lines"] == 1
        order = [s["name"] for s in cm.CANDIDATES["mahler-sym5-mvt1-local-p2"]]
        # the next printed staff below it is the Kleine Trommel
        assert order[order.index("Grosse Trommel") + 1] == "Kleine Trommel"

    def test_the_ui_renders_them_and_never_makes_them_clickable(self):
        """Source assertion — the render path is JS and has no unit seam."""
        src = (MAPS / "server.py").read_text()
        assert "unrepresentable_printed_staves" in src, \
            "the UI must read the record"
        assert "staffrow unrep" in src, "no greyed row is emitted"
        assert ".staffrow.unrep{cursor:default" in src, \
            "a greyed row must not look or behave clickable"


class TestTheINITIALProposalIsUnsortedToo:
    """⚠️ THE HALF THAT WAS UNGUARDED, AND IT WAS LUCK THAT SAVED p3.

    `833afe9f` split `shape_problems`' `sorted-unique` into uniqueness (a real
    invariant) and sortedness (a canonicalisation that MOVES the answer) and
    dropped the second — but only the EDITED path was pinned. The INITIAL
    proposal, `build_cache.research_proposal`, still called `sorted()`, under a
    comment justifying it by the rule that had been removed **the same day**
    (`71b26806` wrote the comment; `833afe9f` removed its reason) and whose own
    closing sentence said *"works.json's convention wins"*.

    `page_normalise.normalise` does `keep = parts[idx[0]]`, so `parts[0]`
    decides which reference part the merged staff IS. Sorting a tacet fold
    ahead of the printed part renamed `Zwei Fagotte.`, `Drei Hoboen.` and
    `Drei Klarinetten in A` all to **Piccolo**.

    Sean's p3 pass matched works.json on 15 of 15 entries EXCEPT entry 0
    `Fag. 1/2`. The only thing that stopped the sorted proposal reaching a row
    was the unrelated "works.json already has a map" refusal.
    """

    def _proposals(self):
        bc = _load("build_cache", MAPS)
        completion = MAPS.parent / "omr-staves-map-completion-2026-09"
        if not (completion / "candidate_maps.py").is_file():
            pytest.skip("candidate_maps not present")
        return bc

    def test_the_proposal_puts_the_PRINTED_part_first_and_the_folds_after(self):
        bc = self._proposals()
        sys.path.insert(0, str(MAPS.parent / "omr-staves-map-completion-2026-09"))
        import candidate_maps                                    # noqa: E402
        seen_a_fold = False
        for row_id, entries in candidate_maps.CANDIDATES.items():
            got = bc.research_proposal(row_id, n_parts=64)
            by_name = {s["name"]: s for s in got["staves"]}
            for spec in entries:
                if not spec.get("absent"):
                    continue
                seen_a_fold = True
                s = by_name[spec["name"]]
                assert s["parts"] == list(spec["parts"]) + list(spec["absent"]), \
                    f"{row_id}/{spec['name']}: the proposal re-ordered `parts`"
                assert s["parts"][0] in spec["parts"], \
                    (f"{row_id}/{spec['name']}: parts[0] is a FOLD, so "
                     f"page_normalise would name the merged staff after a "
                     f"silent part")
        assert seen_a_fold, "no folded entry exercised — the test is vacuous"

    def test_the_proposal_reproduces_works_json_on_every_row_already_merged(self):
        """⚠️ THE CONTROL THAT MAKES THE ABOVE A RESULT: ask the TREE.

        `works.json` already holds these rows, confirmed by hand against the
        print. The proposal must agree with it entry for entry — and the
        SORTED proposal did not, on exactly the three entries
        `merge_additions`' own note names."""
        import json
        bc = self._proposals()
        sys.path.insert(0, str(MAPS.parent / "omr-staves-map-completion-2026-09"))
        import candidate_maps                                    # noqa: E402
        works = json.loads((SCAN / "works.json").read_text())
        rows = {r["row_id"]: r for r in works["rows"]}
        compared = 0
        for row_id in candidate_maps.CANDIDATES:
            held = rows.get(row_id, {}).get("staves")
            if not held:
                continue
            proposed = {s["name"]: s["parts"]
                        for s in bc.research_proposal(row_id, 64)["staves"]}
            for entry in held:
                if entry["name"] not in proposed:
                    continue
                compared += 1
                assert proposed[entry["name"]] == entry["parts"], (
                    f"{row_id}/{entry['name']}: proposal "
                    f"{proposed[entry['name']]} against the confirmed "
                    f"{entry['parts']}")
        assert compared > 10, f"only {compared} entries compared"

    def test_the_proposal_still_passes_the_merge_steps_own_shape_check(self):
        bc = self._proposals()
        ma = _load("merge_additions", MAPS)
        sys.path.insert(0, str(MAPS.parent / "omr-staves-map-completion-2026-09"))
        import candidate_maps                                    # noqa: E402
        for row_id in candidate_maps.CANDIDATES:
            staves = [{"name": s["name"], "parts": s["parts"]}
                      for s in bc.research_proposal(row_id, 64)["staves"]]
            assert ma.shape_problems(staves) == [], row_id

    def test_the_source_no_longer_canonicalises(self):
        """SOURCE-level, the same shape as `test_the_ui_does_not_sort_a_human
        _edit`: the proposal builder must not re-introduce a sort."""
        text = (MAPS / "build_cache.py").read_text()
        assert 'sorted(list(spec["parts"])' not in text, \
            "research_proposal is canonicalising `parts` again"


# ------------------------------------------- the arity fields, and their guard

class TestTheWriterCanCarryTheArityFields:
    """⚠️ THE FIELDS EXISTED AND THE WRITER REFUSED THEM.

    `lines` landed in `166759fc`; `shape_problems` predates it and demanded
    entries be "exactly name+parts", so a CORRECT map carrying `lines: 1` would
    have been rejected at merge time — while `build_cache.research_proposal`
    computed `"lines": spec.get("lines", 5)` for every entry and four
    projections down the path threw it away. mahler p2's hand-confirmed
    21-staff map arrived unflagged, its page stayed unassessable, and the only
    thing that noticed was `test_works_json_staff_lineup.py` — a test on the
    FILE, which fires after the human pass is spent.
    `benchmarks/omr-part-join-2026-09/FINDINGS.md` §7.
    """

    def test_a_one_line_rule_is_accepted(self):
        ma = _load("merge_additions", MAPS)
        assert ma.shape_problems([{"name": "Becken", "parts": [23],
                                   "lines": 1}]) == []

    def test_an_entry_printed_as_several_staves_is_accepted(self):
        ma = _load("merge_additions", MAPS)
        assert ma.shape_problems([{"name": "Cembalo", "parts": [9],
                                   "printed_staves": 2}]) == []

    def test_an_unknown_key_STILL_refuses(self):
        """Allowing two named fields is not allowing anything."""
        ma = _load("merge_additions", MAPS)
        assert ma.shape_problems([{"name": "A", "parts": [0], "extra": 1}])

    def test_a_lines_value_the_file_does_not_model_refuses(self):
        """⚠️ ALLOWED IS NOT UNCHECKED. A typo'd `lines` silently changes how
        many parts the row is expected to emit — the exact failure these
        fields exist to prevent — so a surprising value is LOUD."""
        ma = _load("merge_additions", MAPS)
        assert ma.shape_problems([{"name": "A", "parts": [0], "lines": 3}])
        assert ma.shape_problems([{"name": "A", "parts": [0], "lines": "1"}])

    def test_printed_staves_must_be_a_positive_int(self):
        ma = _load("merge_additions", MAPS)
        assert ma.shape_problems([{"name": "A", "parts": [0],
                                   "printed_staves": 0}])
        assert ma.shape_problems([{"name": "A", "parts": [0],
                                   "printed_staves": True}])

    def test_a_one_line_rule_cannot_also_be_several_printed_staves(self):
        ma = _load("merge_additions", MAPS)
        assert ma.shape_problems([{"name": "A", "parts": [0], "lines": 1,
                                   "printed_staves": 2}])

    def test_a_malformed_value_REFUSES_rather_than_RAISES(self):
        """A validator must refuse bad input, never raise on it — `int()` on an
        arbitrary value does raise, and this one is reached from the merge
        step's own error path."""
        ma = _load("merge_additions", MAPS)
        for bad in ({"name": "A", "parts": [0], "lines": "abc"},
                    {"name": "A", "parts": [0], "lines": None},
                    {"name": "A", "parts": [0], "printed_staves": "2"}):
            assert ma.shape_problems([bad]), bad

    def test_the_projection_preserves_them(self):
        ma = _load("merge_additions", MAPS)
        got = ma._entry_for_works_json(
            {"name": "Becken", "parts": [23], "lines": 1, "verdict": "confirmed"})
        assert got == {"name": "Becken", "parts": [23], "lines": 1}

    def test_the_projection_omits_the_defaults(self):
        """Every merged row omits `lines: 5`; writing it would make this
        writer's output differ from the file it appends to."""
        ma = _load("merge_additions", MAPS)
        got = ma._entry_for_works_json(
            {"name": "Pauken", "parts": [22], "lines": 5, "printed_staves": 1})
        assert got == {"name": "Pauken", "parts": [22]}


class TestTheArityGuardRunsBeforeTheWrite:
    """The guard `test_works_json_staff_lineup.py` asks of the FILE, asked
    HERE — so the merge refuses instead of the suite failing afterwards."""

    def _row(self):
        import json
        works = json.loads((SCAN / "works.json").read_text())
        rows = {r["row_id"]: r for r in works["rows"]}
        return rows["mahler-sym5-mvt1-local-p2"]

    def test_THE_REAL_MAP_THAT_SLIPPED_THROUGH_is_refused(self):
        """⚠️ THE DECISIVE CASE, and it is not synthetic: this is mahler p2's
        map exactly as `1cf44dbc` merged it."""
        ma = _load("merge_additions", MAPS)
        row = self._row()
        as_merged = [{"name": s["name"], "parts": list(s["parts"])}
                     for s in row["staves"]]
        problems = ma.arity_problems(row, as_merged)
        assert problems, "the map that actually slipped through must refuse"
        assert "21" in problems[0] and "17" in problems[0]
        assert "lines" in problems[0], "the message must name the missing field"

    def test_the_repaired_map_is_accepted(self):
        ma = _load("merge_additions", MAPS)
        row = self._row()
        assert ma.arity_problems(row, row["staves"]) == []

    def test_check_row_asks_it(self):
        """Anti-drift, in the shape of `test_the_merge_step_asks_it`: the guard
        is worthless if the write path does not call it."""
        text = (MAPS / "merge_additions.py").read_text()
        after = text.split("def check_row(", 1)[1].split("\ndef ", 1)[0]
        assert "arity_problems(" in after

    def test_it_reuses_expand_lineup_rather_than_recomputing(self):
        """⚠️ `run_ledger.expand_lineup` IS the definition of how many parts a
        lineup expects. A second copy here would drift from the consumer — the
        same reason `prove_normalises` exists."""
        text = (MAPS / "merge_additions.py").read_text()
        assert "expand_lineup" in text

    def test_a_non_uniform_page_abstains(self):
        """A tacet-suppressed page prints a different lineup per system
        (beethoven p3 is 11 then 8), so one lineup names no single count and
        there is nothing to check against — the same abstention the file-level
        test makes by name."""
        ma = _load("merge_additions", MAPS)
        import json
        works = json.loads((SCAN / "works.json").read_text())
        rows = {r["row_id"]: r for r in works["rows"]}
        row = rows["beethoven-sym5-mvt1-984073-p3"]
        assert row["page"]["n_staves"] % (row["page"]["n_systems"] or 1)
        assert ma.arity_problems(row, row["staves"]) == []

    def test_a_row_with_no_page_facts_abstains(self):
        ma = _load("merge_additions", MAPS)
        assert ma.arity_problems({}, [{"name": "A", "parts": [0]}]) == []

    def test_an_ALREADY_MERGED_row_still_gets_the_arity_report(
            self, tmp_path, monkeypatch):
        """⚠️ A REGRESSION THAT HAPPENED AND WAS CAUGHT. Gating the guard on
        `problems` rather than on the SHAPE problems silences it wherever a row
        already carries a map — i.e. on every historical row, which is exactly
        the population worth reporting. The dry run went from 5 refusals to 0
        and nothing else moved."""
        ma = _load("merge_additions", MAPS)
        truth = _score(tmp_path, n_parts=3)
        monkeypatch.setattr(ma, "find_fixture", lambda *a, **k: (truth, None))
        row = {"reference": {"catalog_path": "x"},
               "page": {"n_staves": 2, "n_systems": 1},
               "staves": [{"name": "already", "parts": [0]}]}   # already merged
        add = {"status": "done", "staves": [
            {"name": "A", "parts": [0]}, {"name": "B", "parts": [1]},
            {"name": "Tamtam", "parts": [2]}]}                  # missing lines:1
        got = ma.check_row("row", row, add)
        assert any("already carries" in p for p in got["problems"])
        assert any("expands to 3 five-line staves" in p
                   for p in got["problems"]), got["problems"]

    def test_a_malformed_shape_does_not_reach_the_guard(
            self, tmp_path, monkeypatch):
        """The other half of the same gate: `expand_lineup` reads
        `int(s["lines"])`, so a malformed value must be REFUSED by shape before
        it can RAISE inside the reporter."""
        ma = _load("merge_additions", MAPS)
        truth = _score(tmp_path, n_parts=3)
        monkeypatch.setattr(ma, "find_fixture", lambda *a, **k: (truth, None))
        row = {"reference": {"catalog_path": "x"},
               "page": {"n_staves": 2, "n_systems": 1}}
        add = {"status": "done", "staves": [
            {"name": "A", "parts": [0], "lines": "abc"},
            {"name": "B", "parts": [1]}]}
        got = ma.check_row("row", row, add)          # must not raise
        assert any("`lines` is 'abc'" in p for p in got["problems"])


class TestTheUIWritesWhatTheMergeStepReads:
    """The UI stamps `staves_for_works_json` when a row is marked done. It used
    to build `{name, parts}` inline — a second projection, which is why a field
    the proposal carried could not reach the file however many writers allowed
    it."""

    def test_the_ui_uses_the_shared_projection(self):
        text = (MAPS / "server.py").read_text()
        assert "_entry_for_works_json" in text
        after = text.split("staves_for_works_json\"] = ", 1)[1][:200]
        assert "_entry_for_works_json" in after, (
            "the UI must project through the merge step's own function")

    def test_the_proposal_carries_the_fields_to_the_human(self):
        """A one-line percussion rule must not reach the human — or the file —
        indistinguishable from an ordinary staff."""
        text = (MAPS / "server.py").read_text()
        assert "_ARITY_FIELDS" in text

    def test_build_cache_still_carries_the_fields_to_the_proposal(self):
        """The upstream half of the chain. If this ever stops being computed,
        the fields above have nothing to carry.

        ⚠️ THIS USED TO ASSERT THE STRING `"lines"` APPEARED IN build_cache.py,
        and it went VACUOUS the moment `research_proposal` stopped naming the
        field literally and started carrying every schema key: two other
        `"lines"` literals live in `_one_line_bands`, which is CROP GEOMETRY
        and has nothing to do with the map. Asked of the function's OUTPUT
        instead, which is what the chain actually needs — and which also covers
        `printed_staves`, whose absence here is why the Bach grand staff never
        reached the UI at all.
        """
        bc = _load("build_cache", MAPS)
        mahler = bc.research_proposal("mahler-sym5-mvt1-local-p2", 38)
        assert sum(1 for e in mahler["staves"] if e.get("lines") == 1) == 4, \
            "the four one-line percussion rules must reach the human"
        assert not [e for e in mahler["staves"] if e.get("lines") == 5], \
            "the default is omitted, as every merged row omits it"
        bach = bc.research_proposal("bach-brandenburg3-mvt1-468678-p1", 11)
        assert [e["printed_staves"] for e in bach["staves"]
                if "Cembalo" in e["name"]] == [2], \
            "the grand staff's `printed_staves` must reach the proposal too"


class TestAOneLineRuleSurvivesTheWholeWritePath:
    """End to end through `check_row`: a map whose one-line rule is declared
    must PASS every gate and reach `works.json` with the field intact.

    ⚠️ The unit tests above prove each link; this proves the chain. The defect
    was never one broken link — `build_cache` computed `lines`, and four
    separate projections between it and the file each dropped it.
    """

    def _add(self, staves):
        return {"status": "done", "staves": staves}

    def test_the_declared_map_passes_and_keeps_the_field(
            self, tmp_path, monkeypatch):
        ma = _load("merge_additions", MAPS)
        truth = _score(tmp_path, n_parts=3)
        monkeypatch.setattr(ma, "find_fixture", lambda *a, **k: (truth, None))
        # Three reference parts on three PRINTED staves, one of them a single
        # percussion rule — so the page prints TWO five-line staves.
        row = {"reference": {"catalog_path": "x"},
               "page": {"n_staves": 2, "n_systems": 1}}
        add = self._add([
            {"name": "Violin", "parts": [0], "verdict": "confirmed"},
            {"name": "Cello", "parts": [1], "verdict": "confirmed"},
            {"name": "Tamtam", "parts": [2], "lines": 1, "verdict": "confirmed"},
        ])
        got = ma.check_row("row", row, add)
        assert got["problems"] == [], got["problems"]
        assert got["staves"][2] == {"name": "Tamtam", "parts": [2], "lines": 1}
        assert "verdict" not in got["staves"][2], "UI bookkeeping must not leak"

    def test_the_SAME_map_undeclared_is_refused(self, tmp_path, monkeypatch):
        """The control that makes the test above mean something: identical
        input, the one field removed."""
        ma = _load("merge_additions", MAPS)
        truth = _score(tmp_path, n_parts=3)
        monkeypatch.setattr(ma, "find_fixture", lambda *a, **k: (truth, None))
        row = {"reference": {"catalog_path": "x"},
               "page": {"n_staves": 2, "n_systems": 1}}
        add = self._add([
            {"name": "Violin", "parts": [0], "verdict": "confirmed"},
            {"name": "Cello", "parts": [1], "verdict": "confirmed"},
            {"name": "Tamtam", "parts": [2], "verdict": "confirmed"},
        ])
        got = ma.check_row("row", row, add)
        assert any("expands to 3 five-line staves" in p
                   for p in got["problems"]), got["problems"]
