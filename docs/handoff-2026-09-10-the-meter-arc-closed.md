# Handoff — the meter arc, closed: what shipped, what is refused, and what is next

⚠️ **READ THIS FIRST.** It replaces
[docs/handoff-2026-09-09-the-boundary-measured.md](handoff-2026-09-09-the-boundary-measured.md),
which is still correct about the boundary measurement and stale about
everything after it. Its predecessor chain
([bars-name-a-length](handoff-2026-09-09-bars-name-a-length.md) →
[meter-as-a-range-fact](handoff-2026-09-09-meter-as-a-range-fact.md)) still
governs the design, and **the metric is still not the goal — the staged
pipeline is.**

**Everything below was on `main` at `e6932034`, 2026-09-10, unless a line says
otherwise.** Nothing of this thread is unmerged.

⚠️ **THAT SHA IS A TIMESTAMP, NOT A CLAIM THAT MAIN IS STILL THERE** — and this
line said so badly enough that the same document needed correcting once for it
already (see §7, where a merge falsified a table three hours after it was
verified). **Re-check anything load-bearing against `origin/main` rather than
against this file.** The claims below that are most likely to rot first, with
how to test each in one command:

| claim | check |
|---|---|
| both meter flags still default `0` | `grep 'METER_CARRY_ENV, "0"' tools/omr/staged/adjudicators/rhythm.py` |
| the recorded `cautionary` is read by NOTHING (§6 rank 1) | `grep -rn 'cautionary' tools/omr --include='*.py' \| grep -v tests` — writer only |
| `score_margin` is read by nothing (§5) | `grep -rn score_margin tools/ \| grep -v tests` |
| the suite count | run it |

**Re-verified 2026-09-10 after the staged-pipeline branch landed: all four
still hold, and the suite is now 3531 passed / 11 skipped** (it read 3474 when
this file was written; that number moved because 57 tests arrived with that
branch, not because anything here changed).

---

## 1. THE STATE, IN ONE TABLE

| | |
|---|---|
| the meter arc | **closed** — the ranked task of two handoffs is measured, and its follow-ons are shipped or refused with a reason |
| `OMR_METER_CARRY` | still **`0`**. Objections (1) boundary and (2) second document are RETIRED. A NEW one took their place — see §4 |
| `OMR_METER_FROM_BARS` | still **`0`**, same reason |
| shipped default-ON, no flag | the letter meter (`C`/`¢`), the meter **in force**, the **cautionary** |
| suite | **3531 passed, 11 skipped** (2026-09-10, after the staged-pipeline landing) |
| benchmark | `benchmarks/omr-staged-meter-boundary-2026-09/` — FINDINGS.md is the full account; §4c and §4d are the parts that bound other work |

---

## 2. WHAT SHIPPED, AND WHAT EACH IS WORTH

**Three rules in `_meter_changes`, all default-on, none behind a flag**, because
each adds a reading where there was none or removes one that governed nothing:

1. **A letter meter is a complete meter.** A change engraved as a common-time
   `C` was detected on **23 staves of 23** and proposed nothing —
   `_meter_from_digits` needs two stacked digits and says so in its own
   comment. `_meter_from_letter` reads `C` → 4/4 and `¢` → 2/2.
   ⚠️ It produces **one false change on a Litolff scan page** from a single
   0.377-confidence glyph; reported, not gated, because the hazard is
   `METER_CHANGE_FLOOR` and the celebrated p.62 `3/4` rests on the same
   one-staff property.
2. **A change is against the meter IN FORCE, not the opening.** One system was
   emitting **five consecutive segments, all `4/4`**; and the same comparison
   **silently deleted every change BACK to the opening meter**, which
   Beethoven 9's finale makes seventeen times.
3. **A cautionary is not a change.** A courtesy signature after a line's final
   barline announces the NEXT system and governs no bar here. ⚠️ **The rule was
   checked against the corpus BEFORE it was written**: all four TRUE changes
   sit at a non-last cell, both cautionaries at a last cell. A last-cell
   candidate whose own bar FITS is still a change. The cautionary is
   **RECORDED** on the meter's value, not discarded.

**Measured together, over six fixtures:**

| | printed changes | found | FALSE |
|---|--:|--:|--:|
| engraved, before | 4 | 4 | 1 |
| **engraved, after** | 4 | **4** | **0** |
| scanned, before | 2 | 1 | 10 |
| **scanned, after** | 2 | **1** | **3** |

No true change lost anywhere.

---

## 3. THE BOUNDARY MEASUREMENT (the thing two handoffs asked for)

Rendered ENGRAVED so legibility is not the confound. Same page, asked twice,
differing only in which earlier page is in the window:

* true meter carried at **+8.0** (8 bars fit / 1 not)
* false meter refused at **−8.0** (0 / 9)

On the *Andante* both scored −1.0, which is why that page could never settle it.
In the file: whole rests written at 4.0 ql inside a 3.0 ql bar **196 → 38**, and
the CARRY and BARS exports **byte-identical**.

