# Overnight session log — 2026-09-10 into 09-11

A manager session: one agent at a time, each job merged and verified before the
next is dispatched. Picked up from
[docs/handoff-2026-09-10-three-families-wired.md](handoff-2026-09-10-three-families-wired.md),
executing the remainder of **Phase 1** of
[docs/plan-2026-09-10-wire-first-then-reconcile.md](plan-2026-09-10-wire-first-then-reconcile.md).

⚠️ **This is a LOG, not a findings document.** Every number in it is a pointer
to the arm that produced it. Nothing here is a measurement of its own.

---

## The standing order

Phase 1 wires every remaining decision end to end — adjudicator, emission,
counter — and then **STOPS**. It does not tune. The plan's §2b is the condition
that makes that safe:

> A wiring pass may connect a decision. It may not let one GUESS.

Phase 2 (the first cleanup count on one real movement) is explicitly **not**
this session's work, and its categories must be fixed before anything is
looked at, or the count fits itself to what was found.

---

## 0. The merge that opened the night

`origin/claude/reengraved-fermata-wiring-6958e6` was **18 commits ahead of
main and 0 behind** — a clean fast-forward, landed at `dfc6f409`.

**Verified on the merged tree rather than on the branch's word:**
`python3 -m pytest tools/omr/tests -q` → **3,661 passed, 11 skipped** in 9m18s,
which is the figure that handoff claims to the test. That is the baseline every
job below is measured against; anything under it is a regression.

⚠️ A fast-forward makes the merged tree identical to the branch tip, so this
particular check is cheap. It is run anyway because *measure the MERGED tree*
has been paid for here before.

---

## The jobs

| # | Phase 1 item | branch | state |
|--:|---|---|---|
| 1 | `wedge_anchor` (item 3) | `claude/staged-wedge-anchor` | dispatched |
| 2 | tie CHAIN, `tied_to_next` / `_from_prev` (item 5) | — | queued |
| 3 | `direction` (item 6) | — | queued |

Each entry below is filled in when the job lands, with what it measured and
what it refused.

### Job 1 — `wedge_anchor`

Dispatched with handoff §6 as the brief, and with its one open **stage-boundary
decision** named as the thing to settle before writing code: calling
`_legacy._wedge_anchors` from the exporter is the `_pair_arcs` precedent but
leaves the adjudicator nothing to decide, while deciding in the adjudicator
restates three measured constants unless the legacy function is refactored.

⚠️ Reach is **0 on Litolff and 47 on Brahms**, so Brahms is the only fixture
and a Litolff run would produce a meaningless clean zero. Carried into the
brief explicitly.

⚠️ Also carried: `coverage()` reports this family's `detector_glyphs` as **1**
against **47** rows on the record, because the count is over the DETECTOR's
class space and 46 of the 47 came from the `cv_hairpins` rung. **A family whose
ink comes from a CV reader is under-reported by that headline** — anyone
sizing this work off the coverage report reads its reach as 1. Folded into the
job as a reporting fix rather than left as a footnote.

### Job 2 — the tie CHAIN (`tied_to_next` / `tied_from_prev`)

Dispatched **in parallel** with job 1 on Sean's instruction: a Brahms 4-page
gather is ~45 minutes of pure waiting, and one-at-a-time was costing that time
for nothing. Chosen as the parallel job on a **collision** argument rather than
a priority one — it is the one Phase 1 item that barely touches
`staged/export.py`, because the exporter ALREADY sets both flags
(`staged/export.py:765-766`, from `_pair_arcs`). Job 1 is working in the
`<direction>` / `<wedge>` emission path; these two do not meet.

⚠️ **It runs the OPPOSITE direction from every other wiring item, and that is
its whole hazard.** Everywhere else the record knows something no file carries.
Here the exporter already does the job and the RECORD cannot name it — so the
failure mode is not a missing feature, it is a **decorative quantity**: one
that closes `gather_coverage`'s last two `NO VOCABULARY` entries, reports
green, and is read by nothing. CLAUDE.md already names that shape (*a `wants`
entry the decision never reads is INERT*). The brief sets the bar accordingly:
**the quantity must be READ by something, or the job returns an argued
negative** — and an argued negative was declared an acceptable deliverable up
front, so the agent is not pushed into shipping a green line.

Three things it was told to settle before writing code, not during: what the
SUBJECT of a chain is (a chain is not one arc, and `Q.ARC_KIND` already decides
per-arc); which STAGE owns it (a chain may be *entailed* rather than
adjudicated, which would make it an EVALUATE consequence — and EVALUATE may
not contain a tie-break); and whether `export.py:3282`'s
`tied_to_next=(tied_to_next and ni == 0)` has the **chord-first-member** defect
the fermata work found one week ago in a different function. That last one was
put in as *look, do not assume in either direction*.

**LANDED** — merged at `4ef4a21b`. Suite on the MERGED tree: **3,707 passed /
11 skipped**, matching the branch's claim and +46 over the 3,661 baseline.
`health --check`, `inventory --check`, `gather_coverage` all exit 0.
Findings: [benchmarks/omr-staged-wedge-2026-09/FINDINGS.md](../benchmarks/omr-staged-wedge-2026-09/FINDINGS.md).

`<wedge>` **0 → 20** on Brahms, byte-identical outside the wedge elements,
music21 reading back exactly 20. **46 of 47 decided, 1 abstained
`no_page_frame`** — and that one is precisely the box-less `detector` row, so
the abstention branch is exercised by the page rather than merely defended.
**`stubs()` is now `('direction',)` — one left.**

⚠️ **Its own report of what it got wrong is the most useful part**, and two
items are worth carrying:

* **A `wants`-shaped ordering bug that NO behavioural test could have found.**
  Placed beside the fermata in `ORDER`, `wedge_anchor` ran *before* `Q.VOICES`
  and read `None` every time — and *"one voice"* and *"voices unknown"* give
  the same answer on every one-voice page, so the page cannot tell them apart.
  `inventory --check` caught it. That is the *silent arbiter* shape arriving in
  a new place: **the test that would distinguish the two readings is the one
  the corpus cannot supply.**
* **A byte-identity control that was VACUOUS and nearly shipped.** Exporting
  three committed transcriptions before/after matched — and `grep -c '<wedge'`
  on all three is **zero**, so the code never ran. This is CLAUDE.md's second
  family (*a control that was never testing what its name says*) for the eighth
  recorded time. Replaced with a probe that drives the function directly and
  prints how many cases ANSWERED (10 of 12) as its own positive control.

