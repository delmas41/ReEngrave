# ROADMAP 2.23 -- a head's fill (hollow vs black) is read from the ink, not only from the detector's class

PATH: STAGED. Branch `claude/head-fill-2.23`. Not merged.

`benchmarks/omr-bar-sum-holdout-2026-09/FINDINGS.md` Sec.17b: on Litolff 1/i
(Beethoven 5/i, Litolff `984073`, a MERGING plate -- CLAUDE.md Sec.10), the
single biggest minimal-fix class over the whole movement's held bars is
`F` -- **300 bars**, 405 released as the sole fix -- "one note's head fill
or stem misread", 278 of them a lone quarter-valued chord in a 2/4 bar.
Sec.17b's own crops (`out/print/held-mvt-2026-09-29-litolff-F-*.png`) read as
hollow (half/whole) heads the detector called BLACK on a MERGING plate.

Today the head's fill comes ONLY from the detector's class
(`noteheadBlack*` vs `noteheadHalf*`/`noteheadWhole*`). This item asks
whether the ink under the box says something the class does not, and if
so, wires it in as a NARROW, never a flip.

## Sec.1. First: read the crops by eye, then measure -- is there a gap?

### Sec.1a. The six `F`-class crops, read by eye

`benchmarks/omr-bar-sum-holdout-2026-09/out/r222/litolff-F-jobs.json`
names 6 subjects (page/system/cell, `judged_quarters=2.0`, `voice_sums=
[1.0]` on every one -- the bar is short by exactly one quarter, the
signature of a half misread as a quarter). Zoomed crops of all six
(`held-mvt-2026-09-29-litolff-F-0{1..6}-F.png`, red corners bracket the
subject):

- **#1** (`glyph/1/0/8/8/{3,4}`, m9, P9): a visible white sliver inside
  the black ink, merged with the staff line -- a hollow head whose border
  fused with its own rung.
- **#3** (`glyph/3/0/10/4/1`, m52, P11): stem visible, head sits at the
  cell boundary; ambiguous by eye alone at this zoom.
- **#5** (`glyph/5/0/5/5/{0,1}`, m117, P8): reads as fully solid black at
  10x zoom -- no visible hollow. This one may be a genuine BLACK head
  whose bar is short for a DIFFERENT reason (a spurious/missing event
  elsewhere); `F` is the MINIMAL single-letter fix, not a claim that the
  head itself is the fault.
- **#6** (`glyph/6/0/8/3/{1,4,7}`, m145, P11): unambiguous -- a clear white
  hole inside the black ink at 5x zoom, sitting on the staff line.

