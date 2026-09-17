"""WHERE THINGS FALL — an accumulating store of what we have seen, and where.

Sean, 2026-09-17:

    "We need every bit of information gathered and stored in one place where
    the different stages can continue to learn how to better identify as it
    processes all of the information."

    "it might be helpful to have general information based on publisher or
    common practice of where a certain things fall so if we have an
    undiagnosed blob or dot, we have gathered a lot of information on what
    sorts of things are more likely where."

Today nothing survives the page it was measured on.  Every staged record is
written, exported, and its measurements are never consulted again; each page
starts from zero forever.  This module is the place where they accumulate.

⚠️⚠️ **THE BASE LAYER IS FULL-GRAIN AND EVERY AGGREGATE IS A DERIVED VIEW.**
This design was corrected twice and the second correction is the governing
one.  Sean, on the bucketed histogram that stood here for an hour:

    "I feel like you're trying to solve problems down the road that we can't
    yet predict all the variables of and doing so limiting the build
    architecture.  We may need shape.  We may need location.  We may need
    context on the page or context historically of what we've gathered ... we
    need to find a way to do it that doesn't limit every dot of black from
    being potentially nothing, something, or a part of many things."

A bucket is **a lossy summary decided at storage time**, and `A-INK-3` says
discarding is a decision and decisions belong in a later stage.  A tally of
*"N rests in this square"* has already thrown away which ink made them and
cannot express one dot belonging to several things at once.  So the stored form
is the ENTRY, at the grain it was observed, with every attribute kept; the
position histogram is `PositionIndex`, **computed on demand and rebuildable at
any resolution**, which is what stops bucket size from being a permanent
commitment.

⚠️⚠️ **MEMBERSHIP IS A SET, NEVER A FIELD.**  A piece of ink may belong to
nothing, one thing, or many things.  An earlier draft gave `Entry` a single
`label`, which is exactly the shape Sean's objection names -- it absorbs a
dot's identity into whatever claimed it first.  `Entry.memberships` is a tuple
and may be **empty**, which is the ABSENT/DECLINED distinction applied to ink:
*there is no unseen ink, only unclassified.*

⚠️ **AND THE RECORD ALREADY CARRIES MULTI-MEMBERSHIP THAT NOTHING READS.**
`Q.INK`'s `ink_explained_by` is a LIST of the classes whose detector boxes
overlap a component, and its docstring is explicit that it *"does NOT claim the
component IS one of them"*.  That is many-to-many evidence, already gathered,
consumed by nothing -- the pattern this repo has now found more than ten times.
Flattening it to one label would have destroyed it on the way in.

⚠️⚠️ **WHY IT IS KEYED ON POSITION AND NOT ON THE COMPONENT.**  The first
design keyed entries on the connected component, justified by storage
arithmetic.  Sean killed it: *"how do we know what a component is at the other
stage?"*  A component is not a stable unit -- measured in this repo on two
plates of the same era, Litolff p.62 yields **1,244** components and MERGES
marks, Breitkopf p.1 yields **6,055** and SHATTERS, 56% of them specks, 30
components per cell against 5.6, and the ink layer's own findings say
*neither gives one row per mark.*  The same printed fermata is one component on
one plate and three on another, so a component-keyed store would accumulate
statistics about our SEGMENTATION rather than about the music.  A POSITION does
not care how any run grouped the pixels.

⚠️⚠️ **PROVENANCE TIERS ARE NEVER POOLED BY DEFAULT.**  A store populated from
our own readings and then used to identify new ink is learning from its own
output.  This repo has the scar and the doctrine: `source_kind` exists because
an arbiter that is *"an OMR output of the same raster"* fails together with the
thing it arbitrates, which is why the catalog's `works` tier is admitted and
the `editions` tier refused.  Every entry carries its tier; `ask()` REQUIRES a
tier and refuses to merge them unless a caller says so in as many words.

⚠️ **NO DECISION MAY READ THIS STORE YET.**  It ships producer-only, the same
discipline `Q.INK` shipped under, because a store and its first consumer
landing together makes the reach measurement circular.
"""
from __future__ import annotations

import json
import math
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import (Any, Dict, Iterable, Iterator, List, Optional, Sequence,
                    Set, Tuple)

# ─────────────────────────────────────────────────────────────────────────────
# Provenance tiers
# ─────────────────────────────────────────────────────────────────────────────

#: Position known BY CONSTRUCTION -- we rendered the page, so we know where the
#: renderer put every glyph.  `tools/omr/page_truth.py` emits exactly this from
#: Verovio's `svgBoundingBoxes`.  Free of the circularity below.
TIER_TRUE = "true"

#: A position we READ off a raster.  Useful, and circular the moment it is fed
#: back as truth.
TIER_OBSERVED = "observed"

TIERS = (TIER_TRUE, TIER_OBSERVED)

#: ⚠️ A page truth is not an ENCODING truth, and `page_truth.py` says so in its
#: own docstring: MusicXML writes a `<slur>` at each END while an engraver
#: draws ONE arc, and a clef is declared once and printed every system.  A TRUE
#: entry is truth about WHERE INK WAS DRAWN -- which is the only thing this
#: store claims to hold -- and not about what the encoding says.
TRUE_TIER_CAVEAT = (
    "TRUE positions are where the RENDERER drew ink; they are not an "
    "encoding truth and element counts do not match the MusicXML's.")

UNKNOWN = "UNKNOWN"


# ─────────────────────────────────────────────────────────────────────────────
# Membership — a set, never a field
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Membership:
    """One claim that a piece of ink belongs to something.

    ⚠️ `kind` is what sort of claim this is, and keeping it is what lets a
    later stage weigh claims differently instead of treating them as one
    vocabulary.  `detector_class` is an argmax over a box; `overlaps` is
    `ink_explained_by`, which its own docstring says is coverage and NOT an
    assertion of identity; `drawn_as` is the renderer's own answer and cannot
    be wrong about what it drew.
    """

    kind: str
    name: str
    source: str
    confidence: Optional[float] = None

    def to_json(self) -> Dict[str, Any]:
        d = {"kind": self.kind, "name": self.name, "source": self.source}
        if self.confidence is not None:
            d["confidence"] = round(float(self.confidence), 4)
        return d


