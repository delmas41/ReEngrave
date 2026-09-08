# Handoff — 2026-09-08 close: where the project actually is, for a big-picture session

⚠️ **This is the file to read first.** It replaces
`docs/handoff-2026-09-08-late-step4-and-step3-done.md` as the entry point and
is written to hand the BIG PICTURE to a fresh session, not to continue the
numbered steps. Branch `claude/reengraved-step-4-step-3-105645`, **9 commits,
pushed, NOT merged.**

---

## 1. What closed today, in one table

| step | state |
|---|---|
| 1 — the tenth export gap | closed before today |
| 2 — test the staged pipeline | closed (shadow run, first catch adjudicated) |
| **4 — `entire staff`** | **SEPARATED into four causes; A, B, C all closed. Only D remains** |
| **3 — rests** | **mechanism found and fixed; residual opened and split three ways, cheapest shipped** |
| 5 — the six staged stubs | untouched, still deliberately last |

Rows of the 11 committed scan pairs with a resolved part join: **7 → 10.**
The one left is Mahler p2, which needs a `staves` map nothing on disk supplies.

## 2. ⚠️ THE THING A BIG-PICTURE SESSION SHOULD ACTUALLY TAKE FROM TODAY

**Four of the five real findings were "the value existed and nothing read it",
and two of them were inside the measuring instruments themselves.**

| | the value | who read it |
|---|---|---|
| the ledger's `coverage_check` | `balanced=False` on 9 of 20 rows | **nobody**, ever |
| `_is_propagatable_meter` | names `1/4` as garbage in its own docstring | only the VOTE, never the keeper |
| `page.n_staves` + `n_staves_note` | *"compare `detected` against 13/18/17"* | **nobody** — the gate compared the other number |
| detection confidence in `export.py` | every symbol's | **nobody** (pre-existing, still true) |

That is the same Class-C shape `docs/handoff-probability-gates-2026-09-05.md`
catalogued, and **it is now the highest-yield thing in the codebase**: today it
produced 1,771 recovered truth symbols, 7,007 unblocked symbol rows and a
1,251-error rest correction, at no detector cost whatsoever. **Before building
anything new, ask what is already computed and thrown away.**

## 3. ⚠️ AND THE MEASUREMENT LAYER IS NOW THE BINDING CONSTRAINT, NOT THE READER

Three independent demonstrations landed today, and together they are a
strategic fact rather than three bugs:

1. **OMR-NED is blind to the rest fix on BOTH families.** Engraved 0.12138 /
   2532 identical in all 23 categories; scan gate 34,963 edits identical on all
   11 rows — while the ledger records 1,251 corrected attribute errors and
   nothing else changed by a row. Positive control: six works' rest
   `<duration>` values demonstrably moved.
