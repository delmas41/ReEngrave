"""Which orchestra is this? — instrument identity from POSITION, not from text.

Score order is one of the strongest conventions in music printing: instruments
appear top to bottom in family order — woodwind, brass, percussion, keyboard and
harp, then strings — and never out of it. So "which instrumentation is this
page?" is not a classification problem. It is a monotone alignment of the staves
you can see against a small library of standard layouts, which is the same
machinery `slots.py` already uses to align one system against another; only the
reference differs. There, the reference is the largest system observed; here it
is a layout the printing tradition supplies.

## What this is for

Two things, and the second is why it exists.

**Unlabelled scores.** A scan with no text layer and no margin reading has no
instrument identity at all today, so the clef, transposition and register
priors that identity unlocks are unavailable. Position and bracket structure can
supply a plausible assignment on their own.

**Ambiguous labels.** `Tp.` is Timpani in the German and Italian tradition and
Trumpet in the English one, and no lexicon can settle that — but POSITION can. A
staff labelled `Tp.` directly below one labelled `Tr.` is the timpani, because
trumpets do not follow trumpets; the same label above the horns would be
trumpets. `tools/omr/instruments.py` currently resolves this by picking the
commoner reading for the corpus, with a comment saying a score-order prior
should settle it. This is that prior.

## What it is NOT

It is not a way to invent parts. A layout fit is a HYPOTHESIS about a page, and
the fit is only offered when one layout beats the next by a margin — see
`MIN_MARGIN_PER_STAFF`. A page whose staves fit two traditions equally well gets
no answer, which is the honest outcome and the same abstain-when-blind rule the
geometric readers follow.

It also does not know about divisi. A layout is a list of PARTS as they are
normally printed; a page that splits its first violins across two staves has one
more staff than the layout has parts, and the alignment absorbs that as an
insertion rather than pretending the extra staff is a different instrument.
"""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Sequence
from typing import Any

from .instruments import Instrument, lookup


