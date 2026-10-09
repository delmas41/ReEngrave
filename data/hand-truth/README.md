# `data/hand-truth/` — hand-labeled page truth (ROADMAP 1.7)

Plan: [`docs/plan-2026-10-08-hand-labeled-truth.md`](../../docs/plan-2026-10-08-hand-labeled-truth.md). Code: `tools/omr/hand_truth/`.

| file | what | written by |
|---|---|---|
| `pages/<edition>/<pdf_page_index>.json` | one printed page: every box in PAGE pixels, the cells it was labeled through, pre-fills still in the queue, the staff-line checks, the page's state (`labeling` → `checked` → `verified`) | the labeling tool (`store.PageTruth.save`) — none yet |
| `INVENTORY.json` | every hand label in the tree, who judged it, how complete it is, and the weights lineage | GENERATED: `python3 -m tools.omr.hand_truth.inventory` (`--check` to verify) — never edit |
| `held-out.json` | pages that are test truth and never train weights tested on them | Sean's decision, 2026-10-08 |
| `weights-lineage.json` | which corpus trained which detector weights, with evidence | DECLARED; `inventory --verify-checkpoints omr-weights/` checks it against the `.pt` files |

Truth is what Sean acted on. A model pre-fill is a queue; Claude's double-check only flags.

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

## How to box (Sean's questions while labeling Brahms pdf 0, 2026-10-08)

- **One mark, one box, for the whole page.** A mark seen from two overlapping cells is
  the same box; box it where it is whole, skip the cut-off copy at a crop edge.
  Duplicates: keep the right proposal (`t`, or `c` to fix its class), `f` the other;
  never `f` a green confirmed box to clear a new proposal on it (that deletes it everywhere).
- **A note that belongs to another staff:** box it where you see it. Ownership is not
  asked now; only the notes the reader cannot settle come back as a short queue later.
- **Stems:** `stem`, head to tip; a chord shares one stem, one box. **Beams:** `beam`,
  one box per beam line (a 16th group has two, stacked; a stub gets its own).
  **Flags:** `flag8thUp/Down`, `flag16thUp/Down`, … — one box for the whole flag (a 16th
  is one box), Up/Down is the stem's direction, grace notes use the `…Small` flags.
- **Ledger lines:** `ledgerLine`, one box per stroke, including the one through a
  notehead (head and ledger boxes overlap), and every ledger between head and staff.
- **Staff lines:** never drawn. Confirm the five thin `L*` boxes on a staff's first
  cell; any other `staff` pre-fill is FP (the detector no longer queues them).
- **System bracket** (thick, hooked): `brace` with Notes `bracket`; a curly brace is
  plain `brace`; the thin line joining the staves at the left edge is `barlineSingle`.
- **Slurs and ties cut off by the crop:** look with **Page context** (tie = two heads on
  one line or space; slur = different pitches). Box the arc where it is whole (often the
  cell of the staff above, same bar). Where no cell shows it whole (it crosses a
  barline), box each piece with Notes `part`: touching `part` pieces of one family are
  one mark (`checks.marks`), and a lone `part` is flagged. Can't tell what a mark is:
  box your best guess with Notes `unsure` — it comes back to you as a flag.
- **Words** (`legato`, `Flauti`, tempo): `text`, one box per word or one-line phrase,
  the words typed in Notes; split only where notes or a barline break it. Dynamics
  (`p`, `f`, `sf`) keep their dynamic classes.
