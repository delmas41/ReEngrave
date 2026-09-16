# ReEngrave — Project Brief

**Owner:** Sean Johnson (sole user — see "Scope" in [PROJECT_STATUS.md](PROJECT_STATUS.md))
**Status:** Active development, personal-use scope

## What it is

ReEngrave takes a scanned PDF of a music score, runs optical music
recognition (OMR) to produce MusicXML, then checks the result — either
against itself (theory rules), against a known-good reference score, or
against the original PDF page-by-page with Claude Vision — and lets a human
accept, reject, or edit each flagged difference. The corrected score exports
as MusicXML, LilyPond, or an engraved PDF.

Full technical reference, architecture, and the day-to-day working notes
live in [CLAUDE.md](CLAUDE.md). This brief is the short version: what the
project is for and where it stands, not how the code works.

## The two things being built

1. **A web app** (FastAPI + React, Docker Compose) — upload a PDF, run OMR,
   review diffs, export. Auth and a Stripe payment gate are wired in but not
   the optimization target: Sean is the only user, so new work should
   minimize complexity and cost rather than build for a wider audience.
2. **An in-house OMR pipeline** (`tools/omr/`) — YOLOv8l + classical CV,
   fine-tuned on DeepScoresV2. This is where most of the recent engineering
   effort has gone: reading orchestral conductor's scores accurately is
   hard, and the project has been steadily closing the gap between "reads
   an engraved page" and "reads a real 19th-century scan."

A third, optional piece — the **Maestro theory layer**
(`tools/maestro_bridge/`) — adds harmony/rhythm validation and pitch
re-ranking against music-theory rules. Host-side only, off by default.

## How progress is measured

The project adopted **OMR-NED** (the metric used in published OMR research)
in August 2026 so its accuracy numbers are comparable to outside work, not
just to its own history. The current figure and the benchmark it's measured
on are documented in one place — the OMR-NED section of CLAUDE.md — and a
test fails if that figure drifts out of sync with the recorded JSON. Don't
requote it elsewhere; link to that section instead.

## Where things stand

See [PROJECT_STATUS.md](PROJECT_STATUS.md) for the current snapshot (updated
most recently 2026-09-02) and [NOTES.md](NOTES.md) for the backlog of
research ideas not yet scheduled. Both are living documents — check them at
the start of a session rather than trusting this brief for anything that
changes week to week.

## The example we needed was already on the shelf (2026-09-16)

The note below explains why yesterday's test couldn't answer its question: the
setting it was testing only does anything when the program **gives up** on a
line of music, and the Brahms pages never gave up. So we said what we'd need —
a score that *both* gives up somewhere *and* misreads somewhere else — and
added that no score we have does both.

**That was wrong, and it took twenty minutes to find out.** One does. It is the
same Brahms, different pages, and the evidence has been sitting in our own
saved results for weeks — across five different versions of the program, every
single time.

On that score: one line of music is misread as having four beats to the bar
where the printed page says three. Another line the program gives up on
entirely. Both faults, one score — exactly the case nobody could find.

**And then the good part.** On the line it gave up on, the program borrows the
misread answer from the line above, then checks it against the bars actually
printed there — and **throws it out.** Not by shrugging: the bars positively
say *three beats*, eight times out of nine, which is the right answer. That
matters because the one previous example of this check had it refusing
*everything*, right answers included, which tells you nothing. This one
discriminates.

**What it can't do is spell the answer.** The program works out the bar is three
beats long, and then won't write it down — because to write a time signature it
has to copy the printed form from a nearby line that agrees, and the only
nearby line is the one that misread it. So it knows the length and refuses to
guess the notation. That refusal is correct. But it means the thing standing
between us and the right answer here is a copying rule, not the arithmetic —
and that is a much more specific place to look than "the meter is hard".

Two honest limits. This does **not** mean yesterday's question is answered: the
example covers two lines of music, not a whole movement, so how far a misread
travels is still unmeasured. And three things about my own search tool were
wrong before it was right — the worst being a filter that quietly read twelve
saved files as empty, including the one file about the score that gives up. I
noticed because four scores I had answers for turned up in none of the answer
columns. **A filter that empties a file looks exactly like an empty file.**

## A test that could not test anything (2026-09-16)

Yesterday a setting was switched on by default: it lets the program carry the
beat-count from one line of music onto the next line, where the printing does
not repeat it. It clearly helps on one scanned book. Nobody had ever checked
whether it *hurts* on a book where the program misreads the beat markings in
the first place — and a mistake that gets carried forward is worse than one
that stays put.

That check was finally run, on a Brahms symphony. **It could not answer the
question, and understanding why is the result.**

The setting only does anything when the program **gives up** on a line of
music and needs to borrow an answer. On these Brahms pages it never gave up —
it produced an answer for every single line. So the setting had nothing to do,
and both halves of the test came out identical. That is not "the setting is
free"; it is "this book cannot test it." **The cost is still unknown.**

Two lessons came out of it, and both are about the measuring, not the music.

**The test did not admit it had failed.** It printed a full comparison table,
as though it had measured something, over a question it never got to ask.
Every other test of its kind in this project announces up front how much it
can actually see and stops if the answer is "nothing." This one owes the same
and did not pay it.

