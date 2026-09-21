"""The engraving-convention registry, made machine-readable.

`docs/engraving-conventions.md` holds 114 merged conventions, each with a
structured body: **Says**, **Predicts (mechanically)**, **Numbers**,
**Literature**, **Measured here**, **Status**, **Rigid or
publisher-dependent**, **Would be falsified by**, **Known exceptions**,
**Code**. Sean, 2026-09-17: *"We need to make sure that all of those are
actually included in our decision-making in some form of the stages. The
mechanism has to be intelligent enough to be testing for all of these
rules."*

Measured before this module existed: **zero** files under `tools/` read that
document, while 16 of the 28 staged decisions declare `checked_by=(...)` —
32 convention statements, in English prose, with no link of any kind to the
registry. 114 testable rules in a document, 32 sentences in code, and
nothing joining them.

⚠️⚠️ **THIS IS A PARSE, NOT A COPY.** Every field, every count and every
identifier below is read out of the markdown at call time. A second, typed
copy of 125 conventions is the thing this registry exists to prevent — it
would drift from the first, and drift is the failure. The module knows no
convention's text, no convention's number, and no convention's name.

⚠️⚠️ **A CONVENTION IS A HYPOTHESIS AND A CHEAP TEST, NEVER A LICENCE.**
The registry says so itself, and this project has refuted conventions stated
in its own `CLAUDE.md`. Two API decisions follow, and they are the reason
this module is more than a parser:

* `Convention.rule_text()` **RAISES** `RefutedConvention` on a refuted entry.
  The raw `says` field stays readable — evidence is never thrown out with
  the behaviour, the `OMR_WHOLE_REST_INK` discipline — but the accessor a
  consumer would reach for refuses. A refuted entry cannot be read as a live
  rule by accident.
* `Convention.measured_figure()` **RAISES** `NotMeasuredHere` on a
  LITERATURE-ONLY or ASSERTED entry. The registry's first discipline is
  *never promote LITERATURE ONLY to MEASURED HERE*; a font default is not a
  measurement of a 19th-century plate. The API enforces it rather than
  asking to be trusted.

⚠️ **WHAT THIS DELIBERATELY DOES NOT DO.** It wires nothing into any
decision and adds no predicate layer. A producer and its first consumer
landing together makes the reach measurement circular — the discipline
`Q.INK` and `OMR_FAMILY_POSITIONS` both shipped under. This is the handle;
the consumer is a later, separately measured step.

Run it:

    python3 -m tools.omr.conventions              # reach, grades, findings
    python3 -m tools.omr.conventions --check      # non-zero on any finding
    python3 -m tools.omr.conventions --json
    python3 -m tools.omr.conventions --id C34     # one entry, in full

⚠️ **The positive control is checked BEFORE any finding is reported**, and
`--check` exits **2** when it is at zero. A parser that silently matches
nothing reports a clean registry, which is exactly how
`gather_coverage`'s anti-drift guard compared names for equality, matched
none, and left a closed finding open in four documents.

Exit codes: **0** clean · **1** findings · **2** the parse is DEAD.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional, Sequence, Tuple

DOC_RELATIVE = Path("docs") / "engraving-conventions.md"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_doc_path() -> Path:
    return _repo_root() / DOC_RELATIVE


# ---------------------------------------------------------------------------
# The shape of an entry, derived from the document rather than declared.
#
# ⚠️ These are the field LABELS the markdown prints, and they are required of
# every entry. They are the one piece of literal knowledge in this module and
# they are load-bearing in the safe direction: a label that changes in the
# document makes every entry report a MISSING FIELD, loudly. The alternative
# — discovering the label set from the entries themselves — cannot tell a
# document-wide rename from a document-wide deletion, and would report a
# registry with no fields at all as healthy.
# ---------------------------------------------------------------------------
REQUIRED_FIELDS: Tuple[str, ...] = (
    "Says",
    "Predicts (mechanically)",
    "Numbers",
    "Literature",
    "Measured here",
    "Status",
    "Rigid or publisher-dependent",
    "Would be falsified by",
    "Known exceptions",
    "Code",
)

# The status words the document uses, longest-prefix-wins. An entry's Status
# row routinely carries a qualifying tail ("MEASURED HERE - and refuted as a
# reader"); the tail is KEPT in `status_note` and never discarded, because it
# is where several of this registry's sharpest caveats live.
_STATUS_WORDS: Tuple[str, ...] = (
    "REFUTED HERE",
    "MEASURED HERE",
    "LITERATURE ONLY",
    "ASSERTED",
    "ENCODING",
)


class Status(Enum):
    """What kind of claim this is. **Never promotable.**"""

    MEASURED_HERE = "MEASURED HERE"
    LITERATURE_ONLY = "LITERATURE ONLY"
    ASSERTED = "ASSERTED"
    REFUTED_HERE = "REFUTED HERE"
    ENCODING = "ENCODING"
    # ⚠️ NOT a value the document uses. It means the parse could not READ
    # the Status row, and it exists because the alternative is a fallback
    # that converts "cannot tell" into a definite answer — this tree's
    # governing rule, and the first draft of this module broke it by
    # defaulting an unreadable row to ASSERTED. An UNREADABLE entry is
    # always a FINDING and is never gradeable.
    UNREADABLE = "UNREADABLE"


class Refutation(Enum):
    """How much of an entry is refuted — a three-way fact, not a boolean.

    `WHOLE_ENTRY` is the five in *Conventions that FAILED here*.
    `INTERNAL_CAVEAT` is the nine the registry names as "surviving entries
    [that] carry a refutation INSIDE them" — those are live rules with a
    named trap, and collapsing them into either of the other two buckets
    loses the trap.
    """

    NONE = "none"
    INTERNAL_CAVEAT = "internal_caveat"
    WHOLE_ENTRY = "whole_entry"


class Testability(Enum):
    """Whether a test can be WRITTEN for this entry.

    ⚠️ Orthogonal to `Status`, and conflating the two is the
    never-promote violation: `TESTABLE_AGAINST_INK` says a falsifier exists
    and a reader-side prediction is stated, **not** that the claim has been
    checked on a plate. `Status` is the only thing that says that.
    """

    REFUTED = "refuted"                       # never a live rule
    TESTABLE_AGAINST_INK = "testable"         # a prediction AND a falsifier
    UNGRADED = "ungraded"                     # a required field is missing


class ConventionError(Exception):
    """Base for the registry's refusals."""


