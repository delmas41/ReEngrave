# Gather, then adjudicate

**The pipeline's ordering constraints are real for acquisition and imaginary for
use.** This document separates the two, names what each decision needs against
what it has when it runs, and says which gaps close by *deferring the decision*
rather than by moving the gathering.

Commissioned by Sean, 2026-09-07:

> *"The order is the key… We have the information but not in the right order so
> it kills or discards or miscalculates."*

> *"My assumption is that the best answers will come from all of these gathering
> information simultaneously and different orders being used for different
> elements… **The human brain does this naturally. It gathers all the info and
> uses what it needs to make a particular decision.** There may be a single
> order of gathering the info, but then I feel like all the info needs to flow
> in any direction once it is gathered."*

⚠️ **No pipeline code was changed to write this.** One read-only static probe:
[`benchmarks/omr-gather-adjudicate-2026-09/verify_order.py`](../benchmarks/omr-gather-adjudicate-2026-09/verify_order.py),
**9 checks, all passing** at `482c6104`. It runs no transcription, loads no
weights, opens no PDF.

---

## The finding, in one page

**The architecture Sean is describing is already built four times over. What is
missing is not gathering and not ordering — it is consumers.**

Four places in the tree already record *what a decision saw* alongside *what it
concluded*. That is the gather-then-adjudicate shape, implemented. Verified
consumer count:

| substrate | what it records | production consumer |
|---|---|---|
| `pitch_candidates` | every alternate pitch + weight, on 100% of noteheads | **none** — maintained by one pass, `pop()`ed by another, read only by an off-by-default bridge |
| `clef_evidence["contest"]` | clef candidates, winner, runner-up, margin, the clef in effect *before*, `overturns_inherited` | **none** `[C3]` |
| `contested_notehead_pairs` | every cross-staff ownership contest, both confidences, the deciding tier | **none** — written `transcribe.py:3242`, read by no module in `tools/` or `backend/` |
| key-signature vote evidence | per-staff tally, majority share, `key_signature_source` | ✅ **`key_signature_corroboration`**, default-ON since 2026-09-07 |

The fourth row is the one that matters: **the pattern has landed once already
and it works.** The other three are the same shape waiting for the same move.

**So the actionable claim is not "re-order the pipeline".** It is: *the
adjudication phase already exists — it is everything from
`transcribe.py:5312` onward — and three of the four evidence records that
should feed it reach nobody.*

**The one recommendation** (§7): give `clef_evidence["contest"]` its consumer in
`clef_correction`, converting a tier that reaches **0 staves** into one aimed at
the documented pipeline ceiling. **Its gate is reach, and reach is UNMEASURED**
— named precisely in §7.2, including the trap that the obvious field
(`disagrees`) is absent exactly where the answer lives.

**Sean's third stage** (§6): *evaluate* is **the tail of adjudication, not a
third stage** — nothing in the tree iterates `[C9]`, so consequences flow
downhill once and one pass suffices. But **one half of his question is real and
unowned**: keeping the *record* of what changed. The three `*_final` fields are
value-shaped, so each must be re-maintained by every later writer; two acquired
keepers after going stale and `time_signature_final` has **no keeper at all**
`[C8]`. The event-shaped records beside them (`rhythm_reconciliation`,
`key_signature_corroboration`) cannot go stale — the tree already contains the
right shape.

**And one thing to stop believing** (§2.3): the three per-staff carries
`active_clef_by_staff` / `active_key_sig_by_staff` / `active_time_sig_by_staff`
**can never hit**. Read at `4851`/`4873`/`4885`, written at `5232`–`5234`, same
loop nest, same key, one visit per key — mechanically proved `[C1]`. Every staff
of every system re-establishes clef, key and meter from a default. This is a
defect, not an architecture question, and it is *not* the recommendation; it is
in here because it is the purest instance of Sean's sentence — information
gathered and then discarded by order alone.

---

## Part 1 — What must be gathered before what

### 1.1 The hard graph

Physical or arithmetic. Re-derived against `482c6104`; this is **not** inherited
from `docs/architecture-decision-map.md` §3.1, whose line numbers have drifted
(it is stamped `e1107b5b`; every anchor below moved by ~130–660 lines).

