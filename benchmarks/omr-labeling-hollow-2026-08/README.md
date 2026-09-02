# Labeling batch: hollow noteheads on scans (2026-08-31)

## Why this batch exists

`benchmarks/omr-first-run-2026-08/DURATIONS.md` measured why duration recall on
a real scan is 0.381 against a step recall of 0.714, and it is **not** the
rhythm layer. Twenty of twenty-six duration errors are a half note read as
something shorter, and the half notes are not misclassified — they are **not
detected**. At 600 dpi bitonal on 19th-century print the half notehead's
counter closes to a thin diagonal sliver inside an otherwise solid head, and a
detector trained on clean engraving has no reason to call that hollow.
Beethoven 5 p.1 prints 68 half notes and the pipeline emits 8.

The control is what makes this a labelling problem rather than a code one: the
same music engraved by LilyPond gives 31 hollow detections against 30 real half
notes, and duration recall there equals pitch recall exactly (0.926 both). The
model can see hollow heads. It cannot see *these* hollow heads.

Four code fixes were tried first and all failed — reclassifying by ink fill,
finding the counters as enclosed white, Bravura template matching, and thinning
the ink before re-detecting. They are recorded in DURATIONS.md so nobody spends
the afternoon again.

⚠️ **Not ink-degradation augmentation.** It is the obvious idea and it is the
one already disproven on this exact kind of gap: a fair three-way fine-tune took
dense real-cell notehead recall from 0.652 to 0.122 with augmentation, *worse*
than the clean control. See the domain-augmentation entry in NOTES.md.

## How the cells were chosen

Not uniformly. A bar whose detected content does not fill its own meter is
missing something, and the meter is now read from the header, so the shortfall
is computable with no reference at all. Ranking by it is worth about four times
uniform sampling — measured on Beethoven 5 p.1, where the Gradus reference says
which bars actually hold half notes:

| | contains a half note |
|---|---|
| top 20 by deficit | **20 of 20 (100%)** |
| top 40 by deficit | 37 of 40 (92%) |
| random 20 | 5 of 20 (25%) |
| random 40 | 13 of 40 (32%) |

`SHORT_BAR_HINTS.txt` carries the per-cell figure: the meter, how many beats
resolved, and how many are missing. A bar missing about half its length is the
signature of an undetected half note. **It is a place to look, not a claim** —
label what the cell shows, and if the bar is short because a rest went undetected
then that is what to box.

## What is in it

48 cells, selected by shortfall from four scanned pages:

| source | cells |
|---|---|
| Beethoven 5 (IMSLP984073) p.2 | 14 |
| Beethoven 5 p.4 | 12 |
| Beethoven 5 p.6 | 12 |
| Ravel Boléro (IMSLP421137) p.2 | 10 |

262 pre-labels, a median of 5 per cell — black noteheads, beams, whole rests,
flags. **Zero hollow noteheads among them**, which is the whole point: the model
boxes everything it can see and the hollow heads are what it cannot.

Boléro p.4 contributed nothing: no bar there is short enough to qualify, which
is the selector declining to pad the batch rather than a failure. Mahler 5 and
La Mer were in the plan and dropped for time — their pages are large enough that
the selection pass alone runs for tens of minutes, and adding them is another
run of the same command.

## Labelling this batch

```bash
python3 -m tools.omr.annotate.server --bench-dir benchmarks/omr-labeling-hollow-2026-08
# → http://127.0.0.1:5050
```

The model's own detections are pre-loaded, so most black noteheads, rests and
accidentals are already boxed and only need confirming. **The hollow heads will
not be there** — that is the whole point of the batch, and they have to be drawn
with `a`.

The classes to draw are `noteheadHalfOnLine` / `noteheadHalfInSpace`, and
`noteheadWholeOnLine` / `noteheadWholeInSpace` where a whole note appears. On
line versus in space is the notehead's own position, not the stem's.

**Completeness matters more than usual here.** Anything left unboxed trains the
model that there is nothing there, so a cell where the hollow heads are drawn
and a black notehead is left out teaches one thing and unteaches another. Every
symbol in the cell gets a box or the cell gets skipped.

Hotkeys, and the full rules on what to box and what to leave alone, are in
CLAUDE.md under "Hand-label cells for OMR training". The short version: `t`/`f`
confirm or reject a pre-label, `a` draws a new box and stays in draw mode, `c`
fixes a class, `Tab` moves on and autosaves. Skip cells too bled to read — a
guess is worse than an absence.

## When the labelling is done

```bash
python3 -m tools.omr.training.verdicts_to_yolo_labels \
    --verdicts-dir benchmarks/omr-labeling-hollow-2026-08/verdicts \
    --manifest benchmarks/omr-labeling-hollow-2026-08/cells.json \
    --version-name v<n>-2026-08-hollow --out-root data/user-labeled \
    --labeler sean --description "hollow noteheads on scans with closed counters" \
    --dry-run
python3 -m tools.omr.training.build_catalog_yaml --root data/user-labeled
```

The catalog stays capped at `nc=208`; `noteheadHalf*` and `noteheadWhole*` are
already DSv2 classes, so this batch adds examples rather than classes and none
of the Phase 3.4 head-reinitialisation risk applies.

**Then commit the verdicts.** They are irreplaceable human work and the cell
PNGs are gitignored by design:

```bash
git add data/user-labeled/ benchmarks/omr-labeling-hollow-2026-08/cells.json \
    benchmarks/omr-labeling-hollow-2026-08/verdicts/ \
    benchmarks/omr-labeling-hollow-2026-08/detections/
```

## How to tell whether it worked

The measurement already exists and needs no new harness:

```bash
python3 -m tools.omr.transcribe "<the Beethoven 5 scan>" --pages 1 --out after.json
python3 benchmarks/omr-first-run-2026-08/eval_first_run.py --stem <after>
```

The number to watch is **duration recall, 0.381 today**, and the sanity check is
the notehead histogram: the page prints 68 half notes and currently emits 8. The
engraved control says the ceiling is duration recall equal to pitch recall.

⚠️ And watch the WTC verdict set for forgetting. Fine-tuning on low-density
orchestral cells narrowed the density prior once before and collapsed dense-page
noteheads 2506 → 114 (`[[project_clef_finetune_conclusion]]`); the audit tool
for it is `wtc_forgetting_eval.py`.
