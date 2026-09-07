# Two records that could not leave the process — serialised

Branch `claude/fix-serialise-evidence`, from `main` at `2d4bcc03`, 2026-09-07.

Two builds on 2026-09-06 recorded evidence that a decision had been made with,
and neither could cross the process boundary:

* **`types.Barline`** gained the vote count, the inter-system connectivity, the
  `_spans_system` score, which of five acceptance prongs fired, the open-score
  verdict and the cue-C override. **Barlines were serialised nowhere** —
  `grep '"barline' tools/omr/transcribe.py tools/omr/export.py` returned zero.
  Its own docstring named the limit: *"`transcribe` writes no barline record
  into the result JSON at all."*
* **`types.MeasureCell`** gained the pad it was actually cut with, per side,
  per cell. `transcribe`'s measure dict is built from an **explicit key list**
  with no generic copy, so a field added to the dataclass reaches disk only
  when someone names it there. Nobody had.

The reviewer's framing: *"a number you cannot read from disk still requires a
re-run to ask a question of, which is the exact cost recording was meant to
remove."* This change adds reach and nothing else.

## What was added

| key | where | shape |
|---|---|---|
| `barlines` | each **system** dict | list of 10-key rows, x-ordered |
| `pad_above_staff_lines`, `pad_below_staff_lines` | each **measure** dict | float or null |
| `barlines_with_no_system_in_output` | page dict, **only if non-empty** | orphan guard |

**Why the barline array hangs off the SYSTEM.** A barline is a property of a
system, not of a staff and not of a page: `detect_barlines` clusters candidate
columns across the staves of one system, votes them against one threshold, and
stamps one open-score verdict on the lot. Per staff would repeat one column
once per staff; per page would discard the grouping the vote is defined on.

Two redundancies are **deliberate** and are argued in `_barline_records`'
docstring rather than optimised away:

* `n_staves_in_system` stays on the row although the sibling system dict
  carries `n_staves` — **they are different numbers.** The vote counts staves
  with ≥5 `line_ys`; `sys_dict["n_staves"]` counts staves that produced cells,
  which under `OMR_ONE_LINE_STAVES` includes one-line percussion. Reading the
  denominator off the sibling is a silent off-by-N exactly where percussion is.
* `barlines_cross_gaps` stays on every row although it is a system-level
  verdict. The `Barline` docstring's central warning is that `connectivity` is
  **not comparable across pages and its sign inverts**; a consumer reading one
  row must not have to climb a level to learn the regime it was decided in.

## The payoff, measured from disk

`probe/probe_barline_prongs.py` answers, **with no pipeline run**, the question
an auditor measured on 2026-09-06 by instrumenting `detect_barlines` in
process. Reading the two stored result JSONs:

| page | regime | n | votes alone | vote+conn | connectivity | culled by `>=0.4` |
|---|---|--:|--:|--:|---|--:|
| Beethoven 5 / Litolff scan p1 | cross-gap | 17 | 0 | **17** | 0.818–1.000 | **0 of 17** |
| Brahms 1 / LilyPond engraved p0 | open-score | 8 | **8** | 0 | 1.0 ×1, **0.0 ×7** | **7 of 8** |

Identical to the in-process figures the `Barline` docstring records. All eight
Brahms barlines are real and carry a **unanimous 21 of 21** votes — also now
readable from disk. **A naive `connectivity >= 0.4` filter would cull seven of
eight real, unanimous barlines on the engraved page and none on the scan.**

The probe's second table cross-checks the pad against the distribution
`MeasureCell`'s docstring states from in-process measurement, and reproduces it
to the cell on both pages:

    beet5-984073-p1                (4,4)x48  (4,6)x32  (6,4)x32  (6,6)x80   n=192
    brahms-sym1-mvt1-engraved-p0   (4,4)x49  (4,6)x42  (6,4)x42  (6,6)x14   n=147

⚠️ **`span_ink` is `None` on all 34 rows of both pages** — both are ≥3-staff
systems, so the small-system rescue never ran. That coverage limit was already
recorded in the dataclass; it is now visible *from an artefact* instead of
requiring someone to re-run to state it.

## Byte-identity

`benchmarks/omr-pipeline-audit-2026-09/probe/compare_arms.py` (reused, not
rewritten), `--no-direction-text --no-contextual`, dpi 600, one scanned page and
one engraved fixture.

**Control first** — two `before` arms of the same tree:

    beet5-984073-p1                musicxml byte-identical: True (64,552 B)
    brahms-sym1-mvt1-engraved-p0   musicxml byte-identical: True (165,617 B)
    ... no pre-existing key changed value; new keys: 0
    RESULT: PASS

So the harness is deterministic on these pages and a difference would be
attributable. **`before` vs `after`:**

    beet5-984073-p1                musicxml byte-identical: True (64,552 B)
                                   12 staves, 192 measures unchanged
                                   new keys: 385 occurrences, 3 distinct
    brahms-sym1-mvt1-engraved-p0   musicxml byte-identical: True (165,617 B)
                                   21 staves, 147 measures unchanged
                                   new keys: 295 occurrences, 3 distinct
    RESULT: PASS

No pre-existing key changed value on either page. The only new keys are the
three named above.

## Size

Measured on the same two pages, under both writers that exist (`transcribe`'s
CLI writes `indent=2`; `backend/modules/local_omr.py` writes compact):

| page | writer | before | after | delta |
|---|---|--:|--:|--:|
| Beethoven 5 scan | `indent=2` | 749,291 | 775,023 | **+3.43%** |
| Beethoven 5 scan | compact | 215,920 | 230,515 | **+6.76%** |
| Brahms engraved | `indent=2` | 1,623,674 | 1,641,173 | +1.08% |
| Brahms engraved | compact | 439,989 | 449,969 | +2.27% |

