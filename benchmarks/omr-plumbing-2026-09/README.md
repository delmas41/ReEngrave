# The plumbing test — is everything CONNECTED?

Sean, 2026-09-16: *"I am not yet worried about the quality of what goes through
the plumbing... I want to make sure everything is connected."*

So nothing here scores a reading. Every arm asks two questions only: did the
five stages complete, and which declared producer → consumer connections
actually **carried a value**.

```bash
bash benchmarks/omr-plumbing-2026-09/probe/run_matrix.sh      # the matrix
python3 benchmarks/omr-plumbing-2026-09/probe/edges.py out/matrix/*.record.json
python3 -m tools.omr.staged.reach --check                     # the static half
```

## Why a synthetic fixture and not a real score

A real page is the wrong instrument for this question: it prints what it
prints, so a connection goes untested for want of ink rather than for want of
a wire, and the report cannot tell those apart. These fixtures are engraved by
LilyPond specifically to print **one of everything** — slur, tie, hairpin,
dynamic, fermata, ornament, articulation, tuplet, grace note, chord, two
voices, whole rest, meter change, key change, tacet staff, bracket group — so
that `NOT_EXERCISED` shrinks and what is left is wiring.

⚠️ They are ENGRAVED, which is the easy domain, and `v6_scanlike` (the same
page rasterised, 0 vector drawings, 0 text characters) exists so the scan path
is exercised at all. **None of this says anything about reading quality on a
real scan, and no figure here should ever be quoted as if it did.**

## The arms

| # | arm | what it tests |
|---|---|---|
| 1 | base, 6 fixtures | the default path end to end |
| 2 | determinism | the same fixture twice |
| 3 | each default-OFF flag turned ON | the wire behind a dormant flag |
| 4 | each default-ON flag turned OFF | that the OFF branch still runs |
| 5 | the OCR rungs | margin labels + direction words |
| 6 | **no weights** | the negative control: the pipeline must still complete |

The flag list is DERIVED from the tree (`test_flag_default_direction.py`), so
a new flag joins the matrix with no edit here — as does a new INFER rule, a new
consequence or a new decision, which `edges.py` reads out of the registries.