#: A detector's argmax class for a box it fired on.
KIND_DETECTOR_CLASS = "detector_class"
#: A class whose box merely OVERLAPS this ink.  Coverage, not identity.
KIND_OVERLAPS = "overlaps"
#: What a renderer was asked to draw.  TRUE tier only.
KIND_DRAWN_AS = "drawn_as"


#: ⚠️⚠️ THIS VOCABULARY IS THE SAME AXIS AS `record.CLAIM`, AND IT IS MAPPED
#: RATHER THAN RESTATED. `Membership.kind` was INVENTED here because the
#: staged record had nowhere to put "what sort of claim is this" — one of the
#: two independent pieces of work that reached that gap in a week, and the one
#: that paid for it: pooling `detector_class` geometry with `overlaps`
#: geometry reported a Litolff notehead at mean height 3.646 staff spaces
#: against 1.316 ± 0.133 once split.
#:
#: The record now declares the axis (`record.CLAIM`), so these three words are
#: a PROJECTION of it and not a second answer. `test_positional_store.py`
#: asserts the mapping is total over the three constants and lands only on
#: real `CLAIM` words, so the day either vocabulary grows a word the other
#: does not have, a test goes red instead of the two drifting apart.
#:
#: ⚠️ It is deliberately NOT a rename. These three name the claims a
#: MEMBERSHIP can make — the ways one piece of ink can be associated with a
#: NAME — which is a narrower question than the claim a QUANTITY's value
#: makes, and three of `CLAIM`'s five words have no membership form at all.
#: Collapsing them would lose `drawn_as`, whose whole content is *this came
#: from the encoding and not from the plate*.
CLAIM_OF_MEMBERSHIP_KIND: Dict[str, str] = {
    #: An argmax over a box: it can be wrong about what the ink is.
    KIND_DETECTOR_CLASS: "identification",
    #: Coverage, and its own docstring already said so.
    KIND_OVERLAPS: "coverage",
    #: The renderer's own answer — not read off this raster at all, so it
    #: cannot be wrong because the plate is bad. The `source_kind` doctrine's
    #: property, in the store's vocabulary.
    KIND_DRAWN_AS: "external",
}


# ─────────────────────────────────────────────────────────────────────────────
# An entry — the stored form, at the grain it was observed
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Entry:
    """One observation of ink somewhere, with everything we knew about it.

    ⚠️ `staff_position` is the LOAD-BEARING field and is in **staff STEPS**
    measured from the staff's own top line -- the same unit and origin as
    `Q.NOTEHEAD_STAFF_POSITION`, deliberately, so the two compose.  One step is
    half a staff space; 0 is the top line, 8 the bottom line of a five-line
    staff, negative above it.

    It is staff-relative BECAUSE THAT IS THE ONLY VERTICAL QUANTITY THAT
    COMPOSES ACROSS DOCUMENTS.  A `bbox_page_px` is a fact about one page at
    one dpi: pages differ in size and rendering resolution, so a store keyed on
    page pixels pools nothing and is worthless for this purpose.

    ⚠️ Nothing here is chosen for a known consumer.  `A-INK-3`: *"Theoretically
    every position can at some point contribute even if that is not with our
    current pipeline."*  Shape, location, page context and provenance are all
    kept because we cannot yet predict which the later stages want.
    """

    tier: str
    publisher: str
    memberships: Tuple[Membership, ...]
    staff_position: Optional[float]      # staff steps from the top line

    # ── horizontal, normalised so it composes too ──────────────────────────
    #: Where in its BAR the mark sits, 0.0 at the barline to 1.0 at the next.
    #: Normalised for the same reason the vertical is staff-relative: a bar is
    #: a different number of pixels wide on every page and in every system.
    bar_fraction: Optional[float] = None

    # ── shape, as evidence rather than as the key ──────────────────────────
    width_spaces: Optional[float] = None
    height_spaces: Optional[float] = None
    fill: Optional[float] = None
    n_components_in_cell: Optional[int] = None

    # ── page context ───────────────────────────────────────────────────────
    edition_path: Optional[str] = None
    work_id: Optional[str] = None
    image_type: Optional[str] = None
    page: Optional[int] = None
    system: Optional[int] = None
    staff: Optional[int] = None
    staves_in_system: Optional[int] = None
    cell: Optional[int] = None
    source_quantity: Optional[str] = None
    #: The raw page box, kept even though it composes with nothing, because it
    #: is the only way back to the pixels this entry came from.
    bbox_page_px: Optional[List[float]] = None

    # ── views over the membership set ──────────────────────────────────────
    def names(self, kind: Optional[str] = None) -> Set[str]:
        return {m.name for m in self.memberships
                if kind is None or m.kind == kind}

    @property
    def primary(self) -> str:
        """The strongest single claim, for a view that needs exactly one.

        ⚠️ A CONVENIENCE FOR VIEWS, NOT A FACT ABOUT THE INK.  Anything that
        reduces a set to one name is discarding, so this exists only where a
        statistic needs a single label and the reduction is stated there.  It
        is deliberately NOT stored.
        """
        for kind in (KIND_DRAWN_AS, KIND_DETECTOR_CLASS, KIND_OVERLAPS):
            for m in self.memberships:
                if m.kind == kind:
                    return m.name
        return UNKNOWN

    def to_json(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"tier": self.tier, "publisher": self.publisher,
                             "memberships": [m.to_json()
                                             for m in self.memberships]}
        for k in ("staff_position", "bar_fraction", "width_spaces",
                  "height_spaces", "fill", "n_components_in_cell",
                  "edition_path", "work_id", "image_type", "page", "system",
                  "staff", "staves_in_system", "cell", "source_quantity",
                  "bbox_page_px"):
            v = getattr(self, k)
            if v is not None:
                d[k] = v
        return d

    @classmethod
    def from_json(cls, d: Dict[str, Any]) -> "Entry":
        ms = tuple(Membership(m["kind"], m["name"], m["source"],
                              m.get("confidence"))
                   for m in d.get("memberships", ()))
        kw = {k: v for k, v in d.items() if k not in ("memberships",)}
        kw["memberships"] = ms
        # ⚠️ `to_json` OMITS A NONE FIELD to keep the file small, so reading
        # must restore it -- and the one field that is both REQUIRED and
        # legitimately None is `staff_position`. Without this line an
        # UNPOSITIONED entry crashes on read, which is precisely the
        # population `A-INK-3` insists on keeping. Found by the round-trip
        # test, not by review.
        kw.setdefault("staff_position", None)
        return cls(**kw)