Two of six are unambiguously hollow by eye; one (#5) looks genuinely
solid. This is exactly why the fix must be a NARROW decided by the bar's
own arithmetic (reconcile_duration), never a flip on ink alone -- ink
alone would be wrong on #5.

### Sec.1b. The measurement: does `Q.NOTEHEAD_INK` separate them?

Ported the GATHER half only of `claude/no-ink-head-2.6h` (`a8394476`) --
`gather.notehead_ink_under` / `gather_notehead_ink`, `Q.NOTEHEAD_INK` (two
windows, `center` and `ring`, off BOTH `cell.binary` and `cell.image_no_
staff`) -- into `tools/omr/staged/{gather,record,capture}.py`. Did NOT
port `a8394476`'s own ADJUDICATE half (`notehead_precision._no_ink_
under_box`, measured DEAD AT ZERO and not merged -- ROADMAP row 2.6h).

Re-gathered (CLAUDE.md Sec.5a setup; `--no-surya --no-ocr`, own weights):

- **Engraved control**: `benchmarks/omr-staged-engraved-2026-09/out/
  fixture/beethoven-sym5-mvt1-m1-24.pdf`, pages 0-2, `imgsz2048-ft-30ep.pt`,
  dpi 300 -- the fixture whose truth F1 is 0.951, so the DETECTOR's own
  `noteheadHalf`/`noteheadBlack`/`noteheadWhole` class is a trustworthy
  proxy for the true fill on this population.
- **Litolff**: pdf idx 1-6 (the six pages the `F` crops sit on),
  `deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt`, dpi 600.

372 engraved heads, both `ink_raw` and `ink_net` windows, grouped by the
DETECTOR's own class:

| class | n | `center` (min / median / max) | `ring` (min / median / max) |
|---|--:|---|---|
| `noteheadBlack*` | 532 rows | 1.0 / 1.0 / 1.0 | 0.652 / 0.751 / 0.862 |
| `noteheadHalf*` | 206 rows | 0.070 / 0.108 / 0.449 | 0.477 / 0.573 / 0.652 |
| `noteheadWhole*` | 6 rows | 0.964 / 1.0 / 1.0 | 0.509 / 0.536 / 0.537 |

**There is a clean, decisive gap between BLACK and HALF**: every confirmed
BLACK head reads `center == 1.0` exactly; every confirmed HALF head reads
`center <= 0.449`. At threshold `center <= 0.5` AND `ring - center >=
0.1`: **206/206 HALF heads admit "hollow"; 0/532 BLACK heads do; 0/6 WHOLE
heads do.**

**KNOWN GAP, found by the same measurement, not papered over**: WHOLE
heads read `center == 1.0` too -- indistinguishable from BLACK by this
test. A whole notehead's box is wide and short; shrinking 30% on every
side (`NOTEHEAD_INK_CENTER_SHRINK`) lands the "centre" window back on the
ellipse's own ink rather than its hole. **This test can only ever catch
a HALF head misread as BLACK, never a WHOLE head misread as BLACK.** That
is the correct, safe failure mode (rule 8: it abstains rather than
guessing), and it is why the built rule still offers `whole` as a
candidate FOR THE BAR TO CHOOSE, never claims the ink witnesses it.

**Conclusion: yes, there is a separating gap** -- proceed to ADJUDICATE.

## Sec.2. Built (ADJUDICATE): `rhythm.adjudicate_duration` NARROWS on decisive disagreement

CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED (nobody has
been asked, CLAUDE.md rule 3): a hollow head's own interior stays
near-empty even where its border merges with neighbouring ink; a
genuinely filled BLACK head does not. It would be falsified by a
Sean-adjudicated crop where a confirmed BLACK head reads this way, or a
confirmed HOLLOW head does not (this benchmark's own crops, Sec.4, are the
first test of it).

`tools/omr/staged/adjudicators/rhythm.py`, `adjudicate_duration`: reached
only where NOTHING else already narrowed or added a mark to this note
(no flags, no ambiguous beams, no stem-tip flag ink -- `beam_evidence ==
"none_over_this_note"`, guard `not tip_ink`) and the detector's own class
says BLACK (`base == 1.0`) -- a hollow head never carries a beam or a
flag, so this is exactly the right population. Reads `Q.NOTEHEAD_INK` off
the SAME glyph (`_ink_reads_decisively_hollow`, either raster alone is
enough, same two-raster safety the gather side states). Where decisive,
`Ruling.narrow` over three candidates -- `black` (the detector's own
reading, support 1.0), `half` (support 2.0 -- the single-step misread
Sec.17b's crops show), `whole` (support 1.0, the rarer two-step misread,
included so `reconcile_duration`'s own bar arithmetic can still pick it
where it is the unique landing). **Never flipped outright** -- `reason=
"head_fill_from_ink"`, `Outcome.NARROWED`, exactly the shape 2.19/2.22's
`reconcile_duration` already knows how to search (`_admitted` reads a
NARROWED note's own candidates; no change needed there).

Thresholds (`HEAD_FILL_HOLLOW_CENTER_MAX = 0.5`,
`HEAD_FILL_HOLLOW_RING_GAP_MIN = 0.1`) are the Sec.1b engraved measurement,
with margin on both sides of the gap.

## Sec.3. Priced on the re-gathered pages

**Whole-movement re-gather (pages 1-6, both `F`-crop pages) was attempted
and KILLED, not completed** -- CLAUDE.md Sec.6b's noise floor and
Sec.13's "sessions in parallel" both understated it: load average 6.6-6.8
on this shared machine, two OTHER sessions' processes each holding ~98%
CPU throughout, my own gather sat at 0.0% CPU (frozen wall-clock, not
progressing) for 5+ minutes at a stretch, on page 6 of 6 after ~17 minutes
elapsed. This is the exact "frozen-CPU-time shape... contention, not a
hang" `claude/no-ink-head-2.6h` (`a8394476`) already named. Killed rather
than re-risked (that commit's own precedent); **pricing the full 300-bar
`F` population is NOT DONE and needs a re-attempt when the machine is
less loaded** -- this is the honest state, not a number to round up.

**Fell back to ONE page** (Litolff pdf idx 6, containing the original
`F`-06 crop, m145) -- cheap, and it completed. `--musicxml` on a lone page
carries no `<time>` (the meter is declared at the movement's START, page
0, not on this page), so `bar_sum_check.py` reports every bar
`unassessable` on this file -- an artefact of slicing one page out of a
movement, not a property of this rule. Bar-level pricing therefore reads
the RECORD directly (`Q.EVENT`/`Q.DURATION`), not the exported file.

**Reach, on this one page**: 786 notehead-classed glyphs read
`noteheadBlack*`. Of those, **8 read decisively hollow by ink**
(`center <= 0.5` and `ring - center >= 0.1`, either raster) -- 1.0% of the
population, in line with a genuinely rare misread, not a threshold that
fires promiscuously. Of those 8:

- **2 are genuinely BEAMED** (`beam_evidence == "read"`, both `beats =
  0.5`, real eighth notes) -- the ink's hollow-shaped reading on these is
  a FALSE POSITIVE by the ink test alone, and the marks-gate
  (`beam_evidence == "none_over_this_note"`) correctly keeps them OUT of
  this rule's population. Crops #2/#3 below.
- **4 sit where the beam READER NEVER RAN on that cell**
  (`beam_evidence == "reader_declined"`) -- a different state from "ran
  and found nothing", and the gate (matching `flag_ink_unread`'s own
  convention, same file) correctly declines these too rather than
  narrowing under an unknown beam context. Crops #4/#5 below (2 of the 4).
- **1 is the original `F`-06 crop's own BLACK-classed member**
  (`glyph/6/0/8/3/4`): `ink_net` centre reads **0.6036** -- just ABOVE the
  `0.5` threshold, so the rule correctly declines (rule 8: not decisive,
  left alone). Crop #6.
- **1 reaches the rule and NARROWS** (`glyph/6/1/9/2/9`, `beam_evidence ==
  "none_over_this_note"`): `Ruling.narrow` to `[black 1.0q, half 2.0q,
  whole 4.0q]`, `reason="head_fill_from_ink"`. It stayed NARROWED, not
  DECIDED -- `reconcile_duration`'s cause is `Q.METER`, and this system's
  meter ABSTAINS (the same, already-documented Sec.17a gap: "3,058 [Brahms]
  held bars sit on systems whose `Q.METER` ABSTAINS" -- this is Litolff's
  own instance of it), so the bar arithmetic that would pick among the
  three candidates never runs. **This is an orthogonal, pre-existing gap,
  not a defect introduced by this rule.** Crop #1.

**A caveat worth recording rather than hiding**: the one glyph that
reached and narrowed has a low detector confidence (0.257, against a
0.504 page median) and a page-pixel box only 6.3px wide -- narrow even
for this scan's own noisy population, and possibly a fragment rather
than a clean notehead detection. Confidence alone is not evidence about
what a glyph IS (CLAUDE.md Sec.9's own caution), and 0.257 is within this
page's ordinary noisy range, so this is flagged, not dismissed.

**Also notable, and NOT this rule's effect**: on this fresh re-gather,
the DETECTOR ITSELF already reads two of the original `F`-06 crop's three
boxed glyphs as `noteheadHalfOnLine` (correctly!) rather than
`noteheadBlackOnLine` -- a run-to-run detector variance between the
original whole-movement gather and this one-page re-gather, consistent
with CLAUDE.md Sec.6b's "a shared record is a snapshot of the reader that
made it" and the scan gate's own noise floor. It is evidence the specific
historical misread is not perfectly deterministic, not evidence this
rule fixed it.

**Engraved control, re-checked on the SAME re-gather used for Sec.1b**: 0
of 372 heads carry `reason == "head_fill_from_ink"` and 0 carry a
resolved `head_fill` -- the rule does not fire at all on the engraved
fixture, where the detector's own BLACK/HALF/WHOLE class already agrees
with the truth at F1 0.951. No real BLACK head is narrowed wrongly.

## Sec.4. Crops

6 banded crops, `benchmarks/omr-head-fill-2026-09/out/print/head-fill-2026-09-0{1..6}.png`,
manifest `head-fill-2026-09-manifest.json` (`VERDICT_none_yet: null`).
GREEN = the staff's own lines; red verticals = the cell's x-span; red
corners bracket the subject glyph's own box. **Frame control
(`crop_losers_2_6b._frame_ok`) REFUSED #2 and #4** (contrast -84.2 and
-99.75) -- kept in the manifest with `frame_ok: false` per the others'
convention, not presented as evidence.

| # | subject | frame | what it shows |
|---|---|---|---|
| 1 | `glyph/6/1/9/2/9` | ok (28.7) | the one head that reached and NARROWED |
| 2 | `glyph/6/0/3/8/19` | REFUSED | genuinely beamed, ink false-positive, gate protects it |
| 3 | `glyph/6/1/11/5/3` | ok (29.1) | genuinely beamed, ink false-positive, gate protects it |
| 4 | `glyph/6/0/0/9/1` | REFUSED | beam reader declined, gate protects it |
| 5 | `glyph/6/1/1/0/8` | ok (110.6) | beam reader declined, gate protects it |
| 6 | `glyph/6/0/8/3/4` | ok (202.4) | the original `F`-06 BLACK member, borderline ink, correctly declined |

## Sec.5. Gates

- RED -> GREEN: `tools/omr/tests/test_staged_notehead_ink.py` (14 tests,
  ported GATHER half only -- the pure measurement, positive controls for
  BLACK and HOLLOW synthetic heads, the orchestration on a fake cell).
  `tools/omr/tests/test_staged_duration.py::
  TestAHeadsFillIsReadFromTheInkNotOnlyTheClass` (9 tests): a decisive
  BLACK-vs-hollow disagreement NARROWS to `[black, half, whole]`;
  POSITIVE CONTROL -- a dense centre (the engraved BLACK reading) still
  DECIDES; no `Q.NOTEHEAD_INK` row at all is unchanged (rule 8); an
  ambiguous reading that clears neither threshold is unchanged; a HOLLOW-
  classed head is not this rule's population even with ink rows attached;
  `flag_ink_unread` (2.18c) takes priority when it already narrowed the
  note (`not tip_ink` guard); it never decides straight to `half` -- stays
  NARROWED (rule 6); the ink row is in the verdict's `basis`; either
  raster alone (`ink_raw` XOR `ink_net`) is sufficient. Confirmed RED
  first by reverting the `rhythm.py` diff and re-running: 4 of 9 fail
  (`AssertionError`) against the unmodified tree.
- `pytest tools/omr/tests -m "not slow" -q -p no:cacheprovider`:
  3784 passed, 3 skipped, 0 failed (full run, no mid-run edits).
- `python3 -m tools.omr.staged.check`: **247, status ok** (unchanged; `wiring` 69->67 and `reach` 25->24 both went from `broken` to `ok`
  once the ADJUDICATE consumer was wired -- confirming `Q.NOTEHEAD_INK`
  reaches a live consumer) (baseline on this
  tree before this change: 247, confirmed by stashing this diff and
  re-running).

## Sec.6. Recommendation

**Ship the GATHER + ADJUDICATE mechanism** (safe, tested, reach-confirmed
on a real scan page, zero false narrowing on the 372-head engraved
control, and it costs nothing where it does not fire -- 785 of 786 black
heads on the priced page are untouched). **Do not yet claim it releases
the 300-bar `F` population** -- that number needs the whole-movement
re-gather this session could not complete (killed at page 6/6 GATHER
after ~17 min of shared-machine contention), and the one page priced
turned up exactly one reaching case, blocked from resolving by an
unrelated, already-documented gap (Sec.17a's meter-abstains-on-system
problem, not this rule).

**Next steps, in order**:
1. Re-attempt the whole-movement Litolff (and ideally Brahms) re-gather
   on a quieter machine/window to price the real `F` population and get
   `bar_sum_check` numbers with a declared meter.
2. Sean's read on the 4 valid crops (#1, #3, #5, #6) -- in particular
   whether #1's low-confidence, 6px-wide box is a real notehead at all.
3. If §17a's meter-carry question (already asked, 2.22) is answered, a
   second pass over the SAME re-gather would show whether this rule's one
   narrowed case actually resolves once the meter is decided.

## Sec.8. Does ADJUDICATE rule out stray ink in a bar that already reads a whole rest?

2026-10-01, branch `lane-whole-rest-stray-ink`. STAGED, GATHER+ADJUDICATE
only (CLAUDE.md §6b). No re-gather: read the saved
`beethoven5-litolff-mvt1-whole-20261001.record.json` (commit
`342ec6244`, `dirty=False`) via `readout.load_run` / `Run.verdicts_at` /
`readout.adjudicate_status`, never re-derived. Sean's framing: "ruling out
random ink in a bar that clearly had a whole note rest" — does the reader
notice when a bar/staff it has just read a whole rest on ALSO carries
other boxed ink the detector called a notehead?

**Count.** A "whole rest read" = a `rest`-family glyph classed `restWhole`
surviving `rest_is_not_a_rest` (not refused), OR any glyph with
`notehead_is_a_whole_rest` DECIDED `True` (the mirror case, a
notehead-shaped box read as the bar's rest). A "stray keeper" = another
`note`-family glyph in the SAME cell whose `adjudicate_status` (ADJUDICATE
only) is `KEPT` — not refused by `notehead_is_not_a_notehead`, not given
away by `glyph_owner`, duration DECIDED (not narrowed/abstained) — with
`glyph_owner`'s own staff equal to (or undecided and left on) the
whole-rest's staff. **113 (staff, bar) cells** match, spread over 14 of
the movement's pages (1–16).

**5 sampled, one per page-region** (`out/print/whole-rest-stray/`, red
corners = the whole-rest subject, blue corners = each KEPT glyph, green =
that staff's own lines):

- `cell/1/0/0/3` (`cell_1_0_0_3.png`) — the whole rest is a clean,
  correctly-shaped box hanging under the staff. The KEPT glyph
  (`glyph/1/0/0/3/1`, `noteheadHalfInSpace`) sits **3.79 staff spaces
  above** its own filed staff (`notehead_staff_position -7.58`,
  `glyph_band_distance 3.785`) with **zero ledger rungs** on all four
  tested (`ledger_rung_ink` False ×4, `ledger_owner_density 0.0`,
  `glyph_ladder False`). Staff `staff/1/0/0` is the TOPMOST staff of its
  system (confirmed: page 1's staves are 0–11, system 0), so
  `belongs_to_a_nearer_staff` structurally cannot fire — there is no
  nearer staff to lose to. `glyph_owner` awards it to its own staff by
  `distance`, the weakest tier, and `notehead_is_not_a_notehead` has no
  rule that reads the ledger-absence CLAUDE.md §10 already states is
  dispositive ("there is no such thing as a far note with no ledger
  line"). **This one reads as a genuine reader fault**, not a second
  voice — a note this far with no rung should abstain, not KEEP with a
  decided duration.
- `cell/2/0/1/15` (`cell_2_0_1_15.png`) — textbook two-voice bar: four
  real eighth/quarter noteheads sit ON the staff forming a melody line,
  the whole rest hangs cleanly below the staff in the same cell. **Correct
  reading** — a second voice, not stray ink.
- `cell/9/1/1/6` (`cell_9_1_1_6.png`, under the "Adagio." tempo marking) —
  five real melody noteheads on the staff above, the whole rest (with a
  fermata drawn over it, a common engraving for a tacet voice) sits below
  the staff. **Correct reading**, same two-voice pattern.
- `cell/8/0/3/4` (`cell_8_0_3_4.png`) — a dense, MERGED chord (Litolff is
  the MERGING plate, CLAUDE.md §10): three real noteheads stacked almost
  on top of each other, and the "whole rest" box is small and sits
  embedded in the same ink mass. By eye this reads as **plausibly a
  misclassified fragment of the chord's own merged ink**, not a genuine
  rest — the opposite-direction mislabel `notehead_is_a_whole_rest` exists
  to catch, but this one is a `restWhole`-classed GATHER box, which that
  adjudicator does not re-examine once the detector's own class already
  says `rest`.
- `cell/15/1/2/18` (`cell_15_1_2_18.png`) — another SHATTERING/merged
  passage: six real noteheads under a beamed run, and a wide filled
  rectangle below the staff reads as the whole rest. Ambiguous by eye at
  this zoom; consistent with either a real rest or heavy ink bleed, not
  conclusively one or the other without a sharper crop.

**0 of 5 samples is "random ink masquerading as a note next to an
untouched rest."** 2 of 5 (`cell/2`, `cell/9`) are confidently a second,
tacet voice — correct. 1 of 5 (`cell/1`) is a confirmed reader fault, but
its cause is the ledger/ownership convention, not the rest. 2 of 5
(`cell/8`, `cell/15`) raise doubt about the REST reading itself on this
MERGING plate, not about stray noteheads.

**The cause, named by adjudicator:**

1. `notehead_is_not_a_notehead` (`tools/omr/staged/adjudicators/
   notehead_precision.py:1736`) ships only GEOMETRIC rules —
   `clipped_fragment`, `too_narrow`, `belongs_to_a_nearer_staff`,
   `notehead_is_a_duplicate_box`, `stacked_head_duplicate` — none of which
   reads `Q.REST`, `Q.NOTEHEAD_IS_A_WHOLE_REST`, or any other fact about
   what else the cell/bar contains. A box that passes these geometric
   gates survives regardless of whether the same staff already reads a
   whole-bar rest beside it.
2. `Q.NOTEHEAD_IS_A_WHOLE_REST` (`rhythm.py:5784`, "is this notehead-classed
   glyph ACTUALLY a whole rest") is the one place CLAUDE.md's "a whole
   rest means the BAR" conclusion is read at ADJUDICATE — but its ORDER
   placement comment (`adjudicate.py` ~line 1023) states outright: "though
   nothing in ADJUDICATE reads its verdict today." Confirmed by grep: its
   only other reader anywhere is `export.py:844`, at EXPORT. So even a
   correctly-decided whole rest changes nothing about how ADJUDICATE
   treats any OTHER glyph in that cell.
3. `glyph_owner`'s weakest tier (`distance`) defaults a far, ledgerless
   glyph to its OWN filed staff whenever no competing staff is near enough
   to trigger `belongs_to_a_nearer_staff` — `cell/1`'s case. Nothing
   downstream re-asks whether a note 3.8 spaces from its staff with zero
   ledger rungs should ever have been kept at all.

**The convention, and its falsifier.** CONVENTION ASSUMED / NOT CONFIRMED
(nobody asked, CLAUDE.md rule 3): *a whole-bar rest in one voice does not
refuse a note in a SIBLING voice on the same staff* — supported by 2 of 5
crops here, both showing the textbook pattern (melody above/below the
staff, rest on the opposite side). This is the right behaviour for
genuine two-voice writing and must not be "fixed" by refusing every
notehead that shares a cell with a rest. It would be FALSIFIED by: (a) a
bar where the "other voice" note has no stem-direction or bar-sum evidence
of a second stream anywhere nearby (`adjudicate_voices`,
`rhythm.py:6192`, already exists to answer exactly this but runs AFTER
duration/ownership and never feeds back to refuse a glyph); or (b) a note
whose own ledger evidence contradicts it belonging to the staff at all
(`cell/1`'s case) — CLAUDE.md §10's own rule ("no such thing as a far note
with no ledger line") already falsifies that one without needing the rest
at all. **Not fixed here** (no code changed; this is a SMALL
investigation, not a re-gather or a battery): a real fix would gate
`notehead_is_not_a_notehead` or `glyph_owner`'s distance tier on the
ledger-rung evidence already gathered (`Q.LEDGER_RUNG_INK`,
`glyph_band_distance`) rather than inventing a new rest-aware rule — the
evidence for `cell/1`'s fault was already on the record and simply never
consulted by the rule that owns that convention.

Crops: `out/print/whole-rest-stray/cell_{1_0_0_3,2_0_1_15,8_0_3_4,
9_1_1_6,15_1_2_18}.png` + `manifest.json`. Script:
`/private/tmp/.../scratchpad/crop_whole_rest_stray.py` (not committed —
scratchpad, reproducible from this section's own queries against the
cited record).

