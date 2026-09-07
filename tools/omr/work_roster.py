"""The work's KNOWN roster, from the catalog, as a constraint on margin labels.

## The two faults this addresses, and why they are one fault

A margin label can arrive at the lexicon with its opening characters gone —
`'larinetti in A'`, `'orni in F I II'`, `'mpani in C-G'`. Two things then happen,
and only the first was ever noticed:

* the lexicon **abstains** and the staff behaves as unlabelled;
* or a shorter alias inside what is left **captures** the label, and the staff
  is named WRONGLY. `Tromboni Alto e Tenore` truncated to `Alto e Tenore` reads
  as **Tenor**, a singer; `Trombone Basso` truncated to `mbone Basso` reads as
  **Bass voice**. Both at `medium` confidence, both invisible to the unmatched
  label report, both feeding `clef_correction` and the written-range veto.

⚠️ **Widening the lexicon is the refused fix** and stays refused
(`benchmarks/omr-corpus-widening-2026-09/FINDINGS.md`: *"adding `larinetti` as
an alias would paper over it"*). An alias is GLOBAL: `orni` admitted for
Tchaikovsky is admitted for every score ever read, and the next fixture's
differently-cut string is not covered by it anyway.

**What this module does instead is narrow the QUESTION rather than widen the
vocabulary.** `data/score-library/catalog.json` records what each work is scored
for, read from its IMSLP work page — `source_kind: "catalog"`, independent of
the MusicXML the benchmarks score against. Within Brahms 1's ~10 instruments
there is exactly one plausible parent for `orni`; against the open 400-alias
lexicon there are several. The roster CONSTRAINS the guess instead of widening
it, and where it does not constrain to exactly one, this abstains.

## The tier discipline

Only the catalog's `works` map is read. The catalog also holds an `editions`
map whose rosters are `source_kind: "page"` — those are an OMR output of the
same raster this is trying to read, so a measurement path may not use them as
evidence here. `work_roster()` refuses anything that is not `source_kind ==
"catalog"`.

## How this interacts with `roster.py`

`tools/omr/roster.py` acquires a roster from **the document's own first labelled
system** and carries only label-sourced identity. This is a SECOND, independent
source: the roster is a property of the WORK and arrives from outside the page
entirely. They do not compete — this one runs at the label boundary, before any
identity exists, and can only change what a label RESOLVES TO. `roster.py`'s
rule ("only label-sourced identity is carried") is untouched: what it carries is
still a label a reader read, and a label repaired here is still that label.

## ⚠️ A roster is a POSITIVE list and is incomplete by construction

Three ways, all measured on the committed catalog:

1. **A section word may be dropped entirely.** Tchaikovsky 6's InstrDetail ends
   `..., tam-tam ''(ad lib.)'', strings` and `strings` landed in
   `segments_ignored` — so that work's parsed roster names **no string
   instrument at all** at `parse_rate 1.0`. 13 of 219 rosters have no string
   presence. A veto that read absence as denial would delete every violin on a
   Tchaikovsky 6 page.
2. **A roster describes the WORK, and a page prints part of it.** Absence of an
   instrument from a page is normal; presence of one not in the roster is what
   would be surprising.
3. **The roster is a parse.** 41 of 219 carry `unparsed` fragments.

So absence is weak evidence about an INSTRUMENT and strong evidence only about
a FAMILY, and only where the family could not have been dropped. That is why
the veto here is family-level, gated on a complete parse, and why the raw
instrumentation string is re-read for section words (`strings`, `orchestra`)
that admit whole families the parsed roster may have lost.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from .instruments import INSTRUMENTS, Instrument, Match, aliases_of, lookup, normalize_label

REPO_ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = REPO_ROOT / "data" / "score-library" / "catalog.json"

#: Section words that admit a whole family the parsed roster may not name.
#: Read off the RAW instrumentation string, because the parser drops some of
#: them (see the docstring's Tchaikovsky 6 case).
_SECTION_FAMILIES: dict[str, frozenset[str]] = {
    "strings": frozenset({"string"}),
    "string orchestra": frozenset({"string"}),
    "archi": frozenset({"string"}),
    "streicher": frozenset({"string"}),
    "cordes": frozenset({"string"}),
    "continuo": frozenset({"string", "keyboard"}),
    "basso continuo": frozenset({"string", "keyboard"}),
    "orchestra": frozenset({"string", "woodwind", "brass", "percussion"}),
    "orchestre": frozenset({"string", "woodwind", "brass", "percussion"}),
    "orchester": frozenset({"string", "woodwind", "brass", "percussion"}),
    "percussion": frozenset({"percussion"}),
    "chorus": frozenset({"voice"}),
    "choir": frozenset({"voice"}),
    "coro": frozenset({"voice"}),
    "chor": frozenset({"voice"}),
    # ⚠️ Singular too, and it is not redundant: Mahler's *Gesellen* songs say
    # `low voice, orchestra`, the segment `low voice` resolves to no alias, and
    # without this the one work in the store whose singer the parse genuinely
    # loses would have the name vetoed off every vocal staff in it.
    "voice": frozenset({"voice"}),
    "voices": frozenset({"voice"}),
    "narrator": frozenset({"voice"}),
    "soli": frozenset({"voice"}),
    "solo voices": frozenset({"voice"}),
    "cast": frozenset({"voice"}),
    "keyboard": frozenset({"keyboard"}),
}

#: A truncated token must keep at least this many letters. Below three letters
#: a suffix is a syllable, not a name: `ni` is the tail of `corni`, `tromboni`
#: AND `violini`, and the honest answer there is ambiguity, not a guess.
MIN_KEPT_LETTERS = 3

#: …and at least this fraction of the alias it is a tail of. Measured on the
#: truncations the engraved fixtures actually produce: `larinetti` keeps 0.90 of
#: `clarinetti`, `orni` 0.80 of `corni`, `mbone` 0.63 of `trombone`, `mpani`
#: 0.71 of `timpani`. The rejected tail `ani` keeps 0.43 of `timpani` and `ni`
#: 0.40 of `corni` — the population separates at half.
MIN_KEPT_FRACTION = 0.5


def enabled() -> bool:
    """`OMR_ROSTER_LABELS` — resolve margin labels against the work's roster.

    **Default OFF.** See `benchmarks/omr-roster-constrained-labels-2026-09/`
    for the reach, which is what a default turns on.
    """
    return os.environ.get("OMR_ROSTER_LABELS", "0").strip().lower() in (
        "1", "true", "yes", "on")


@dataclass(frozen=True)
class WorkRoster:
    """What one work is scored for, as a constraint. `source_kind: catalog`."""

    work_id: str
    instruments: frozenset[str]     # canonical `instruments.Instrument` names
    families: frozenset[str]        # families the roster admits
    complete: bool                  # every fragment of the raw field parsed
    source_kind: str = "catalog"

    def admits_family(self, family: str) -> bool:
        return family in self.families

    def admits(self, inst: Instrument) -> bool:
        return inst.name in self.instruments or self.admits_family(inst.family)


@lru_cache(maxsize=1)
def _catalog(path: str | None = None) -> dict[str, Any]:
    p = Path(path) if path else CATALOG_PATH
    if not p.is_file():
        return {}
    return json.loads(p.read_text())


def _families_from_raw(raw: dict[str, Any]) -> frozenset[str]:
    """Every family the RAW instrumentation fields mention, section words and all.

    ⚠️ **Read from the raw text and from BOTH fields, not from the parsed
    roster**, because the parse loses families two different ways and each of
    them would turn into a wrong veto:

    1. **A section word is dropped.** Tchaikovsky 6's InstrDetail ends
       `..., tam-tam ''(ad lib.)'', strings` and `strings` went to
       `segments_ignored`, so its parsed roster names no string instrument at
       `parse_rate 1.0`.
    2. **THE PARSE READS ONE FIELD.** `roster_field` is `InstrDetail` where a
       work has one, and a detail line lists the ORCHESTRA — Beethoven's
       *Egmont* says `narrator (optional), soprano, orchestra` in
       `Instrumentation` and its detail line is winds, brass and strings, so the
       SOPRANO is nowhere in the roster. Measured: **4 works with real singers**
       (Egmont, Mahler 4, Fauré's *Pelléas*, Mahler's *Gesellen* songs) admit no
       voice family from the parse alone, and a family veto would have stripped
       the name off every vocal staff in them.

    The segments are resolved through `instruments.lookup`, not by word search,
    precisely so `bass clarinet` stays a woodwind: the lexicon is longest-alias
    first and already settles that.
    """
    text = " ".join(str(v) for v in raw.values())
    flat = re.sub(r"[^a-z ]+", " ", text.lower())
    out: set[str] = set()
    for word, fams in _SECTION_FAMILIES.items():
        if re.search(rf"(?<![a-z]){re.escape(word)}(?![a-z])", flat):
            out |= fams
    for segment in re.split(r"[,;:<>\n()\[\]]+|''|\{\{|\}\}", text):
        segment = segment.strip()
        # Bounded on purpose: `lookup` costs ~0.6 s on a string it cannot match,
        # and a roster field holds a few dozen fragments. A fragment longer than
        # a name is prose, and prose is what the parser's `unparsed` list is for.
        if not (2 <= len(segment) <= 48):
            continue
        hit = lookup(segment)
        if hit is not None:
            out.add(hit.instrument.family)
    return frozenset(out)


def work_roster(work_id: str, *, catalog_path: str | None = None
                ) -> WorkRoster | None:
    """The work's roster, or None where the catalog has none for it.

    ⚠️ Refuses any fact whose `source_kind` is not `catalog` — the `editions`
    tier is `page`, an OMR output of the same raster, and using it here would
    be the input judging itself.
    """
    works = _catalog(catalog_path).get("works") or {}
    entry = (works.get(work_id) or {}).get("instrumentation") or {}
    if entry.get("source_kind") != "catalog":
        return None
    roster = entry.get("roster") or []
    names: set[str] = set()
    families: set[str] = set()
    for item in roster:
        if item.get("kind") == "instrument":
            names.add(item["instrument"])
            if item.get("family"):
                families.add(item["family"])
            # A doubling player holds two instruments on one chair; both are
            # legitimately on the page.
            for double in item.get("doubles") or ():
                names.add(double)
                for inst in INSTRUMENTS:
                    if inst.name == double:
                        families.add(inst.family)
        elif item.get("kind") == "section":
            families |= _SECTION_FAMILIES.get(
                str(item.get("section", "")).lower(), frozenset())
    families |= _families_from_raw(entry.get("raw") or {})
    if not names and not families:
        return None
    complete = (not entry.get("unparsed")) and entry.get("parse_rate", 0) == 1.0
    return WorkRoster(work_id=work_id, instruments=frozenset(names),
                      families=frozenset(families), complete=complete)


@lru_cache(maxsize=1)
def _editions_by_key(catalog_path: str | None = None) -> dict[str, str]:
    """`basename` and IMSLP id of every held edition -> its `work_id`.

    Keyed loosely on purpose: the legacy `tools/omr/training/data/imslp/...`
    paths are symlinks into the store and a run may be given either form.
    """
    out: dict[str, str] = {}
    for entry in _catalog(catalog_path).get("entries") or ():
        if entry.get("kind") != "edition":
            continue
        wid = entry.get("work_id")
        if not wid:
            continue
        out[Path(entry["path"]).name] = wid
        if entry.get("imslp_id"):
            out[f"imslp-{entry['imslp_id']}"] = wid
            out[f"imslp{entry['imslp_id']}"] = wid
    return out


def work_id_for_pdf(pdf_path: str | Path, *, catalog_path: str | None = None
                    ) -> str | None:
    """Which catalogued work this PDF is an edition of, or None.

    ⚠️ Abstains rather than guessing. A PDF outside the store — an upload, a
    generated fixture — has no roster, and the whole layer then does nothing.
    """
    keys = _editions_by_key(catalog_path)
    p = Path(pdf_path)
    hit = keys.get(p.name)
    if hit:
        return hit
    for part in p.parts:
        if part in keys:
            return keys[part]
    return None


def roster_for_pdf(pdf_path: str | Path) -> WorkRoster | None:
    """The roster of the work this PDF is an edition of, or None.

    ⚠️ **`OMR_WORK_ID` names the work for a PDF the store does not hold**, and
    it is the difference between this layer reaching the engraved benchmark and
    not reaching it at all: `orchestral_eval` renders its own fixtures into a
    gitignored build directory, so `work_id_for_pdf` correctly abstains on all
    eleven and the whole layer is a no-op there. The override is for a harness
    that KNOWS which work it just rendered; it is not a guess, and nothing sets
    it by default.

    ⚠️ It is the score LIBRARY's id (`tchaikovsky--symphony-6`), not the
    dossier's (`tchaikovsky-sym6-mvt2`). CLAUDE.md records a session lost to
    conflating those, so an id the catalog does not hold returns None rather
    than being matched to something near it.
    """
    override = os.environ.get("OMR_WORK_ID", "").strip()
    if override:
        return work_roster(override)
    return _roster_for_pdf(str(pdf_path))


@lru_cache(maxsize=16)
def _roster_for_pdf(pdf_path: str) -> WorkRoster | None:
    """Cached per path: a run asks once per page, and it is a document fact."""
    wid = work_id_for_pdf(pdf_path)
    return work_roster(wid) if wid else None


def match_of(label: Any) -> Match | None:
    """The `Match` a reader's `StaffLabel` already stands for, or None.

    `StaffLabel` keeps the instrument, the alias and the CONFIDENCE but not the
    `coverage` and `ocr_folded` those were computed from, so the two are
    re-derived from the confidence — which is the only function of them
    `Match` exposes, and `Match.confidence` is a pure function of the pair.
    Reconstructing beats re-running `lookup`: that costs ~0.6 s on a string
    that matches nothing, which is most of what this layer looks at.
    """
    if getattr(label, "instrument", None) is None:
        return None
    conf = getattr(label, "confidence", "none")
    return Match(label.instrument, getattr(label, "fifths_offset", 0),
                 getattr(label, "alias", ""),
                 coverage=(0.9 if conf == "high" else 0.3),
                 ocr_folded=(conf == "low"))


#: Spelled-out COUNTS, which a margin prints constantly — `Vier Hörner`,
#: `Drei Klarinetten`, `Due Flauti` — and which are not names.
#:
#: ⚠️ Found by the false-positive stress, not reasoned into existence:
#: `Vier Flöten` was **recovered as a PIANO**, because `vier` is a tail of
#: `klavier` and keeps 0.57 of it. `instruments._STRIP_TOKENS` already removes
#: this class (roman numerals, digits, `solo`, `due`, `zu`) and simply does not
#: hold the German and French words; they are dropped HERE rather than there,
#: because widening the shared normalizer would change what `lookup` matches
#: for every caller and this layer must not move the lexicon.
_COUNT_WORDS = frozenset("""
    one two three four five six seven eight
    ein eine zwei drei vier funf fuenf sechs sieben acht
    un une deux trois quatre cinq six sept huit
    uno una due tre quattro cinque sei sette otto
