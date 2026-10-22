# Note accuracy on a real scan

Every note-accuracy figure in this repository comes from engraved input.
`benchmarks/omr-end-to-end` authors a score, renders it through LilyPond and
recognises the result; `benchmarks/omr-orchestral-e2e` does the same to an
excerpt of a Gradus MusicXML at eighteen staves. Both are honest about it —
`orchestral_eval.py` says so in its docstring — and both are the right tool for
isolating recognition from print quality. Neither says anything about a scan.

That gap has cost this project real money. Three shipped constants
(`rhythm.py:120`, `transcribe.py:1783`, and the 300-vs-600 DPI policy) have
their only supporting evidence on engraved input, and four confident
conclusions were retracted in one week for adjacent reasons. This benchmark
exists to put ONE number on the other side of the line: how many of the notes
printed on a real, degraded, 19th-century orchestral page does the pipeline
actually read.

## Status: the tripwire is refusing, and there is no number yet

`build_truth.py` will not emit a truth file for `beet5-p2`, so `score.py` will
not produce a score. This is the designed behaviour, not a bug in the harness:

```
  system 0 measures hand  17   phase1  16   MISMATCH
      per staff: [16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16]
      phase1 barlines, system 0 staff 0 (px @ run dpi):
        419  824  1052  1198  1354  1504  1803  1915  2125  2331 …
      cell widths — a merged pair reads about double its neighbours:
        405  228  146  156  150  299  112  210  206  211 …
  system 1 measures hand  15   phase1  15   ok
```

The page carries 32 bars (mm.17–48); Phase 1 finds 31. The disagreement is one
missing barline, and `build_truth.py` localises it on every refusal — that is
what the width row is for. The 299 px cell sits among neighbours of 112–228 px:
Phase 1 has merged two bars into one cell. Comparing its boundaries with the
hand-read ones for the same staff, at 450 dpi:

| | boundaries (px @450 dpi) |
|---|---|
| hand | 436, 835, 1064, 1204, 1361, 1510, **1710**, 1809, 1922, 2128, 2333, 2545, 2747, 2943, 3136, 3341, 3530, 3737 |
| Phase 1 | 419, 824, 1052, 1198, 1354, 1504, — , 1803, 1915, 2125, 2331, 2542, 2743, 2943, 3134, 3341, 3518, 3742 |

Every boundary agrees within about ten pixels except **x ≈ 1710**, the m.22/m.23
barline, which Phase 1 does not see; it emits one 299 px cell where the page has
a 200 px bar and a 99 px bar. That barline is plainly visible on the scan, and
it is visible on the Timpani staff, which is resting there and so has no stem
that could be mistaken for it.

So the next step is a Phase 1 fix, not a truth-set edit. When Phase 1 reports 17
and 15, `build_truth.py` writes the file and `score.py` produces the number
with no further changes.

**Do not make the hand count match the pipeline.** The hand count is right (see
below), and moving it would turn this benchmark into a measurement of the
pipeline's agreement with itself.

## What the bar range rests on

The bar range is the only input here with no independent source, and a wrong one
produces a score indistinguishable from a real one — real music, correctly
extracted, from the wrong place. `pages.py` records the evidence beside the
number. In short: page 1 of the print carries 16 bars; the Timpani's
rest/three-eighths/quarter figure at the top of page 2 is mm.17–21 in the
MusicXML; six Violino I landmarks (`f` m.19, the F♯ of the A♭/F♯/C chord m.20,
fermata m.21, `ff` m.22, fermata m.24, `p` m.25) each fall in the bar a 17-bar
system predicts; the Flauti's 5 rests / 5 `sf` bars / 5 half notes in system 2 is
mm.34–48; and 16 + 17 + 15 = 48 closes without being fitted.

`landmarks.py` prints that checklist for any range you want to test, so the
human half of the check is repeatable:

```bash
python3 benchmarks/omr-real-scan-notes-2026-08/landmarks.py --page beet5-p2
python3 benchmarks/omr-real-scan-notes-2026-08/landmarks.py --page beet5-p2 --first 1 --last 40
```

A barline-counting probe was written for this job and deleted. On this print a
column-of-ink test returns 15, 16 or 17 bars for the same system depending on
the ink threshold — note stems make full-height columns and faded barlines do
not — so it agreed with the truth about as often as it disagreed. A cross-check
that is wrong half the time is worse than none, because it would talk a later
reader out of a correct count.

## What this measures

For the parts that own a printed staff **by themselves**, on one page of one
real scan: how much of the written-pitch note sequence the pipeline recovers.

- **Truth** is the Gradus MusicXML for the work, restricted to the page's bar
  range. `PROJECT_STATUS.md` sanctions this use — "The MusicXML feeds
  verification and benchmarking, not label generation." No bounding boxes are
  placed and none are implied: the closed MXL→bbox recipe (F1 0.064,
  `benchmarks/omr-mxl-autolabel/FINDINGS.md`) is about per-symbol PLACEMENT for
  training labels. This is sequence comparison for scoring.
- **Pitch is written pitch** — what is printed — matching the dossier
  convention. MusicXML stores written pitch plus a `<transpose>`, so no
  conversion happens; the transposition of every scored part is recorded in the
  truth file so the choice stays visible. All four parts scored on `beet5-p2`
  are non-transposing.
