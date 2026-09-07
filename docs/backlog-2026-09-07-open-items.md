# Open items after the 2026-09-06/07 identity session

**Written 2026-09-07 by the coordinating session.** One day produced fourteen new
benchmark directories and eleven merges; the follow-ups were being tracked in
conversation rather than anywhere durable, which is how they get lost. This is
that list. Every item names its evidence.

⚠️ **Read `docs/scope-identity-upstream-2026-09-06.md` alongside this** — several
items below are its phases, and its §9 records a recommendation of mine that was
MEASURED AND REFUTED the same day (`clef_register_warning`: reach 7/193, precision
0 of 11). Do not resurrect it.

---

## A00. ⚠️ STANDING RULE — a worse score does not condemn the mechanism

**Sean, 2026-09-07:** *"We should not assume a decision process is wrong because
it apparently makes things worse — there are too many variables of why something
may score worse. If we believe the information will be helpful in a good
environment, then when a bad result comes back our first response should be
'what else is wrong', not 'this isn't the best way forward'."*

**Order of enquiry before shelving a believed-good signal:**

1. **Is the COMPARISON valid?** Same code, same page-set regime, same inputs, not
   a cached arm. ⚠️ Today's scare — "more evidence made identity worse", 50 of
   807 records — was a transcription compared against a *replay*, and a replay
   hands `fit_layouts` no clefs. Labels moved **0** records; clefs moved **51**.
2. **Is the METRIC charging for something other than correctness?** Structural
   charge for a printing convention (28-40% of the scan figure), the symmetric
   reward for under-prediction, unpaired truth parts.
3. **Can a DOWNSTREAM consumer use it at all?** The lineup-swap boundary detector
   was excellent (support 8 vs max 1) and scored worse because the document
   reference cannot express a union of lineups — the placement IS the identity,
   so the score was capped whatever the boundary said.
4. **Only then: is the mechanism wrong?**

Two dormant flags are live candidates for re-examination under this rule:
`OMR_SLOT_STITCH` (charged for unpaired truth parts — never re-priced against a
page-normalised truth) and `OMR_CONDENSED_PARTS` (improves the metric by making
the OUTPUT less faithful to the page — fix the truth, not the reading).

⚠️ This does **not** license shipping what measures worse. It licenses
investigating before concluding. The shipping bar is unchanged: measured, both
families, controls that can fail.

## A0. Sequencing decision — Sean, 2026-09-07, after the machine crash

**Resume the three crash-interrupted agents ONE AT A TIME, `page_normalise` first,
then the other two once it lands.** Recorded here because the machine crashed
once already today and a sequencing instruction held only in conversation is the
first thing lost.

| agent | branch | rescued as | state |
|---|---|---|---|
| `page_normalise` fixes | `claude/page-normalise-fixes-2026-09-06` | `492f1e07` | **RESUMED, running alone** |
| one-line staves | `worktree-agent-a64f7fb5bce33d36a` | `92b12cf4` | waiting |
| score language | `claude/score-language-2026-09-06` | `fc908c72` | waiting |

⚠️ **All three rescues are UNVERIFIED** — no suite, no controls, no A/B completed
before the crash. Each was committed from NAMED paths only (a build tree was
deliberately excluded). ⚠️ The one-line-staves branch touches **three** pipeline
files and is the one to be most careful with.

**Why one at a time:** seven concurrent agents drove load average to 51-61
earlier today, the test suite timed out at 10 minutes, and the lineup-swap agent
**abandoned its control runs at 13 of 166 pages** rather than compete for cores.
Serial is slower per task and faster to a trustworthy answer.

## A0b. QUEUED — re-price `OMR_SLOT_STITCH` against the page-normalised truth

**Sean, 2026-09-07: commissioned, to fire once coverage lands.** Not dispatched
yet, deliberately — it needs 19/20 map coverage to be answerable, and running it
now would both measure the wrong thing and compete with `page_normalise` for
cores.

**The hypothesis, which is Sean's** (*"I am not fully convinced about the slot
stitch — something feels off, like maybe it needs something else solved first"*):
`_stitch_slots` does the structurally RIGHT thing — Brahms p2 recovers 14
continuous parts from 27 fragments and correctly leaves the suppressed trumpet
slot short — and is dormant only because it scores worse. But the recorded reason
is that **musicdiff charges an unpaired truth PART more than that part's unpaired
MEASURES**, so `entire staff` doubles (715 → 1,632). **Unpaired truth parts are
the condensation artefact**, not the stitcher's fault: the truth has 18 parts
where the page prints 12 staves, so any structurally correct output leaves parts
unpaired and is billed for them. Normalise the truth to the page and they should
pair.