# ─────────────────────────────────────────────────────────────────────────────
# The base store — full grain, lossless, append-only
# ─────────────────────────────────────────────────────────────────────────────

class EntryStore:
    """Every entry we have ever accumulated, at the grain it was observed.

    JSON Lines, because the store is append-only across runs and a line-
    delimited file can be extended, streamed and re-read without loading it
    whole -- the same property that makes the 443 MB staged records readable.

    ⚠️ THIS IS THE STORE.  `PositionIndex` below is a VIEW of it.  Deleting
    every index loses nothing; deleting this loses everything.
    """

    def __init__(self, path: Optional[Path] = None) -> None:
        self.path = Path(path) if path else None
        self.entries: List[Entry] = []
        self.sources: List[Dict[str, Any]] = []

    def extend(self, entries: Iterable[Entry]) -> int:
        n = 0
        for e in entries:
            if e.tier not in TIERS:
                raise ValueError(
                    "unknown provenance tier %r; the tier is not optional"
                    % (e.tier,))
            self.entries.append(e)
            n += 1
        return n

    def write(self, path: Optional[Path] = None) -> int:
        p = Path(path or self.path)
        p.parent.mkdir(parents=True, exist_ok=True)
        n = 0
        with open(p, "w") as fh:
            fh.write(json.dumps({"_meta": True, "schema": 1,
                                 "sources": self.sources,
                                 "caveats": {"true_tier": TRUE_TIER_CAVEAT}})
                     + "\n")
            for e in self.entries:
                fh.write(json.dumps(e.to_json(), separators=(",", ":")) + "\n")
                n += 1
        return p.stat().st_size

    @classmethod
    def read(cls, path: Path) -> "EntryStore":
        st = cls(path)
        with open(path) as fh:
            for line in fh:
                d = json.loads(line)
                if d.get("_meta"):
                    st.sources = d.get("sources", [])
                    continue
                st.entries.append(Entry.from_json(d))
        return st

    def summary(self) -> Dict[str, Any]:
        per_tier: Dict[str, int] = defaultdict(int)
        per_pub: Dict[str, int] = defaultdict(int)
        names: Set[str] = set()
        unpositioned = 0
        no_membership = 0
        multi = 0
        for e in self.entries:
            per_tier[e.tier] += 1
            per_pub[e.publisher] += 1
            names |= e.names()
            if e.staff_position is None:
                unpositioned += 1
            if not e.memberships:
                no_membership += 1
            elif len(e.memberships) > 1:
                multi += 1
        return {
            "entries": len(self.entries),
            "per_tier": dict(per_tier),
            "per_publisher": dict(per_pub),
            "distinct_names": len(names),
            "unpositioned": unpositioned,
            "entries_with_no_membership": no_membership,
            "entries_with_several_memberships": multi,
            "sources": self.sources,
        }


# ─────────────────────────────────────────────────────────────────────────────
# A derived view — rebuildable at any resolution, committing to nothing
# ─────────────────────────────────────────────────────────────────────────────

#: ⚠️ CHOSEN BY MEASUREMENT AND NOT A COMMITMENT.  `benchmarks/omr-positional-
#: store-2026-09` sweeps bucket width against the label-shuffle null: the
#: bias-corrected information plateaus over **0.05-0.25 staff spaces** (96%,
#: 100%, 96% of peak) and falls away sharply after -- 79% at 0.5, 36% at 4.0.
#: 0.25 is the COARSE END of that plateau, taken because it keeps 96.1% of the
#: peak information with 2.5x more observations per bucket than the peak at
#: 0.1.  Because the index is derived, this number can be re-chosen at any time
#: and several resolutions can coexist; nothing is lost by it being wrong.
DEFAULT_VBUCKET_SPACES = 0.25
DEFAULT_HBUCKETS = 20


def vbucket(position_steps: float, width_spaces: float) -> int:
    """Bucket index for a staff-relative position.

    `position_steps` is in STEPS and `width_spaces` in SPACES, because the
    record's unit is the step and the criterion was pre-registered in spaces.
    One space is two steps; the conversion lives here, once, rather than at
    each call site.
    """
    return int(math.floor(position_steps / (width_spaces * 2.0)))


def hbucket(bar_fraction: Optional[float], n: int) -> Optional[int]:
    if bar_fraction is None:
        return None
    return min(n - 1, max(0, int(bar_fraction * n)))


