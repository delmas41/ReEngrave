# Choir-grouped system layouts — why the Bach Brandenburg 3 page shatters, and a flag-gated candidate

2026-09-04, branch `claude/bach-choir-grouping` (off `0487be1f`). The scan
benchmark's stress row (`bach-brandenburg3-mvt1-468678-p1`, works.json
`pooled: false`) reads a true 2-systems-of-12 page as **6 "systems"**
(12 / 3 / 3 / 3 / 1 / 2) and **122 measure-cells against a true 10** —
OMR-NED 0.9241 / 6735 edits on the graft weights
(WIDENED_BASELINE_2026-09-04.md). Structural charges are the row's whole
score, and the fragments align exactly with the instrument choirs
(3 Violini / 3 Viole / 3 Violoncelli / Contrabasso / Cembalo pair), so the
question this benchmark answers: **is this a layout family the grouping rule
does not understand, and what exactly fails?**

Everything below is measured on the actual page ink
(`probe_bach_gaps.py` → `probe_bach_gaps.json`; page rendered at the
pipeline's own 600 dpi, 4682×6554, 24 staves found, spacing median 22.75 px —
"sp" below means staff spaces).

## Phase 1 — diagnosis

### 1. The engraving really is choir-barred: interior barlines stop at choir edges

Full-width crossing profiles (same 0.8-coverage test and 0.6 sp closing as
`gap_bridging_counts`, scanned over the whole page width) per adjacent-staff
gap. Interior barlines live at x ≈ 1170 / 1985 / 2795 / 3605 / 4460
(system 1) and ≈ 1160 / 1980 / 2790 / 3620 / 4458 (system 2):

| gap | pair | kind | interior-barline columns crossing? | what crosses instead |
|---|---|---|---|---|
| 2 | Vni III → Vle I (sys 1) | choir edge | **none** | left-edge complex only (x 816–845) |
| 5 | Vle III → Vc I (sys 1) | choir edge | **none** | x 812–843 |
| 8 | Vc III → Cb (sys 1) | choir edge | **none** | x 814–841 |
| 9 | Cb → Cembalo RH (sys 1) | block edge | **none** | x 836–843 only (8 columns) |
| 14 | Vni III → Vle I (sys 2) | choir edge | **none** | x 198–227 (18 columns) |
| 17 | Vle III → Vc I (sys 2) | choir edge | **none** | x 196–225 (22) |
| 20 | Vc III → Cb (sys 2) | choir edge | **none** | x 198–225 (18) |
| 21 | Cb → Cembalo RH (sys 2) | block edge | **none** | x 222–227 only (6) |
| 12, 13, 15, 16, 18, 19, 22 | within-choir (sys 2) | — | **yes** (every bar position) | plus the left-edge complex |

So the layout convention is real: **this Peters engraving draws every
interior barline per choir** — through the three violins, through the three
violas, through the celli, through the Cembalo pair — and through nothing
between. Both systems are barred this way (system 1's choir gaps 2/5/8/9 have
no interior crossings either).

### 2. But the page still carries a system-spanning signal, at raw coverage 1.0

Zoomed inspection of the left edge (`bach_gap14_zoom` crop; raw per-column
coverage measured in the gap bands) — three vertical rules stand at the left
of every system, listed left → right with system-2 x-positions (system-1
counterparts in parentheses):

| rule | x (sys 2) | (sys 1) | spans |
|---|---|---|---|
| per-choir rule at the staff start | 182–187 | (798–803) | its own choir only |
| thick string-block bracket | 200–211 | (820–831) | Vni I through Cb — crosses the three choir gaps, stops at the Cembalo |
| thin **systemic barline** | 222–227 | (840–847) | **every gap of the system, Cb → Cembalo included** — raw coverage 0.95–1.00 |

The connectivity rule's premise — "every gap inside a system is crossed by
ink" — **holds on this page**. Nothing about choir-barring needed a new kind
of evidence.

### 3. What fails is the scan WINDOW: the page-median anchor on a bimodally-indented page

`_robust_x_window` anchors the wide scan window on the **median `x_start`
across the page's staves**, by design robust to single broken staves. This
page's `x_start`s are **bimodal**, not outlier-contaminated: system 1 is
indented for full instrument names (x_start 792–836, twelve staves), system 2
is full-width (178–200, twelve staves). The median, 450, lands in the empty
land between the modes, and the window becomes **[359, 4554]**:

