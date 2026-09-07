# Review — FIX AGENT G, `claude/fix-serialise-evidence`

**Reviewer: Agent II**, reviewed cold at `844117a7` (base `2d4bcc03`). Read-only:
nothing in the worktree was edited. Its test file was run (**12 passed**); the
suite was not, and no `scan_eval` was started.

## VERDICT: **APPROVE** — merge it. Two minors listed as follow-ups; neither blocks.

---

## Claim 1 — the from-disk probe. **VERIFIED, and by a method that could have failed**

This was the check that mattered, because a probe that quietly re-derived from
the raster would print the same table and prove nothing.

**It cannot re-derive.** Its entire import list is `argparse`, `json`, `sys`,
`collections.Counter`, `pathlib.Path`. The four hits for
`tools.|cv2|numpy|fitz|PIL|pdf|transcribe|detect_barlines` are at lines 5, 7, 18
(inside the docstring, which ends at line 32) and 43 (a comment on `CULL_AT`).
**No detector, no raster, no pipeline module is reachable from it.**

**And I exercised it rather than reading it.** I hand-wrote two synthetic result
JSONs — no pipeline anywhere — shaped like the claimed arms, and ran the probe on
them:

```
page              regime        n  votes  vote+conn  rescue     conn range  culled@0.4
synth-engraved    open-score    8      8          0       0    0.000-1.000       7/8
synth-scan        cross-gap    17      0         17       0    0.818-1.000       0/17
```

That is the claimed table, reproduced from disk alone: **8 admitted on votes
alone with 7 of 8 culled at 0.4, and 17 with 0 culled.** The reading path and the
arithmetic are both right, and the schema the probe reads matches the schema the
serialiser writes (checked by extracting the emitted key list from the AST).

⚠️ **What this does NOT establish, and the build should say so:** that the
*pipeline* produced those numbers on those pages. No arm artefact is committed —
`benchmarks/omr-serialise-evidence-2026-09/` holds `FINDINGS.md` and `probe/` and
nothing else — so the figures live in prose, exactly as the clef sweep's did.
**This build is in a better position than that one**, because `run_arm.py` is
committed and FINDINGS gives a one-command reproduction. Still worth committing
the two arm JSONs (or a trimmed extract): a record-the-evidence branch whose own
evidence needs a re-run is arguing against itself.

## Claim 2 — both redundancies are RIGHT, and (a) is a genuine near-miss

**(a) `n_staves_in_system` vs the sibling `n_staves` — confirmed, in the tree.**

- The vote's denominator is built at `measure_extractor.py:558-563` with
  `if len(s.line_ys) >= 5:` — and that filter is **unconditional**.
  `_admit_one_line_staves`' own docstring (`:1183-1197`) enumerates the four
  things the filter guards and says of the barline vote: *"STILL FILTERED,
  unconditionally"*, while item 4 — *"The CELL … This is the one the flag
  opens"* — is the only one relaxed.
- `sys_dict["n_staves"] = len(systems[sys_idx])` (`transcribe.py:4735`), where
  `systems` is keyed off **`MeasureCell`** objects (`:4556-4558`).

So under `OMR_ONE_LINE_STAVES` a one-line percussion staff **produces cells** and
therefore counts in `n_staves`, and is **excluded from the vote** and therefore
does not count in `n_staves_in_system`. **The two numbers diverge precisely where
percussion is**, which is exactly where anyone would be reading them. Refusing to
hoist is correct, and this is the class of near-miss the audit exists to catch.

**(b) `barlines_cross_gaps` on every row — confirmed, and my synthetic run is
the demonstration.** In the open-score arm the eight rows are unanimous and carry
connectivity 0.0, and a naive `>= 0.4` sweep culls **seven of eight**. A consumer
iterating rows without the regime on the row would do exactly that. One bool per
row against a load-bearing caveat that would otherwise be one level up and
skippable — the trade is obviously right.

## Claim 3 — both named vacuity shapes bite, and the strongest test is one they did not name

- **`"barlines": []` on every system.**
  `test_barlines_reach_disk_with_the_evidence_that_admitted_them` opens with
  `assert rows, "no barline reached the JSON on a page drawn with barlines"`
  **before** iterating, then asserts on values (`n_votes >= 1`,
  `n_votes <= n_staves_in_system`, `accept_prong` in the five-name set,
  `barlines_cross_gaps in (True, False)`, x-order). An existence check would pass
  the mutation; this cannot.
- **The pad wired to the module constant.** Verified the constants:
  `PAD_ABOVE = 4`, `PAD_BELOW = 4`, `PAD_MAX = 6`. The top staff must record
  `(6.0, 4.0)` — **different values on the two sides of one cell**, which no
  module constant can produce — and interior staves must record `(4.0, 4.0)`, so
  a blanket wiring to either constant fails on one side or the other.
- **The anti-vacuity gate itself is real.**
  `test_the_fixture_actually_produces_disagreeing_pads` asserts `len(above) > 1`
  **and** that the set is exactly `{4.0, 6.0}`, so if the fixture drifts it fails
  first with a message saying the file can no longer detect the mutation. That is
  the pattern five agents needed tonight and did not have.
- ⚠️ **The strongest test in the file is not on the list they gave you.**
  `test_the_serialised_barlines_are_the_ones_phase_one_accepted` **re-runs
  `detect_barlines` on the same page** and compares
  `(system_index, x, n_votes)` tuples against the JSON. That pins the record to
  the pipeline's own answer, so a serialiser that filtered or invented rows fails
  every self-consistency test above and this one too.

