# ReEngrave — CLAUDE.md

The spec: what the system is, the rules a session works under, and where
everything else lives. It restates no measurement — every number is produced
by a tool it names or lives in a benchmark `FINDINGS.md`. Loaded into every
session, so it stays short; the detail is in the docs §8 indexes.

**Read in this order before you start:** this file; [ROADMAP.md](ROADMAP.md)
(your work is an item on it or it is not work); [docs/DECISIONS.md](docs/DECISIONS.md)
(append-only, newest lines first — Sean's rulings outrank anything below);
then only the §8 doc your lane needs.

---

## 1. What the product is

ReEngrave reads a scanned or engraved orchestral score (a PDF, normally an
IMSLP edition in the score library) and produces MusicXML and a
LilyPond-engraved PDF of the same music, to be cleaned up by a musician, not
re-entered.

**Definition of done** (plan §4): one command, a whole movement, MusicXML
and a LilyPond PDF, in which every bar the reader could not read is MARKED
as unread and never invented, every staff is named or held out and counted,
meter/key/clef are right or abstained, and the cleanup — counted in
fix-actions per page — is small enough that Sean would rather fix than
re-enter.

Sean is a musician who reads these plates. He is the cheapest evidence in the
project. Ask him.

---

## 2. The ten rules

1. **Brief from the tree, not from a document.** `git log --all -S <thing>`,
   `ls benchmarks/`, `python3 -m tools.omr.staged.check` before the first
   line. A withdrawn investigation changes no code; open the benchmark
   directory named after the thing.
2. **Say which path.** Every claim about a mechanism names LEGACY or STAGED.
3. **Ask first.** How would a human read this off the page, and which
   engraving convention governs it. One line to Sean before code. If nobody
   can be asked, write `CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT
   CONFIRMED` at the top and proceed.
4. **One objective, three measures.** Report against the acceptance set
   (`docs/measuring.md`). Anything a lane measures internally is a control.
5. **Reach before accuracy, and print before default.** No default flips on
   agreement with our own reading. A crop is cheaper than a lane.
6. **Connect, never guess.** A wiring change may connect a decision, never
   let one guess. Guessing lives in INFER and is labelled.
7. **A control must be able to fail.** Run it where it fails before trusting
   it where it passes. A number that is exactly another number is a
   computation, not a measurement. **Before trusting any result, ask who
   says it's right:** Sean, the print or the reference encoding is evidence;
   a model's own output, or a result whose raw data is gone, is not.
8. **A fallback never converts "cannot tell" into an answer** — not "same",
   not "clean", not a whole rest that means silence.
9. **No new flag, benchmark directory, derived check or handoff without a
   roadmap item.** Findings go in the benchmark's `FINDINGS.md`; general
   lessons become a rule here or a DECISIONS line; nothing is restated
   anywhere else.
10. **The tree outranks every ledger** — a commit message, a report, a
    handoff, this file. `git merge-base --is-ancestor` settles where work is.

---

## 3. The stage model

Two readers: **STAGED** (`tools/omr/staged/`) is the product path; **LEGACY**
(`tools/omr/transcribe.py`, `export.py`, `contextual.py`) is FROZEN — bug
fixes only, no new mechanisms or flags, and its flags may not be read from
`staged/`. Shared: the detector, staff/system/measure extraction, the header
readers, the text readers, the library (`docs/staged-internals.md` §1).

| stage | question | acts when |
|---|---|---|
| **GATHER** | what is on the page? | always — decides nothing |
| **ADJUDICATE** | what does this ONE thing mean, on what evidence? | it can read it; else abstains |
| **EVALUATE** | what follows NECESSARILY from what we now know? | the answer is forced |
| **INFER** | what is most LIKELY, given everything at once? | the answer is best — labelled |
| **EXPORT** | write it, and count what did not make it | always |

The one question that decides a stage: **does the answer FOLLOW, or is it
merely BEST?** EVALUATE goes silent where two answers both fit; INFER alone
chooses between them, only among a reader's own candidates, and never
overturns a DECIDED verdict. EXPORT refuses to argmax a narrowing and
RAISES rather than silently dropping a notehead. Until further notice every
test is GATHER + ADJUDICATE only (Sean, 2026-09-30). The record, the
adjudicators, the derived checks: `docs/staged-internals.md`.

---

## 4. What the output may say (Sean, 2026-10-12/13)

- **Nothing uncertain is ever written unmarked.** Every symbol is READ (seen
  clearly, written plain, held to a very high bar), GUESSED (an INFER
  collapse, a bar-sum confirmation, or any reading below the READ bar —
  written AND flagged blue `#1F6FEB`, carrying its candidates) or UNREAD
  (marked red, nothing invented). *"I don't want any hidden. I can't fix
  those."*
- **A note is an eighth only on evidence** — a flag or beam read on its
  stem, or a value shared from it. Bar arithmetic may CONFIRM a value the
  page already supports; it never SUPPLIES one, and never shortens a note
  with no flag and no beam seen. Two exceptions (Sean, 2026-10-17), both
  written GUESSED (blue): a bar holding ONE event (one head, or one chord
  on one stem) under a known meter may take the value that fills it; and
  where every other note in the bar is DECIDED and one note is narrowed to
  exactly two values, the bar may choose the LONGER when it fills the bar.
  A DECIDED note is never moved by the bar.
- **The written value comes from the shape; a tuplet exists only where its
  marking is seen.** A bar that adds up only under an unmarked tuplet
  confirms nothing.
- **Only a clef stands before the key accidentals**, and key accidentals
  come in the fixed flat/sharp order; a slot out of order is a place to
  look again, never a rest.
- **The 95% bar is not fixed** (*"I am not tied to 95%"*): the bar for a
  DECIDED rule is set by the cost of being wrong
  (`docs/plan-2026-10-12-inference-principles.md`); measure it on Sean's
  blind tiles per lane, never assume it.

**How inference decides** (Sean, 2026-10-13, adopted from
`docs/plan-2026-10-12-inference-principles.md`; the full checklist is there):

- **A convention is a prior; a cut-off is a measurement.** A rule resting on
  a confirmed engraving convention may decide; a rule resting on a number
  tuned on our two plates may only NARROW until another publisher confirms it.
- **Count evidence by its source, not its number.** Two readings of the same
  ink fall together and count once; a second witness comes from a different
  source. The bar sum inherits every error in the bar, so it is the weakest
  witness and can only confirm.
- **A refusal says how close it came.** Every non-structural refusal records
  its candidates and signed margin; near-misses go to Sean as blind tiles,
  which tell "keep working" (wrong cut, or measure locally) from "wrong axis".
- **Before landing, ask:** what evidence, from which source, what happens
  when the rest of the bar is wrong, and who said it's right.

---

## 5. Page conventions every lane needs

Page facts and DECISIONS never quietly disagree: a ruling that changes a fact updates `docs/page-facts.md` in the same commit with its SCOPE (general or a named publisher/score/staff kind); a lane that finds them disagreeing stops and asks Sean, never picks a winner.

The full list with Sean's quotes and dates is `docs/page-facts.md`; the
registry is `tools/omr/conventions.py`. The ones that cost lanes weekly:

- A whole rest means the BAR whatever the meter. A meter or key change is
  printed on every staff at one bar; a change HOLDS until the printed
  return — where the bars overturn a carry, a return was MISSED: label and
  mark, never switch silently.
- Stems: up → right, down → left. Every note on one stem shares one written
  value; a whole note has no stem. An arc is OVER its notes, a hairpin
  BETWEEN; of stacked arcs the nearer is the tie.
- **The ledger lines name the owner**; there is no far note without one, so
  "no rungs either way" is OUR failure — abstain and count it.
- **Measure against the staff LOCALLY**, at the subject's x; a scanned staff
  tilts and ~1 px decides a near-boundary pitch.
- Litolff MERGES and Breitkopf SHATTERS: an ink component is not a mark.
  A cell index restarts per system: key a bar on (page, system, cell).
- A word printed between the staves of a brace names every staff in that
  brace, each with its own crook (`Hr.` with `(C)`/`(Es)`); a brace alone
  names nothing (it also groups Fag./K-Fag. and 1./2. Viol.). The condensed
  count is an encoding property and cannot come from the page.
- Two witnesses off one raster fall silent together; a second witness comes
  from a different source (catalog, roster, a clef-free range check).

---

## 6. How a session works

Check yourself against Sean's past answers first: `python3 -m tools.omr.staged.judged score REC --doc litolff|brahms`.

**Where.** A worktree off `origin/main`, never the main checkout; symlink
the four root assets first (`docs/running.md` §1). Never `git checkout` a
dirty file; never bare `git stash`. Claim a ROADMAP number by pushing its
row to main before building; fence lanes by FUNCTION NAME when two touch one
file.

**Lean lanes, one shared box** (Sean, DECISIONS 2026-10-12 "HOW LANES
RUN", after two machine crashes; ROADMAP "How to work"): at most 2–3 lanes
at once, every lane on Sonnet; one page gather at a time; the fast tier at
≤ 4 workers or serial; every lane commits and pushes at each milestone;
test output quiet (pass count + failures only); landings, answer-recording
and crash recovery go to a fresh small agent with a short brief, never by
resuming the big lane agent; blind tiles and print checks are kept in full. Machine time is free, context and tokens are not —
long runs are unattended nohup scripts that write a small summary, never
per-change whole-movement A/Bs. Never `pkill -f llama-server`. Sean runs
the overnight re-gather; never ask about it.

**Evidence** (Sean's rules): prove a lane cheaply — tests + one page or
record + crops. Blind tiles go to Sean with nothing of ours drawn and his
answers are recorded in `answers.json` and a DECISIONS line. Who says it's
right: the print, Sean, or the reference encoding — never our own output.
A change is proposed to Sean before dispatch; ask him one plain question,
say what each crop colour means, no tables.

**Landing.** Every lane report is a ledger: check its claims against the
tree with one command before believing it. Merge main first; an `A/B` on a
cached run or a dirty record is not a result. A session ends by updating its
ROADMAP line, adding one entry to `version_memory.md` (and `PROJECT_BRIEF.md`
where the state it describes moved) and, if it learned something general, a
rule here or a DECISIONS line — not a handoff.

**Tests.** `pytest -m "not slow" tools/omr/tests` is the fast tier; a new
file whose code names `library/`, `omr-weights`, a venv or a `.pdf` goes
slow silently until measured. Do not edit `tools/` while a suite runs.
`python3 -m tools.omr.staged.check` — the open-findings number must go down.

---

## 7. The detector in one paragraph

A box the detector never drew has no subject; no stage can repair it.
Fine-tuning deletes classes in the last layer, so production is a grafted
head (`docs/detector.md`); never load `phase-j-mix`; never erase staff
lines before the detector; weights route by input domain. New weights are
tested `--through adjudicate` against a copy of production.

---

## 8. Where everything else lives

| read | when you need |
|---|---|
| `docs/running.md` | setup, worktree symlinks, every CLI, the small/full re-gathers, the web app, deployment |
| `docs/staged-internals.md` | the record model, scopes, adjudicators, EVALUATE/INFER/EXPORT, the derived checks and their blind spots |
| `docs/page-facts.md` | every engraving/plate convention with Sean's quotes and dates |
| `docs/measuring.md` | the acceptance set, A/B rules, test tiers, flags |
| `docs/data-sources.md` | library, rosters, dossiers, fact sheet, conventions registry |
| `docs/detector.md` | weights, labels, fine-tuning facts, labeling UI |
| `docs/flags-2026-09.md` | the verdict on every flag |
| `docs/<stage>-sequence-*.md` | the order inside each stage |
| `docs/plan-2026-09-22-from-here-to-a-finished-score.md` | why the roadmap looks as it does |
| `docs/plan-2026-10-12-inference-principles.md` | READ/GUESSED/UNREAD and the cost-of-error bar |
| `benchmarks/<name>/FINDINGS.md` | every measurement, one directory each |
| `docs/chronicle-2026-09.md` | May–Sept history; search it, never brief from it |
| `docs/claude-md-migration-2026-10-13.md` | where each line of the old 6,000-word CLAUDE.md went |

```
tools/omr/staged/      product pipeline     tools/omr/            shared readers + frozen legacy
tools/omr/tests/       tests (fast tier)    tools/omr/training/   datasets, training, head surgery
tools/omr/annotate/    labeling UI          tools/library/        score library + IMSLP provenance
data/dossiers/         97 per-work facts    data/hand-truth/      Sean's labeled pages
benchmarks/            FINDINGS per lane    out/print/            crops and blind tiles for Sean
library/, omr-weights/ gitignored, machine-local       backend/, frontend/   the web app
```

`PROJECT_BRIEF.md` is the short "what and where"; `version_memory.md` the
change log; `PROJECT_STATUS.md` and `NOTES.md` are frozen history.
