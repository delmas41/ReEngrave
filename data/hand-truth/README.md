# `data/hand-truth/` — hand-labeled page truth (ROADMAP 1.7)

Plan: [`docs/plan-2026-10-08-hand-labeled-truth.md`](../../docs/plan-2026-10-08-hand-labeled-truth.md). Code: `tools/omr/hand_truth/`.

| file | what | written by |
|---|---|---|
| `pages/<edition>/<pdf_page_index>.json` | one printed page: every box in PAGE pixels, the cells it was labeled through, pre-fills still in the queue, the staff-line checks, the page's state (`labeling` → `checked` → `verified`) | the labeling tool (`store.PageTruth.save`) — none yet |
| `pages/<edition>/<pdf_page_index>.pagepass.json` | the PAGE PASS (ROADMAP 2.287, Sean 2026-11-10): page-wide marks (staff, barline, bracket, clef, key, meter, word, dynamic, arc, hairpin, repeat) labelled once on the whole page. One list of `labels`: `kind`, `shape` (`{"rect":[x0,y0,x1,y1]}` or `{"poly":[[x,y],...]}`, PAGE pixels at the page's dpi), `pass` (`"page"`), `state` (`pending` = a pre-fill, NOT truth; `confirmed`; `rejected`, kept so it is never proposed again), `origin` (`drawn` / `prefill-confirmed` / `prefill-fixed`), `source`, `text` (words, dynamics), `sub` (`tie`/`slur`), `note` (a pre-fill's assumption), `ink_ref` (the claimed-ink reference: `rule` `pageink-1`, `mode`, `px`, `bbox`, `sha1` of the claimed mask). A label claims INK, not its rectangle: `tools/omr/hand_truth/pageink.py` documents the rule per kind. Cell-pass labels stay in `<page>.json`, which is never edited by the page pass | the labeling tool's page pass (`pagepass.PagePass.save`); first built by `python3 -m tools.omr.hand_truth.pagepass_prefill new <page>.json --arc-key prefill/imslp317803-0.arc-key-2.281.json` (pre-fills only) |
| `prefill/imslp317803-0.arc-key-2.281.json` | a COPY of the 2.281 corrected Brahms p0 arc key (e1e0bf726, `benchmarks/omr-arc-binding-2026-10/key-brahms-p0-corrected.json`: 100 arcs from 153 hand boxes), the arc pre-fill source for the page pass. A proposal list, not truth | copied, never edited |
| `INVENTORY.json` | every hand label in the tree, who judged it, how complete it is, and the weights lineage | GENERATED: `python3 -m tools.omr.hand_truth.inventory` (`--check` to verify) — never edit |
| `aligned/<edition>/<page>.<master>.json` | each labelled box's cell in the MASTER cell map (ROADMAP 2.231), by page rect, and why the old `cell_id` disagrees; Sean's page files are not touched | GENERATED: `python3 -m tools.omr.hand_truth.align` (`--check`, `--report`, `--control`) — never edit |
| `held-out.json` | pages that are test truth and never train weights tested on them | Sean's decision, 2026-10-08 |
| `weights-lineage.json` | which corpus trained which detector weights, with evidence | DECLARED; `inventory --verify-checkpoints omr-weights/` checks it against the `.pt` files |

Truth is what Sean acted on. A model pre-fill is a queue; Claude's double-check only flags.

## Two passes (ROADMAP 2.287): the page, then the cell

Pass 1 -- the page. Page-wide marks, once, end to end across barlines, in claim order, with ink tinted by state
(vermilion = nobody has claimed it, blue = claimed by what you confirmed, purple = under a pre-fill still waiting,
green = claimed in the cell pass). Pass 2 -- the cell pass below, with pass-1 ink laid over each cell in blue.

```bash
python3 -m tools.omr.annotate.server --page-pass \
    --page-store data/hand-truth/pages/imslp317803/0.json \
    --arc-key data/hand-truth/prefill/imslp317803-0.arc-key-2.281.json      # page pass alone: http://127.0.0.1:5050/page
# with the cell pass too (also pass-1 ink in the cell view): add --bench-dir $BENCH
```

The PDF is found in `library/` by the page file's name (or `--pdf`). The first request renders the page (a few seconds).

## Labeling a page, start to finish (on the machine with the PDFs and weights)

The first page is Brahms 1, Breitkopf `317803`, PDF index 0 (plan §3, page order).

```bash
PDF=library/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf
PAGE=data/hand-truth/pages/imslp317803/0.json
BENCH=benchmarks/hand-truth-sessions/imslp317803-p0

# 1. Cut the page (product-path cells + margin/top/bottom cells for every other bit
#    of ink) and queue the pre-fills: your old labels on this page, then the detector.
python3 -m tools.omr.hand_truth.session new --pdf $PDF --page 0 \
    --weights omr-weights/deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt

# 2. Label, one cell at a time, in the labeling UI you already use (http://127.0.0.1:5050).
#    t confirms a pre-fill, f rejects it, c/b fix it, draw what nobody proposed.
#    Words: class `text`, type them in Notes. Specks: `noise`. On a staff's first cell,
#    `t` each of the five thin `staff` boxes if that line is right. Tab moves on and
#    stamps the cell as swept. Every save lands in $PAGE in page pixels.
python3 -m tools.omr.annotate.server --bench-dir $BENCH --page-store $PAGE

# 3. Claude's check: the fixed checks + the ink-coverage control raise flags; Claude's
#    visual pass adds its own (`session raise ...`). You accept or reject each one.
python3 -m tools.omr.hand_truth.session status $PAGE --pdf $PDF
python3 -m tools.omr.hand_truth.session flag $PAGE f0 rejected      # or accepted (and fix the cell)
python3 -m tools.omr.hand_truth.session advance $PAGE --to checked --pdf $PDF

# 4. LilyPond, side by side, bar by bar: the reader with PERFECT EYES (your boxes in
#    place of the detector), then the review page. Mark every bar ok / label wrong /
#    reader wrong.
python3 -m tools.omr.hand_truth.perfect_eyes $PAGE --pdf $PDF --out $BENCH/eyes
python3 -m tools.omr.hand_truth.review build $PAGE --pdf $PDF --musicxml $BENCH/eyes/imslp317803-p0-perfect-eyes.musicxml
python3 -m tools.omr.hand_truth.review serve $PAGE                     # http://127.0.0.1:5051
python3 -m tools.omr.hand_truth.session advance $PAGE --to verified

# 5. Commit the page and your review marks (the session dir is regenerable and ignored).
git add $PAGE data/hand-truth/pages/imslp317803/0.review.json
```

If a save ever shows ERROR in the UI, the verdict is on disk but the page did not take
it: `python3 -m tools.omr.hand_truth.session resync $PAGE --bench $BENCH` folds every
saved cell back in.