- system 1's left-edge complex (798–847) is **inside** the window → its choir
  gaps read wide counts 20–68 (all of it left-complex columns) → **system 1
  held**;
- system 2's left-edge complex (178–227) is **outside** the window → its
  choir gaps read **wide = 0** → four breaks, exactly at gaps 14 / 17 / 20 /
  21 → **3 / 3 / 3 / 1 / 2**.

Per-gap evidence (`wide` = shipped `gap_bridging_counts`; `full` = same test
over the whole width):

```
[11] s11->s12  gap 9.4sp  wide=0  full=0    <- the TRUE system break: nothing crosses, anywhere
[14] s14->s15  gap 7.3sp  wide=0  full=18   <- bracket+barline cross at x 198-227, window starts at 359
[17] s17->s18  gap 7.3sp  wide=0  full=22
[20] s20->s21  gap 7.1sp  wide=0  full=18
[21] s21->s22  gap 9.2sp  wide=0  full=6    <- systemic barline only (the bracket stops at Cb)
```

Gap size confirms it cannot be the discriminator here (the design's original
point): the true break is 9.4 sp while *within-system* gaps run up to 9.3 sp
(sys 1 Cb→Cembalo) and 10.3 sp (the Cembalo pair's own internal gap, held
together by its own barlines).

**Cue A (`OMR_LEFT_EDGE_SPLIT`) is inert here, for the same root cause**: its
narrow band is anchored on the same poisoned median (band [404, 552] — empty
land), every gap reads left = 0, and its gate fails 0/18. It did not cause
the shatter; it also cannot see anything on this page.

Failure classification, in the assignment's terms: **(c)** — the choir-barred
convention is real (a layout family, not a freak), but the rule already owns
the right signal for it; the defect is the **page-global window anchor**,
which assumes indentation is unimodal. On pages whose interior barlines are
drawn through the whole system, a poisoned window is masked (interior
barlines sit mid-page, inside any window) — which is why the engraved
benchmark and the other ten scan rows never see this. The family that
shatters = choir-barred interior barlines × per-system indentation
difference. A fully choir-barred page with *uniform* indentation is fine
under the current rule (its left complex sits at the median).

### 4. The secondary failure: 122 measure-cells, mechanically

Once grouping broke, each fragment vets barline candidates on its own:

- **3-staff fragments** (Vni, Vle, Vc): vote threshold is n−1 = 2, and in
  this tutti the parts share one rhythm, so stem columns align across the
  fragment and pass the vote. None of them crosses the two inter-staff gaps,
  so `barlines_cross_gaps` reads `n_connected*2 >= len(vote_passed)` false →
  **open-score mode** (the adaptive rule for one-staff-per-voice engravings,
  measure_extractor.py) → the votes stand alone → every aligned stem column
  is a "barline". Measured widths of the resulting "bars" on staff 12:
  69–140 px ≈ one beat, against ~810 px true bars → **28 / 29 / 25** cells.
- **1-staff fragment** (Cb): `_intersystem_connectivity` returns 1.0 for
  single-staff systems by construction → vote-only → **24** cells.
- **2-staff fragment** (Cembalo): both staves must agree; **10** cells.
- The intact system 1 reads **6** (one spurious split at x=1518 inside
  printed bar 1 — a pre-existing, unrelated defect of the barline layer).

6+28+29+25+24+10 = **122**. No new mechanism: fragments lack the height that
makes the connectivity vet discriminate, which is the regime the vote tiers
were built for. Fixing the grouping fixes this wholesale.

### 5. What a candidate cue would see (measured on this page)

A **pair-local left band** — the cue-A band geometry
(−2.0 / +4.5 sp, the measured plateau for where the left-edge complex sits
relative to `x_start`) but anchored at `min(upper.x_start, lower.x_start)`
of the pair itself rather than the page median:

```
wrongly-broken gaps:  [14]=18  [17]=22  [20]=18  [21]=6   columns crossing
the true break:       [11]=0
```

Clean separation on this page, including the weakest rescue (the Cembalo
gap, whose only witness is the 6-px systemic barline). Fail-safe behavior
observed at gap 2 (sys 1): staff 2's `x_start` is broken leftward (700
against its neighbours' ~792), the anchor follows it, the band misses the
complex and reads 0 — which merely declines to rescue a gap that was never
broken. A mis-anchored band can only *fail to merge*, never split.

## Phase 2 — the candidate rule (`OMR_CHOIR_GROUPING`, default OFF)

