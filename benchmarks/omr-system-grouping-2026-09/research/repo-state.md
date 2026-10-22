# System grouping — definitive current-state report (Phase 1A)

2026-09-01. Produced by the repo-state research agent (Opus) for the
publisher-stratified grouping project. All paths absolute. Code identical between
the worktree and `/Users/seanjohnson/Desktop/ReEngrave`; citations use the main
checkout. `library/` and `omr-weights/` exist **only** in the main checkout
(`library/` is untracked via `.git/info/exclude:21`).

Pilot artifacts referenced at the end were copied to `../pilot/` in this
benchmark directory.

## 0. Three corrections to the received briefing

These change what the planned benchmark should test.

**(a) `_gap_is_bridged` does not exist.** Not on main, not in the worktree. It
lived only on branch `claude/reengraved-score-evaluation-cd4c92` (commit
`87a5196`) and was explicitly discarded at merge `45e19a6`: *"Main has since
landed the measured version of the same idea as `system_grouping.assign_systems`
(43% -> 86%)… Main's kept; the branch's dropped as superseded."* The stale name
is still cited in `CLAUDE.md:355` and
`/Users/seanjohnson/Desktop/ReEngrave/benchmarks/omr-orchestral-e2e/README.md:107`.

**(b) The mechanism is connectivity-PRIMARY, not "gap breaks + veto."**
`/Users/seanjohnson/Desktop/ReEngrave/tools/omr/staff_detector.py:901-903`:

```python
staves, used_bridging = assign_systems_by_bridging(page.binary, staves)
if not used_bridging:
    staves = _assign_systems(staves)
```

Connectivity is a **full replacement**. The gap heuristic runs only when *no gap
anywhere on the page* is bridged.

**(c) "Can merge an over-split page but never split a correct one" is false for
the shipped code.** `system_grouping.py:230-234` *creates* breaks — on
`bridging[i] == 0` and on x-overlap ≤ 0.5 — independent of gap size. The module
docstring records that the larger-than-median-gap guard was deliberately
**removed** (`system_grouping.py:110-115`): *"on Beethoven 9 p25 the true break
between two 12-staff systems has a 68 px gap while intra-system gaps reach 99 px,
so the guard suppressed a real break."* This matters because all three standing
failures are **merges caused by a break failing to fire** — which the veto
framing predicts is impossible.

---

## 1. MECHANISM MAP

### 1.1 The grouping call site

`/Users/seanjohnson/Desktop/ReEngrave/tools/omr/staff_detector.py:838`
`detect_staves(page) -> PageWithStaves` is the sole entry point. Grouping is the
last step, at `:901`. Everything before it is staff *detection* (steps 1–3d),
and **grouping runs before any YOLO inference** — it is pure classical CV.

Order inside `detect_staves`:
- `:840-842` ink profile → candidate rows → 5-line groups
- `:853` `_reject_spacing_outliers` (phantom staves)
- `:854-855` comb pass + merge (recovers faint staves)
- `:859-860` `_single_line_staff_rows` (percussion rules)
- `:865` `_refit_misaligned_group` (step 3d, beam-capture fix)
- `:888-891` **text-as-staff filter** (`_line_ink_runs_per_space`, threshold
  `MAX_LINE_INK_RUNS_PER_SPACE = 1.7` at `:57`) — applied *before* grouping so
  indices stay contiguous
- `:901` grouping

### 1.2 The live rule — `/Users/seanjohnson/Desktop/ReEngrave/tools/omr/system_grouping.py`

`assign_systems(binary, staves, *, fallback=True) -> (staves_sorted_by_y,
used_bridging)` at `:201`.

**Break test** (`:228-234`), evaluated per adjacent pair top→bottom:
```python
if _x_overlap_frac(upper, lower) <= MIN_X_OVERLAP_FRAC:   # multi-column
    system += 1
elif bridging[i] == 0:                                     # nothing crosses
    system += 1
```
There are **no gap statistics here at all**. Only two conditions produce a break.

**Fallback trigger** (`:223-224`): `if fallback and not any(n > 0 for n in
bridging): return staves, False` — i.e. only when the page is so faint that
*nothing anywhere* bridges.

**`gap_bridging_counts(binary, staves, *, ink_fraction=BRIDGE_INK_FRACTION)` at
`:135`** — what actually gets tested:

| aspect | value | line |
|---|---|---|
| x-range searched | `_robust_x_window`: **median** `x_start`/`x_end` across the page's staves, ± `WINDOW_MARGIN_SPACINGS × median line spacing` | `:118-126` |
| vertical band | `upper.bottom_y + 2` … `lower.top_y - 2` — **the gap only** | `:159-160` |
| ink column definition | after morphological close, column mean > `ink_fraction` | `:168` |
| gap-closing kernel | `k = max(3, round(spacing × 0.6) × 2 + 1)`, vertical (`(k,1)`) | `:166-167` |
| degenerate result | `-1` = "no evidence" | `:161-162` |
| min run length | **none** — no run-length test exists; it is a per-column mean over the closed band | `:168` |

⚠️ **The function does not implement its own docstring.** Lines `:34-45`
describe a band running *"from the top line of the upper staff to the bottom
line of the lower staff"* and argue that extending through both staves is what
discriminates barlines from stems. The code measures the gap only (`:159-160`).
This discrepancy is documented as unresolved in
`RULE_FIX_ATTEMPT_2026-08-31.md:80-89` — and attempt 3 proved implementing the
documented version *does not help*, so it is open whether the code or the prose
is wrong.

**Constants — every knob touching grouping** (`system_grouping.py:83-108`):

| constant | value | purpose |
|---|--:|---|
| `BRIDGE_INK_FRACTION` | 0.8 | column must be near-solid over the band |
| `BRIDGE_GAP_TOLERANCE_SPACINGS` | 0.6 | closes print breaks; **added because a bracket solid at 300 dpi is dotted at 600** — B5 p10 grouped 2 systems @300, 4 @600 |
| `GROUP_BOUNDARY_RATIO` | 0.5 | bracket-group (`group_index`) split within a system |
| `WINDOW_MARGIN_SPACINGS` | 4.0 | reach past staff ends to catch bracket + closing barline |
| `MIN_X_OVERLAP_FRAC` | 0.5 | multi-column break, overrides connectivity |

**`_assign_groups` at `:172`** sets `Staff.group_index` — within a system, split
where bridging < median × 0.5. Feeds `slots.py` only.

### 1.3 The fallback — `staff_detector._assign_systems` at `:605`

Three additive gap thresholds plus x-overlap (`:674-679`); a break fires if
**any** matches:
1. `_bipartition_threshold` (`:576`, 1-D Lloyd's k-means, requires cluster gap ≥
   2× intra-spread), else `MAX_SYSTEM_GAP_FACTOR × mean_spacing` (`:45`, = 6.0)
2. MAD rule: `median_gap × 2.0` (`:639-641`) — added `2b9948b` to split
   wind/brass/string blocks, later identified as the primary over-splitter
3. quartile rule: `max(p25(gaps) × SYSTEM_BREAK_GAP_FACTOR, mean_spacing × 2.0)`
   (`:656-661`); `SYSTEM_BREAK_GAP_FACTOR = 2.5` at `:56`
4. `x_overlap_frac <= 0.5`

### 1.4 Brackets, braces, systemic barlines, dividers — used at all?

**No glyph-level detection of any of them exists.** They are used **only
implicitly**, as ink that happens to bridge a gap. Verified by grep across
`tools/omr/*.py`:
- The bracket is *reasoned about* in comments (`system_grouping.py:28,43,50,99-103`)
  and the window margin exists to include it, but nothing localizes it.
- `yolo_detector.py:158` has a `"brace": "structural"` class — **unreachable for
  grouping**, since grouping runs before YOLO.
- `header_ink.py:55` *erases* "the initial barline, the system bracket" — the
  opposite use.
- `visualize.py:7` "system divider lines" are drawn output, not input.

This is the single largest unexploited signal, and attempt 4 (§3) tried and
failed to exploit it.

### 1.5 Downstream flow

| consumer | dependency | file:line |
|---|---|---|
| **`measure_extractor.detect_barlines`** | groups staves by `system_index` (`:273-276`); barline = column voted by ≥half the system's staves; vote threshold **scales with system size** (`:308-332`) — so a merged system raises the threshold and can lose all barlines | `measure_extractor.py:257` |
| `_measure_x_boundaries` | system edges are the **median** `x_start` across the system's staves + max `x_end` | `:458`, `:476-478` |
| `extract_measures` | emits `MeasureCell.system_index`; `measure_index` renumbers **per system** | `:625`; `dossier.py:77` |
| **`transcribe`** | iterates `sorted({st.system_index …})`, per-system clef inheritance via `start_system`/`end_system` (only inherits from a **same-sized** previous system) | `transcribe.py:1166`, `:580-629` |
| **`dossier.slot_facts_for_system`** | **abstains unless `len(parts) == n_staves`** | `dossier.py:459`, `:479-480` |
| **`dossier.slot_facts_for_page`** | the page-level fallback — literally `return slot_facts_for_system(n_staves_on_page, dossier)` | `dossier.py:483-500` |
| `dossier.join_parts_to_slots` | monotone alignment on **margin labels, never clefs** (circularity guard) | `dossier.py:388`, `:406-409` |
| **`slots.build_reference`** | picks the largest system as the part list — with two anti-merge guards: `REFERENCE_MAX_SIZE_RATIO = 2.0` (`slots.py:72`) and `_looks_merged` (`:160`), plus "prefer a size that recurs" (`:141-148`) | `slots.py:119` |
| `contextual.apply_contextual_analysis` | chain starts *"correct systems (system_grouping)"*; keys everything on `(page, system_index, staff_index)`; vision budget spends **per system** | `contextual.py:5-8`, `:314`, `:305-306` |