This is §A00's standing rule applied to its clearest candidate: the metric was
charging for something other than correctness.

**Firing order:** `page_normalise` fixes → Mahler rows merge (15/20 → 19/20) →
this. Queue behind the two crash-interrupted agents (§A0).

**What the arm must do:** re-price slot stitch OFF vs ON against BOTH truths —
raw and page-normalised — same predictions, one shared read pass, `--tag=` per
arm. ⚠️ Report the normalised delta as a SEPARATE BENCHMARK ERA that may not be
differenced against the raw figure or any historical one. ⚠️ The prior figure was
priced on **n=1 page**, so a null is a real possibility and would itself settle
the question. ⚠️ `OMR_CONDENSED_PARTS` composes with it (oracle ceiling −4,557
together) but is separately argued to be an anti-feature — measure stitch alone
first.

## A. BLOCKING — someone's finished work cannot land until these are fixed

| # | item | evidence |
|---|---|---|
| A1 | **Two faults in `page_normalise.py` block merging the Mahler maps.** `_tokens` sorts `str` against `tuple`; `_voice_merge` inserts a deepcopy still pointing at its old site. Both reproduced with the exact bar. `merge_additions.py` refuses p3 and p4 until fixed. Two more (Unpitched) are latent for any edition condensing percussion. | `benchmarks/omr-staves-map-completion-2026-09/FINDINGS.md` §"latent faults" |
| A2 | **A 57-slot confirmation pass is waiting for Sean** at `http://127.0.0.1:5076` (89 slots offered; only 57 carry value — p2 is already verbatim in `works.json`, Bach is worth exactly zero). Do A1 first so the work can actually merge. | same FINDINGS |

## B. Flags that landed OFF and need a second work before defaulting

⚠️ **Every one of these is n=1.** The project shipped `OMR_MOVEMENT_REFERENCE`
default-ON on one work and a second work then measured it making things four
times worse. That is the precedent these items exist to respect.

| # | flag | state | what would settle it |
|---|---|---|---|
| B1 | `OMR_ROSTER_SCORE_ORDER_VETO` | off. Removes all 17 Brahms `Trombone → Tuba`; wrong 23 → 6, correct unchanged at 741, zero correct names lost. Blast radius provably the exported `<part-name>` only. | a second work with a plain `score_order` slot. Beethoven 5 has none, so it must be a third document. Exposure over 213 rosters: 42 works have the shape. |
| B2 | `OMR_ROSTER_LABELS` | off. 20 of 1422 real labels change (1.4%), all 28 firings hand-adjudicated correct. | ⚠️ **production reach is currently NIL**: it needs `OMR_WORK_ID` and *nothing sets it*. Wiring that is the prerequisite, not more measurement. |
| B3 | `OMR_SLOT_STITCH`, `OMR_CONDENSED_PARTS` | off, pre-existing. Oracle ceiling −4,557 scan edits, and they compose. | the condensed COUNT cannot come from the page (proved). ⚠️ And the headline-validity work argues `OMR_CONDENSED_PARTS` is an **anti-feature**: it makes the OUTPUT less faithful to the page to please the metric. Fix the truth, not the reading. |

## C. Known faults with a named location, unfixed

| # | fault | where |
|---|---|---|
| C1 | **`Tb.` → Tuba at HIGH confidence.** Litolff abbreviates *Tromboni* `Tb.`; largest single residual on Beethoven 6 (2 wrong + 34 of 38 impossible). Same family as the `Tr.` = Trombe/Tromboni fix. ⚠️ `Tb.` really IS Tuba elsewhere — needs the 1422-label harness, not a one-liner. | `instruments.py`; harness in `benchmarks/omr-lexicon-2026-09/` |
| C2 | **A lineup SWAP at constant size defeats the span logic.** Brahms 4 movements III and IV both print 16 staves with different lineups; `lineup_spans` keys on staff COUNT, so ~150 names slide one slot. Outside the axiom "a bigger system proves the lineup GREW". | `benchmarks/omr-span-reach-2026-09/FINDINGS.md` §4. The signal a fix needs: **the margin labels on p41 and p67 disagree** |
| C3 | **One-line percussion staves are detected and then dropped** by `if len(s.line_ys) >= 5`. All 11 present, at exactly the gaps in the run's own numbering. A pipeline ceiling with a location. | `tools/omr/measure_extractor.py:464` (and 1148, 1471) |
| C4 | **Bach's reference condenses where the print does not** — its Cembalo is one single-staff part, the page prints two and we read two. The map idiom only merges, so it cannot express this. Not a labelling gap. | `benchmarks/omr-staves-map-completion-2026-09/FINDINGS.md` |
| C5 | **`Timpani → Trombone` ×1 on Beethoven p31 sys1 survives every arm** — the seventh record of the recorded seven is not the group-map fault. Found because a self-test assertion FAILED rather than being laundered. | `benchmarks/omr-identity-harness-2026-09/` |

