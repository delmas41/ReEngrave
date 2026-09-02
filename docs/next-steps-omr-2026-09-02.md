# Where the OMR work stands — 2026-09-02

Successor to `next-steps-omr-2026-09-01.md`, written at the end of the
overnight session recorded in [overnight-2026-09-01-summary.md](overnight-2026-09-01-summary.md).
The change since the predecessor: **generalization is measured now.** The
engraved benchmark widened from 3 works to 10, the scan domain went from one
anecdotal page to a five-row benchmark, and the fixes both corpora produced
are landed. Figures live in their home files — the canonical pooled figure in
CLAUDE.md's OMR-NED section, the widened corpus in
`benchmarks/omr-corpus-widening-2026-09/FINDINGS.md`, the scan table in
`benchmarks/omr-scan-e2e-2026-09/RESULTS.md` — and are deliberately not
restated here (the copies-go-stale lesson is a year old now; pointers only).

## How to reproduce the three numbers

```bash
python3 -m tools.omr.training.orchestral_eval --omr-ned          # canonical 3
python3 -m tools.omr.training.orchestral_eval --omr-ned \
    --works mozart-sym41-mvt1 mozart-sym40-mvt1 brahms-sym4-mvt1 \
            bruckner-sym5-mvt1 dvorak-sym9-mvt4 tchaikovsky-sym6-mvt2 \
            tchaikovsky-sym4-mvt2 beethoven-sym3-mvt1 \
    --work-dir benchmarks/omr-corpus-widening-2026-09/fixtures    # widened 8
python3 benchmarks/omr-scan-e2e-2026-09/scan_eval.py              # scan 5
```

## Ranked next steps

### 1. The hollow noteheads — the scan domain's top lever, and it needs Sean

Unchanged from the predecessor but **re-priced upward**: the scan benchmark
shows duration recall as the weakest column on *every one of five publishers*,
and the condensation attribution shows the scan residue is a **reading**
problem (53.3% `wrong note` once the part convention is accounted for). The
48-cell labeling batch is prepared and ranked by meter shortfall; it is the
one item on this list that needs human hands.

### 2. Boulanger's segmentation — the one thing that would make its row readable

The only work of ten whose row is dominated by structure (43 of 46 parts
unpairable). Everything else on that page is *right* — 263 of 271 direction
marks exported correctly and charged anyway. Diagnose before fixing: is it
system grouping, part stitching, or the exporter's refuse-to-stitch guard
firing correctly on genuinely inconsistent staff counts?

### 3. The YOLO-band half of beam attachment

`rhythm._beams_attached_to_stem` now measures against the band (the sloped-
stroke fix, Mozart 41 −602 edits) — but a YOLO beam box bounds a *stack*, so
half its height is not slope. All 9 residual flips are Brahms 4's entire +2.
The clean fix is for the beam list to say what a band *means* (CV stroke vs
YOLO stack) rather than `rhythm.py` guessing from height. Small, well-bounded,
and touches the same seam as the earlier kept-beams rule — measure both.

### 4. `staff_header`'s window is sometimes the BRACKET

Now the **largest remaining time-signature cause** (Dvořák 9: header cells
301 px wide against 1600 at the same spacing, containing solid black), and it
starves every header reader equally — clef, key, meter. One fault, three
consumers. `benchmarks/omr-timesig-2026-09/FINDINGS.md` names the page.

### 5. Small, evidenced, queued

- **Attribute the Mahler scan row's +37** (0.8149 → 0.8412 across the night,
  concentrated in `wrong timesig`/`wrong keysig`): toggle the meter agreement
  floor and the key-vote weight change on that one page — each was priced
  0-wrong on its own corpus, and this dense Peters scan sits outside both.
  The final-tree numbers are in the summary's verification section.
- Two lexicon one-liners: `Contrafagott` alias; strip Surya's stacked-numeral
  `\frac{1}{2}` in the normaliser (three labels on the Dvořák row).
- The Litolff `3` / Bravura `6` template collision (6 staves on Beethoven 3 —
  currently a correct abstention, recoverable with a second font or a
  digit-confusion gate).
- `eval_first_run.py`: positional measure slice is off by one on pickup works;
  it and `orchestral_eval` still read `~/Desktop/gradus-vercel/public/scores/`
  directly instead of the library.
- `SURYA_BAKEOFF_2026-08-31.md`'s w14/w20/w26 table no longer reproduces (the
  lexicon it scored through has changed); conclusion survives, stated reason
  doesn't — correct the doc.
- The Mahler 5 scan page prints a **22nd staff** (one-line percussion, no
  reference part); one-line percussion is priced at 182 edits of that row and
  is structural (a five-line detector cannot see it) — a scoring-convention
  decision, not a fix.

### 6. Decisions for Sean

- **Does the 8-work corpus join the tracking benchmark?** Tonight it reports
  beside the canonical 3; folding it in changes `DEFAULT_WORKS` and the
  headline's meaning.
- **Direction text default-on** (unchanged from the predecessor).
- **The `magical-bhabha` port** (web-app measure patching — cheap, already
  specified by 2 failing tests on main) when web-app time comes around.

## Do not spend time on these — additions this session

The predecessor's list stands (system-break threshold rules, detector
fine-tuning, synthetic augmentation, VLM transcription). Added, each with its
measurement in tonight's docs:

- **Key-signature inference from the music** — ceiling measured on ground
  truth: 36.7% at page scope, breaks the 4♯ control. The vote fixes replaced it.
- **Routing `accidental*` into the key readers** (item #8) — refused twice,
  now with the mechanism named: precedence. It must enter last, into gaps
  only, if ever.
- **Adding 4/8 to the meter candidate list** — changes not one line; the
  candidate-list gap is ~1% and is not the lever.
- **Cut-common as a searched template** — still wrong (3 → 12 wrong when
  tried); the shipped answer reads the stroke *by position* after `C` wins.
- **Widening `end_window` for beam attachment** — reaches the sloped-stroke
  stems only at 1.30×, admitting 77 indiscriminate pairs against the band
  rule's 49.

## Environment

Unchanged from the predecessor (two gitignored venvs, `OMR_SURYA_KEEP_ALIVE=1`
in `~/.zshenv`). Worktrees need three symlinks into the main checkout —
`.venv-omrned`, `.venv-surya`, `tools/omr/training/data` — after which the
full benchmark stack runs from a worktree; verified this session.
