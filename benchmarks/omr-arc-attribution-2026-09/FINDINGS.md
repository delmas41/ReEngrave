# Cross-staff ARC attribution — the arbitration noteheads already had (2026-09-04)

The beam-gap session (`benchmarks/omr-beam-gap-2026-09/FINDINGS.md`) closed the
`wrong flag/beam` bucket and left one seed: on `brahms-sym1-mvt1` its beam edits
fell 154 → 6 while `entire measure insert/delete` rose 7 → 156, because the
Timpani's now beam-perfect bars carry **four spurious slurs and one spurious tie**
and a bar differing only by an arc loses its diagonal pairing to an exact-equal
bar elsewhere in the part. This benchmark attributes those arcs and lands the fix.

**Headline: pooled OMR-NED 0.1176 / 2,473 edits → `0.1127` / `2,371`,
Brahms 1 490 → 390. No work gets worse.**

⚠️ These figures are recorded HERE ONLY. `current-accuracy.json`, the CLAUDE.md
OMR-NED block and `--record` are untouched by this session — the branch is not
merged, and the headline is a property of the tree that carries it.

Both bases agree to the edit. The fast loop below is a re-export of the
recorded `.omr.json` fixtures; a full
`orchestral_eval --omr-ned --work-dir …` run on this tree independently reports
**0.1127, 2,371 edits over 10,665 truth + 10,373 predicted symbols**, with
every work's per-row edit count identical to the re-export basis and every
work's note recall, precision and duration rate **unchanged from the baseline
table** — the pass touches no notehead, and two independent measurements say
so. Pooled slur count
199 → 207 against a truth of 241, so the gain is not the metric's
under-prediction reward: the arm that scores best is also the arm that emits
MORE arcs, and the right ones.

## Method

Export-only, so the A/B is re-export + re-score of the recorded `.omr.json`
fixtures with no YOLO rerun (`reexport_and_score.sh`, the beam-gap session's
loop pointed at this tree). Two controls before any conclusion:

* the unmodified tree re-exports to **exactly** the recorded per-work costs
  (`ops-baseline`: 215 / 43 / 490 / 401 / 185 / 239 / 42 / 218 / 301 / 69 / 270,
  pooled 2,473 — the beam-gap table to the edit);
* with `OMR_ARC_ATTRIBUTION=off` the eleven exports are **byte-identical** to
  that baseline (`diff -rq pred-baseline pred-offcheck`), so the flag-off path
  is provably the old code.

## Attribution: what the four arcs actually are

⚠️ **The beam-gap findings' guess was wrong, and the correction matters for the
fix.** It recorded them as "the staff BELOW's arcs, caught in the cell's
padding". Rendering the page region (`crop.py`, page px 2780,7040–4200,7800)
shows something else: **Violin 1 plays four ledger lines above its own staff
there, so ITS slurs and ties are drawn high in the gap between Timpani and
Violin 1** — the arcs are the lower staff's, drawn in the upper staff's
neighbourhood because that is where the notes they bind are printed.

That distinction is the whole reason a duplicate-resolution rule cannot fix
this. The measured geometry, `brahms-sym1-mvt1` system 0:

| | page y |
|---|---|
| Timpani staff, top → bottom line | 7093 → 7259 |
| the disputed arcs | 7272 → 7460 |
| Violin 1's ledger noteheads | ~7300 → 7400 |
| Violin 1 staff, top line | 7580 |

The Timpani–Violin 1 gap is 321 px = **7.7 staff spaces**, past the 6-space
threshold at which `measure_extractor` grows the cell pad, so the Timpani's
cell reaches down to ~7508 and swallows the arcs, while Violin 1's own cell
starts at ~7336 and **does not contain most of them at all**. So the arc exists
only in the wrong staff: there is no duplicate to arbitrate between, and
`transcribe._dedupe_cross_staff_detections` (which handles the noteheads) has
nothing to work on.