## D. ⚠️ Measurement hazards discovered today — carry these into any identity work

| # | hazard |
|---|---|
| D0 | ✅ **SETTLED 2026-09-07 — the experiment ran and the answer is NO** (`benchmarks/omr-readpass-monotonicity-2026-09/FINDINGS.md`). At one commit off one cached read pass (staves identical 1616/1616), withholding the 11 extra labels moves **0 of 807** records: 0.9368 with 973 labels and with 962, 1.0000 with either once CLEFS are supplied. **Neither the evidence nor the code did it — the two passes were a TRANSCRIPTION and a clef-blind REPLAY.** An identity-only replay passes empty page dicts, `_read_clefs_by_slot` returns `{}`, and `fit_layouts` decides the ambiguous `Tp.` (Timpani-or-Trumpet) at slot 8 blind: it answers Trumpet, which is a candidate, so the label is overturned document-wide; with the real bass clef it answers Trombone, which is not, so the label stands. The decisive control was already on disk — the same session's own `whole-identity.json`, same commit, byte-identical 962-row label evidence, scores 750/807 = 0.9294 against its transcription's 0.9913. The clefs are worth **51 records**; the labels are worth **0**. ⚠️ Sean was right to refuse the claim. Original text follows. — ⚠️ **D1 and D2 below were RELAYED BY ME AS FINDINGS AND THEY ARE NOT.** The harness's own FINDINGS says in bold: *"Not attributed, deliberately. The two passes also differ in CODE (pass A predates the group-map and span-composition fixes), and committed artefacts cannot separate 'the extra evidence did it' from 'the code drift did it'."* What IS established is the floor (two passes of one PDF differ by 50 records) and the mechanism (**ONE slot decision, inherited by 50 staves** — pass A names slot 8 `Timpani` from a label, pass B names it `Trumpet` from `score_order_ambiguity`). What is NOT established is the cause. Sean refused the claim on exactly this ground before the confound was surfaced to him. **The settling experiment is defined and cheap** — one ~26-min whole-work read pass at ONE commit, serving both label sets off one cache through the `_labels_for_page` patch `compose.py` already implements. Until it runs, D2 is a hypothesis. |
| D1 | ⚠️ **CORRECTED by D0's settling experiment: it is not a READ-PASS floor, it is a HARNESS floor.** The 50 records are the difference between a transcription and a clef-blind replay, not between two reads. The operational rule survives in a sharper form: **never compare an identity figure across harnesses**, and stamp every arm with its clef regime as well as its page-set regime. Original text follows. — **The read-pass floor is LARGER than the faults being measured.** Two whole-work passes of the same PDF differ by **50 of 807** records where a flag moves 6 — and pass B's margin evidence *strictly contains* pass A's (962/962 shared rows agree, 11 extra labels, zero contradictions) yet scores WORSE. **More correct evidence, worse answer.** Settling it is one ~26-min read pass at one commit; until then, no single-pass identity delta under ~50 records is evidence. |
| D2 | ✅ **REFUTED 2026-09-07. Phases 2 and 4 are unblocked.** The label manipulation moves 0 of 807 records in both clef conditions; the reference lineup is identical between the two label sets; the two extra `Timpani` labels at p50 s8 / p52 s8 are inert because slot 8 is decided by the layout fit, not by the label count. The evidence that DID matter — clefs — is additive and monotone in the right direction (0.9368 → 1.0000). Original text follows. — **HYPOTHESIS (see D0), not a finding: that the identity join is not monotone in label evidence** — which phases 2 and 4 of the identity scope both assume. If true it is the most consequential thing found all day; if it is code drift it is nothing. **Do not build on it either way until the D0 experiment runs.** The unexplained part that keeps it alive: pass B read TWO EXTRA `Timpani` labels on exactly the staff position slot 8 covers (p50 s8, p52 s8) and still named that slot by deduction. |
| D3 | **Page-set regime dominates every flag.** The same printed Beethoven system reads **4/12** in a 5-page run and 12/12 whole-work; a boundary-crossing window reads **0 of 85**. `OMR_MAX_PAGES=5` is the web app's default. `run_harness` refuses to pool across regimes — keep that. |
| D4 | **Human cost is nearly orthogonal to identity accuracy.** Between two passes identity moved 44 records and human cost moved **2** (197 → 195). Driving `impossible` to zero converted categorical errors into contradictions and left the reviewer the same number of staves. This is the scope §7 failure, now measurable — and it is the thing Sean's "human interaction is the most expensive part" was meant to prevent. |
| D5 | **Calibration is blocked on WORKS, not records.** ECE 0.1277 (n=197) → 0.0204 (n=1571) is not calibration: Brier skill vs a constant predictor **+0.0004**, 95.8% of mass in one bin, and every non-`label` tier is unseen in its own fold (`score_order` predicted 0.990, observed **0.000**). `label` was 89% of the old corpus and is 89% of this one. **Two more hand-read works, or the held-out-label design.** Dvořák 9's lineup is already in `corpus.py` awaiting an arm. |

