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
| `barlines` | each **system** dict | list of 13-key rows, x-ordered |
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
* `page_index` / `system_index` stay on every row for the same reason
  (**added in review** — see below). Cost is bounded by the barline count, not
  the cell count: 25 rows across both pages.

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
| Beethoven 5 scan | `indent=2` | 749,291 | 776,110 | **+3.58%** |
| Beethoven 5 scan | compact | 215,920 | 231,058 | **+7.01%** |
| Brahms engraved | `indent=2` | 1,623,674 | 1,641,685 | +1.11% |
| Brahms engraved | compact | 439,989 | 450,225 | +2.33% |

Worst case **+7.01%**, on the production web-app writer, on the denser-per-byte
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


---

# Review round (2026-09-07)

Agent II approved with two minors. Both fixed; a third item — committing the
arm artefacts — was asked for and done.

## Minor 1 — the pad table had no anti-vacuity guard. FIXED

The barline half refused correctly on an empty input. The **pad** half did
not: a document with systems and **zero cells** yields `Counter()`, whose key
set is `set()` — which is not `{(None, None)}`, so it slipped past the
pre-fix-JSON check and printed a confident **`(n=0)` at exit 0**. That is
exactly the shape this file's own docstring warns about one table up, arriving
in the instrument itself.

⚠️ **Found by the reviewer, on a synthetic input, not by me.** My own refusal
test used an empty directory and an arm of pre-fix JSON, and *both of those
paths already worked* — so the test passed and the hole stayed open. The
missing case was a document that is well-formed and populated in one half and
empty in the other, which neither of my inputs was.

Proven with a control, on the reviewer's shape (systems + barlines, zero
cells):

    pre-fix probe   printed the table, exit 0     <- the bug
    post-fix probe  REFUSING ... exit 3

## Minor 2 — `system_index` promised and not emitted. EMITTED (not struck)

`_barline_records`' docstring listed `system_index` among the keys, *"so a row
is self-locating"*; the dict had eleven keys and that was not one of them.

**Emitted rather than struck**, and `page_index` with it. The phrase is what
invites lifting a row out of its parent, and that is precisely when the
redundancy stops being redundant — the same argument already made for
`barlines_cross_gaps`, applied to location instead of regime. Striking the
phrase would have removed the promise and left the hazard. Cost is bounded by
the **barline** count, not the cell count (25 rows across both pages, +0.25pt
of the total growth), which is why this is not the place to economise.

Four further mutations, each run and each RED: drop `system_index`, drop
`page_index`, emit either as a constant `0`. The constant-`0` pair is caught
by a new e2e test asserting the locator **agrees with the dicts it hangs in**
— a locator that disagrees with its parent is worse than none, because it
would be believed.

## Committed artefacts — `arm-after/`

A record-the-evidence branch whose own evidence needed a re-run to check was
the fair criticism. `arm-after/` now holds both pages:

| file | bytes |
|---|--:|
| `beet5-984073-p1.json.gz` | 37,282 |
| `brahms-sym1-mvt1-engraved-p0.json.gz` | 72,331 |
| `beet5-984073-p1.musicxml` | 64,552 |
| `brahms-sym1-mvt1-engraved-p0.musicxml` | 165,617 |

340 KB total. **Gzipped, and the decompressed bytes are the pipeline's own
output unmodified** — sha256 verified against the arm directory. A projection
or a trimmed copy would have been smaller and would have defeated the
demonstration: the probe has to read a real result JSON, or it is not showing
that the record reaches disk. `probe_barline_prongs.py` reads `.json.gz`
transparently and reproduces the table from the committed files.

⚠️ **The committed MusicXML is byte-identical to the BEFORE arm's**, verified
by `cmp`, so it doubles as the gate's own artefact: the headline claim is
checkable against these files without producing a before arm.

    35ea276d5fb3fd577ee7f6c0711beb7943863024860ce6694d76e3617ef54b0b  beet5-984073-p1.musicxml
    7fe2a2aca16c425dc513429744bc50fbcfa953733dca975ae0a1ec4c4f4240a0  brahms-sym1-mvt1-engraved-p0.musicxml

## `deletion_counts` — the coordinator's sharpening, recorded here

My reach limit 2 nominated `deletion_counts` as the next record. The review
sharpened the reason and, in doing so, **changed the scope**, which is worth
carrying:

*The accepted set is a convenience; the rejected set is the only route to the
information.* An accepted barline is partly recoverable from the output
already — it produced a measure boundary that is on disk — so recording it
removes a re-run. **A rejected column is recoverable from nothing.**

⚠️ **But serialising `deletion_counts` as it stands would not deliver it.**
Those 27 keys are *counters*. Writing them out buys *"eight columns were
rejected on this page"* — the same shape as `n_unladdered_noteheads_dropped`,
which reaches the JSON today as an integer consumed by nobody. **A tally is
not a record.** The thing worth serialising is the `evidence` map inside
`detect_barlines` — per-candidate x, votes, connectivity, span, failing prong
— which is what reach limit 2 already names. The cheap version ships a number
that looks like a record and answers nothing.

## Verification note worth keeping

The reviewer confirmed the probe reads the artefact rather than recomputing,
by a method that could have failed: extracting its import list (`argparse`,
`gzip`, `json`, `sys`, `Counter`, `Path` — no `tools.*`, `cv2`, `numpy`,
`fitz`, `PIL`, `transcribe` or `detect_barlines` outside a docstring and a
comment), then hand-writing synthetic result JSONs with no pipeline anywhere
and running the probe against them. **That is the check that matters for a
from-disk claim**, and it is cheaper than trusting the source.