```
render ──▶ staff detection ──▶ system grouping ──▶ barlines ──▶ measure cells
              │                                                      │
              │                                            canonical cell rescale
              ▼                                                      │
       staff.line_ys ────────────────────────────────────▶ YOLO detection
              │                                                      │
              ▼                                                      ▼
       header window ──▶ CLEF ──▶ key-signature slot table    notehead y
                           │                 │                       │
                           └────────┬────────┘                       │
                                    ▼                                │
                                  PITCH ◀────────────────────────────┘
                                    │
                    beams/flags/dots ──▶ DURATION ──▶ meter vote
                                    │                    │
                                    └────────┬───────────┘
                                             ▼
                              meter → rhythm reconciliation
```

Five edges are genuinely hard, each because it has bitten someone:

| edge | why it cannot be reordered |
|---|---|
| staff detection → everything | a cell is *defined* by `staff.line_ys`; nothing has coordinates before it |
| **clef → key signature** | the slot table is *chosen* by the clef. Fitting against a guessed clef read three flats as **two sharps** (`transcribe.py:4670-4679`, in the code's own comment) |
| **clef → pitch** | a clef transposes every note on its staff |
| duration → meter vote | the meter is voted out of resolved lengths |
| detections → direction text | it works by *subtracting* every detection from the page's ink |

### 1.2 Four claims of "late by history, not necessity", checked

`docs/architecture-decision-map.md` §3.2 asserts most late work is late by
accident. Four of its claims, verified:

| § | claim | verdict |
|---|---|---|
| (a) | *identity runs last and roughly half of it need not* | ✅ **and stronger than stated.** `contextual.py` contains **zero** reads of a resolved pitch `[C5]` — the entire pitch dependency of the identity stage lives in `clef_correction.py` (4 refs), which contextual imports at `:55`. The identity pass *itself* has no arithmetic reason to be at 5628 |
| (b) | *the header clef is read twice and the first read is discarded* | ✅ verbatim in the tree: `transcribe.py:4677` — *"it is not written to the output, and the measure pass below still reads the clef its own way."* Two independent readings of one fact exist at runtime and **are never compared** |
| (c) | *the four consistency checks could run anywhere* | ✅ `_flag_measure_count_inconsistency`, `_flag_key_signature_inconsistency`, `_flag_clef_register_inversion`, `_flag_time_signature_disagreement` are called at `5446`–`5449`, each taking only `sys_d` — pure functions over a finished system dict |
| (d) | *export is a separate entry point and therefore a separate era* | ✅ `export.py` runs from a stored JSON. Measured consequence: it reads **0** `pitch_candidates` and performs **0** executable reads of `confidence` `[C4]` — its single mention is prose in a docstring at `:1020` |

### 1.3 The distinction that matters

**Physical**: a cell has no coordinates until staff lines exist. **Conventional**:
identity runs at 5628 because that is where it was added. Only the first kind
constrains anything.

⚠️ And the conventional ordering is not free — it is what makes the difference
between *gathering* and *deciding* invisible. Three decisions below conclude
while still inside the gathering phase, with evidence that arrives later in the
same run.

---

## Part 2 — What each decision needs vs. what it has

### 2.1 The verified call order

Line numbers re-derived at `482c6104` by `[C7]`, not inherited.

| line | decision | scope |
|--:|---|---|
| 4604 | `detect_staves` | page |
| 4607 | `extract_measures` | page |
| 4631 | `remove_staff_lines` — **for the CV consumers only** | cell |
| 4677 | header clef, **discarded**; chooses the key slot table and nothing else | staff |
| 4699 | ⚠️ dead read of `active_clef_by_staff` `[C2]` | staff |
| 4851 | ⚠️ **CLEF seed** — dead read `[C1]` | staff |
| 4873 | ⚠️ **KEY seed** — dead read `[C1]` | staff |
| 4885 | ⚠️ **METER seed** — dead read `[C1]` | staff |
| 4981 | **NOTE** — `_detections_for_cell`: clef argmax, key fit, pitch | cell |
| 5232–5234 | the three carries written (too late to be read) | staff |
| 5312 | ownership: `_drop_unladdered_noteheads` | page |
| 5319 | ownership: `_dedupe_cross_staff_detections` | page |
| 5371 | `drop_uncorroborated_key_changes` ✅ *consumes evidence* | page |
| 5382 | `backfill_page_time_signatures` | page |
| 5410 | `_reconcile_page_to_meter` | page |
| 5446–5449 | the four consistency checks (inert) | system |
| 5597 | `read_directions` | page |
| **5628** | **INSTRUMENT** — `apply_contextual_analysis` | **document** |
| 5653 | `_apply_roster_range_veto` (`OMR_ROSTER_RANGE_VETO`, default `off`) | document |

**Sean's chain is *system → instrument → clef → key → time signature → note*.
The tree's is the reverse from `instrument` onward: the instrument arrives 647
lines after the note** `[C7]`.

### 2.2 needs · has · gap

Only decisions where the gap is non-empty.

| decision | needs | **has when it runs** | gap |
|---|---|---|---|
| **clef argmax** `4981` | the instrument; the header pre-pass's independent read; the staff's own reading on other systems | detection confidence within one cell, `clef_continuity` by role | the instrument (**+647 lines**); the second reading, **discarded 300 lines earlier at 4677**; the losing candidates *are recorded but reach nobody* |
| **key signature** `4981` | the clef; the work's key; the system's agreement | a slot table chosen by a clef read in the same call | the cross-staff vote runs *earlier* (header pass) but the **seed is dead** `[C1]`, so a continuation system re-fits from `fifths=0` |
| **glyph ownership** `5319` | which instrument each staff is (to apply a written-range veto) | the ledger ladder, then **distance** | identity (**+309 lines**). The range tier exists, defers to `5653`, and is **off by default**; on scans it is additionally vacuous — `_staff_written_ranges` returns `{}` with no dossier, and the scan gate runs dossier-free by protocol |
| **meter** `5382` | the work's meter; the system's agreement | durations already committed, plus the header reader's vote | **none of substance** — this one is correctly ordered, and `_READING_SOURCES` stops a derived meter voting for itself |
| **instrument** `5628` | margin labels; roster; bracket structure; score order | all of them, plus every resolved pitch it does not read | **none for acquisition.** Its problem is that it is a *terminus*: nothing downstream of it re-decides anything except the off-by-default veto |
| **export** (separate run) | detection confidence; pitch alternates | neither `[C4]` | the entire evidence layer. On a scan **29.7% of detections are under 0.40** (measured elsewhere — `omr-pipeline-audit-2026-09`; not re-run here) and the exporter treats each as certainly true |

### 2.3 ⚠️ The three carries are dead — mechanically proved

```
read   4851  active_clef      = active_clef_by_staff.get((p, sys_idx, staff_idx), …)
read   4873  active_key_sig   = active_key_sig_by_staff.get((p, sys_idx, staff_idx), …)
read   4885  active_time_sig  = active_time_sig_by_staff.get((p, sys_idx, staff_idx), …)
                    … cell loop at 4969 …
write  5232  active_clef_by_staff[(p, sys_idx, staff_idx)]     = active_clef
write  5233  active_key_sig_by_staff[(p, sys_idx, staff_idx)]  = active_key_sig
write  5234  active_time_sig_by_staff[(p, sys_idx, staff_idx)] = active_time_sig
```

`[C1]` establishes, by AST, that read and write sit under the **same** loop nest
`[4601 → 4821 → 4841]`, keyed on that nest's own loop variables, with exactly
**one** writer each and the read above the write. `sys_idx` iterates
`sorted(systems.keys())` and `staff_idx` iterates `sorted(systems[sys].keys())`
— dict keys, so each `(p, sys_idx, staff_idx)` is visited exactly once. **The
lookup cannot hit.** `[C2]` adds a fourth dead read at `4699`, in the header
pre-pass, dead for the same reason one loop earlier.

**What survives, and why it survives.** `clef_continuity` is keyed on the
staff's **role** — its vertical position within a system — not on
`(page, system, staff)`, so it inherits across systems and pages as intended. It
is the *only* reason a continuation system's clefs are not uniformly the
positional default. Key signature and meter have no such fallback: each
continuation system re-establishes them from `alterations_for_fifths(seeded_fifths or 0)`
and the header reader's vote respectively.

⚠️ **Why nothing caught it.** The defaults are good. A dead `.get()` with a
sound default degrades quietly to "the positional default was right about half
the time" — which `omr-additive-vs-gated-2026-09` §4.5 measured directly, at
`already_in_effect` 46.7%/53.4%. **A carry that never fires and a carry that
fires and agrees are indistinguishable from the output.**

⚠️ **Blast radius is UNMEASURED and is not assumed here.** This is exactly the
population Sean's input is made of — scanned orchestral scores whose
continuation systems reprint neither labels nor, often, clefs. Whether repairing
it helps or hurts is a separate measurement, and a repair is *not* what §7
recommends.

---

## Part 3 — Which gaps close by DEFERRING the decision

The move: **record the measurement now, conclude later.** A notehead's staff
position is a measurement; calling it a pitch requires a clef. A glyph's
overlap with two staves is a measurement; awarding it requires an instrument.

### 3.1 Already deferred, and reaching nobody

| substrate | written | the decision it could feed | reaches |
|---|---|---|---|
| `pitch_candidates` | `transcribe.py:2328`, 100% of noteheads, with weights | pitch, once the key and instrument are known | ⚠️ **nobody in production.** Maintained by `key_signature_corroboration:288` (re-spells them on a key change — a *maintainer*, not a consumer), destroyed by `clef_correction:368` (`pop`), read for a decision only by `tools/maestro_bridge/re-rank.ts`, off by default and absent from the container |
| `clef_evidence["contest"]` | `transcribe.py:1914`, per staff and per clef-reading cell | clef, once the instrument is known | ⚠️ **nobody** `[C3]` — 29 writer references in `transcribe.py`, 0 consumers anywhere else |
| `contested_notehead_pairs` | `transcribe.py:3242` | ownership, once the instrument is known | ⚠️ **nobody in production** — one benchmark probe reads it |

⚠️ **Correction to two standing documents.** `docs/architecture-decision-map.md`
§7.3 calls `pitch_candidates` *"the only key that is written and then explicitly
`pop`ped without ever being read"*, at `clef_correction.py:312`. Both halves need
amending: the line is **368** at `482c6104`, and it **is** now read — by
`key_signature_corroboration.py:288`, which landed default-ON the same day the
map was written. The accurate statement is narrower and more useful: *no
production consumer reads `pitch_candidates` to **decide** anything.*

### 3.2 Not yet deferred, and cheap to defer

| measurement | computed at | discarded at | what it would mean later |
|---|---|---|---|
| the notehead's **fractional** staff position | `pitch_resolver.py:180` — `pos_float = (y_center - top_y) / half_step` | `:181` — `pos = int(round(pos_float))` | a residual near 0.5 is *"this note sat exactly between two positions"*. On a warped scan that is the population `OMR_CELL_LINE_TRACE` exists for, and the adjudication phase knows the clef, key and instrument that the rounding did not |

### 3.3 What each decision would then have

| decision | with deferral, at adjudication time |
|---|---|
| clef | its own candidate list *with sources*, the discarded header read, the instrument, the same part's reading on other systems |
| ownership | both confidences, the deciding tier, the instrument's written range |
| pitch | alternates with weights, the settled key, the instrument's range, the fractional residual |

⚠️ **Deferral does not make weak evidence strong, and one arrow here is already
refuted.** See §4.3.

---

## Part 4 — What may not flow, and why

### 4.1 The rule, and why it is cheap

> **The safety constraint is PROVENANCE, not topology.** Two signals sharing an
> ancestor are ONE signal, not corroboration.

Sean: *"Circular is bad but should be easy enough to keep away from."* Correct —
**and cheap only because provenance is a tag on the fact rather than a
discipline in the reader's head.** The three refusals below were not reasoned
out in advance; each was measured after being bitten. A cycle is invisible in
the moment, because two signals sharing an ancestor look like two signals. What
makes the check local and free is that `clef_correction` can read one field and
refuse, with no global reasoning.

### 4.2 The three standing refusals — still in the tree

| where | line at `482c6104` | edge refused |
|---|--:|---|
| `clef_correction.py` | **566**, **646**, **652** (map said 396 — drifted) | deduced identity → clef: `if instrument_source_by_slot.get(slot) != "label"` |
| `dossier.py` | 434 | clef → part↔staff join |
| `score_layouts.py` | 682 | clef → layout pin |

All three stand. The asymmetry is deliberate and correct: **read** identity →
clef is permitted; **deduced** identity → clef is not.

### 4.3 A refuted edge — do not re-propose it

**Detection confidence as a tie-break in `_dedupe_cross_staff_detections`.**
Already measured over the 20-row scan gate, 4,521 contested pairs
(`benchmarks/omr-additive-vs-gated-2026-09/out/contests-analysis.txt`):

```
distance decided 4255 (94.1%)   ladder decided 266 (5.9%)
P(winner conf > loser conf):  ladder 0.617 [0.558, 0.674]   distance 0.545 [0.530, 0.560]
a |Δconf| > 0.00 tie-break would OVERTURN distance on 45.5% of pairs
```

0.545 against a 0.500 null. **Confidence carries almost no ownership
information, and acting on it would overturn nearly half of all contests.**
Ownership's missing evidence is identity, not confidence.

### 4.4 Provenance tags — the census

Verified by `[C6]`.

| fact | tag | carried? | gated on by | if untagged, would it BIND? |
|---|---|---|---|---|
| instrument | `instrument_source` | ✅ 1 writer, 4 readers | `clef_correction:566/652`, `absent_instrument:293`, `offroster_name:160`, `label_contradiction:128` | — already load-bearing |
| clef | `clef_source` | ✅ 2 writers, 4 readers | `contextual._read_clefs_by_slot`, `key_signature_corroboration:395` | — already load-bearing |
| meter | `time_signature["source"]` | ✅ 7 distinct values | **`rhythm._READING_SOURCES`** — *"anything else with a `source` is derived and must not vote for itself"* | — already load-bearing |
| **key signature** | `key_signature_source` | ⚠️ **partial** — written at **one** site, value `"header_vote"`; `dossier.py:165` supplies `"detector"` as a **default**, not a reading | `key_signature_corroboration:395` | **it would bind, weakly.** The tag is *inferred* for every non-vote reading, so a future consumer cannot distinguish detector-read from back-filled |
| **glyph ownership** | **none** | ❌ the survivor of a contest carries no tag `[C6]` | nothing | ⚠️ **moot today** — the fact has no cross-decision consumer at all. Tagging it is bookkeeping until §3.1's substrate gets one |
| pitch | none on the resolved pitch | ❌ | nothing | moot — `pitch_candidates` carry weights but no consumer |

**Answering the coordinator's three questions directly:**

1. **Carried:** `instrument_source`, `clef_source`, `time_signature["source"]`.
   **Not carried:** glyph ownership (nothing), resolved pitch (nothing).
   **Partial:** `key_signature_source` — one positive value, the rest defaulted.
   The guess that meter carries no tag was wrong: it carries the *best-enforced*
   one in the tree.
2. **Would the missing tags bind?** Key signature: yes, weakly. Ownership and
   pitch: **no — moot**, because those facts have no cross-decision consumer.
   ⚠️ Reach before accuracy: a tag on a fact nobody consumes is bookkeeping.
3. **Prerequisite for §7?** ⚠️ **No — independent.** The clef candidates already
   carry provenance: every entry appended at `transcribe.py:1829/1836` has
   `"source": "detector"` and `"read_source"`, and the sibling keys
   (`detector_header`, `cv_locator`, `specialist`, `dossier`) name their reader.
   `clef_correction` already gates on `instrument_source == "label"`. **§7 needs
   no new tag and no new field — only a consumer.** That is what keeps it cheap.

### 4.5 Would §7's edge close a loop?

No. The evidence it adds is **readers' clef opinions** (detector, header
detector, CV locator, specialist). The evidence it already uses is a **margin
label**. Different ancestors. And `clef_correction` writes no `clef_source`, so
its own output cannot re-enter the candidate list.