@dataclass
class Cell:
    """What was seen in one bucket, for one name, in one tier and publisher."""

    count: int = 0
    _w: float = 0.0
    _w2: float = 0.0
    _h: float = 0.0
    _h2: float = 0.0
    _fill: float = 0.0
    _shape_n: int = 0
    min_h: Optional[float] = None
    max_h: Optional[float] = None
    #: ⚠️ A bucket standing on ONE edition is a fact about that plate, not
    #: about the publisher's practice, so the count of contributing editions
    #: travels with every number here.
    editions: Set[str] = field(default_factory=set)
    #: Indices back into the base store.  This is what keeps the view a VIEW:
    #: any aggregate can be re-derived, and any number can be traced to the ink
    #: that made it.
    rows: List[int] = field(default_factory=list)

    def add(self, e: Entry, idx: int) -> None:
        self.count += 1
        self.rows.append(idx)
        if e.edition_path:
            self.editions.add(e.edition_path)
        if e.width_spaces is None or e.height_spaces is None:
            return
        self._shape_n += 1
        self._w += e.width_spaces
        self._w2 += e.width_spaces ** 2
        self._h += e.height_spaces
        self._h2 += e.height_spaces ** 2
        if e.fill is not None:
            self._fill += e.fill
        self.min_h = e.height_spaces if self.min_h is None \
            else min(self.min_h, e.height_spaces)
        self.max_h = e.height_spaces if self.max_h is None \
            else max(self.max_h, e.height_spaces)

    @staticmethod
    def _sd(s: float, s2: float, n: int) -> Optional[float]:
        if n < 2:
            return None
        var = (s2 - s * s / n) / (n - 1)
        return math.sqrt(var) if var > 0 else 0.0

    def to_json(self, with_rows: bool = False) -> Dict[str, Any]:
        n = self._shape_n
        out: Dict[str, Any] = {"count": self.count,
                               "editions": len(self.editions)}
        if n:
            out.update(
                shape_n=n,
                mean_width_spaces=round(self._w / n, 3),
                sd_width_spaces=_r(self._sd(self._w, self._w2, n)),
                mean_height_spaces=round(self._h / n, 3),
                sd_height_spaces=_r(self._sd(self._h, self._h2, n)),
                mean_fill=round(self._fill / n, 3),
                min_height_spaces=_r(self.min_h),
                max_height_spaces=_r(self.max_h))
        if with_rows:
            out["rows"] = self.rows
        return out


def _r(v: Optional[float]) -> Optional[float]:
    return None if v is None else round(v, 3)


class PositionIndex:
    """A position histogram DERIVED from an `EntryStore`.

    ⚠️⚠️ **THIS IS A VIEW AND MUST STAY ONE.**  It is built on demand, it keeps
    row indices back into the base store, and it may be thrown away and rebuilt
    at a different resolution without losing anything.  The moment something
    persists this INSTEAD of the entries, bucket size becomes a permanent
    decision taken at storage time -- which is the thing Sean's correction
    rejected.

    ⚠️ An entry with SEVERAL memberships is indexed under EACH of them, so the
    counts across names deliberately sum to more than the entry count.  That is
    the honest shape for many-to-many: collapsing to a primary name here would
    reintroduce the single-label flattening one layer down.  `entries_indexed`
    reports the distinct entries so the difference is visible.
    """

    def __init__(self, store: EntryStore, *,
                 vbucket_spaces: float = DEFAULT_VBUCKET_SPACES,
                 hbuckets: int = DEFAULT_HBUCKETS,
                 kinds: Optional[Sequence[str]] = None) -> None:
        self.store = store
        self.vbucket_spaces = float(vbucket_spaces)
        self.hbuckets = int(hbuckets)
        self.kinds = tuple(kinds) if kinds else None
        self._c: Dict[Tuple[str, str, str],
                      Dict[Tuple[int, Optional[int]], Cell]] = defaultdict(dict)
        self.unpositioned = 0
        self.entries_indexed = 0
        self._build()

    def _build(self) -> None:
        for i, e in enumerate(self.store.entries):
            if e.staff_position is None:
                self.unpositioned += 1
                continue
            self.entries_indexed += 1
            bk = (vbucket(e.staff_position, self.vbucket_spaces),
                  hbucket(e.bar_fraction, self.hbuckets))
            names = {m.name for m in e.memberships
                     if self.kinds is None or m.kind in self.kinds}
            for name in (names or {UNKNOWN}):
                d = self._c[(e.tier, e.publisher, name)]
                if bk not in d:
                    d[bk] = Cell()
                d[bk].add(e, i)

    # ── the query ──────────────────────────────────────────────────────────
    def ask(self, staff_position: float, *, tier: Optional[str],
            publisher: Optional[str] = None,
            bar_fraction: Optional[float] = None,
            height_spaces: Optional[float] = None,
            shape_tolerance: float = 2.0,
            require_tier: bool = True) -> Dict[str, Any]:
        """What has been seen HERE?

        ⚠️ `tier` is REQUIRED, and passing `None` is an explicit request to
        pool provenance tiers.  It is not a default, because pooling a rendered
        truth with our own readings is how a store starts laundering its own
        output back in as evidence.  `require_tier=False` is the only way past
        it, and exists so a caller has to say in one place that it meant to.

        ⚠️ The answer is a TABLE OF WHAT WAS SEEN, with counts and the
        contributing edition count beside each row.  It is not a probability
        and it is deliberately not normalised into one: an uncalibrated
        probability is worse than none, measured here at ECE 0.1277.
        """
        if tier is None and require_tier:
            raise ValueError(
                "ask() requires a provenance tier. Pass tier='true' or "
                "tier='observed'; to pool them deliberately pass tier=None "
                "with require_tier=False.")
        vb = vbucket(staff_position, self.vbucket_spaces)
        hb = hbucket(bar_fraction, self.hbuckets)
        hits: List[Dict[str, Any]] = []
        for (t, pub, name), d in self._c.items():
            if tier is not None and t != tier:
                continue
            if publisher is not None and pub != publisher:
                continue
            # ⚠️ MERGED ACROSS THE UNCONSTRAINED AXIS, AND THIS WAS A REAL
            # DEFECT.  A cell is keyed `(vbucket, hbucket)`, so a query that
            # names no `bar_fraction` matches every horizontal bucket at this
            # height -- and the first cut returned them as SEPARATE ROWS, so
            # one name came back nine times with its evidence split nine ways
            # and every `share` nine times too small.  Merging is a VIEW
            # operation and loses nothing: the cells are still there, and
            # constraining `bar_fraction` still narrows to one of them.
            merged: Optional[Cell] = None
            for (v, h), c in d.items():
                if v != vb:
                    continue
                if hb is not None and h is not None and h != hb:
                    continue
                if merged is None:
                    merged = Cell()
                merged.count += c.count
                merged.rows.extend(c.rows)
                merged.editions |= c.editions
                merged._shape_n += c._shape_n
                merged._w += c._w
                merged._w2 += c._w2
                merged._h += c._h
                merged._h2 += c._h2
                merged._fill += c._fill
                for attr, fn in (("min_h", min), ("max_h", max)):
                    mine, theirs = getattr(merged, attr), getattr(c, attr)
                    if theirs is not None:
                        setattr(merged, attr,
                                theirs if mine is None else fn(mine, theirs))
            if merged is None:
                continue
            j = merged.to_json()
            if height_spaces is not None:
                mh = j.get("mean_height_spaces")
                if mh is None:
                    continue
                sd = j.get("sd_height_spaces") or max(mh * 0.5, 1e-6)
                if not (mh - shape_tolerance * sd <= height_spaces
                        <= mh + shape_tolerance * sd):
                    continue
            hits.append(dict(tier=t, publisher=pub, name=name,
                             vbucket=vb, hbucket=hb, **j))
        total = sum(h["count"] for h in hits) or 1
        for h in hits:
            h["share_of_this_position"] = round(h["count"] / total, 4)
        hits.sort(key=lambda h: -h["count"])
        return {
            "query": dict(staff_position=staff_position, tier=tier,
                          publisher=publisher, bar_fraction=bar_fraction,
                          height_spaces=height_spaces, vbucket=vb,
                          hbucket=hb, vbucket_spaces=self.vbucket_spaces),
            "n_candidates": len(hits),
            "observations_here": sum(h["count"] for h in hits),
            "candidates": hits,
        }

    def summary(self) -> Dict[str, Any]:
        buckets = sum(len(d) for d in self._c.values())
        return {"keys": len(self._c), "buckets": buckets,
                "entries_indexed": self.entries_indexed,
                "unpositioned": self.unpositioned,
                "vbucket_spaces": self.vbucket_spaces,
                "hbuckets": self.hbuckets}