Worst case **+6.76%**, on the production web-app writer, on the denser-per-byte
page. Under the ~10% tonight's clef record cost and which was accepted on the
argument that the growth IS the evidence. Split: the pad is ~82–84 B per
measure at `indent=1` and dominates (192 and 147 cells); a barline row is
~265–273 B and there are only 17 and 8 of them.

⚠️ **No projection was applied and no flag was added.** The standing rule is
that an instrument which is off is not a record (`OMR_CONTEST_DUMP`,
`locate_clef(trace=)`), and the sanctioned answer if size bit would be a
write-time projection — keeping the aggregates, dropping the per-item payload.
It did not bite. Were it to, the projection to take first is the **pad**, not
the barlines: it is 78% of the growth and its per-cell variation is only
interesting where the growth fires, whereas every barline row is already an
aggregate of a whole system's vote.

## Reach — stated honestly

**Nothing in the pipeline reads any of this back, and that is by design.**
`detect_barlines` decided with the evidence in process and the decision is
already made by the time serialisation runs. The consumer today is **a probe**.
What changed is that the question can be asked from an artefact.

Three inherited limits are NOT removed by writing the record, and are named in
`_barline_records`' docstring so a consumer does not discover them by building
on sand:

1. This is the **accepted** set only. A column that cleared no prong is counted
   in `deletion_counts` (`n_barline_clusters_rejected_no_prong`) and discarded,
   and `deletion_counts` is itself still not serialised — so this cannot answer
   *"what did the vote nearly accept"*.
2. `_drop_close_outliers` runs **before** the `Barline` objects exist, so it
   still cannot read any of this. The fix there is the `evidence` map inside
   `detect_barlines`, which is a signature change plus a measured decision.
3. `resegment_fused_measures` can add a **measure boundary** that no barline
   here accounts for, and appends nothing to `pws.barlines`. So a system's row
   count is **not** its measure count minus one, and a consumer assuming that
   will be wrong on exactly the fused pages.

## What a manifest change would additionally require — NOT DONE

The pad's obvious next home is the labeling manifest, and it was deliberately
left alone. `annotate/recut_cells.choose_mode_and_cut` currently **derives**
which padding mode cut a batch, by cutting the page under each candidate and
keeping the one that reproduces the manifest's recorded width, height and
canonical staff-line ys — and it **aborts on mismatch**, which is a safety
property over irreplaceable human verdicts. Putting the pad in the manifest
would need, at minimum:

* a **read** path tolerant of every legacy batch, since no manifest on disk
  carries the field and none ever will retroactively — so the derivation cannot
  be deleted, only shortcut, and a batch without the field must take exactly
  the path it takes today;
* a decision about the **undecidable cells**: a cell grown to the ceiling on
  both sides records `(6.0, 6.0)` under *either* padding mode (80 of 192 on
  Beethoven, 14 of 147 on Brahms), so the field alone cannot identify the
  cutter and a consumer treating it as authoritative would be guessing;
* **not weakening the abort.** A recorded pad agreeing with the frame is not
  evidence the frame is right; the frame comparison is the check, and a
  self-reported field must not be allowed to satisfy it;
* an e2e test in the shape of `test_recut_cells_e2e.py` — cut, delete images,
  re-cut **byte-identically** under both modes — extended to a manifest that
  carries the field and one that does not;
* and a separate review, because it changes the on-disk format of batches
  holding human work that cannot be regenerated.

## Tests

`tools/omr/tests/test_serialised_evidence.py`, 12 tests. Ten mutations, each
run and each **RED**:

| mutation | result |
|---|---|
| `connectivity` coerced `or 0.0` | RED (2 failed) |
| `span_ink` coerced `or 0.0` | RED (2) |
| drop `barlines_cross_gaps` from the row | RED (3) |
| drop `n_staves_in_system` from the row | RED (3) |
| one prong emitted for the whole system | RED (1) |
| system dict stops calling `_barline_records` | RED (3) |
| pad wired to `PAD_ABOVE_STAFF_LINES` | RED (1 + 4 errors) |
| `barlines` key present but always `[]` | RED (3) |
| pad's ABOVE value emitted on both sides | RED (2) |
| only barlines with connectivity serialised | RED (7) |

⚠️ **Anti-vacuity was the design constraint.** A test asserting a key *exists*
passes on `[]`; a test asserting a pad equals 4.0 passes against a field wired
to the module constant, which is the exact bug the field was added to prevent.
So the e2e tests assert on values that **differ between rows of one page**, and
`test_the_fixture_actually_produces_disagreeing_pads` fails first if the
fixture ever stops producing that variation — mutation 8 above (`[]` for every
system) is the specific vacuity that check was written against, and it is red.

The e2e fixture stubs the detector to return no detections. Legitimate here and
worth saying why: nothing under test is a recognition result — the pad comes
from the crop and the barline evidence from `detect_barlines`, both of which
run before any inference. It also means the file runs with no weights present,
in 2.2 s.

Also run green: `test_barline_evidence.py`, `test_measure_cell_pad.py`,
`test_left_edge_split_e2e.py` — 41 passed.

## Reproducing

    python3 benchmarks/omr-serialise-evidence-2026-09/probe/run_arm.py <dir>
    python3 benchmarks/omr-pipeline-audit-2026-09/probe/compare_arms.py <before> <after>
    python3 benchmarks/omr-serialise-evidence-2026-09/probe/probe_barline_prongs.py <after>

Both probes resolve inputs from `__file__` / `OMR_FIXTURE_ROOT`, never the CWD,
and **exit non-zero** on a missing or empty input set — verified: an empty
directory exits 3, and so does an arm of pre-fix JSON, which carries zero
barline rows.
