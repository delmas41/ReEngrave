"""The `works.json` `staves` shape is DERIVED, and it may not be typed out.

⚠️ THE SECOND PASS OVER ONE FAULT, AND THE FIRST PASS IS WHY IT IS WORTH ONE.

`shape_problems` refused, in words, *"works.json entries are exactly
name+parts"*, while FIVE projections between `candidate_maps` and the file each
rebuilt an entry as a hand-written `{name, parts}`.  The refusal was visible;
the projections were silent, and they are what put
`mahler-sym5-mvt1-local-p2` into the file with a correct 21-entry lineup and
none of its four `lines: 1` flags — moving its part join from cause D to cause
B instead of closing it, and leaving two tests red until the flags were typed
back in by hand (`981cbc41`).

`e9c82c82` repaired most of that, and its `arity_problems` is the strongest
thing here and is untouched: an allow-list can only carry a field that is
PRESENT, while asking `run_ledger.expand_lineup` at write time catches one that
is ABSENT.  What it did not do is stop the allow-list being hand-written — and
**on the day it landed that list was already incomplete**:
`beethoven-sym5-mvt1-984073-p1` carries `clef` and `key` on all twelve staves
and was still refused, so the writer still could not re-merge a sixth of the
file.  `build_cache.research_proposal` still named `lines` and dropped
`printed_staves`, so the Bach grand staff never reached the UI at all;
`api_adopt` still rebuilt `{name, parts}`; and neither field was shown to the
human confirming it.

So the shape is derived from the consumer and declared where no consumer reads
it, its values are validated (`e9c82c82`'s rule, kept and extended), and every
projection goes through `staves_schema.project`.  Each test here was run RED.

⚠️ THE VACUITY TRAP IS REAL HERE and is checked twice.  A derivation that
returns nothing makes every check downstream of it pass; a "committed rows
conform" test would pass trivially if the allow-list were itself derived from
`works.json`.  `test_the_derivation_is_not_empty` and
`test_name_plus_parts_alone_would_still_refuse_six_rows` are the positive
controls that keep the rest honest.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SCAN = ROOT / "benchmarks" / "omr-scan-e2e-2026-09"
MAPS = ROOT / "benchmarks" / "omr-staves-map-2026-09"
WORKS = SCAN / "works.json"


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


def _schema():
    return _load("staves_schema", SCAN)


def _rows() -> list[dict]:
    if not WORKS.is_file():
        pytest.skip("works.json not present")
    return json.loads(WORKS.read_text())["rows"]


def _mapped_rows() -> list[dict]:
    return [r for r in _rows() if isinstance(r.get("staves"), list)]


# --------------------------------------------------------- the derivation

class TestTheOptionalKeysAreDerived:

    def test_the_derivation_is_not_empty(self):
        """⚠️ THE POSITIVE CONTROL. An empty derivation would let every entry
        key be "undeclared" and every projection drop everything, and nothing
        else in this file would notice."""
        ss = _schema()
        assert set(ss.arity_fields()) == {"lines", "printed_staves"}, (
            "the consumer's own reads are the optional schema; if this set "
            "moved, that is a data-model change and works.json's rows should "
            "be checked against it, not this assertion relaxed")

    def test_it_reads_the_consumer_and_not_a_list_in_this_repo(self):
        """Run backwards: a source that reads a different key derives that key.

        Without this the AST walk could be returning a constant and nobody
        would know — which is the fault one level up, wearing a decorator."""
        ss = _schema()
        assert ss.keys_read_by(
            'def expand_lineup(staves):\n'
            '    for s in staves:\n'
            '        if s.get("braced") or s["voices"]:\n'
            '            pass\n', "expand_lineup") == {"braced", "voices"}

    def test_arity_fields_FOLLOWS_the_consumer_file(self, tmp_path):
        """⚠️ RUN RED AGAINST A HAND LIST. `test_the_derivation_is_not_empty`
        above cannot tell a derivation from a `frozenset({...})` literal that
        happens to be right — replacing the AST call with that constant left
        this whole file green until this test existed. Point `CONSUMER` at a
        source that reads different keys; a constant does not move."""
        ss = _schema()
        fake = tmp_path / "fake_consumer.py"
        fake.write_text('def expand_lineup(staves):\n'
                        '    for s in staves:\n'
                        '        if s.get("rules") or s.get("braced"):\n'
                        '            pass\n')
        ss.ROOT, ss.CONSUMER = tmp_path, ("fake_consumer.py", "expand_lineup")
        assert set(ss.arity_fields()) == {"rules", "braced"}

    def test_a_chained_receiver_is_not_an_entry_key(self):
        """`row.get("page", {}).get("n_staves")` names a key of the PAGE.
        Admitting it would put `n_staves` in the entry schema."""
        ss = _schema()
        assert ss.keys_read_by(
            'def f(row):\n'
            '    return row.get("page", {}).get("n_staves")\n', "f") == {"page"}

    def test_a_missing_consumer_RAISES_and_does_not_degrade(self, tmp_path):
        """⚠️ An empty derivation is not a smaller schema, it is a SILENT one:
        the allow-list narrows to name+parts and `project()` starts dropping
        `lines: 1` again, indistinguishable from the original defect. A broken
        checkout must stop the writer, not quietly restore the old behaviour."""
        ss = _schema()
        ss.ROOT, ss.CONSUMER = tmp_path, ("nope.py", "expand_lineup")
        with pytest.raises(ss.SchemaUnreadable):
            ss.arity_fields()
        (tmp_path / "nope.py").write_text("def expand_lineup(staves):\n"
                                          "    return list(staves)\n")
        with pytest.raises(ss.SchemaUnreadable):
            ss.arity_fields()   # present, but reads no entry key

    def test_every_allowed_key_has_a_VALIDATOR(self):
        """⚠️ ALLOWED IS NOT UNCHECKED — `e9c82c82`'s rule, and DERIVING the
        list is what makes it need its own test. A hand list and its validators
        are edited together; a derived list can grow a field on its own, and
        that field would then reach hand-verified truth unchecked."""
        ss = _schema()
        assert ss.unvalidated() == []

    def test_the_validators_refuse_rather_than_raise(self):
        """A validator is reached from the merge step's own error path, so bad
        input must come back as a complaint — `int()` on it would raise."""
        ss = _schema()
        for bad in ({"lines": 3}, {"lines": "1"}, {"lines": None},
                    {"printed_staves": 0}, {"printed_staves": True},
                    {"printed_staves": "2"}, {"clef": ""}, {"key": 12},
                    {"key": "flat"}):
            e = dict({"name": "A", "parts": [0]}, **bad)
            assert ss.problems([e]), bad
        # and the contradiction e9c82c82 named
        assert ss.problems([{"name": "A", "parts": [0], "lines": 1,
                             "printed_staves": 2}])

    def test_a_recorded_only_key_carries_its_reason(self):
        ss = _schema()
        assert set(ss.RECORDED_ONLY) == {"clef", "key"}
        for k, why in ss.RECORDED_ONLY.items():
            assert len(why.strip()) > 40, f"{k}: declare WHY it is kept"
        # and it may not shadow something a consumer reads: a key in both
        # tables would mean the reason is stale.
        assert not (set(ss.RECORDED_ONLY) & set(ss.arity_fields()))


# ------------------------------------------------- the committed file

class TestTheCommittedFileConforms:

    def test_every_mapped_row_passes_the_shape_check(self):
        ss = _schema()
        bad = {r["row_id"]: ss.problems(r["staves"]) for r in _mapped_rows()
               if ss.problems(r["staves"])}
        assert not bad, bad

    def test_the_hand_list_alone_would_still_refuse_a_row(self):
        """⚠️ THE DECISIVE CONTROL, and the reason the test above is not
        vacuous. The allow-list is declared in code, NOT read back out of
        `works.json` — so if it were still the old `{name, parts}` the rows
        below would fail. They are named, so a row that stops carrying its
        fact is a failure here too, not a quiet pass."""
        rows = {r["row_id"]: r["staves"] for r in _mapped_rows()}
        outgrown = {rid: sorted({k for s in st if isinstance(s, dict)
                                 for k in s} - {"name", "parts"})
                    for rid, st in rows.items()}
        outgrown = {k: v for k, v in outgrown.items() if v}
        assert outgrown == {
            "beethoven-sym5-mvt1-984073-p1": ["clef", "key"],
            "mahler-sym5-mvt1-local-p2": ["lines"],
            "mahler-sym5-mvt1-local-p3": ["lines"],
            "mahler-sym5-mvt1-local-p4": ["lines"],
            "mahler-sym5-mvt1-local-p5": ["lines"],
            "bach-brandenburg3-mvt1-468678-p1": ["printed_staves"],
        }, outgrown

    def test_projecting_a_committed_entry_is_the_identity(self):
        """Stronger than "it passes the shape check", and it is what makes a
        re-merge safe: `project()` reproduces every committed entry exactly,
        keys and ORDER included, so the writer churns nothing. It fails the
        moment the allow-list is narrower than the file."""
        ss = _schema()
        for r in _mapped_rows():
            for e in r["staves"]:
                got, dropped = ss.project(e)
                assert got == e and list(got) == list(e) and not dropped, \
                    f"{r['row_id']}: {e} -> {got} (dropped {dropped})"

    def test_nothing_on_the_committed_file_is_unaccounted_for(self):
        """A new hand-read fact must be DECLARED before it is truth. This is
        what turns that from a convention into a failing test."""
        ss = _schema()
        assert ss.unaccounted() == {}


# ------------------------------------------------- the writer, BOTH branches

def _check_row(add: dict, row: dict | None = None):
    m = _load("merge_additions", MAPS)
    return m.check_row("synthetic-row-not-on-disk", row or {
        "reference": {"catalog_path": "reference/x/y/z.mxl"}}, add)


LINEUP = [
    {"name": "Pauken", "parts": [0]},
    {"name": "Becken", "parts": [1], "lines": 1},
    {"name": "Cembalo", "parts": [2], "printed_staves": 2},
]


class TestALinesFlagSurvivesTheWriter:
    """⚠️ BOTH BRANCHES, and the fallback is the one that had the drop.

    A test written only against `staves_for_works_json` passes vacuously —
    that branch takes the list verbatim and never projected anything. The
    fallback branch is where `{"name": ..., "parts": ...}` was typed out, and
    it is the branch the three unfinished additions rows take today."""

    def test_the_staves_for_works_json_branch(self):
        c = _check_row({"status": "done",
                        "staves_for_works_json": [dict(s) for s in LINEUP]})
        assert c["staves"] == LINEUP

    def test_the_fallback_branch_carries_the_facts(self):
        c = _check_row({"status": "done", "staves": [
            dict(s, proposed={"name": s["name"], "parts": s["parts"]},
                 verdict="confirmed")
            for s in LINEUP]})
        assert c["staves"] == LINEUP, (
            "the fallback projection dropped a hand-read fact about the "
            "engraving — this is the mahler-p2 defect")

    def test_the_fallback_branch_still_drops_ui_bookkeeping(self):
        """The projection is right; projecting onto a hand list was not.
        `proposed`/`verdict` are the UI's state and must not reach truth."""
        c = _check_row({"status": "done", "staves": [
            dict(s, proposed=None, verdict="confirmed") for s in LINEUP]})
        for e in c["staves"]:
            assert set(e) <= {"name", "parts", "lines", "printed_staves"}

    def test_what_was_dropped_is_reported_never_silent(self):
        """A misspelled fact is dropped exactly like bookkeeping is, so the
        only thing that separates them is that the drop is printed."""
        c = _check_row({"status": "done", "staves": [
            {"name": "Becken", "parts": [0], "linnes": 1, "verdict": "edited"}]})
        assert c["dropped"] == {0: ["linnes", "verdict"]}

    def test_an_undeclared_key_in_staves_for_works_json_is_REFUSED(self):
        """That branch is hand-authored and carries no bookkeeping, so an
        unknown key there is a typo and must not be quietly dropped."""
        c = _check_row({"status": "done", "staves_for_works_json": [
            {"name": "Becken", "parts": [0], "linnes": 1}]})
        assert any("linnes" in p for p in c["problems"])

    def test_the_real_invariants_still_hold(self):
        ss = _schema()
        assert ss.problems([{"name": "x", "parts": [1, 1]}])
        assert ss.problems([{"name": "", "parts": [1]}])
        # ⚠️ an entry whose `parts` is EMPTY stays refused. `page_normalise`
        # raises `NoHandMap` on one, and `candidate_maps.UNREPRESENTABLE` is
        # the display path that keeps such a printed staff visible without
        # letting it into the decision path.
        assert ss.problems([{"name": "Becken u. Gr.Trommel", "parts": []}])

    def test_parts_order_is_never_canonicalised(self):
        """`page_normalise` keeps `parts[0]`, so sorting renames the staff."""
        ss = _schema()
        out, _ = ss.project({"name": "Zwei Fagotte.", "parts": [10, 0]})
        assert out["parts"] == [10, 0]