⚠️ It also shipped and then found **its own accounting bug**: a per-part head
index made *"not in this part"* and *"never written"* the same condition, so
ten decided hairpins were counted by nobody while the balance reported
`True` — **because it had been written as `<=`**. The previous session's
warning (§2 of the three-families handoff: relaxing the balance to an
inequality would have shipped a real bug) **came true within a day, in a new
counter, written by someone who had read the warning.** It is now an exact
equality: 20 + 26 = 46.

⚠️ Its mutation battery paid **twice** — 9 of 19 arms not red on the first run
(2 mis-anchored onto `arc_owner`, 1 equivalent mutant, **6 genuine gaps**), and
it caught more again after the repair. Final: 21 arms red, positive control
red.

#### A hazard it found in passing, recorded and deliberately NOT fixed

The Brahms record is stamped `e3d0d455, dirty: false` — **a commit that did not
exist when the run began.** `_provenance()` reads git at the END, so a long
gather started on tree A and finished on tree B is stamped B, and **a clean
stamp is no evidence the tree was clean while the page was read.**
`regather_control.py` compares exactly those stamps to decide whether two
records may be compared. Queued as its own job: fixing it means stamping at the
START as well, and whether a mismatched pair should then REFUSE is a decision
rather than an edit.

### Job 3 — `direction` (the LAST declared stub)

Dispatched off `9f1ea83e`, in parallel with job 2. Job 1's `<direction>`
emission work is already IN main, so the collision that kept this item back
earlier tonight no longer exists.

⚠️ **It is two jobs, not one**, which is why it was left for last:
`Q.DIRECTION_WORD` is the last input-starved quantity on the record, so the
gatherer must be written as well as the adjudicator. The READING half already
exists on the legacy path (`direction_text.py`, default-on, gated on a
181-word musical lexicon that CLAUDE.md marks *never loosen*) and the brief
forbids rebuilding it.

**The one line that matters most in that brief** is CLAUDE.md's own governing
rule, because this family walks straight into it: the direction reader
**self-disables where neither `.venv-surya` nor Tesseract exists**, so

> A fallback must never convert *"cannot tell"* into a definite answer.

An unavailable OCR rung gathering zero words is otherwise indistinguishable
from a page with no words printed on it. Making those two states
unrepresentable-as-one is the acceptance condition, ahead of any coverage
figure.

Three hazards measured in the last 24 hours were carried in by name, because
each has already cost someone a re-run: **ORDER placement** (a decision reading
`None` from a quantity settled later, which no page can detect); **a
byte-identity control passing while the code never runs**; and **a mutation
battery anchored on a fragment that occurs three times**, silently mutating a
different function. The `<=` balance warning was repeated in the strongest
terms available — it has now been ignored once by someone who had read it.

**LANDED as an ARGUED NEGATIVE** — merged at `5f57e183`. Suite on the MERGED
tree **3,728 passed / 11 skipped** (3,707 + 21); `NO VOCABULARY` still reads
**2**, which is the negative standing rather than being papered over. Findings:
[benchmarks/omr-staged-tie-chain-2026-09/FINDINGS.md](../benchmarks/omr-staged-tie-chain-2026-09/FINDINGS.md).

**No `Q.TIE_LINK` was built, and that is the right answer.** The reason is
structural and closes the item rather than deferring it: **nothing below EXPORT
can contribute a record row at all.** `staged/__main__.py` writes the record
JSON *before* it imports the exporter, and a part is built inside `export.build`
from `Q.PART_PARTITION` — so the merge that makes two detected halves one tie
has no home in the record. EVALUATE is excluded separately, on the plan's own
testable rule: `_paired_spans` prefers the first head's VOICE over dropping the
span, which is a tie-break, and **no EVALUATE consequence may contain one.**

⚠️ The handoff's framing of this item (*"the exporter ALREADY sets both flags;
what is missing is a quantity NAMING the chain"*) was accurate and **stopped one
step short** — it did not say the record has no way to receive one. That is now
written into `NO_VOCABULARY` itself, where the next person meets it.

REACH, measured by calling the exporter's own functions so the figure cannot
drift from what the exporter does:

| | Litolff p1-3 | Brahms p0-3 |
|---|--:|--:|
| tie LINKS / CHAINS | 59 / 46 | 632 / 275 |
| chains longer than two notes | 4 | **82** |
| crossing a system break | **0** | 2 |

⚠️ **One document would have got two things wrong**: on Litolff the
system-break case looks IMPOSSIBLE and every chain looks like a pair. The
second publisher correcting the first, for what is now at least the fifth time
in this thread.

#### ⚠️⚠️ The defect it found is worth more than the quantity would have been

**A chord's tie is written on the wrong note.** `<tied>` carries no `number=`
and joins the two notes it names, but `voicing.group_chords_in_measure` hoists
the flag onto the EVENT with `any()` and the renderer writes it at `n == 0` —
so a chord whose UPPER member is tied gets the tie on its LOWEST note.
Measured: **17 of 48 written ties on Litolff (35%) and 103 of 349 on Brahms
(29%)** land on a note carrying no tie — **two publishers agreeing to within
six points**, which is what makes it structural rather than one page's luck.

⚠️ It is the **fermata bug's shape, one week later, in a different function and
worse**: that one LOST a mark, this one puts a mark on the WRONG NOTE.
⚠️ **Correctly NOT fixed here.** The hoist is in `voicing.py`, shared with the
legacy exporter and therefore with the 11-work engraved benchmark, and the
repair moves hundreds of elements — *a wiring pass may not change behaviour it
has not priced*, which is the plan's §2b applied to the agent's own temptation.
It is now counted on every run. **Queued.**

⚠️ A second defect, found and fixed: `FAMILIES` maps **both** `tie` and `slur`
to `Q.ARC_KIND` and `coverage()` credited **each with the whole population** —
`decided: 514` where the split is 270/244. A reader comparing `decided 514`
against `written 49` would have concluded the exporter drops 465 ties. Now
attributed by value, derived from `FAMILIES` itself.

⚠️ Its own first reach probe failed in the way this repo predicts, and it said
so: a `start -> stop` dict loses a head that begins two links and read
`{2: 50}` — **a plausible histogram whose tell was that not one chain exceeded
two notes** on a document that plainly holds longer ones. *A plausible
aggregate is not evidence that its parts are real*, for the second recorded
time.

### Job 4 — the chord tie, repaired and PRICED