**One of its numbers was measured against the wrong yardstick.** A second tool
in the test checks whether each bar of music holds the right amount of time.
It had a built-in assumption about how long a bar is — taken from a
*Beethoven* score studied earlier — and nobody had told it this was Brahms,
whose bars are half again as long. So it reported that 96% of the bars were
too full, while quietly counting 684 perfectly correct bars as wrong. The
built-in assumption is now removed: the tool refuses to run until it is told
what it is looking at. Guessing was the whole problem.

**And the project's own notes described that tool as doing something it has
never done** — reading each bar's length from the music itself. It doesn't. It
only looked right because, on the one score it had been used on, the guess and
the truth happened to match.

**One useful thing did come out of it.** The Brahms file really does contain 97
beat-markings the printed page does not have. But that was equally true with
the new setting turned off — so the blame lies elsewhere, and yesterday's
change is cleared.

**And the real obstacle finally has a name.** To test this properly we need a
score that does *both* things at once: gives up on some lines *and* misreads
others. One book we have gives up often but reads correctly. Another misreads
badly but never gives up. Nobody had noticed that the two halves of the
problem have never appeared together in one book — which means every previous
worry about "not enough examples" was counting the wrong thing.

## Where the work is now (2026-09-03)

- Engraved benchmark: pooled OMR-NED **0.1306 / 2745 edits** over 11 works
  (the figure lives in CLAUDE.md's OMR-NED section; do not requote it).
- Scan domain: hollow noteheads are the top lever. All five round-2
  hollow-notehead batches are labeled, and the gated training run (Sean,
  2026-09-02) says the labels **work** — half-note detection 8 → 25 — while
  the dense-page narrowing is the fine-tune recipe's, not the labels'. v8
  stays out of the catalog until an imgsz-matched fine-tune re-gates it
  (`benchmarks/omr-labeling-survey-2026-09/GATE_RESULTS.md`).
- MXL-guided auto-labeling (`tools/omr/training/mxl_verdicts.py`) is built,
  unit-tested, and measured once on the Brahms 1 / Breitkopf batch: 51 of 56
  cells pre-filled. Its hollow-notehead signal on that print is weak because
  the reference spells out tremolo abbreviations as repeated eighths where
  the page prints one hollow head; see `version_memory.md` for the numbers.
  Inventory and plan: [docs/status-brief-2026-09-02-labeling-and-training.md](docs/status-brief-2026-09-02-labeling-and-training.md).
- Tremolo and tremolando abbreviations are reconciled by the reading (one
  head for a repeated pitch, two for an alternating pair) and a hollow-vs-black
  disagreement is routed to the human as a `CONFLICT` — the committed Brahms
  hints carry both (5 conflicts on 4 cells; all five reviewed 2026-09-03 and
  none is live — three are the reference's tie-split fragments of one printed
  note, two are accidental glyphs misdetected as heads, and the existing
  human verdicts were already right on every cell). Measured against a complete
  human pass on six cells: **precision 0.84**, so the pre-fill is a queue
  rather than labels for now — six of its eight errors are detection box
  placement, which means its accuracy rises as recognition does. A follow-up
  measurement (`benchmarks/omr-prefill-admission-2026-09/`) showed the eight
  errors are separable by three cheap signals (cell parity consistency, a
  small-head veto, the reference's own line/space variant) — in-sample the
  clean subset reaches 37/37 at 74% coverage, pending an unbiased re-test.
  The first half of that plan now lives in the pre-fill itself: the variant
  follows the reference on exact pairs, tie-split encodings collapse to the
  one printed head, and every pre-filled box carries a labels/queue
  admission tier that `--score` prices (six-cell precision 0.84 → 0.88,
  labels tier 22/22; still metadata until a random pass re-tests it). Better
  weights then lifted the same measurement to **0.96 exact with no pre-fill
  change** — the clearest evidence yet that this approach improves for free
  as recognition does, which is the reason to keep investing in it. All of
  those figures come from the same six cells, chosen as the ones the pre-fill
  decided most. ⚠️ **That measurement has now been made and it came back
  negative: on a pre-registered random sample labeled blind, precision falls
  to 0.84 (0.92 pooled over 141 boxes), under the 0.97 bar set in advance —
  so pre-filled boxes stay a review queue and are not admitted as labels.**
  The rest of this paragraph describes how that measurement was set up: a
  **pre-registered random
  sample of 25 cells labeled blind** (the UI can now withhold its own hints,
  since a human shown them cannot measure them). That sample is registered
  and waiting on labeling time; it is the step that would turn pre-filled
  boxes from a review queue into labels. A batch checked out on a machine
  that did not cut it has no cell images (they are gitignored) and shows a
  blank canvas; `tools/omr/annotate/recut_cells.py` re-renders them from the
  manifest, refusing anything whose frame does not match. Where the work stands and
  Sean's checklist: [docs/handoff-2026-09-03-prefill-session.md](docs/handoff-2026-09-03-prefill-session.md).

## The alternative pipeline met the real one (2026-09-08)

A second OMR pipeline has been built alongside the existing one — the same
page read twice, by two different designs, with the disagreements listed.
It ran against real ink for the first time today.

On one scanned Beethoven page the two paths agreed on 50 of 74 facts. The
interesting column is not the disagreements but the **abstentions**: the new
pipeline declined to answer 20 times, where the old one always answers. On
key signatures the old pipeline gave a reading for all twelve staves and was
wrong on every one that could be checked; the new one answered four and got
three right.

⚠️ **That is a feature that looks like a failure to a score.** A metric
charges for a missing answer, so a pipeline that declines to guess measures
worse while being more honest. The project has hit this before and the rule
is written down: read the abstention column before reading any score.

One open question, deliberately not guessed at: a viola staff read its key a
third short. The obvious explanation — that its unusual clef confused the
reader — was tested and **proved wrong**, so the cause is somewhere else and
a single recorded number will say where.

## The tenth export gap, and the check that could not see it (2026-09-08)

Ten times now the pipeline has recognised something correctly and then lost it
on the way to the file. The check built to catch that class of bug —
`export_coverage` — was itself iterating a **hand-written list of 19 element
names**, so anything not on that list failed nothing. `<ornaments>` was one of
the things it could not see. The list is gone; the elements to check are now
**derived from the reference files themselves**, with deliberate exclusions
written down and justified rather than silently omitted.

⚠️ **Confirming the report inverted the job, and that is the finding.** The
handoff listed two gaps; they are one, and the marks involved are **tremolos**,
which the detector does not currently produce at all — zero detections across
every stored transcription. So the export side is now wired and correct, and
the engraved number will not move until the detector reads the symbol. That is
recorded as a detection problem rather than reported as a fix, which is the
distinction this project has been burned by in both directions.

Full reading:
[benchmarks/omr-export-gaps-2026-09/FINDINGS-2026-09-08-ornaments-and-the-derived-check.md](benchmarks/omr-export-gaps-2026-09/FINDINGS-2026-09-08-ornaments-and-the-derived-check.md).

## Two problems that were four, and a rest that was not a whole note (2026-09-08)

**The largest single thing wrong with the pipeline's output was 51% of symbols
having no reference part to compare against at all** — eight of twenty scanned
pages. It was recorded as three causes filed under one name, which meant any
attempted fix would have been measured against a mixture of them.

Separated, it is **four** causes, and only one is the reader's fault: on three
pages we genuinely emit one part per system instead of joining them (a fix for
which is already built and measured, sitting behind a flag); on four more, our
staff count is **right** and the measurement is comparing it to a lineup that
counts different things — one-line percussion rules, or a harpsichord's two
printed staves listed as one instrument; and on one page the hand-verified
lineup simply does not exist. So more than half of the "biggest problem in the
output" is a problem in how it is being measured, and the split is exact:
14,992 symbols accounted for, none unexplained.

**Underneath that, the measuring instrument was quietly losing 1,771 reference
symbols** — its own self-check said so on nine of twenty pages, wrote the
verdict into a file, and nothing ever read it. Two thirds of what it lost were
rests, because a rule dropped every rest on a shared staff on the grounds that
"one part rests while the other plays, so no rest is printed" — true only when
another part *does* play. Where every part rests, the engraver prints exactly
one rest, and that was 1,050 of the 1,066 it was discarding.

**Then the rests themselves.** A whole-rest glyph does not mean a whole note's
worth of silence. An engraver fills any silent bar with one centred whole rest
whatever the time signature, and the glyph stands for the *bar* — so in 4/8 it
is half as long as it looks. We were reading the glyph correctly and applying
the wrong rule to it, and that single convention accounts for **90% of every
wrong rest duration** on the pages that can be checked.

⚠️ **The previous session's diagnosis of this was wrong in an instructive way.**
It concluded that the sizing function was correct but never given the time
signature. The function is correct — and it is never *called*: the detector
found the rest glyph, so the bar was not empty, so the branch that calls it was
never taken. The page knew its meter perfectly well; a second consumer had
never been told the convention.

⚠️ **And the standard metric cannot see the fix, on either kind of page.** Both
before-and-after scores are identical to the edit — 2,532 on engraved pages,
34,963 on scans — while the per-symbol ledger records 1,251 rest errors
corrected and *nothing else changed by a single row*. The control that makes
those zeros a result rather than a suspect: six works' rest durations
demonstrably moved, and Beethoven's Third — which is in 3/4 — now writes its
silent bars at three beats instead of four, matching its reference exactly.
This is a concrete instance of something the project measured in the abstract
last week: this metric can score a genuine duration error at zero.

⚠️ **And the conclusion I first drew from what was left was wrong, which is
worth recording as plainly as the fix.** It looked like a time-signature
problem — only 86 of the 159 parts we export carry a meter at all. Checked
before acting on it: every page that OPENS a movement reads its meter on every
single staff, and every continuation page reads almost none, because a time
signature is printed once at a movement's start and the pipeline already
carries it forward from the previous page. **The benchmark transcribes one page
at a time, so there is no previous page to carry from.** Reading two
consecutive pages in a single pass, the second page goes from 0 of 22 staves
knowing its meter to 20 of 22, and 218 of 255 silent bars come out at the
printed length instead of twice it.

So the rest fix is worth **more** in real use than the benchmark can show — and
the general lesson is larger than the rest problem: the benchmark's one-page-
per-row design silently switches off anything that works across pages, and then
that reads as a fault in the pipeline. What genuinely remains is four staves out
of thirty-four misreading the time signature itself, which is a disagreement-
resolution question rather than a reading one.

Full reading:
[benchmarks/omr-part-join-2026-09/FINDINGS.md](benchmarks/omr-part-join-2026-09/FINDINGS.md)
and [benchmarks/omr-rests-2026-09/FINDINGS.md](benchmarks/omr-rests-2026-09/FINDINGS.md).

## The pattern worth naming (2026-09-08, close of day)

Four of the five real findings in a single session were the same thing: **a
value the code had already worked out, correctly, that nothing ever read.**

- The measuring instrument's own self-check said "these figures are invalid" on
  nine of twenty pages, wrote that verdict into a file, and no run ever looked
  at it. It was flagging 1,771 reference symbols being silently dropped.
- A function that decides which time signatures are plausible names `1/4` as
  garbage *in its own documentation* — and was only ever asked which readings
  may vote, never whether a staff may keep one. Four staves shipped a
  meaningless time signature.
- The score library already recorded how many staves a page prints and even
  said in words which number to compare against; the measurement compared the
  other one, and wrote off 4,815 symbols as uncomparable over a units error.
- The exporter still treats a symbol recognised with 26% confidence and one
  recognised with 98% confidence as equally true. (Known since last week, still
  true.)

None of these needed a better reader, a new corpus, or more training. Together
they recovered 1,771 reference symbols, unblocked 7,007 more for comparison,
and corrected 1,251 rest errors. **Before building anything new here, the first
question is what the code already knows and throws away.**

⚠️ **Two claims had to be withdrawn the same day, and both were the same
mistake in reverse:** naming a mechanism without checking it. One said a
measurement gap was a reading problem when it was an artefact of how the
benchmark is cut; the other proposed a safety check for a change that, by
construction, cannot see that change. In both cases the check that would have
caught it was a single search of the codebase.

⚠️ **And one fix paid off somewhere other than where it was aimed.** The time
signature filter was shipped to correct silent-bar lengths and corrected none
of them; what it actually did was let the rhythm layer re-read four note
durations and clear nine bar-length warnings. Worth attributing effects after
the fact rather than assuming them in advance.

## Decisions made without a probability (2026-09-05)

Work on clef assignment found that a lot was being lost because a staff's clef
was either *selected* or *discarded* — no middle ground, and no way to combine
the several things the page already knew. A scan of the rest of the recognition
pipeline found the same shape in five distinct forms, written up in
[docs/handoff-probability-gates-2026-09-05.md](docs/handoff-probability-gates-2026-09-05.md).

The two largest findings are both "the number exists and nothing reads it". The
exporter never consults a detection's confidence at all — a symbol recognised
with 26% certainty and one recognised with 98% certainty are written out as
equally true. And the five self-consistency checks, which already grade how
strongly a page contradicts itself, are read by nothing: on one real scanned
score, 85 such signals fire and every one is inert.

The practical payoff is a ranked shortlist of seven places where a graded answer
would replace a yes/no one, each with an estimate of how much it touches and
which existing measurement could prove it helped. The first item goes straight
back to the clef work: a register-inversion check already fires on the same page
and is never consulted, and unlike the range test it needs no instrument name —
which matters, because on real scans the names usually are not printed.

⚠️ Nothing in that document is a measured result; it is a survey that says what
to measure next.

## Loud markings and quiet ones (September 2026)

A score tells a player how loud to be in two ways: with letters — *p*, *f*,
*sf* — and with the long hairpin wedges that mean "get louder" or "get softer".
The reader had been treated as failing at both. Measured, it is failing at
exactly one: it finds the letters on real scans at roughly seven in ten, and it
finds **none of the hairpins at all**.

The natural guess is that the letters need a text-recognition tool, since they
look like ordinary letters. They are not — they are music-font symbols that
happen to be letter-shaped, and the text reader the project already runs on
every page deliberately leaves them alone, because a single character gives it
nothing to check a guess against. The letters are already being found by the
right tool.

The hairpins are the real gap, and a reader for them already exists in the
codebase, switched off because an earlier measurement said it made the overall
score worse. That measurement was taken one day before an unrelated fix repaired
the single page responsible for half of its cost — so the first move was to
measure again rather than to build anything.

**That re-measurement has now been done, and it did two things at once.** The
guess was wrong: the page was indeed repaired, and the hairpin reader's cost on
it did not change by a single point. But the re-run also scored the same two
readings with a second instrument — one that compares symbol to symbol instead
of comparing two finished files — and that instrument says the reader recovers
**136 of the wedges the score actually contains, 97 of them exactly right**,
where before it found none at all, at the price of inventing 53 that are not
there.

So the two measurements disagree, and the disagreement is the finding rather
than a puzzle. The older one is a whole-document comparison, and adding a
correct symbol to a bar that already fails to line up makes that comparison
*worse*, not better — most of the cost is that effect and not the hairpins being
wrong. The recommendation is to switch the reader on; it is left off for now
because it is the owner's call, and because it does buy those 136 real marks
with 53 invented ones.

The same work also put both kinds of loud marking into the newer,
decision-by-decision pipeline for the first time, so that *which staff a marking
belongs to* is settled by the part of the system built to answer that question,
rather than by which slice of the page the marking happened to be cut into.
A third, smaller change — keeping half-read letters instead of discarding them —
was built, measured, and rejected: it recovers real ink, and nothing on the
page improved by it.

Part of that measuring can now be done away from the main machine. A cloud
session has none of the large files — no trained model, no score library — so it
cannot read a page. But one real scanned page's worth of already-read symbols,
its ground truth, and the hand-checked notes that line the two up are all small
enough to live in the repository, so a change to how a reading is *written out*
can be scored there. A change to how a page is *read* still cannot.

## A fact can arrive and still not be usable (2026-09-08)

To judge how well a page was read, the project has to know which printed staff
corresponds to which part of the reference score. For one dense Mahler page
that correspondence had never been written down, and it was the last such gap:
a human read the page and supplied it, closing the item.

The page still could not be judged. It prints four percussion staves that are a
single line rather than the usual five — a shape the staff finder cannot see at
all — so the new list named 21 staves while the reader had produced 17, the
two counts disagreed, and the tool refused to guess. The gap had not closed so
much as changed its name.

The repair was to record, for each of those four staves, that it is a one-line
staff. Nothing was inferred from the instrument names: the page's own notes
already listed the four in words, and a separate hand-read table in the same
file already carried the answer for all 21 staves, so the two independent
records could be checked against each other. The timpani, which looks like
percussion but is printed on a normal five-line staff, is the case a
name-matching shortcut would have got wrong.

Measured before and after with everything else held fixed, the page went from
nothing that could be said about it to 17 of its staves being assessable, and
exactly one page in the twenty changed. The four one-line staves are still
unread — the fix makes the tool *say* they are unread instead of giving up on
the whole page.

Two things worth carrying, and the second was then fixed. A test written
earlier for exactly this mistake is the only thing that caught it; every other
check passed. And the tool that writes these staff lists could not record the
one-line fact at all — it rejected it — so the next page mapped this way would
have arrived with the same problem.

That second half is now closed. The fact was being worked out correctly early
on and thrown away four separate times before reaching the file, so the writing
path can now carry it, and it checks the value rather than merely permitting
it. More importantly the tool now asks, *before* it writes, the same question
the test asks afterwards: does this list of staves add up to the number the
page says it prints? Run against the existing records, it correctly objects to
all five pages whose entries predate the field — the whole group that had the
problem, not just the one that was noticed.

The distinction worth keeping is *when* a check runs. Asking after the fact
means a person has already spent an hour confirming twenty-one staves by eye;
asking at the point of writing costs them nothing and names the missing piece.

There was a third thing, found a day later. The repair above fixed the writer
by giving it a new list of the two facts it was now allowed to record — and
that list was already short on the day it was written. One page in the set
records the clef and key signature printed on each of its staves, read by hand
off the scan precisely because the printed page and the reference file
disagree; those are not on the list, so the writer still could not re-read a
sixth of its own file. Another fact — that one line in the list is printed as
two staves — was still being dropped before the person ever saw it, so the new
check would have objected to that page with no way for them to answer.

So the list is no longer written down. It is now read out of the code that
consumes it, which cannot fall behind that code by definition, and the facts
nothing consumes yet are recorded separately with a note saying why they are
kept. The check that runs before writing is unchanged and is still the stronger
of the two: a list can only carry a fact that is there, while asking whether
the staves add up catches one that is missing.

One more thing worth carrying, because it is the same mistake in a smaller
place. A test written for the earlier repair checked that a particular word
still appeared somewhere in a file. When the code stopped using that word for
this purpose, two unrelated uses of it elsewhere kept the test passing — so it
could no longer fail. It was rewritten to check what the code actually
produces, not what it says.

---

## Taking stock of what the reader writes down

The project is being rebuilt around three stages: **gather** what is on the
page, **adjudicate** what it means, **evaluate** what follows. The point of the
split is that every decision leaves a record — including a record of having
declined to decide — so that when something is wrong you can find out *which*
judgement went wrong, rather than only that the final file differs.

That only works if the record has a word for everything worth writing down. In
September Sean noticed one it did not: **chords**. Notes stacked at the same
moment in a bar are grouped by real judgement — how close counts as "the same
moment", a check that two notes sharing a position but pointing their stems
opposite ways are two lines rather than one chord, a vote on how long the group
lasts — and none of it had a name in the record.

Rather than write a list of what else was missing, the answer was a small
program that works it out from the code itself and can be re-run whenever the
code changes. Lists written by hand in this project have a poor record of
staying true.

**And then the program proved its own point at its own expense.** While it was
being written, other sessions working in parallel found the same gaps and fixed
them — chords and rests both have proper names now. The program was still
correct, but the notes written *around* it described problems that had already
been solved. That is the exact failure the project keeps paying for: a thing
fixed in the code and left open in the writing. It was caught by trying the
merge rather than by reading it over.

Worse, the automatic check meant to prevent that had a small flaw — it compared
words letter for letter, so the plural "events" never matched the new singular
"event" — and waved the stale claim straight through. Four documents carried it
before a *different* check happened to trip. The flaw is fixed and pinned, and
the lesson is the durable part: **a safeguard against things going out of date
is itself a thing that goes out of date.**

What the program reports now: of 66 quantities the record can name, 37 are
actually collected. Seven things the older pipeline carries still have no name
at all — which voice a note belongs to, which way a stem points, whether a note
is tied to the next one, fermatas, ornaments. Fifteen kinds of printed symbol
are recognised on the page but land in the record only as "a symbol", with
accidentals the largest — and an accidental is an awkward case, because it is
not really a mark at all but a *stretch*: once printed it governs every later
note of that bar, and the record has nowhere to keep a stretch.


## What else is on the page

The same question asked the other way round: not "what does the code collect"
but "what is actually printed on a page of music, and what does a musician read
that we have no word for". Three kinds of thing, and they need different work.

Some are simply **ink we don't pick up** — rests as a category of their own,
accidentals, the octave-shift bracket that moves everything under it by an
octave. And two that are quietly valuable because the engraver has already done
work for us: **bar numbers and rehearsal letters**. We currently count the bars
on a line by measuring where the barlines are, when the printing often states
the answer.

Some are **left out on purpose, and the omission is the meaning**. Music
notation is unusual in that absence is a value: a bar left empty means that
instrument is silent, a note without an accidental inherits the one printed
earlier in the bar, a continuation line without a key signature means the key
has not changed. The project already handles some of these well. But one is a
real hole — **a bar we read nothing in and a bar that is genuinely silent come
out identical**, both written as a full bar of rest. That is exactly the
distinction the new pipeline was built to preserve, appearing in the music
rather than in the bookkeeping, and the thing that separates them (is there ink
there or not?) is already being measured for another purpose.

The third kind is not ink at all — **relations between things**. The most
valuable one is a direct enlargement of the chord finding. Notes stacked at the
same point in a bar are a chord; notes at the same point *across the whole
system* are the same moment of music. That is what a conductor's score is. It
means a page of twenty-one staves is twenty-one independent readings of the
same stretch of time, which have to agree — and nothing in the project compares
them. It is the only place on the page where the evidence is *repeated*, and
repeated evidence is what lets you work out which reading was wrong rather than
only that something is. The coarse version of this check (do the staves agree
how many bars are on the line?) already exists and has never once found a
disagreement — the disagreements are inside the bar, where nothing looks.

**That one is now built and measured (2026-09-09).** The blocker turned out
not to be the idea but the *ruler*: every glyph's position was recorded inside
its own bar, on a crop rescaled so every staff looks the same size — so two
staves' positions were not comparable numbers at all. Recording the position on
the *page* as well made the question askable. Asked of a real Brahms page, the
staves agree about where the moments are far more than their own rhythm alone
explains: the printed page needs 1,483 distinct instants to describe the same
music that a shuffled version of itself needs 2,409 for, and half the events
that would stand alone in the shuffle are corroborated in the print.

⚠️ With two honest limits, both recorded rather than smoothed over. On a
crowded bar much of that agreement is available by chance, so every reading
carries how crowded its bar was — a consumer that ignores it would rank a
weak bar above a strong one for having a bigger number. And nothing acts on
the result yet: it is written down, not used. The first sensible use is the
one the reasoning doc named — a staff playing at a moment all thirteen of its
neighbours skip is the staff worth a second look.

Full reasoning, including what is deliberately not proposed:
`docs/exploration-what-is-on-the-page-2026-09-09.md`; the measurement, the
null control and a bug it caught: `benchmarks/omr-onset-columns-2026-09/FINDINGS.md`.

## Which instrument is on which staff (Sept 14)

A printed orchestral score leaves out the instruments that are silent. So the
fifth staff down is not the fifth instrument — on one page here it is the
seventh, because three above it were left out. The project had been matching
staff to instrument **by counting down the page**, which is right only when
nothing is missing.

The code already described the better rule — read the instrument names printed
in the margin and match those instead — in its own documentation, in bold. **It
had never been written.** The function did the counting on every path, including
in the branch that claimed to be doing the naming.

Written and measured against a person's reading of the actual print: over 75
staves, counting puts **12 on the wrong instrument**; reading the names puts
**none** wrong. The honest part of that result is the cost — the new rule only
*repairs* 3 of the 12. The other 9, and 16 staves counting happened to get right,
it now declines to answer at all, because the page does not print enough to say.
That is the intended trade: a gap in the output is recoverable, an instrument's
music filed under another instrument's name is not.

⚠️ It also refuted a claim the code made about itself — a safeguard the
documentation called "the common case" turns out never to fire on a real page,
for a reason worth knowing: it guards against repeated names, and the repeated
names here are the string parts, which are exactly the ones this publisher stops
labelling. The claim is corrected in the code, not just noted.

Full reading: `benchmarks/omr-slot-index-2026-09/FINDINGS.md`.

### A bar number that means the same bar in every part

The same score, a different complaint of Sean's: *"none of the measure math
makes sense"*. A part that is silent on one system printed no bars for it, and
the exporter numbered each part by counting down from its own first bar — so
measure 82 in one instrument and measure 82 in another were **different moments
of music**. Anything reading the file downstream, including the notation
renderer we preview with, said so out loud.

Measures are now numbered by where the bar falls in the **document**, so a
number names one instant. 90 of 1,183 numbers move and **no note, rest or slur
changes** — the file is byte-identical apart from that one attribute. Where the
page cannot say how many bars a system holds, the change declines for the whole
file and leaves the old numbering rather than inventing an answer.

Full reading: `benchmarks/omr-measure-numbering-2026-09/FINDINGS.md`.

### A note printed nowhere — opened, and it is two problems

Sean's last unanswered complaint: bars the page prints as silent come out of our
system holding an actual note. Read against photographs of the print, that turns
out to be **two different faults wearing one symptom**. About a third are the
one he guessed at — a rest and a notehead are both small blobs of ink, and we
read the rest as a note. The larger half are notes belonging to the instrument
on the staff *above or below*, which drift into the silent bar because each bar
is cut out of the page with a margin of space around it.

Nothing was changed. Two reasons, both deliberate: a half-built fix already on a
shelf turns out to address only the smaller cause, and the file Sean read was
made **before** a repair that landed since and may already have removed much of
the larger one. Confirming that needs a machine holding the score library.

⚠️ It also found that the way the problem had been counted is wrong in both
directions — it was defined by our own output rather than by the page, so it
misses bars where we invent *two* notes and wrongly blames bars we simply
under-read.

Full reading: `benchmarks/omr-phantom-notes-2026-09/FINDINGS.md`.

⚠️ **Followed up the next day, and the follow-up overturned part of the above.**
The worry was that the file Sean read was made before a repair that has since
landed, so some of the problem might already be gone. That question was answered
**without** needing the score library: the earlier repair only ever acts on ink
that two staves both detected, and for **11 of the 13 bars — 20 of the 25
notes — no second staff saw it at all**. Those bars come out identical either
way, so the artefact is not stale for them. It also killed the tidy story about
where the strays come from: **five of them sit above the topmost instrument on
the page**, with nothing above to have leaked in.

Nothing was changed, again deliberately: the fix on the shelf reaches at most
the smaller group, and shipping it would have meant declaring the complaint
closed while most of it remained.

### Bars where an instrument is silent now appear

The last of the three measure-math repairs. A part that doesn't play on a
system previously had **no bars at all** there, so parts were different lengths
and one simply stopped partway. Those spans are now written as full-bar rests
in the right places.

⚠️ **On the one score available it fills in nothing, and that is the rule
behaving correctly.** A rest has to say how long it is, and the length comes
from the time signature — which we read on exactly one of this score's seven
systems, and it is the one system where no instrument is silent. So all 149
silent bars are declined and counted rather than invented at a guessed length.
A clearly-labelled what-if run, with the time signature supplied, fills all 149
and makes every part the same length — which is a measurement of what reading
the time signature better would be worth, not a result.

Full reading: `benchmarks/omr-tacet-padding-2026-09/FINDINGS.md`.

### Reading the time signature — two switches turned on, and a guard with them

A time signature is printed once, at the start of a movement, and nowhere else.
Everything downstream needs it: how long a bar should be, how long a whole-bar
rest is, whether a bar adds up. From a movement's second page onward the system
simply had none, and two mechanisms that could fill the gap were built, measured
and left switched off for want of a second test score.

**Both are now on.** With them, on the pages we have been reading, bars that add
up go from **38% to 69%**.

They landed with a guard, because turning them on is exactly what makes a
misreading dangerous: without it a time signature read on a single staff spreads
across pages. The guard is narrow on purpose — a reading nothing else confirms
still governs its own line of music, it just may not decide the next one.

⚠️ **The obvious version of that guard was measured and refused**, which is the
more useful result. Refusing any reading only one staff saw would have deleted
the one real time-signature change this system has ever found on a scanned page.
The true and false readings overlap exactly where a rule would want to cut.

⚠️ **And the measurement that motivated the refused version was ours and was
wrong** — it pooled seven generations of saved results as though they were
repeat runs of one program. Recorded, with the rule it produces: a measurement
of "how often does this happen" has to say which version of the program it was
measured on.

⚠️ **What is still not known** is the cost. The two switches are on, and the
run that would price what they cost on a badly-printed score is written and has
not been executed — it needs the full score library.

Full reading: `benchmarks/omr-meter-corroboration-2026-09/FINDINGS.md`.

### The second opinion the page prints, and why it cannot settle the argument

When an engraver is about to change the time signature, they print it twice —
once as a courtesy at the end of the line that is ending, and again at the head
of the line that begins. So on the one page where our reading of the time
signature is known to be wrong, the page itself carries a second, correct
reading a few inches earlier. Sean asked the obvious question: if the two
disagree, can we use the courtesy copy to overrule the misreading?

**Measured, and the answer is no — for a reason worth having.** The two
readings are not on the same scale. The reader scores how well printed ink
matches a template, and it scores a *wide* strip of the page higher than a
narrow one simply because a wide strip gives it more places to look — 968 of
1,612 real cases went up when the strip was widened, and **not one went down**.
The opening is read in a wide strip and the courtesy copy in a narrow one, so
comparing their scores is rigged in favour of the reading we already know is
wrong.

The natural repair — read both in the same narrow strip — **is blind**: a time
signature at the start of a line sits behind the clef and the key signature, ten
to twelve staff-widths in. Given a narrow strip the reader found **0 of 16**
real time signatures on a page that prints one on every staff, and invented
plausible-looking wrong ones out of the clef. Widened, it found **16 of 16**.

⚠️ And the one number both readings *do* state — how many staves saw it — turns
out to be **two different counts from two different readers**, which makes that
route incoherent rather than merely unhelpful.

None of this argues against reading time-signature changes mid-line, which is a
separate mechanism built the same week: a change mid-line has no clef in front
of it, which is exactly why its window is narrow.

**What is not known:** this is one piece of music with three courtesy copies,
and the case that would cost us something — a courtesy copy that is wrong where
the opening is right — has never once been seen. The cheapest thing that would
move it is a second score, and its test fixture already exists.

Full reading: `benchmarks/omr-meter-cautionary-arbiter-2026-09/FINDINGS.md`.

### The thing that was blocking us turned out not to be true

Almost every finding about time signatures ends the same way: *we only have one
piece of music that does this, so we cannot tell whether what we learned is
about the program or about that one score.* It appears in five separate
write-ups, and each one names a single candidate second score to try next.

Nobody had counted how many we actually have. **We have 32.**

The project keeps a small committed fact-file for each of 97 works, generated
from the reference sheet music — what meter it is in, how many bars, where the
meter changes. Those files answer the question directly and need none of the
large machinery: no score library, no trained model, no engraving software. The
count was a two-minute query nobody had run, because each session reached for the
next score by name instead.

⚠️ **And the shape matters more than the number.** A time-signature change that
makes bars a different LENGTH can be checked by adding up the notes in a bar. One
that changes only how the meter is *written* — `4/4` printed as a `¢`, same
length — cannot be, ever, by construction rather than by bad printing. Of the 143
changes, **7 are that second kind**, and we have measured exactly one of them.
Six are sitting there unused.

⚠️ That also re-reads the piece we were about to spend a long run on: Beethoven
5's finale at bar 364 is one of the seven, not one of the ordinary ones, so the
bar-counting check would have been silent there by design. Worth knowing before
the run rather than after. And a **cheaper** version of the same test was never
considered — Beethoven's First Symphony makes the identical change at bar 13.

⚠️ **What this does not show:** nothing was read, rendered or scored. Whether we
hold a printed edition of each of those 32 works, and whether its pages are legible
enough to read the change off, are two further questions — but they are checkable
questions about our library, where before we thought the problem was that the
music itself did not exist.

⚠️ **And the follow-up question answered itself the same afternoon.** Having
found 32 candidate works, the obvious next question was whether we actually own
printed editions of them — which I said would need the big score library on the
desktop machine. That was wrong for the same reason: the library's *catalogue*
is committed even though the PDFs are not, so it records what we hold. **We hold
all 23 of the ones we can match by name, and none is missing.**

The sharper version: the "printed one way, sounds another" case had been
measured on a single publisher. All six unmeasured instances are on disk across
**four** publishers — including two whose printing this project has never once
read. That was the part most likely to make our conclusions parochial, and it
turns out to be fixable from files we already have.

⚠️ **What is still genuinely unknown** is whether those pages are legible enough,
and which page of each PDF the change actually falls on. The second one needs a
human checking a page against the printed bar numbers — that is real work, and it
is now the only part that needs the desktop.

Full reading: `benchmarks/omr-meter-fixture-pool-2026-09/FINDINGS.md`.

## Running it

- **Web app:** `docker compose up -d` → http://localhost
- **CLI:** `python3 -m tools.omr.transcribe score.pdf` — no Docker needed
- **Production:** a self-hosted VPS via `scripts/deploy.sh` +
  `docker-compose.prod.yml` (Traefik, Let's Encrypt). This is the deploy
  path actually in use — see the note in `version_memory.md` about the
  unused/disabled GitHub Actions Vercel+Railway workflow.

Full setup and environment variables: CLAUDE.md → "Running locally" and
"Environment variables".

## Surya, measured: it is switched on now (2026-09-16)

The question above was answered by measuring it, and both OCR rungs are now
**on by default**. Reading the instrument names off a scan's margin costs
about a minute and a half per page of a run that takes half an hour, and on
the test document it produced **fifty names over seventy-five staves, every
one of them correct** when checked against what a human read off the printed
page. The free alternative — the text hidden inside the PDF — read nothing at
all on that 1870 edition, so this is the difference between knowing which
instrument each staff belongs to and guessing from its position.

The surprise was elsewhere. A *second* use of the same OCR, reading tempo and
expression words printed inside the music, has been switched on since early
September and had never been timed on a scan. It costs nearly three times as
much as the switch under discussion and, on this document, recovered six
words. Turning it off while leaving the instrument-name reader on makes the
whole run faster than it is today. That is now the thing to look at, and its
value on cleanly engraved scores is not in doubt — only on scans.

## The Surya opt-in, and a number that was never measured (2026-09-16)

Sean asked whether the staged pipeline should opt in to the free local OCR
(Surya) for reading instrument names off a scan's margin, what it adds per
page, and whether an in-house OCR model would be worth training. The answer
was scoped from committed artefacts without running anything.

Three things turned out to be different from how they were remembered. The
"time it adds" figure the opt-out cited — three quarters of a run — **does not
exist in the file that was cited for it**; the one real comparison on the same
pages says about 18%, once, on different code. The OCR is **already running on
every staged page** for a different job (reading tempo and expression words),
so the switch in question saves one of two model loads, not the load. And the
staged record cannot currently tell a machine with no OCR installed from a
page that prints no instrument names — which is the exact shape of failure
this project has been burned by most, and the fix that has to land before any
default moves.

⚠️ **Training our own OCR is the wrong spend.** The free reader ties the paid
one on every label the ground truth can check; what it loses is crop clipping,
one-letter lexicon slips, and the ability to read a smudged name from the
names above it — none of which a retrained recognizer fixes. The project has
already run eleven small-corpus fine-tunes on this pipeline and every one
deleted whole symbol classes. The cheap, well-aimed work is elsewhere:
render the dynamics glyphs from the music font already in the repo, widen the
margin crop, and wire the per-work instrument roster into the staged path.

Decision: turn both free OCR readers on together, after the record fix and a
short pre-registered timing run — Sean's call at the flip. Full reading and
the start prompt for the next local session:
[docs/scope-surya-staged-optin-2026-09-16.md](docs/scope-surya-staged-optin-2026-09-16.md).
