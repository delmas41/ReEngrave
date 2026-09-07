# Runbook — completion passes for an INPUT ceiling across publishers

**Scoped by Agent III, 2026-09-07. HUMAN WORK, not agent work — this is a
labeling plan, and no agent should attempt it.**

⚠️⚠️ **READ THIS SENTENCE BEFORE PLANNING ANY OF IT: the ask is not more
labeling, it is more PAIRED labeling.** A completion pass on a batch yields
human boxes. It does **not** yield a ceiling. A ceiling needs those boxes
measured *against what the encoding says is printed in those bars*, and that
needs a `reference.mxl`, a `prefill/` and a hand-confirmed window map. **Only
the Brahms batch has all three; nine of ten have none of them.** Step 1 below —
attaching a reference and a window map — is therefore the real cost, and it
needs judgement rather than clicks. A weekend spent completing the other nine
batches without it produces 5,000 human boxes and **zero** ceilings.

It exists because the audit's one empty ceiling kind (`input`) now has evidence
from exactly **one edition**, and one publisher is not a ceiling.

## Why this, and why it is not optional

Every scan detector figure in `metric-registry.json` — `scan:pitch` 83.4 %,
`scan:duration` 75.0 %, `scan:hairpin_detect` 1.01 % — is scored against an
**assumed** ceiling of 1.0: the claim that a perfect reader could recover every
symbol from a bitonal 600 dpi scan of 1870 type. Round 3 measured that claim on
one edition and it is *roughly* true for noteheads (≤ 0.971) and *badly wrong*
as an explanation for hairpins (a human found 17 where the detector found 0).

The question the board cannot answer is: **is `scan:hairpin_detect` at 1.01 %
this bad on Peters, Simrock, Durand and Novello too, or is Breitkopf's engraving
unusually kind?** Nothing in the corpus can say.

## The blocker is not labeling effort — it is that only one batch can be SCORED

(Restating the warning above, because this is the section someone will skim to.)

Ten batches were swept for one symbol at a time. A completion pass on any of them
yields human boxes. **It does not yield a ceiling**, because a ceiling needs the
comparison *human boxes vs what the encoding says is printed in those bars*, and
that needs three things the Brahms batch has and the others do not:

| batch | cells | verdicts | completion pass | `reference.mxl` | `prefill/` | cell PNGs |
|---|--:|--:|---|---|---|--:|
| `hollow2-…-breitkopf-brahms1` | 56 | 56 | **yes** | **yes** | **yes** | 0 |
| `hollow2-…-peters-mahler5` | 56 | 56 | — | no | no | 0 |
| `hollow2-…-litolff-hires` | 56 | 56 | — | no | no | 0 |
| `hollow2-…-eulenburg-scheherazade` | 56 | 56 | — | no | no | 0 |
| `hollow2-…-simrock-dvorak9` | 56 | 55 | — | no | no | 0 |
| `hollow3-…-durand-lamer` | 56 | 55 | — | no | no | 0 |
| `hollow3-…-jurgenson-tchaikovsky1` | 56 | 55 | — | no | no | 0 |
| `hollow3-…-novello-elgar1` | 56 | 55 | — | no | no | 0 |
| `hollow3-…-universal-mahler1` | 56 | 55 | — | no | no | 0 |
| `simrock-2026-09` | 110 | 110 | — | no | no | 0 |

⚠️ **Every batch shows 0 cell PNGs** — `benchmarks/*/cells/` is gitignored and
this worktree has none. That is expected and is a first step, not a fault.

## Per batch, in order

**0 · Re-cut the images.** `cells.json`, `detections/` and `verdicts/` are all
present; the PNGs are not.

```bash
python3 -m tools.omr.annotate.recut_cells --bench-dir benchmarks/<batch> --dry-run
python3 -m tools.omr.annotate.recut_cells --bench-dir benchmarks/<batch>
```

⚠️ **Do NOT re-run a cutter.** `select_cells_orchestral` and `rank_and_trim.py`
CHOOSE cells; pointing either at a labeled batch can renumber the set and orphan
every verdict. `recut_cells` never writes `cells.json` and never deletes.
It derives the padding mode from the manifest's own
`cell_canonical_w`/`staff_line_ys_canonical` and **aborts on a mismatch** — that
abort is the safety property, do not pass `--allow-partial` to get past it.