# ── Scoring ─────────────────────────────────────────────────────────────────
# The label terms mirror `slots.py`, deliberately: a label agreement is strong
# evidence and a label CONFLICT is the only hard negative available, because two
# differently-named instruments are certainly not the same part.
SCORE_LABEL_MATCH = 6.0
SCORE_LABEL_CONFLICT = -8.0
# A clef is weaker evidence than a name but much cheaper to come by, and on the
# prints this exists for it is often the only evidence there is: a bassoon staff
# in bass clef and a viola staff in alto are the two anchors that hold the
# middle of an orchestral system in place.
SCORE_CLEF_MATCH = 1.5
SCORE_CLEF_CONFLICT = -1.5
# ...except against a TREBLE read, which is worth much less as evidence
# AGAINST a part. Reading everything as treble is the documented failure mode of
# clef detection on degraded orchestral prints — it is what the positional
# default falls back to and what the detector produces when it is guessing — so
# "this staff reads treble" is weak evidence that a part is not the viola, while
# "this staff reads alto" is strong evidence that it is not the first violins.
# Measured on Beethoven 5 p.15, where the viola and cello staves are both
# misread as treble: with a symmetric penalty the prior reads the string section
# as three violin staves, because that is what its evidence says.
SCORE_TREBLE_CONFLICT = -0.3
SCORE_POSITION_WEIGHT = 1.0
# Skipping a layout part: the instrument is not on this page. Cheap, because
# real scores omit parts constantly — a Classical symphony without trombones is
# not a different tradition.
GAP_LAYOUT = -0.8
# Skipping an OBSERVED staff: this page has a staff the layout has no part for.
# Dearer than the above, because it is the failure that matters — a layout small
# enough to skip half the page would otherwise win by having nothing to disagree
# with.
GAP_STAFF = -2.0
# A part CONTINUED onto another staff: two horns on two staves, a harp's two
# staves, first violins divided across three. This is not a gap and must not be
# priced like one — it is how orchestral scores are actually printed, and
# without it every layout is wrong about a page the moment one part takes two
# staves. Measured on La Mer p.25, which prints 21 staves for 17 parts: without
# continuation the alignment slips by one at the horns and never recovers, and
# 8 of 21 staves come out right; with it, 21 of 21.
EXTEND_PENALTY = -0.3
# The mirror of it: several consecutive PARTS printed on ONE staff. Off unless
# the caller asks (`allow_merge`), because the layouts in this module are
# already written one entry per printed STAFF — a Classical pair of flutes IS
# one entry — so allowing it here would count the same convention twice. It is
# for callers aligning against a WORK's parts, where condensation is the norm:
# Beethoven 5 is written for 18 parts and printed 11 staves to a system.
#
# Two prices, and the difference is what makes the move usable. Condensation
# almost always joins parts of the SAME instrument (Flauti, Oboi), so that is
# cheap; joining different instruments is the "Violoncello e Basso" case, real
# but rarer. Measured on Beethoven 5 p.2: with one price for both, the aligner
# drops the second violin rather than condensing cello with bass, and the whole
# string section slips by one.
MERGE_SAME_PENALTY = -0.3
MERGE_OTHER_PENALTY = -1.5
# The mirror of MERGE_SAME_PENALTY, and the actual bug it was hiding. That price
# is cheap because numbered parts of one instrument share a staff — Flauti 1 and
# 2, Oboi 1 and 2. That is true of the winds and the brass and FALSE of the
# violins: first and second violins are separate desks and take separate staves
# in every tradition in `LAYOUTS` below.
#
# It bites because canonicalisation collapses "Violin 1" and "Violin 2" to one
# name, so the aligner sees a cheap same-name pair where the score has none.
# Measured on Beethoven 5 p.2 — 18 parts printed on 11 staves, so 7 merges are
# required, and the work offers exactly 7 same-name merges ONLY IF the violins
# count. The aligner duly condenses the two violin sections onto one staff, and
# every string slot below shifts by one: Violino II reads as Viola, Viola as
# Violoncello, the cello-and-bass staff as Contrabass. Excluding the violins
# takes that page from 8 of 11 slots correct to 10, with the Pastoral unchanged.
#
# Naming the cello-and-bass condensation as a cheap PAIR was tried at the same
# time — it is the obvious partner to this, since "Violoncello e Basso" is a
# printed convention — and it is NOT here because it was measured and lost:
# alone it takes Beethoven 5 p.2 to 9 of 11 and the Pastoral DOWN from 9 to 7,
# because a cheap cross-instrument merge lets the aligner condense whenever it is
# short of staves rather than only where the engraving does. Which parts share a
# staff is a fact about the page, and a flat price cannot express it.
NEVER_CONDENSED: frozenset[str] = frozenset({"Violin"})
# The other half of that fact is a trap, and it has now been measured twice.
#
# "Violoncello e Basso" IS a printed convention, and Beethoven 5 p.2 needs it:
# the page makes its two condensations below the trumpets but pairs the VIOLA
# with the cello, and since both are ordinary cross-instrument merges at one
# price the choice falls to the position term, where the wrong pairing wins by
# 0.018. So naming (Cello, Contrabass) as a cheaper conventional pair looks
# exactly right, and it takes p.2 from 10 of 11 to 11 of 11.
#
# It was rejected in an earlier session (the Pastoral 9/10 -> 7/10) and rejected
# AGAIN here, after a specific argument that the ground had moved: merging is now
# offered only inside a span short of staves (`align_to_layout_pinned`), so the
# reasoning went, the price can no longer run loose. That argument is wrong, and
# the way it is wrong is the thing to remember:
#
#   **The span bounds HOW MANY condensations happen. It does not bound WHICH.**
#
# The Pastoral's last span needs exactly one, and the cheap pair moves it from
# the horns to the cello and bass. The horns then have to stretch across two
# staves to keep the count, and every string staff below shifts by one: measured
# under the pipeline's own label conditions, 10 of 10 -> 5 of 10, and because the
# tail is now anchored those wrong parts reach the clefs — the clef corpus went
# 69/69 -> 65/69, the Pastoral 20/20 -> 16/20.
#
# It hid from `eval_join` because that harness's realistic arm supplies SIX
# labels and the pipeline reads FIVE; the sixth is `Violino I`, which pins the
# strings and conceals the whole failure. A fifth arm now covers the real
# condition.
#
# Which parts share a staff remains a fact about the PAGE. A price is a fact
# about the WORK, and no price has yet been found that can express it.





# Confidence is NOT the score margin between the best two layouts. That was the
# first design and it was wrong: measured on two hand-read pages, the natural
# margin between neighbouring traditions is about 0.05 per staff — Beethoven 5
# p.15 fits `classical-condensed` at 1.000 and `classical-shared-bass` at 0.952
# while being 12 of 12 correct — so any threshold that rejects a coin-flip also
# rejects a page that was read perfectly.
#
# What separates a confident staff from a doubtful one is not which layout won
# but whether the plausible layouts AGREE about that staff. The strings at the
# bottom of an orchestral system are the same in every tradition; the middle of
# the woodwind is where traditions differ. So every layout within
# `SCORE_BAND_PER_STAFF` of the best votes, weighted by its score, and a staff
# is named only where the winner carries `MIN_AGREEMENT` of the vote.
SCORE_BAND_PER_STAFF = 0.15
# Swept on two hand-read pages (Beethoven 5 p.15 system 0, 12 staves; La Mer
# p.25, 21 staves), scoring PRECISION — a wrong instrument is worse than no
# instrument, because it carries a wrong clef and a wrong transposition with it:
#
#   agreement   with clefs                  position only
#   0.60        29 named, 27 correct        18 named, 13 correct
#   0.75        23 named, 23 correct        12 named, 11 correct
#   0.80        22 named, 22 correct         5 named,  4 correct  <- cliff
#
# 0.75 is the knee: everything it names on either page is right. At 0.80 the
# position-only reading of the Beethoven page collapses from 7 staves to none,
# which is the kind of edge a single-corpus tuning would have walked straight
# off — see the clef-threshold lesson in benchmarks/omr-clef-geometry.
MIN_AGREEMENT = 0.75
# ...and only when the best layout itself scores this well per staff, so a page
# that matches nothing does not win by default.
MIN_SCORE_PER_STAFF = 0.5
# Fewer staves than this is not an ensemble whose order says anything.
MIN_STAVES = 3