# ─────────────────────────────────────────────────────────────────────────────
# Reading a saved staged record
# ─────────────────────────────────────────────────────────────────────────────

def stream_observations(path: Path) -> Iterator[Dict[str, Any]]:
    """Yield each observation of a staged record without loading the file.

    ⚠️ The Brahms record is 443 MB.  `json.load` on it wants several GB, so
    this walks the pretty-printed structure instead: the record is written by
    ``json.dump(..., indent=2)``, so an observation inside
    ``record.observations`` opens at exactly six spaces and closes at exactly
    six, and anything deeper is nested within it.
    """
    started = False
    buf: List[str] = []
    with open(path) as fh:
        for line in fh:
            if not started:
                if '"observations": [' in line:
                    started = True
                continue
            if buf:
                buf.append(line)
                if line.startswith("      }"):
                    yield json.loads("".join(buf).rstrip().rstrip(","))
                    buf = []
                continue
            if line.startswith("      {"):
                buf = [line]
            elif line.startswith("    ]"):
                return


_SUBJ = re.compile(r"^(\w+)/(.*)$")


def _parts(subject: str) -> List[int]:
    m = _SUBJ.match(subject)
    if not m:
        return []
    out = []
    for p in m.group(2).split("/"):
        try:
            out.append(int(p))
        except ValueError:
            return out
    return out


#: ⚠️ ONE SOURCE FOR NAMED MARKS, ON PURPOSE.  `gather_glyph_families` re-files
#: the SAME detections under `rest`, `arc_box`, `dynamic_letter` and friends,
#: on the same `glyph/...` subjects, so accumulating those beside `glyph_box`
#: would count one piece of ink several times and inflate every number in the
#: store.  `glyph_box` is the detector's whole output with its class attached;
#: `ink` is the unnamed population.  Those two, and nothing else.
NAMED_QUANTITY = "glyph_box"
UNNAMED_QUANTITY = "ink"