**1 · Attach a reference and a window map.** This is the step that turns a
labeling pass into a measurement, and it is the real cost.

- the work must be in `library/reference/` — check with
  `python3 -m tools.library.ingest catalog` and the batch's own PDF provenance;
- draft the per-page measure windows with
  `python3 -m tools.omr.training.draft_windows` from a hand-verified base row,
  then **confirm the first measure of each page against the print by eye** —
  every drafted row carries `"confidence": "draft"` and a `check` list;
- run `mxl_verdicts … --write-hints` to produce `prefill/`, which is what
  supplies `measure_number` and `parts` per cell.

⚠️ **`--work-id` is the score LIBRARY's id** (`brahms--symphony-1`), never the
dossier's. Beethoven 5 is held in two scans of the same plate offset by one page
and needs `--row-id` as well.

**2 · Run the completion pass BLIND.**

```bash
cp benchmarks/<batch>/batch_config.json benchmarks/<batch>/batch_config.<old>.bak
cp benchmarks/omr-labeling-hollow2-2026-09-breitkopf-brahms1/batch_config.completion.json \
   benchmarks/<batch>/batch_config.json
python3 -m tools.omr.annotate.server --bench-dir benchmarks/<batch> --blind
```

⚠️ **`--blind` is required if these labels will ever score the pre-fill**, and
harmless otherwise: the UI draws hints by default and every `Tab` is a page load,
so "just press `h`" is not a protocol.

⚠️ **Complete means complete.** The 14-slot completion config is still not the
class space: the Brahms cells also needed `keyFlat`, `clefG`, `timeSig8/9`,
`ornamentTrill`, `accidentalNaturalSmall` and two grace-sized heads through the
**full picker**. Only staff lines, stems, beams and free text are skipped — and
`beam` and `ledgerLine` being skipped is *not* free (they are pipeline-consumed;
see CLAUDE.md).

**3 · Stamp completeness.** Tabbing out of a cell writes
`inspected_passes: ["completion"]` even when nothing was drawn. **An
inspected-and-empty cell is the ceiling signal** — "looked and found none" —
and is distinct from a never-opened cell, which has no entry. This is what makes
coverage provable rather than eyeballed, and it is why the probe below can
restrict itself honestly.

**4 · Score it.**

```bash
python3 benchmarks/omr-pipeline-audit-2026-09/probe/probe_input_ceiling_from_labels.py
python3 benchmarks/omr-pipeline-audit-2026-09/probe/probe_hairpin_ceiling_value.py
```

Both currently hard-code the Brahms batch in a `BATCH` constant; widening them to
take `--batch` is ten minutes and should happen when the second batch exists, not
before.

## Which batch first, and why

**`hollow2-2026-09-peters-mahler5`.** Peters is the edition whose margin
labelling already behaves differently from Breitkopf's in three recorded places,
Mahler 5 is in the reference library, and it is the batch whose publisher most
differs in weight of engraving from Breitkopf — which is the axis a ceiling claim
is most exposed on. ⚠️ Known obstacle: the library holds Mahler 5 movements 1–3
and one existing batch is the Adagietto (mvt 4); confirm the movement before
committing to the window map.

Second: **`hollow3-2026-09-durand-lamer`** (a 20th-century French engraving,
furthest from the two German houses).

## What a result would license, and what it would not

- **Two editions agreeing** would let `ceiling:input:notehead:scan` move from
  `bounded_above` on one publisher to a bound with cross-publisher support, and
  would let the hairpin ceiling stop carrying a publisher name in every sentence.
- **Two editions disagreeing** is the more valuable outcome and the likelier one:
  it would mean the `input` ceiling is a property of the EDITION, and every scan
  detector percentage would need a per-edition ceiling rather than one number —
  which is the same lesson `OMR_WEIGHT_ROUTING` already learned about weights.
- ⚠️ **Neither licenses a general claim about scans.** Ten batches is ten
  editions, not a sample of the world's printed music.

## Cost

The Brahms completion pass was 55 cells and produced 554 human-affirmed boxes.
At the same density a batch is ~55 cells / ~550 boxes, plus step 1 (the
reference + window map), which is the part that needs judgement rather than
clicks and is the reason this is not a one-evening task.