The `slot_facts_for_page` docstring (`dossier.py:487-491`) still cites the
**pre-fix** state — *"one musical system of 21 staves was reported as TWELVE
systems"* — which the connectivity rebuild fixed (Brahms 12 → 1). The fallback
remains justified by Mahler (31 staves vs 38 parts), but the quoted evidence is
stale.

---

## 2. MEASUREMENTS

### 2.1 `benchmarks/omr-system-grouping-2026-08/eval_grouping.py` — the only scored grouping metric

**Metric:** system *count* per page vs truth. Ground truth is **inlined as
literals at `:39-72`** — there is no GT JSON. GT method (`:35-38`), verbatim:

> "Ground truth is the number of LEFT BRACKETS on the page, read off a crop of
> the left margin. Counting systems from a whole-page thumbnail does not work
> and produced a wrong label set on the first attempt: at thumbnail scale the
> brass-to-strings bracket-GROUP gap looks exactly like a system break, so pages
> 30-50 (single 13-staff systems) were all mislabelled as 2."

**Re-measured live today (23 cases): gap heuristic 7/23 (30%), connectivity
20/23 (87%), spurious single-staff systems 37 → 0.**

**The three failures, all merges** — `RULE_FIX_ATTEMPT_2026-08-31.md:10-17`,
verbatim:

> "`system_grouping.assign_systems` breaks a system only where the
> crossing-column count is EXACTLY zero. Three adjudicated pages are genuine
> breaks with nonzero bridging, so all three merge:
> | page | truth | got | bridging at the true break |
> | B9 p25 | 2 | 1 | 66 |
> | B9 p60 | 2 | 1 | 324 |
> | B5 p40 | 3 | 1 | 3 and 11 |"

And the diagnosis (`LEGATO_CROSSCHECK_2026-08-31.md:97-100`):

> "So the rule is not wrong so much as **zero-tolerance**: it works whenever
> nothing at all crosses the break, and fails silently the moment a little ink
> does — margin text, a measure number, scan noise. p40 prints its measure
> number and restarts its instrument labels inside the very window the scan
> looks at."

B5 p40 adjudication (`:55-61`): *"there are three brackets, three measure
numbers (229, 243, 256), and the instrument labels restart at each (Cl./Fag./Cor.
— Cl./Fag./Cor. — Ob./Cl./Fag.)."* Evidence image:
`benchmarks/omr-system-grouping-2026-08/evidence/b5-p40-margin.png`.

**⚠️ "43%" is stale.** `findings.md:1,41-47` records 6/14 → 12/14. The gap
heuristic reproduces at **5/14 (36%)**, already noted in
`LEGATO_CROSSCHECK_2026-08-31.md:140`. Connectivity's 12/14 reproduces exactly.
The number propagated unchanged into `NOTES.md:424`,
`PROJECT_STATUS.md:27,121-122,389`, `docs/state-of-play-2026-08-28.md:61,92`.

**A finer GT exists only in the probes** — `probes/fulldist.py:27-29` carries
break *indices* (the actual partition) and includes **B5 p47, truth 0 breaks — a
free 24th case not in `eval_grouping.py`**.

### 2.2 `legato_crosscheck.py` + `legato-crosscheck.json` (47 rows)

The only **partition-level** comparison in the repo (`classify()` at `:89-116`:
`agree` / `we_merge` / `we_split` / `boundary_moved`). Against
`guangyangmusic/legato-1.5-YOLO` (AGPL-3.0, hence quarantined in
`benchmarks/`). Result: **46 agree, 1 `we_merge` (B5 p40)**, zero `we_split`,
`staves_legato_missed = 0` on all 47. LEGATO is a **miner, not an oracle** — two
recorded errors: B9 p25 (both wrong) and Boléro p10, where
`eval_grouping.py:65-66` notes *"LEGATO says 3 here and is WRONG — it returns
three overlapping boxes on this page."*