def entries_from_record(path: Path, *, publisher: str,
                        tier: str = TIER_OBSERVED,
                        edition_path: Optional[str] = None,
                        work_id: Optional[str] = None,
                        image_type: Optional[str] = None) -> Iterator[Entry]:
    """Walk a saved staged record into entries.

    ⚠️⚠️ **THE STAFF-RELATIVE POSITION IS DERIVED HERE, AND NEEDS NO
    RE-GATHER.**  No quantity on the record carries a staff-relative position
    for anything but a notehead -- `Q.INK` and `Q.GLYPH_BOX` carry a canonical
    box and page pixels, and the cell grid's ORIGIN (`top_y`) is computed by
    `_cell_grid` and thrown away.  But `Q.STAFF_LINES` is on the record in the
    PAGE frame, and every mark carries `y_center_page`, so the position is

        (y_center_page - top_line_y) / half_space

    which is the same arithmetic `gather_notehead_positions` does in the cell
    frame, done in the frame the two quantities share.  That is why this store
    can be built from records that already exist.
    """
    lines: Dict[Tuple[int, int, int], List[float]] = {}
    cells: Dict[Tuple[int, int, int, int], List[float]] = {}
    staves_per_system: Dict[Tuple[int, int], Set[int]] = defaultdict(set)
    marks: List[Dict[str, Any]] = []

    for o in stream_observations(path):
        q = o.get("quantity")
        subj = o.get("subject", "")
        if q == "staff_lines":
            p = _parts(subj)
            if len(p) >= 3 and isinstance(o.get("value"), list):
                lines[(p[0], p[1], p[2])] = [float(v) for v in o["value"]]
                staves_per_system[(p[0], p[1])].add(p[2])
        elif q == "cell_box":
            p = _parts(subj)
            if len(p) >= 4 and isinstance(o.get("value"), list) \
                    and len(o["value"]) == 4:
                cells[(p[0], p[1], p[2], p[3])] = [float(v) for v in o["value"]]
        elif q in (NAMED_QUANTITY, UNNAMED_QUANTITY):
            marks.append(o)

    for o in marks:
        p = _parts(o.get("subject", ""))
        if len(p) < 5:
            continue
        page, sysi, staff, cell = p[0], p[1], p[2], p[3]
        d = o.get("detail") or {}
        yc, xc = d.get("y_center_page"), d.get("x_center_page")
        ls = lines.get((page, sysi, staff))
        pos = space = None
        if ls and len(ls) >= 2 and (ls[-1] - ls[0]) > 0:
            space = (ls[-1] - ls[0]) / float(len(ls) - 1)
            if yc is not None:
                pos = (float(yc) - ls[0]) / (space / 2.0)
        # ⚠️ A ONE-LINE PERCUSSION STAFF HAS NO ORIGIN AND NO SPAN, and is
        # DECLINED rather than defaulted: inventing a spacing for it would put
        # a fabricated number into the one field this store is keyed on.
        frac = None
        cb = cells.get((page, sysi, staff, cell))
        if cb and xc is not None and cb[2] > cb[0]:
            frac = min(1.0, max(0.0, (float(xc) - cb[0]) / (cb[2] - cb[0])))

        bb = d.get("bbox_page_px")
        w = h = fill = ncomp = None
        if o["quantity"] == NAMED_QUANTITY:
            val = o.get("value")
            cls = val[0] if isinstance(val, list) and val else None
            ms = (Membership(KIND_DETECTOR_CLASS, cls, "detector",
                             o.get("score")),) if cls else ()
            if bb and space:
                w = round((bb[2] - bb[0]) / space, 3)
                h = round((bb[3] - bb[1]) / space, 3)
        else:
            # ⚠️ MANY-TO-MANY, STRAIGHT OFF THE RECORD.  `ink_explained_by` is
            # a LIST of the classes whose boxes overlap this component, and
            # `gather_ink` is explicit that it "does NOT claim the component IS
            # one of them".  An empty list is unclassified ink and gets an
            # entry with NO membership, which is the point.
            ms = tuple(Membership(KIND_OVERLAPS, str(n), "detector_coverage",
                                  d.get("ink_detector_coverage"))
                       for n in (d.get("ink_explained_by") or ()))
            w, h = d.get("width_spaces"), d.get("height_spaces")
            fill, ncomp = d.get("ink_fill"), d.get("ink_n_components")

        yield Entry(
            tier=tier, publisher=publisher, memberships=ms,
            staff_position=pos, bar_fraction=frac, width_spaces=w,
            height_spaces=h, fill=fill, n_components_in_cell=ncomp,
            edition_path=edition_path, work_id=work_id, image_type=image_type,
            page=page, system=sysi, staff=staff,
            staves_in_system=len(staves_per_system.get((page, sysi), ())) or None,
            cell=cell, source_quantity=o.get("quantity"), bbox_page_px=bb)


# ─────────────────────────────────────────────────────────────────────────────
# The TRUE tier — positions known by construction
# ─────────────────────────────────────────────────────────────────────────────

_STAFF_BBOX = re.compile(
    r'<g id="bbox-[^"]*" class="staff bounding-box">\s*'
    r'<rect x="([-\d.]+)" y="([-\d.]+)" height="([-\d.]+)" width="([-\d.]+)"')


def _musicxml_text(path: Path) -> str:
    """The score XML, whether the file is `.musicxml` or a zipped `.mxl`."""
    if path.suffix.lower() != ".mxl":
        return path.read_text()
    import zipfile
    with zipfile.ZipFile(path) as z:
        names = [n for n in z.namelist()
                 if n.endswith(".xml") and not n.startswith("META-INF")]
        names.sort(key=lambda n: -z.getinfo(n).file_size)
        return z.read(names[0]).decode("utf-8", "replace")


def _render(musicxml_text: str) -> List[str]:
    import verovio  # type: ignore
    from tools.omr.page_truth import VEROVIO_OPTIONS
    tk = verovio.toolkit()
    tk.setOptions(dict(VEROVIO_OPTIONS))
    if not tk.loadData(musicxml_text):
        raise RuntimeError("verovio could not load the score")
    return [tk.renderToSVG(i + 1) for i in range(tk.getPageCount())]