Dispatched in parallel with job 3, off `818d8e26`. **Not a wiring job** — a
measured correctness defect handed over with its price already taken, which is
exactly the handoff job 2 was right to make rather than to do.

The crux is a stated convention that is **wrong for MusicXML**, and the brief
leads with it because the symmetric-looking line three rows below is CORRECT:

> a `<tied>` element carries **no `number=`** — it binds the two notes it names.
> A `<slur>` does carry one and legitimately attaches once per chord.

So the slur hoist beside it must NOT be "fixed by symmetry", and the brief says
so by name. The repair itself deletes a lossy collapse rather than adding a
rule: the per-note flags already survive on the group members, so the renderer
can read each note's own flag instead of the event-level `any()`.

⚠️ **The pricing is the job, not the patch.** `voicing.py` is shared with the
legacy exporter, so this reaches the 11-work engraved benchmark and the 20-row
scan gate. Four traps were carried in by name, each already paid for here:
`scan_eval` **caches by default** and a cached A/B reports *identical on every
row* — the clean result a change like this hopes for, whose only tell is the
wall clock; the gate's **±6 edit** noise floor; OMR-NED's symmetry
**rewarding under-prediction**; and the real possibility that **the metric is
blind to this entirely** — the same number of `<tied>` elements is written
either way, just on different notes, which is precisely the whole-rest
convention's situation (identical on both families while the symbol ledger
recorded 1,251 corrections). If the metric cannot see it, the ledger scores it.

⚠️ One judgement was named rather than left to be discovered: **LilyPond's `~`
is a chord-level suffix and cannot express a per-note tie.** The two exporters
may legitimately diverge — `_lily_wedge_plan` set that precedent by dropping
what it cannot express rather than approximating — but the choice must be
stated, not made silently.

The brief ends by making a **measured refusal an acceptable outcome**: if the
price is unacceptable, come back with the number. This repo's refusals are
among its most valuable entries and an agent that believes it must ship will
ship anyway.