### 2.3 `benchmarks/omr-phase1-baseline/ground-truth.json` — the only staves-per-system truth

Three hand-verified pages: `wtc-p5` (10 staves, 5 systems, `[2,2,2,2,2]`, 600
dpi), `beet5-p10` (22, 2, `[11,11]`, 600 dpi), `lamer-p25` (21, 1, `[21]`, 300
dpi, one-line percussion staff at index 11). Provenance (`:2-14`): *"Every
number here was read off the printed page by a human, NOT copied from pipeline
output… it asserted 18 staves on a 22-staff page, which a phantom staff
satisfied."*

Both `known_gaps` are closed. The `beet5-p10` lesson (`:100`) for the new
benchmark: *"A measurement taken through a broken reader describes the reader,
not the page."*

**⚠️ `lamer-p25` is a 9-vs-1 grouping failure that no metric counts.**
`training/phase1_layout_eval.py` snapshots show `[7,1,3,2,1,1,2,1,2]` against a
truth of one system, and the page is **not** in `eval_grouping.py`'s cases.

### 2.4 Tests

`tools/omr/tests/test_system_grouping.py` (458 lines) — **entirely synthetic**
(drawn rules; header at `:1-5`), **no xfail/skip**. Notable: `:119`
`test_wide_bracket_group_gap_does_not_split_a_system` is the regression the
module exists for; `:86` and `:100` encode the B9 p60 and B5 p10@600 numbers
directly; `:160` covers multi-column.

`tools/omr/tests/test_pipeline.py` (marked `omr_smoke`, skips if PDF absent) —
the only real-PDF system assertions: WTC p5 `[2,2,2,2,2]` (`:119-123`),
beet5-p10 `[11,11]` (`:212-222`), Nottebohm p46 `[4,4,4]` (`:264-274`). No
xfail markers remain anywhere in `tools/omr/tests/`.

`tools/omr/tests/test_slots.py:65-107` — three tests that exist purely to defend
against grouping merges.

### 2.5 Other corpora (no grouping ground truth)

- `benchmarks/omr-corpus-sweep-2026-08/sweep.jsonl` — **220 pages / 10 scores**,
  records `systems` per page but is explicitly *"behaviour, not correctness"*
  (`README.md:42`). Needs YOLO; ~20-30 s/orchestral page.
- `benchmarks/omr-orchestral-e2e/README.md:93-117` — where grouping was first
  exposed; LilyPond-engraved from Gradus MusicXML, so **publisher-free by
  construction**. Records the pre/post table (Brahms 12→1, Beethoven 4→1,
  Mahler 4→1) but does **not** score system counts in its output.

### 2.6 The designated regression gate does not exist as an artefact

`RULE_FIX_ATTEMPT_2026-08-31.md:191-192`: *"**The 54-page cross-check as the
regression gate**, since it is the only thing that caught attempt 1. Run it
before believing `eval_grouping.py`."* There is no such script; the nearest is
`legato_crosscheck.py` (47 rows), and **only 4 of the 12 pages it broke are ever
named**.

---

## 3. FAILURE TAXONOMY

### Currently open

| # | mode | cause | example | status |
|---|---|---|---|---|
| **F1** | **Over-merge — `bridging == 0` is zero-tolerance** | any ink in the window (measure number, margin label, restarted instrument names, noise) suppresses a real break | B9 p25 (bridged 66), B9 p60 (324), B5 p40 (3 and 11) | **open**; 5 fixes attempted and rejected |
| **F2** | Staff count deflated, blocking the dossier join | detection, not grouping | Mahler 5: 31 staves vs 38 parts | open |
| **F3** | La Mer p25 read as 9 systems against truth 1 | not diagnosed; page carries the one-line percussion staff | `lamer-p25` | open, **uncounted** |
| **F4** | Multi-column / multi-movement pages | only guard is the ≥50% x-overlap test, which `de63d6f` measured as a net false-break source | none — **no GT page anywhere is multi-column** | untested live code |
| **F5** | `gap_bridging_counts` ≠ its docstring | see §1.2 | — | open |

`5b1ef55` characterises F1 as one narrow case: *"all three of its failures are
the same narrow case — **two systems printed so close that their brackets nearly
touch.**"*

### Fixed, with mechanism recorded

