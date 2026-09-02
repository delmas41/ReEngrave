# Overnight session summary — 2026-09-01 → 09-02

The companion to [overnight-2026-09-01-plan.md](overnight-2026-09-01-plan.md):
what actually happened. Seven workstreams ran (four planned, one added when Sean
asked about time signatures mid-evening, two dispatched on what the new
measurements found). Everything below is committed and pushed on
`claude/transcription-overnight-progress-426c90`; the final-tree verification
figures at the bottom were measured on the settled tree after the last commit.

## The night in one paragraph

The plan was measurement-led generalization, and it paid immediately: a new
8-work engraved corpus opened at **twice the error rate** of the three pages
everything had been tuned on (0.2770 vs 0.1364) and ended the night at
**0.1613**; a new 5-row scan benchmark — the first ever — opened at **0.7960**
pooled and got its first four fixes; the time-signature issue Sean asked about
turned out to be real and *mischaracterized* (cut-common pages were not
abstaining, they were reading as common time — 2/2 shipped as 4/4 on 15.5% of
the repertoire — now 0 wrong on an 11-source corpus); key-signature-from-music
was closed as a measured NO-GO and replaced by two vote fixes the research
uncovered; and the canonical benchmark improved from 0.1364/966 to
**0.1328/942** while staying byte-identical under every fix that shouldn't
touch it. The unit suite grew 1468 → **1567**, all green.

## Workstream results

### A — the engraved corpus widened from 3 works to 10
Home: [benchmarks/omr-corpus-widening-2026-09/FINDINGS.md](../benchmarks/omr-corpus-widening-2026-09/FINDINGS.md)