def entries_from_render(musicxml: Path, *, publisher: str,
                        max_pages: int = 2,
                        edition_path: Optional[str] = None,
                        work_id: Optional[str] = None) -> Iterator[Entry]:
    """Positions known BY CONSTRUCTION, from a Verovio render.

    ⚠️⚠️ **THIS IS THE TIER THAT IS NOT CIRCULAR**, and it is the only reason
    the store can say anything about the MUSIC rather than about our reader.
    Everything in the OBSERVED tier is labelled by the detector, so a
    separation measured there is partly the detector agreeing with itself.
    Here the label is what the renderer was ASKED to draw and the position is
    where it drew it; neither passes through a classifier.

    ⚠️ `TRUE_TIER_CAVEAT` applies: a PAGE truth is not an ENCODING truth.

    ⚠️ The staff-relative frame comes from Verovio's own `staff` bounding box,
    whose height spans the five printed lines -- so `half_space = height / 8`
    and the origin is the top line, the SAME convention as
    `Q.NOTEHEAD_STAFF_POSITION`.  That equality is not assumed: the probe
    checks it by landing a whole rest where a whole rest belongs.
    """
    from tools.omr import page_truth as _pt

    for pi, svg in enumerate(_render(_musicxml_text(Path(musicxml)))):
        if pi >= max_pages:
            break
        units_per_css, _w, _h = _pt._scale_to_css_px(svg)
        k = 1.0 / units_per_css
        m = _pt._PAGE_MARGIN_RE.search(svg)
        mx, my = (float(m.group(1)) * k, float(m.group(2)) * k) if m \
            else (0.0, 0.0)
        staves = sorted((float(y) * k + my, float(h) * k)
                        for _x, y, h, _w2 in _STAFF_BBOX.findall(svg))
        if not staves:
            continue
        boxed, _glyphs = _pt.symbols_in_svg(svg, 1.0)
        for s in boxed:
            yc = s["y"] + s["h"] / 2.0
            # The staff whose band contains the mark, else the nearest.  A mark
            # ABOVE its staff (a dynamic, a ledger note) is normal, so
            # "contains" cannot be the only rule.
            bi = bd = None
            for si, (sy, sh) in enumerate(staves):
                if sh <= 0:
                    continue
                dist = 0.0 if sy <= yc <= sy + sh \
                    else min(abs(yc - sy), abs(yc - (sy + sh)))
                if bd is None or dist < bd:
                    bi, bd = si, dist
            if bi is None:
                continue
            sy, sh = staves[bi]
            half_space = sh / 8.0
            if half_space <= 0:
                continue
            space = half_space * 2.0
            yield Entry(
                tier=TIER_TRUE, publisher=publisher,
                memberships=(Membership(KIND_DRAWN_AS, s["class"], "verovio"),),
                staff_position=(yc - sy) / half_space,
                width_spaces=round(s["w"] / space, 3),
                height_spaces=round(s["h"] / space, 3),
                edition_path=edition_path, work_id=work_id,
                page=pi, staff=bi,
                source_quantity="page_truth:%s" % s.get("family", "?"))


# ─────────────────────────────────────────────────────────────────────────────
# Publisher — the conditioning variable
# ─────────────────────────────────────────────────────────────────────────────

def catalog_path() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "score-library" \
        / "catalog.json"


def edition_facts(edition_path: str) -> Dict[str, Any]:
    """Publisher, work and scan type for an edition, from the COMMITTED catalog.

    ⚠️ `source_kind` matters here exactly as it does everywhere else in this
    repo.  The publisher comes from IMSLP's own work page through the catalog,
    not from reading the plate, so it does not fall silent when the raster is
    bad -- which is the property that makes it usable as a conditioning
    variable rather than as another OMR output.
    """
    try:
        cat = json.loads(catalog_path().read_text())
    except (OSError, ValueError):
        return {}
    for e in cat.get("entries", ()):
        if e.get("kind") == "edition" and e.get("path") == edition_path:
            return {k: e.get(k) for k in
                    ("path", "work_id", "publisher", "image_type", "pages",
                     "imslp_id", "variant", "composer")}
    return {}


def edition_for_pdf(pdf_path: Any) -> Dict[str, Any]:
    """The catalog's facts for a PDF on disk, matched on its BASENAME.

    ⚠️ THE BASENAME AND NOT THE FULL PATH, because the store is machine-local
    and gitignored while the catalog's `path` is repo-relative, so the two only
    ever agree on the tail.  A library filename carries its own IMSLP id
    (`...--imslp984073.pdf`), which is what makes the basename unique.

    ⚠️ ABSTAINS rather than guessing.  A PDF the store does not hold returns
    `{}`, and every caller treats that as *no identity was read* rather than
    as a default -- the `OMR_WORK_ID` escape exists for exactly that case, and
    its recorded trap is that it takes the score LIBRARY's id
    (`beethoven--symphony-5`), never the dossier's (`beethoven-sym5-mvt1`).
    """
    if not pdf_path:
        return {}
    name = Path(str(pdf_path)).name
    try:
        cat = json.loads(catalog_path().read_text())
    except (OSError, ValueError):
        return {}
    for e in cat.get("entries", ()):
        if e.get("kind") == "edition" \
                and Path(e.get("path", "")).name == name:
            return {k: e.get(k) for k in
                    ("path", "work_id", "publisher", "image_type", "pages",
                     "imslp_id", "variant", "composer")}
    return {}


#: ⚠️⚠️ **A LEGACY RECORD DOES NOT NAME THE PDF IT WAS GATHERED FROM.**  Its
#: `provenance` block carries the commit and a dirty flag and nothing about the
#: source, so for records written before `gather_document_identity` the
#: publisher can only be supplied from OUTSIDE.  That is a real gap, and this
#: table is the honest patch for it rather than a design: every line is a
#: hand-made assertion about which plate a file came from, kept small and named
#: so nobody mistakes it for something derived.
LEGACY_RECORD_EDITIONS = {
    "beethoven5-p1-p4.record.json":
        "editions/beethoven/symphony-5-op67/"
        "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--"
        "imslp984073.pdf",
    "brahms1-breitkopf-p0-p3.record.json":
        "editions/brahms/symphony-1-op68/"
        "brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf",
}


def publisher_label(publisher: Optional[str]) -> str:
    """A short, stable key for a publisher string.

    The catalog's string is a full imprint (*"Henry Litolff's Verlag,
    Braunschweig, 1870, plate 2769"*), which is right to keep and wrong to key
    on -- two plates of one house must land in one bucket set.
    """
    if not publisher:
        return "unknown"
    p = publisher.lower()
    for k, v in (("litolff", "litolff"), ("breitkopf", "breitkopf"),
                 ("peters", "peters"), ("eulenburg", "eulenburg"),
                 ("simrock", "simrock"), ("bruckner", "bruckneraga"),
                 ("philharmonia", "philharmonia"), ("kalmus", "kalmus")):
        if k in p:
            return v
    return re.sub(r"[^a-z0-9]+", "-", p.split(",")[0]).strip("-")[:24] \
        or "unknown"


