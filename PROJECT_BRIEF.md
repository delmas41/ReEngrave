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
the single page responsible for half of its cost — so the first move is to
measure again rather than to build anything.

Part of that measuring can now be done away from the main machine. A cloud
session has none of the large files — no trained model, no score library — so it
cannot read a page. But one real scanned page's worth of already-read symbols,
its ground truth, and the hand-checked notes that line the two up are all small
enough to live in the repository, so a change to how a reading is *written out*
can be scored there. A change to how a page is *read* still cannot.

## Taking stock of what the reader writes down

The project is being rebuilt around three stages: **gather** what is on the
page, **adjudicate** what it means, **evaluate** what follows. The point of the
split is that every decision leaves a record — including a record of having
declined to decide — so that when something is wrong you can find out *which*
judgement went wrong, rather than only that the final file differs.

That only works if the record has a word for everything worth writing down. In
September Sean noticed one it did not: **chords**. Notes stacked at the same
moment in a bar are grouped by a real piece of judgement — how close in
horizontal position counts as "the same moment", a check that two notes sharing
a position but pointing their stems opposite ways are two separate lines rather
than one chord, and a vote on how long the group lasts — and none of that had a
name in the record. It was happening, and it was invisible.

Rather than write a list of what else might be missing, the answer is a small
program that works it out from the code itself and can be re-run whenever the
code changes. Lists written by hand in this project have a poor record of
staying true.

It found two different problems that look the same from a distance. Some things
are **not collected at all** — fermatas, for instance, are recognised on the
page and written into the final file, and the record has no word for one. Others
**are collected, under a name too general to be useful**: every mark the
recogniser finds is filed as "a symbol", so slurs, ties, accents and dynamic
markings are all genuinely in there, and the step that needs to reason about
slurs specifically cannot reach them — it asks for slurs and is told there are
none. The first needs a new reader. The second only needs the filing corrected,
which is much cheaper.

The most useful thing it turned up was about work already planned. Six steps in
the new pipeline are known to be unwritten placeholders, and the natural reading
was that each needs its decision-making written. In fact **every one of them is
also missing its input** — so each is two jobs rather than one, and for four of
the six the missing half is the cheap filing fix rather than new recognition
work. Encouragingly, every step that is finished is properly fed.


## Running it

- **Web app:** `docker compose up -d` → http://localhost
- **CLI:** `python3 -m tools.omr.transcribe score.pdf` — no Docker needed
- **Production:** a self-hosted VPS via `scripts/deploy.sh` +
  `docker-compose.prod.yml` (Traefik, Let's Encrypt). This is the deploy
  path actually in use — see the note in `version_memory.md` about the
  unused/disabled GitHub Actions Vercel+Railway workflow.

Full setup and environment variables: CLAUDE.md → "Running locally" and
"Environment variables".