⚠️ One filter is required and is not optional: the candidate list must exclude
`clef_evidence["dossier"]` on any run where the dossier seeded the clef, or the
pass would read back its own seed as corroboration. Dossier-free scan runs are
unaffected.

---

## Part 5 — What can run in parallel

⚠️ **Nothing is parallelised today.** The pipeline is one serial loop.

| independent | why | ⚠️ |
|---|---|---|
| **pages** | every page is assembled independently until 5628 | the only document-scope consumers are `apply_contextual_analysis`, the run-level dossier check, and `_apply_roster_range_veto` |
| the four consistency checks | pure over a finished system dict `[c]` | inert today |
| key-signature vs. time-signature readers | different header sub-windows | |
| CV rungs vs. YOLO | they read **different images** | **do not unify** — erasing staff lines before YOLO measured −7 to −13 reading points and up to a third of the noteheads |

**Deliberately serial, do not parallelise:** the three margin-label readers.
`contextual._labels_for_page` is a cheapest-first cascade that only pays for the
next rung when the free one returns empty. Running them together spends money
the cascade exists to save.

⚠️ **Cost, stated correctly.** Direction text is **~19% of page wall clock at the
median** (min 11.2%, max 84.5%), measured on **single-page** runs. The **~75%**
figure quoted elsewhere describes a **whole-work** regime. **The two are not
comparable** and neither should be used to justify work on the other's
workload. Both figures are cited from the coordinator's brief and were **not
re-measured here — UNMEASURED by me.**

