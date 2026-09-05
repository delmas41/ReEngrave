# Vendored from the labels workstream — data, not a second source

Both files are **byte-copies** of the labels workstream's committed output,
taken from `claude/staff-identity-labels-2026-09-05` @ `672607c9`:

```
git show 672607c9:benchmarks/omr-staff-identity-labels-2026-09/classified.json
git show 672607c9:benchmarks/omr-staff-identity-labels-2026-09/margin-ink.json
```

They are copied rather than recomputed, and that is sound **because the readers
and the lexicon have not moved**:

```
git diff 672607c9 HEAD -- tools/omr/instruments.py tools/omr/staff_labels.py \
    tools/omr/staff_labels_surya.py tools/omr/staff_labels_tesseract.py \
    tools/omr/staff_detector.py tools/omr/contextual.py \
    tools/omr/staff_labels_vision.py
# (empty)
```

* `classified.json` — 407 staves over the 20 scan-benchmark rows, each with the
  LADDER's answer (not the best rung) and its class.
* `margin-ink.json` — the 130 unresolved staves with the ink measured in the
  margin band beside each, bracket excluded. **Trusted only in the negative:**
  `a_NO_INK` (117) means 0 px over a band of 100k–260k; `INK_look` (13) means a
  human still has to look, and those are excluded from this probe's population.

Where these disagree with that workstream's `FINDINGS.md`, the data wins — the
FINDINGS table is an earlier vintage of the same classification (115/0/1/29/4
against this file's 117 `a_NO_INK`). See `../ROSTER_OPPORTUNITY.md` §"four ways".

The scripts that produced them are NOT copied; recover them with `git show` at
the same commit. The ladder-selection block in `../probe_roster_reach.py` is a
verbatim copy of that workstream's `probe_ladder.py`, cited in its docstring.
