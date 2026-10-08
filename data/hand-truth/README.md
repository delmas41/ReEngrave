# `data/hand-truth/` — hand-labeled page truth (ROADMAP 1.7)

Plan: [`docs/plan-2026-10-08-hand-labeled-truth.md`](../../docs/plan-2026-10-08-hand-labeled-truth.md). Code: `tools/omr/hand_truth/`.

| file | what | written by |
|---|---|---|
| `pages/<edition>/<pdf_page_index>.json` | one printed page: every box in PAGE pixels, the cells it was labeled through, pre-fills still in the queue, the staff-line checks, the page's state (`labeling` → `checked` → `verified`) | the labeling tool (`store.PageTruth.save`) — none yet |
| `INVENTORY.json` | every hand label in the tree, who judged it, how complete it is, and the weights lineage | GENERATED: `python3 -m tools.omr.hand_truth.inventory` (`--check` to verify) — never edit |
| `held-out.json` | pages that are test truth and never train weights tested on them | Sean's decision, 2026-10-08 |
| `weights-lineage.json` | which corpus trained which detector weights, with evidence | DECLARED; `inventory --verify-checkpoints omr-weights/` checks it against the `.pt` files |

Truth is what Sean acted on. A model pre-fill is a queue; Claude's double-check only flags.