---

## Part 6 — Is there a third stage? *(gather → adjudicate → evaluate)*

> Sean: *"I wonder if there is a third stage — gather → adjudicate → evaluate —
> the eval stage being one where once decisions have been made about a
> particular decision, it then must be determined how or if that impacts other
> decisions. Or is that just a later part of the adjudication stage?"*

### 6.1 The answer

**Two things are bundled in that question, and they separate cleanly.**

**Evaluation-as-deciding — "what else must now change" — is the TAIL OF
ADJUDICATION, not a third stage.** It is not separable today and should not be
made so. The distinguishing test is whether it *iterates*: a stage that merely
propagates consequences once along the dependency edges is the last part of
deciding, whereas a stage that re-opens an earlier decision on the strength of a
later one is genuinely separate — and needs a fixpoint. **Nothing in the tree
iterates** `[C9]`: all three propagations are single-pass `for` loops over
pages/systems/staves, with no `while` and no repeat-until-stable.

**Evaluation-as-bookkeeping — maintaining the RECORD of what changed — IS a
separate concern, and it is the one with no owner.** That is what the `*_final`
fields are, and §6.4 shows they are the wrong shape for the job.

So: *one* of the two halves of Sean's third stage is real. It is the half nobody
would have guessed, and it is a records problem rather than a control-flow one.