**Second document AND publisher, and the result SPLITS.** Brahms 1 mvt 1 prints
`6/8`, one bar of `9/8`, then `6/8` — and the Breitkopf scan of that music is
already in the scan gate with a **hand-verified window**, so the same 22 bars
run engraved and scanned differing only in the printing. Engraved finds the
change at the exact bar (support 60.0); the scan votes **`9/4`**, misses it,
and invents changes.

⚠️ **The +8.0 was +6.0 until a sibling's DURATION work landed.** Bar sums are
this mechanism's second witness, so better durations made the bars speak more
clearly. Re-measured, not assumed.

---

## 4. ⚠️⚠️ WHAT IS *NOT* ESTABLISHED — read before quoting §2 or §3

* **A NEW BLOCKING OBJECTION replaced the two that were retired.** On a
  Breitkopf scan the meter GLYPHS are misread badly enough that the weighing
  never gets a fair candidate. The flags are not blocked on their logic any
  more; they are blocked on the reading beneath them.
* ⚠️ **THE HAZARD THAT BOUNDS EVERY BAR-ARBITRATED RULE HERE: the case that
  most needs an arbiter is the case where the arbiter is silent.** A page whose
  meter the reader mangles is a page whose ink is degraded, and the same
  degradation stops its bars from summing — on the system that votes `9/4`,
  **not one of its seven bars clears the cross-staff quorum.** The bars are not
  an independent umpire over a bad reading; **they fail together with it.**
  ⚠️ Scope: this needs both readers on the SAME INK. A dossier fact or a
  `source_kind: "catalog"` roster does not fall silent because a raster is bad
  — which is why the `page` tier is refused where the `catalog` tier is
  admitted. **If you want a second witness that does not fall silent exactly
  when it is needed, it must not come off the same raster.**
* ⚠️ **Bar assessability falls with DENSITY, not with print quality** — 100% /
  100% / 78% / **33%** as events per bar go 1.0 / 1.5 / 3.1 / **4.5**. These
  mechanisms are strongest where the music is SPARSE.
* ⚠️ `METER_CARRY_MIN_BARS = 2` was seen refusing a CORRECT carry. First
  observation of that constant's cost.
* **n is still small**: two documents, two publishers, six fixtures.

---

## 5. THE `9/4`: THREE ROUTES MEASURED AND REFUSED — do not re-try these

Brahms 1 / Breitkopf p.1 prints `9/8` on every staff and the template reader
votes **`9/4`**. Diagnosed to the mechanism; **no fix shipped**, and each route
is refused by a measurement rather than a judgement:

1. **staff-line removal shreds the digits** — the crop really does look
   shredded (`9`→`U`, `8`→`A`) and the locator really does use
   `image_no_staff`. **Scoring BOTH variants still gives `9/4`**, lower.
2. **`score_margin` separates** — computed by the locator, written by GATHER,
   **read by nothing**, so it looks like a free discriminator. TRUE
   0.0681-0.3840 vs FALSE 0.0675: **a gap of 0.0006.**
3. **the CAUTIONARY plus the BARS arbitrate, with no threshold** — the design
   was sound and **its precondition was measured before anything was built**:
   not one of that system's seven bars clears the quorum.

⚠️ **What DOES separate is the absolute score** — TRUE 0.656-0.781, FALSE
0.514, **nothing between 0.531 and 0.656** against a `min_score` of **0.50**.
Not taken: that constant is `time_signature_locator`'s, shared with the legacy
`transcribe` path and set on an 11-source corpus. **7 correct / 1 wrong over 4
documents is not the evidence to move it**, and pricing it means re-running the
eleven-work engraved benchmark and the 20-row scan gate.

⚠️ **No structural signal catches it either — the wrong reading is UNANIMOUS**
across all 10 staves that spoke. Cross-staff agreement is not independent
evidence when every staff feeds the SAME reader the SAME typeface.

---

## 6. THE NEXT WORK, RANKED

### 1. The scan-side meter READING — the only thing between the flags and a default

Not the weighing, which is measured. `9/8` voted `9/4`; the real change missed
for want of a digit pair. ⚠️ **The document holds its own answer one system
earlier**: the cautionary reads `9/8` on **9 staves** from the DETECTOR's digit
pairs, and it is **on the record** (`value["cautionary"]`) with **nothing
reading it**. Consuming it is carry/borrow-shaped. ⚠️ It is EVIDENCE, not an
answer — the same scan records another cautionary at support **3.5 on ONE
staff**. The abstaining-system half needs no arbitration at all and is
un-built; **reach on this corpus is ZERO**, so it needs a corpus first.

### 2. A third document, and a scan whose bars can speak

Every open question now needs a page where the meter is misread AND the bars
are legible — this corpus has no such page, which is §4's hazard as a corpus
requirement rather than as a finding.

### 3. Unchanged from the predecessors