""".split())


@lru_cache(maxsize=1)
def _known_aliases() -> frozenset[str]:
    """Every alias the lexicon holds, for ANY instrument — not just the roster's."""
    return frozenset(alias for inst in INSTRUMENTS for alias in aliases_of(inst))


def _tokens(text: str) -> list[str]:
    norm = normalize_label(text)
    return [t for t in norm.split() if t.isalpha() and t not in _COUNT_WORDS]


@lru_cache(maxsize=256)
def _roster_aliases(roster: WorkRoster) -> list[tuple[str, Instrument]]:
    """Every SINGLE-WORD alias of every instrument this work admits.

    Family admission counts: a roster saying `strings` admits `Violino`, which
    is the whole reason the section words are read.

    ⚠️ **Multi-word aliases are excluded, deliberately.** A truncation is the
    tail of a WORD — the engraver's slot ran out mid-name. Matching a token
    against the tail of `tr tenore` or `bass drum` is a different claim, and it
    reaches across families: `alt` is a tail of the Trombone alias `tr alt`, so
    a truncated `Fl. Alt.` (an ALTO FLUTE) would resolve to a trombone. Priced
    at one real loss — Tchaikovsky's `Alto e Tenore` would recover to Trombone
    through `tr tenore` and instead only gets vetoed — and taken anyway, because
    that recovery is luck rather than mechanism.
    """
    out = [(alias, inst) for inst in INSTRUMENTS if roster.admits(inst)
           for alias in aliases_of(inst) if " " not in alias]
    out.sort(key=lambda pair: -len(pair[0]))
    return out