### 6.2 The propagations that already exist

| propagation | bounded? | one-directional? | records what it did? | record consumed by? |
|---|---|---|---|---|
| **meter → rhythm** `_reconcile_measure_to_meter` (5410, after the meter settles at 5382) | ✅ **the tightest in the tree**: re-reads a beam level by **±1 only**, the bar must land **exactly** on the meter, the answer must be **unique**, single-voice measures only; never adds, deletes or re-pitches a note | ✅ durations vote the meter *before*; the meter never re-votes after | ✅ `rhythm_reconciliation` — `from_level`, `to_level`, `n_noteheads`, `expected_beats`, `beats_before`, `meter_source` (`transcribe.py:3719-3725`) | ⚠️ **the integer counter only** — `n_rhythm_reconciliations`, printed and put in the eval row. The record itself reaches nobody |
| **key guard → re-spell** `drop_uncorroborated_key_changes` (5371) | ✅ reverts only a mid-staff key change no other staff witnessed | ✅ re-spells the notes **and** their `pitch_candidates`, and **never re-derives the key from the new spelling** — the record's `to` is the restored key, re-read | ✅ `key_signature_corroboration` — `from`, `to`, `measures_reverted`, `witnesses`, `staves_in_system`, `contradicted_vote`, `vote_reason` | ⚠️ page counter |
| **clef → pitch restatement** `apply_proposal` (inside 5628) | ✅ by `propose_clef`'s six exits | ✅ clef → pitch only; **drops** `pitch_candidates` rather than shifting them, because they were ranked against the old clef | ✅ `clef_proposal` with `applied`; also maintains `clef_final` | ⚠️ **nobody** |

