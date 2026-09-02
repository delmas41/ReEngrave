# Phase 1 — positive system-START detector: results

2026-09-01 (Opus). Measurement-first prototype. **No live pipeline edits** —
everything here is in `fix/`, importing `tools.omr` read-only.

## Verdict

**A positive left-anchored start-detector CLEARS THE BAR.** The winning cue is
**not** either of the two the plan named (clef-header column, bracket restart) —
both were built and measured and both fail. The cue that works emerged from
characterising the over-merges directly (task step 5): **systemic-barline-column
continuity** — count crossing ink in a narrow band at the shared left edge; a
system boundary is where that column is empty even though the wide-window rule
saw bridging.

| metric | result |
|---|--:|
| original FAILURES fixed | **2 / 3** (B9 p60, B5 p40; B9 p25 missed) |
| discovered instrumental over-merges also fixed | **+1** (Beethoven 3 *Eroica* p36) |
| genuine CONTROLS regressed | **0 / 37** |
| robustness | 45/45 param settings with band right-edge R≥3sp clear the bar; only R=2sp (too narrow) regresses |
| DPI | holds at both 300 and 600 dpi |

The bar was: fix ≥2/3 failures AND regress 0 controls. **Met** (2/3 + 0), and the
detector generalised to a **third instrumental over-merge** on a different
symphony that was hiding inside the control set as a "dense single-system page".

## Why each over-merge over-merged (step 5, the characterisation)

Cropping the true-break gap on each failure (`crops/*_break_*.png`) and profiling
where the "bridging" ink actually sits (`characterize_gaps.py`, `profile_left.py`)
gives one mechanism for all three:

> The wide-window connectivity rule counts crossing ink over
> `[median x_start − 4sp, median x_end + 4sp]` — essentially the whole staff
> width. At a real system boundary there is **no systemic barline** crossing the
> gap, but there IS music ink (note stems, an `a 2.` marking, ottava `8·····`
> dots, a measure number, a brace curve). That music ink, out in the staff body,
> is counted as "bridging" and fakes a connection.

Per true break, splitting the crossing columns by x-position relative to
`x_start` (in staff-spaces):

| failure | true break | wide bridging | at the left edge (systemic barline) | out in the music |
|---|--:|--:|--:|--:|
| B9 p25 | gap 11 | 66 | 4 (a brace, +1.2–1.4sp) | 62 |
| B9 p60 | gap 11 | 324 | **0** | 324 |
| B5 p40 | gap 6 / 13 | 3 / 11 | **0 / 0** | 3 / 11 |

The new system visibly starts with an instrument label + fresh clef and **no left
rule crossing** (`crops/B9-p60_break_gap11.png`: "Fl." + treble clef below the
boundary, nothing at the blue `x_start` line; `crops/B5-p40_break_gap6.png`:
"Cl." + clef + measure number 243). So the medicine is a **left-anchored** test,
not a wider or narrower version of the whole-width count. This is exactly
publisher-conventions.md's #1 ranked feature (systemic-barline continuity scanned
in a narrow band at the shared left edge) and Audiveris's privileged "start
column".

## The detector (`system_start_detector.py`, scored by `score.py`)

Three cues were implemented. Only cue A survives.

### Cue A — systemic / leftmost-barline column continuity  ✅ WINNER
For each gap *i*, count the columns that are ≥80 %-inked over the gap band, within
`[x_start − L·sp, x_start + R·sp]`, after the same vertical closing the live rule
uses. Call gap *i* **barline-crossed** if that count ≥ `min_cross`.

- **Constructive splitter:** predict a break at every candidate gap whose count is
  **below `min_cross`** (the left column is empty). Union with the existing rule's
  breaks — it can only ADD a split, never merge (matches the Phase-2 contract).
- **Per-page gate:** only trust the cue if a fraction ≥ `gate_frac` of interior
  candidate gaps are barline-crossed — i.e. the page actually uses a continuous
  left barline. (Not load-bearing on this corpus once the band is wide enough; see
  below. Kept as insurance for degraded multi-system scans.)

**The one parameter that matters is `R` (how far right the band reaches).** The
systemic barline sits at a *different* x-offset from `x_start` per edition:
~0sp on Beethoven/B5, but **+1.4–3sp on La Mer**, +1.2–1.4sp on Boléro (measured
in `profile_left.py`) — because `x_start` is "after the clef margin" and the
leftmost measure barline is what the band must reach. A band that stops at +2sp
misses La Mer's barline and false-splits it; **R ≥ 3sp catches every edition's
leftmost barline** and the result is flat thereafter.

Recommended operating point: **L=2.0, R=4.5, min_cross=1, gate_frac=0.7**.

### Cue B — clef-header column  ❌
Per-staff clef-sized cluster just right of `x_start`. Measured
(`measure_cues_BC.py`): **99 % of all staves carry a header cluster**, and a
cluster is present on **both** sides of **37/37 true-break gaps and 725/747
interior gaps**. Every staff of both stacked systems shares the same header x, so
clef presence is uniform and **cannot locate a stacked-system boundary**. (It
would only help a side-by-side multi-column layout, already handled by
`x_overlap`.)

### Cue C — left-margin bracket restart  ❌
Bracket ink crossing a gap left of `x_start`. Measured: true breaks max=0,
interior **min=0** (p50=0, max=10). Brackets are **per-family**, so they cross
neither a family boundary nor a system boundary → 0 at both. This reproduces
**attempt 4** in RULE_FIX_ATTEMPT_2026-08-31.md exactly ("perfect recall, no
precision"). Useless as a standalone splitter; adds nothing to cue A (both read
0 at a break).

