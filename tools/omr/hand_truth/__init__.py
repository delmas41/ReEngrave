"""Hand-labeled page truth (ROADMAP 1.7, plan `docs/plan-2026-10-08-hand-labeled-truth.md`).

One store per printed page, every box in PAGE pixels. Sean labels one cell at
a time; the cell is only a window onto the page, so a mark in the padded
overlap of two cells is ONE box (Sean 2026-10-08: "Boxes stored in page pixels
is very important").

    store         the page-truth schema, cell <-> page transforms, lifecycle
    completeness  which families are complete on a page (computed, never
                  asserted) and the ink-coverage control
    export_yolo   page boxes -> YOLO cell labels for training; held-out pages
                  refused by name
    inventory     the generated inventory of every hand label in the tree and
                  the weights lineage (`data/hand-truth/INVENTORY.json`)

Truth is what a HUMAN acted on. A model pre-fill lives in the page's `queue`
until Sean confirms or fixes it (CLAUDE.md §9: a pre-filled verdict is a
QUEUE, not a label), and Claude's double-check only ever FLAGS (rule 7).
"""