@dataclass(frozen=True)
class ScoreLayout:
    """One standard instrumentation, in printed score order.

    `parts` are canonical `instruments.Instrument` names, one per STAFF as the
    tradition normally prints it — so a Classical score's pair of flutes is one
    entry, because they share a staff.
    """

    name: str
    parts: tuple[str, ...]
    note: str = ""

    @property
    def size(self) -> int:
        return len(self.parts)


# The library. Small on purpose: these are the layouts that account for most of
# the printed repertoire, and a layout that never wins is a layout that only
# dilutes the margin test.
#
# Order within each is the printed one, which is not always the one a modern
# editor would choose — see `french-large`, where the piccolo sits BELOW the
# flutes rather than above them. That is not an error to be normalised away: it
# is the convention Debussy's publisher used, and a page set that way should fit
# a layout set that way.
LAYOUTS: tuple[ScoreLayout, ...] = (
    ScoreLayout(
        "piano",
        ("Piano", "Piano"),
        "Grand staff. Two staves, one part.",
    ),
    ScoreLayout(
        "string-quartet",
        ("Violin", "Violin", "Viola", "Cello"),
    ),
    ScoreLayout(
        "piano-trio",
        ("Violin", "Cello", "Piano", "Piano"),
    ),
    ScoreLayout(
        "classical-condensed",
        ("Flute", "Oboe", "Clarinet", "Bassoon", "Horn", "Trumpet", "Timpani",
         "Violin", "Violin", "Viola", "Cello", "Contrabass"),
        "Haydn / Mozart / early Beethoven as printed in pocket score: each wind "
        "pair condensed onto one staff, cellos and basses separate.",
    ),
    ScoreLayout(
        "classical-shared-bass",
        ("Flute", "Oboe", "Clarinet", "Bassoon", "Horn", "Trumpet", "Timpani",
         "Violin", "Violin", "Viola", "Cello"),
        "As above, with cellos and basses sharing the bottom staff — the older "
        "'Bassi' convention.",
    ),
    ScoreLayout(
        "romantic",
        ("Piccolo", "Flute", "Oboe", "Clarinet", "Bassoon",
         "Horn", "Trumpet", "Trombone", "Tuba", "Timpani", "Percussion",
         "Violin", "Violin", "Viola", "Cello", "Contrabass"),
    ),
    ScoreLayout(
        "late-romantic-large",
        ("Piccolo", "Flute", "Oboe", "English horn", "Clarinet", "Bass clarinet",
         "Bassoon", "Contrabassoon",
         "Horn", "Trumpet", "Trombone", "Tuba",
         "Timpani", "Percussion", "Harp",
         "Violin", "Violin", "Viola", "Cello", "Contrabass"),
    ),
    ScoreLayout(
        "french-large",
        ("Flute", "Piccolo", "Oboe", "English horn", "Clarinet", "Bassoon",
         "Horn", "Trumpet", "Tuba", "Timpani", "Percussion", "Harp",
         "Violin", "Violin", "Viola", "Cello", "Contrabass"),
        "Debussy / Ravel house style: petites flûtes printed BELOW the grandes, "
        "cor anglais between oboes and clarinets, harp above the strings.",
    ),
    ScoreLayout(
        "wind-band",
        ("Piccolo", "Flute", "Oboe", "Clarinet", "Bass clarinet", "Bassoon",
         "Saxophone", "Horn", "Trumpet", "Trombone", "Tuba", "Timpani",
         "Percussion"),
    ),
    ScoreLayout(
        "choral-satb",
        ("Soprano", "Alto", "Tenor", "Bass voice"),
    ),
)