**LANDED** — merged at `11b8866b` (+ the branch's last two commits). Suite on
the MERGED tree, run here rather than taken on trust: **3,741 passed / 11
skipped** (3,728 + 13). Findings:
[benchmarks/omr-chord-tie-2026-09/FINDINGS.md](../benchmarks/omr-chord-tie-2026-09/FINDINGS.md).

**The repair is essentially free and it is not the headline.** Engraved
**2532 → 2530** edits; scan (11 rows) **34,731 → 34,739**, +8 at 0.023%, and a
third measurement-only arm SPLITS that +8: **relocation alone is +2, the twelve
newly-expressible marks are +6** — the metric's under-prediction reward,
charged for writing ties the record says are there. Shipping the cheaper
relocation-only arm was **refused on exactly that ground**, which is the right
call: it would have withheld twelve correct marks to please a metric.

⚠️ **Every moved element was adjudicated, not sampled** — and with no print,
because the record carries its own test: `record.Checkable`'s rule that *a
tie's two ends must be the same pitch*. The one engraved element ties
**G2 → D5** before and **D5 → D5** after. Decisive.

#### ⚠️⚠️ The finding that outranks the repair

**`transcribe._pair_ties_in_staff` pairs tie ends by GEOMETRY; `<tied>`
resolves by PITCH.** **20 of 79 engraved links (25%) and 64 of 237 scan links
(27%) bind two notes of different pitch** — thirds — and a further **115 of 237
scan links (49%) have no end in the next event at all.** No renderer can write
those correctly.

⚠️ **The old hoist was MASKING it**, by writing both ends at the chord's bottom
note so that any two chords sharing a bottom pitch agreed by accident. The
proof the mask was accidental is the sharpest thing in the report: **the base
arm resolves 60 ties where the record supports at most 58.** So the +8 is not
the repair being wrong — it is a defect becoming *visible*.

**The boundary case is handed over ready to run**, and it is the good kind —
two ENGRAVED pages where the pitch reading is near-perfect, so the pairing is
the only suspect: `mozart-sym41-mvt1` **8 of 9 wrong** against
`beethoven-sym5-mvt1` **11 of 11 right**. `probe/pairing_pitches.py` needs no
truth file.

⚠️ **LilyPond diverges, deliberately and on evidence rather than on principle**:
`~` after a chord resolves BY PITCH, verified by compiling both cases
(`<c e g>~ <c e>` ties silently; `<c e g>~ <d f a>` warns three times), **so the
defect does not exist there** and the exporter was left alone.

#### ⚠️ Two instrument failures worth more than their fixes

* **A race it created and caught**: the mutation battery `git checkout`s the
  file it mutates while a three-arm A/B was reading the live worktree — and
  `export.py` was in fact left mutated. Both killed, arms re-run against
  snapshot trees, and the clean results **checked** (the snapshot run
  reproduces 34739 and 2530 to the edit) rather than argued.
* ⚠️⚠️ **`pytest` reported `577.54s` for a run that took hours of wall clock.**
  That is TEST time, not elapsed — *the number that makes a starved run look
  normal in a log*. Under a load average above 7 from sibling sessions it twice
  nearly reported a starved run as a HANG, and what separated the two was the
  process CPU clock, not the progress bar. ⚠️ And diagnosing it by running
  candidates in parallel made it worse: **the instrument competed with its
  subject.** Carry this into any overnight run on a loaded machine.

#### ⚠️ A correction I had to make MYSELF, and it is the named failure

The agent reported the tie-chain findings doc and CLAUDE.md *"both corrected in
place"*. **CLAUDE.md was; the findings doc was not** — §2 still read
**NOT FIXED, DELIBERATELY** with no supersession note, one day after it was
fixed. That is *fixed-then-kept-open-in-prose*, the documentation dual of
detected-then-dropped, which this repo has now paid for three times (the
accents claim, the `Tp.` branch, this).

⚠️ **The governing file being right is what makes the stale copy dangerous**:
whoever opens the findings doc first meets a work order that no longer exists,
and nothing contradicts them. Supersession note added here, with the original
reasoning explicitly NOT retracted — declining to change unpriced shared
behaviour was correct, and *a wiring pass may not change behaviour it has not
priced* never forbade the repair, it named its precondition.

⚠️ **The general lesson for this manager role: a report saying "docs corrected"
is a claim about the tree and is one grep from being checked.** It was checked
here because CLAUDE.md has a standing warning about exactly this shape.

### Job 5 — tie pairing: GEOMETRY in, PITCH out

Dispatched off `0b1efb31`, in parallel with job 3. **A diagnosis-first job**,
and the brief says so in its first line: *do not open with a fix*. The defect
has been invisible for months; naming its cause is worth more than a rushed
patch, and **a diagnosis with no repair was declared a complete deliverable.**

`_pair_ties_in_staff` (`transcribe.py:2390`) pairs a tie's two flanking
noteheads by **page-pixel geometry** and sets two booleans. It **records no
link** — and `<tied>` carries no `number=`, so the ends are re-associated
downstream **by pitch**. Two mechanisms, no shared identifier.

⚠️ **The boundary case is the gift and the brief leads with it.**
`mozart-sym41-mvt1` is **8 of 9 wrong**; `beethoven-sym5-mvt1` is **11 of 11
right** — both ENGRAVED, where the pitch reading is near-perfect, **so the
pitch reading is ruled out as the confound and the pairing is the only
suspect.** That is an unusually clean separation for this project. Four
hypotheses were handed over unprivileged, with a note that the answer may be
more than one — the leading one being that Mozart 41's Viola plays **divisi
double stops**, which CLAUDE.md already records as distorting that work's note
recall, and which is *exactly* the geometry (two heads a third apart at one x)
that a nearest-flanking-head rule gets wrong.

⚠️ **The invariant is what makes this measurable at scale with no truth file**:
a tie joins two notes of the SAME pitch — that is what a tie IS, and
`record.Checkable` already encodes it. So a pairing that binds a third is
**provably** wrong off the print. The brief forbids weakening it to make a rule
pass, and allows exactly one exception, handled as a spelling question rather
than a tolerance: enharmonics.

⚠️ One boundary drawn in advance, because it is the difference between a fix
and a fabrication: **using the pitch invariant as a VETO is legitimate; using
it to SEARCH for a same-pitch partner is not obviously so** — that manufactures
ties between notes that merely share a pitch. Priced apart if attempted.

⚠️ And one trap specific to this job, which would otherwise have produced a
confident zero: **`_pair_ties_in_staff` runs inside `transcribe`, not inside
`export`**, so the export-only A/B that every recent job has rightly preferred
is **structurally blind to this change**. Named in the brief as something to
check *before* trusting a zero — a control that cannot see its subject is this
repo's single most repeated instrument failure.

**LANDED — and PHASE 1 OF THE WIRING PLAN IS COMPLETE.** Merged at `7a1a0bf8`.
**`adjudicate.stubs()` is `()`.** Suite on the MERGED tree: **3,765 passed / 11
skipped**. Findings:
[benchmarks/omr-staged-direction-2026-09/FINDINGS.md](../benchmarks/omr-staged-direction-2026-09/FINDINGS.md).

⚠️ **The check itself needed care**: a bare `import adjudicate` leaves
`REGISTRY` empty and `stubs()` returns `()` **for the wrong reason**. I hit
that earlier tonight and nearly reported it as a discrepancy against job 1.
The registry fills when the adjudicators package loads — *a passing check can
mean nothing*, and this one has two ways of passing.

**REACH, and this family has THREE ways of being empty**, which is the whole
point of the job:

| | Litolff p1-3 | Brahms p0-3 |
|---|--:|--:|
| word-shaped candidates (the CV's ink) | 42 | 56 |
| accepted by the lexicon | **2** | **10** |
| `<words>` written | 0 → **2** | 0 → **10** |

Both OCR rungs live for every figure, so **none of these zeros is the
machine's**. ⚠️ **Nothing here is a rate — it is 2 and 10.**

**The acceptance condition was met, and with more structure than asked for:
FOUR states, not two.** `READER_UNAVAILABLE` and `OUT_OF_SCOPE` are
**abstentions**; `NO_INK` and `NO_READING` / `NOT_IN_LEXICON` are **a decision
with an empty value**, because *"this bar carries no words"* is a definite
answer. Both write nothing to the file — correctly, since **MusicXML cannot say
"a reader could not run here" and the record can**, which is exactly where the
distinction belongs.

⚠️ **The load-bearing detail is where the page-wide reason is filed**: on every
CELL as well as the page. Without that, a blind page has no `Q.DIRECTION`
subject at all and reports `decided: 0, abstained: {}` — **a family never
ASKED, indistinguishable from one asked and silent.** That is the same
collapse, one level up, that the brief was written to prevent.

⚠️ **The control that mattered was the shim, and the failure it guards against
is invisible**: a wrong `bbox_page` convention **does not raise**, it just
looks like *"this document has few directions"* — which is ALSO the true
answer. Run against the legacy path on the same four pages: **10 accepted vs
10, and 7 of 7 `(page, text)` pairs exact.** ⚠️ It compared the text SET and
not just the count, *because 10 == 10 over different words is
coincidence-as-diagnosis* — the lesson job 4 recorded, applied by a different
agent before it could bite.

#### ⚠️⚠️ Three corrections to this file and the handoff, one of them new

1. **THE IMPORT HAZARD IS BIDIRECTIONAL AND ONLY ONE DIRECTION WAS RECORDED**,
   and the missing half cost two gathers (~50 min). The handoff says the
   exporter is imported AFTER the gather, so a mid-run edit **reaches** it. The
   mirror: a module imported at process **START** keeps its code, so a mid-run
   edit silently does **NOT** take effect — while `_provenance()` reads git at
   the END and stamps the new commit. **A stamp taken at the end names the tree
   that FINISHED the run; the code that RAN is whatever was on disk at first
   import — and the stamp reports neither.** Three sessions have now each found
   one fact about that single import order.
2. **A FOURTH "declared input that could never answer"**, and it is the one no
   derived tool can catch: `ev.rows(Q.DIRECTION_WORD)` at the default
   `Scope.EXACT` can never see a word, because words are on glyph subjects.
   `inventory --check` and `gather_coverage` are both blind to it — **the
   `wants` entry IS read and the quantity IS gathered.** Only a test asserting
   a word comes out of the file found it.
3. `coverage()` under-reports this family **21× and 5.6×** — it counts accepted
   WORDS where the family's ink is the CANDIDATES. Same shape as the wedge's
   1-against-47, from the other direction. **Deliberately not fixed**: it would
   move every family at once.

⚠️ **Its mutation battery went 18/18 red on the first run and it recorded that
as WORTH DISTRUSTING**, since the battery came from the same hazard list as the
tests — the first agent tonight to treat its own clean result as suspicious
rather than as a finish line.

**Not established, in its own words**: no word checked against the print
(equivalence, not truth), no recall figure, n = 2 documents / 7 pages / **12
words**. ⚠️ **Brahms pages 2-3 yield 20 candidates and ZERO accepted words and
were not opened** — the largest unexplained population, and the honest place
for the next session to start.

⚠️ One correction I made myself again: the wedge section's heading still read
*"the LAST declared stub is now `direction`"*, true for exactly one day. The
file's other two stub-count blocks already carry an explicit *"that was the
state on \<date\>"* guard; this one relied on the superseding section sitting
below it, which does not help a reader arriving by search. Same guard added.
**Second manager-side prose correction in two jobs** — worth noting as a
pattern rather than as two incidents.

---

## PHASE 1 IS CLOSED — what the night bought

| | at `dfc6f409` (start) | at `1659a299` |
|---|---|---|
| declared stubs | `arc_kind`, `arc_owner`, `articulation_owner`, `wedge_anchor`, `direction` → **5**, three days earlier | **`()`** |
| `NO_VOCABULARY` | 2 | 2, **now with a written reason** |
| suite | 3,661 | **3,765** |

⚠️ **The exit condition is the plan's, not a headline**: *`gather_coverage`
reports no family the detector reads and the record cannot name, except those
with a WRITTEN reason.* The two survivors (`tied_to_next` / `tied_from_prev`)
acquired theirs tonight — job 2's argued negative, which established that
**nothing below EXPORT can contribute a record row at all**. So the condition is
met by an argument rather than by a build, which is the honest way for it to be
met and is why that negative was worth more than the quantity would have been.

### Job 6 — the Phase 2 instrument

Dispatched off `1659a299`, in parallel with job 5. Phase 2 is *"one movement,
one human pass"* — **Sean's judgement, not an agent's** — so the brief's first
constraint is a prohibition: **you are not doing the count.** A machine
pre-pass is allowed and must be labelled as a proposal *in the artefact*, never
merged into the human's marks.

⚠️ **The plan's ordering constraint is the heart of it and it is ENFORCEABLE.**
*Fix the categories BEFORE looking, or the count fits itself to what was
found.* So `CATEGORIES.md` is committed **first and alone**, and `git log` is
the proof; a later revision must be a NEW commit saying what changed, never an
amend. That turns a discipline into an artefact.

The four categories are the plan's (**missing / wrong / spurious /
would-not-notice**) and are not the agent's to replace — but **the definitions
are the real work**, and four hard calls were handed over by name because each
has already broken a metric here: whether a right-pitch/wrong-duration note is
one *wrong* or a *missing* plus a *spurious* (OMR-NED's answer to that is what
made its buckets unrankable); whether a failed staff is one item or many
(attributing by the `entire staff` bucket **systematically under-counts
fragmentation**); **whose eye** *would-not-notice* refers to — engraver, player
or editor, which differ; and what the UNIT is, since a human cleaning up works
in **fix-actions** and that is what Sean's question asks about.

⚠️ The artefact must be ordered **by where the human's time goes, not by page
number** — a structurally failed page must not sit behind thirteen that are 95%
right.

⚠️ And the one thing Phase 1 bought is what this artefact has to spend: when a
family is absent, the record can now say whether **the page has none**, **the
detector found none**, or **a decision abstained**. Three different facts, and
the brief requires them reported apart.

### Job 5 — tie pairing: LANDED, and it refuted the brief

Merged at `753d5965`. Suite on the MERGED tree **3,779 passed / 11 skipped**
(3,765 + 14, exact). Findings:
[benchmarks/omr-tie-pairing-2026-09/FINDINGS.md](../benchmarks/omr-tie-pairing-2026-09/FINDINGS.md).

⚠️⚠️ **THE BRIEF WAS WRONG AND THAT IS THE RESULT.** I wrote that because both
boundary pages read pitch near-perfectly, *"the pitch reading is ruled out as
the confound and the pairing is the only suspect."* **There was a third suspect
and on that case it is the one — the arc's CLASS.** One `grep` settles it:

| | truth `<tied>` | truth `<slur>` | detected `tie` | detected `slur` |
|---|--:|--:|--:|--:|
| `mozart-sym41-mvt1` | **2** (one tie) | **88** (44 slurs) | 13 | 60 |
| `beethoven-sym5-mvt1` | **27** | **0** | 17 | 2 |

Mozart's page prints essentially **no ties**, so 12 of 13 `tie` detections are
false — and a false tie lands on whatever two notes a **slur** connects.
Beethoven's page prints **zero slurs**, so a class error there is impossible by
construction. **The 8-of-9 against 11-of-11 is what the pages PRINT**, not how
they are paired. My "only suspect" framing enumerated two causes and asserted
the remainder; the agent counted a third.

⚠️ **And the 25% headline was three populations wearing one number.** Split:
**SPELLING 11** (same staff STEP, accidental differs — **the PROBE is wrong,
not the pairing**: it compares *spelled* pitches, and `export._pitch_step`
exists in this repo precisely because that is the wrong key), **STEP_APART 8**
(the class), **WIDE 4** (the pairing). So the engraved pairing defect is
**5.7% of links, not 25%** — a number I had passed on twice.

**The decisive instrument needs no truth file and is the durable part**: a
tie's two heads are at ONE staff position, so box-y is a *second reading* of
each link. **Engraved 70 of 70 on the diagonal, zero off it.** The scan breaks
in one direction only — 25 links at one position whose pitches disagree anyway
(pitch-reading faults, not pairing) and 108 of 302 genuinely far apart.

**Repaired**: the two flanking heads are now chosen **together**, a pair at one
staff position outranking one that is not — additive, comparative, **reading
boxes and never pitch**, which is what keeps it clear of `OMR_ARC_RECLASS`'s
measured refusal. ⚠️ **The missing premise was already written down**:
`_pair_ties_in_cell`'s own docstring says *"real tied notes are at the same
y-position by definition"* — **and neither rule ever used it.** *The value
existed and nothing read it*, in a docstring this time.

⚠️ Price: engraved **0 edits** with both files DIFFERING — one `<tied
type="stop">` relocates per work and **OMR-NED charges nothing, because it
pairs by pitch**. Scan **unmeasured and declared so**: reach is there
(same-position links 122 → 183) but the ±6 floor cannot resolve it and the
cheap routes are closed. Refuted with evidence and worth not re-trying:
**divisi double stops** (the candidates are successive notes, dx 47 and 115 —
no chord in any link) and **arc span** (flanking is exact, 2-4 px).

#### ⚠️ A second, unrecorded defect — found by a control FAILING

`_pair_ties_in_cell` and `_pair_ties_in_staff` set flags; then
`_dedupe_cross_staff_detections` runs **later** and deletes the losing copy of a
contested tie **without its flags**. **27 of 148 engraved tie flags have no tie
glyph in their staff, and 27 of 27 are explained by the next staff down holding
it.** ⚠️ It also means **a stored `.omr.json` cannot be replayed faithfully** —
which bears on every export-only arm this project runs. Not repaired; it needs
`Q.TIE_LINK`, **now with a third independent symptom** and a stronger case than
job 2 could make.

#### Instrument failures, and one is CLAUDE.md's own documented trap

1. Its first re-transcribe A/B excluded **11 of 11 rows** because the base tree
   had **no `.venv-surya`**, so Surya self-disabled and Tesseract read the words
   — **the worktree symlink trap, from inside a control built for something
   else.** The four-symlink warning exists for exactly this and still caught
   someone who had read it.
2. The run then **wedged on the shared Surya server**; restarted under
   `OMR_SURYA_KEEP_ALIVE=0`, **only its own PIDs killed**, `llama-server` left
   alone. The standing rule held under pressure.
3. `counterfactual.py` counts link **properties, not identity** — it named one
   reachable work and the arm moved two. ⚠️ ***Counting cannot see a
   relocation; only naming the notes can*** — the same lesson the arc-export
   session learned (a frame error is invisible to a span count) arriving from a
   third direction.

⚠️ It also corrected `OMR_ARC_RECLASS`'s row in CLAUDE.md, whose engraved
figure **predated the chord-tie repair landed six hours earlier** (2530 → 2536,
+6, not +2; scan +149, not +130) and whose *"all +130 is in the tie→slur half"*
is true and **not actionable as stated** — that half is FOUR rules, only one is
provable, and on the three works where it fires alone the arm is **−4 edits**.
**The refusal still stands.**

### Job 6 — the Phase 2 INSTRUMENT: landed, and scoped to ONE page on Sean's call

Merged at `55efe3c8`. Suite **3,779 / 11** unchanged, which is the expected
result: this branch adds an instrument and an artefact, not pipeline behaviour.

⚠️ **The commit ORDER is the deliverable as much as the artefact is**, and it
holds: the four categories landed **first and alone** (`175812e9`), the
instrument second, the artefact third, and the worked examples came back as
their **own later commit** (`43b1d25c`) rather than as an amend of the first.
So `git log` is the evidence the definitions were not fitted to what the
artefact turned out to contain — the one discipline a cleanup count cannot
recover after the fact.

**Sean chose option 2 — one PAGE, not one movement**, to calibrate the
categories before any wider count is trusted. The agent had already scoped
itself to pp.1-4 (tighter than its brief) and then started a whole-movement
gather, which died with the session; that gather was not asked for and nothing
is lost. **Page 1 is the calibration unit**: one system, 12 staves, 16 bars —
12 of the sheet's 77 rows. `out/counting-sheet-PAGE1-calibration.csv` is that
slice, cut by the manager rather than by re-running the builder, which takes no
page filter.

⚠️ **It answered BOTH questions the manager had flagged as needing a human,
and answered them in writing before measuring anything:**

* **The unit** is *one FIX-ACTION — one edit in a score editor, counted at the
  largest scope a single gesture repairs* — with a **closed** scope vocabulary
  (`element` … `page`) and `other` requiring a description. Re-entering a whole
  bar is **ONE** action even if the bar holds nine wrong notes, which is the
  largest deliberate divergence from OMR-NED and is the right one: musicdiff's
  amplification differs **6×-2× by error kind**, and a fix-action count is
  amplification-free by construction.
* **Whose eye** is **THE EDITOR'S** — *would you ship the file with this in
  it?* — chosen over the engraver (who notices everything, emptying the
  category) and the player (who notices almost nothing, swallowing it).

⚠️⚠️ **And it named the counter-hazard of its own unit rather than leaving it
for a reader to find: a fix-action count REWARDS a pipeline that fails in large
contiguous blocks over one that fails in scattered singles**, and those are not
equally good outputs — a scattered error is easier to MISS. Its repair is
structural: `would-not-notice` is *cost zero*, while something the editor would
fix if they saw it but might miss is `wrong` with a **`missable`** flag. ⚠️
Collapsing those two would let the count launder exactly the hazard the unit
creates.

⚠️ The 132 MB staged record is correctly NOT committed. The `attention_score`
that orders the sheet carries its own disclaimer — the weights are DISPLAY
ORDER, read by nothing, and are *"not a claim that a staff costs thirty
notes"*.

---

## Phase 2 STOPPED at the calibration page — and that is the instrument working

Sean took the page-1 pass, and the verdict is **"we are pretty far off and need
to do some more work before any calibration or more pages."** No count was
taken, deliberately, and **that is the right outcome from a calibration page**:
the plan's whole reason for fixing categories first is that a count taken over
output this wrong would measure the WIRING, and it says so.

⚠️ **He gave seven observations, and they are worth more than a total would
have been**, because five of them name a mechanism rather than a quantity.
Recorded verbatim, then grounded in the file before any agent was briefed —
because *a convincing reading of someone else's report is not evidence about
its cause*, a lesson this repo has paid for repeatedly.

| # | Sean, reading the print | grounded in the exported file |
|--:|---|---|
| 1 | the time signature is correct | `2/4` everywhere ✅ |
| 2 | key sigs should be **3 flats** except **Cl. 1 flat**, **Tr/Cor none** | `<fifths>` ∈ {−3, −2, −1, **1**, **7**}, and **five parts CHANGE key mid-part** |
| 3 | whole rests worth 2 beats come out as a single quarter | `divisions=96` → a 2/4 bar is **192**; the file writes **466 rests at 384** and **217 at 96**, with only **108** correct measure rests |
| 4 | almost no ties or slurs convert | 32 slur starts, 84 tie starts over 4 pages |
| 5 | none of the measure math makes sense | downstream of 3 |
| 6 | doubled notes on a staff, two of the same note on one stem | see below |
| 7 | the page prints only `ff`; ours has extra `f`s | `ff` 47, `f` 63, **`fff` 10, `ffff` 11** |

### ⚠️⚠️ TWO OF THE SEVEN ARE ONE CAUSE, AND IT IS A MISSING CALL

`grep -rn "dedupe" tools/omr/staged/*.py` returns **two hits and both are prose
inside docstrings**. The legacy path calls `_dedupe_cross_staff_detections` at
`transcribe.py:5557`; **the staged path calls nothing.** So the same ink
detected twice is written twice — which is a doubled notehead on one stem, and
is very likely why a printed `ff` assembles as `ffff`.

⚠️ It was already half-recorded from another direction and nobody joined it up:
the fermata wiring measured *"the 13 'absorbed' marks are DUPLICATE DETECTIONS,
not chords — 13 carriers named by exactly two marks each, overlapping boxes,
one confident and one not."* **Duplicates were known to be in the record; what
they COST was never asked.** That is the cleanup count doing its job on its
first outing — it did not need a number to find this, only a human looking at
the page.

### ⚠️ The rest arithmetic names its own mechanism

466 rests at **twice** the bar length and 217 at **half** it, against 108 that
are right. CLAUDE.md already holds the convention (*a whole-rest glyph means
the BAR*) and the consequence that applies it (`size_measure_rest`) — which
needs the **settled meter**, and the artefact's own FINDINGS record the meter
as decided on **ONE system of seven**, with `empty_bars_padded_without_meter`
at 162. ⚠️ So this is likely `OMR_METER_CARRY`, **held OFF on `n` = one
document**, visibly costing the human on the first real page anyone looked at.
The plan predicted exactly this use: *a cleanup count is what says which
abstentions are worth resolving.* ⚠️ It is NOT dispatched yet, deliberately —
a duplicated whole rest is not a LONE whole rest, so the dedupe job may move
these numbers before anyone prices the meter.

### The jobs, and why these two first

| job | covers | why now |
|---|---|---|
| `claude/staged-duplicate-detections` | 6 and 7 | one cause, two symptoms, and it pollutes every measurement downstream |
| `claude/key-signature-truth` | 2 | **a hand-read truth for a whole page exists**, which this project almost never has |
| *(held)* rests / measure math | 3 and 5 | downstream of dedupe — price it after |
| *(held)* ties and slurs | 4 | CLAUDE.md already measures **76% of merged arcs bind fewer than two noteheads** and calls that residue the DETECTOR's; likely reach-limited, and partly repaired by dedupe |

⚠️ The key-signature brief carries the three hazards this repo has already
recorded for that module — *`fit_key_signature` may not infer* (its own
recorded failure is **seven sharps on a four-sharp page**, and P7 now reads
seven sharps), *it may not carry across systems*, and *it inherits the clef
problem* (a wrong clef yields wrong signatures rather than abstentions —
measured, bass staves defaulted to treble read 3 flats as **2 sharps**, which
is the `-2` in the table). **The brief says plainly that "this is a clef
problem wearing a key-signature costume" is an acceptable answer** and worth
more than a repair in the wrong module.

### Key signatures — LANDED, and it refuted the manager's leading hypothesis again

Merged at `2c07f225`. Suite **3,791 / 11** (3,779 + exactly its 12 tests);
health, inventory, `gather_coverage`, `export_coverage` all 0. Findings:
[benchmarks/omr-keysig-truth-2026-09/FINDINGS.md](../benchmarks/omr-keysig-truth-2026-09/FINDINGS.md).

⚠️⚠️ **THE BRIEF ASKED WHETHER THIS WAS "A CLEF PROBLEM WEARING A
KEY-SIGNATURE COSTUME" AND SAID YES WOULD BE THE MORE VALUABLE ANSWER. IT IS
NO.** Over the same 75 printed staves the clef reads **68 correct / 6
abstained / 1 wrong**, and **all ten wrong key readings sit on a
correctly-read clef**. The single wrong clef (Fagotti, bass header with a
tenor change at bar 37) costs an **abstention**, not a wrong key —
`run_fits_no_slot_table` doing its job. ⚠️ The `-2` that looked like the
recorded *bass-defaulted-to-treble reads 3 flats as 2 sharps* signature is
NOT that; the manager offered that reading in the brief and it did not
survive.

**Graded twice, because the FILE CANNOT SAY "I could not tell"** — an
abstained key exports no `<key>`, which reads as no accidentals:

| | correct | wrong | abstained |
|---|--:|--:|--:|
| READING before | 16 | 10 | 49 |
| READING after | **35** | 15 | 25 |
| FILE before | 33 | — | 42 wrong |
| FILE after | **44** | — | 31 wrong |

12 gained, **1 lost and NAMED** (a Corni abstention that was accidentally
right became a template `-1`). ⚠️⚠️ **17 of the 33 "before" right rows were
ABSTENTIONS landing on a horn/trumpet/timpani** — which print no signature
anyway — **so a count of parts reading `-3` was never the score**, and the
staff→instrument join is what makes this gradeable at all. Sean's one sentence
about Cl./Tr./Cor. is the whole enabling fact.

#### ⚠️⚠️ THE BIGGEST CAUSE WAS A FOURTH MECHANISM NOBODY NAMED — AN EMPTY CROP

**Eleven of 75 header crops contained no clef and no key signature at all.**
Every window is 16.0 staff spaces except those eleven at **6.1-6.2**.
`system_left_edge` takes the **MINIMUM** of one estimate per staff; on p.2
system 1 the eleven estimates are `331, 345, 345, 263, 334, …` and the fourth
under-runs its siblings by ~70 px (4.5 staff spaces), so **the minimum PREFERS
the outlier and it decides the window for all eleven staves.**

⚠️ **ONE CAUSE, TWO DIFFERENT FAILURES, AND THE SECOND IS THE FAMILIAR ONE:**
the locator **abstained**; the template found a *"clean window"* and answered a
confident **`fifths: 0`** — **a key signature fabricated from an empty crop.**
That is *a fallback converting "cannot tell" into a definite answer*, the rule
this file already states in its widest form.

⚠️ **THE TREE IS NARROWER THAN THE REPORT AND THE TREE IS RIGHT.** The summary
said the repair *"swaps a statistic (min → median)"*; `system_left_edge`'s own
docstring says **the under-run is NOT repaired** — a second statistic is
computed ALONGSIDE the minimum so a bad `x0` now costs a window that is too
**WIDE** (which both readers survive) instead of an empty one. The direct
clamp was measured and **refused**: 3 correct readings lost for 6 new wrong,
moving 19 windows to fix 11. **Read the docstring, not the summary.**

#### It re-ranked the next work AWAY from itself

⚠️ **12 of 75 staff-systems are joined to the WRONG INSTRUMENT**, on the two
systems whose lineup is not canonical (8 staves; 11 with Timpani tacet and
Vc/Basso printed apart) — both stitched by ORDINAL. **P7's seven sharps are
the Timpani's part carrying a reading taken from the VIOLA.** That is
`_stitch_slots`, not the key reader. And the **cross-system vote** that would
fix most of the remaining key residue is **blocked on that same join** —
keyed on it, it would carry the viola's `7` onto the timpani, which is
`StaffCandidate.can_carry`'s own recorded hazard arriving from a new
direction.

**So the PART JOIN is the ranked lever**, named by the job rather than by the
manager, and it is plausibly also Sean's *"none of the measure math makes
sense"*.

#### Refused, and docs corrected

Refused: `max_inferred_ratio` (the `7` — one staff of 75, documented rationale
pointing the other way), the `x0` clamp, every locator/template threshold, and
the cross-system vote (blocked on the join). ⚠️ **Nothing was tuned.**

Corrected in place: `system_left_edge`'s docstring asserted the invariant that
makes the minimum safe — *"can only ever be too far right and never too far
left"* — **measured FALSE**; `ASSUMPTIONS.md` **D20 closed**; and
`adjudicate_key_signature`'s `checked_by` names `key_signature_corroboration`
as *"CONSUMED, default-ON"* while it is imported only by `transcribe.py` and
is **unreachable from the staged path** — with two inert `wants` entries
beside it (`KEYSIG_MARKER` is a THIRD reader, gathered and read by nothing).

⚠️ **Declared, not buried**: the after-grade is a **three-arm probe**
reproducing the shipped artefact on 71 of 75 — both repairs are GATHER
changes, so `readjudicate` is structurally blind to them — and **the
end-to-end re-gather did NOT complete**, so **no regenerated `<fifths>` table
is claimed**. `grade_artefact.py --map` is committed to finish it. n = 1
document, 1 publisher.

---

## Items 3, 4 and 5 — three agents, and how the collisions are managed

Sean: *"send agents out to work on 3,4 and 5 1 agent each manage them for
collisions."* Dispatched off `e98338cf`.

### ⚠️⚠️ THE BASELINE WAS RE-TAKEN FIRST, AND RE-TAKING IT FOUND SOMETHING

The numbers in the first triage came from the artefact built **before** dedupe
and the key-signature work landed. Re-exporting the SAME committed record on
the current tree:

| | shipped artefact | current main |
|---|--:|--:|
| pitched `<note>` | 1793 | **1618** |
| `ffff` / `fff` | 11 / 10 | **11 / 10 — unmoved** |
| rest duration 384 (2× the bar) | 466 | **471** |
| rest duration 96 (½ the bar) | 217 | **218** |
| slur starts / tie starts | 32 / 84 | 32 / **80** |
| measures per part | 111×8, 93×3, 16×1 | **unchanged** |

⚠️⚠️ **THE DYNAMICS NOT MOVING IS NOT A FAILED FIX — IT IS THE `readjudicate`
BLIND SPOT ARRIVING IN THE MANAGER'S OWN HANDS.** The dedupe repair has two
halves: `export._place_notes` (EXPORT) and `adjudicate_dynamic` (ADJUDICATE).
**Re-exporting a SAVED record replays saved verdicts**, so the export half
shows (1793 → 1618, matching that job's claim to the unit) and the adjudicate
half cannot. The same is true of every key-signature repair, which are GATHER
changes. **A re-export is a partial instrument and says so.** This is now
stated in all three briefs, because a sibling reporting "my change did
nothing" off a re-export would be reporting the instrument.

### The collision plan — ownership by PATH, not by file

All three items live partly in `tools/omr/staged/export.py`. That is
unavoidable; it is the exporter. So ownership is assigned by **path within
it**, named in every brief, with each agent told who else is in the file and
which regions are not theirs:

| agent | branch | owns |
|---|---|---|
| **3 rests** | `claude/rests-sized-to-the-bar` | `consequences.size_measure_rest`, the REST emission path, meter carry in `rhythm.py`, `OMR_METER_CARRY` |
| **4 arcs** | `claude/arcs-not-converting` | `_pair_arcs`, `_merge_arcs_across_barlines`, `annotate_slurs_*`, the slur/tie emission block, `arc_kind`/`arc_owner` |
| **5 measure math** | `claude/measure-math-part-join` | `_stitch_slots`, `Q.PART_PARTITION`, part building + measure numbering, the coverage join fields |

⚠️ **One deliberate overlap is pre-negotiated rather than forbidden**: if
agent 5 concludes the repair is to PAD the suppressed spans, that is the REST
path and belongs to agent 3. Its brief tells it to **say so and coordinate
rather than edit**, because *"do not silently write measure rests"* is cheaper
to enforce than a merge conflict is to untangle. Each is told to append ONE
CLAUDE.md section and that the manager will resolve the additive conflict —
which is what the last pair produced and it took one scripted edit.

⚠️ **The 132 MB record is gitignored and existed only inside one agent's
worktree.** Three parallel jobs would each have paid ~45 minutes to re-gather
it. Staged READ-ONLY at `library/_shared-records/beethoven5-p1-p4.record.json`
(md5 `d3620ba9cb70fc93f6b7ee91b6cbe40a`) and named in all three briefs.

### What each was told NOT to do, and why that is the manager's job

* **3** — `OMR_METER_CARRY` is the obvious lever and is OFF on `n`. The brief
  carries the recorded hazard that **a lone whole rest may not corroborate a
  meter**, because it stands for the bar whatever the meter and its 4.0 is our
  own default — *and that is exactly the population this job works on*, so it
  must say how it avoids the fixpoint. **Measure and recommend; the default
  flip is Sean's.**
* **4** — told to assume it is **mostly NOT an export bug**, because the tree
  already measures **76% of merged arcs binding fewer than two noteheads** and
  calls that residue the DETECTOR's. Forbidden to emit an arc binding fewer
  than two heads (an INVALID file), to re-open `OMR_ARC_RECLASS` (measured and
  refused twice), or to chase OMR-NED (symmetric, and it *rewards* emitting
  more). Told that **"this is a detection ceiling of size N" is a complete
  answer.**
* **5** — forbidden the tempting repair: making `_stitch_slots` join by
  ordinal across disagreeing systems is **exactly what its refusal exists to
  prevent** and would graft one instrument's music onto another. Told that
  *"this is blocked on instrument identity, which abstains on 22 of 22 staves
  here"* is a first-class answer.

All three are told that a refutation of the brief is a first-class result —
**two of the last three jobs came back that way**, and both were worth more
than their repair.