### Combination / the relative variant  ❌ (the trap)
A per-page **relative** form of cue A — break where `cueA[i] ≤ frac · p75(page)` —
does reach **3/3** (it catches B9 p25, whose gap-11 reads 4 against neighbours of
18–19). But across every setting tried it **regresses 7–15 controls**, always
including Mahler5 p2/p10/p20 and La Mer p20: single-system pages whose systemic
barline is genuinely broken at some interior gaps read "anomalously low" and get
split. This is precisely how the 5 prior attempts died, so it is **rejected**. The
absolute "empty-left" condition is strictly safer and is what holds the controls.

## Full confusion matrix (recommended params; `PHASE1_confusion.txt`)

3 failures + 37 controls + 2 adjudicated dense-single pages = 42 pages.

| bucket | n | detector result |
|---|--:|---|
| **failures fixed** | 2 | B9 p60 → [12,12]; B5 p40 → [7,7,7] |
| failure missed | 1 | B9 p25 (brace at the true break — see below) |
| **discovered instrumental over-merge fixed** | 1 | Eroica p36 → [11,11] |
| discovered vocal over-merge missed | 1 | Matthäuspassion p302 (Phase-3 scope) |
| **controls regressed** | **0** | — |
| controls kept | 37 | all eval + fulldist + phase1 + 14 sweep pages unchanged |

Control set (all kept, detector fired nothing on any of them):
- 20 `eval_grouping.py` non-failure cases (B9 p20/30/35/40/45/50/55/65/70/75,
  B5 p10@300, B5 p10@600, Mahler5 p2/p10/p20, La Mer p2/p20, Boléro p2/p10/p20).
- fulldist-only: B5 p47.
- phase1-baseline: wtc-p5 `[2,2,2,2,2]`, lamer-p25 `[21]` (beet5-p10 `[11,11]` ==
  B5 p10@600).
- 14 clean sweep pages across **Eulenburg, Peters, Breitkopf, Simrock, Litolff,
  Arthur P. Schmidt** / Bach (Brandenburg ×5, Mass, Orchestral Suite), Beethoven
  (Egmont, Piano Concerto ×3, Coriolan), Beach — chosen because equal-size stacked
  systems (`[7,7,7]`, `[11,11]`, …) or a uniform-gap dense single system are the
  safest presumed-correct grouping (see `pick_sweep.py`). Detector added 0 breaks.

### B9 p25 — the one failure cue A misses, honestly
Its true break (gap 11) carries a **brace** on system 2's first staves at +1.2–1.4
staff-spaces from `x_start` — the *same* relative-x band as La Mer's real leftmost
barline. So no fixed band width can admit La Mer's barline while excluding B9 p25's
brace. A brace is curved (≤0.5–0.7 column coverage per publisher-conventions), so a
**curvature / solidity discriminator** is the principled way to separate them — but
it must be validated on both editions before use, not tuned on this one page.

### Method finding — dense single-system pages are NOT safely presumed correct
Two of four "dense single-system" sweep pages I picked as controls turned out to
be **over-merges** (an over-merge *looks* like a legit dense single system — the
DIAGNOSIS predicted this). Eroica p36 (`[22]` → truly `[11,11]`, gap-10 is 140px
vs 71px median) the detector **correctly fixed**; Matthäuspassion p302 (`[16]` →
truly `[8,8]`, vocal) it missed. Both adjudicated by eye (`crops/ADJ_*_thumb.png`).
The equal-size **multi-system** presumption is safe; the dense-single one is not.
Only pages where the detector actually *fired* can create a regression, and it
fired on exactly one control — Eroica p36 — which is a correct fix.

## Recommendation for Phase 2

1. **Integrate cue A** (systemic / leftmost-barline column continuity) as the
   constructive splitter, behind a flag, with **L=2.0, R=4.5sp, min_cross=1**. It
   is a ~15-line addition next to `gap_bridging_counts`: same band machinery, just
   anchored narrowly at `median(x_start)` and reaching R·sp right, and it only
   ADDS a break where the left column is empty. Union with the existing rule.
   - Expected effect on the sweep harness: fixes the 3 known over-merges' class
     (2 of the 3 GT pages + Eroica p36), 0 fragmentation added, 20/23
     `eval_grouping` stays ≥20/23 (it becomes 22/23: +B9 p60, +B5 p40).
2. **Keep the per-page gate** as insurance even though it is inactive here — a
   badly degraded *multi-system* scan (broken interior barlines) is the one case
   the wide band alone would over-split, and my corpus has no such page to prove
   it either way.
3. **Drop cues B and C.** Measured dead (uniform / no precision). Don't spend
   Phase-2 effort on a bracket detector for the over-merge problem — it cannot
   separate a family boundary from a system boundary.
4. **B9 p25 and the vocal over-split family are the remaining work.** B9 p25 needs
   a brace-vs-barline **curvature** test (Phase 2, guarded). Vocal/choral
   over-*splits* (Matthäuspassion, and the DIAGNOSIS's Bruckner/Mozart cases) are
   a different direction entirely and remain **Phase 3** — cue A does not help
   where the barline is conventionally absent.

## Files (`fix/`)
- `system_start_detector.py` — the three cue implementations.
- `score.py` — end-to-end scorer (union semantics), `--grid`, relative-variant.
- `_harness.py` — the 42-page set with adjudicated GT + render/detect cache.
- `characterize_gaps.py`, `profile_left.py`, `inspect_fp_gaps.py` — step-5
  measurements.
- `measure_cues.py`, `measure_cues_BC.py` — cue separation measurements.
- `pick_sweep.py` → `sweep_controls.py` — the sweep control picks.
- `PHASE1_confusion.txt` — the scored table.
- `crops/` — break crops, FP-risk interior-gap crops, adjudication thumbnails.
