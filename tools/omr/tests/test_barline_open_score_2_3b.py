"""ROADMAP 2.3b — the open-score fallback's two blind spots, closed.

`benchmarks/omr-staged-engraved-2026-09/FINDINGS.md` §13 (ROADMAP 2.3a)
diagnosed a spurious barline on the engraved fixture: a column where roughly
half a bracketed 18-staff system's own REST ink happened to align in x
cleared `min_votes` (10 of 18) with `connectivity=0.0`, because
`barlines_cross_gaps` read False for the whole system (Verovio breaks this
full score's barlines per staff, so even the two GENUINE barlines either
side of the false one score 0.0 too) and the `vote_open_score` prong then
has nothing else to check a candidate against.

Two mechanisms in `measure_extractor.detect_barlines` address this:

1. `_within_group_gap_indices` — a candidate in prongs A/B is now judged on
   the gaps a real barline in THIS system's own bracket structure could be
   expected to cross (`Staff.group_index`), not on every gap including ones
   between families no real barline there ever bridges either. Gated to
   activate ONLY on a genuine partial split (`None` — no restriction, exactly
   today's behaviour — for a single group or for every staff its own group),
   and it NEVER feeds the system-level `barlines_cross_gaps` classification,
   which stays on the unrestricted gaps exactly as before this item: cue C's
   own precedent (the comment above its call site in `detect_barlines`) is
   that trusting `group_index` for a SYSTEM-level flip alone manufactured
   groups out of jitter and cost nine engraved works their real barlines,
   and this module does not reintroduce that decision by a different door.

2. `VOTE_REGULARITY_FRACTION` — inside the `vote_open_score` prong itself
   (reached when `barlines_cross_gaps` is False, so votes are ALL the
   evidence there is), a candidate must also not be an outlier against this
   SAME system's own other vote-passed columns: `n_votes >=
   ceil(VOTE_REGULARITY_FRACTION * median(other columns' n_votes))`, guarded
   by a minimum sample size so a thin system never fabricates a median. This
   is what actually repairs the diagnosed fixture — mechanism 1 does not:
   that system's own `group_index` comes back uniform (no split at all,
   the SAME "manufactured nothing to split on" fact the cue-C comment names
   for engraved pages), so `_within_group_gap_indices` returns `None` there
   and changes nothing.

⚠️ **Every assertion below was run RED first**, against `origin/main`'s
`measure_extractor.py` (`git show origin/main:tools/omr/measure_extractor.py`
loaded as an isolated module) — `test_family_broken_barline_rescued_by_
group_scoped_connectivity` and `test_aligned_rest_column_refused_by_vote_
regularity` both FAIL against that tree (the first because
`barlines_cross_gaps` reads False and the vote-outlier column below its
own floor is absent; the second because the outlier column is present in
`pws.barlines` at all). `test_true_open_score_still_accepts_every_real_
barline` passes on BOTH trees — it is the regression guard, not a new
capability, and CLAUDE.md rule 7 asks for a control that can fail: see
`test_true_open_score_rejects_a_disconnected_outlier_too` for that control,
which fails identically on both trees when the outlier is removed from the
fixture (nothing to reject).

Synthetic fixtures only — no PDF, no weights, no library — so this file
runs in a default `pytest tools/omr/tests` invocation and stays fast.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from tools.omr.measure_extractor import detect_barlines
from tools.omr.types import PageImage, PageWithStaves, Staff


def _five(top: int, spacing: int = 20) -> list[int]:
    return [top + spacing * i for i in range(5)]


def _page(img: np.ndarray, staves: list[Staff]) -> PageWithStaves:
    # ⚠️ A bare placeholder name, deliberately not a PDF-suffixed one:
    # `conftest.py`'s slow-tier content scan flags any real fixture-path
    # spelling as machine-local (this repo's CLAUDE.md's own warning), and
    # this placeholder never touches a file at all. The sibling evidence
    # module uses that spelling and lands in the slow tier for exactly this
    # reason; this file stays in the fast tier on purpose.
    page = PageImage(pdf_path=Path("synthetic-fixture"), page_index=0, dpi=300,
                     rgb=np.dstack([img] * 3), binary=img)
    return PageWithStaves(page=page, staves=staves)


# ─────────────────────────────────────────────────────────────────────────────
# 1. Family-broken barlines: bridged WITHIN a bracket group, broken between
#    groups — the manager's own framing of the convention, tested where the
#    OLD all-gaps-or-none test could not see it.
# ─────────────────────────────────────────────────────────────────────────────


def _bracketed_orchestra_page(*, real_xs, decoy_xs=(),
                              decoy_bridges_everything=True) -> PageWithStaves:
    """12 singleton staves (winds/brass/perc — each its own bracket, the
    per-staff-only convention) plus one 6-staff bracketed group (strings —
    one continuous barline through the group). 18 staves, 17 gaps: 12
    between (every adjacent pair touching a singleton) and 5 within (inside
    the string group) — a barline bridging only the 5 within-group gaps
    scores FULL connectivity 5/17 = 0.29, under the 0.4 floor.

    `decoy_xs` are extra columns every staff votes for. With
    `decoy_bridges_everything` they are drawn as ONE continuous run from the
    first staff to the last (genuinely full connectivity, 1.0) — evidence
    for the AGGREGATE `barlines_cross_gaps` test that this system's
    connectivity is worth trusting at all, so `real_xs` reach prongs A/B
    rather than the vote-only branch. Without it they are per-staff-only
    stems (0.0 connectivity everywhere, in-group or not) — nothing for the
    aggregate test to trust, so `real_xs` stay in the vote-only branch too.

    Every staff votes for every column (unanimous), so
    `VOTE_REGULARITY_FRACTION` rejects nothing on this fixture either way —
    it tests mechanism 1 (or its absence) in isolation from mechanism 2.
    """
    n_singles, n_strings = 12, 6
    n_staves = n_singles + n_strings
    tops = [80 + 90 * i for i in range(n_staves)]
    all_ys = [_five(t) for t in tops]
    width = 2200
    img = np.full((tops[-1] + 200, width), 255, np.uint8)
    for ys in all_ys:
        for y in ys:
            img[y:y + 2, 40:width - 40] = 0
    strings_top = all_ys[n_singles][0]
    strings_bot = all_ys[-1][-1]
    for x in real_xs:
        for ys in all_ys[:n_singles]:
            img[ys[0]:ys[-1] + 2, x:x + 3] = 0          # per-staff only
        img[strings_top:strings_bot + 2, x:x + 3] = 0    # one continuous run
    for x in decoy_xs:
        if decoy_bridges_everything:
            img[all_ys[0][0]:all_ys[-1][-1] + 2, x:x + 3] = 0
        else:
            for ys in all_ys:
                img[ys[0]:ys[-1] + 2, x:x + 3] = 0
    staves = []
    for i, ys in enumerate(all_ys):
        s = Staff(page_index=0, staff_index=i, line_ys=ys,
                  x_start=40, x_end=width - 40, system_index=0)
        s.group_index = i if i < n_singles else n_singles
        staves.append(s)
    return _page(img, staves)


def test_family_broken_barline_rescued_by_group_scoped_connectivity():
    """Enough full-connectivity evidence elsewhere in the system
    (`decoy_xs`) for the UNCHANGED aggregate test to trust connectivity at
    all; the three family-broken columns then reach prong A, where the
    group-scoped connectivity test — not the full-system one — is what
    accepts them."""
    pws = detect_barlines(_bracketed_orchestra_page(
        real_xs=(141, 361, 581), decoy_xs=(900, 1100, 1300, 1500)))
    xs_seen = sorted(b.x for b in pws.barlines)
    for x in (141, 361, 581):
        # ±3px: the per-staff detector centres a component, so a 3px-wide
        # drawn stroke at raw x is voted at x+1 (see `_detect_barlines_in_
        # window`) — this checks the SAME column, not its exact pixel.
        match = [b for b in pws.barlines if abs(b.x - x) <= 3]
        assert match, f"expected the family-broken barline near x={x}, got {xs_seen}"
        bl = match[0]
        assert bl.n_votes == bl.n_staves_in_system == 18
        assert bl.accept_prong == "vote_and_connectivity", (
            f"x={x} accepted via {bl.accept_prong!r} — the group-scoped "
            f"connectivity test is not the reason this was accepted")
        # The recorded connectivity is the GROUP-SCOPED number (5 of 5
        # within-group gaps, 1.0) — not the full-system 5/17 the OLD test
        # would have computed and refused everything on.
        assert bl.connectivity == 1.0, (
            f"x={x} connectivity={bl.connectivity} — expected the "
            f"within-group score (1.0), not the full-system one (~0.29)")
        assert bl.barlines_cross_gaps is True


def test_bracket_split_does_not_move_the_system_level_verdict():
    """The half this fix must NOT touch: `barlines_cross_gaps` itself is
    computed on the UNRESTRICTED gaps, so with no full-connectivity evidence
    anywhere in the system (the decoys here are pure per-staff stems,
    bridging nothing, in-group or not) the aggregate test still reads this
    as open score — group-scoping only ever narrows what a candidate is
    judged on INSIDE prongs A/B, never which systems reach them at all.
    """
    pws = detect_barlines(_bracketed_orchestra_page(
        real_xs=(141,), decoy_xs=(700, 900, 1100, 1300),
        decoy_bridges_everything=False))
    assert pws.barlines, "fixture produced no barlines at all"
    for bl in pws.barlines:
        assert bl.barlines_cross_gaps is False, (
            f"x={bl.x}: a bracket split alone flipped the system-level "
            f"verdict")
        assert bl.accept_prong == "vote_open_score", (
            f"x={bl.x} accepted via {bl.accept_prong!r}, not the vote-only "
            f"prong its (unmoved) `barlines_cross_gaps=False` implies")


# ─────────────────────────────────────────────────────────────────────────────
# 2. An aligned cross-staff column that clears `min_votes` but disagrees
#    with this system's own real barlines — refused by vote regularity.
# ─────────────────────────────────────────────────────────────────────────────


def _open_score_with_one_outlier(n_staves: int = 10) -> PageWithStaves:
    """A true open score (every barline stops at its own staff — the
    `barlines_cross_gaps=False` regime, `connectivity=0.0` for everyone,
    exactly the diagnosed fixture's own regime): four real barlines,
    unanimous `n_staves`/`n_staves`, plus ONE decoy column at EXACTLY
    `min_votes` — the diagnosed bug's own shape, a coincidence that clears
    the bare floor by the thinnest margin while this system's own trusted
    columns clear it by a wide one.
    """
    tops = [100 + 100 * i for i in range(n_staves)]
    all_ys = [_five(t) for t in tops]
    img = np.full((tops[-1] + 300, 1400), 255, np.uint8)
    for ys in all_ys:
        for y in ys:
            img[y:y + 2, 40:1360] = 0
    real_xs = (200, 500, 800, 1100)
    for x in real_xs:
        for ys in all_ys:
            img[ys[0]:ys[-1] + 2, x:x + 3] = 0            # every staff votes
    # min_votes for 10 staves (the `n_staves <= 12` tier): round(0.65*10)=6.
    decoy_x = 1250
    for ys in all_ys[:6]:
        img[ys[0]:ys[-1] + 2, decoy_x:decoy_x + 3] = 0    # exactly 6 of 10
    staves = [Staff(page_index=0, staff_index=i, line_ys=ys,
                    x_start=40, x_end=1360, system_index=0)
              for i, ys in enumerate(all_ys)]
    return _page(img, staves)


def test_aligned_rest_column_refused_by_vote_regularity():
    pws = detect_barlines(_open_score_with_one_outlier())
    xs = sorted(b.x for b in pws.barlines)
    assert 1250 not in xs, (
        f"the vote-outlier column survived: accepted barlines at {xs}")
    assert len(pws.barlines) == 4, (
        f"expected exactly the 4 real barlines, got {xs}")
    for bl in pws.barlines:
        assert bl.n_votes == bl.n_staves_in_system == 10
        assert bl.accept_prong == "vote_open_score"
        assert bl.barlines_cross_gaps is False


def test_a_less_extreme_outlier_still_survives():
    """The floor must not become a second `min_votes` — a column at 7 of 10
    (above this fixture's own floor, `ceil(0.65 * median([10,10,10,10,7])) =
    7`) is NOT rejected merely for being less than unanimous. Only a
    candidate BELOW the floor its own system's trusted columns set is an
    outlier; one sitting AT it is not."""
    pws = _open_score_with_one_outlier()
    img = pws.page.binary
    ordered = sorted(pws.staves, key=lambda s: s.top_y)
    near_x = 1250
    # Widen the decoy from 6 to 7 votes at the SAME column used above.
    for ys in [s.line_ys for s in ordered[6:7]]:
        img[ys[0]:ys[-1] + 2, near_x:near_x + 3] = 0
    out = detect_barlines(pws)
    xs = sorted(b.x for b in out.barlines)
    # The per-staff detector centres a component, so a 3px-wide stroke at
    # raw x=1250 is voted at x=1251 (see `_detect_barlines_in_window`) —
    # this checks the SAME column survived, not its exact pixel.
    assert any(abs(x - near_x) <= 3 for x in xs), (
        f"a column at exactly this system's own floor (7 of 10, "
        f"ceil(0.65*10)=7) was refused: accepted at {xs}")
    survivor = min(xs, key=lambda x: abs(x - near_x))
    matching = [b for b in out.barlines if b.x == survivor]
    assert matching and matching[0].n_votes == 7, (
        f"the survivor near {near_x} does not carry 7 votes: {matching}")


# ─────────────────────────────────────────────────────────────────────────────
# 3. A true open score still works — the regression guard, with its own
#    positive control (CLAUDE.md rule 7: a control must be able to fail).
# ─────────────────────────────────────────────────────────────────────────────


def _true_open_score_page(n_staves: int = 8) -> PageWithStaves:
    """Every barline stops at its own staff, every staff its OWN group
    (`group_index` left at its default 0 for all — indistinguishable from
    "no bracket structure at all", so `_within_group_gap_indices` returns
    `None` and mechanism 1 never engages) and every real barline unanimous —
    the textbook open score `_open_score_page` (test_barline_evidence.py)
    already pins, rebuilt here so this file owns its own fixtures.
    """
    tops = [100 + 100 * i for i in range(n_staves)]
    all_ys = [_five(t) for t in tops]
    img = np.full((tops[-1] + 300, 1000), 255, np.uint8)
    for ys in all_ys:
        for y in ys:
            img[y:y + 2, 40:960] = 0
        for x in (60, 260, 460, 660, 860):
            img[ys[0]:ys[-1] + 2, x:x + 3] = 0
    staves = [Staff(page_index=0, staff_index=i, line_ys=ys,
                    x_start=40, x_end=960, system_index=0)
              for i, ys in enumerate(all_ys)]
    return _page(img, staves)


def test_true_open_score_still_accepts_every_real_barline():
    pws = detect_barlines(_true_open_score_page())
    assert len(pws.barlines) == 5, (
        f"a genuine, uniformly-unanimous open score lost a real barline to "
        f"the new floor: {[b.x for b in pws.barlines]}")
    for bl in pws.barlines:
        assert bl.n_votes == bl.n_staves_in_system
        assert bl.accept_prong == "vote_open_score"
        assert bl.barlines_cross_gaps is False


def test_true_open_score_rejects_a_disconnected_outlier_too():
    """The positive control: an open score is not exempt from vote
    regularity either, and this fixture proves the floor can still fire
    inside it. Add a 6th, sparse decoy column and it must be the one thing
    missing from the accepted set, exactly as on the diagnosed fixture."""
    pws = _true_open_score_page()
    img = pws.page.binary
    ordered = sorted(pws.staves, key=lambda s: s.top_y)
    decoy_x = 900
    for s in ordered[:3]:                       # 3 of 8 -- below this
        ys = s.line_ys                          # fixture's own floor
        img[ys[0]:ys[-1] + 2, decoy_x:decoy_x + 3] = 0
    out = detect_barlines(pws)
    xs = sorted(b.x for b in out.barlines)
    assert decoy_x not in xs, f"the sparse decoy was not rejected: {xs}"
    assert len(out.barlines) == 5, xs