Per-part arc counts, `brahms-sym1-mvt1`, prediction against truth:

| part | baseline | truth |
|---|--:|--:|
| Timpani | **4 slurs, 1 tie** | **0, 0** |
| Violin 1 | 2 slurs | 5 |
| Contrabassoon (staff 8) | 0 slurs | 7 |
| Flute 2 | 2 slurs | 6 |
| whole work | 74 slurs | 82 |

The Timpani is where it costs, because `dump_ops` puts **149 of the work's 156
`entire measure` edits on that one part**.

## The evidence, and why distance to the staff is the wrong axis

An arc binds a run of noteheads and is drawn just clear of them, on the side
away from the stems. So the staff an arc belongs to is **the one whose
noteheads it hugs** — and that question can be asked of a staff that never
detected the arc, because the noteheads have already been arbitrated across
staves and each staff's head set is the one a reader would see.

Distance to the staff LINES is the same trap it was for notes (CLAUDE.md,
cross-staff notes): an engraver opens the gap above a staff precisely so its
ledger notes and their slurs can live there, which puts them nearer the staff
above. Four of the Timpani's arcs sit 1.1–3.3 spaces below the Timpani's bottom
line, which is exactly where a real slur under a staff would sit.

Clearance in staff spaces from an arc's box to the nearest notehead it covers
**in its own staff**, pooled over the eleven works, counting only arcs covering
>= 2 heads (fewer never becomes a slur) — `populations_owner.py`:

| own clearance | part whose truth has NO arc | part whose truth has arcs |
|---|--:|--:|
| [0.00, 0.25) | 5 | 165 |
| [0.25, 0.50) | 0 | 31 |
| [0.50, 0.75) | 1 | 8 |
| [0.75, 1.00) | 1 | 0 |
| [1.00, 1.50) | 2 | 1 |
| [1.50, 2.00) | 0 | 2 |
| [2.00, 3.00) | 6 | 0 |
| [3.00, inf) | 2 | 30 |

A real slur hugs its notes — **204 of 237 arcs on arc-bearing parts sit under
half a space**. But that tail is not clean enough to threshold on: 33 arcs on
arc-bearing parts sit above 0.5, and an absolute rule would have to guess about
them. ⚠️ **So the rule is COMPARATIVE, not absolute** — an arc leaves a staff
only when another staff of the same system explains it better. That is the same
shape as the notehead arbitration, and it cannot fire at all on a single-staff
page.

`OMR_ARC_ATTRIBUTION` (default `move`) in `export.arbitrate_arcs_across_staves`,
run once per export over each page's systems:

> An arc moves to the staff of its system whose noteheads it hugs, when that
> staff hugs it within `_ARC_RIVAL_NEAR_SPACES` (0.75), covers at least
> `_ARC_RIVAL_MIN_COVERED` (2) of its own heads with it, and beats the
> incumbent by `_ARC_RIVAL_MARGIN_SPACES` (0.5). An arc covering nothing in its
> current staff is claimed outright — it binds no note there, so there is
> nothing for it to be.

On the Brahms Timpani every one of the four slurs reads own 1.3–3.3 against a
Violin 1 reading of **0.00–0.52**. Decisive by an order of magnitude.

### Both constants are plateaus, not tuned values

`populations_owner.py`'s sweep, in reattributed arcs (silent-part / arc-bearing):

| margin \ near | 0.50 | 0.75 | 1.00 | 1.50 |
|---|---|---|---|---|
| 0.25 | 7/14 | **8/15** | 8/17 | 8/17 |
| 0.40 | 7/14 | **8/15** | 8/17 | 8/17 |
| 0.50 | 7/14 | **8/15** | 8/17 | 8/17 |
| 0.60 | 7/14 | **8/15** | 8/17 | 8/17 |
| 0.75 | 7/14 | **8/15** | 8/17 | 8/17 |
| 0.90 | 7/14 | 7/15 | 7/17 | 7/17 |
| 1.00 | 7/14 | 7/15 | 7/17 | 7/17 |

