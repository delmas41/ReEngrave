"""Tests for the % of achievable renderer — the RULES, not the render.

⚠️ WHY THESE ASSERT ON PLACEMENT AND NOT ON PRESENCE. The renderer this replaces
was rejected for putting a required caption behind a `<details>` disclosure, and
for dropping `ceiling.edition` when the schema moved beneath it. A test asserting
that a caption *appears in the file* would have PASSED that build — the string
was there, inside the one container the rule forbids by name. So every caption
test below walks the parsed document and asserts the caption is a DESCENDANT OF
THE SAME ELEMENT AS THE NUMBER, with no disclosure anywhere on the path.

Each test names the mutation that turns it red, so a future reader can check it
is not vacuous the way the last one's would have been.

    python3 -m pytest tools/dashboard/tests/test_registry_report.py -q
"""
from __future__ import annotations

import copy
import json
import re
from html.parser import HTMLParser
from pathlib import Path

import pytest

from tools.dashboard import registry_report as rr


# ── a tiny DOM, so placement can be asserted rather than grepped ─────────────

class Node:
    def __init__(self, tag, attrs=None, parent=None):
        self.tag, self.attrs = tag, dict(attrs or {})
        self.parent, self.children, self.text = parent, [], []

    @property
    def classes(self):
        return set((self.attrs.get("class") or "").split())

    def walk(self):
        yield self
        for c in self.children:
            yield from c.walk()

    def find_all(self, *, cls=None, tag=None, attr=None):
        for n in self.walk():
            if cls and cls not in n.classes:
                continue
            if tag and n.tag != tag:
                continue
            if attr and n.attrs.get(attr[0]) != attr[1]:
                continue
            yield n

    def inner_text(self):
        out = list(self.text)
        for c in self.children:
            out.append(c.inner_text())
        return " ".join(t for t in out if t)

    def ancestors(self):
        n = self.parent
        while n is not None:
            yield n
            n = n.parent


_VOID = {"br", "hr", "img", "meta", "link", "input", "col"}