class RefutedConvention(ConventionError):
    """Raised when a refuted entry is consumed as a live rule."""


class NotMeasuredHere(ConventionError):
    """Raised when a literature default is consumed as a measurement."""


def slugify(title: str) -> str:
    """The GitHub heading anchor for a title.

    Derived, and checked: every internal `](#anchor)` link in the document
    resolves to a heading this function produces, which is what makes a
    broken link a FINDING rather than an unnoticed rot.
    """
    text = title.strip().lower().replace("`", "")
    out: List[str] = []
    for ch in text:
        if ch.isalnum() or ch in " -_":
            out.append(ch)
        elif unicodedata.category(ch).startswith("M"):
            out.append(ch)
    return "".join(out).replace(" ", "-")


@dataclass(frozen=True)
class Convention:
    """One registry entry, verbatim, with its derived grades."""

    id: str
    sources: Tuple[str, ...]
    title: str
    slug: str
    category: str
    line: int
    fields: Dict[str, str]
    status: Status
    status_note: str
    refutation: Refutation
    testability: Testability
    code_paths: Tuple[str, ...]
    declares_no_consumer: bool
    cited_in_disagreements: bool
    missing_fields: Tuple[str, ...] = ()

    # -- verbatim field accessors ------------------------------------------
    @property
    def says(self) -> str:
        return self.fields.get("Says", "")

    @property
    def predicts(self) -> str:
        return self.fields.get("Predicts (mechanically)", "")

    @property
    def numbers(self) -> str:
        return self.fields.get("Numbers", "")

    @property
    def literature(self) -> str:
        return self.fields.get("Literature", "")

    @property
    def measured_here(self) -> str:
        return self.fields.get("Measured here", "")

    @property
    def variability(self) -> str:
        return self.fields.get("Rigid or publisher-dependent", "")

    @property
    def falsified_by(self) -> str:
        return self.fields.get("Would be falsified by", "")

    @property
    def known_exceptions(self) -> str:
        return self.fields.get("Known exceptions", "")

    @property
    def code(self) -> str:
        return self.fields.get("Code", "")

    # -- derived facts ------------------------------------------------------
    @property
    def is_refuted(self) -> bool:
        """Refuted OUTRIGHT. An internal caveat is not this."""
        return self.refutation is Refutation.WHOLE_ENTRY

    @property
    def is_live(self) -> bool:
        return not self.is_refuted

    @property
    def is_measured_here(self) -> bool:
        return self.status is Status.MEASURED_HERE

    @property
    def is_literature_only(self) -> bool:
        return self.status is Status.LITERATURE_ONLY

    @property
    def is_publisher_dependent(self) -> bool:
        """⚠️ TRUE only when the variability row LEADS with it.

        The registry's own warning is that the leading word undercounts in
        both directions — several `RIGID` entries carry a publisher or scan
        caveat in **Known exceptions**. Read `variability` and
        `known_exceptions`; this flag is a filter, never an answer.
        """
        head = self.variability.replace("*", "").strip().upper()
        return head.startswith("PUBLISHER") or head.startswith("EDITION")

    # -- the accessors that REFUSE -----------------------------------------
    def rule_text(self) -> str:
        """The rule, for a consumer that means to act on it.

        Raises `RefutedConvention` when the entry is refuted outright. Use
        `.says` to read a refuted entry's text as evidence.
        """
        if self.is_refuted:
            raise RefutedConvention(
                f"{self.id} is REFUTED HERE and is not a rule: "
                f"{self.title!r}. Its text is readable as evidence via "
                f".says; it may not be consumed as a licence."
            )
        return self.says

    def measured_figure(self) -> str:
        """What was measured on a plate here.

        Raises `NotMeasuredHere` for a LITERATURE ONLY or ASSERTED entry —
        the registry's first discipline, enforced rather than requested.
        """
        if self.status in (Status.LITERATURE_ONLY, Status.ASSERTED):
            raise NotMeasuredHere(
                f"{self.id} is {self.status.value} and has no measurement "
                f"here: {self.title!r}. A font default is not a measurement "
                f"of a plate; read .literature or .numbers instead."
            )
        if self.is_refuted:
            raise RefutedConvention(
                f"{self.id} is REFUTED HERE; its measurement is a refutation."
            )
        return self.measured_here

    def to_json(self) -> Dict[str, object]:
        return {
            "id": self.id,
            "sources": list(self.sources),
            "title": self.title,
            "slug": self.slug,
            "category": self.category,
            "line": self.line,
            "status": self.status.value,
            "status_note": self.status_note,
            "refutation": self.refutation.value,
            "testability": self.testability.value,
            "publisher_dependent": self.is_publisher_dependent,
            "code_paths": list(self.code_paths),
            "declares_no_consumer": self.declares_no_consumer,
            "cited_in_disagreements": self.cited_in_disagreements,
            "missing_fields": list(self.missing_fields),
            "fields": dict(self.fields),
        }