- **Alignment** is the longest-common-subsequence over pitch names from
  `tools/omr/training/end_to_end_eval.py`, imported rather than reimplemented,
  so this row and the engraved rows are the same measurement on different input.
  It is deliberately generous: it does not care where a note sits in the bar,
  only that the sequence of pitches is right.

### Only 1:1 parts, and why that is not a shortcut

A printed conductor's score condenses — Flauti 1 and 2 share a staff — while the
MusicXML keeps them as separate parts. Unioning the condensed parts to make a
staff's truth over-counts it, and there is no defensible note ORDER for the
result. On this page that would corrupt 7 of the 11 staves. So `beet5-p2` scores
four: **Timpani, Violino I, Violino II, Viola**. The other seven are listed in
`pages.py` with the parts that share them, and `build_truth.py` refuses if any
MusicXML part is neither scored nor explicitly excluded — so a part cannot go
missing silently.

Beethoven 5's Violoncello and Contrabass are separate parts printed on one staff
on this page, so the cello staff is excluded too, even though a different page
of the same work might print them apart.

## What this does NOT measure

- **Not the page.** Four staves of eleven. The excluded seven are the dense
  condensed ones, and nothing here predicts how the pipeline does on them.
- **Not the pipeline's accuracy in general.** One page, one edition, one
  publisher's print quality, one work, one composer, 259 notes.
- **Not a scan-vs-engraved contrast** on its own. It has the same alignment as
  the engraved benchmarks, which makes a contrast *possible*, but the works and
  textures differ, so a gap between this number and an engraved one is not by
  itself a print-quality effect.
- **Not rhythm or voicing.** Duration accuracy is reported only over notes whose
  pitch already matched, so it is conditional and cannot be read as a duration
  score. The alignment ignores bar position entirely.
- **Not clefs, key signatures, dynamics, articulation, or any structural
  element.** Those have their own benchmarks.
- **Nothing about ordering within a chord.** Chords are expanded to one entry
  per pitch, so a chord read with the right pitches in the wrong order still
  aligns.

## The caption the number must always carry

Any figure from this benchmark travels with this sentence, which `score.py`
prints and writes into its report as `caption`:

> **beet5-p2 @ 450 dpi, mm.17-48: 4 of the page's 11 staves — the parts that own
> a printed staff alone — 259 notes. Real scan.**

Without it, a recall figure from here reads as "the pipeline's accuracy on this
page", which is not what was measured and is the exact error this benchmark was
built to stop repeating.

## What DPI means here

The page runs at **450 dpi**, which is the corpus convention for these two IMSLP
orchestral scans — it is what `benchmarks/omr-corpus-sweep-2026-08/sweep.py`
uses and what `benchmarks/omr-key-signature/ground_truth.json` records — and is
**not** the pipeline default of 600. `end_to_end_eval.py` warns that a benchmark
run at a non-default setting measures a configuration nobody uses; that warning
is about silently pinning a stale value, and this is a deliberate, documented
choice that keeps the real-scan row comparable to the other measurements on the
same two PDFs. A number from here is a number at 450 dpi and should say so.

Because `CLAUDE.md` records DPI as a genuine sparse-vs-dense tradeoff that must
not be "fixed" without measuring both, the right follow-up is to run this page
at 600 as well and report both, not to pick one.

## Files

| file | what it is |
|---|---|
| `pages.py` | The pages, the hand-read facts, and the evidence for the bar range. The only place a human-supplied number lives. |
| `build_truth.py` | Runs the tripwire; on agreement writes `truth/<page>.json`. Non-zero exit and no file on disagreement. No override flag, by design. |
| `score.py` | Re-checks the tripwire against the run it is about to score, aligns, reports per part and overall. |
| `landmarks.py` | Prints the printed marks that let a human confirm a bar range by eye. |
| `omr_run.py` | One cached pipeline run per page, shared by the other two so they cannot disagree about which run they mean. |
| `pipeline-runs/<page>.omr.json` | The cached pipeline output. **Not committed** — the root `.gitignore` rules that a run dump is not a record ("Commit the REPORT that cites the numbers, not the dump it read them from"), and it regenerates in about half a minute. The report is the boundary table above. |

## Running it

```bash
# 1. tripwire + truth  (refuses today; see Status)
python3 benchmarks/omr-real-scan-notes-2026-08/build_truth.py --page beet5-p2

# 2. score  (requires the truth file from step 1)
python3 benchmarks/omr-real-scan-notes-2026-08/score.py --page beet5-p2 \
    --out benchmarks/omr-real-scan-notes-2026-08/results/beet5-p2.json
```

Both reuse `pipeline-runs/<page>.omr.json`. **Pass `--fresh` after any pipeline change**
— otherwise the tripwire asserts against an old Phase 1 and the score describes
a build that no longer exists.

## Adding the second page

`pastoral-p2` (Beethoven 6, `imslp-504082`, `page_index` 1) is the intended
second entry and is **not** added yet, because `beet5-p2` is not clean. It adds
five separate 1:1 string staves — Violino I, Violino II, Viola, Violoncello and
Basso are printed apart there — which is why it is worth having: it more than
doubles the scored staff count and it is a second print with its own defects.
Adding it means writing a `PAGES` entry with a bar range established the same
way, by looking at the scan and checking the landmarks. Do not copy the beet5
range; it is a different page of a different work.
