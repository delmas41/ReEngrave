# System grouping × publisher — project plan

2026-09-01 · branch `claude/system-break-rule-publishers-62ead4` · manager: Fable; research/build subagents: Opus + Sonnet.

## Problem

A staves→systems grouping rule that works everywhere keeps eluding us. Gap thresholds
are provably impossible (within-system gaps 17–345 px overlap between-system gaps
across page types). **Corrected 09-01 by Phase 1A** (see `research/repo-state.md` —
CLAUDE.md's account is stale): the shipped rule is `system_grouping.assign_systems`,
connectivity-PRIMARY, not a veto — a break fires only where x-overlap ≤ 0.5 or a gap's
bridging count is exactly **0**. It scores 20/23 (87%) on the count-level GT (gap
fallback: 7/23). All three standing failures are **over-merges** from that
zero-tolerance: real breaks with nonzero bridging (margin text, measure numbers,
fingering ink). Five fix attempts were rejected on 2026-08-31 with a recorded "stop"
recommendation — every signal that passed the GT broke on editions outside it.
Grouping failures cascade: the dossier part→staff join abstains, measure counts skew,
clef/key seeding is lost.

## Hypothesis (Sean's)

The residual failures are edition-dependent: publishers differ in exactly the layout
facts our rule leans on. Candidate mechanisms — to test, not assume:

- **Interior barlines**: unbroken through the full system vs broken between instrument
  families. The veto needs an inked column through the gap; a family-break edition
  starves it at family boundaries unless the left systemic barline carries it.
- **System dividers** (double-slash marks between systems): printed by some
  publishers — an unused *positive* break cue.
- **Brackets/braces**: a bracket spans exactly one system — unused grouping evidence.
- **Spacing/indentation** conventions, and reprint degradation (Kalmus/Dover plates)
  as confounds.

## Phases

0. **Setup** — worktree sane, this plan. ✅
1. **Research** (parallel, running):
   - A. In-repo state: mechanism map, every existing grouping measurement + enumerated
     failures, cheapest layout-only sweep path. *(Opus)*
   - B. Corpus inventory: PDFs × MusicXML × publisher metadata across the Gradus
     library, the ReEngrave checkout, and the IMSLP-catalog experiment. *(Sonnet)*
   - C. External: publisher engraving conventions + OMR literature on system
     segmentation → ranked publisher-robust features. *(Opus)*
2. **Benchmark**: publisher-stratified ground truth (~100–200 pages, orchestral-first;
   Nottebohm banned), per page `{n_systems, staves_per_system}`; layout-only sweep
   script; per-publisher accuracy table. GT read from rendered pages; every
   GT-vs-pipeline disagreement gets a second independent read before it counts.
3. **Diagnosis**: **test the reframed hypothesis first** (see Reframe below) —
   do over-split failures cluster at bracket-group/family boundaries, and does per-page
   failure rate scale with the number of groups? Then, separately, does *any* failure
   stratify by publisher (esp. does the systemic barline's survival correlate with
   edition/scan quality)? Classify each failure: over-split at family boundary /
   over-merge from stray ink / staff-detection upstream / vocal-gap / brace / other.
4. **Fix** (order set by diagnosis): (a) **audit the `x_start` scan window** for an
   off-by-one that drops the systemic barline — cheapest possible partial fix; (b) make
   connectivity **constructive** (union-find over connectors, no gap stage) as Audiveris
   does; (c) add **classical-CV bracket detection** to the left of `x_start` (3× the
   barline's ink; groups' boundaries become explicit); (d) add the **positive
   header-column system-start test** reusing existing header readers. Prefer
   page-measurable, publisher-invariant evidence over per-publisher config; publisher
   profiles acceptable only as dossier/catalog-supplied hints that degrade gracefully
   when absent. Never tune on one corpus.
5. **Verify**: benchmark re-run; currently-correct pages stay correct (byte-identical
   where possible); orchestral e2e + dossier-join impact measured.

## Ground rules

- Measure on both a sweep corpus and a precision corpus before believing any change
  (the clef-work lesson: every threshold that passed one corpus failed another).
- GT provenance recorded per page; ambiguous pages flagged, never guessed.
- No commits until results are real; irreplaceable GT gets committed as soon as it exists.

## Log

- 09-01: kicked off; research agents A/B/C launched.
- 09-01: **Agent A (repo state) landed** — `research/repo-state.md`. Mechanism
  corrected (connectivity-primary; standing failures are over-merges); the existing GT
  is 65% one publisher (Litolff 1870, adjacent plate numbers), which explains why every
  candidate rule that passed it died elsewhere; edition-dependence is already named as
  the mechanism in `RULE_FIX_ATTEMPT_2026-08-31.md`. A's 172-page/86-publisher pilot
  (copied to `pilot/`) found new failures on publishers outside the GT: Augener 1914
  over-merge via fingering ink (bridging=9), Eulenburg 1920 spurious single-staff
  system `[1,11,11]`. Sweep cost ~1 s/page; render must normalize to target pixel
  height (~3300 px), not fixed DPI. GT adjudication method: left-margin bracket crops,
  never whole-page thumbnails (recorded methodology lesson).
- 09-01: **Agent B (corpus) landed** — `research/corpus-inventory.md`. The central
  library already exists on disk: 122 PDF editions with IMSLP-verified publisher
  metadata (118/122 authoritative), 1,745 reference MXL, 24 works with both. B&H is
  31% of pages. **Zero cross-publisher pairs inside the 122** — but Mozart K.183
  exists as B&H 1880 (library) + Bärenreiter NMA (Downloads): the one true publisher
  pair, usable read-only. Three same-plate two-scan pairs (B5, Brahms 1, Mozart 41)
  are scan-variance controls. Mahler 5's publisher is genuinely unknown (two files
  disagree; treat as unknown).
