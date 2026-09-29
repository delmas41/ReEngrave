# Accidentals adjudication queue

Built like `benchmarks/omr-queue-ties-2026-09` (`build_family_queue.py --family
ties`, ROUND6_SPECIALISTS_2026-09-04.md): 155 cells, 211 existing human
accidental boxes pre-marked TP, 106 teacher candidates PENDING. Teacher = the
PRODUCTION scan weights (`hollow-graft-shift09-2026-09-04.pt`). 8 cells were
dropped — different canonical frame on re-cut, a pre-existing corpus issue.

Two exclusions run ahead of the queue so Sean never triages key-signature
junk: (1) `keyFlat/Natural/Sharp` are a SEPARATE detector class from
`accidentalFlat/Natural/Sharp` and were never candidates; (2) 40 candidates
inside an `m0` cell's own header window (leftmost 16 staff spaces —
`HeaderWindowConfig.max_width_spaces`, `tools/omr/staff_header.py`) were
dropped as likely a key-sig glyph the teacher misnamed. "Matching a decided
key-signature marker" (the third thing Sean asked about) is NOT implemented
here — this script runs the raw teacher over a specialist corpus with no
adjudicated record, same as the ties queue, so there is no decided marker to
match against. 214 further candidates were dropped as matching artefacts
(within IoU 0.20 of an existing human box, or its centre within half a staff
space of one).

Serve at :5050:

    export OMRNED_PYTHON=/Users/seanjohnson/Desktop/ReEngrave/.venv-omrned/bin/python
    python3 -m tools.omr.annotate.recut_cells --bench-dir benchmarks/omr-queue-accidentals-2026-09
    python3 -m tools.omr.annotate.server --bench-dir benchmarks/omr-queue-accidentals-2026-09 --port 5050

Hotkeys (palette is `accidentalFlat/Natural/Sharp` only): `t` TP, `f` FP, `c`
fix-class, `b` fix-bbox (redraw), `u` unsure, `n`/`p` next/prev, `Tab`/
`Shift-Tab` cycle detections, `1-9` jump to a class. Draw mode is on, so an
accidental both missed can still be boxed — including one inside an m0 cell's
header window, since the header guard only excludes TEACHER candidates, not
what a human can add.

After triage: `verdicts_to_yolo_labels` on this batch alone → the complete
accidental-family corpus with no merge step → retrain the accidentals
specialist (~3 GPU minutes) → export rows → `merge_class_head.py` grafts them
into the generalist checkpoint bit-exactly → the three-axis gate
(`benchmarks/omr-labeling-survey-2026-09/`) before it ships.