| mode | cause | example | fix |
|---|---|---|---|
| **Over-split: gap size cannot separate a system from a bracket group** | orchestral engraving spaces families apart | *"gaps WITHIN one Brahms system run 17-237 px and within one Beethoven system 130-345 px — both wider than the gaps BETWEEN systems on a piano page"* (`87a5196`); B9 p40 came out `[3,1,2,1,5]` for one 12-staff system | `dc867d5`+`5efc66e` connectivity |
| **Over-split: thresholds contaminated by the breaks themselves** | bipartition + MAD computed over *all* gaps | Nottebohm p90 gaps `65,65,65,341,394,830`, median 203 puts thresholds above the real breaks | `c853a69` p25 quartile rule (still live in fallback) |
| **Over-split: resolution-dependent bracket** | bracket solid @300 dpi, dotted @600 | **B5 p10: 2 systems @300, 4 @600** | `BRIDGE_GAP_TOLERANCE_SPACINGS` |
| **Over-split: broken `x_start` as scan window** | `x_start` = longest ink run | B9 p60 staff 3: `x_start=885, x_end=1826` vs ~275/~2485 for neighbours | `_robust_x_window` (median) |
| **Over-split: window clipped to staff extent** | bracket sits *outside* the staff lines | B5 p10@600: only crossing columns at x=334-353 and x=2630+, against staff extent 355..2629 | `WINDOW_MARGIN_SPACINGS = 4.0` |
| **Over-split: x-overlap was doing grouping by accident** | `_staff_x_extent` returned longest ink run | `c853a69`: *"once every staff correctly spanned the page, they all overlapped and merged into one system, which raised the barline vote threshold out of reach"*; Nottebohm p90 9 barlines → 1 | x-extent fix; **x-overlap break still live in both paths** |
| **Phantom staves (5 read as 1)** | prominence gate calibrated by the densest music | B5 p10 **pocket score**: 18 staves on a 22-staff page, *"every note on the Flute, Oboe, Clarinet, Bassoon and Horn staves was invisible"* | `cc975ba`; beet5 p10 18→22, p2 16→22, p8 16→20 and 5 systems→2 |
| **Missed one-line percussion staves** | grouper accepts only 5-peak windows | La Mer p25 Cymbales; Mahler 5 p10 where a **wavy trill line** (1410 px) between Gr.Tr. (1857) and Kl.Tr. (1858) took both real rules down | `1b16626`, `5240044`, `b443762` |
| **Text detected as staves** | justified prose passes the 35%-width test | **147 of 1522 "staves" over 156 Nottebohm pages** | `_line_ink_runs_per_space` (music ≤1.39, text ≥2.02) |
| **Staff window one space off (beam captured as a line)** | top "line" was an 18 px beam vs 5 px real lines | Brahms staff 20 (Contrabass): 42 of the page's 65 wrong pitches | `f2e1991`; pooled OMR-NED 0.3045→0.2716 |
| **Downstream crash from a one-line staff** | span 0 → 1×0 kernel → OpenCV raises | *"That page could not be transcribed at all"* | `ba396e1` |

### Ground-truth methodology failures (happened twice; itself a taxonomy entry)

`findings.md`, and `5efc66e`: *"The previous commit's headline came from a
ground-truth-free proxy… The proxy metric was the more dangerous one because it
produced a *confident* number."* The proxy — "a correct detector yields a tight
staves-per-system distribution" — **rewards merging every page into one system,
and duly reported success.** The second failure was counting systems off
whole-page thumbnails, which mislabelled every single-system B9 page 30-50 as 2.

### The five rejected fixes (2026-08-31) — do not re-propose without reading these

| # | signal | on GT | why it died | sha |
|---|---|---|---|---|
| 1 | rightmost bridging column over page window | 262 boundaries, zero overlap; 14/14 | **12 pages newly over-split, every one outside the Beethoven editions** | `79266eb` |
| 2 | reach vs staves' own right end | breaks 2.15-29 spacings short | within-system gaps elsewhere sit **145 spacings short** | `79266eb` |
| 3 | the band the docstring specifies | — | no separation at all | `79266eb` |
| 4 | bracket zone only, 32 configs | 15/15 recall | `min(non-break) = 0` in **all 32** | `3ba7286` |
| 5 | instrument-label continuity | best TP12/FN3/FP5 | shipped rule makes 3 errors; best of these makes 8 | `5b1ef55` |