def identity_of_record(path: Path) -> Dict[str, Any]:
    """The document identity a record names, or the legacy fallback.

    Looks first for the `document_identity` observation `gather_document_
    identity` files; falls back to `LEGACY_RECORD_EDITIONS` and SAYS which it
    used, so a consumer can tell a derived fact from a hand-made one.
    """
    for o in stream_observations(path):
        if o.get("quantity") == "document_identity":
            d = o.get("detail") or {}
            return {"from": "record", "edition_path": d.get("edition_path"),
                    "publisher": d.get("publisher"),
                    "work_id": d.get("work_id"),
                    "image_type": d.get("image_type")}
        if o.get("quantity") in (NAMED_QUANTITY, UNNAMED_QUANTITY):
            break   # identity is filed at the head of the gather; we are past it
    ed = LEGACY_RECORD_EDITIONS.get(Path(path).name)
    if not ed:
        return {"from": "none"}
    f = edition_facts(ed)
    return {"from": "legacy-table", "edition_path": ed,
            "publisher": f.get("publisher"), "work_id": f.get("work_id"),
            "image_type": f.get("image_type")}


def publisher_of_record(path: Path) -> str:
    return publisher_label(identity_of_record(path).get("publisher"))


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def _accumulate(paths: Sequence[str], store: EntryStore) -> None:
    for p in paths:
        path = Path(p)
        ident = identity_of_record(path)
        pub = publisher_label(ident.get("publisher"))
        n = store.extend(entries_from_record(
            path, publisher=pub, edition_path=ident.get("edition_path"),
            work_id=ident.get("work_id"), image_type=ident.get("image_type")))
        store.sources.append({"record": path.name, "publisher": pub,
                              "identity_from": ident.get("from"),
                              "entries": n, "bytes": path.stat().st_size})
        print("  %-40s %-11s %7d entries  (identity from %s)"
              % (path.name, pub, n, ident.get("from")))


def main(argv: Optional[Sequence[str]] = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("records", nargs="*", help="staged record JSON files")
    ap.add_argument("--render", action="append", default=[],
                    help="a MusicXML/.mxl to add at the TRUE tier")
    ap.add_argument("--render-publisher", default="rendered")
    ap.add_argument("--render-pages", type=int, default=2)
    ap.add_argument("--out", help="write the base store (JSONL) here")
    ap.add_argument("--load", help="read an existing base store")
    ap.add_argument("--vbucket-spaces", type=float,
                    default=DEFAULT_VBUCKET_SPACES)
    ap.add_argument("--hbuckets", type=int, default=DEFAULT_HBUCKETS)
    ap.add_argument("--ask", type=float,
                    help="staff position (steps from the top line) to query")
    ap.add_argument("--tier", default=TIER_OBSERVED, choices=list(TIERS))
    ap.add_argument("--publisher")
    ap.add_argument("--height-spaces", type=float)
    ap.add_argument("--bar-fraction", type=float)
    args = ap.parse_args(argv)

    store = EntryStore.read(Path(args.load)) if args.load else EntryStore()
    if args.records:
        print("ACCUMULATING (observed)")
        _accumulate(args.records, store)
    for r in args.render:
        n = store.extend(entries_from_render(
            Path(r), publisher=args.render_publisher,
            max_pages=args.render_pages,
            # ⚠️ The render's own file IS its edition, so the "how many
            # distinct sources agree here" count means the same thing in both
            # tiers.  Leaving it None made the TRUE rows report `editions: 0`,
            # which reads as "nothing contributed" rather than "this is a
            # render".
            edition_path=str(r)))
        store.sources.append({"render": Path(r).name, "entries": n,
                              "publisher": args.render_publisher})
        print("  %-40s %-11s %7d entries  (TRUE tier)"
              % (Path(r).name, args.render_publisher, n))

    s = store.summary()
    print("\nBASE STORE: %d entries, %d distinct names" %
          (s["entries"], s["distinct_names"]))
    print("  per tier      : %s" % s["per_tier"])
    print("  per publisher : %s" % s["per_publisher"])
    print("  unpositioned  : %d (counted, never dropped)" % s["unpositioned"])
    print("  no membership : %d   several memberships: %d"
          % (s["entries_with_no_membership"],
             s["entries_with_several_memberships"]))
    if s["entries"] == 0:
        print("DEAD: the store is empty. Nothing was accumulated.")
        return 2

    if args.out:
        n = store.write(Path(args.out))
        print("  wrote %s (%.2f MB, %.0f bytes/entry)"
              % (args.out, n / 1e6, n / max(1, s["entries"])))

    idx = PositionIndex(store, vbucket_spaces=args.vbucket_spaces,
                        hbuckets=args.hbuckets)
    print("\nDERIVED INDEX (rebuildable; not the store): %s" % idx.summary())

    if args.ask is not None:
        r = idx.ask(args.ask, tier=args.tier, publisher=args.publisher,
                    height_spaces=args.height_spaces,
                    bar_fraction=args.bar_fraction)
        print("\nQUERY %s" % json.dumps(r["query"]))
        print("  %d observations here, %d candidate names"
              % (r["observations_here"], r["n_candidates"]))
        print("  %-26s %7s %7s %9s %9s %5s"
              % ("name", "n", "share", "mean_h", "sd_h", "eds"))
        for c in r["candidates"][:12]:
            print("    %-24s %7d %7.3f %9s %9s %5d"
                  % (c["name"], c["count"], c["share_of_this_position"],
                     c.get("mean_height_spaces"), c.get("sd_height_spaces"),
                     c["editions"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