⚠️ **And a design point worth recording as good:** the *probe* deliberately
re-runs nothing (that is its entire purpose) while the *test* deliberately
re-runs `detect_barlines` (that is its entire purpose). Opposite choices, each
correct in its place, and both stated in their own docstrings.

## Claim 4 — size confirmed, keys unconditional

All four percentages recompute exactly from the stated byte counts:
230,515/215,920 = **+6.76%**; 775,023/749,291 = **+3.43%**;
1,641,173/1,623,674 = **+1.08%**; 449,969/439,989 = **+2.27%**.

**Both keys are unconditional** — `"barlines": _barline_records(...)` inside the
`sys_dict` literal at `:4742`, and `pad_above/below_staff_lines` inside the
measure dict literal at `:4971-4972`. No flag, no `if`. **The standing rule is
respected**, and it is the right call: a default-off evidence record reproduces
the defect it was written to fix (`OMR_CONTEST_DUMP` and `locate_clef(trace=)`
are both complete recorders that record nothing).

Declining a flag and a projection at +6.76% is consistent with what was accepted
at ~10% one branch over. Nothing to change.

## Claim 5 — byte-identity discipline correct

**Control first**: two `before` arms of the same tree, MusicXML byte-identical,
**0 new keys**, PASS — which is what makes a later difference attributable, and
is the same discipline the clef sweep used. Then `before` vs `after`: MusicXML
byte-identical on both pages, **no pre-existing key changed value**, exactly
**3 distinct new keys**. `compare_arms.py` reused rather than a third comparator
written.

---

## MINOR 1 — the docstring names a key that is not emitted

`_barline_records`' key inventory opens with:

> ``x`` / ``y_top`` / ``y_bottom`` / ``system_index`` — Where it is. … carried so
> a row is self-locating.

The emitted dict has **11 keys and `system_index` is not among them**
(`x`, `y_top`, `y_bottom`, `n_votes`, `n_staves_in_system`, `min_votes`,
`connectivity`, `span_ink`, `accept_prong`, `barlines_cross_gaps`,
`choir_cue_c_override`).

Harmless in place — the row hangs off a system dict that carries
`system_index`, and the probe reads it from there. But the docstring's own
justification is *self-locating*, and a consumer lifting rows out of their parent
(which is what "self-locating" invites) loses the locator. **Either emit it or
strike the phrase.** Documented-but-not-implemented is the family this audit
tracks, and it is cheaper to fix now than to find later.

## MINOR 2 — the probe's second table has no anti-vacuity guard

The barline half refuses correctly: no `*.json` under an arm dir → exit **3**;
every input carrying zero rows → exit **3**. Its docstring is explicit that *"a
probe that globs nothing prints a clean zero and exits 0, which is the failure
this guard exists to prevent."*

**The pad table has no equivalent.** `set(cells) == {(None, None)}` catches a
pre-fix JSON, but a document with systems and **no cells at all** yields an empty
`Counter`, whose key set is `set()` — so it falls through to the printing branch
and emits a blank row with `(n=0)` at exit 0. I hit this on my synthetic input:

```
PAD PER CELL, PER SIDE  (above, below) -> n cells
  synth-engraved                    (n=0)
  synth-scan                        (n=0)
```

Same shape as the failure the file's own docstring is proud of guarding against,
one table down. One `if not cells:` branch.

---

## Judgement — are near-misses the more valuable half? **YES, and for a sharper reason than "refusals matter"**

The build records the **accepted** set, and nominates
`n_barline_clusters_rejected_no_prong` — trapped in `deletion_counts`, **26
`_bump` call sites** (verified exactly), still unserialised (verified: the only
`deletion_counts` occurrence in `transcribe.py` is inside a docstring) — as the
next record in this family. It is right, on the distinction I drew in
`DECISION_TYPES.md` §5.3:

> **The accepted set is a CONVENIENCE; the rejected set is the only route to the
> information.**

An accepted barline is partly recoverable from the output already — it produced a
measure boundary, and the boundary is on disk. Recording it removes a re-run,
which is real and is what the probe just demonstrated. **A rejected column is
recoverable from nothing.** It is IRREVERSIBLE-BY-DELETION in the §5.3 sense, and
at equal reach a deletion site outranks a quantisation site precisely because the
input is gone.

⚠️ **But serialising `deletion_counts` as it stands would NOT deliver it, and the
nomination should say so.** Those 27 keys are *counters*. Writing them out buys
"eight columns were rejected on this page" — the same shape as
`n_unladdered_noteheads_dropped`, which reaches the JSON today as an integer,
consumed by nobody, and which I flagged in round 1 for exactly this reason: a
tally is not a record. The valuable version is **per-candidate evidence rows** —
x, votes, connectivity, span, and which prong it failed — which is the `evidence`
map inside `detect_barlines` that this build already names as reach limit 2.

**So: yes, near-misses are the more valuable half, and the cheap version of it is
not worth doing.** If this becomes the next commission, scope it as the evidence
map, not as serialising the counters — otherwise it ships a number that looks
like a record and answers nothing, which is the failure mode this whole audit is
about.

## What I want on the record as good

- Exercising the from-disk claim by **making the probe unable to cheat** rather
  than by asserting it — no pipeline import is a property a reviewer can check in
  one grep, and it is the right way to build a claim like this.
- **Refusing two optimisations and writing down why**, both correctly. The
  `n_staves` one is a real off-by-N waiting for a percussion page.
- Naming its own **three reach limits** unprompted, including that the row count
  is not the measure count minus one on fused pages — a consumer would have
  assumed that.