@dataclass(frozen=True)
class LayoutFit:
    """What the plausible layouts say this system's staves are.

    `assignment` is the agreed reading, one entry per staff top to bottom, with
    None where the layouts within the score band did not agree. `agreement` is
    the vote fraction behind each entry, so a caller can be stricter than
    `MIN_AGREEMENT` without re-running anything.

    `support` is the whole ballot — every name any voter put at that staff, with
    its share — because being stricter is not the only thing a caller may want.
    A caller asking a NARROWER question than "what is this staff" can be
    answered by a ballot that failed to answer the wide one: the layouts can
    split 0.64 Contrabass / 0.36 Cello, name the staff nothing, and still be
    unanimous that it is not a singer. `agreement` cannot say that and
    `assignment` throws it away. See `resolve_ambiguous_label`.
    """

    layout: ScoreLayout             # the best-scoring layout, i.e. the tradition
    assignment: tuple[str | None, ...]
    agreement: tuple[float, ...]
    score_per_staff: float
    considered: tuple[str, ...]     # every layout that got a vote
    support: tuple[dict[str, float], ...] = ()

    def instrument_for(self, ordinal: int) -> str | None:
        """The instrument agreed for the `ordinal`-th staff of the system."""
        if 0 <= ordinal < len(self.assignment):
            return self.assignment[ordinal]
        return None

    def support_for(self, ordinal: int) -> dict[str, float]:
        """`{instrument name: vote share}` at the `ordinal`-th staff."""
        if 0 <= ordinal < len(self.support):
            return self.support[ordinal]
        return {}

    @property
    def n_named(self) -> int:
        return sum(1 for a in self.assignment if a is not None)


def _default_clef(instrument_name: str) -> str | None:
    match = lookup(instrument_name)
    return match.instrument.default_clef if match else None


def _pair_score(
    label: str | None,
    clef: str | None,
    staff_position: float,
    part: str,
    part_position: float,
    part_clef: str | None,
) -> float:
    score = SCORE_POSITION_WEIGHT * (1.0 - abs(staff_position - part_position))
    if label is not None:
        score += SCORE_LABEL_MATCH if label == part else SCORE_LABEL_CONFLICT
    if clef is not None and part_clef is not None:
        if clef == part_clef:
            score += SCORE_CLEF_MATCH
        else:
            score += SCORE_TREBLE_CONFLICT if clef == "treble" else SCORE_CLEF_CONFLICT
    return score