@dataclass(frozen=True)
class Problem:
    """One thing the document and the parse disagree about."""

    kind: str
    subject: str
    detail: str

    def __str__(self) -> str:
        return f"{self.kind}: {self.subject} — {self.detail}"


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------
_ENTRY_TAG = re.compile(r"^`\[([CL]\d+(?:\s*\+\s*[CL]\d+)*)\]`\s*$")
_SOURCE_TOKEN = re.compile(r"[CL]\d+")
_FIELD_LINE = re.compile(r"^- \*\*([^*]+):\*\*\s*(.*)$")
# A `path/to/file.py` or `path/to/file.py:123` inside a Code row.
_CODE_PATH = re.compile(r"`([A-Za-z0-9_./-]+\.(?:py|md|json|yaml|yml|ly))(:\d+)?`")
_NO_CONSUMER = re.compile(
    r"no (?:reader-side )?consumer found|nothing reads it|consumed by nothing"
    r"|no consumer|not built",
    re.I,
)


def _normalise_status(raw: str) -> Tuple[Status, str]:
    plain = raw.replace("*", "").strip()
    upper = plain.upper()
    for word in _STATUS_WORDS:
        if upper.startswith(word):
            return Status(word), plain[len(word):].strip(" —-–.")
    raise ValueError(f"unrecognised Status row: {raw!r}")


