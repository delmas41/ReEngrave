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
| **1** | **`OMR_CONDENSED_PARTS`** — oracle ceiling **−4,557 scan edits**, composes with the now-ON slot stitch, blocked because the COUNT is a property of the ENCODING (proved). ⚠️ But the page-truth redirect says condensed staves should STAY condensed, which makes it an anti-feature. **These two conclusions contradict and nobody has reconciled them.** | needs the reconciliation first, not a measurement |
| **2** | **Cause D** — Mahler p2's `staves` map. One hand-verified fact. | unblocks the 20th row |
| **3** | the meter guards (b) and (c) parked in `benchmarks/omr-rests-2026-09/FINDINGS.md` §14 — a corroboration guard and a vote-override, **different rules, different risks** | needs a multi-page corpus, which the gate is not |
| **4** | `<transpose>` — 92 in the engraved truth, ours 0, the fact is in the pipeline | `export_coverage`, already reports it |
| **5** | `<stem>` — 1,534 in truth, ours 0, musicdiff does not score it | the ledger, if a family were added |
| **6** | step 5, the six staged stubs — and ⚠️ **the staged pipeline still has no exporter**, a missing component rather than plumbing. **Do not start one as a side quest.** | nothing, until an exporter exists |

⚠️ **Item 1 is the interesting one for a big-picture session** and it is not a
coding task: two separately-measured conclusions in this repo disagree about
whether condensed staves should be split at all
(`benchmarks/omr-condensed-parts-2026-09/FINDINGS.md` says −4,557 edits;
`project_page_truth_benchmark` says the truth should stop expecting the split).
**One of them is measuring the wrong thing and the repo does not currently say
which.**

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