def align_to_layout(
    layout: ScoreLayout,
    n_staves: int,
    labels: dict[int, str] | None = None,
    clefs: dict[int, str] | None = None,
    part_clefs: list[str | None] | None = None,
    allow_merge: bool = False,
    return_indices: bool = False,
    staff_positions: list[float] | None = None,
    part_positions: list[float] | None = None,
    absorbed: dict[int, list[int]] | None = None,
    balance: bool = False,
) -> tuple[float, list[str | None] | list[int | None]]:
    """Align `n_staves` observed staves against one layout.

    Needleman-Wunsch with three moves, and the third is the one that makes this
    work on real scores:

    * **skip a part** — the instrument is absent from this page;
    * **skip a staff** — this staff has no part in the layout at all;
    * **continue a part** — this staff is another staff of the SAME part, which
      is how two horns, a harp, or divided violins are printed;
    * **merge parts** (`allow_merge`) — this staff carries SEVERAL consecutive
      parts, which is how a printed score condenses Flauti 1 and 2 onto one
      staff. See `MERGE_SAME_PENALTY`.

    `part_clefs` overrides the clef expected of each part. A caller aligning
    against a standard layout leaves it None and gets each instrument's own
    convention; one aligning against a WORK passes the clefs that work actually
    prints.

    `absorbed`, when given, is filled with `{staff: [every part it took]}`. The
    returned assignment cannot carry that — a staff that condenses two parts gets
    ONE index, the lower — so the other part looks unassigned to any caller
    counting what is left. That is not cosmetic: `dossier._determined_tail` asks
    exactly that question, and without this the Pastoral's second horn reads as
    still available, and its five string staves look like five staves chasing six
    parts when the count in fact closes.

    `staff_positions` and `part_positions` override where each staff and part
    sits on its axis, normally 0 to 1 across whatever was passed in. A caller
    solving a SLICE of a page must pass the positions the whole page gives them
    — see `align_to_layout_pinned`, where renormalising within a span moves the
    two sides relative to each other and flips merges that are already close.

    Order is never violated, which is the whole content of the score-order
    prior. Returns `(total score, one part name or None per staff)`.
    """
    labels = labels or {}
    clefs = clefs or {}
    m, n = n_staves, layout.size
    if m == 0 or n == 0:
        return 0.0, [None] * m

    s_denom = max(1, m - 1)
    p_denom = max(1, n - 1)
    if staff_positions is None:
        staff_positions = [i / s_denom for i in range(m)]
    if part_positions is None:
        part_positions = [j / p_denom for j in range(n)]
    if part_clefs is None:
        part_clefs = [_default_clef(p) for p in layout.parts]

    # ── EQUAL-COUNT BALANCE (opt-in, `balance=True`) ───────────────────────
    # When the reference is THIS WORK'S OWN ROSTER and the page prints exactly
    # as many staves as the roster has entries, THE ONLY ORDER-PRESERVING
    # BIJECTION IS THE IDENTITY MAP. A skip must be paid for by a continuation
    # elsewhere, and both are wrong by construction — so the DP's freedom to do
    # it is freedom to be wrong. It uses that freedom: 7 of the 14 errors on
    # the page-1-roster arm sit in equal-count systems (Brahms 14 v 14, Dvorak
    # 15 v 15), and pinning the diagonal fixes exactly those 7 (0.903 -> 0.952).
    #
    # ⚠️⚠️ IT IS OPT-IN, NOT A GLOBAL FLAG, AND THAT SCOPING IS MEASURED. On a
    # GENERIC LAYOUT reference the same rule COSTS accuracy: 137 -> 135 correct
    # staves on the 20-row gate, because a 14-staff page matching a 14-part
    # layout is a COINCIDENCE of counts, not evidence of an identity map. Only
    # a roster — the work's own printed lineup — makes m == n mean what the
    # argument needs it to mean. A first implementation gated this on an env
    # flag for every caller and would have shipped that regression.
    #
    # ⚠️ WHAT IT CANNOT SEE: a page that DROPS one staff and ADDS another keeps
    # the counts equal while the map is emphatically NOT the identity. No row in
    # the 20-row gate has that shape, so this rule's safety there is UNTESTED
    # and must not be claimed — `R1` is the guard for it.
    # `return_indices`, `allow_merge` and `absorbed` callers are excluded
    # outright rather than reasoned about.
    if (balance and m == n and not allow_merge and not return_indices
            and absorbed is None):
        total = sum(
            _pair_score(labels.get(i), clefs.get(i), staff_positions[i],
                        layout.parts[i], part_positions[i], part_clefs[i])
            for i in range(m))
        return total, list(layout.parts)

    NEG = float("-inf")
    # dp[i][j]  — first i staves against first j parts, staff i free to be
    #             matched or not.
    # ext[i][j] — the same, but staff i IS matched to part j, which is what a
    #             continuation has to build on.
    dp = [[NEG] * (n + 1) for _ in range(m + 1)]
    ext = [[NEG] * (n + 1) for _ in range(m + 1)]
    dp_back: list[list[str | None]] = [[None] * (n + 1) for _ in range(m + 1)]
    ext_back: list[list[str | None]] = [[None] * (n + 1) for _ in range(m + 1)]

    dp[0][0] = 0.0
    for j in range(1, n + 1):
        dp[0][j] = dp[0][j - 1] + GAP_LAYOUT
        dp_back[0][j] = "skip_part"
    for i in range(1, m + 1):
        dp[i][0] = dp[i - 1][0] + GAP_STAFF
        dp_back[i][0] = "skip_staff"

    for i in range(1, m + 1):
        for j in range(1, n + 1):
            pair = _pair_score(
                labels.get(i - 1), clefs.get(i - 1), staff_positions[i - 1],
                layout.parts[j - 1], part_positions[j - 1], part_clefs[j - 1],
            )
            open_ = dp[i - 1][j - 1] + pair
            cont = ext[i - 1][j] + pair + EXTEND_PENALTY
            if allow_merge and j >= 2:
                same = (layout.parts[j - 1] == layout.parts[j - 2]
                        and layout.parts[j - 1] not in NEVER_CONDENSED)
                merge = ext[i][j - 1] + pair + (
                    MERGE_SAME_PENALTY if same else MERGE_OTHER_PENALTY)
            else:
                merge = float("-inf")
            best_ext = max(open_, cont, merge)
            ext[i][j] = best_ext
            ext_back[i][j] = ("open" if best_ext == open_
                              else "continue" if best_ext == cont else "merge")

            skip_part = dp[i][j - 1] + GAP_LAYOUT
            skip_staff = dp[i - 1][j] + GAP_STAFF
            best = max(ext[i][j], skip_part, skip_staff)
            dp[i][j] = best
            dp_back[i][j] = ("match" if best == ext[i][j]
                             else "skip_part" if best == skip_part else "skip_staff")

    out: list[Any] = [None] * m
    i, j = m, n
    while i > 0 or j > 0:
        if i == 0:
            j -= 1
            continue
        if j == 0:
            i -= 1
            continue
        move = dp_back[i][j]
        if move == "match":
            # Walk back through however many staves this part absorbed.
            # Walk back through however many staves this part absorbed, and
            # however many parts this staff absorbed.
            while True:
                out[i - 1] = (j - 1) if return_indices else layout.parts[j - 1]
                if absorbed is not None:
                    absorbed.setdefault(i - 1, []).append(j - 1)
                step = ext_back[i][j]
                if step == "continue":
                    i -= 1
                elif step == "merge":
                    j -= 1
                else:
                    i -= 1
                    j -= 1
                    break
        elif move == "skip_part":
            j -= 1
        else:
            i -= 1
    return dp[m][n], out