def _section_bodies(text: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    parts = re.split(r"^## (.+?)\s*$", text, flags=re.M)
    for i in range(1, len(parts), 2):
        out[parts[i].strip()] = parts[i + 1]
    return out


@dataclass
class Registry:
    """Every entry in the document, parsed, plus what the document CLAIMS.

    The claims (its own Counts tables) are parsed too, so `problems()` can
    compare the document against itself rather than against anything written
    here. Neither side is a hand list.
    """

    path: Path
    entries: Tuple[Convention, ...]
    claimed_status_counts: Dict[str, int]
    claimed_category_counts: Dict[str, int]
    claimed_category_literature: Dict[str, int]
    claimed_contents_counts: Dict[str, int]
    failed_table_anchors: Dict[str, str]
    claimed_entry_total: Optional[int]
    claimed_source_total: Optional[int]
    failed_table_ids: Tuple[str, ...]
    internal_caveat_ids: Tuple[str, ...]
    disagreement_ids: Tuple[str, ...]
    anchors_referenced: Tuple[str, ...]
    heading_slugs: Tuple[str, ...]
    conservation_rows: Dict[str, str] = field(default_factory=dict)

    # -- lookup -------------------------------------------------------------
    def __iter__(self) -> Iterator[Convention]:
        return iter(self.entries)

    def __len__(self) -> int:
        return len(self.entries)

    def by_id(self, ident: str) -> Convention:
        key = ident.strip().upper()
        for entry in self.entries:
            if entry.id == key:
                return entry
        raise KeyError(f"no convention with id {ident!r}")

    def by_source(self, token: str) -> Convention:
        """The entry that ABSORBED a source-file entry (`C34`, `L46`)."""
        key = token.strip().upper()
        for entry in self.entries:
            if key in entry.sources:
                return entry
        raise KeyError(f"no convention carrying source {token!r}")

    def by_slug(self, slug: str) -> Convention:
        for entry in self.entries:
            if entry.slug == slug:
                return entry
        raise KeyError(f"no convention with slug {slug!r}")

    def categories(self) -> Tuple[str, ...]:
        seen: List[str] = []
        for entry in self.entries:
            if entry.category not in seen:
                seen.append(entry.category)
        return tuple(seen)

    def in_category(self, category: str) -> Tuple[Convention, ...]:
        return tuple(e for e in self.entries if e.category == category)

    def with_status(self, status: Status) -> Tuple[Convention, ...]:
        return tuple(e for e in self.entries if e.status is status)

    def refuted(self) -> Tuple[Convention, ...]:
        return tuple(e for e in self.entries if e.is_refuted)

    def live_rules(self) -> Tuple[Convention, ...]:
        """Every entry that is NOT refuted outright.

        ⚠️ Nine of these carry a refutation INSIDE them
        (`refutation is Refutation.INTERNAL_CAVEAT`). They are live and they
        have a named trap; read `known_exceptions` before quoting `says`.
        """
        return tuple(e for e in self.entries if e.is_live)

    def testable(self) -> Tuple[Convention, ...]:
        return tuple(
            e for e in self.entries
            if e.testability is Testability.TESTABLE_AGAINST_INK
        )

    def without_consumer(self) -> Tuple[Convention, ...]:
        """Entries whose own **Code** row says nothing reads them.

        The registry's point 6: *the value existed and nothing read it* is
        this tree's highest-yield bug class, and the document is a list of
        the values.
        """
        return tuple(e for e in self.entries if e.declares_no_consumer)

    # -- reach --------------------------------------------------------------
    def reach(self) -> Dict[str, int]:
        """The POSITIVE CONTROL. Every number here must be non-zero."""
        sources = {t for e in self.entries for t in e.sources}
        return {
            "entries_parsed": len(self.entries),
            "entries_with_all_fields": sum(
                1 for e in self.entries if not e.missing_fields
            ),
            "source_tokens_resolved": len(sources),
            "statuses_resolved": sum(
                1 for e in self.entries if e.status is not None
            ),
            "refuted_found": len(self.refuted()),
            "testable_found": len(self.testable()),
            "anchors_referenced": len(self.anchors_referenced),
            "claims_parsed": (
                len(self.claimed_status_counts)
                + len(self.claimed_category_counts)
            ),
            "conservation_rows": len(self.conservation_rows),
            "contents_rows": len(self.claimed_contents_counts),
            "failed_table_rows": len(self.failed_table_anchors),
        }

    def field_coverage(self) -> Dict[str, int]:
        return {
            name: sum(1 for e in self.entries if e.fields.get(name, "").strip())
            for name in REQUIRED_FIELDS
        }

    # -- the check ----------------------------------------------------------
    def problems(self) -> List[Problem]:
        """Everything the document and the parse disagree about."""
        found: List[Problem] = []

        # 1. Every entry carries every field, non-empty.
        for entry in self.entries:
            for name in entry.missing_fields:
                found.append(Problem("MISSING FIELD", entry.id,
                                     f"{name!r} is absent or empty"))

        # 1b. A Status row the parse could not read. Never graded, never
        #     defaulted — "cannot tell" stays "cannot tell".
        for entry in self.entries:
            if entry.status is Status.UNREADABLE:
                found.append(Problem("STATUS UNREADABLE", entry.id,
                                     f"row does not begin with any of "
                                     f"{', '.join(_STATUS_WORDS)}: "
                                     f"{entry.status_note[:60]!r}"))
            if not entry.sources:
                found.append(Problem("NO SOURCE TAG", entry.id,
                                     "entry carries no [C../L..] source tag"))

        # 2. Slugs are unique.
        #
        # ⚠️ There is deliberately NO separate duplicate-ID check. An entry's
        # id IS its first source token, so two entries can only share an id
        # by sharing a source token, and (3) below fires on exactly that. A
        # duplicate-ID branch was written, found by the mutation battery to
        # be an EQUIVALENT MUTANT — no mutation of it could go red — and
        # DELETED. A branch that cannot be reached cannot be wrong, and
        # cannot be right either.
        seen_slug: Dict[str, str] = {}
        for entry in self.entries:
            if entry.slug in seen_slug:
                found.append(Problem("DUPLICATE SLUG", entry.slug,
                                     f"{entry.title!r} and {seen_slug[entry.slug]!r}"))
            seen_slug[entry.slug] = entry.title

        # 3. A source token belongs to exactly one entry.
        owners: Dict[str, List[str]] = {}
        for entry in self.entries:
            for token in entry.sources:
                owners.setdefault(token, []).append(entry.id)
        for token, ids in sorted(owners.items()):
            if len(ids) > 1:
                found.append(Problem("SOURCE CLAIMED TWICE", token,
                                     f"claimed by {', '.join(ids)}"))

        # 4. CONSERVATION: the source numbering has no gap and no surplus.
        #    Derived from the entries and from the Conservation ledger, both
        #    of which are in the document; neither is written here.
        for prefix in ("C", "L"):
            nums = sorted(int(t[1:]) for t in owners if t.startswith(prefix))
            if not nums:
                continue
            missing = [n for n in range(1, max(nums) + 1) if n not in set(nums)]
            for n in missing:
                found.append(Problem("SOURCE ENTRY VANISHED", f"{prefix}{n}",
                                     "numbered in the source range and carried "
                                     "by no registry entry"))
        for token in sorted(self.conservation_rows):
            if token not in owners:
                found.append(Problem("CONSERVATION ROW UNPLACED", token,
                                     "named in the Conservation ledger and "
                                     "carried by no entry"))
        for token in sorted(owners):
            if self.conservation_rows and token not in self.conservation_rows:
                found.append(Problem("CONSERVATION ROW MISSING", token,
                                     "carried by an entry and absent from the "
                                     "Conservation ledger"))

        # 5. The document's own Counts tables must match the entries.
        actual_status: Dict[str, int] = {}
        for entry in self.entries:
            actual_status[entry.status.value] = actual_status.get(
                entry.status.value, 0) + 1
        for name, claimed in sorted(self.claimed_status_counts.items()):
            got = actual_status.get(name, 0)
            if got != claimed:
                found.append(Problem("COUNT DISAGREES", f"status {name}",
                                     f"document says {claimed}, entries give {got}"))
        for name in sorted(actual_status):
            if self.claimed_status_counts and name not in self.claimed_status_counts:
                found.append(Problem("COUNT DISAGREES", f"status {name}",
                                     "present in the entries and absent from "
                                     "the Counts table"))

        actual_cat: Dict[str, int] = {}
        actual_cat_lit: Dict[str, int] = {}
        for entry in self.entries:
            actual_cat[entry.category] = actual_cat.get(entry.category, 0) + 1
            if not any(t.startswith("C") for t in entry.sources):
                actual_cat_lit[entry.category] = actual_cat_lit.get(
                    entry.category, 0) + 1
        for name, claimed in sorted(self.claimed_category_counts.items()):
            got = actual_cat.get(name, 0)
            if got != claimed:
                found.append(Problem("COUNT DISAGREES", f"category {name}",
                                     f"document says {claimed}, entries give {got}"))
        for name, claimed in sorted(self.claimed_category_literature.items()):
            got = actual_cat_lit.get(name, 0)
            if got != claimed:
                found.append(Problem(
                    "COUNT DISAGREES", f"category {name} literature-only",
                    f"document says {claimed}, entries give {got}"))

        if self.claimed_entry_total is not None and \
                self.claimed_entry_total != len(self.entries):
            found.append(Problem("COUNT DISAGREES", "registry entries",
                                 f"document says {self.claimed_entry_total}, "
                                 f"parse gives {len(self.entries)}"))
        if self.claimed_source_total is not None and \
                self.claimed_source_total != len(owners):
            found.append(Problem("COUNT DISAGREES", "source entries",
                                 f"document says {self.claimed_source_total}, "
                                 f"entries carry {len(owners)}"))

        # 6. A REFUTED entry must be refuted in BOTH places — the FAILED
        #    table and its own Status row. Either alone is a live rule
        #    wearing a refutation, which is the one thing this registry must
        #    not let happen.
        table = set(self.failed_table_ids)
        status_refuted = {e.id for e in self.entries
                          if e.status is Status.REFUTED_HERE}
        for ident in sorted(table - status_refuted):
            found.append(Problem("REFUTATION HALF-STATED", ident,
                                 "listed in 'Conventions that FAILED here' "
                                 "and its Status row does not say REFUTED"))
        for ident in sorted(status_refuted - table):
            found.append(Problem("REFUTATION HALF-STATED", ident,
                                 "Status says REFUTED and it is absent from "
                                 "'Conventions that FAILED here'"))

        # 6b. The FAILED table gives each refuted entry TWICE — a link and a
        #     source tag. They must name the same entry, or a reader
        #     following the link lands on a live rule while believing it
        #     refuted, which is this registry's one forbidden outcome.
        for token, anchor in sorted(self.failed_table_anchors.items()):
            try:
                by_anchor = self.by_slug(anchor).id
            except KeyError:
                continue  # already reported as BROKEN ANCHOR
            try:
                by_tag = self.by_source(token).id
            except KeyError:
                continue  # already reported as DANGLING CITATION
            if by_anchor != by_tag:
                found.append(Problem("REFUTATION ROW MISADDRESSED", token,
                                     f"its link lands on {by_anchor} and its "
                                     f"tag names {by_tag}"))

        # 6c. The Contents list restates every category's size.
        for name, claimed in sorted(self.claimed_contents_counts.items()):
            got = len(self.in_category(name))
            if got != claimed:
                found.append(Problem("COUNT DISAGREES", f"contents {name}",
                                     f"Contents says {claimed}, entries give "
                                     f"{got}"))

        # 7. Every id cited in a prose section resolves to an entry.
        known = {e.id for e in self.entries} | set(owners)
        for label, idents in (
            ("FAILED table", self.failed_table_ids),
            ("internal-refutation bullet", self.internal_caveat_ids),
            ("DISAGREE section", self.disagreement_ids),
        ):
            for ident in idents:
                if ident not in known:
                    found.append(Problem("DANGLING CITATION", ident,
                                         f"cited in the {label} and no entry "
                                         f"carries it"))

        # 8. Every internal link resolves to a heading.
        heads = set(self.heading_slugs)
        for anchor in self.anchors_referenced:
            if anchor not in heads:
                found.append(Problem("BROKEN ANCHOR", anchor,
                                     "linked and no heading produces it"))

        return found


def _parse_counts(text: str) -> Tuple[Dict[str, int], Dict[str, int],
                                      Dict[str, int], Optional[int],
                                      Optional[int]]:
    sections = _section_bodies(text)
    body = sections.get("Counts", "")
    status: Dict[str, int] = {}
    cats: Dict[str, int] = {}
    cats_lit: Dict[str, int] = {}
    entry_total: Optional[int] = None
    source_total: Optional[int] = None

    head = re.search(r"\*\*(\d+) registry entries\*\*,\s*from (\d+) source",
                     body)
    if head:
        entry_total = int(head.group(1))
        source_total = int(head.group(2))

    for line in body.split("\n"):
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 2:
            name = cells[0].replace("*", "").strip()
            if name.lower() in ("status", "n") or not cells[1].isdigit():
                continue
            # "LITERATURE ONLY (untested here)" -> the status word.
            for word in _STATUS_WORDS:
                if name.upper().startswith(word):
                    status[word] = int(cells[1])
                    break
        elif len(cells) == 3:
            name = cells[0].replace("*", "").strip()
            nums = [c.replace("*", "").strip() for c in cells[1:]]
            if name.lower() in ("category", "total") or not nums[0].isdigit():
                continue
            cats[name] = int(nums[0])
            if nums[1].isdigit():
                cats_lit[name] = int(nums[1])
    return status, cats, cats_lit, entry_total, source_total


def _parse_conservation(text: str) -> Dict[str, str]:
    """The Conservation ledger's rows: source token -> source entry name."""
    body = _section_bodies(text).get("Conservation", "")
    rows: Dict[str, str] = {}
    for line in body.split("\n"):
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2:
            continue
        token = cells[0].replace("*", "").strip()
        if re.fullmatch(r"[CL]\d+", token):
            rows[token] = cells[1]
    return rows


def parse(text: str, path: Optional[Path] = None) -> Registry:
    """Parse the registry markdown. Knows no convention by name."""
    lines = text.split("\n")
    heading_slugs: List[str] = []
    for line in lines:
        if line.startswith("## "):
            heading_slugs.append(slugify(line[3:]))
        elif line.startswith("### "):
            heading_slugs.append(slugify(line[4:]))
        elif line.startswith("# "):
            heading_slugs.append(slugify(line[2:]))

    # An ENTRY is an H3 immediately followed by its source-tag line. That
    # pairing is the document's own shape and it is what separates the 114
    # entries from the 11 other H3s (the Conservation sub-headings and the
    # arithmetic block), with no list of exceptions anywhere.
    starts: List[int] = []
    for i, line in enumerate(lines):
        if line.startswith("### ") and i + 1 < len(lines) \
                and _ENTRY_TAG.match(lines[i + 1].strip()):
            starts.append(i)

    h2_at: List[Tuple[int, str]] = [
        (i, line[3:].strip()) for i, line in enumerate(lines)
        if line.startswith("## ")
    ]

    def category_of(index: int) -> str:
        name = ""
        for at, title in h2_at:
            if at < index:
                name = title
        return name

    sections = _section_bodies(text)
    failed_body = sections.get("Conventions that FAILED here", "")
    failed_ids = [
        m.group(1)
        for line in failed_body.split("\n") if line.startswith("| [")
        for m in [re.search(r"`\[([CL]\d+)", line)] if m
    ]
    caveat_ids = re.findall(r"^- \*\*`\[([CL]\d+)\]`\*\*", failed_body, re.M)
    disagree_ids = sorted(set(re.findall(
        r"`\[?([CL]\d+)\]?`",
        sections.get("Where the two sources DISAGREE", ""))))
    anchors = sorted(set(re.findall(r"\]\(#([a-z0-9\-_]+)\)", text)))

    contents_body = sections.get("Contents", "")
    contents_counts = {
        m.group(1).strip(): int(m.group(2))
        for m in re.finditer(r"^- \[([^\]]+)\]\(#[^)]+\) — (\d+)\s*$",
                             contents_body, re.M)
    }
    failed_anchors: Dict[str, str] = {}
    for line in failed_body.split("\n"):
        if not line.startswith("| ["):
            continue
        anchor = re.search(r"\]\(#([a-z0-9\-_]+)\)", line)
        tag = re.search(r"`\[([CL]\d+)", line)
        if anchor and tag:
            failed_anchors[tag.group(1)] = anchor.group(1)

    failed_set = set(failed_ids)
    caveat_set = set(caveat_ids)
    disagree_set = set(disagree_ids)

    entries: List[Convention] = []
    for n, start in enumerate(starts):
        end = starts[n + 1] if n + 1 < len(starts) else len(lines)
        block = lines[start:end]
        title = block[0][4:].strip()
        tag = _ENTRY_TAG.match(block[1].strip())
        sources = tuple(_SOURCE_TOKEN.findall(tag.group(1))) if tag else ()

        fields: Dict[str, str] = {}
        current: Optional[str] = None
        buffer: List[str] = []
        for raw in block[2:]:
            if raw.startswith("## ") or raw.startswith("### "):
                break
            match = _FIELD_LINE.match(raw)
            if match:
                if current is not None:
                    fields[current] = "\n".join(buffer).strip()
                current = match.group(1).strip()
                buffer = [match.group(2)]
            elif current is not None and raw.startswith("  "):
                buffer.append(raw.strip())
            elif current is not None and not raw.strip():
                continue
        if current is not None:
            fields[current] = "\n".join(buffer).strip()

        missing = tuple(
            name for name in REQUIRED_FIELDS if not fields.get(name, "").strip()
        )

        status_raw = fields.get("Status", "")
        try:
            status, note = _normalise_status(status_raw)
        except ValueError:
            status, note = Status.UNREADABLE, status_raw.strip()

        ident = sources[0] if sources else slugify(title)[:24]

        if ident in failed_set or any(s in failed_set for s in sources) \
                or status is Status.REFUTED_HERE:
            refutation = Refutation.WHOLE_ENTRY
        elif ident in caveat_set or any(s in caveat_set for s in sources):
            refutation = Refutation.INTERNAL_CAVEAT
        else:
            refutation = Refutation.NONE

        if status is Status.UNREADABLE:
            grade = Testability.UNGRADED
        elif refutation is Refutation.WHOLE_ENTRY:
            grade = Testability.REFUTED
        elif fields.get("Predicts (mechanically)", "").strip() and \
                fields.get("Would be falsified by", "").strip():
            grade = Testability.TESTABLE_AGAINST_INK
        else:
            grade = Testability.UNGRADED

        code_row = fields.get("Code", "")
        code_paths = tuple(
            m.group(1) + (m.group(2) or "") for m in _CODE_PATH.finditer(code_row)
        )

        entries.append(Convention(
            id=ident,
            sources=sources,
            title=title,
            slug=slugify(title),
            category=category_of(start),
            line=start + 1,
            fields=fields,
            status=status,
            status_note=note,
            refutation=refutation,
            testability=grade,
            code_paths=code_paths,
            declares_no_consumer=bool(_NO_CONSUMER.search(code_row)),
            cited_in_disagreements=(
                ident in disagree_set or any(s in disagree_set for s in sources)
            ),
            missing_fields=missing,
        ))

    status_counts, cat_counts, cat_lit, entry_total, source_total = \
        _parse_counts(text)

    return Registry(
        path=path or default_doc_path(),
        entries=tuple(entries),
        claimed_status_counts=status_counts,
        claimed_category_counts=cat_counts,
        claimed_category_literature=cat_lit,
        claimed_entry_total=entry_total,
        claimed_source_total=source_total,
        failed_table_ids=tuple(failed_ids),
        internal_caveat_ids=tuple(caveat_ids),
        disagreement_ids=tuple(disagree_ids),
        anchors_referenced=tuple(anchors),
        heading_slugs=tuple(heading_slugs),
        conservation_rows=_parse_conservation(text),
        claimed_contents_counts=contents_counts,
        failed_table_anchors=failed_anchors,
    )


def load(path: Optional[Path] = None) -> Registry:
    """Parse `docs/engraving-conventions.md` (or another copy of it)."""
    doc = Path(path) if path else default_doc_path()
    return parse(doc.read_text(encoding="utf-8"), path=doc)


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------
def format_report(reg: Registry) -> str:
    out: List[str] = []
    out.append("THE ENGRAVING-CONVENTION REGISTRY")
    out.append(f"  {reg.path}")
    out.append("")
    out.append("REACH  (every number must be non-zero, or the parse is DEAD)")
    for name, value in reg.reach().items():
        flag = "  <-- ZERO" if value == 0 else ""
        out.append(f"  {value:6d}  {name}{flag}")
    out.append("")
    out.append("FIELD COVERAGE  (of %d entries)" % len(reg))
    for name, value in reg.field_coverage().items():
        flag = "  <-- ZERO" if value == 0 else ""
        out.append(f"  {value:6d}  {name}{flag}")
    out.append("")
    out.append("STATUS  — never promotable")
    for status in Status:
        rows = reg.with_status(status)
        if rows:
            out.append(f"  {len(rows):6d}  {status.value}")
    out.append("")
    out.append("USABLE AS A TEST")
    for grade in Testability:
        rows = [e for e in reg if e.testability is grade]
        if rows:
            out.append(f"  {len(rows):6d}  {grade.value}")
    out.append("")
    out.append("REFUTATION")
    for kind in Refutation:
        rows = [e for e in reg if e.refutation is kind]
        if rows:
            out.append(f"  {len(rows):6d}  {kind.value}")
    out.append("")
    out.append("REFUTED OUTRIGHT — never a live rule")
    for entry in reg.refuted():
        out.append(f"  {entry.id:<5} {entry.title}")
    out.append("")
    out.append("LIVE, WITH A REFUTATION INSIDE — read Known exceptions first")
    for entry in reg:
        if entry.refutation is Refutation.INTERNAL_CAVEAT:
            out.append(f"  {entry.id:<5} {entry.title}")
    out.append("")
    out.append("CATEGORIES")
    for name in reg.categories():
        rows = reg.in_category(name)
        lit = sum(1 for e in rows if e.is_literature_only)
        out.append(f"  {len(rows):6d}  {name}   (literature-only {lit})")
    out.append("")
    no_consumer = reg.without_consumer()
    out.append("THE REGISTRY'S OWN POINT 6 — entries whose Code row says "
               "nothing reads them")
    out.append(f"  {len(no_consumer)} of {len(reg)}")
    out.append("")
    problems = reg.problems()
    if problems:
        out.append(f"FINDINGS  ({len(problems)})")
        for problem in problems:
            out.append(f"  {problem}")
    else:
        out.append("FINDINGS  (0) — the document agrees with itself")
    return "\n".join(out)


def format_entry(entry: Convention) -> str:
    out = [f"{entry.id}  [{' + '.join(entry.sources)}]",
           f"  {entry.title}",
           f"  category   {entry.category}   (line {entry.line})",
           f"  status     {entry.status.value}"
           + (f" — {entry.status_note}" if entry.status_note else ""),
           f"  refutation {entry.refutation.value}",
           f"  testable   {entry.testability.value}",
           f"  anchor     #{entry.slug}"]
    if entry.is_refuted:
        out.append("  ⚠️ REFUTED OUTRIGHT — rule_text() refuses this entry.")
    elif entry.refutation is Refutation.INTERNAL_CAVEAT:
        out.append("  ⚠️ live, and it carries a refutation INSIDE it.")
    out.append("")
    for name in REQUIRED_FIELDS:
        out.append(f"  {name}:")
        out.append(f"    {entry.fields.get(name, '(absent)')}")
    return "\n".join(out)


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--doc", default=None,
                    help="path to the registry markdown "
                         "(default: docs/engraving-conventions.md)")
    ap.add_argument("--id", default=None,
                    help="print ONE entry in full, by id (C34) or source (L46)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--check", action="store_true",
                    help="exit 1 on a finding, 2 if the parse reaches nothing")
    args = ap.parse_args(argv)

    reg = load(Path(args.doc) if args.doc else None)

    if args.id:
        try:
            entry = reg.by_id(args.id)
        except KeyError:
            entry = reg.by_source(args.id)
        print(json.dumps(entry.to_json(), indent=2) if args.json
              else format_entry(entry))
        return 0

    if args.json:
        print(json.dumps({
            "doc": str(reg.path),
            "reach": reg.reach(),
            "field_coverage": reg.field_coverage(),
            "entries": [e.to_json() for e in reg],
            "problems": [{"kind": p.kind, "subject": p.subject,
                          "detail": p.detail} for p in reg.problems()],
        }, indent=2))
    else:
        print(format_report(reg))

    if args.check:
        # ⚠️ THE POSITIVE CONTROL IS CHECKED FIRST. A parser that matches
        # nothing reports a clean registry, and this repo has shipped
        # exactly that guard once already.
        dead = [name for name, value in reg.reach().items() if value == 0]
        if dead:
            print("\nDEAD: the parse reaches nothing — " + ", ".join(dead)
                  + ". No finding below this line means anything.",
                  file=sys.stderr)
            return 2
        problems = reg.problems()
        if problems:
            print(f"\nFAIL: {len(problems)} finding(s); the document and the "
                  f"parse disagree.", file=sys.stderr)
            return 1
        print("\nOK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
