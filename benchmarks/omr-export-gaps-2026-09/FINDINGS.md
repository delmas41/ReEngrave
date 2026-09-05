# Export gaps, September round: the accents "gap", and the tie/slur veto

**Date:** 2026-09-04 · **Branch:** `claude/export-accents-arcs` (base `0487be1f`)
· **Charter:** close the accents export gap (KNOWN_GAPS' recorded open item)
and build the tie/slur impossible-configuration veto from
`docs/position-grammar-confusables-2026-09-04.md` R3, both measured on both
benchmark families before anything defaults on.

**Duplication check first (mandatory, both hairpin branches inspected):**
`claude/friendly-pike-395b8e`'s tip IS its merge-base with main — zero unique
commits. `claude/mystifying-curran-613606` carries one commit (`53e6f233`,
hairpins: `<wedge>` export + staff attribution); its diff touches accents only
as CLAUDE.md prose — and *propagates the stale claim* this document refutes
("The one open item now is **accents** … nothing consumes them"). Neither
branch closed accents; neither needed to. Hairpins were left entirely alone.

---

## 1. Task A verdict: THE ACCENTS GAP WAS ALREADY CLOSED — two days before the work order

The premise came from CLAUDE.md's OMR-NED section: *"Two open items are
recorded there now: **accents** (Mahler's truth has 6, the detector finds
exactly 6, nothing consumes them)"* — and the design doc's §5 row repeating it
("consumed **0** — a pure export gap wearing a confusable costume"). Both were
stale on the day they were read, and the second inherited the first.

**What the tree actually says, verified live on `0487be1f`:**

| link in the chain | where | state |
|---|---|---|
| the class | `articAccentAbove` / `articAccentBelow` (Mahler: 1 + 5 — the original KNOWN_GAPS entry itself said so) | detected |
| attachment | `transcribe._attach_articulations_in_cell` — "accent" is in `_ARTICULATION_KINDS`, side-aware, 0.75-notehead-width gate | wired; pinned by `test_transcribe_helpers.py` (`articAccentAbove → ("accent", True)`, attach tests) |
| MusicXML | `export._MXL_ARTICULATION["accent"] = "accent"` | wired; pinned by `test_export.py::TestArticulations` |
| LilyPond | `export._LILY_ARTICULATION["accent"] = "->"` | wired; **was unpinned** — test added this round |
| the file | `to_musicxml(mahler.omr.json)` on this tree | **6 `<accent>` against the truth's 6**; `to_lilypond` emits 6 `->` |
| KNOWN_GAPS | the `"accent"` entry ("EIGHTH GAP, open and cheap … This is the next one to close") | **already removed** — left at `6d40e95e`, the same day `df29e9b2` wrote it |

The timeline: `df29e9b2` created `export_coverage.py` with accents as the
eighth gap on 2026-09-01; the articulations work (`0eb1271`, that evening)
closed it — all ten `artic*` classes attached and exported, accents among
them — and the entry was removed; the merge landed on main as `bdda54d`
2026-09-02. CLAUDE.md's articulation section was updated; the sentence in its
OMR-NED section was not, and the 2026-09-04 design doc copied the stale
sentence into its opportunity table, from which this task was cut.

**So there is nothing to wire, and no A/B to run — before equals after by
construction.** The 11-work baseline run of this round (§4's OFF arm) is the
verification run: its Mahler export carries the 6 accents, and
`export_coverage --all` over it reports no `accent` gap. Redoing the wiring
was explicitly declined; what this round contributes instead:

- **CLAUDE.md corrected** (the OMR-NED section's KNOWN_GAPS sentence now names
  hairpins as the one open item and records how the accents copy went stale);
- **the design doc's §5 accents row corrected in place**, dated, so the third
  session to read it does not cut the same work order;
- **`test_lilypond_accent` added** — the one genuinely unpinned half-link
  (MusicXML accent emission was tested; LilyPond `->` was not, for any test
  naming accent).

The shape of the failure is worth the entry it now has in CLAUDE.md: the
project's recurring bug is "detected, then dropped on the way out", and this
is its documentation dual — **fixed, then kept open in the prose**. A stale
"open" claim costs a session the way a stale figure does, which is exactly
why the OMR-NED figure lives in one generated block. Gap ordinals already
live in one place (`export_coverage.py`, numbered, with closing commits);
what failed here is the two prose restatements outside it.

## 2. Task B: the tie/slur impossible-configuration veto (`OMR_ARC_RECLASS`, default OFF)

A tie and a slur are the same drawn arc; the notes under its ends tell them
apart (`docs/position-grammar-confusables-2026-09-04.md` §2 ARC). The veto,
R3-shaped — veto the impossible, reclass only when decisive, abstain
otherwise — lives entirely at EXPORT time in `export._pair_slurs_in_run`,
behind `OMR_ARC_RECLASS` (env, default off):

- **slur → tie**: a merged slur arc covering **exactly two heads, adjacent
  events of one voice, one pitch** becomes a tie (flags set on the pair; the
  merge matters — the canonical tie crosses a barline and arrives as two
  fragments). Adjacency counts REST events (a tie cannot cross a rest), so a
  same-pitch pair with a rest between abstains. Chords defend themselves:
  a covered chord member drags its mates into the covered set (same x) and
  the count passes two.
- **tie → slur**: a tie arc is refuted by its own configuration. Its pair is
  re-derived by `_tie_flank_pair` — a mirror of
  `transcribe._pair_ties_in_staff`'s pairing relation, pinned against the
  original by test — and vetoed where the pair's **pitches differ** or a
  **third event of the pair's voice sits under the arc's span**. An arc that
  never paired (no exported tie today) is reclassed only where decisively
  slur-shaped: >2 events of one voice under its span, or exactly two heads of
  different pitches. A vetoed arc joins the slur pool — **widened to the
  flanked centres and split at cell boundaries**, because a tie arc spans the
  GAP between its heads and slur coverage asks what sits under the ink;
  moved unchanged it covers nothing and "corrected to a slur" silently
  degrades to a bare deletion (found on the first smoke run: Mahler's two
  vetoed ties produced zero slurs until the widening).
- **bookkeeping**: every flag the pass adds or removes is recorded
  (`arc_reclass_added` / `arc_reclass_removed`) and the next annotate pass
  restores the transcription's own state before re-deriving — so one result
  dict exports identically under either flag in either order, and re-export
  is idempotent. Firings are counted per rule in `export.ARC_RECLASS_STATS`.

What it deliberately does NOT do: create ties the pairing never made (a
same-pitch pair under an unpaired tie arc abstains — pairing-by-coverage
would be a new pathway, not a veto); touch flags beyond the vetoed arc's own
mirror pair (chained ties share heads); veto a flagged same-pitch pair with a
rest between (the task's two impossible configurations only — span and
pitch).

Unit tests: `test_export.py::TestArcReclassOff / TestSlurToTie / TestTieToSlur
/ TestArcReclassBookkeeping` — both veto directions, the abstain cases
(different pitch, three heads, rest between, legal tie, arc over nothing),
flag-off inertness, restore, idempotency, and the flank-pair mirror agreement.

## 3. Flag OFF is byte-identical

Verified three ways: (a) unit tests pin the off-path on the veto-triggering
fixtures; (b) exports of the stored 3-work-era transcriptions under this
tree's flag-off code are byte-equal to the base commit's exports (MusicXML
and LilyPond, checked before any benchmark ran); (c) §4's A/B asserts, per
work and per scan row, that the flag-off re-export is byte-equal to the
`.omr.musicxml` the baseline eval itself wrote.

## 4. Engraved 11-work A/B: neutral to the ratio, +2 edits — after the step-key correction the first cut demanded

Both arms score the SAME stored transcriptions (the flag is export-time), so
the OFF arm re-exports the baseline eval's own fixtures — asserted BYTE-EQUAL
to the `.omr.musicxml` that eval wrote, per work, all 11 — and the baseline
run itself reproduces the canonical figure to the digit (**0.1306 / 2745
edits over 10665 + 10361 symbols**, the CLAUDE.md block's own numbers), so
the comparison is anchored to the recorded benchmark, not to a private rerun.

**Pooled: 0.1306 / 2745 → 0.1306 / 2747 (+2 edits, ratio unchanged at four
decimals). 24 firings across 6 of 11 works; 5 works fire nothing and export
byte-identically.**

| work | OFF | ON | Δ edits | firings |
|---|--:|--:|--:|---|
| Beethoven 5 | 0.0595 / 77 | 0.0602 / 78 | +1 | unpaired_span 1 |
| Brahms 1 | 0.1196 / 494 | 0.1201 / 497 | +3 | unpaired_diff_pitch 4, unpaired_span 5, flagged_span 1, slur_to_tie 1 |
| Mahler 5 | 0.0272 / 52 | 0.0272 / 52 | 0 | — |
| Mozart 40 | 0.1772 / 273 | 0.1772 / 273 | 0 | — |
| Mozart 41 | 0.1447 / 425 | 0.1447 / 425 | 0 | flagged_diff_pitch 8 |
| Beethoven 3 | 0.1294 / 215 | 0.1282 / 213 | **−2** | flagged_diff_pitch 1 |
| Brahms 4 | 0.2238 / 419 | 0.2223 / 416 | **−3** | flagged_diff_pitch 1 |
| Dvorak 9 | 0.3380 / 239 | 0.3380 / 239 | 0 | — |
| Tchaikovsky 4 | 0.0580 / 90 | 0.0580 / 90 | 0 | — |
| Tchaikovsky 6 | 0.1916 / 274 | 0.1916 / 274 | 0 | — |
| Bruckner 5 | 0.0941 / 187 | 0.0956 / 190 | +3 | flagged_diff_pitch 1, unpaired_diff_pitch 1 |

**Every delta, justified:**

- **Mozart 41, 8 firings, Δ0 — and the most instructive row.** OFF exports
  9 ties against the truth's 1, and musicdiff charges 8 `wrong tie`. The
  veto removes exactly those 8 (all step-apart pairs, `F#5 → G5` across six
  staves — appoggiatura figures the detector classed as ties) and the tie
  channel lands exactly on the truth's count (9 → 1). The freed arcs become
  slurs, `wrong slur` 26 → 34: **musicdiff charges a wrong tie and a wrong
  slur identically, so the metric is indifferent to the correction** — the
  element inventory is what shows it (ties 9→1 against truth 1, slurs
  48→56 against truth 44).
- **Beethoven 3 (−2), Brahms 4 (−3)**: one step-apart flagged veto each; the
  freed arc becomes a slur the truth can pair better than the false tie.
- **Beethoven 5 (+1), Brahms 1 (+3), Bruckner (+3)**: the residual cost is
  the UNPAIRED family — tie-classed arcs that export nothing today, turned
  into slurs by their own span. On engraved pages, where tie pairing works
  well, an arc classed tie that failed to pair is usually detector junk, and
  a slur made from junk is a new charge (Beethoven 5: truth has 0 slurs, ON
  emits 1). Brahms 1's +3 nets its 9 junk-slur charges against the arcs
  that did bind real runs.

**The step-key correction, priced separately because the first cut shipped
without it and lost.** The veto as first written compared SPELLED pitches
and scored **0.1315 / 2766 (+21)**: every losing veto was a same-step pair
differing only in accidental — Mahler `F#4 → F4` / `D#5 → D5` broke that
work's only two ties, both truth-matched (+4 on a page with zero tie edits
before); Brahms 1 charged 8 more the same way (`C#5 → C5`, `A4 → Ab4`). The
mechanism is the accidental-EXPIRY artifact: the canonical tie crosses a
barline, the far head does not restate its accidental (the tie carries it),
and `pitch_resolver` spells that head from the key signature alone — so the
spelling disagreement is evidence about the resolver, not about the arc.
The veto now compares `_pitch_step` (letter + octave, the staff position),
the same key the pre-fill alignment moved to for the same reason; every
winning veto was step-apart and survives. The CONVERSION direction keeps
the strict full-pitch key: a slur over `F#4 → F4` is a chromatic-neighbour
slur, real music, and asserting tie-ness needs the stronger evidence.
`TestArcReclassStepKey` pins both halves of the asymmetry.

Element movement vs truth (ET-parsed, tie/slur starts): Beethoven 5 truth
16 ties/0 slurs, OFF 11/0 → ON 11/1; Brahms 1 truth 52/82, OFF 44/74 → ON
44/83; Mozart 41 truth 1/44, OFF 9/48 → ON 1/56; Beethoven 3 truth 3/3,
OFF 2/2 → ON 1/3; Brahms 4 truth 6/54, OFF 7/30 → ON 6/30; Bruckner truth
6/2, OFF 4/1 → ON 3/3.

## 5. Scan 10-row A/B: REFUSED — +130 edits, and the damage is one direction's

The OFF arm transcribed the ten pooled rows fresh in this worktree with the
pinned graft weights (`OMR_SCAN_EVAL_WEIGHTS=…hollow-graft-shift09-2026-09-04.pt`)
and reproduces the recorded production baseline to the digit: **0.8387 /
29082 edits over 19828 + 14847 symbols**. The ON arm re-exports the same
stored transcriptions (`ab_scan.py`; flag-off re-export asserted byte-equal
to the OFF arm's own musicxml on all ten rows) and scores through the same
`scan_eval.py --score-only` harness.

**Pooled: 0.8387 / 29082 → 0.8391 / 29212 (+130 edits). ~330 firings.**

| row | OFF | ON | Δ edits | dominant delta |
|---|--:|--:|--:|---|
| beethoven-984073-p1 | 0.7152 / 1286 | 0.7151 / 1285 | −1 | wrong note −1 |
| beethoven-984073-p2 | 0.8833 / 4449 | 0.8834 / 4453 | +4 | wrong slur +3 |
| beethoven-575951-p1 | 0.7626 / 1362 | 0.7633 / 1367 | +5 | measure ins/del +5 |
| beethoven-575951-p2 | 0.8770 / 4471 | 0.8776 / 4497 | +26 | wrong slur +19 |
| dvorak-405834-p5 | 0.4306 / 673 | 0.4335 / 681 | +8 | wrong slur +10 |
| dvorak-405834-p6 | 0.7279 / 2611 | 0.7303 / 2643 | +32 | wrong slur +41 |
| brahms-317803-p1 | 0.9192 / 3434 | 0.9185 / 3458 | +24 | wrong slur +18 |
| brahms-317803-p2 | 0.9459 / 6610 | 0.9460 / 6638 | +28 | wrong slur +30, wrong note +25 |
| mahler-local-p2 | 0.6882 / 1117 | 0.6882 / 1117 | 0 | — |
| mahler-local-p3 | 0.8873 / 3069 | 0.8871 / 3073 | +4 | wrong slur +6 |

**Element movement, the counts the task asked for** (`<tie>` elements
start+stop, matching the "420 of 805" framing; slur starts; ET-parsed):

|  | tie elements | slur starts |
|---|--:|--:|
| truth (10 rows) | **805** | **195** |
| OFF (graft baseline) | 420 | 138 |
| ON (full veto) | **182** | **395** |

The veto guts the tie channel and floods the slur channel to twice the
truth. The sharpest single row: `brahms-317803-p2`, whose OFF tie export is
nearly PERFECT as an inventory — 192 tie elements against the truth's 194 —
and the veto slashes it to 87, firing `flagged_diff_pitch` 56 times on one
page. On a scan the resolved pitch of a flanked pair is downstream of
exactly what scans get wrong (`wrong note` is 26% of this pool's edits), so
a step-level disagreement between two tie endpoints is usually a
RESOLUTION error, not a slur — the veto inherits the pitch error and
converts it into a structure error. The doc's own counterweight, measured:
*"grammar needs anchors — anchor recall is the foundation the grammar
multiplies; it cannot replace it"* (R4). The step-key correction that
neutralised the engraved side (§4) cannot help here, because scan pitch
errors are step-level, not spelling-level.

**Attribution — the damage is entirely one direction's**
(`probe_scan_directions.py`, each direction neutered in turn on the same
stored transcriptions):

| arm | pooled edits | tie elements | slur starts |
|---|--:|--:|--:|
| OFF | 29082 | 420 | 138 |
| slur→tie only | **29082** | **462** | 115 |
| tie→slur only | 29213 | 138 | 418 |
| full veto | 29212 | 182 | 395 |

The **slur→tie** direction (23 conversions) is EDIT-FREE on the metric and
moves the tie inventory toward the truth (420 → 462 of 805) — the
duration-semantic default costing nothing. The **tie→slur** direction
carries all +130, in both its families: `flagged_diff_pitch` breaks real
ties on misread pitches, and the `unpaired_*` rules turn junk tie
detections into junk slurs (`wrong slur` + at every firing row; on the
engraved side the same family is the whole +7 residual).

## 6. Verdict, and what would change it

**`OMR_ARC_RECLASS` ships DEFAULT OFF, and stays off** — a priced refusal
of the R3 kind: the veto-the-impossible shape is right, but its evidence
(the pipeline's own resolved pitches and event structure at the two ends of
an arc) is not yet trustworthy enough to act on where it matters. Engraved:
neutral (+2 edits, and only after the step-key correction — the naive
spelled-pitch key cost +21 by breaking truth-matched ties on the
accidental-expiry artifact). Scan: refused outright (+130, tie channel
420 → 182 of 805).

What the measurements say WOULD earn a default, in order:

1. **The slur→tie half alone** is already free on both families and
   tie-positive on scans (462 vs 420 of 805, engraved 1 firing). If any
   part of this defaults on, it is that half, gated by the same strict
   full-pitch + adjacency + single-voice test it has now. Not done here:
   the charter asked for the two-direction veto as specified, measured as
   a unit, and no default flips without Sean.
2. **The tie→slur half is blocked on anchors, not on grammar** — the exact
   R4 ordering. When scan pitch resolution improves (the head-graft arc is
   already moving it), the same probe re-prices it in minutes:
   `ab_scan.py` + `probe_scan_directions.py` on any newer transcription
   set.
3. The `unpaired_*` sub-rules could plausibly gate on arc size or
   confidence, but that is threshold-tuning on the family this benchmark
   already scores — R6 says a sweep corpus per edition first, and nothing
   here needed it yet.

Everything in this round is export-time and flag-gated; with the flag off
every export in both families is byte-identical to its baseline, asserted
per work and per row on every A/B run in this document.