def fit_layouts(
    n_staves: int,
    labels: dict[int, str] | None = None,
    clefs: dict[int, str] | None = None,
    layouts: tuple[ScoreLayout, ...] = LAYOUTS,
    balance: bool = False,
) -> LayoutFit | None:
    """What this system's staves are, by position — or None if it cannot say.

    `labels` and `clefs` are keyed by ORDINAL within the system — position top
    to bottom — not by `staff_index`, because that is what score order is about.
    Both are optional. Clefs matter far more than their weight suggests: on
    La Mer p.25 they take the reading from 8 of 21 staves right to 18 of 21, and
    they are what picks the French tradition (piccolo below the flutes) over the
    German one. A bassoon in bass clef and a viola in alto are the anchors that
    hold the middle of a system in place.
    """
    n = n_staves
    if n < MIN_STAVES:
        return None
    scored = []
    for layout in layouts:
        total, assignment = align_to_layout(layout, n, labels, clefs,
                                            balance=balance)
        scored.append((total / n, layout, assignment))
    scored.sort(key=lambda t: -t[0])

    best_score, best_layout, _ = scored[0]
    if best_score < MIN_SCORE_PER_STAFF:
        return None

    voters = [t for t in scored if t[0] >= best_score - SCORE_BAND_PER_STAFF]
    # Weight each voter by how far above the band's floor it sits, so a layout
    # scraping in at the edge does not cancel the winner.
    floor = best_score - SCORE_BAND_PER_STAFF
    weights = [max(1e-6, score - floor) for score, _, _ in voters]
    total_weight = sum(weights)

    assignment: list[str | None] = []
    agreement: list[float] = []
    support: list[dict[str, float]] = []
    for i in range(n):
        tally: dict[str, float] = {}
        for (_, _, a), w in zip(voters, weights):
            name = a[i]
            if name is not None:
                tally[name] = tally.get(name, 0.0) + w
        support.append({name: w / total_weight for name, w in tally.items()})
        if not tally:
            assignment.append(None)
            agreement.append(0.0)
            continue
        winner, weight = max(tally.items(), key=lambda kv: kv[1])
        share = weight / total_weight
        assignment.append(winner if share >= MIN_AGREEMENT else None)
        agreement.append(share)

    return LayoutFit(
        layout=best_layout,
        assignment=tuple(assignment),
        agreement=tuple(agreement),
        score_per_staff=best_score,
        considered=tuple(layout.name for _, layout, _ in voters),
        support=tuple(support),
    )


def resolve_ambiguous_label(
    ordinal: int,
    candidates: tuple[Instrument, ...],
    fit: LayoutFit | None,
) -> Instrument | None:
    """Pick between instruments an alias cannot separate, using position.

    `Tp.` is the case this exists for: Timpani in the German and Italian
    tradition, Trumpet in the English one. The lexicon cannot know which, and
    picking the commoner reading is a guess about the whole corpus made once.
    The page itself has the answer — a staff below the trumpets is the timpani —
    and that is what the layout fit reads.

    Returns None when the fit does not cover this staff, so the caller keeps
    whatever it would have done anyway. This never invents a reading; it only
    chooses among ones already on the table.

    ⚠️ **The agreed reading is the answer to a wider question than this one, and
    asking only for it is what kept `Basso` dormant.** Beethoven 5 p.1 prints
    `Basso` at the foot of a twelve-staff system; the candidates are Bass voice
    and Contrabass; and the layouts vote 0.64 Contrabass / 0.36 Cello — which is
    below `MIN_AGREEMENT`, so `assignment` is None and this used to give up. But
    the twelve-way question "which instrument is this staff" being unsettled
    does not make the two-way question "voice, or contrabass" unsettled: **not
    one voter put a voice there.** So when there is no agreed reading, the
    BALLOT is consulted, and a candidate is chosen only when it is the only one
    of them with any support at all.

    Unanimity among the candidates is the right bar rather than a share
    threshold, because the question is two-way. `MIN_AGREEMENT` is calibrated
    for "which of a dozen instruments", and reusing it here would ask a 2-way
    choice to clear a 12-way bar. A ballot that backs BOTH candidates is a
    genuine disagreement about this very question and still abstains.
    """
    if fit is None or not candidates:
        return None
    proposed = fit.instrument_for(ordinal)
    if proposed is not None:
        for candidate in candidates:
            if candidate.name == proposed:
                return candidate
        # The layouts agreed, and on something the alias does not allow. That is
        # a real disagreement, not a gap — abstain rather than fall through.
        return None

    support = fit.support_for(ordinal)
    backed = [c for c in candidates if support.get(c.name, 0.0) > 0.0]
    return backed[0] if len(backed) == 1 else None