Every margin from **0.25 to 0.75 reattributes the identical set**; the answer
first moves at 0.90. 0.5 is the middle of that plateau. And `near` 0.75 and 1.00
score **identically end to end** (2,371 both), the second plateau.

## Arms, measured

| arm | pooled edits | Brahms 1 | pooled slurs emitted | note |
|---|--:|--:|--:|---|
| baseline | 2,473 | 490 | 199 | |
| **drop** (remove, don't regift) | 2,388 | 408 | **183** | REFUSED — see below |
| move, margin 1.0 | 2,411 | 429 | 207 | superseded |
| **shipped: move, margin 0.5, near 0.75** | **2,371** | **390** | **207** | |
| move, margin 0.5, near 1.0 | 2,371 | 390 | 207 | identical; plateau |

Truth: 241 slurs.

### ⚠️ The `drop` arm is refused, and it is the interesting refusal

Deleting a mis-attributed arc instead of regifting it scores **2,388 against the
move arm's 2,411 at the same margin** — better, on the arm-for-arm comparison —
and it is wrong. It gets there by emitting **20 fewer slurs, at least 12 of them
real**: on Brahms 1 it leaves Contrabassoon at 0 (truth 7), Flute 2 at 2
(truth 6) and Violin 1 at 2 (truth 5), where moving takes them to 7, 5 and 6.
Pooled slurs 199 → **183** against a truth of 241.

This is the metric's symmetry rewarding under-prediction, the trap CLAUDE.md
names beside OMR-NED, seen from the other side: a bar that loses a spurious arc
pairs exactly, and so does a bar that loses a real one. The control that
separates them is the arc COUNT against the truth (`arc_totals.py`), which is
why it is run on every arm and printed above. Once the margin is set from the
population sweep rather than from the score, the shipped arm wins outright
(2,371 vs 2,388) — but the count control is what makes that a decision rather
than a coincidence.

`mozart-sym41-mvt1` is the one work where the drop arm still scores better
(298 vs 301): it over-predicts slurs 48 against a truth of 44, and dropping 3
of them helps while moving them keeps the count. Recorded rather than chased —
3 edits, and the fix for an over-count is detection, not attribution.

## Per-work deltas (re-export basis, baseline → shipped)

| work | edits | slurs emitted | truth slurs |
|---|--:|--:|--:|
| beethoven-sym3-mvt1 | 215 → 215 | 2 → 2 | 3 |
| beethoven-sym5-mvt1 | 43 → 43 | 0 → 0 | 0 |
| **brahms-sym1-mvt1** | **490 → 390** | 74 → 81 | 82 |
| brahms-sym4-mvt1 | 401 → 400 | 30 → 30 | 54 |
| bruckner-sym5-mvt1 | 185 → 185 | 1 → 1 | 2 |
| dvorak-sym9-mvt4 | 239 → 239 | 16 → 16 | 20 |
| mahler-sym5-mvt1 | 42 → 42 | 0 → 0 | 0 |
| mozart-sym40-mvt1 | 218 → 218 | 19 → 19 | 20 |
| mozart-sym41-mvt1 | 301 → 301 | 48 → 48 | 44 |
| tchaikovsky-sym4-mvt2 | 69 → 69 | 0 → 0 | 0 |
| tchaikovsky-sym6-mvt2 | 270 → 269 | 9 → 10 | 16 |
| **pooled** | **2,473 → 2,371** | 199 → 207 | 241 |

Categories: `entire measure insert/delete` 428 → 356, `wrong other object`
527 → 499, `wrong flag/beam` 31 → 29. Every other bucket byte-identical,
including `wrong note` at 1,258 — the pass touches no notehead, and the
benchmark says so.

On Brahms 1 the Timpani's own charge falls **149 → 75** and its slur count
**4 → 0** against a truth of 0. The 75 that remain are a single spurious tie at
detector confidence **0.29**, whose nearest notehead really is the Timpani's own
(clearance 0.82 spaces against Violin 1's 2.50) — a false detection, not a
mis-attribution, and correctly left alone.

## The scan side: unchanged to the edit

Arcs on scans are where a too-aggressive drop would cost real slurs, so both
rows of `brahms-sym1-mvt1-317803` were run through `scan_eval.py` — one YOLO
pass, two exports (`scan_reexport.py`), since the change is export-only.

| row | attribution off | attribution on | arcs reattributed |
|---|--:|--:|--:|
| `...-p1` | 0.9184 / 3,431 | 0.9184 / 3,431 | 5 |
| `...-p2` | 0.9424 / 6,562 | 0.9424 / 6,562 | 18 |
| pooled (2 pages) | **0.9340 / 9,993** | **0.9340 / 9,993** | 23 |

Identical to the edit, and the exports genuinely differ (84 and 6 changed
lines), so this is a real null rather than a mis-run. ⚠️ **A null here is not
evidence that the rule works on scans**, only that it does not regress them:
these pages read 8 measures against a truth window of 7 and 15, spend 49.9% of
their budget on `entire measure` and 17.2% on `entire staff`, and at that level
of structural failure an arc landing on the right staff cannot reach the score.

## The `wrong tie` bucket, attributed but not fixed

Unchanged at 28 across every arm — `transcribe._pair_ties_in_staff` is a
separate pairing implementation and the tie flags are baked into the
`.omr.json`, so no export-side change can move them. Opened anyway, and it is
**two clusters, neither of them cross-staff attribution**:

* **12 of the 18 `tieins` are the EXCERPT BOUNDARY, not a defect.** They sit in
  the excerpt's last bar, where the truth carries a `<tied type="start"/>` whose
  partner is in the bar after the window: Beethoven 5 has 5 of them at m8 of 8
  (verified — Bassoon 1's m8 `start` has no `stop` anywhere in the file, while
  its m7→m8 pair is read correctly and charged nothing), Beethoven 3 2 at m7–m8
  of 8, Brahms 1 5 at m7 of 7. A perfect reader scores these edits too. Same
  family as the fermata render floor CLAUDE.md documents.
* **8 of the 10 `tiedel` are one system-wide invention**: `mozart-sym41-mvt1`
  m5 (not the last bar), eight parts at once — Flauto, Oboe I/II, Fagotto I/II,
  Viola, Violoncello — every one with the identical event signature. One arc
  read as a tie across a whole system. That is a real defect, it lives upstream
  in tie pairing, and pricing it needs a YOLO rerun. Left open with its
  coordinates rather than guessed at.

## Tools

| file | what it answers |
|---|---|
| `probe_arcs.py` | every arc per staff: coverage in its own staff, cross-staff duplicates |
| `probe_arc_dy.py` | the clearance from an arc to the notes it claims to bind |
| `probe_owner.py` | which staff of the system hugs each arc best |
| `populations.py` / `populations_owner.py` | the pooled distributions and the constant sweep |
| `count_arcs_xml.py` / `arc_totals.py` | per-part and per-work arc counts vs the truth |
| `crop.py` | render a page-pixel region of a fixture PDF — how the guess got corrected |
| `reexport_and_score.sh` / `tab.py` | the A/B loop and its table |
| `scan_reexport.py` | re-export a cached scan-e2e transcription under a new tag |

Pinned by `TestArcAttribution` in `tools/omr/tests/test_export.py` (9 tests:
the bled-arc move, the arc that stays, the photo-finish refusal, one-staff
systems, flag-off, drop mode, idempotence, the moved arc pairing on its new
staff, and the lone-rival-head floor). Full suite green: 1,989 passed,
8 skipped.
