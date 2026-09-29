# Rests adjudication queue

Built like `benchmarks/omr-queue-ties-2026-09` (`build_family_queue.py --family
ties`, ROUND6_SPECIALISTS_2026-09-04.md): 192 cells, 225 existing human rest
boxes pre-marked TP, 138 teacher candidates PENDING. Teacher = the PRODUCTION
scan weights (`hollow-graft-shift09-2026-09-04.pt`), not round 6's own teacher.
2 cells (`dvorak9-p8-sys1-s23-m0`, `dvorak9-p18-sys0-s15-m3`) were dropped —
they re-cut at a different canonical frame than the manifest, a pre-existing
corpus issue, not this queue's own bug.

Serve at :5050:

    export OMRNED_PYTHON=/Users/seanjohnson/Desktop/ReEngrave/.venv-omrned/bin/python
    python3 -m tools.omr.annotate.recut_cells --bench-dir benchmarks/omr-queue-rests-2026-09
    python3 -m tools.omr.annotate.server --bench-dir benchmarks/omr-queue-rests-2026-09 --port 5050

Hotkeys (single-symbol pass — palette is `restWhole/Half/Quarter/8th/16th/HBar`
only): `t` TP, `f` FP, `c` fix-class, `b` fix-bbox (redraw), `u` unsure, `n`/`p`
next/prev, `Tab`/`Shift-Tab` cycle detections, `1-9` jump to a class in the
picker. Draw mode is on for every cell, so a rest BOTH the human and the
teacher missed can still be boxed.

After triage: `verdicts_to_yolo_labels` on this batch alone → the complete
rest-family corpus with no merge step → retrain the rests specialist (~3 GPU
minutes) → export rows → `merge_class_head.py` grafts them into the
generalist checkpoint bit-exactly → the three-axis gate
(`benchmarks/omr-labeling-survey-2026-09/`) before it ships.
