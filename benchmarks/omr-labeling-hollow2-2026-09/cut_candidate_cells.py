"""Uniform cell selection over pages already VERIFIED to print hollow noteheads.

Same CLI as `tools.omr.annotate.select_cells_orchestral`.

WHY NOT THE SHORTFALL SELECTOR. `select_short_bar_cells` ranks bars by how far
their detected content falls short of their own meter, which is worth about
four times uniform sampling — on a page where the meter is READ. Measured
across this round's editions it mostly is not:

    Beethoven 5 / Litolff 1870      43-49 short bars per page   (2/4 read)
    Dvorak 9 / Simrock 1894          2-16                        (4/4, 3/2, 1/1 mixed)
    Scheherazade / Eulenburg         1-7                         (4/1, 1/4, 1/1 — garbage)
    Mahler 5 mvt I / Peters          1-3                         (cut common, never searched for)

With no meter there is no shortfall and nothing to rank, so the selector
returns a handful of cells and declines the rest. The Mahler case is
structural: `time_signature_locator` deliberately does not search for
`timeSigCutCommon`, so a cut-common movement can never be ranked this way.

The ranking earns its 4x by finding WHERE the half notes are on a page that
has them in a few places. On a page that prints them in most bars of most
staves — a Largo, an Adagietto, a finale with the brass holding whole notes —
the base rate is already high and uniform sampling loses little. So the filter
moves up a level: the PAGE is chosen by looking at it, and the cells are then
taken uniformly across the (staff x measure) grid.

WHAT THIS CHANGES vs select_cells_orchestral: nothing except the crop padding.
That selector monkey-patches `PAD_ABOVE/BELOW_STAFF_LINES` to 5.0; this leaves
the pipeline's own values alone, which is the argument `select_short_bar_cells`
makes in its docstring and which keeps this round's cells framed exactly like
the first round's — a cell a specialist is trained on should be what the
detector sees at inference, and padding changes the canonical scale.
"""
from __future__ import annotations

import random
import sys

from tools.omr.annotate import select_cells_orchestral as sel

# Leave measure_extractor's PAD_* constants at the pipeline's own values.
sel._patch_padding_globals = lambda: None


def _sample_random(items: list, n: int) -> list:
    """Replace `_sample_uniform`'s even spacing with a seeded random sample.

    `_sample_uniform` takes `items[int(i * len/n)]`, and the cell list arrives
    ordered by (system, staff, measure). When the stride lands near the number
    of measures per staff — which it does whenever `n` is about the number of
    staves — every pick is the same measure index. Measured on Scheherazade:
    **23 of 54 cells were measure 0**, i.e. the clef-and-key cell at the head
    of a system, which is the least useful crop on the page for labelling
    noteheads. The first round's shortfall ranking cannot alias this way and
    its histogram is flat.

    Seeded so a re-run reproduces the batch.
    """
    if n >= len(items):
        return list(items)
    if n <= 0:
        return []
    return random.Random(20260902).sample(list(items), n)


sel._sample_uniform = _sample_random

if __name__ == "__main__":
    print("[driver] random sampling (even spacing aliases onto measure 0); "
          "cell padding left at the PIPELINE's values", file=sys.stderr)
    sel.main()