class _Tree(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("#root")
        self.cur = self.root

    def handle_starttag(self, tag, attrs):
        n = Node(tag, attrs, self.cur)
        self.cur.children.append(n)
        if tag not in _VOID:
            self.cur = n

    def handle_endtag(self, tag):
        n = self.cur
        while n is not None and n.tag != tag:
            n = n.parent
        if n is not None and n.parent is not None:
            self.cur = n.parent

    def handle_data(self, data):
        if data.strip():
            self.cur.text.append(data.strip())


def dom(markup: str) -> Node:
    p = _Tree()
    p.feed(markup)
    return p.root


# ── fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def reg():
    return rr.load_registry()


@pytest.fixture(scope="module")
def built(reg):
    html_s, md_s, warns, skipped = rr.build(reg, rr.ROOT)
    return {"html": html_s, "md": md_s, "warnings": warns, "skipped": skipped,
            "dom": dom(html_s)}


def _mutate(reg, fn):
    r = copy.deepcopy(reg)
    fn(r)
    return r


def _rows_with_caption(reg):
    return [r for r in reg["rows"] if r.get("mandatory_caption")]


def _rows_with_edition(reg):
    return [r for r in reg["rows"] if (r.get("ceiling") or {}).get("edition")]


def _article(root, row_id):
    hits = list(root.find_all(tag="article", attr=("data-row-id", row_id)))
    return hits[0] if hits else None


# ══ R1 — the caption is rendered beside the number, in the SAME element ══════

def test_R1_every_captioned_row_puts_its_caption_in_the_number_s_own_element(reg, built):
    """MUTATION: emit the caption as a sibling of `.headline` (or inside a
    `<details>` after it) instead of a child of it — every assertion below
    fails, because `.pct` and `.mandatory-caption` stop sharing an ancestor
    that is not the whole article."""
    captioned = _rows_with_caption(reg)
    assert captioned, "the registry declares no captions — the test would be vacuous"

    for row in captioned:
        art = _article(built["dom"], row["id"])
        assert art is not None, f"{row['id']} declares a caption and did not render"

        caps = list(art.find_all(cls="mandatory-caption"))
        assert len(caps) == 1, f"{row['id']}: expected exactly one caption element"
        cap = caps[0]

        # The number's element, whether a percentage or the unscoreable marker.
        pcts = list(art.find_all(cls="pct"))
        assert len(pcts) == 1, f"{row['id']}: expected exactly one number element"
        pct = pcts[0]

        # SAME BLOCK: they must share an ancestor tighter than the article.
        cap_anc = [id(a) for a in cap.ancestors()]
        pct_anc = [id(a) for a in pct.ancestors()]
        shared = [a for a in cap.ancestors() if id(a) in pct_anc]
        assert shared, f"{row['id']}: caption and number share no ancestor"
        assert shared[0].tag != "article" and "row" not in shared[0].classes, (
            f"{row['id']}: the tightest shared ancestor is the whole row — the "
            "caption is not in the number's own visual block")
        assert "headline" in shared[0].classes, (
            f"{row['id']}: caption and number share {shared[0].tag}."
            f"{sorted(shared[0].classes)}, not the headline block")
        assert id(art) in cap_anc  # sanity: it really is this row's caption

        # NOT behind a disclosure, at any depth.
        assert not any(a.tag in ("details", "summary") for a in cap.ancestors()), (
            f"{row['id']}: the caption is inside a disclosure — the one placement "
            "the schema rule forbids by name")

        # The literal text is present, not merely a tooltip.
        assert rr.prose(row["mandatory_caption"])[:60] in cap.inner_text()


def test_R1_the_page_contains_no_disclosure_element_at_all(built):
    """MUTATION: wrap anything in `<details>` — this fails. The rejected build
    put the caption's scope text inside one."""
    assert "<details" not in built["html"].lower()


def test_R1_no_caption_is_smuggled_into_a_title_attribute(reg, built):
    """MUTATION: render the caption as `title="…"` instead of as text."""
    for row in _rows_with_caption(reg):
        head = rr.prose(row["mandatory_caption"])[:40]
        for n in built["dom"].walk():
            assert head not in (n.attrs.get("title") or ""), (
                f"{row['id']}: caption text found in a title attribute")


def test_R1_a_blanked_caption_withholds_the_whole_row(reg):
    """The schema's rule: a renderer that cannot place the caption must not show
    the row. MUTATION: render the row bare instead of skipping it."""
    victim = _rows_with_caption(reg)[0]["id"]

    def blank(r):
        for row in r["rows"]:
            if row["id"] == victim:
                row["mandatory_caption"] = "   "
    mutated = _mutate(reg, blank)
    html_s, _md, warns, skipped = rr.build(mutated, rr.ROOT)

    assert victim in dict(skipped), f"{victim} was not withheld"
    assert f'data-row-id="{victim}"' not in html_s, (
        f"{victim} rendered despite having no placeable caption")
    assert any(rid == victim for rid, _kind, _detail in warns)


def test_R1_requirement_survives_deleting_the_caption_field(reg):
    """⚠️ THE POINT OF DERIVING THE REQUIREMENT FROM THE SCHEMA. A row whose
    `ceiling.edition` is set needs a caption whether or not it declares one, so
    deleting the field cannot buy compliance.

    MUTATION: define `caption_required` as `bool(row['mandatory_caption'])` —
    this test goes red, because the row would then render with no caption."""
    victims = _rows_with_edition(reg)
    assert victims, "no row carries ceiling.edition — the test would be vacuous"
    victim = victims[0]["id"]

    def delete(r):
        for row in r["rows"]:
            if row["id"] == victim:
                row.pop("mandatory_caption", None)
    mutated = _mutate(reg, delete)
    html_s, _md, _w, skipped = rr.build(mutated, rr.ROOT)

    assert victim in dict(skipped)
    assert f'data-row-id="{victim}"' not in html_s


# ══ R2 — the schema version gate ════════════════════════════════════════════

def test_R2_an_unknown_schema_version_is_refused_by_name(reg, capsys):
    """MUTATION: drop `gate_schema_version` from `build` — the render succeeds
    on a schema it was not written against, which is precisely how the previous
    build read 0.3.0 and dropped `ceiling.edition` in silence."""
    mutated = _mutate(reg, lambda r: r.update(schema_version="9.9.9-nonsense"))
    mutated["consumer_contract"]["current"] = "9.9.9-nonsense"
    mutated["consumer_contract"]["understood_by_a_conforming_consumer"] = ["9.9.9-nonsense"]

    with pytest.raises(SystemExit) as exc:
        rr.build(mutated, rr.ROOT)
    assert exc.value.code != 0
    err = capsys.readouterr().err
    assert "9.9.9-nonsense" in err, "the refusal must NAME the version it saw"
    assert str(rr.UNDERSTOOD_SCHEMA_VERSIONS[0]) in err


def test_R2_the_current_version_is_actually_understood(reg):
    assert reg["schema_version"] in rr.UNDERSTOOD_SCHEMA_VERSIONS


def test_R2_a_never_drop_field_this_build_does_not_handle_is_refused(reg, capsys):
    """⚠️ THE MECHANISM THAT WOULD HAVE CAUGHT THE BREITKOPF LOSS. A new
    must-not-drop field arriving in a future schema is refused rather than
    silently ignored.

    MUTATION: delete the `unhandled` check in `gate_schema_version`."""
    def add(r):
        r["consumer_contract"]["fields_a_consumer_may_never_drop"] = (
            list(r["consumer_contract"]["fields_a_consumer_may_never_drop"])
            + ["ceiling.provenance (a field invented by this test)"])
    with pytest.raises(SystemExit) as exc:
        rr.build(_mutate(reg, add), rr.ROOT)
    assert exc.value.code != 0
    assert "ceiling.provenance" in capsys.readouterr().err


def test_R2_a_registry_disagreeing_with_its_own_contract_is_refused(reg):
    def skew(r):
        r["consumer_contract"]["current"] = "0.3.0"
    with pytest.raises(SystemExit):
        rr.build(_mutate(reg, skew), rr.ROOT)


# ══ R3 — the edition clause ═════════════════════════════════════════════════

def test_R3_every_edition_row_names_its_edition_beside_its_number(reg, built):
    """The clause as a READER meets it: the publisher is in the same block as
    the figure, not in a field somewhere.

    MUTATION: strip the publisher from a caption — `caption_problem` withholds
    the row, so the loop below finds no article and fails."""
    rows = _rows_with_edition(reg)
    assert rows, "no row carries ceiling.edition — the test would be vacuous"
    for row in rows:
        art = _article(built["dom"], row["id"])
        assert art is not None, f"{row['id']} did not render"
        headline = list(art.find_all(cls="headline"))[0].inner_text()
        for term in rr._edition_terms(row["ceiling"]["edition"]):
            assert term.lower() in headline.lower(), (
                f"{row['id']}: the edition term {term!r} is not in the same "
                "block as the number")


def test_R3_a_caption_that_drops_the_publisher_withholds_the_row(reg):
    """MUTATION: delete the edition check inside `caption_problem` — the row
    renders with a publisher-scoped ceiling and no publisher, which is the
    defect the clause exists for."""
    victim = _rows_with_edition(reg)[0]
    edition_terms = rr._edition_terms(victim["ceiling"]["edition"])

    def scrub(r):
        for row in r["rows"]:
            if row["id"] == victim["id"]:
                row["mandatory_caption"] = "Measured on one edition. Not a claim about scans in general."
    html_s, _md, _w, skipped = rr.build(_mutate(reg, scrub), rr.ROOT)
    assert victim["id"] in dict(skipped)
    assert edition_terms[0] in dict(skipped)[victim["id"]]
    assert f'data-row-id="{victim["id"]}"' not in html_s


def test_R3_the_publisher_reaches_the_page(reg, built):
    """The regression in its plainest form: the term that vanished from the
    rejected page is on this one."""
    for row in _rows_with_edition(reg):
        for term in rr._edition_terms(row["ceiling"]["edition"]):
            assert term in built["html"]


# ══ R4 — --strict actually gates ════════════════════════════════════════════

def test_R4_strict_exits_nonzero_on_missing_ceiling_evidence(reg, tmp_path):
    """MUTATION: return 0 after printing warnings — the previous build did
    exactly that, reporting missing evidence beside a clean exit."""
    def break_evidence(r):
        for row in r["rows"]:
            if (row.get("ceiling") or {}).get("evidence"):
                row["ceiling"]["evidence"] = ["benchmarks/this/file/does/not/exist.json"]
                return
    p = tmp_path / "reg.json"
    p.write_text(json.dumps(_mutate(reg, break_evidence)))
    args = ["--registry", str(p),
            "--out-html", str(tmp_path / "o.html"), "--out-md", str(tmp_path / "o.md")]

    assert rr.main(args) == 0, "without --strict a warning must not fail the build"
    assert rr.main(args + ["--strict"]) != 0, "--strict did not gate"


def test_R4_strict_gates_on_a_withheld_row(reg, tmp_path):
    def blank(r):
        for row in r["rows"]:
            if row.get("mandatory_caption"):
                row["mandatory_caption"] = ""
                return
    p = tmp_path / "reg.json"
    p.write_text(json.dumps(_mutate(reg, blank)))
    assert rr.main(["--registry", str(p), "--out-html", str(tmp_path / "o.html"),
                    "--out-md", str(tmp_path / "o.md"), "--strict"]) != 0


def test_R4_a_clean_registry_still_renders_without_strict(reg, tmp_path):
    p = tmp_path / "reg.json"
    p.write_text(json.dumps(reg))
    assert rr.main(["--registry", str(p), "--out-html", str(tmp_path / "o.html"),
                    "--out-md", str(tmp_path / "o.md")]) == 0
    assert (tmp_path / "o.html").exists()


# ══ R5 — head-to-head groups on the declared key only ═══════════════════════

def test_R5_declared_groups_are_exactly_the_rows_carrying_the_key(reg, built):
    """MUTATION: group on `ceiling.kind == "competitive"` — the group key would
    then be a KIND, which equals no row's `head_to_head` value, and the set
    comparison below fails on both groups."""
    declared, _fallback = rr.head_to_head(reg["rows"])
    assert declared, "no declared head-to-head keys — the test would be vacuous"
    kinds = set(rr.load_registry()["ceiling_kinds"])

    for key, members in declared:
        expected = {r["id"] for r in reg["rows"]
                    if (r.get("comparable_as") or {}).get("head_to_head") == key}
        assert {m["id"] for m in members} == expected
        assert len(expected) == 2, (
            f"{key} has {len(expected)} side(s); v0.4.0 refuses one-sided keys")
        assert key not in kinds, "a group is keyed on a ceiling KIND, not on the key"
        assert key in built["html"]


def test_R5_a_keyless_competitive_row_lands_in_a_labelled_fallback(reg):
    """MUTATION: let the fallback merge into the declared group — the keyless
    row would appear under a heading claiming a comparability nothing declares."""
    def unkey(r):
        for row in r["rows"]:
            if (row.get("ceiling") or {}).get("kind") == "competitive":
                row["comparable_as"]["head_to_head"] = None
                return row["id"]
    mutated = _mutate(reg, unkey)
    victim = next(r["id"] for r in mutated["rows"]
                  if (r.get("ceiling") or {}).get("kind") == "competitive"
                  and not (r.get("comparable_as") or {}).get("head_to_head"))

    declared, fallback = rr.head_to_head(mutated["rows"])
    assert victim in {r["id"] for r in fallback}
    for _key, members in declared:
        assert victim not in {m["id"] for m in members}, (
            "a row with no head-to-head key was filed under a declared group")

    html_s, _md, _w, _s = rr.build(mutated, rr.ROOT)
    d = dom(html_s)
    fb = [n for n in d.find_all(cls="fallback")]
    assert fb, "the fallback block is not rendered"
    assert "FALLBACK" in fb[0].inner_text().upper(), "the fallback is not labelled as one"
    assert victim in fb[0].inner_text()


def test_R5_head_to_head_is_never_called_a_delta(built):
    d = built["dom"]
    h2h = [n for n in d.find_all(tag="h2") if "head-to-head" in (n.attrs.get("id") or "")]
    assert h2h, "no head-to-head section"
    # the section's own prose must say it is not a delta
    assert "not a delta" in built["html"].lower()


# ══ R6 — the page cannot end on a flattering number ═════════════════════════

def _section_ids(root):
    return [n.attrs["id"] for n in root.find_all(tag="h2") if n.attrs.get("id")]


def test_R6_the_document_ends_on_what_nothing_measures(built):
    """MUTATION: move the inventory section above the families, or append any
    family after it — this fails.

    Without it the page ends on whichever family happens to be last, and a
    reader's final impression is a number rather than the harness's blind spots."""
    ids = _section_ids(built["dom"])
    assert ids[-1] == "nothing-measures", f"page ends on {ids[-1]!r}"


def test_R6_cross_cutting_rows_are_met_first_and_never_last(reg, built):
    """⚠️ THE PAIRING THIS EXISTS TO PREVENT: a cross-cutting rate in green
    landing immediately after a family's worst red. A `family: "both"` row
    shares no ceiling, era or sample with either family, so it is rendered
    before both and can never terminate the document.

    MUTATION: put "both" last in FAMILY_ORDER — both assertions fail."""
    ids = _section_ids(built["dom"])
    if "family-both" in ids:
        for fam in ("family-engraved", "family-scan"):
            if fam in ids:
                assert ids.index("family-both") < ids.index(fam)

    arts = [n for n in built["dom"].find_all(tag="article")]
    assert arts
    assert arts[-1].attrs.get("data-family") != "both", (
        "a cross-cutting row is the last metric on the page")


def test_R6_no_metric_row_is_rendered_outside_an_era_group(built):
    """Adjacency is only ever WITHIN a stated sample. MUTATION: render rows
    straight into the family section — every row then has no eragroup ancestor
    and this fails."""
    for art in built["dom"].find_all(tag="article"):
        assert any("eragroup" in a.classes for a in art.ancestors()), (
            f"{art.attrs.get('data-row-id')} is rendered outside any sample group")


def test_R6_rows_of_one_sample_are_contiguous(reg, built):
    """⚠️ THE GENERIC FORM OF THE SHOWCASE PAIR. A screening rate and the defect
    rate it is seven times larger than share one `era_key`; so do a headline and
    the five stages of its own era that no harness can see. Grouping on the era
    key keeps ALL of them adjacent — naming one pair in prose would have kept
    only that one.

    MUTATION: sort rows by percentage across the whole family — the pair is
    separated by twenty rows and this fails."""
    order = [a.attrs["data-row-id"] for a in built["dom"].find_all(tag="article")]
    era = {r["id"]: (r.get("family"), r.get("era_key")) for r in reg["rows"]}
    seen_spans = {}
    for i, rid in enumerate(order):
        seen_spans.setdefault(era[rid], []).append(i)
    for key, idxs in seen_spans.items():
        assert idxs == list(range(idxs[0], idxs[0] + len(idxs))), (
            f"rows of sample {key} are not contiguous: {idxs}")


# ══ the unit's own trap: never a fabricated number ══════════════════════════

def test_unscoreable_rows_render_as_unscoreable_and_never_as_a_number(reg, built):
    """MUTATION: give an unscoreable row a bar or a `%` figure — a zero-length
    bar reads as 0% and a fabricated 100 is the worst outcome available here."""
    unscoreable = [r for r in reg["rows"] if not r.get("scoreable")]
    assert len(unscoreable) == reg["coverage"]["n_unscoreable"]

    rendered = 0
    for row in unscoreable:
        art = _article(built["dom"], row["id"])
        if art is None:          # withheld for a caption fault, which is fine
            continue
        rendered += 1
        assert art.attrs["data-scoreable"] == "false"
        pct = list(art.find_all(cls="pct"))[0]
        assert "unscoreable" in pct.classes
        assert pct.inner_text().strip().lower() == "unscoreable"
        assert not list(art.find_all(cls="bar")), f"{row['id']} drew a bar"
        assert list(art.find_all(cls="whynot")), f"{row['id']} gives no reason"
    assert rendered == len(unscoreable)


def test_every_scoreable_row_carries_its_own_trustworthiness(reg, built):
    for row in reg["rows"]:
        if not row.get("scoreable"):
            continue
        art = _article(built["dom"], row["id"])
        assert art is not None
        trust = list(art.find_all(cls="trust"))[0].inner_text()
        assert "ceiling" in trust
        assert "n =" in trust
        assert ("noise floor" in trust) or ("cannot be gated" in trust)
        badges = list(art.find_all(cls="badges"))[0].inner_text()
        assert "CEILING" in badges, f"{row['id']} does not say measured vs assumed"


def test_an_assumed_ceiling_does_not_look_like_a_measured_one(reg, built):
    for row in reg["rows"]:
        if not row.get("scoreable") or row.get("pct_of_achievable") is None:
            continue
        art = _article(built["dom"], row["id"])
        fill = list(art.find_all(cls="fill"))[0]
        assert ("hatched" in fill.classes) != rr.trusted(row), (
            f"{row['id']}: bar style does not match ceiling trust")


def test_there_is_no_page_level_single_number(built):
    """`generate.py`'s standing warning, promoted to a property: engraved and
    scan never merge into one figure."""
    assert "no page-level number" in built["html"]
    fams = {a.attrs.get("data-family") for a in built["dom"].find_all(tag="article")}
    assert {"engraved", "scan"} <= fams
    # every number belongs to exactly one family section
    for art in built["dom"].find_all(tag="article"):
        assert art.attrs.get("data-family") in ("engraved", "scan", "both")


# ══ the anti-regression that encodes the rejection itself ═══════════════════

def test_the_renderer_names_no_row_id_anywhere(reg):
    """⚠️ THE REJECTION, AS A TEST. The previous build "solved the instance, not
    the class": it hand-authored a section for the one pair it had been told
    about in prose. Every rule here is keyed on a schema property, so the source
    must not contain a single row identifier.

    MUTATION: special-case any row by id — this fails."""
    src = Path(rr.__file__).read_text()
    for row in reg["rows"]:
        assert row["id"] not in src, (
            f"registry_report.py names the row {row['id']!r} — that is a fix to "
            "an instance, not to a class")


def test_the_markdown_also_keeps_the_caption_with_the_number(reg, built):
    """MUTATION: emit the caption as a separate bullet — the caption would no
    longer be on the same line as the figure."""
    for row in _rows_with_caption(reg):
        head = rr.prose(row["mandatory_caption"])[:50]
        lines = [ln for ln in built["md"].splitlines() if row["id"] in ln]
        assert lines, f"{row['id']} missing from the markdown"
        assert any(head in ln for ln in lines), (
            f"{row['id']}: the caption is not on the same line as the number")


def test_check_mode_detects_staleness(reg, tmp_path):
    p = tmp_path / "reg.json"
    p.write_text(json.dumps(reg))
    out = ["--registry", str(p), "--out-html", str(tmp_path / "o.html"),
           "--out-md", str(tmp_path / "o.md")]
    assert rr.main(out + ["--check"]) != 0        # nothing written yet
    assert rr.main(out) == 0
    assert rr.main(out + ["--check"]) == 0
    (tmp_path / "o.md").write_text("tampered")
    assert rr.main(out + ["--check"]) != 0