@dataclass(frozen=True)
class Decision:
    """What the roster made of one label. `kind` is the whole answer."""

    kind: str    # "unchanged" | "recovered" | "disambiguated" | "vetoed"
    match: Match | None          # the resolution to use; None means unlabelled
    reason: str = ""
    before: str = ""             # instrument name the lexicon gave, if any

    @property
    def names_a_staff(self) -> bool:
        """Whether this decision INSTALLS a name, which is the risky half.

        `recovered` and `disambiguated` name a staff and can name it wrongly;
        `vetoed` only removes a name the lexicon had already got wrong.
        """
        return self.kind in ("recovered", "disambiguated")


def recover_truncated(text: str, roster: WorkRoster) -> Match | None:
    """A truncated label read against this work's roster, or None.

    **A truncation is a SUFFIX of its parent**, because the missing characters
    are the leading ones — the engraver's slot ran out on the left. So a token
    of the label is accepted only where it is a PROPER suffix of an alias of an
    instrument the roster admits, keeps `MIN_KEPT_LETTERS` letters and
    `MIN_KEPT_FRACTION` of that alias.

    ⚠️ **Ambiguity within the roster abstains.** `ni in F III IV` is a tail of
    `corni`, `tromboni` and `violini` and every one of the three is on a
    Tchaikovsky page; naming one would be a coin flip dressed as evidence.
    Returns None, and the staff stays unlabelled exactly as it is today.
    """
    hits: dict[str, tuple[str, str, Instrument]] = {}
    known = _known_aliases()
    for token in _tokens(text):
        if len(token) < MIN_KEPT_LETTERS:
            continue
        if token in known:
            # ⚠️ A WORD THE LEXICON ALREADY HOLDS IS NOT A FRAGMENT OF ANOTHER.
            # `soprano` is a tail of `mezzosoprano`, so `Soprano Saxophone` was
            # recovered as an ALTO — the cross-family capture
            # `benchmarks/omr-lexicon-2026-09/SUBSTRING_CAPTURE_2026-09-05.md`
            # is about, arriving by a new route. Found by the stress probe.
            continue
        for alias, inst in _roster_aliases(roster):
            if len(token) >= len(alias) or not alias.endswith(token):
                continue
            if len(token) / len(alias) < MIN_KEPT_FRACTION:
                continue
            hits.setdefault(inst.name, (token, alias, inst))
    if len(hits) != 1:
        return None
    token, alias, inst = next(iter(hits.values()))
    from .instruments import parse_in_key
    # An explicit "in F" is read exactly as `lookup` reads it; a BARE trailing
    # key token is deliberately not, because `_parse_bare_key` reads the token
    # after the alias and the alias never fired here.
    offset = parse_in_key(text)
    if offset is None:
        offset = inst.default_fifths_offset
    # `medium`, never `high`: the alias did not fire, a tail of it did. A
    # `medium` label is usable by `slots` and by `roster.py` and is still below
    # what an intact printed name earns.
    return Match(inst, offset, alias, coverage=0.5, ocr_folded=False)


