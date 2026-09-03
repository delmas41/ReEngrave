# Runbook — first real-batch measurement of the MXL-guided pre-fill

**Batch:** `benchmarks/omr-labeling-hollow2-2026-09-breitkopf-brahms1` (Brahms 1,
movement I, Breitkopf, PDF pages 1-3). Chosen because the scan benchmark already
holds a hand-verified row for page 0 of the SAME PDF, and the reference
encoding is in the library. (The Mahler batch cannot be used: the library has
no Adagietto reference.)

Everything runs on the Mac, in the main checkout. Each step is one command;
read the line under it before moving on.

## 0. Get the code

```bash
cd ~/Desktop/ReEngrave
git fetch origin
git checkout claude/score-labeling-training-system-iech0i
python3 -m pytest tools/omr/tests/test_mxl_verdicts.py tools/omr/tests/test_draft_windows.py -q
```
Expect all green. If not, stop and paste the output back.

## 1. Transcribe the batch's three pages (a few minutes)

```bash
python3 -m tools.omr.transcribe \
    library/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf \
    --pages 1-3 \
    --out benchmarks/omr-labeling-hollow2-2026-09-breitkopf-brahms1/transcription.json
```
This is the reading the reference will check. It must cover exactly pages 1, 2, 3.

## 2. Draft the window rows

```bash
python3 -m tools.omr.training.draft_windows \
    --transcription benchmarks/omr-labeling-hollow2-2026-09-breitkopf-brahms1/transcription.json \
    --base benchmarks/omr-scan-e2e-2026-09/works.json --row-id brahms-sym1-mvt1-317803-p1 \
    --out benchmarks/omr-labeling-hollow2-2026-09-breitkopf-brahms1/windows.json
```
It prints, per page, the measure range it inferred and a list of things to check.

## 3. Check the draft against the print (the only hand work)

Open `windows.json` and, for each of the three pages, confirm two things
against the PDF page:

1. **`first_ref_measure`** — page 0 is measures 1-7, so page 1 should start at 8.
   Count the bars on a tacet staff of page 1 to get page 2's start, and so on.
   The draft already did this from the reading; you are confirming it.
2. **Each system's `staves` list** — the instrument names in the margin, top to
   bottom, and which reference parts each staff carries (the `parts` numbers
   come from the page-0 row: `[0, 1]` is 2 Flöten, `[16]` is 1. Violine, …).
   Any staff with `"parts": []` needs its numbers filled in.

When a page is right, delete its `"confidence": "draft"` line. Leave a page
marked draft if unsure; its cells will still run, the marker is for you.

## 4. Dry run

```bash
python3 -m tools.omr.training.mxl_verdicts \
    --bench-dir benchmarks/omr-labeling-hollow2-2026-09-breitkopf-brahms1 \
    --transcription benchmarks/omr-labeling-hollow2-2026-09-breitkopf-brahms1/transcription.json \
    --truth library/reference/brahms/symphony-1/brahms--symphony-1--mvt1--gradus.mxl \
    --windows benchmarks/omr-labeling-hollow2-2026-09-breitkopf-brahms1/windows.json \
    --dry-run
```
Read the summary: how many cells pre-filled, how many abstained and why. Nothing
is written. If most cells abstain with "measures" in the reason, step 3's
measure numbers are off; with "staves" in the reason, a system's staff list is.

## 5. Write the hints only, then label as usual

```bash
python3 -m tools.omr.training.mxl_verdicts \
    --bench-dir benchmarks/omr-labeling-hollow2-2026-09-breitkopf-brahms1 \
    --transcription benchmarks/omr-labeling-hollow2-2026-09-breitkopf-brahms1/transcription.json \
    --truth library/reference/brahms/symphony-1/brahms--symphony-1--mvt1--gradus.mxl \
    --windows benchmarks/omr-labeling-hollow2-2026-09-breitkopf-brahms1/windows.json \
    --write-hints
python3 -m tools.omr.annotate.server --bench-dir benchmarks/omr-labeling-hollow2-2026-09-breitkopf-brahms1
```
In the cell list pick **Order: Queue**. On each cell the dotted ghosts are the
notes the reference says are there and the reading did not find — on a
hollow-notehead pass, those are mostly the half and whole notes you are
looking for. Label the batch the normal way (`h` hides the ghosts). Your boxes
stay yours; the pre-fill has not written a single verdict.

## 6. Score the pre-fill against your labels

```bash
python3 -m tools.omr.training.mxl_verdicts \
    --bench-dir benchmarks/omr-labeling-hollow2-2026-09-breitkopf-brahms1 \
    --transcription benchmarks/omr-labeling-hollow2-2026-09-breitkopf-brahms1/transcription.json \
    --truth library/reference/brahms/symphony-1/brahms--symphony-1--mvt1--gradus.mxl \
    --windows benchmarks/omr-labeling-hollow2-2026-09-breitkopf-brahms1/windows.json \
    --score --dry-run
```
It prints precision and recall of the boxes the pre-fill WOULD have written,
against the hollow-notehead boxes you drew. Paste that output back. That
number decides whether the other batches get `--write` (pre-filled verdicts
you only review) or stay on `--write-hints`.

## 7. Commit

```bash
git add benchmarks/omr-labeling-hollow2-2026-09-breitkopf-brahms1/windows.json \
        benchmarks/omr-labeling-hollow2-2026-09-breitkopf-brahms1/verdicts/ \
        benchmarks/omr-labeling-hollow2-2026-09-breitkopf-brahms1/prefill/
git commit -m "labeling: Brahms 1 / Breitkopf hollow batch, with window rows and the pre-fill score"
```
(`transcription.json` is large and regenerable; leave it out.)