2. **The scan gate's one-page-per-row cut silently disables every PAGE-SPANNING
   mechanism.** The meter carry is one. Pooled, it read as a reading gap ("only
   86 of 159 parts carry a `<time>`"); per row, every movement-opening page
   reads 100% and every continuation page reads ~0%. **I published that
   conclusion and had to withdraw it an hour later.**
3. **The ledger's own arity gate was comparing printed staves to five-line
   staves** and calling the difference a guess, costing 4,815 symbol rows.

**So: a big-picture session should treat "can any instrument see this?" as the
first question about any proposed work, not the last.** The ledger is the
instrument that works; OMR-NED remains valid for DIRECTION only.

## 4. Defaults changed today

* **`OMR_SLOT_STITCH` → ON** (Sean's call). 10 of 11 exports byte-identical;
  the one that changes is Brahms p2's 27 fragments → 14 continuous parts, 0% →
  100% correspondence. Canary: `slot_stitch_canary.py`, 30 stitched parts with
  label evidence, **0 disagreements**, positive control printed.
  ⚠️ The flag site's docstring still carried the refuted *"it still costs more
  OMR-NED"* claim; corrected in place.
* **`rhythm._drop_implausible_meters`** — unconditional, no flag. 4 of 227
  staves / 45 of 2,538 measures across three publishers. ⚠️ Measured end to
  end it fixes **0 rests, 4 durations and 9 bar-sum warnings** — its payoff
  came through the meter→rhythm feedback loop, not the rest sizing that
  motivated it, and the 37 wrongly-sized rests on that page belong entirely to
  the two PARKED meter guards. See `benchmarks/omr-rests-2026-09/FINDINGS.md`
  §14.
* Everything else unchanged.

## 5. ⚠️ Two claims I made today and had to withdraw — the pattern matters

1. *"The residual is a meter-reading problem, and it is the next lever"* —
   a fixture artefact (§3 above).
2. *"`label_contradiction` is the free canary for `OMR_SLOT_STITCH`"* — it is
   computed in the CONTEXTUAL pass and the flag is read in `export.py`,
   strictly downstream, so the count is identical with the flag on and off **by
   construction**. I recommended it before checking.

Both were mechanism claims asserted from plausibility, which
`feedback_measure_the_mechanism` already names. **The cheap check in both cases
was one grep.** A big-picture session will be making exactly this kind of claim
constantly; budget a grep per claim.

## 6. What is genuinely open, ranked, with what could price each

| | what | instrument that can see it |
|---|---|---|
| **1** | **Build check 3 of the page-truth benchmark** — compare music STAFF-TO-STAFF instead of part-to-part. See below; this is the missing half of the structural programme. | itself: it is the instrument |
| **2** | **Cause D** — Mahler p2's `staves` map. One hand-verified fact. | unblocks the 20th row |
| **3** | the meter guards (b) and (c) parked in `benchmarks/omr-rests-2026-09/FINDINGS.md` §14 — a corroboration guard and a vote-override, **different rules, different risks** | needs a multi-page corpus, which the gate is not |
| **4** | `<transpose>` — 92 in the engraved truth, ours 0, the fact is in the pipeline | `export_coverage`, already reports it |
| **5** | `<stem>` — 1,534 in truth, ours 0, musicdiff does not score it | the ledger, if a family were added |
| **6** | step 5, the six staged stubs — and ⚠️ **the staged pipeline still has no exporter**, a missing component rather than plumbing. **Do not start one as a side quest.** | nothing, until an exporter exists |

### ⚠️ Item 1, and a correction to an earlier draft of this file

An earlier draft called the condensed-staff question *"a contradiction nobody
has reconciled"*. **That was wrong and it is worth saying why**, because the
next session would have spent time re-deciding a settled question.

It LOOKS like a contradiction: `benchmarks/omr-condensed-parts-2026-09/FINDINGS.md`
measures splitting a condensed staff at **−4,557 scan edits**, the largest
single lever on the corpus (87% of the `entire staff` bucket, with our
detection already correct); `project_page_truth_benchmark` calls the same flag
an **anti-feature**.

**It is settled, by Sean, 2026-09-05:** *"If the scan comes in with 2 parts on a
staff I want it to stay 2 parts on a staff — so this is a measurement issue
against the MXL."* The page prints one staff; the user wants one staff back.
The −4,557 is a **benchmark artefact, not user-visible quality**. A second and
independent reason it was never shippable: the COUNT is a property of the
ENCODING, not the engraving (proved — a label rule costs +2,181 on Dvořák).

**So the open item is the BENCHMARK, not the question.** Its consequence is the
uncomfortable part and belongs in every summary: ⚠️ **when the exporter stops
splitting condensed staves, OMR-NED gets WORSE on those rows while the output
gets BETTER.** Today's rest fix is the same shape — 1,251 corrected errors
scored at exactly zero.

The replacement, scoring structure against the PAGE rather than against
MusicXML, is three checks and is half-built:

| check | state |
|---|---|
| 1 — parts emitted == staves detected, systems preserved | **built and run**, 17/20, **needs no truth file at all** |
| 2 — detection vs the page | already exact 20/20; a regression guard |
| 3 — music compared **staff-to-staff** | **DESIGNED, NOT BUILT** — the piece that sidesteps condensation entirely |

**Check 3 is the missing half**, and until it exists the project measures
structure with an instrument that rewards the wrong answer.

## 7. Operational, for whoever picks this up

* Four symlinks in a worktree (`.venv-omrned`, `.venv-surya`,
  `tools/omr/training/data/weights`) plus `OMRNED_PYTHON`; three of the four
  failures are scan-side only.
* **`benchmarks/omr-hairpins-2026-09/score_export_arm.py`** is the right tool
  for any EXPORT A/B on the engraved benchmark — re-exports the 11 stored
  transcriptions, so the detector never re-runs. Minutes, not half an hour.
* `run_ledger.py --no-musicdiff` over
  `benchmarks/omr-part-join-2026-09/pairs-restamp-composed.json` is the fast
  scan-side instrument. **Its controls now include per-row symbol accounting
  and it REFUSES to quote a figure when that fails.**
* Full suite **3,079 passed, 4 skipped, 0 failed / 8m57s** on the final tree —
  after the `rhythm.py` change and the `OMR_SLOT_STITCH` flip (excluding
  `test_direction_text.py`, whose Surya-venv test is environment-dependent in a
  worktree). `export_coverage --all` exits 0.
* `timeout` does not exist on this macOS; `| tail` buffers a whole pytest run.
* ⚠️ `OMR_SURYA_KEEP_ALIVE=0` for unattended runs; **never `pkill` the shared
  Surya daemon.**