Ten works selected across eras (Mozart ×2, Beethoven 3, Brahms 4, Bruckner 5,
Dvořák 9/iv, Tchaikovsky ×2, Boulanger; Mahler 5/iv failed to render and is
recorded, not fought). The near-neighbour controls passed — nothing in the
prior sixteen fixes was page-shaped — but the corpus found **three more
"detected and dropped" categories** (instances 7–9 of the repo's most-paid
lesson): the time-signature *symbol* (cut/common lost while the numbers
survived — every delta exactly 3 × staff count, predicted per work before the
run, 5/5), triplet digits arriving classed as `fingering3` and filtered by a
structural gate (which exposed a latent double-ratio bug: a sixteenth
triplet's two beam strokes each applied 2/3 — Mozart 41 −464 edits), and
articulations (detected on every page, exported from none). One judgment call
shipped with the counter-argument recorded: the articulation fix costs +97
pooled edits *on Boulanger alone*, whose 43-of-46-part segmentation charges
correct symbols against unpairable bars.

New-corpus pooled (8 works, Boulanger excluded as segmentation-bound):
**0.2770 / 3691 → 0.2057 / 2793** by A's fixes, then → **0.1613 / 2193** after
G's beam fix. Canonical: 0.1364 → **0.1328 / 942**.

### G — the Mozart 41 residue: a beam band is not its centre
Home: [benchmarks/omr-corpus-widening-2026-09/MOZART41_BEAMS.md](../benchmarks/omr-corpus-widening-2026-09/MOZART41_BEAMS.md)

A's handoff blamed `line_detection`; the attribution overturned that — the CV
detector reads both strokes correctly, and `rhythm._beams_attached_to_stem`
was measuring each stem against the beam box's **centre**, which a *sloped*
stroke only occupies mid-group. The outermost stem of a rising run measured
half a band-height wrong, in exactly the direction that pushed it past the
window — one worked example sits 3 px past the fence. The counterpart function
in `line_detection` already made this correction *and documented why*. Fixed
by changing the measured quantity (band, not centre) with no constant touched:
31 of 1239 stems change corpus-wide, a strict widening. **Mozart 41
0.3632 → 0.1541** (worst row → fourth best, ×2 duration bucket 18 → 0),
canonical byte-identical. Refused with numbers: widening `end_window` instead
(reaches the same stems only at 1.30×, admitting 77 indiscriminate pairs
against the band rule's 49).

### B — the scan domain is now a benchmark, not an anecdote
Home: [benchmarks/omr-scan-e2e-2026-09/RESULTS.md](../benchmarks/omr-scan-e2e-2026-09/RESULTS.md)
(baseline) + [FIX_ROUND_2026-09-02.md](../benchmarks/omr-scan-e2e-2026-09/FIX_ROUND_2026-09-02.md)

Five scanned pages, five publishers, ground truth from the score library's
reference MusicXML trimmed to hand-verified page windows (the trimmer runs in
`.venv-omrned` and writes `.musicxml` — a suffix mismatch would make the
worker re-stage both files and launder the prediction's lenient parse).
Baseline pooled **0.7960** against 0.1328 engraved. Layout is *not* the
bottleneck — staff counts exact on all five pages. Duration recall is the
weakest column everywhere: **the invisible-half-notehead problem is
scan-general, not Beethoven-specific**, which prices the prepared labeling
batch as the scan domain's top lever.

Two designed comparisons paid off. Same plates scanned twice (proven identical
engraving): **resolution explains recall** (0.728 → 0.612 downscaled) **but
not OMR-NED**, which ranks the arms the other way because the low-res arm
emits fewer symbols — the symmetric-denominator trap measured from the other
side. And the condensation arm (`partsToVoices`, sanity-checked as an exact
no-op on the 1:1 Dvořák row): the convention explains **23.4%** of the pooled
edits, not the 29.6% the structural bucket claimed — and 47% of what leaves
the structural buckets **returns as note-level reading errors** (`wrong note`
rises from 22.7% raw to 53.3% condensed). The scan problem is a *reading*
problem more than a part-model problem.

### F — four scan-side fixes, each with a measured distribution behind it

1. **A part's opening clef came from measure 0** even when measure 0 is
   furniture — all 15 Dvořák parts exported treble while their per-measure
   clefs were right. Now the first clef-*bearing* measure; LilyPond fixed too.
2. **The margin-label crop still clipped leading characters** — measured
   label reach across 5 editions / 74 staves runs to 26.4 spacings and the
   crop stopped at 20, cutting labels on *all five publishers including the
   edition the 2026-08-31 fix was tuned on*; 30 sits in a measured empty band
   (nothing between 26.4 and 45). Labels character-identical at 20/26/30.
3. **The `Basso` disambiguation mechanism had never fired** — the ambiguous
   label was fed as an *input* to the layout fit meant to overturn it, and the
   resolver asked a one-way question where its own question is two-way.
   `ambiguous_labels_resolved` 0 → 1; an SATB control still resolves to voice.
4. **Furniture measures** (a brace-only or lone-meter-digit cell at a system's
   head or tail): 243 columns probed across 27 systems — exactly 2 are
   music-free on every staff, both furniture, one of them too wide for any
   width rule. Dvořák measures 9/8 → **8/8**.

Dvořák row 0.5873 → **0.5667**, labels 45 → 54 staves named corpus-wide,
canonical unchanged to the edit throughout. Refused with numbers: the
courtesy-meter column on Brahms stays (it holds nine notehead false positives,
so no honest content rule catches it).

### E — the time-signature issue (Sean's mid-evening ask)
Home: [benchmarks/omr-timesig-2026-09/FINDINGS.md](../benchmarks/omr-timesig-2026-09/FINDINGS.md)

**It still existed, and not in the recorded shape.** August closed at 8/0/21
naming *silence* as the residual gap; on a corpus widened 5 → 11 sources the
reader was **wrong three times**, and the biggest wrong class was the one the
record called safe: withholding the cut-common template does not make a ¢ page
abstain — plain `C` wins on a subset of the ¢'s own ink and the page ships as
4/4, *unanimously* (Mozart 40: 11 staves of 11). **15 of the 97 dossier works
open on a ¢.** Fixed by position, not shape: after `C` clears threshold and
vote, the stroke is *read* in the centre column (cut staves fill 1.00 of it,
common 0.00–0.30 — every threshold in 0.50–1.00 identical), so there is no new
false-positive surface by construction. Plus an agreement floor moved into a
measured gap (correct readings agree ≥0.909; the one wrong at exactly 0.500).
End-to-end: **3 wrong → 0 wrong**, 10 → 12 correct, abstentions honest. The
candidate-list gap measured at ~1% (only 4/8 missing — adding it changes not
one line; refused). What a wrong meter costs, priced: **+226 bar-check
failures over abstaining** on one movement — with the methodology trap
recorded that the bar-check count rewards the longer meter, so it may only be
read when the favoured meter is the shorter one.

### C — key signatures: inference refused, the vote fixed instead
Home: [benchmarks/omr-keysig-from-music-2026-09/](../benchmarks/omr-keysig-from-music-2026-09/) (PHASE1.md, PHASE2 results)

Inferring the signature from the music — wanted since the roadmap — is a
**measured NO-GO**: the ceiling, taken on ground-truth MusicXML before any OMR
(118 works / 773 parts), is 57.6% accuracy at movement scope and **36.7% at
the 8-bar scope a page offers**; 26% of parts are self-contradictory because
music modulates; and it reads the 4♯ control page as 7♯. Both pages that
motivated the idea were **mis-attributed**: Beethoven 5 p.15 had three staves
reading the correct 3♭ *rejected by the vote* (a defaulted-clef reading's
weight **replaced** its accidental count, so a 3-flat and a 1-flat reading
arrived identical at 0.5, and the reference fell to two under-counting
readers), and Boléro p.10 *genuinely prints five signatures* — Ravel
polytonality, read correctly — its only errors being template flats asserting
on empty headers through the no-majority branch. Both vote bugs fixed:
**p.15 0 correct/6 wrong → 3 correct/1 wrong** (the residual wrong never
reaches the vote), **Boléro 6/5 → 6/0**, every other ground-truth page
identical, canonical byte-identical (the engraved works take signatures from
the dossier, so this path must not reach them — and doesn't). Item #8
(routing `accidental*` into the key readers) was re-measured on the fixed
reference and **refused a second time, with its mechanism named**: precedence
— the noisiest source runs first and pre-empts the readers that were
succeeding. If ever revisited it must enter *last*, into gaps only.

### D — the branch audits closed
Home: [docs/branch-assessments-2026-09-02.md](branch-assessments-2026-09-02.md)

`claude/omr-dossier-verification-layer-eaf6d0` — the last branch billed as
holding "a capability main lacks" — is **superseded on all four phases**
(one was landed as a deliberate cherry-pick main's own audit couldn't see, and
then measured inert; one *cannot* be generated from MusicXML because page
layout is an edition fact). Archive. `claude/magical-bhabha` (measure-level
MusicXML patching): **cheap port** — the target function is byte-identical to
March and main already carries tests specifying the behavior, 2 of 5 failing
against the stub. `claude/peaceful-kapitsa` (job queue): re-implement fresh if
ever; personal-use scope deprioritizes it.

## Cross-cutting lessons the night added

- **Corpus widening pays the same day.** Twice the error rate on music of the
  same kind, three new detected-and-dropped categories, and one false claim in
  CLAUDE.md disproven (Mahler's "markerless" fifth triplet carries a
  `fingering3` at 0.72 — the highest-confidence marker on the page).
- **The detected-and-dropped ledger now has nine entries** (beams, dots,
  dynamics, tuplets, slurs, articulations, timesig symbols, triplet digits
  under a foreign class, beam strokes discarded at the stem-attachment step).
  When a bucket is large, grep the JSON before blaming the detector.
- **A shared working tree defeats per-agent measurement.** Three agents
  independently hit mid-measurement drift from another's uncommitted edits;
  the mitigations that worked — sha256-pinning scored files, predicting a
  fix's delta from the JSON before running it, and final verification on the
  settled tree — are worth keeping as standing practice for multi-agent
  nights.
- **Withholding a capability is not abstention.** The cut-common lesson: a
  missing template didn't produce silence, it produced the *nearest wrong
  answer*. Absence has failure modes of its own.

## The morning list

1. **Serve the hollow-notehead labeling batch** (the one item needing human
   hands; ~48 cells, prepared and waiting — `python3 -m
   tools.omr.annotate.server --bench-dir <batch dir>` → http://127.0.0.1:5050).
   The scan benchmark confirmed duration recall is the weakest column on
   *every* publisher, so this is the scan domain's top lever.
2. **Decide whether the 8-work corpus joins the tracking benchmark** (it
   currently reports beside the canonical 3; changing `DEFAULT_WORKS` and the
   headline's meaning is Sean's call).
3. **Direction-text default-on** — unchanged decision, still Sean's.
4. Queued small fixes, each evidenced in tonight's docs: **(4a) attribute the
   Mahler scan row's +37** (which header-layer change moved it, by toggling
   the meter floor and key-vote weights on that one page); two lexicon
   one-liners (`Contrafagott` alias; the stacked-numeral `\frac` normaliser),
   the YOLO band-is-a-stack half of beam attachment (9 pairs, all Brahms 4),
   `staff_header`'s bracket-as-window fault (now the *largest* remaining
   time-signature cause), the Litolff `3`/Bravura `6` font collision,
   Boulanger's segmentation (the only thing that would make its row readable),
   `eval_first_run.py`'s positional-slice pickup bug + stale gradus-path
   dependencies, the `SURYA_BAKEOFF_2026-08-31.md` accuracy table that no
   longer reproduces (conclusion survives, stated reason doesn't), and the
   Mahler 22nd staff (one-line percussion, priced at 182 edits, structural).
5. **The `magical-bhabha` port** when web-app time comes around.
6. LEGATO 1.5 weights: still waiting on the author's HF review.

One administrative note: a side session was started from a chip filed early in
the night ("Correct PROJECT_STATUS.md's dossier-branch row"). That fix was
made on this branch directly (`ef06919`); if the side session produced its own
version elsewhere, prefer this branch's.

## Final-tree verification

Measured on the settled tree after the last workstream commit (`6687782`) —
this section is the reconciliation the shared-tree lesson demands:

- **Unit suite: 1567 passed** (from 1468 at the start of the night).
- **Canonical 3-work benchmark: pooled 0.1328 / 942 edits**, and
  `accuracy_record --check` agrees — the settled tree reproduces the recorded
  figure exactly.
- **Widened 8-work corpus: pooled 0.1613 / 2193 edits** — reproduces
  workstream G's landing figure exactly.
- **Scan 5-row benchmark: pooled 0.7987 / 9032 edits** against the baseline's
  0.7966 / 9051. Net −19 edits and +0.002 on the ratio, the symmetric-
  denominator effect once more (predicted symbols 5211 → 5158). Per row:
  Dvořák **0.5873 → 0.5667** (−59, F's fixes, measures 8/8), Beethoven rows
  stable to within an edit, Brahms +3 (the YOLO-band residue G's handoff
  names), **Mahler 0.8149 → 0.8412 (+37)** — concentrated in `wrong timesig`
  (34) and `wrong keysig` (56) on a dense Peters scan whose truth is 2/2 with
  four sharps and whose prediction reads scattered meters and mostly no
  signature. The +37 is a cross-workstream interaction of the header-layer
  changes (the meter agreement floor and the key-vote weights were each priced
  0-wrong on *their* corpora; this page sits outside both) and is **queued for
  attribution as morning item 4a** rather than hand-waved here. The scan table
  remains what RESULTS.md declares it: a baseline row set, not yet a
  regression gate.