**All three are bounded, all three are one-directional, all three record what
they did — and no record is read.** That is this document's pattern for the
third time (§3.1, §4.4, here). The propagation *mechanism* is in good shape; the
evaluate stage's *output* is write-only.

### 6.3 ⚠️ Termination — which regime, and which one §7 implies

**Current regime: single-pass, downhill along the dependency DAG.** Consequences
flow only in the direction of §1.1's arrows. One pass suffices; no convergence
argument is required, and none exists.

**§7's recommendation stays in that regime, and this is a hard constraint on how
it is built.** It changes what `clef_correction` *reads* — evidence frozen at
gather time — not the direction in which it writes. The clef contest is a record
of what the readers saw *before* any pitch was restated.

⚠️ **The way to get this wrong is specific and worth naming:** if a future
version re-derived the clef contest *from restated pitches*, the edge becomes
uphill (clef → pitch → clef), and a fixpoint plus a convergence argument would be
required. **This project has twice declined to build one.** The contest must be
consumed as a frozen artifact of the gathering phase, never recomputed.

### 6.4 ⚠️ The `*_final` fields are the wrong shape — and the tree contains the right one

The pipeline records "this fact changed" in **two shapes**, and `[C8]` shows the
stale ones are all the same shape:

| shape | fields | why it behaves as it does |
|---|---|---|
| **VALUE** — *"the clef at the end of the staff"* | `clef_final`, `key_signature_final`, `time_signature_final` | a value must be **re-maintained by every later writer**. Miss one and it silently announces a change the file no longer contains |
| **EVENT** — *"at measure N, X became Y, on evidence E"* | `rhythm_reconciliation`, `key_signature_corroboration` | append-only. **Cannot go stale**, because it describes a moment rather than a current state |