_UNSET = object()


def decide(text: str, roster: WorkRoster | None, *, hit: Any = _UNSET) -> Decision:
    """What this label should resolve to, given the work's roster.

    Four outcomes, and they do not carry the same risk:

    * **recovered** — the lexicon abstained and exactly one roster instrument
      owns a tail of the label. NAMES A STAFF, so a wrong one names it wrongly.
    * **disambiguated** — the lexicon resolved into a family the work does not
      have, and the alias that fired is one the lexicon ITSELF declares
      ambiguous (`AMBIGUOUS_ALIASES`) with exactly one reading the roster
      admits. `Basso.` on Beethoven 5 is Contrabass, not a singer. Also NAMES A
      STAFF — but the candidate set is the lexicon's own, not this module's.
    * **vetoed** — same family miss with nothing to put in its place. Only ever
      REMOVES a name that was already wrong; it never installs one.
    * **unchanged** — everything else, which is the overwhelming majority.

    ⚠️ The order matters and is measured. A family miss is tried as a RECOVERY
    first (a captured label is in exactly the evidential position an abstaining
    one is: what the lexicon said is known wrong), then as a disambiguation,
    and only then vetoed. `mbone Basso` — `Trombone Basso` with its head cut
    off, read as a BASS VOICE — comes back as Trombone that way; the other
    order makes it Contrabass.

    Pass `hit` where the caller has already run `instruments.lookup(text)` —
    every reader in the ladder has. `lookup` costs ~0.6 s on a string that
    matches NOTHING (it walks ~400 aliases twice, compiling a regex per alias
    and thrashing `re`'s cache), so re-asking would double the cost of exactly
    the labels this layer exists for.
    """
    if hit is _UNSET:
        hit = lookup(text)
    if roster is None:
        return Decision("unchanged", hit)
    if hit is None:
        if not roster.complete:
            return Decision("unchanged", None)
        rec = recover_truncated(text, roster)
        if rec is None:
            return Decision("unchanged", None)
        return Decision("recovered", rec,
                        reason=f"tail of {rec.alias!r} in the work's roster")
    if roster.complete and not roster.admits_family(hit.instrument.family):
        # ⚠️ FAMILY, not instrument, and only on a complete parse. See the
        # module docstring: a parsed roster routinely lacks an instrument the
        # page prints, but a work with no singer at all does not grow one.
        # ⚠️ RECOVERY IS TRIED FIRST, and the order was MEASURED, not assumed.
        # `mbone Basso` is a family miss whose alias `basso` is ambiguous with
        # Contrabass admitted — so disambiguation-first answers **Contrabass**,
        # confidently and wrongly, on a label whose surviving five letters spell
        # the tail of `trombone`. Recovery reads the longer, more specific token
        # the lexicon could not use at all; disambiguation chooses between
        # readings of a short one. On the corpora here, flipping the order costs
        # nothing (`Basso.` alone recovers to nothing — `basso` keeps 0.45 of
        # `contrabasso`, under the floor) and fixes that one.
        rec = recover_truncated(text, roster)
        if rec is not None:
            return Decision("recovered", rec, before=hit.instrument.name,
                            reason=f"tail of {rec.alias!r} in the work's roster")
        admitted = [alt for alt in hit.alternatives if roster.admits(alt)]
        if len(admitted) == 1:
            inst = admitted[0]
            return Decision(
                "disambiguated",
                Match(inst, inst.default_fifths_offset, hit.alias,
                      hit.coverage, hit.ocr_folded),
                before=hit.instrument.name,
                reason=(f"{hit.alias!r} is ambiguous and only {inst.name} is "
                        f"in the roster"))
        return Decision("vetoed", None, before=hit.instrument.name,
                        reason=f"no {hit.instrument.family} in the roster")
    return Decision("unchanged", hit)