`A-DUR-6` items 6 and 7 — beat subdivision, and `A-DUR-5`'s **unclassified
ink**, Sean's standing request, still needing a RASTER pass in GATHER. Unify
the two chord groupings. Calibration from the score library, which bar sums
make possible with no truth files.

---

## 7. COORDINATION — what is on main and what is not

The staged-pipeline session (`claude/staged-pipeline-progress-bf3b29`) worked
in the same files all day. **Verified against `origin/main`, not from memory:**

| | on main? |
|---|---|
| export consumes `record.meter_at` (a meter change can reach a file) | ✅ yes |
| the carry takes the source's **END** meter, not its opening | ✅ yes |
| `METER_SOURCE_REASONS` replaces the `voted`-only source gate | ✅ yes |
| dynamics reaching the file, `status_census`, `decided_uncounted`, `ARC_KIND.md` | ✅ **yes — landed 2026-09-10, see below** |

⚠️⚠️ **THIS ROW READ "❌ their branch only" AND THE PARAGRAPH BELOW IT READ
"CURRENT, NOT STALE". BOTH WERE TRUE WHEN WRITTEN AND THE MERGE FALSIFIED
THEM** — corrected here by the staged-pipeline session as part of landing,
because a handoff that survives the event it predicts becomes a work order to
redo finished work. That is *fixed-then-kept-open-in-prose*, which this repo
has recorded three times.

The original text, kept because the correction is the point: *"THE `NOTES.md`
ENTRY ABOUT `decided_but_unwritten` IS CURRENT, NOT STALE. I called it stale in
conversation; checked against main, it is accurate — the branch order there
still lets `elif decided:` swallow every decided family, so the status is still
unreachable on main. Their fix is on their branch. **It becomes stale the
moment that branch lands**, and they are tracking its removal plus turning the
`ARC_KIND.md` citation in CLAUDE.md into a link, in the same PR. ⚠️ If you land
their branch, do both."*

**Both were done in that landing merge**: the `NOTES.md` entry is REMOVED
(`grep -c decided_but_unwritten NOTES.md` → 0) and the `ARC_KIND.md` citation
in CLAUDE.md is a link, with its own "deliberately un-linked, not on main yet"
clause removed so the sentence does not contradict itself. ⚠️ The prediction in
that paragraph was exactly right, which is why it was worth writing — the
failure mode is not predicting the staleness, it is leaving the prediction
sitting there after the event.

---

## 8. OPERATIONAL

* **Four symlinks** in a worktree: `library`,
  `tools/omr/training/data/weights`, `.venv-surya`, `.venv-omrned`.
  ⚠️ **`omr-weights/` does not exist in a worktree** — use the training path.
* ⚠️ **The staged CLI does no weight routing.** Engraved fixtures want
  `deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt`; scans want
  `deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt`.
* **Fixtures regenerate in ~15 s each** — `render_boundary.py`. The staged
  records are gitignored build products; `out/*.meter.json` and `REPORT.txt`
  are the committed reduction.
* ⚠️ **`run_arms.py` REFUSES to reuse an arm this tree did not build**, exiting
  non-zero. `--force` re-runs, `--reuse-stale` overrides loudly. A dirty tree
  can never be named, so it always refuses — expect that and pass `--force`.
* ⚠️ **A duration-level A/B across meter arms is INVALID** — a decided meter is
  consumed by `size_measure_rest` and `reconcile_duration` (159 of 314 verdicts
  move on one page). Control on `bar_lengths_seen` instead:
  `report_boundary.py --control bars`.
* ⚠️ Do not edit a source file while the suite runs (`inspect.getsource` reads
  through `linecache`). zsh does not word-split `env $VARS python3 …` or
  `for f in $FILES` — use `${=VAR}`.
* `OMR_SURYA_KEEP_ALIVE=0` for unattended runs; **never `pkill` the shared
  `llama-server`.**

---

## 9. ⚠️ THE CROSS-CUTTING LESSON, which is not about the meter

Two sessions produced **eight failed controls in a day**, every one giving a
clean number nobody would have queried. **The failure is never the wrong
answer, it is the RIGHT-LOOKING one.** Full account in CLAUDE.md beside *"a
check that cannot fail is worse than no check"*; the shape worth carrying:

* they split into **two families with different repairs** — *a control that
  computes the wrong thing* (make it able to fail) and *a control that was
  never testing what its name says* (state the contract, check it holds for
  THIS use);
* the same defect appeared at **three levels** — code, test, and test suite;
* **one red arm is not a battery**, and **a refusal battery needs an ACCEPT
  case** or it passes by refusing everything;
* **a fallback must never convert *"cannot tell"* into a definite answer** —
  not into "same", not into "clean";
* **`git blame` on a line is not evidence about who broke the paragraph** — it
  cannot attribute a SPLIT, which is what anchored markdown editing produces.
  `tools/omr/tests/test_docs_not_split_mid_sentence.py` now guards the standing
  docs.