Attempt 1's regression, verbatim: `La Mer p20 1 → 16`, `Haendel lead-sheet p20
2 → 12`, `Boléro p2 4 → 8`, `Mahler 5 p10 1 → 4`.

**One salvage kept** (`:116-119`): *"bracket-zone reach of 0 is a NECESSARY
condition — 15/15 true breaks satisfy it and it never misses one… a future
combined rule could use it as the cheap first filter."*

**Standing recommendation** (`5b1ef55`): *"**Recommendation: stop.** Five
attempts across two families… all land well short of a rule already at 20/23."*

### Edition/publisher dependence — already named as the mechanism

`RULE_FIX_ATTEMPT_2026-08-31.md:159-174`, verbatim — **this is the planned
benchmark's hypothesis, already stated**:

> "**In orchestral engraving, barlines are deliberately broken between
> instrument families.** Winds, brass and strings each get their own barline
> run. So 'what crosses this gap, and how far' is a property of the EDITION's
> engraving convention, not of whether a system ends there.
>
> Beethoven 9 and Beethoven 5 (the ground-truth editions) happen to run barlines
> across their group gaps, which is why every signal looked clean on them.
> Mahler, La Mer, Boléro and the Handel reductions do not, so within-system gaps
> there carry the same signature as a break. Two editions is not a sample; it is
> a coincidence that held twice."

One layer down (`3ba7286`): *"a system bracket is a thin curved tapered
engraving rather than a printed rule, and **whether it clears an ink-fraction
test over a tall band is ITSELF an edition property.**"*

Further instances: score-order rank is edition-dependent (`5b1ef55`); two
Beethoven 5 *scans of the same edition* need different barline thresholds
(`e83605a`); Beethoven 1 imslp-52848's 2-system pages have inter-system gaps
only ~1.5× median intra-system (`d30db31`); pocket scores print winds more
lightly than strings (`cc975ba`); 19th-century line thickness (`0619f39`); scan
warp drifting a barline 40 px top-to-bottom (`6ba276f`); open score vs orchestral
barline continuity (`c853a69`, `test_pipeline.py:236-241`).

---

## 4. CHEAP SWEEP PATH

### 4.1 Minimal programmatic path — no YOLO, no weights, no DB

```python
from tools.omr.preprocessing import render_page      # (pdf, page_index, dpi=...) -> PageImage
from tools.omr.staff_detector import detect_staves    # (PageImage) -> PageWithStaves
from tools.omr.system_grouping import gap_bridging_counts  # (binary, staves_sorted_by_y) -> list[int]

pi  = render_page(pdf_path, page_index, dpi=300)
pws = detect_staves(pi)                     # grouping already applied
for s in pws.staves:
    s.staff_index, s.system_index, s.group_index, s.top_y, s.bottom_y, s.x_start, s.x_end
