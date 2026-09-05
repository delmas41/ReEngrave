"""Edition-level instrumentation: the second tier, and its disagreement with the first.

Lives beside the OMR tests because that is the suite that actually runs; the
module under test is ``tools/library/edition_instrumentation.py``.  No PDFs and
no Surya: the page reader is exercised through :func:`_roster_from_labels`,
which takes the label objects the reader returns, so every trap here is pinned
without a 10-second render.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

import pytest

from tools.library import edition_instrumentation as ed
from tools.library import instrumentation as work_tier
from tools.library import score_library as lib


# --- doubles for what the reader hands back -------------------------------

@dataclass
class FakeInstrument:
    name: str
    family: str = "woodwind"


@dataclass
class FakeStaff:
    staff_index: int
    system_index: int
    top_y: float = 0.0
    bottom_y: float = 10.0


@dataclass
class FakeLabel:
    staff_index: int
    text: str
    instrument: FakeInstrument | None
    confidence: str = "high"


def _page(rows):
    """rows: [(system_index, text, instrument_name|None)] in printed order."""
    staves, labels = [], []
    for i, (system, text, name) in enumerate(rows):
        staves.append(FakeStaff(staff_index=i, system_index=system, top_y=float(i)))
        if text is not None:
            labels.append(FakeLabel(i, text,
                                    FakeInstrument(name) if name else None))
    return labels, staves


BRAHMS_SYSTEM = [
    ("2 Flöten", "Flute"), ("2 Oboen", "Oboe"), ("2 Klarinetten in B", "Clarinet"),
    ("2 Fagotte", "Bassoon"), ("Kontrafagott", "Contrabassoon"),
    ("in C 1 2", None), ("in Es 3 4", None), ("2 Trompeten in C", "Trumpet"),
    ("Pauken in C u. G", "Timpani"), ("1. Violine", "Violin"),
    ("2. Violine", "Violin"), ("Bratsche", "Viola"), ("Violoncell", "Cello"),
    ("Kontrabaß", "Contrabass"),
]


class TestOneSystemNotOnePage:
    """⚠️ A page can print the roster twice."""

    def test_a_two_system_page_reads_one_roster_not_two(self):
        # Brahms 1 / Breitkopf p.1 really is 27 staves in two systems.  Reading
        # the page would report Flute, Oboe, Clarinet … twice over.
        rows = [(0, t, n) for t, n in BRAHMS_SYSTEM] + \
               [(1, t, n) for t, n in BRAHMS_SYSTEM[:13]]
        out = ed._roster_from_labels(*_page(rows))
        assert out["system_index"] == 0
        assert out["system_staves"] == 14
        assert [i["instrument"] for i in out["roster"]].count("Flute") == 1

    def test_the_system_with_the_most_named_staves_wins(self):
        rows = [(0, "???", None), (0, "???", None), (0, "???", None), (0, "???", None),
                (1, "Fl.", "Flute"), (1, "Ob.", "Oboe")]
        assert ed._roster_from_labels(*_page(rows))["system_index"] == 1


class TestStavesAreNotPlayers:
    """⚠️ N instruments is not N staves, in both directions."""

    def test_two_staves_of_one_instrument_are_one_item(self):
        out = ed._roster_from_labels(*_page([(0, t, n) for t, n in BRAHMS_SYSTEM]))
        violin = next(i for i in out["roster"] if i["instrument"] == "Violin")
        assert violin["staves"] == 2                  # 1. Violine + 2. Violine
        assert violin["staff_indices"] == [9, 10]
        assert sum(1 for i in out["roster"] if i["instrument"] == "Violin") == 1

    def test_a_printed_count_is_quoted_and_never_summed_into_staves(self):
        out = ed._roster_from_labels(*_page([(0, t, n) for t, n in BRAHMS_SYSTEM]))
        flute = next(i for i in out["roster"] if i["instrument"] == "Flute")
        assert flute["staves"] == 1                   # one staff carries the name
        assert flute["count_printed"] == [2]          # "2 Flöten" claims two players
        assert "count" not in flute                   # nothing merges the two

    def test_a_label_the_lexicon_cannot_name_is_recorded_not_dropped(self):
        out = ed._roster_from_labels(*_page([(0, t, n) for t, n in BRAHMS_SYSTEM]))
        assert [u["text"] for u in out["unparsed"]] == ["in C 1 2", "in Es 3 4"]
        assert out["named_staves"] == 12 and out["system_staves"] == 14
        assert out["yield"] == pytest.approx(12 / 14, abs=1e-3)


class TestProvenance:
    def _entry(self, **kw):
        base = {"path": "editions/x/y/z.pdf", "work_id": "w", "sha256": "abc",
                "pages": 40, "raw": {"file_description": "Complete Score"}}
        base.update(kw)
        return base

    def _fact(self, **kw):
        read = ed._roster_from_labels(*_page([(0, t, n) for t, n in BRAHMS_SYSTEM]))
        read["page_index"] = 1
        read["staves"] = 14
        read["labels_raw"] = []
        return ed.build_fact(self._entry(**kw), read, [{"page": 1}])

    def test_a_page_read_is_its_own_source_kind(self):
        # Not "catalog": a roster read off a raster is an OMR OUTPUT, and a
        # measurement path that scores OMR must not read it back as truth.
        fact = self._fact()
        assert fact["source"] == "page"
        assert fact["source_kind"] == "page"
        assert work_tier.SOURCE_KINDS["page"] == "page"

    def test_the_kinds_stay_three_and_distinct(self):
        assert set(work_tier.SOURCE_KINDS.values()) == {"catalog", "encoding", "page"}

    def test_a_page_fact_claiming_catalog_kind_is_refused(self):
        fact = self._fact()
        fact["source_kind"] = "catalog"
        with pytest.raises(ValueError):
            work_tier.validate_fact(fact)

    def test_it_says_it_describes_an_edition(self):
        assert self._fact()["describes"] == "edition"

    def test_the_raw_label_strings_are_the_evidence(self):
        assert "labels" in self._fact()["raw"]


class TestScoreType:
    """An ARRANGEMENT is a kind of edition, never a bad read."""

    def test_a_complete_score_is_a_full_score(self):
        out = ed.classify_score_type({"raw": {"file_description": "Complete Score"}})
        assert out["score_type"] == "full_score"

    def test_a_local_reduction_is_caught_by_its_filename(self):
        # Both non-full-scores in this store are `source: local` with NO
        # file_description at all — the filename is the only evidence there is.
        out = ed.classify_score_type(
            {"original_filename": "Haendel_Messiah_reduction.pdf"})
        assert out["score_type"] == "reduction"
        assert out["score_type_field"] == "original_filename"

    def test_a_lead_sheet_is_named_by_its_variant_slug(self):
        assert ed.classify_score_type({"variant": "lead-sheet"})["score_type"] \
            == "lead_sheet"

    def test_a_plate_catalogue_in_the_variant_slug_is_not_orchestral_parts(self):
        # ⚠️ `variant` is DERIVED FROM THE PUBLISHER STRING, so it carries
        # bibliographic words that are not statements about the document:
        # chausson--poeme-op25--catalog-part-b-2051-2051 is a full score whose
        # plate catalogue is called "Part B".  The word is only evidence in a
        # field that describes the FILE.
        out = ed.classify_score_type({"variant": "catalog-part-b-2051-2051"})
        assert out["score_type"] != "part"
        assert ed.classify_score_type(
            {"raw": {"file_description": "Parts"}})["score_type"] == "part"

    def test_no_evidence_is_unknown_not_full_score(self):
        assert ed.classify_score_type({})["score_type"] == "unknown"


class TestCatalogRecording:
    def _fact(self):
        read = ed._roster_from_labels(*_page([(0, t, n) for t, n in BRAHMS_SYSTEM]))
        read.update(page_index=1, staves=14, labels_raw=[])
        return ed.build_fact({"raw": {}}, read, [])

    def test_the_key_is_the_path_so_two_editions_of_one_work_coexist(self):
        # This is the whole point of the tier: one work_id, several printings,
        # and they are allowed to disagree.
        catalog = {"entries": []}
        for path in ("editions/a/w/one.pdf", "editions/a/w/two.pdf"):
            ed.record(catalog, {"path": path, "work_id": "a--w", "sha256": "s"},
                      self._fact())
        assert sorted(catalog["editions"]) == ["editions/a/w/one.pdf",
                                               "editions/a/w/two.pdf"]
        assert all(v["work_id"] == "a--w" for v in catalog["editions"].values())

    def test_recording_is_idempotent_and_carries_the_checksum(self):
        catalog = {"entries": []}
        entry = {"path": "p.pdf", "work_id": "w", "sha256": "deadbeef"}
        assert ed.record(catalog, entry, self._fact()) == "added"
        assert ed.record(catalog, entry, self._fact()) == "updated"
        # sha256 rides along so a replaced PDF's stale roster is detectable.
        assert catalog["editions"]["p.pdf"]["sha256"] == "deadbeef"

    def test_a_rebuild_does_not_destroy_edition_facts(self, tmp_path):
        # Same trap as `works`: there is no sidecar to rebuild an edition fact
        # from, so `ingest catalog` has to carry it forward explicitly.
        path = tmp_path / "catalog.json"
        catalog = {"entries": []}
        ed.record(catalog, {"path": "p.pdf", "work_id": "w", "sha256": "s"},
                  self._fact())
        lib.save_catalog(catalog, path)
        lib.rebuild_catalog(path)
        held = json.loads(path.read_text())["editions"]["p.pdf"]
        assert held["instrumentation"]["source_kind"] == "page"

    def test_the_schema_version_names_the_editions_map(self):
        assert lib.CATALOG_SCHEMA_VERSION >= 3


class TestTierDisagreement:
    """The verdict is the deliverable — three findings wearing one shape."""

    def _work(self, names, sections=(), unparsed=()):
        return {"roster": [{"kind": "instrument", "instrument": n} for n in names]
                          + [{"kind": "section", "section": s} for s in sections],
                "unparsed": list(unparsed)}

    def _edition(self, names, *, yld=1.0, score_type="full_score"):
        return {"acquired": True, "score_type": score_type,
                "roster": [{"kind": "instrument", "instrument": n} for n in names],
                "quality": {"yield": yld}}

    def test_a_section_is_satisfied_by_a_member_not_expanded_into_all_of_them(self):
        # Without this every symphony in the corpus reads as a disagreement,
        # which would say nothing about editions and everything about the
        # vocabulary.  And it must not ASSERT the members: the page never said
        # the work has a Contrabass part.
        out = ed.compare_tiers(
            self._work(["Flute"], sections=["Strings"]),
            self._edition(["Flute", "Violin", "Viola", "Cello"]))
        assert out["verdict"] == "agrees"
        assert out["edition_extra"] == []

    def test_an_instrument_only_the_page_names_is_edition_extra(self):
        out = ed.compare_tiers(self._work(["Flute", "Oboe"]),
                               self._edition(["Flute", "Oboe", "Cornet"]))
        assert out["verdict"] == "edition_extra"
        assert out["edition_extra"] == ["Cornet"]

    def test_a_shortfall_under_a_partial_read_is_read_incomplete(self):
        out = ed.compare_tiers(self._work(["Flute", "Oboe", "Horn"]),
                               self._edition(["Flute", "Oboe"], yld=0.66))
        assert out["verdict"] == "edition_missing"
        assert out["missing_explained_by"] == "read_incomplete"

    def test_the_same_shortfall_under_a_COMPLETE_read_escalates(self):
        # Identical rosters, identical shortfall; only the read's own yield
        # separates "our reader missed it" from "this printing may not have it".
        out = ed.compare_tiers(self._work(["Flute", "Oboe", "Horn"]),
                               self._edition(["Flute", "Oboe"], yld=1.0))
        assert out["missing_explained_by"] == "variant_suspected"

    def test_a_reduction_contradicting_the_work_wholesale_is_triage_not_error(self):
        out = ed.compare_tiers(
            self._work(["Flute", "Oboe", "Clarinet", "Horn", "Trumpet", "Timpani"]),
            self._edition(["Piano"], score_type="reduction"))
        assert out["verdict"] == "arrangement_suspected"
        assert out["score_type"] == "reduction"

    def test_a_declared_double_absent_from_the_page_is_not_a_variant(self):
        # The work says the 2nd flute also plays piccolo; the system we read
        # shows only `Flauti`, because the player has not picked it up yet.
        work = {"roster": [{"kind": "instrument", "instrument": "Flute",
                            "doubles": ["Piccolo"]},
                           {"kind": "instrument", "instrument": "Piccolo"}],
                "unparsed": []}
        out = ed.compare_tiers(work, self._edition(["Flute"], yld=1.0))
        assert out["verdict"] == "doubling_suspected"
        assert out["edition_missing"] == []          # must NOT inflate this
        assert out["doubling"][0]["work"] == "Piccolo"

    def test_the_auxiliary_appearing_on_the_page_is_doubling_too(self):
        # The other direction: we read a later page and it prints Cornet.
        out = ed.compare_tiers(self._work(["Trumpet", "Horn"]),
                               self._edition(["Trumpet", "Horn", "Cornet"]))
        assert out["verdict"] == "doubling_suspected"
        assert out["edition_extra"] == []

    def test_doubling_is_within_family_only(self):
        # A cross-family disagreement can never be explained by a player
        # switching instruments, so the filter must not reach it.
        out = ed.compare_tiers(self._work(["Flute", "Timpani"]),
                               self._edition(["Flute", "Timpani", "Harp"]))
        assert out["verdict"] == "edition_extra"
        assert out["doubling"] == []

    def test_a_string_disagreement_is_never_doubling(self):
        # Strings essentially never double; this must stay a real finding.
        out = ed.compare_tiers(self._work(["Violin", "Viola", "Cello"]),
                               self._edition(["Violin", "Viola"], yld=1.0))
        assert out["verdict"] == "edition_missing"
        assert out["doubling"] == []

    def test_an_unacquired_roster_is_not_a_disagreement(self):
        out = ed.compare_tiers(self._work(["Flute"]),
                               {"acquired": False, "score_type": "full_score"})
        assert out["verdict"] == "no_edition_roster"

    def test_no_work_roster_is_reported_as_such(self):
        assert ed.compare_tiers(None, self._edition(["Flute"]))["verdict"] \
            == "no_work_roster"

    def test_the_work_tiers_own_abstentions_are_carried_into_the_verdict(self):
        # `edition_extra` is just as often a work-tier LEXICON GAP as an
        # editorial variant, and `unparsed` is what says which.
        out = ed.compare_tiers(self._work(["Flute"], unparsed=["2 cornets"]),
                               self._edition(["Flute", "Cornet"]))
        assert out["work_unparsed"] == 1


class TestPageHints:
    def test_an_ambiguous_key_yields_no_hint_rather_than_a_guess(self, tmp_path):
        # The sweep's rows record no path, and two of this store's documents
        # share a (work_id, publisher, pages) key with a sibling.  A wrong join
        # must cost time, never a wrong fact.
        path = tmp_path / "hints.json"
        path.write_text(json.dumps([
            {"work_id": "w", "publisher": "P", "pages": 86,
             "acquired": True, "hit_page": 1},
            {"work_id": "w", "publisher": "P", "pages": 86,
             "acquired": True, "hit_page": 5},
            {"work_id": "v", "publisher": "Q", "pages": 40,
             "acquired": True, "hit_page": 3},
        ]))
        hints = ed._hints(path)
        assert ("w", "P", 86) not in hints
        assert hints[("v", "Q", 40)] == 3

    def test_a_document_the_sweep_found_nothing_for_gets_no_hint(self, tmp_path):
        path = tmp_path / "hints.json"
        path.write_text(json.dumps([{"work_id": "v", "publisher": "Q",
                                     "pages": 40, "acquired": False}]))
        assert ed._hints(path) == {}