# ── Pinning: the labels know the PRINT's order ──────────────────────────────
# `align_to_layout` is monotone, and monotone is right about score order — the
# families never swap. It is NOT right about a particular engraving. Beethoven 5
# p.48 prints `Timp.` above the three trombones; the work's part list has the
# trombones first, which is the standard order, and this edition is the one that
# deviates (editions commonly do). Having consumed Timpani the aligner cannot go
# back, so the trombone staves come back empty — and they carry the alto, tenor
# and bass clefs the dossier exists to supply, the ones no detector reads.
#
# What knows the print's order is the margin labels. So a labelled staff may PIN
# its part: the alignment then runs only on the spans BETWEEN pins, and two pins
# may sit in either order, which is exactly the transposition the monotone path
# forbids.
#
# **A pin fixes a boundary; it does not consume a run.** That distinction was
# measured, not assumed. Pinning a labelled staff to its instrument's whole run
# of parts costs the Pastoral a staff: `Violino I` labels ONE staff, and a run
# pin hands it both violin parts, so the unlabelled second-violin staff below
# has to start at the viola and the rest of the section shifts down. A label
# says where an instrument BEGINS. How many staves it takes, and whether it
# condenses, is what the alignment is for, so the pinned part is only the FIRST
# of its run and the span that follows decides the rest.
#
# A pin is a hard constraint, so it is only taken where the evidence is
# unambiguous, and four things withdraw one:
#
#   * an ambiguous alias — `Tp.` is Timpani or Trumpet and `Basso` is a voice or
#     the contrabasses (`instruments.AMBIGUOUS_ALIASES`). POSITION settles those,
#     and a pin is the one move that takes position off the table;
#   * a name the work prints in two separate places, so the run is not unique;
#   * the same name claimed by two separated blocks of staves, which is a
#     contradiction rather than evidence — it is what a misread does. Beethoven 5
#     p.48 prints `Tr.` for the trumpets and `Tr. Bas.` for the bass trombone,
#     and the lexicon reads both as Trumpet; neither pins, and the alignment goes
#     back to weighing them, which is what it is for;
#   * a clef — never. Supplying clefs is what the join exists to do, and pinning
#     on them would be circular exactly where it matters.


def unique_part_runs(parts: Sequence[str]) -> dict[str, tuple[int, int]]:
    """Canonical name -> its one maximal run of consecutive parts.

    A name the work prints in TWO places is left out: "which run did the label
    mean?" has no answer, and a pin may not guess. Runs are maximal and
    consecutive because that is how a part list writes an instrument — Flute 1
    then Flute 2, Alto then Tenor then Bass Trombone.
    """
    runs: dict[str, list[tuple[int, int]]] = {}
    i = 0
    while i < len(parts):
        j = i
        while j + 1 < len(parts) and parts[j + 1] == parts[i]:
            j += 1
        runs.setdefault(parts[i], []).append((i, j))
        i = j + 1
    return {name: found[0] for name, found in runs.items() if len(found) == 1}


def label_pins(
    n_staves: int,
    labels: dict[int, str],
    parts: Sequence[str],
    pinnable: set[int] | None = None,
) -> list[tuple[int, int]]:
    """Which staves pin to which part: `(slot, part index)`, in slot order.

    Only the FIRST staff of a run of consecutive same-named staves pins, to the
    FIRST part of that instrument's run — the three staves labelled `Tr. Alt.`,
    `Tr. Ten.` and `Tr. Bas.` say "the trombones start here", and the span that
    follows distributes them. Consecutive matters: an unlabelled staff between
    two same-named ones breaks the run rather than being assumed to belong to it.

    `pinnable` is the staves whose label was unambiguous enough to constrain on;
    the caller owns that judgement because only it still has the raw text.
    """
    runs = unique_part_runs(parts)
    allowed = set(range(n_staves)) if pinnable is None else set(pinnable)

    blocks: list[tuple[int, str]] = []
    i = 0
    while i < n_staves:
        name = labels.get(i)
        if name is None or i not in allowed or name not in runs:
            i += 1
            continue
        j = i
        while j + 1 < n_staves and (j + 1) in allowed and labels.get(j + 1) == name:
            j += 1
        blocks.append((i, name))
        i = j + 1

    claimed: dict[str, int] = {}
    for _, name in blocks:
        claimed[name] = claimed.get(name, 0) + 1
    return [(slot, runs[name][0]) for slot, name in blocks if claimed[name] == 1]