# ------------------------------------------ the four projections upstream

class TestEveryProjectionUsesTheOneDefinition:
    """Source-level anti-drift, in the shape of `TestEventlessMeasureKeepsItsMarks`.

    There is no unit seam on the FastAPI handlers or on the proposal builder,
    and the failure being guarded is a projection quietly growing its own hand
    list again. Each assertion was verified to go RED with its call removed."""

    def test_the_server_has_no_inline_projection_left(self):
        """`api_done` and `api_adopt` go through the writer's own
        `_entry_for_works_json`; the seed splices the arity fields onto the
        proposal. ⚠️ `api_adopt` was the site `e9c82c82` left behind — it still
        rebuilt `{name, parts}`, so a 575951 twin adopting its finished map
        lost the fields the twin had just been confirmed to carry."""
        src = (MAPS / "server.py").read_text()
        assert src.count("_entry_for_works_json(") == 2, (
            "`done` and `adopt` each project an entry through the writer; a "
            "third site, or one that stopped, needs looking at")
        assert '"parts": list(s["parts"]),\n             "proposed"' not in src, \
            "api_adopt's hand-written projection is back"

    def test_the_proposal_builder_carries_every_optional_key(self):
        src = (MAPS / "build_cache.py").read_text()
        assert "staves_schema.optional_keys()" in src, \
            "research_proposal named `lines` and dropped `printed_staves`"

    def test_the_whole_chain_carries_a_lines_flag_end_to_end(self, tmp_path):
        """proposal -> UI seed -> `staves_for_works_json` -> `check_row`.

        The source assertions above say each site CALLS the schema; this says
        the chain they form does not lose the fact, which is the thing that
        actually went wrong. Exercises the real `Store.row` — the seed is the
        site with no other seam."""
        pytest.importorskip("fastapi")
        srv = _load("server", MAPS)
        m = _load("merge_additions", MAPS)
        store = srv.Store(tmp_path / "additions.json")
        seed = {"proposal": {"source": "candidate_maps",
                             "staves": [dict(s) for s in LINEUP]},
                "reference": {"n_parts_music21": 3, "catalog_path": "x.mxl",
                              "source": "s"},
                "detected": {"artefact": "a", "artefact_origin": "o"}}
        st = store.row("r1", seed)
        assert st["staves"][1]["lines"] == 1, "the SEED dropped it"
        sfwj = [srv._entry_for_works_json(s) for s in st["staves"]]
        assert sfwj == LINEUP, "`done` dropped it"
        c = m.check_row("r1", {"reference": {"catalog_path": "x.mxl"}},
                        {"status": "done", "staves_for_works_json": sfwj})
        assert c["staves"] == LINEUP

    def test_THE_WRITER_ACCEPTS_EVERY_ROW_IT_HAS_ALREADY_WRITTEN(self):
        """⚠️ THE DECISIVE ONE, and it is not synthetic: every `staves` map in
        the committed file, through the writer's OWN front door.

        This is the property the whole thread is about — the only tool allowed
        to write `works.json` must be able to re-merge the file it has written
        — and it is the one `e9c82c82` did not reach: `clef`/`key` are not
        arity fields, so `beethoven-sym5-mvt1-984073-p1` was still refused on
        the day the hand list landed."""
        m = _load("merge_additions", MAPS)
        bad = {r["row_id"]: m.shape_problems(r["staves"])
               for r in _mapped_rows() if m.shape_problems(r["staves"])}
        assert not bad, bad

    def test_the_writer_derives_its_arity_fields(self):
        """`ARITY_FIELDS` is the hand list that was already incomplete when it
        was written. It is the same tuple, obtained from the consumer."""
        m = _load("merge_additions", MAPS)
        ss = _schema()
        assert m.ARITY_FIELDS == ss.arity_fields() == ("lines", "printed_staves")
        src = (MAPS / "merge_additions.py").read_text()
        assert 'ARITY_FIELDS = ("lines", "printed_staves")' not in src, \
            "the hand list is back"
        assert "staves_schema.problems(" in src
        assert "staves_schema.project(" in src