```

Fields: `Staff.system_index` (`types.py:58`), `Staff.group_index` (`:59`),
`PageWithStaves.staves_in_system(i)` (`:126`). Staves-per-system =
`Counter(s.system_index for s in pws.staves)`. `gap_bridging_counts` gives the
raw per-gap evidence (`-1` = no evidence) — essential for diagnosing *why*.

### 4.2 Measured cost

| what | cost |
|---|--:|
| Mahler 5 p10, 300 dpi: render / detect / total | 0.53 / 0.10 / **0.64 s** |
| same at 600 dpi | 1.94 / 0.26 / **2.19 s** |
| **172-page pilot across 86 publishers** | **182 s total, mean 1.06 s/page, median 0.69 s** |
| worst page seen | 31.8 s (one oversized scan) |

**100-200 pages is 2-4 minutes of CPU.** The bottleneck is human
bracket-reading, not compute.

### 4.3 Existing harnesses to reuse

- **`python3 -m tools.omr.staff_detector <pdf> --page N --dpi 600`**
  (`staff_detector.py:910-927`) — prints staves with `sys=` per staff.
- **`python3 -m tools.omr.run_pipeline <pdf> --pages 0-4 --dpi 300 --out-dir DIR`**
  — writes `summary.json` (`staves`, `systems`, `measures_per_system`,
  `runtime_s`) + `pageNNN-overlay.png` per page. No YOLO. Measured: Mahler 5
  p10 → "20 staves, 1 systems, 8 barlines, 144 cells, 2.97s".
- **`python3 -m tools.omr.visualize <pdf> --page N --out X.png`** — overlay
  alone; `draw_overlay` (`visualize.py:34`) labels each staff
  `s{staff_index} sys{system_index}` and draws yellow dashed system dividers
  (`:73-91`). The human-verification artifact.
- **`benchmarks/omr-system-grouping-2026-08/eval_grouping.py`** — copy its
  `CASES` shape; the scoring harness with 23 hard-coded cases.
- **`benchmarks/omr-corpus-sweep-2026-08/sweep.py`** — robustness pattern to
  imitate: one JSON line per page flushed immediately, resumable, a page that
  raises is recorded and the sweep continues.

### 4.4 ⚠️ Two sweep hazards, both measured

**(a) Fixed `--dpi` silently zeroes out editions with a small page box.**
`render_page` scales by the PDF's declared mediabox.
`brahms--symphony-2-op73--simrock-1878--imslp23103.pdf` has a **2.38 × 2.82
inch** mediabox, so 300 dpi renders 713×846 px and Phase 1 finds **zero
staves** — on a page that is 13% ink. Measured:

```
dpi=300   713x846   staves=0   systems=0
dpi=900  2138x2538  staves=27  systems=3  sizes=[15, 11, 1]
dpi=1200 2850x3384  staves=29  systems=2  sizes=[15, 14]
```

Across `library/` page height runs min 2.82 in / median 11.69 / max 58.64.
**Normalize to a target pixel height (~3000-3500 px), not a fixed DPI.** Two
library PDFs fall below 6 inches.

**(b) DPI changes the answer even on normal pages.** Mahler 5 p10: 20 staves
@300, 19 @600. B5 p10 grouped 2 systems @300 and 4 @600 before the gap-closing
fix. `eval_grouping.py` carries B5 p10 at *both* DPIs as separate cases — keep
that pattern.

---

## 5. EDITION DIMENSION

### 5.1 The GT is one publisher, not two editions

`RULE_FIX_ATTEMPT_2026-08-31.md` reasons about *"the two Beethoven editions."*
The edition catalog says they are **one**:

| corpus | publisher / edition | plate | text layer |
|---|---|---|---|
| **B9** `imslp-516488` | **Henry Litolff's Verlag, Braunschweig, 1870**, ed. H. C. Litolff | 2773 | yes |
| **B5** `IMSLP984073` (Gradus) | **Litolff, Braunschweig, 1870** | 2769 | **no** |
| B5 `imslp-575951` | **Litolff 1870** — same edition, different scan | 2769 | yes |
| B6 "pastoral" `imslp-504082` | **Litolff 1870** | 2770 | yes |

**15 of the 23 GT cases (65%) are a single publisher's 1870 plates**, adjacent
plate numbers. The real statement: 65% of the ground truth is *one engraving
house in one year*.

### 5.2 Edition per benchmark corpus page

| corpus | file | publisher | type |
|---|---|---|---|
| B9 pp.20-75 (12 cases) | `tools/omr/training/data/imslp/beethoven-symphony-9/pdfs/imslp-516488/score.pdf` | Litolff 1870 pl. 2773 | scan |
| B5 p10 ×2 dpi, p40 | `~/Documents/Gradus-Assets/Scores/Scores For Gradus/IMSLP984073-PMLP1586-...pdf` | Litolff 1870 pl. 2769 | scan |
| La Mer p2, p20, p25 | `.../PDF Scores/IMSLP15420-Debussy_-_La_Mer_(orch._score).pdf` | **Durand & Fils**, pl. D.&F. 6532/6838 | scan |
| Boléro p2, p10, p20 | `.../PDF Scores/IMSLP421137-PMLP03667-Ravel_Bolero.pdf` | **Éditions Nicolas Sceaux 2016**, LilyPond 2.19.37 | **typeset** |
| Mahler 5 p2, p10, p20 | `.../PDF Scores/Mahler_5_.pdf` | **UNKNOWN** — catalog `unidentified-scan-2016`; `omr-phase1-baseline/ground-truth.json:103` asserts "Edition Peters" but is unsourced; PDF metadata says only "Adobe Acrobat 9.2 Image Conversion", 2016. **Two files disagree; treat as unknown.** | scan |
| WTC p5 | `.../IMSLP932182-...well-tempered-clavier-I-book.pdf` | **Knute Snortum 2024**, LilyPond 2.24.4 | **typeset** |
| Handel reduction / lead-sheet | `.../Haendel_Messiah_{reduction,lead-sheet}.pdf` | **Éditions Nicolas Sceaux** © 2009-2022, LilyPond 2.23.4 | **typeset** |
| Kirchhoff | `.../Kirchhoff_L'ABC-Musical.pdf` | **Derek Remeš 2020**, Sibelius 19.5 | **typeset** |
| orchestral-e2e | `benchmarks/omr-orchestral-e2e/fixtures/*.pdf` | none — LilyPond from Gradus MusicXML | synthetic |
| Nottebohm | (test_pipeline only) | **banned from OMR benchmarking** per user feedback | scan |