The consequences are exactly as the shape predicts (figures from
`benchmarks/omr-pipeline-audit-2026-09/DECISION_TYPES.md` §3.3 and
`REVIEW-fix-keysig-corroboration.md`; **cited, not re-run**):

- `clef_final` — **9 of 20 occurrences stale**. It has since acquired a keeper
  (`clef_correction.py:606-608`), which is a *patch on the shape*, not a fix of
  it.
- `key_signature_final` — **19 of 26 stale**. Also since acquired a keeper
  (`key_signature_corroboration.py:415-416`).
- `time_signature_final` — **present on 32 scan staves where zero show a
  per-measure change**, and `[C8]` finds it has **no keeper at all**: one write
  site, zero references in any other module.

⚠️ **And every keeper is its own only reader.** `[C8]` finds no consumer of any
`*_final` field outside the module that maintains it. The audit put it exactly:
*"its only reader is its own keeper."*

**Salvageable? No — and they do not need to be.** The right record already
exists in the tree, twice, in the event shape, complete with the evidence that
triggered it. The value-shaped fields are a summary that a reader can derive
from the event log but that cannot derive itself from anything. **Two keepers
were added because two fields went stale; a third field has no keeper and is
stale now. That is a shape failing, not three separate oversights.**

⚠️ Nothing here is a recommendation to change them — that is a fourth
workstream and this document has one. It is recorded so the evaluate stage is
not built on a record that cannot stay true.

---

## Part 7 — The one recommendation

### 7.1 Give `clef_evidence["contest"]` its consumer

**Change:** `clef_correction`, which already runs at 5628 *with the instrument
in hand*, reads `staff["clef_evidence"]["contest"]` in addition to the clef
that won.

**Why this one:**

- **The substrate exists and is complete.** Candidates with confidences and
  sources, the winner, the runner-up, the margin, `clef_in_effect_before`,
  `clef_in_effect_after`, `overturns_inherited`. Written on every staff's first
  cell — `read_clef=(cell_idx == 0)` makes the record unconditional there.
- **The consumer exists and is already in the right place.** No reordering, no
  new pass, no new field, no new tag (§4.4 Q3), no new model or corpus.
- **It is aimed at the documented ceiling.** `clef_correction`'s FILL tier fires
  only where **no** clef was read — and measured, it produced 5 proposals on 193
  scan staves and **applied 0** (`omr-additive-vs-gated-2026-09` §4.5). The
  documented pipeline ceiling is clefs read **wrong**, a population the fill
  tier cannot see by construction. The contest record is the only place in the
  tree where that population is visible.
