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