**Cue B — pair-local left-edge merge**, `tools/omr/system_grouping.py`, the
mirror of cue A and additive in the opposite direction (merge-only, as cue A
is split-only):

> A gap the wide rule broke for lack of evidence (`bridging == 0`, x-overlap
> intact) is re-examined in a narrow band anchored at the PAIR's own shared
> left edge. If near-solid columns cross the whole gap there — the system
> bracket or systemic barline, the same physical objects cue A reads the
> absence of — the break is cancelled.

Design properties, in the house terms:

- **Union-only**: it can only merge gaps the wide rule broke; it cannot
  split, cannot touch multi-column breaks (x-overlap ≤ 0.5 is excluded),
  and a band that finds nothing changes nothing — flag ON is byte-identical
  on any page where it never fires.
- **Constants are inherited, not tuned**: the band geometry (−2.0/+4.5 sp)
  and the 0.8-coverage / 0.6-sp-closing test are cue A's, measured in
  `benchmarks/omr-system-grouping-2026-09/fix/PHASE1_RESULTS.md` (flat for
  RIGHT ≥ 3) — the same physical object measured from the other side. The
  min-crossing threshold is read off the probe population (below).
- **Order**: cue B runs before cue A, so cue A retains the last word on
  splits at the left edge where its gate passes — a wrong cue-B merge on a
  page with a healthy left-barline population is re-splittable by cue A.
- `bridging[]` is left untouched, so `_assign_groups` sees 0 at the merged
  gaps and marks them group boundaries — which is the true structure
  (choirs are bracket groups of one system).

Guard results land in this file as they are measured; nothing in this
section asserts an outcome that has not been run yet.

### Cue C — the merged system's stems, and the open-score flip

Cue B alone restores [12, 12] but the merged system 2 still read **14 bars
against 5**: in this rhythm-unison tutti, stem columns align across ≥8 of 12
staves and pass the vote, none of them connected, so
`detect_barlines`' open-score question — "are the vote-accepted columns
mostly connected?" — counts 9 unconnected stem columns against 6 true
barlines and flips the system into open-score mode, where votes stand alone
(measured x's: 625, 1332, 1417, 1693, 1786, 2414, 2951, 3135, 3229 accepted
beside the true 183 / 1163 / 1978 / 2791 / 3623 / 4457).

**Cue C** (same flag): the STAVES already answer the open-score question —
a system whose staves form ≥2 bracket-groups, at least half of them in
multi-staff groups, cannot be an open score, because `group_index` only
becomes non-trivial where cross-staff ink crosses some gaps and not others
(`_assign_groups`), which is exactly what an open score never has. For such
systems the connectivity filter keeps its role; thresholds and rescue are
untouched. The half-in-multi guard keeps true open-score pages (singleton
voices + a keyboard pair) in open-score mode. With B + C the page reads
**[6, 5] measures — system 2 exact**; the +1 in system 1 is the pre-existing
spurious split at x=1518 (§4).

## Measured results (2026-09-04, graft weights pinned via OMR_SCAN_EVAL_WEIGHTS)

### The Bach row, end to end (`results-bach-choiron.json` / `-choiroff.json`)

| arm | systems | page cells | OMR-NED | edits | pred | structure charges |
|---|---|--:|--:|--:|--:|--:|
| flag OFF | 6 | 122 | **0.9241** | 6735 | 3739 | 3077 measure + 1828 staff = 4905 |
| flag ON (B+C) | **2** | **11** | **0.8152** | **6236** | 4101 | 2079 measure + 286 staff = 2365 |