- 09-01: **Agent D launched** (Sonnet): full-library sweep + partition-level scoring
  harness + import of all existing free GT (23 eval cases, phase1 baseline, La Mer
  p25, B5 p47), incl. the K.183 publisher pair and same-plate scan pairs.
- 09-01: **Literature survey landed** (sub-agent of C) —
  `research/literature-system-segmentation.md`. Two negative findings that define the
  territory: (1) no published system-grouping accuracy exists on orchestral-density
  scores (benchmark corpora average 1.8–3.1 staves/system); (2) no paper isolates
  publisher/engraver as the variable — this benchmark is the first such measurement.
  The only published grouping heuristic (Egozy & Clester: white-space gap) is the one
  this repo already disproved; MUSCIMA++'s bracket+brace+systemic-barline
  `staff_grouping` relation is the right conceptual model for a fix but was never
  implemented as an algorithm. Reusable asset: v-dvorak/omr-layout-analysis YOLOv8m
  (public, 0.83 s/page CPU) as a possible cross-check miner — untested at orchestral
  density; check license first.
- 09-01: **Engine survey landed** — `research/omr-engines-survey.md`. Every shipping
  engine that handles orchestral scores uses bracket-anchored grouping PLUS a manual
  repair affordance; ScanScore documents our exact F1 over-merge cause ("vertical
  elements that appear to connect multiple systems"); capella-scan's user-supplied
  "System Template" validates the dossier/publisher-profile direction; homr (AGPL —
  quarantine, never port) does pairwise bracket/brace-overlap grouping + transitive
  closure.
- 09-01: **Audiveris deep-dive landed** — `research/audiveris-grid.md`. The mature
  engine builds systems **constructively from a peak graph** (union-find over ink
  connectors) with **no gap-distance stage at all** — confirms our finding in the
  design of the best OSS OMR engine, and shows the fix shape: constructive
  connectivity + a privileged left "starting column" + bracket/brace read to its left +
  a header-column cross-check. LEGATO 2 (SOTA, weights unreleased) is the only
  published orchestral-capable system detector: mAP50 0.990 but no per-density
  breakdown.
- 09-01: **Conventions memo landed** — `research/publisher-conventions.md`. **REFRAMES
  the project** (see Reframe below). A controlled LilyPond experiment shows the only ink
  crossing an instrument-family boundary is the ~0.16-staff-space systemic barline at
  the extreme left edge — **~2 px at pocket-score/300 dpi**, sitting at exactly
  `x_start`. Barlines-follow-brackets is a near-universal convention (MOLA + all 4
  engines + MusicXML/MEI), so failures persist across editions by mechanism, not house
  style; publisher enters second-order (does that 2-px rule survive this plate/scan?).
  Actionable: (1) a **falsifiable prediction** — failures cluster at family boundaries,
  scale with n groups — testable from the sweep now; (2) **audit the `x_start` scan
  window** (off-by-one would drop the systemic barline); (3) CLAUDE.md's "bracket
  encloses exactly the system" is wrong (per-family brackets, not one). External GT
  found: AudioLabs measure boxes (Wagner Ring + others, multi-publisher).

- 09-01: **Sweep + diagnosis landed** — `SWEEP_SUMMARY.md`, `DIAGNOSIS.md`. 964 pages /
  235 editions swept layout-only. Current rule reproduced at 20/23 via three independent
  paths; same 3 over-merge failures. **The failure axis is SCORE TYPE, not publisher:**
  vocal/choral pages fragment ~2× more (run-of-≥3-lone-staves 2.5% vocal vs 0.0%
  instrumental); instrumental grouping is ~0% fragmentation across every publisher
  (Breitkopf/Litolff/Eulenburg/Peters/Simrock/Jurgenson/Durand/Bärenreiter all clean).
  Confirmed visually: Bruckner Te Deum (choral pocket score) shatters a 2-system page
  into ~10 fragments — vocal staves aren't barline-joined (convention) + pocket-score
  thin systemic barline. Two failure directions: over-SPLIT ← vocal gaps (the prize),
  over-MERGE ← stray ink on dense instrumental pages (the 3 known). "Publisher effect"
  is really SCAN quality (B5 p57 same plate, 2 scans → [17] vs [9,15]). K.183 pair
  groups cleanly both ways (the [8,8,8]/[7,7,7] diff is staff count, not grouping).
- 09-01: **x_start audit landed** — `xstart-audit/`. The hoped-for cheap window fix is
  REFUTED: `_robust_x_window` already sits 4sp left of x_start with ~5.4sp headroom;
  a 1px systemic barline is counted; controlled LilyPond GT confirms family/vocal gaps
  bridged correctly. No window fix. The one remaining structural gap it names — a gap
  bridged only by a bracket/brace spine >4sp left of x_start — is a bracket-DETECTION
  problem, i.e. exactly the Audiveris-style bracket read the fix already plans. Diagnosis
  + audit converge: no shortcut; fix = constructive rebuild with bracket + header-column
  redundancy so grouping doesn't depend on a fragile 2px line surviving the scan.

## Reframe (09-01, after research)

Sean's question was "do the rules change by publisher?" The evidence says: **the
rule that breaks grouping is a near-universal engraving convention** (interior
barlines are broken between instrument families; only the thin left-edge systemic
barline crosses a family gap), which is *why* failures persist across editions rather
than sorting by publisher. **Publisher is a real but second-order modifier** — it
governs whether that ~2 px systemic barline survives a given edition's plate wear,
scan quality, and page size. So the benchmark still stratifies by publisher (to
measure that modifier and to avoid the 65%-one-publisher trap the old GT fell into),
but the primary diagnostic is **failure-vs-family-boundary**, not failure-vs-publisher.
The fix direction is Audiveris-shaped and publisher-invariant: constructive
connectivity + explicit bracket detection + a positive header-column start test, with
publisher/dossier hints only as graceful-degradation fallback.
