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
    """

    layout: ScoreLayout             # the best-scoring layout, i.e. the tradition
    assignment: tuple[str | None, ...]
    agreement: tuple[float, ...]
    score_per_staff: float
    considered: tuple[str, ...]     # every layout that got a vote

    def instrument_for(self, ordinal: int) -> str | None:
        """The instrument agreed for the `ordinal`-th staff of the system."""
        if 0 <= ordinal < len(self.assignment):
            return self.assignment[ordinal]
        return None

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
) -> tuple[float, list[str | None]]:
    """Align `n_staves` observed staves against one layout.

    Needleman-Wunsch with three moves, and the third is the one that makes this
    work on real scores:

    * **skip a part** — the instrument is absent from this page;
    * **skip a staff** — this staff has no part in the layout at all;
    * **continue a part** — this staff is another staff of the SAME part, which
      is how two horns, a harp, or divided violins are printed.

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
    part_clefs = [_default_clef(p) for p in layout.parts]

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
                labels.get(i - 1), clefs.get(i - 1), (i - 1) / s_denom,
                layout.parts[j - 1], (j - 1) / p_denom, part_clefs[j - 1],
            )
            open_ = dp[i - 1][j - 1] + pair
            cont = ext[i - 1][j] + pair + EXTEND_PENALTY
            if open_ >= cont:
                ext[i][j], ext_back[i][j] = open_, "open"
            else:
                ext[i][j], ext_back[i][j] = cont, "continue"

            skip_part = dp[i][j - 1] + GAP_LAYOUT
            skip_staff = dp[i - 1][j] + GAP_STAFF
            best = max(ext[i][j], skip_part, skip_staff)
            dp[i][j] = best
            dp_back[i][j] = ("match" if best == ext[i][j]
                             else "skip_part" if best == skip_part else "skip_staff")

    out: list[str | None] = [None] * m
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
            while True:
                out[i - 1] = layout.parts[j - 1]
                if ext_back[i][j] == "continue":
                    i -= 1
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
        total, assignment = align_to_layout(layout, n, labels, clefs)
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
    for i in range(n):
        tally: dict[str, float] = {}
        for (_, _, a), w in zip(voters, weights):
            name = a[i]
            if name is not None:
                tally[name] = tally.get(name, 0.0) + w
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
    """
    if fit is None or not candidates:
        return None
    proposed = fit.instrument_for(ordinal)
    if proposed is None:
        return None
    for candidate in candidates:
        if candidate.name == proposed:
            return candidate
    return None