−0.1089 OMR-NED, −499 edits, structure charges −2540. `wrong note` rises
1679 → 3599: bars that used to be charged whole now pair and expose their
contents — the same shift the WTC part-stitching fix documented ("the metric
has stopped measuring the exporter and started measuring the reading").
The page total (11 cells vs true 10) crosses the row's stated re-admission
bar ("segmentation reads ~10 measures"); the residual +1 is §4's spurious
x=1518 split, present in both arms.

### Guard 2 — flag OFF is byte-identical

The flag-OFF arm on this branch **hash-matches the widened-graft baseline
fixture** produced on `claude/scan-rebaseline` (84a5ccac, an ancestor of
this branch's base with zero tools/omr changes between):
`sha256 936319bc…` for both `bach-…choiroff.omr.musicxml` and
`bach-…widened-graft.omr.musicxml`, and scores identically
(0.9241 / 6735). Full-pipeline byte-reproduction, across worktrees, YOLO +
OCR included — the flag default cannot have changed anything.

### Guard 3 — the ten pooled scan rows (`ab_structural_rows.py`)

The two cues are the only flag-dependent code and both act strictly upstream
(grouping; barline acceptance), so a row whose complete structural
fingerprint — system sizes, group indices, per-system barline x lists, every
cell's (system, staff, measure, bbox) — is identical under both flags
produces a byte-identical `.omr.json` by construction. Measured at the
protocol's 600 dpi:

```
beethoven-984073-p1  IDENTICAL [12]      192 cells     brahms-317803-p1  IDENTICAL [14]     112
beethoven-984073-p2  IDENTICAL [11,11]   341           brahms-317803-p2  IDENTICAL [14,13]  202
beethoven-575951-p1  IDENTICAL [12]      192           mahler-local-p2   IDENTICAL [19]     153
beethoven-575951-p2  IDENTICAL [11,11]   352           mahler-local-p3   IDENTICAL [15]     117
dvorak-405834-p5     IDENTICAL [15]      135           bach-468678-p1    DIFFERS 6→2 sys, 359→132 cells
dvorak-405834-p6     IDENTICAL [15]      105
```

**All ten pooled rows byte-identical flag-ON; the 10-row pooled figure is
untouched (0.8387 / 29082).** Bach is the only row the flag reaches, and it
moves to the truth.

### Guard 1 — test suite

1885 passed, 8 skipped, 1 failed: `test_mxl_verdicts.py::
test_windows_accept_the_scan_benchmark_file`, which fails identically on the
base commit `0487be1f` with this branch's changes stashed — pre-existing,
unrelated (pre-fill area). New tests: 7 cue-B unit tests
(test_system_grouping.py), 4 cue-C unit tests (test_measure_extractor.py,
including the vocal-page guard and the pinned disease), 3 e2e tests on the
real page (test_choir_grouping_e2e.py, omr_smoke, both flag directions).

## Guard 5 — the 969-page library probe (`probe_library.py` → `probe_library.jsonl`)

Same population as the left-edge work's sweep (every non-error row of
`benchmarks/omr-system-grouping-2026-09/sweep.jsonl`, its own render
normalization). Per page: staff detection once, then `assign_systems` with
the flag off and on, recording every gap the wide rule broke (bridging = 0,
x-overlap intact) with cue B's pair-band count.

**The population the min-cross floor is read off: 757 examined gaps — 735
read exactly 0, 22 read ≥ 4, and NOTHING reads 1–3.**

```
pair_left:  0 ×735   4 ×1   5 ×2   6 ×3   8 ×1   9 ×4   10 ×2   11 ×5   12 ×2   15 ×1   16 ×1
```

The empty band and the real rule do not come close to overlapping, so any
floor in 1..4 reads the whole population identically; `CHOIR_MERGE_MIN_CROSS
= 1` mirrors cue A's `LEFT_BAND_MIN_CROSS` and sits inside that gap. The
735 zeros are overwhelmingly TRUE system breaks (every true break is
examined, since nothing bridges it), which makes the same histogram the
false-merge measurement: **no adjudicated true system break shows a single
pair-band crossing column anywhere in the population.**

### Every page the flag changes, hand-adjudicated (crops via `adjudicate_crop.py`)

10 of 969 pages change (after the cue-A exemption below), plus the scan
benchmark's own Bach page. Every change moves toward the truth; none moves
away; there are no false merges:

| page | flag off | flag on | truth | verdict |
|---|---|---|---|---|
| bach brandenburg3 p1 *(the scan row)* | [12,3,3,3,1,2] | [12,12] | [12,12] | exact heal |
| bach brandenburg3 p16 | [11,2,3,3,1,2] | [11,11] | [11,11] | exact heal — true break correctly declined (pair band empty at the 363/60 bimodal gap) |
| handel water-music p26 | [10,2,4,2,2] | [10,10] | [10,10] | exact heal — Baroque continuo layout, Cembalo pairs set apart |
| haydn 96 p26 | [10,6,4] | [10,10] | [10,10] | exact heal |
| tchaikovsky 1 p49 | [12,4,3,5] | [12,12] | [12,12] | exact heal — winds/brass/strings blocks, Jurgenson |
| mozart 40 p32 | [2,8,11] | [10,11] | [10,11] | exact heal (needs the cue-A exemption below) |
| zauberflöte p150 | [9,7,1,1] | [9,9] | [9,9] | exact heal — orphaned voice staff (lyric bands) + Bassi rejoined |
| figaro p278 | [8,6,1,1] | [8,8] | [8,8] | exact heal — "Dove sono", voice staff between lyric bands |
| don giovanni p534 | [2,3,1,1,1,1,1] | [2,3,5] | [5,5] | 5 wrong breaks → 1 (accompagnato page; system 1's [2,3] declined on jittered anchors) |
| brahms 2 p29 | [23,4] | [27] | [14,13] | 2 wrong → 1: the false break healed; the残 missed break at the true boundary is the over-merge family (bridging=3 body ink), which cue A cannot fix here because ITS band is median-poisoned — see below |
| brahms 2 p47 | [4,2,5,4,2,5] | [4,7,4,7] | [11,11] | 4 wrong → 2: two rescues, two declined (pair `x_start` jitter mis-anchored the band — fail-safe abstention) |

The family is exactly what the assignment predicted: Baroque/choir-grouped
layouts (Bach, Handel), block-barred classical/romantic pages (Haydn,
Tchaikovsky, Brahms), and **opera vocal pages** — where lyric bands play the
role of choir gaps and orphan the voice staves. Cue B's evidence (the
left-edge complex) is the same physical object on all of them.

### The cue-A interplay, measured, and the exemption it forced

Mozart 40 p32 is bimodally indented the other way round (ten staves at
x_start 206–221, eleven at 530–544, median on the SECOND mode). Cue B merged
the wrongly-broken gap 1 on its true systemic barline (11 columns in the
pair band) — and cue A promptly re-split it: its page-median band reads
mid-staff ink of system 1 as "the left edge" (page_left = 4 at gaps its own
music happens to cross there), the gate passes, and gap 1's band is empty at
that anchor. The original "cue A keeps the last word" ordering therefore
undid a correct, positively-evidenced merge.

**A cue-B merge is now exempt from cue A's re-split.** This cannot touch cue
A's validated fix set, because the two cues act on disjoint gap sets by
construction: cue A splits gaps the wide rule kept interior (bridging > 0 —
body ink faking a connection), cue B merges gaps the wide rule broke
(bridging == 0). Where they meet — only a gap cue B just merged — the
evidence is asymmetric: positive ink through the whole gap at the pair's own
edge, against absence at an anchor this whole benchmark documents as
poisoned. Unit-pinned (`test_cue_b_merge_is_exempt_from_cue_a_resplit`), and
the exemption changes exactly one probe page (mozart 40 p32, to the
adjudicated truth); the left-edge e2e suite is untouched.

## Cue C falsified once, and the condition that survived

Cue C's first formulation — bracket-groups alone (≥2 groups, half the staves
in multi-staff groups) — **was falsified by the engraved benchmark and
repaired before any of it shipped**. Flag ON, the 11-work pooled OMR-NED
read **0.8560 against the tree's 0.1306** (17891 edits), nine works at
0.94–0.98 with `entire staff insert/delete` at 48% of the pool, while two
works matched their recorded scores to the fourth digit. Flag OFF on the
same tree: Beethoven 5 reproduced its recorded 0.0595 exactly — the flag did
the damage.

Mechanism: LilyPond's orchestral fixtures are genuine OPEN SCORES — barlines
per staff, one `SystemStartBar` crossing every gap — so their bridging
counts are uniformly LOW (a few start-barline columns per gap), and
`_assign_groups`' *relative* threshold (median × 0.5) manufactures
"bracket-groups" out of the jitter. Condition 1 then held, cue C flipped the
open-score gate, and the per-staff barlines (connectivity ≈ 0 by layout)
were deleted wholesale.

What separates the Bach family from that shape is **the window-blind gap**:
a gap INSIDE a system that no in-window column crosses at all — possible
only when something outside the window holds the system together (the very
thing cue B merges on), and impossible for an open score, whose systemic
start barline touches every gap a little or its staves would never have been
one system. Cue C now requires one (`_window_blind_systems`, computed over
the whole page's staves — the same frame `assign_systems` used; a
per-system recomputation would anchor the window on the system's own median
and the blind gap would stop being blind, measured on the Bach page).
Re-measured with the condition: Beethoven 5 flag ON **0.0595**, identical to
flag OFF. Pinned by `test_cue_c_requires_a_window_blind_gap`, which draws
the LilyPond shape (all gaps touched by a start barline) over the choir
fixture and asserts open-score mode survives.