## E. Wired but undecided

| # | item |
|---|---|
| E1 | **The label-contradiction signal is live and unconditional** (fires 158 times, 0.873 of them the export being wrong, 0 both-right). What it should DO is undecided. Per scope §8b the default assumption is an additive evidence term, not a veto — but three cheap direction discriminators were measured and the sharpest **inverts between works**, so the signal says the chain `staff → slot → name` is broken, not which link. |
| E2 | **Structural accounting prints on every scan run**; the page-normalised truth exists, is versioned and control-validated, and is NOT the score. Adopting it is a benchmark-era decision and needs 20/20 map coverage first (15/20 today, and A1+A2 would take it to 19/20 with Bach unreachable). |

## F. The identity-upstream programme (scope §5)

Phase 0 **done** — the harness exists, runs in ~10 s off committed JSON, 78 arms,
1571 graded records, three self-tests passing in both directions.

Phases 1-4 not started. ✅ **D2 is refuted and phases 2 and 4 are unblocked** —
adding evidence was measured to make the answer worse exactly zero times; see D0.
⚠️ Two things to carry in instead: (a) **phase 1's evidence store should record
the CLEF channel**, which is worth 51 records on Beethoven 5 where the label
channel is worth 0, and which a replay harness silently drops; (b) **58 of the
harness's 59 arms are clef-blind replays and exactly one is a transcription**, so
an identity figure needs a clef-regime stamp beside its page-set regime stamp.

## F2. The architecture / decision map (commissioned 2026-09-07)

Sean: *"a map of every recognition point, every time there is a decision and a
list of what information that decision needs, as well as a tracking of how each
piece of information is used once it is gathered and where it should be used…
**We need the architectural blueprints.**"* Purpose is a **checkpoint for every
agent building a tool or process** — what is available, what could help, and how
what it is gathering fits the whole.

Commissioned with three axes: the decision inventory; **dependencies, best order,
what can run in parallel, and the interreferential cycles**; and — ⚠️ **LOW
PRIORITY, tracked here so it is not lost if the agent skips it** — a **VISUAL**
version, generated rather than hand-drawn, in which an unconsumed output, a
cycle, and an unsatisfiable dependency are each obvious at a glance rather than
findable only in a table.

Why it is worth a commission of its own: this project's most-repeated defect is
information gathered correctly and then silently unused — nine export gaps found
by forensics, 85 inert consistency warnings, `confidence` reaching `export.py`
only as a comment, ~20 sites that compute a number and discard it while
refusing, and (2026-09-07) the clef channel worth **51 records** on a work where
labels were worth **0**, dropped without complaint by 58 of the identity
harness's 59 arms. **The map's job is to make that visible by construction
instead of by a day of forensics.**

## G. Housekeeping

- **~108 worktrees**, survey at `docs/worktree-prune-survey-2026-09-06.md`. Nothing deleted. ⚠️ Merge state does NOT protect gitignored cell PNGs — 6,486 images were rescued into the main checkout today for exactly this reason.
- **Three agents were blocked from writing files named for reports.** Two findings files had to be transcribed by the coordinator from chat messages. Worth fixing at the harness level.
- `OMR_EVAL_INDENT_MM` — **measured and closed**: 8 edits of 2362, noise, not worth a fixture discontinuity. Flag stays off.