- **It is the pattern that already landed.** `key_signature_corroboration`
  consumed exactly this kind of record and went default-ON on 2026-09-07.

### 7.2 ⚠️ The gate — name it before building

**REACH, measured before any accuracy claim.** This dies exactly as the fill
tier died if the contested population is empty.

> Over the 20-row scan gate, how many staves carry a clef contest whose
> resolution could differ — i.e. `overturns_inherited == True`, or
> `clef_in_effect_before != clef_in_effect_after`, or `n_resolved ≥ 2` with
> `disagrees == True`?

**Pass:** a population large enough to price, on staves that also satisfy
`instrument_source == "label"` (the existing provenance gate — a contest on a
staff `clef_correction` may not act on is not reach). **Fail:** the fill tier's
outcome again — proposals in single figures, applied 0.

⚠️ **Two traps, named in advance:**

1. **Do not count `disagrees`.** `benchmarks/omr-pipeline-audit-2026-09/REVIEW-fix-record-refusals-clef.md`
   §BLOCKING-2 establishes that mid-staff clef flips carry `n_resolved == 1` and
   **no `disagrees` key at all** — the field is absent exactly where the answer
   lives. Count `overturns_inherited` and the before/after pair.
2. **`overturns_inherited` is PRE-REPAIR** (the code says so at
   `transcribe.py:1887-1897`): the dossier override runs ~200 lines later and can
   restore the inherited clef. On a seeded run it counts overturns the file never
   shows. Read it together with `clef_evidence["dossier"]`. The scan gate is
   dossier-free, so this bites the engraved arm, not the scan arm.

**Cost of the gate.** ⚠️ No stored artifact carries `clef_evidence` — a
repo-wide search finds it in `.md` and `.py` only, never in a result JSON. So the
reach probe requires a transcription pass over the 20-row scan gate. That is the
same shape and roughly the same cost as
`benchmarks/omr-additive-vs-gated-2026-09/probe/dump_contests.py`, which did
exactly this to produce `out/contests`; point it at `clef_evidence` instead of
`contested_notehead_pairs`. **This is a real cost and is why the reach
measurement, not the change, is the next step.**

### 7.3 What this recommendation is not

- Not a repair of the three dead carries (§2.3). That is a defect with an
  unmeasured blast radius and deserves its own decision.
- Not a confidence tie-break for ownership — **refuted**, §4.3.
- Not a reordering. Nothing moves.

---

## Verification

```bash
python3 benchmarks/omr-gather-adjudicate-2026-09/verify_order.py
```

9 checks, all passing at `482c6104`. Exit `1` on disagreement with the tree,
**exit `2` on an empty or missing input set** — demonstrated by running, not
asserted: `--root /tmp` (no `tools/omr`), a tree with an empty `tools/omr`, and a
tree holding only test files each exit 2, and the per-check guard fired live
during development when `[C6]` consumed 0 files.

| check | claim |
|---|---|
| `[C1]` | the three carries can never hit |
| `[C2]` | a fourth dead read at 4699 |
| `[C3]` | `clef_evidence` has 29 writers, 0 consumers |
| `[C4]` | `export.py`: 0 `pitch_candidates`, 0 executable `confidence` reads |
| `[C5]` | `contextual.py` reads 0 resolved pitches |
| `[C6]` | the provenance census of §4.4 |
| `[C7]` | the ordering anchors; instrument arrives 647 lines after the note |
| `[C8]` | the `*_final` fields have no reader but their own keeper; `time_signature_final` has neither |
| `[C9]` | all three propagations are single-pass — no `while`, no fixpoint |

### UNMEASURED here

- The **reach** of the clef contest — §7.2, the gate.
- The **blast radius** of the dead carries — §2.3.
- Every figure quoted from another benchmark (`4,521` contests, `0.545`, the
  fill-tier funnel, `29.7%` under 0.40, the direction-text wall-clock shares).
  Cited with source; **not re-run**.
- Whether `clef_correction` would get a contested staff *right*. §7 measures
  reach first, deliberately.