def align_to_layout_pinned(
    layout: ScoreLayout,
    n_staves: int,
    labels: dict[int, str] | None = None,
    clefs: dict[int, str] | None = None,
    part_clefs: list[str | None] | None = None,
    allow_merge: bool = False,
    pinnable: set[int] | None = None,
    absorbed: dict[int, list[int]] | None = None,
) -> tuple[list[int | None], list[tuple[int, int]]]:
    """`align_to_layout`, with labelled staves held to their part.

    Falls straight through to the unpinned alignment when nothing pins, so a page
    with no labels — or none the lexicon can resolve — behaves exactly as before.

    Each pin opens a span running to the next pinned staff, and drawing on the
    parts from its own forward until the next part some OTHER pin has spoken for.
    That last clause is what carries the transposition: on Beethoven 5 p.48 the
    Timpani pin takes part 17 and stops at 18, while the trombone pin below it
    takes 14 and stops at 17 — so the three staves the monotone path could not
    reach are simply the span of the pin that names them.
    """
    labels = labels or {}
    clefs = clefs or {}
    if part_clefs is None:
        part_clefs = [_default_clef(p) for p in layout.parts]

    pins = label_pins(n_staves, labels, layout.parts, pinnable)
    if not pins:
        _score, assignment = align_to_layout(
            layout, n_staves, labels, clefs, part_clefs, allow_merge,
            return_indices=True, absorbed=absorbed,
        )
        return list(assignment), []

    out: list[int | None] = [None] * n_staves
    # Positions are the PAGE's, not the span's. A span is a slice of both
    # sequences, and renormalising it would stretch that slice back over the full
    # 0..1 range — moving the two sides relative to each other and deciding
    # merges on an axis the page never had. Measured on Beethoven 5 p.2 and the
    # Pastoral, where the local axis makes condensing Violin 2 with the viola
    # look no worse than the cello-and-bass staff the engraving actually prints,
    # and both pages lose a staff.
    s_axis = [i / max(1, n_staves - 1) for i in range(n_staves)]
    p_axis = [j / max(1, layout.size - 1) for j in range(layout.size)]

    def solve(slot_lo: int, slot_hi: int, pool: list[int]) -> None:
        if slot_lo > slot_hi or not pool:
            return
        sub = ScoreLayout(layout.name, tuple(layout.parts[p] for p in pool))
        sub_absorbed: dict[int, list[int]] = {}
        _score, assignment = align_to_layout(
            sub, slot_hi - slot_lo + 1,
            {k - slot_lo: v for k, v in labels.items() if slot_lo <= k <= slot_hi},
            {k - slot_lo: v for k, v in clefs.items() if slot_lo <= k <= slot_hi},
            [part_clefs[p] for p in pool],
            # Condensation is what a page does when it has MORE parts than
            # staves, and between two pins both counts are known — which is the
            # one place that global fact becomes local. Leaving merge on where
            # the span does not need it is not neutral: a merge is rewarded with
            # another full pair score, so on a span whose parts all share one
            # name — the three trombones, the two violins — every label matches
            # every part and the DP condenses them all onto one staff rather
            # than reading them 1:1. Measured on Beethoven 5 p.48: with merge
            # left on, the three trombone staves the pins finally reach all come
            # back "Alto Trombone".
            allow_merge and len(pool) > slot_hi - slot_lo + 1,
            return_indices=True,
            staff_positions=s_axis[slot_lo:slot_hi + 1],
            part_positions=[p_axis[p] for p in pool],
            absorbed=sub_absorbed,
        )
        for offset, index in enumerate(assignment):
            if index is not None:
                out[slot_lo + offset] = pool[index]
        if absorbed is not None:
            for offset, taken in sub_absorbed.items():
                absorbed.setdefault(slot_lo + offset, []).extend(
                    pool[t] for t in taken)

    # Every pin opens a span of staves, running to the next pinned staff. The
    # leading span, above the first pin, has no part of its own.
    spans: list[tuple[int, int, int, list[int]]] = [(0, pins[0][0] - 1, -1, [])]
    for (slot, part), (next_slot, _) in zip(pins, pins[1:] + [(n_staves, 0)]):
        spans.append((slot, next_slot - 1, part, [part]))

    # Now the parts no pin holds. Each goes to the LAST span, in STAFF order,
    # whose own part lies above it — and that is the whole content of the
    # transposition. Score order RESUMES after one: on Beethoven 5 p.48 the
    # timpani are printed above the trombones, so the timpani pin sits on an
    # earlier staff while holding a later part, and the strings below belong to
    # the staves below — the trombone span — not to the displaced pin that
    # happens to hold the numerically nearest part. Taking the nearest part
    # instead strands all five string staves with nothing to read.
    anchored = {part for _, part in pins}
    for q in range(layout.size):
        if q in anchored:
            continue
        home = max((i for i, (_, _, part, _) in enumerate(spans) if part < q),
                   default=0)
        spans[home][3].append(q)

    for slot_lo, slot_hi, _part, pool in spans:
        solve(slot_lo, slot_hi, sorted(pool))

    return out, pins