Effective GT span: **Litolff 1870 (65%), Durand, Nicolas Sceaux typeset, one
unknown scan.** Only two real 19th-century orchestral houses represented.

### 5.3 The asset that makes a publisher-stratified benchmark cheap

`/Users/seanjohnson/Desktop/ReEngrave/library/` — **untracked, main checkout
only** (`.git/info/exclude:21`).

- **122 PDFs**, 40 composers, filename convention
  `composer--work--publisher-year--imslpID.pdf` — publisher parseable from the
  filename alone.
- Per-edition `*.json` records alongside each PDF carry `publisher`, `variant`,
  text-layer and image-type fields.
- **~86 distinct publisher tokens.** Deepest: Litolff 1870 (10),
  Breitkopf-Härtel Mozart 1880 (10), Breitkopf & Härtel (6+ variants),
  Eulenburg (3), Simrock (8 across years), Jurgenson (5), Novello (5),
  Durand (4), Peters (3), Hansen, Aibl, Kahnt, Hofmeister, Fürstner, Belaieff,
  Augener, Lienau, Enoch, Éditions Russes.
- `library/reference/` holds 3490 MXL+JSON files; `data/dossiers/` holds 97
  generated dossiers — cross-checks, though neither carries grouping truth.

### 5.4 New failures found by the 172-page pilot — publishers outside the GT

Pilot: one PDF per publisher token, 2 pages each, 300 dpi, 182 s. Raw data:
`../pilot/pilot.jsonl`; overlays `../pilot/muss_p14.png`, `../pilot/muss_gap.png`.

**(1) Confirmed over-merge on Augener 1914 — F1 on a publisher not in the GT.**
`mussorgsky--pictures-at-an-exhibition--augener-1914--imslp272845.pdf` p14
grouped `[2,2,2,4]`. Bridging across the nine gaps:
`[36, 0, 50, 0, 54, 0, 34, 9, 27]`. Three real breaks read 0 correctly; the
fourth reads **9** and no break fires, merging two 2-staff piano systems. The
bridging columns are at x=670-678 only — cropped, the ink is **fingering digits
and slur tails**, not a barline. p28 shows the mirror case `[2,4,2,2]`.

**(2) Spurious single-staff system on Eulenburg 1920.**
`strauss--also-sprach-zarathustra-op30--eulenburg-1920` p95 → `[1, 11, 11]`.
Connectivity produces zero single-staff systems on the 23-case GT, so this is
outside all recorded behaviour — adjudicate first.

**(3) Other uneven pages worth hand-reading** (uneven sizes are a tell, not
proof): Mahler 4 `edition-1911` p75 `[4,6,8]`; Dvořák `simrock-1896` p22
`[7,5,16]`; Strauss `jos-aibl-verlag-1898` p56 `[6,13]`; Mozart 25
`breitkopf-hartel-mozart-1880` p11 `[7,7,4,4]`; Vidal `univerzitet-umetnosti-u`
p82 `[6,1,1,1,1]`.

Pages that look alarming but are almost certainly correct: WTC `snortum-2024`
`[2,2,2,2,2,2]`, Kirchhoff `[2,2,2,2]`, Handel lead-sheet `[3,3,3,3,3]` —
keyboard/lead-sheet layouts genuinely have many small systems.

---

## 6. Gaps the new benchmark should close

1. **No metric scores the partition** — `eval_grouping.py` compares counts only.
   `legato_crosscheck.classify()` is the only partition comparator and has no
   ground truth. Adopt its verdict vocabulary with human GT.
2. **The designated regression gate ("54-page cross-check") is not a runnable
   artefact**, and 8 of the 12 pages attempt 1 broke are never named.
3. **La Mer p25** (9 vs 1) and **B5 p47** (probe-only GT) are free cases not in
   `eval_grouping.py`.
4. **65% of GT is one publisher**; only two real 19th-century orchestral houses
   are represented at all.
5. **Multi-column layout is live, untested code** with no GT page anywhere.
6. Stale references to fix while in here: `_gap_is_bridged` (`CLAUDE.md:355`,
   `omr-orchestral-e2e/README.md:107`); the "43%" figure (reproduces at
   36%/30%); `findings.md:110` naming a since-renamed test; `dossier.py:487-491`
   citing the pre-fix Brahms 12-system result.
7. **Normalize render resolution by target pixel height, not DPI** — a fixed
   300 dpi produced zero staves on a real edition.
